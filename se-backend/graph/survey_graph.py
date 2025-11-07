from typing import List, TypedDict
from langchain_core.messages.base import BaseMessage
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import interrupt
from services.service_manager import service_manager
from utils.custom_serializer import CustomSerializer
from utils.redis_checkpointer import RedisCheckpointer
from typing import Dict, Any
from utils.unified_logger import get_logger
from utils.chat_logger import ChatLogger
from langchain_core.messages.ai import AIMessage
import os


class SurveyGraphState(TypedDict):
    messages: List[BaseMessage]
    steps: List[Dict[str, Any]]  # 步骤内容及元数据，包含 content、type、branches 等字段
    system_prompt: str
    background_knowledge: str
    max_turns: int
    current_step: str
    current_step_messages: List[BaseMessage]
    thread_id: str
    end_message: str


class SurveyGraph():
    def __init__(self, steps: List[Dict[str, Any]]):

        self.logger = get_logger(__name__)
        self.config = service_manager.get_config()
        llms = service_manager.get_llms()
        self.fast_llm = llms.get('fast_llm')
        self.store = service_manager.store
        self.steps = steps
        
        # 使用 Redis checkpointer 替代 MemorySaver，支持分布式部署
        redis_client = service_manager.get_redis_client()
        self.checkpointer = RedisCheckpointer(
            redis_client=redis_client,
            key_prefix=self.config.redis_key_prefix,
            serde=CustomSerializer(),
            ttl=self.config.redis_ttl if self.config.redis_ttl > 0 else None
        )

        chat_log_path = getattr(self.config, 'chat_log_path', 'logs/chat_logs') if self.config else 'logs/chat_logs'
        self.chat_logger = ChatLogger(chat_log_path)

        self.graph = self._build_graph()

        self.logger.info(f"SurveyGraph 实例创建完成，包含 {len(steps)} 个步骤")

    def _build_graph(self) -> CompiledStateGraph:
        """构建条件执行图 - 支持路径执行"""
        workflow = StateGraph(SurveyGraphState)

        if not self.steps:
            raise ValueError("Steps列表不能为空")

        length = len(self.steps)
        for i in range(length): # type: ignore[arg-type]
            workflow.add_node(str(i) + "_q", self._generate_question)
            workflow.add_node(str(i) + "_a", self._get_user_answer)
        workflow.add_node("end_survey", self._end_survey)

        workflow.set_entry_point("0_q")

        for i in range(length): # type: ignore[arg-type]
            edge_map = {"end_survey": "end_survey"}
            for j in range(i, length): # type: ignore[arg-type]
                edge_map[str(j) + "_a"] = str(j) + "_a"
                edge_map[str(j) + "_q"] = str(j) + "_q"
            workflow.add_conditional_edges(
                str(i) + "_q",
                self._should_continue,
                edge_map
            )

        for i in range(length): # type: ignore[arg-type]
            edge_map = {"end_survey": "end_survey"}
            # 添加当前问题节点（用户回答后可能返回到同一问题节点继续提问）
            edge_map[str(i) + "_q"] = str(i) + "_q"
            for j in range(i, length): # type: ignore[arg-type]
                edge_map[str(j) + "_q"] = str(j) + "_q"
            workflow.add_conditional_edges(
                str(i) + "_a",
                self._should_continue,
                edge_map
            )

        workflow.add_edge("end_survey", END)
        compile_graph = workflow.compile(checkpointer=self.checkpointer)
        # self._visualize_graph(compile_graph)
        return compile_graph

    def _should_continue(self, state: SurveyGraphState):
        """判断是否继续当前节点或进入下一个节点
        返回:
            - 节点名称字符串，如 "0_q", "1_q", "end_survey"
        """
        return state.get("current_step")

    def _assemble_conversation_context(self, current_step_messages):
        messages_text = []
        for msg in current_step_messages:
            content = msg.content if hasattr(msg, 'content') else str(msg)
            if isinstance(msg, HumanMessage):
                messages_text.append(f"用户回复：{content}")
            elif isinstance(msg, AIMessage):
                messages_text.append(f"AI提问：{content}")
            else:
                messages_text.append(str(content))
        conversation_context = "\n".join(messages_text) if messages_text else "无对话记录"
        return conversation_context

    def _generate_question(self, state: SurveyGraphState):
        current_step_index, _ = state.get("current_step").split("_")
        current_step_messages = state.get("current_step_messages")
        steps = state.get("steps")
        max_turns = state.get("max_turns")
        messages = state.get("messages")

        if len(current_step_messages) == 0:
            step_message = AIMessage(content=steps[int(current_step_index)]["content"]) # type: ignore[arg-type]
            messages.append(step_message)
            current_step_messages.append(step_message)
        response = self.fast_llm.invoke(messages)
        response_content = response.content if hasattr(response, 'content') else str(response)
        if response_content.startswith("# 目标"):
            response = self.fast_llm.invoke(messages)
            response_content = response.content if hasattr(response, 'content') else str(response)

        is_finish = "FINISH" in response_content.upper() or len(current_step_messages) >= max_turns * 2 + 1
        if is_finish:
            next_step = str(int(current_step_index) + 1) + "_q" \
                if int(current_step_index) + 1 < len(state.get("steps")) else "end_survey"

            if steps[int(current_step_index)]["type"] == "condition": # type: ignore[arg-type]
                conversation_context = self._assemble_conversation_context(current_step_messages)
                condition_prompt = f"""根据对话记录分析是否满足判断条件，若满足则回复'Y'，否则回复'N'，只回答"Y"or"N"，不要其他内容。
                判断条件：{steps[int(current_step_index)]["condition"]}  
                对话记录：{conversation_context}"""
                response = self.fast_llm.invoke([HumanMessage(content=condition_prompt)])
                result = response.content.strip().lower()
                branches = steps[int(current_step_index)]["branches"] # type: ignore[arg-type]
                selected_branch = branches[0] if "y" in result or "yes" in result or "true" in result else branches[1]
                next_step = "end_survey" if selected_branch.upper() == "END" else str(int(selected_branch) - 1) + "_q"

            updated_state = {
                **state,
                "current_step": next_step,
                "current_step_messages": [],
            }
        else:
            ai_response = AIMessage(content=response_content)
            updated_state = {
                **state,
                "current_step": current_step_index + "_a",
                "messages": messages + [ai_response],
                "current_step_messages": current_step_messages + [ai_response],
            }
        return updated_state

    def _get_user_answer(self, state: SurveyGraphState):

        user_message = HumanMessage(content=interrupt(state))

        current_step_index, _ = state.get("current_step").split("_")
        next_step = current_step_index + "_q" if int(current_step_index) < len(state.get("steps")) else "end_survey"

        updated_state = {
            **state,
            "current_step": next_step,
            "messages": state["messages"] + [user_message],
            "current_step_messages": state["current_step_messages"] + [user_message],
        }
        return updated_state

    def _end_survey(self, state: SurveyGraphState):
        """结束调研节点 - 输出配置的结束语并保存聊天记录"""
        end_message = state.get("end_message")
        end_ai_message = AIMessage(content=end_message)

        # 添加结束消息到消息列表
        messages = state["messages"] + [end_ai_message]
        conversation_id = state.get("thread_id")

        try:
            saved_path = self.chat_logger.save_chat_log(messages, conversation_id)
            self.logger.info(f"调研会话结束，聊天记录已保存到: {saved_path}")
        except Exception as e:
            self.logger.error(f"保存聊天记录失败: {str(e)}")

        updated_state = {
            **state,
            "messages": messages,
        }
        return updated_state


    def _visualize_graph(self, compiled_graph):
        try:
            graph = compiled_graph.get_graph()
            png_data = graph.draw_mermaid_png()

            if png_data:
                logs_dir = "logs"
                if self.config:
                    logs_dir = getattr(self.config, 'log_dir', 'logs')

                os.makedirs(logs_dir, exist_ok=True)
                import time
                png_file = os.path.join(logs_dir, f"survey_graph_{time.time()}.png")

                with open(png_file, 'wb') as f:
                    f.write(png_data)

                self.logger.info(f"SurveyGraph 可视化图片已保存到: {png_file}")
        except Exception as e:
            self.logger.warning(f"保存可视化图片失败: {str(e)}")
