import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from langchain_core.messages.ai import AIMessage
from langchain_core.messages.human import HumanMessage
from langchain_core.messages.system import SystemMessage
from pydantic import BaseModel
from langgraph.types import Command

from api.template import load_template_by_id, template_graph_cache
from graph.survey_graph import SurveyGraph
from utils.unified_logger import get_logger

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
async def chat_survey(request: ChatRequest):
    """与调研助手对话 - 使用astream_events实现流式响应"""
    template = load_template_by_id(request.template_id)
    conversation_id = request.conversation_id

    async def generate_stream(template):
        try:
            steps = [step["content"] for step in template["steps"]]
            survey_graph = SurveyGraph(steps)
            template_graph_cache[request.template_id + conversation_id] = survey_graph
            system_prompt = template["system_prompt"]
            max_turns = template["max_turns"]
            msg_list = [SystemMessage(content=system_prompt),
                        AIMessage(content=template["welcome_message"]),
                        HumanMessage(content=request.message)]
            initial_state = {
                "messages": msg_list,
                "steps": steps,
                "system_prompt": system_prompt,
                "max_turns": max_turns,
                "current_step": 0,
                "current_step_finish": False,
                "current_step_messages": [],
                "thread_id": conversation_id,
                "end_message": template["end_message"]
            }
            async for data in process_survey_stream(survey_graph, initial_state, conversation_id):
                yield data
        except Exception as e:
            yield f"data: {json.dumps(f'{str(e)}', ensure_ascii=False)}\n\n"

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

    try:
        async for event in survey_graph.graph.astream_events(current_state, config=config):
            print(f"收到event: {event['event']} - {event.get('name', 'unknown')}")
            if event["event"] == "on_chain_stream":
                chunk = event.get("data", {}).get("chunk", {})
                if isinstance(chunk, dict) and not "__interrupt__" in chunk:
                    for node_name, node_state in chunk.items():
                        if isinstance(node_state, dict) and "messages" in node_state:
                            last_message = node_state["messages"][-1]
                            if hasattr(last_message, 'content') and isinstance(last_message, AIMessage):
                                content = last_message.content
                                yield f"data: {json.dumps(content, ensure_ascii=False)}\n\n"
                            break
    except Exception as e:
        logger.error(f"流式处理失败: {str(e)}")
        yield f"data: {json.dumps(f'处理流式输出时出现错误: {str(e)}', ensure_ascii=False)}\n\n"


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
