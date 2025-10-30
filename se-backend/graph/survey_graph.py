from typing import List, TypedDict
from langchain_core.messages.base import BaseMessage
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import interrupt
from services.service_manager import service_manager
from utils.custom_serializer import CustomSerializer
from typing import Dict, Any
from utils.unified_logger import get_logger
from utils.chat_logger import ChatLogger
from langchain_core.messages.ai import AIMessage


class SurveyGraphState(TypedDict):
    messages: List[BaseMessage]
    steps: List[str]
    system_prompt: str
    background_knowledge: str
    max_turns: int
    current_step: int
    current_step_finish: bool
    current_step_messages: List[BaseMessage]
    is_end: bool
    thread_id: str
    end_message: str
    step_metadata: List[Dict[str, Any]]  # 步骤元数据


class SurveyGraph():
    def __init__(self, steps: List[str], step_metadata: List[Dict[str, Any]] = None):

        self.logger = get_logger(__name__)
        self.config = service_manager.get_config()
        llms = service_manager.get_llms()
        self.fast_llm = llms.get('fast_llm')
        self.store = service_manager.store
        self.steps = steps
        self.step_metadata = step_metadata or []
        self.checkpointer = MemorySaver(serde=CustomSerializer())

        # 初始化聊天记录保存器
        if self.config:
            chat_log_path = getattr(self.config, 'chat_log_path', 'logs/chat_logs')
        else:
            chat_log_path = 'logs/chat_logs'
        self.chat_logger = ChatLogger(chat_log_path)

        self.graph = self._build_graph()

        self.logger.info(f"SurveyGraph 实例创建完成，包含 {len(steps)} 个步骤")

    def _build_graph(self) -> CompiledStateGraph:
        """构建条件执行图 - 支持路径执行"""
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
                        "next": self._get_next_step,  # 根据路径决定下一步
                        "end": "end_survey"  # 进入结束节点
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

        if state["is_end"]:
            return "end"

        if current_step_finish:
            if current_step < len(steps):
                return "next"
            else:
                return "end"
        else:
            return "continue"

    def _get_next_step(self, state: SurveyGraphState):
        """根据条件跳转决定下一步"""
        current_step = state.get("current_step")
        step_metadata = state.get("step_metadata", [])

        # 获取当前步骤的元数据
        current_step_meta = step_metadata[current_step] if current_step < len(step_metadata) else {}

        # 如果是条件节点，根据条件选择下一步
        if current_step_meta.get("type") == "condition":
            next_step_id = self._evaluate_condition(current_step_meta, state)
            return self._find_step_by_id(next_step_id, step_metadata)

        # 如果是普通节点，按顺序执行下一步
        return self._get_next_sequential_step(current_step, step_metadata)

    def _evaluate_condition(self, step_meta: Dict[str, Any], state: SurveyGraphState) -> str:
        """使用AI模型评估条件并返回下一步步骤ID"""
        condition = step_meta.get("condition", "")
        branches = step_meta.get("branches", [])

        # 获取用户最后一条消息
        messages = state.get("messages", [])
        if not messages or len(branches) < 2:
            return branches[1] if len(branches) > 1 else "end_survey"

        last_message = messages[-1]
        user_response = last_message.content if hasattr(last_message, 'content') else str(last_message)

        if not condition:
            return branches[1] if len(branches) > 1 else "end_survey"

        # 使用AI模型判断条件是否满足
        condition_prompt = f"""你是一个条件判断助手。请根据以下信息判断用户的回答是否满足条件：

判断条件：{condition}
用户回答：{user_response}

请仔细分析用户回答的内容，判断是否满足上述条件。
- 如果用户回答满足条件，回答"是"
- 如果用户回答不满足条件，回答"否"
- 只回答"是"或"否"，不要其他内容"""

        try:
            # 使用AI模型进行条件判断
            response = self.fast_llm.invoke([HumanMessage(content=condition_prompt)])
            result = response.content.strip().lower()
            
            # 判断AI的回答
            if "是" in result or "yes" in result or "true" in result:
                self.logger.info(f"条件判断：满足条件 '{condition}'，跳转到 {branches[0]}")
                return branches[0]  # 满足条件
            else:
                self.logger.info(f"条件判断：不满足条件 '{condition}'，跳转到 {branches[1]}")
                return branches[1]  # 不满足条件
                
        except Exception as e:
            # 如果AI判断失败，回退到简单字符串匹配
            self.logger.warning(f"AI条件判断失败，回退到字符串匹配: {str(e)}")
            if condition.lower() in user_response.lower():
                return branches[0]
            else:
                return branches[1]

    def _find_step_by_id(self, step_id: str, step_metadata: List[Dict[str, Any]]) -> str:
        """根据步骤ID查找对应的节点"""
        for i, step_meta in enumerate(step_metadata):
            if step_meta.get("id") == step_id:
                return f"{i}_q"
        return "end_survey"

    def _get_next_sequential_step(self, current_step: int, step_metadata: List[Dict[str, Any]]) -> str:
        """获取下一个顺序步骤"""
        next_step = current_step + 1
        if next_step < len(step_metadata):
            return f"{next_step}_q"
        else:
            return "end_survey"

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

        # 某个节点直接结束
        if "END" in response_content.upper():
            updated_state = {
                **state,
                "current_step_finish": True,
                "current_step_messages": [],
                "is_end": True,
            }
            return updated_state

        is_finish = "FINISH" in response_content.upper() or len(current_step_messages) >= max_turns * 2 + 1
        if is_finish:
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
        """结束调研节点 - 输出配置的结束语并保存聊天记录"""
        end_message = state.get("end_message")
        end_ai_message = AIMessage(content=end_message)

        # 添加结束消息到消息列表
        messages = state["messages"] + [end_ai_message]
        conversation_id = state.get("thread_id")

        # 保存聊天记录
        try:
            saved_path = self.chat_logger.save_chat_log(messages, conversation_id)
            self.logger.info(f"调研会话结束，聊天记录已保存到: {saved_path}")
        except Exception as e:
            self.logger.error(f"保存聊天记录失败: {str(e)}")

        updated_state = {
            **state,
            "messages": messages,
            "current_step_finish": True,
        }
        return updated_state
