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
import os


class SurveyGraphState(TypedDict):
    messages: List[BaseMessage]
    steps: List[Dict[str, Any]]  # 步骤内容及元数据，包含 content、type、branches 等字段
    system_prompt: str
    background_knowledge: str
    max_turns: int
    current_step: int
    current_step_finish: bool
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
        self.checkpointer = MemorySaver(serde=CustomSerializer())

        chat_log_path = getattr(self.config, 'chat_log_path', 'logs/chat_logs') if self.config else 'logs/chat_logs'
        self.chat_logger = ChatLogger(chat_log_path)

        self.graph = self._build_graph()

        self.logger.info(f"SurveyGraph 实例创建完成，包含 {len(steps)} 个步骤")

    def _build_graph(self) -> CompiledStateGraph:
        """构建条件执行图 - 支持路径执行"""
        workflow = StateGraph(SurveyGraphState)

        if not self.steps:
            raise ValueError("Steps列表不能为空")

        for i in range(len(self.steps)):
            # 使用闭包为每个节点创建绑定步骤索引的函数
            workflow.add_node(str(i) + "_q", self._make_generate_question(i))
            workflow.add_node(str(i) + "_a", self._get_user_answer)
        workflow.add_node("end_survey", self._end_survey)

        workflow.set_entry_point("0_q")
        for i in range(len(self.steps)):
            workflow.add_edge(str(i) + "_q", str(i) + "_a")

        for i in range(len(self.steps)):
            # 创建条件边映射，包含所有可能的节点名称
            edge_map = {}
            
            # 为所有可能的条件跳转节点添加映射（0 到 len(self.steps)-1）
            for j in range(len(self.steps)):
                edge_map[str(j) + "_q"] = str(j) + "_q"  # 条件跳转到第j步
            edge_map["end_survey"] = "end_survey"  # 条件跳转结束
            
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
        """判断下一步应该路由到哪个节点"""
        current_step = state["steps"][state["current_step"]]
        step_type = current_step["type"]
        
        if step_type.lower() == 'linear':
            return self._should_continue_for_linear(state)
        else:
            return self._route_condition_step(state)


    def _route_condition_step(self, state: SurveyGraphState):
        """路由条件步骤到正确的下一步节点"""
        try:
            next_step_result = self._get_next_step(state)
            
            # 如果返回的是"END"字符串，直接跳转到结束节点
            if next_step_result == "END":
                return "end_survey"
            
            # 如果是索引，检查有效性并转换为节点名称
            if isinstance(next_step_result, int):
                if next_step_result < 0 or next_step_result >= len(self.steps):
                    return "end_survey"
                return str(next_step_result) + "_q"
            return "end_survey"
        except Exception as e:
            return "end_survey"


    def _get_next_step(self, state: SurveyGraphState):
        """获取条件步骤的下一个目标节点
        
        返回:
            - 如果是"END"，返回字符串"END"
            - 如果是步骤ID，返回对应的步骤索引（整数）
        """
        current_step = state["steps"][state["current_step"]]
        conversation_context = self._assemble_conversation_context(state.get("current_step_messages", []))
        condition_prompt = f"""根据对话记录分析是否满足判断条件，若满足则回复'Y'，否则回复'N'，只回答"Y"or"N"，不要其他内容。
判断条件：{current_step["condition"]}
对话记录：{conversation_context}"""

        response = self.fast_llm.invoke([HumanMessage(content=condition_prompt)])
        result = response.content.strip().lower()
        branches = current_step["branches"]

        selected_branch = branches[0] if "y" in result or "yes" in result or "true" in result else branches[1]
        if selected_branch.upper() == "END":
            return "END"

        try:
            next_step = int(selected_branch) - 1
            # 注意：这里修改 state 是无效的，因为路由函数不能更新状态
            # 状态的更新会在目标节点函数中进行
            return next_step
        except (ValueError, TypeError):
            return "END"


    def _should_continue_for_linear(self, state: SurveyGraphState):
        """判断是否继续当前节点或进入下一个节点
        
        返回:
            - 节点名称字符串，如 "0_q", "1_q", "end_survey"
        """
        current_step_index = state.get("current_step", 0)

        if not state.get("current_step_finish"):
            return str(current_step_index) + "_q"

        next_step = current_step_index + 1
        if next_step < len(state.get("steps", [])):
            return str(next_step) + "_q"
        else:
            return "end_survey"


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


    def _make_generate_question(self, step_index: int):
        """创建生成问题的节点函数，绑定步骤索引
        
        这样当条件跳转到新节点时，可以确保使用正确的步骤索引
        """
        def _generate_question(state: SurveyGraphState):
            # 更新 current_step 为当前节点的步骤索引
            current_step = step_index
            
            # 检测是否发生了步骤跳转（条件跳转或线性跳转）
            # 如果步骤索引发生变化，需要重置当前步骤的状态
            current_step_messages = [] if state.get("current_step") != step_index else state.get("current_step_messages", [])
            steps = state.get("steps")
            max_turns = state.get("max_turns")
            messages = state.get("messages")

            if len(current_step_messages) == 0:
                current_step_data = steps[current_step] if current_step < len(steps) else {}
                step_content = current_step_data.get("content", "")
                step_message = AIMessage(content=step_content)
                messages.append(step_message)
                current_step_messages.append(step_message)
            response = self.fast_llm.invoke(messages)
            response_content = response.content if hasattr(response, 'content') else str(response)

            is_finish = "FINISH" in response_content.upper() or len(current_step_messages) >= max_turns * 2 + 1
            if is_finish:
                updated_state = {
                    **state,
                    "current_step": step_index,
                    "current_step_finish": True,
                    "current_step_messages": [],  # 步骤完成，清空消息
                }
            else:
                ai_response = AIMessage(content=response_content)
                updated_state = {
                    **state,
                    "current_step": step_index,
                    "messages": messages + [ai_response],
                    "current_step_finish": False,  # 步骤未完成
                    "current_step_messages": current_step_messages + [ai_response],
                }
            return updated_state
        return _generate_question

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
