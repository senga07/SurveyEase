import json
import os
import asyncio

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from langchain_core.messages.ai import AIMessage
from langchain_core.messages.human import HumanMessage
from langchain_core.messages.system import SystemMessage
from pydantic import BaseModel
from langgraph.types import Command

from api.template import load_template_by_id, template_graph_cache, apply_variable_substitution
from api.host import load_host_by_id
from graph.survey_graph import SurveyGraph
from utils.unified_logger import get_logger
from utils.chat_logger import ChatLogger
from cfg.setting import get_settings

router = APIRouter()
logger = get_logger(__name__)
chat_logger = ChatLogger(get_settings().chat_log_path)


class ChatRequest(BaseModel):
    conversation_id: str
    message: str
    template_id: str


class ContinueRequest(BaseModel):
    conversation_id: str
    user_response: str
    template_id: str


@router.post("/chat/stream")
async def chat_survey(request: ChatRequest):
    """与调研助手对话 - 使用astream_events实现流式响应"""
    raw_template = load_template_by_id(request.template_id)
    template = apply_variable_substitution(raw_template)
    conversation_id = request.conversation_id

    async def generate_stream(template):
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

            system_prompt = build_system_prompt(template)
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
            async for data in process_survey_stream(survey_graph, initial_state, conversation_id):
                yield data
        except Exception as e:
            yield f"data: {json.dumps(f'{str(e)}', ensure_ascii=False)}\n\n"

    def build_system_prompt(template):
        system_prompt = get_host_prompt(template)
        system_prompt += "\n" + template["system_prompt"]
        background_knowledge = template.get("background_knowledge", "")
        if background_knowledge.strip():
            system_prompt = f"{system_prompt}\n# 背景知识\n{background_knowledge}"
        return system_prompt

    def get_host_prompt(template):
        host_id = template.get("host_id")
        if host_id:
            try:
                host = load_host_by_id(host_id)
                if host and host.get("role"):
                    return host['role']
            except Exception as e:
                raise ValueError(f"加载主持人配置失败: {str(e)}")
        raise ValueError("加载主持人配置失败")

    return return_response(generate_stream(template))


@router.post("/chat/continue")
async def continue_survey(request: ContinueRequest):
    """继续调研对话 - 接收用户回答并继续执行图流程"""
    conversation_id = request.conversation_id
    template_id = request.template_id
    survey_graph = template_graph_cache[template_id + conversation_id]

    async def continue_stream():
        try:
            async for data in process_survey_stream(survey_graph,
                                                    Command(resume=request.user_response),
                                                    conversation_id):
                yield data
        except Exception as e:
            yield f"data: {json.dumps(f'{str(e)}', ensure_ascii=False)}\n\n"

    return return_response(continue_stream())


async def process_survey_stream(survey_graph, current_state, conversation_id):
    """处理调研流式输出的公共逻辑"""
    config = {"configurable": {"thread_id": conversation_id}}
    end_survey_completed = False

    try:
        async for event in survey_graph.graph.astream_events(current_state, config=config):
            if event["event"] == "on_chat_model_end":
                log_llm_response(event)

            # 检测 end_survey 节点执行完成
            # 检测多种事件类型以确保捕获到节点完成
            event_name = event.get("name", "")
            if event_name and "end_survey" in event_name:
                if event["event"] in ["on_chain_end", "on_chain_start", "on_chain_stream"]:
                    end_survey_completed = True
                    logger.info(f"检测到 end_survey 节点执行，会话 {conversation_id} 即将结束")

            # 处理流式输出
            if event["event"] == "on_chain_stream":
                chunk = event.get("data", {}).get("chunk", {})
                if isinstance(chunk, dict) and not "__interrupt__" in chunk:
                    for node_name, node_state in chunk.items():
                        # 检测是否到达 end_survey 节点
                        if node_name == "end_survey":
                            end_survey_completed = True
                            logger.info(f"检测到 end_survey 节点流式输出，会话 {conversation_id} 即将结束")
                        
                        if isinstance(node_state, dict) and "messages" in node_state:
                            last_message = node_state["messages"][-1]
                            if hasattr(last_message, 'content') and isinstance(last_message, AIMessage):
                                content = last_message.content
                                yield f"data: {json.dumps(content, ensure_ascii=False)}\n\n"
                            break
        
        # 图执行完成后，清除 Redis 状态
        # 等待一小段时间确保所有状态都已保存
        if end_survey_completed:
            await asyncio.sleep(0.1)  # 等待 100ms 确保状态保存完成
            try:
                survey_graph.checkpointer.clear_thread_state(conversation_id)
                logger.info(f"已清除会话 {conversation_id} 的 Redis 状态")
            except Exception as e:
                logger.error(f"清除 Redis 状态失败: {str(e)}")
                
    except Exception as e:
        import traceback
        error_msg = str(e) if e else "未知错误"
        error_trace = traceback.format_exc()
        logger.error(f"流式处理失败: {error_msg}")
        logger.error(f"错误堆栈: {error_trace}")
        yield f"data: {json.dumps(f'处理流式输出时出现错误: {error_msg}', ensure_ascii=False)}\n\n"
        # 即使出错，如果已经执行了 end_survey，也尝试清除 Redis 状态
        if end_survey_completed:
            try:
                survey_graph.checkpointer.clear_thread_state(conversation_id)
                logger.info(f"已清除会话 {conversation_id} 的 Redis 状态（错误恢复后）")
            except Exception as clear_error:
                logger.error(f"清除 Redis 状态失败: {str(clear_error)}")


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
    filename: str
    conversation_id: str
    timestamp: str
    created_at: str
    message_count: int


@router.get("/chat/history")
async def get_chat_history():
    """获取所有聊天记录列表"""
    try:
        log_files = chat_logger.list_chat_logs()
        history = []
        
        for file_path in log_files:
            try:
                # 读取文件获取基本信息
                with open(file_path, 'r', encoding='utf-8') as f:
                    log_data = json.load(f)
                
                filename = os.path.basename(file_path)
                history.append(ChatLogSummary(
                    filename=filename,
                    conversation_id=log_data.get("conversation_id", ""),
                    timestamp=log_data.get("timestamp", ""),
                    created_at=log_data.get("created_at", ""),
                    message_count=log_data.get("message_count", 0)
                ))
            except Exception as e:
                logger.error(f"读取聊天记录文件失败 {file_path}: {str(e)}")
                continue
        
        # 按创建时间倒序排列（最新的在前）
        history.sort(key=lambda x: x.timestamp, reverse=True)
        return history
        
    except Exception as e:
        logger.error(f"获取聊天记录列表失败: {str(e)}")
        return []


@router.get("/chat/history/{filename}")
async def get_chat_log_detail(filename: str):
    """获取单个聊天记录的详细信息"""
    try:
        # 安全检查：只允许访问 chat_logs 目录下的文件
        if not filename.endswith('.json') or '..' in filename or '/' in filename:
            return {"error": "无效的文件名"}
        
        file_path = os.path.join(chat_logger.log_path, filename)
        
        # 检查文件是否存在
        if not os.path.exists(file_path):
            return {"error": "文件不存在"}
        
        # 读取并返回聊天记录
        log_data = chat_logger.load_chat_log(file_path)
        
        # 过滤消息，只返回用户和AI的消息（不返回系统消息）
        filtered_messages = [
            msg for msg in log_data.get("messages", [])
            if msg.get("type") in ["HumanMessage", "AIMessage"]
        ]
        
        log_data["messages"] = filtered_messages
        return log_data
        
    except Exception as e:
        logger.error(f"获取聊天记录详情失败: {str(e)}")
        return {"error": f"获取聊天记录失败: {str(e)}"}
