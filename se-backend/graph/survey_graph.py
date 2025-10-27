from typing import List, AsyncIterator

from langchain_core.runnables import RunnableConfig
from typing import List, TypedDict, AsyncIterator
from langchain_core.messages.base import BaseMessage
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledStateGraph
from langmem import create_manage_memory_tool, create_search_memory_tool
from langgraph.types import interrupt
from typing import Dict, Any
from services.service_manager import service_manager
from utils.custom_serializer import CustomSerializer
from utils.unified_logger import get_logger
from langchain_core.messages.ai import AIMessage


class SurveyGraphState(TypedDict):
    messages: List[BaseMessage]
    steps: List[str]
    system_prompt: str
    max_turns: int
    current_step: int
    current_step_finish: bool
    current_step_messages: List[BaseMessage]
    thread_id: str
    end_message: str


class SurveyGraph():
    def __init__(self, steps: List[str]):

        self.logger = get_logger(__name__)
        self.config = service_manager.get_config()
        llms = service_manager.get_llms()
        self.fast_llm = llms.get('fast_llm')
        self.store = service_manager.store
        self.steps = steps
        self.checkpointer = MemorySaver(serde=CustomSerializer())
        self.graph = self._build_graph()

        self.logger.info(f"SurveyGraph 实例创建完成，包含 {len(steps)} 个步骤")

    def _build_graph(self) -> CompiledStateGraph:
        """构建条件执行图 - 根据节点完成状态决定下一步"""
        workflow = StateGraph(SurveyGraphState)

        if not self.steps:
            raise ValueError("Steps列表不能为空")

        for i in range(len(self.steps)):
            workflow.add_node(str(i) + "_q", self._generate_question)
            workflow.add_node(str(i) + "_a", self._get_user_answer)

        # 添加结束节点
        workflow.add_node("end_survey", self._end_survey)

        workflow.set_entry_point("0_q")
        for i in range(len(self.steps)):
            workflow.add_edge(str(i) + "_q", str(i) + "_a")

        for i in range(len(self.steps)):
            if i < len(self.steps) - 1:
                workflow.add_conditional_edges(
                    str(i) + "_a",
                    self._should_continue,
                    {
                        "continue": str(i) + "_q",  # 继续当前步骤（多轮对话）
                        "next": str(i + 1) + "_q",  # 进入下一步骤
                    }
                )
            else:
                workflow.add_conditional_edges(
                    str(i) + "_a",
                    self._should_continue,
                    {
                        "continue": str(i) + "_q",  # 继续当前步骤
                        "end": "end_survey"  # 进入结束节点
                    }
                )
        workflow.add_edge("end_survey", END)
        return workflow.compile(checkpointer=self.checkpointer)

    def _should_continue(self, state: SurveyGraphState):
        """判断是否继续当前节点或进入下一个节点"""
        current_step = state.get("current_step")
        current_step_finish = state.get("current_step_finish")
        steps = state.get("steps")

        if current_step_finish:
            if current_step < len(steps):
                return "next"
            else:
                return "end"
        else:
            return "continue"

    def _generate_question(self, state: SurveyGraphState):

        current_step = state.get("current_step")
        current_step_messages = state.get("current_step_messages")
        steps = state.get("steps")
        max_turns = state.get("max_turns")
        messages = state.get("messages")

        if len(current_step_messages) == 0:
            step_message = AIMessage(content=steps[current_step])
            messages.append(step_message)
            current_step_messages.append(step_message)
        response = self.fast_llm.invoke(messages)
        response_content = response.content if hasattr(response, 'content') else str(response)
        is_end = "END" in response_content.upper() or len(current_step_messages) >= max_turns * 2 + 1

        if is_end:
            updated_state = {
                **state,
                "current_step_finish": True,
                "current_step_messages": [],
            }
        else:
            ai_response = AIMessage(content=response_content)
            updated_state = {
                **state,
                "messages": messages + [ai_response],
                "current_step_finish": False,
                "current_step_messages": current_step_messages + [ai_response],
            }
        return updated_state

    def _get_user_answer(self, state: SurveyGraphState):
        current_step_messages = state["current_step_messages"]
        current_step_finish = state["current_step_finish"]
        if len(current_step_messages) == 0 and current_step_finish:
            return {
                **state,
                "current_step": state["current_step"] + 1,
            }

        user_input = interrupt(state)
        user_message = HumanMessage(content=user_input)
        updated_state = {
            **state,
            "messages": state["messages"] + [user_message],
            "current_step_messages": current_step_messages if state["current_step_finish"]
            else current_step_messages + [user_message],
        }
        return updated_state

    def _end_survey(self, state: SurveyGraphState):
        """结束调研节点 - 输出配置的结束语"""
        end_message = state.get("end_message")
        end_ai_message = AIMessage(content=end_message)
        updated_state = {
            **state,
            "messages": state["messages"] + [end_ai_message],
            "current_step_finish": True,
        }
        return updated_state
