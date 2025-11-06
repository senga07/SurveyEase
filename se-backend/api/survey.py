import json
import os

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from langchain_core.messages.ai import AIMessage
from langchain_core.messages.human import HumanMessage
from langchain_core.messages.system import SystemMessage
from pydantic import BaseModel
from langgraph.types import Command

from api.template import load_template_by_id_from_db, template_graph_cache, apply_variable_substitution
from api.host import get_host_by_id_from_db
from database import get_db
from graph.survey_graph import SurveyGraph
from utils.unified_logger import get_logger
from services.chat_service import ChatService

router = APIRouter()
logger = get_logger(__name__)


class ChatRequest(BaseModel):
    conversation_id: str
    message: str
    template_id: str


class ContinueRequest(BaseModel):
    conversation_id: str
    user_response: str
    template_id: str


@router.post("/chat/stream")
async def chat_survey(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    """与调研助手对话 - 使用astream_events实现流式响应"""
    raw_template = await load_template_by_id_from_db(request.template_id, db)
    template = apply_variable_substitution(raw_template)
    conversation_id = request.conversation_id

    async def generate_stream(template, db_session: AsyncSession):
        try:
            steps = []
            for step in template["steps"]:
                step_data = {
                    "content": step.get("content", ""),
                    "type": step.get("type", "linear"),
                    "branches": step.get("branches", []),
                    "condition": step.get("condition", "")
                }
                steps.append(step_data)
            survey_graph = SurveyGraph(steps)
            template_graph_cache[request.template_id + conversation_id] = survey_graph

            system_prompt = await build_system_prompt(template, db_session)
            max_turns = template["max_turns"]
            msg_list = [SystemMessage(content=system_prompt),
                        AIMessage(content=template["welcome_message"]),
                        HumanMessage(content=request.message)]
            initial_state = {
                "messages": msg_list,
                "steps": steps,
                "system_prompt": system_prompt,
                "max_turns": max_turns,
                "current_step": "0_q",
                "current_step_messages": [],
                "thread_id": conversation_id,
                "end_message": template["end_message"],
            }
            
            # 创建会话记录
            await ChatService.create_or_update_conversation(
                db=db_session,
                conversation_id=conversation_id,
                template_id=request.template_id,
                message_count=0
            )
            
            # 保存初始消息（系统消息、欢迎消息和用户第一条消息）
            for order, msg in enumerate(msg_list, start=1):
                await ChatService.save_message(
                    db=db_session,
                    conversation_id=conversation_id,
                    message=msg,
                    message_order=order
                )
            
            async for data in process_survey_stream(survey_graph, initial_state, conversation_id, request.template_id, db_session):
                yield data
        except Exception as e:
            yield f"data: {json.dumps(f'{str(e)}', ensure_ascii=False)}\n\n"

    async def build_system_prompt(template, db_session: AsyncSession):
        host_prompt = await get_host_prompt(template, db_session)
        system_prompt = host_prompt
        system_prompt += "\n" + template["system_prompt"]
        background_knowledge = template.get("background_knowledge", "")
        if background_knowledge.strip():
            system_prompt = f"{system_prompt}\n# 背景知识\n{background_knowledge}"
        return system_prompt

    async def get_host_prompt(template, db_session: AsyncSession):
        host_id = template.get("host_id")
        if host_id:
            try:
                from api.host import get_host_by_id_from_db
                host = await get_host_by_id_from_db(host_id, db_session)
                if host and host.role:
                    return host.role
            except Exception as e:
                raise ValueError(f"加载主持人配置失败: {str(e)}")
        return ""

    return return_response(generate_stream(template, db))


@router.post("/chat/continue")
async def continue_survey(request: ContinueRequest, db: AsyncSession = Depends(get_db)):
    """继续调研对话 - 接收用户回答并继续执行图流程"""
    conversation_id = request.conversation_id
    template_id = request.template_id
    survey_graph = template_graph_cache[template_id + conversation_id]

    async def continue_stream():
        try:
            # 保存用户回复消息
            user_message = HumanMessage(content=request.user_response)
            # 获取当前消息数量
            existing_messages = await ChatService.get_messages_by_conversation_id(db, conversation_id, include_system=True)
            next_order = len(existing_messages) + 1
            await ChatService.save_message(
                db=db,
                conversation_id=conversation_id,
                message=user_message,
                message_order=next_order
            )
            
            async for data in process_survey_stream(survey_graph,
                                                    Command(resume=request.user_response),
                                                    conversation_id,
                                                    template_id,
                                                    db):
                yield data
        except Exception as e:
            yield f"data: {json.dumps(f'{str(e)}', ensure_ascii=False)}\n\n"

    return return_response(continue_stream())


async def process_survey_stream(survey_graph, current_state, conversation_id, template_id, db: AsyncSession):
    """处理调研流式输出的公共逻辑"""
    config = {"configurable": {"thread_id": conversation_id}}
    saved_message_count = 0  # 已保存的消息数量（用于确定消息顺序）
    
    # 初始化已保存消息数量
    existing_messages = await ChatService.get_messages_by_conversation_id(db, conversation_id, include_system=True)
    saved_message_count = len(existing_messages)

    try:
        async for event in survey_graph.graph.astream_events(current_state, config=config):
            if event["event"] == "on_chat_model_end":
                log_llm_response(event)

            # 处理流式输出
            if event["event"] == "on_chain_stream":
                chunk = event.get("data", {}).get("chunk", {})
                if isinstance(chunk, dict) and not "__interrupt__" in chunk:
                    for node_name, node_state in chunk.items():
                        if isinstance(node_state, dict) and "messages" in node_state:
                            messages = node_state["messages"]
                            # 保存新增的消息
                            if len(messages) > saved_message_count:
                                for i in range(saved_message_count, len(messages)):
                                    msg = messages[i]
                                    # 跳过系统消息（已在开始时保存），但需要增加计数以保持顺序正确
                                    if isinstance(msg, SystemMessage):
                                        saved_message_count += 1
                                        continue
                                    saved_message_count += 1
                                    try:
                                        await ChatService.save_message(
                                            db=db,
                                            conversation_id=conversation_id,
                                            message=msg,
                                            message_order=saved_message_count
                                        )
                                    except Exception as e:
                                        logger.error(f"保存消息失败: {str(e)}")
                                
                                # 更新会话记录的消息数量
                                try:
                                    await ChatService.create_or_update_conversation(
                                        db=db,
                                        conversation_id=conversation_id,
                                        template_id=template_id,
                                        message_count=saved_message_count
                                    )
                                except Exception as e:
                                    logger.error(f"更新会话记录失败: {str(e)}")
                            
                            # 流式输出最后一条AI消息
                            if messages:
                                last_message = messages[-1]
                                if hasattr(last_message, 'content') and isinstance(last_message, AIMessage):
                                    content = last_message.content
                                    yield f"data: {json.dumps(content, ensure_ascii=False)}\n\n"
                            break
            
            # 监听节点结束事件，检查是否到了结束节点
            if event["event"] == "on_chain_end":
                node_name = event.get("name", "")
                if node_name == "end_survey":
                    # 确保所有消息都已保存
                    try:
                        # 获取最终的消息列表
                        final_state = event.get("data", {}).get("output", {})
                        if isinstance(final_state, dict) and "messages" in final_state:
                            messages = final_state["messages"]
                            # 保存剩余的消息
                            for i in range(saved_message_count, len(messages)):
                                msg = messages[i]
                                # 跳过系统消息（已在开始时保存），但需要增加计数以保持顺序正确
                                if isinstance(msg, SystemMessage):
                                    saved_message_count += 1
                                    continue
                                saved_message_count += 1
                                await ChatService.save_message(
                                    db=db,
                                    conversation_id=conversation_id,
                                    message=msg,
                                    message_order=saved_message_count
                                )
                            # 更新会话记录
                            await ChatService.create_or_update_conversation(
                                db=db,
                                conversation_id=conversation_id,
                                template_id=template_id,
                                message_count=saved_message_count
                            )
                    except Exception as e:
                        logger.error(f"保存最终消息失败: {str(e)}")
                        
    except Exception as e:
        logger.error(f"流式处理失败: {str(e)}")
        yield f"data: {json.dumps(f'处理流式输出时出现错误: {str(e)}', ensure_ascii=False)}\n\n"


def log_llm_response(event):
    output = event.get("data", {}).get("output")
    if output:
        # 处理 AIMessage 对象
        if hasattr(output, 'content'):
            logger.info(f"llm: {output.content}")
        # 处理字典格式的输出
        elif isinstance(output, dict):
            if "content" in output:
                logger.info(f"llm: {output['content']}")
            # 如果是消息列表，取最后一条
            elif "messages" in output and isinstance(output["messages"], list):
                last_msg = output["messages"][-1]
                if hasattr(last_msg, 'content'):
                    logger.info(f"llm: {last_msg.content}")


def return_response(func):
    return StreamingResponse(
        func,
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream"
        }
    )


class ChatLogSummary(BaseModel):
    """聊天记录摘要"""
    conversation_id: str
    timestamp: str
    created_at: str
    message_count: int


@router.get("/chat/history")
async def get_chat_history(db: AsyncSession = Depends(get_db)):
    """获取所有聊天记录列表"""
    try:
        conversations = await ChatService.get_conversation_list(db)
        history = []
        
        for conv in conversations:
            history.append(ChatLogSummary(
                conversation_id=conv.conversation_id,
                timestamp=conv.timestamp,
                created_at=conv.create_datetime.isoformat() if conv.create_datetime else "",
                message_count=conv.message_count or 0
            ))
        
        return history
        
    except Exception as e:
        logger.error(f"获取聊天记录列表失败: {str(e)}")
        return []


@router.get("/chat/history/{conversation_id}")
async def get_chat_log_detail(conversation_id: str, db: AsyncSession = Depends(get_db)):
    """获取单个聊天记录的详细信息"""
    try:
        # 从数据库获取会话详情
        detail = await ChatService.get_conversation_detail(db, conversation_id)
        
        if not detail:
            return {"error": "会话记录不存在"}
        
        return detail
        
    except Exception as e:
        logger.error(f"获取聊天记录详情失败: {str(e)}")
        return {"error": f"获取聊天记录失败: {str(e)}"}
