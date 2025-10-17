"""
语音代理图(Graph)实现

本模块实现了语音对话代理的主要 LangGraph 工作流,
定义不同处理节点之间的流程和条件路由。
"""
# 从各个包中导入相关模块
import logging
import asyncio
from typing import Dict, Any, Optional, List

try:
    from langgraph.graph import StateGraph, END
    from langgraph.checkpoint.memory import MemorySaver
    LANGGRAPH_AVAILABLE = True
except ImportError:
    # LangGraph not available in test environment
    LANGGRAPH_AVAILABLE = False
    StateGraph = None
    END = None
    MemorySaver = None

from .state import AgentState, create_initial_state
from .nodes import AgentNodes

# 导入 LLM 兼容性工具
try:
    from utils.llm_compat import prepare_llm_params
except ImportError:
    def prepare_llm_params(model, messages, temperature=0.7, max_tokens=16384, **kwargs):  # 🔧 修复默认值
        params = {"model": model, "messages": messages}
        # GPT-5 系列不传 temperature，使用 API 默认值
        if not model.startswith("gpt-5"):
            params["temperature"] = temperature
        if model.startswith("gpt-5"):
            params["max_completion_tokens"] = max_tokens
        else:
            params["max_tokens"] = max_tokens
        params.update(kwargs)
        return params

try:
    from config.models import VoiceAgentConfig
    from config.settings import ConfigManager
except ImportError:
    # Fallback for when running as script
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from config.models import VoiceAgentConfig
    from config.settings import ConfigManager


logger = logging.getLogger(__name__)

# 主类
class VoiceAgent:
    """
    主语音对话代理,使用 LangGraph 进行流程控制。
    
    该类协调对话流程通过不同处理阶段:
    输入处理、LLM 调用、工具处理和响应格式化。
    """
    # 初始化方法
    def __init__(self, config: VoiceAgentConfig):
        """使用配置初始化语音代理。"""
        self.config = config
        self.logger = logger  # Set logger before building graph
        self.nodes = AgentNodes(config)
        self.graph = self._build_graph()
        
        self.logger.info("语音代理初始化成功")
    
    def _build_graph(self):
        """构建 LangGraph 工作流。"""
        if not LANGGRAPH_AVAILABLE:
            raise ImportError("LangGraph 不可用。请安装 langgraph 包。")
        
        # Create graph with state schema
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("process_input", self.nodes.process_input)
        workflow.add_node("call_llm", self.nodes.call_llm)
        workflow.add_node("handle_tools", self.nodes.handle_tools)
        workflow.add_node("format_response", self.nodes.format_response)
        
        # Set entry point
        workflow.set_entry_point("process_input")
        
        # Add conditional edges based on next_action
        workflow.add_conditional_edges(
            "process_input",
            self._route_after_input,
            {
                "call_llm": "call_llm",
                "error": END,
                "end": END
            }
        )
        
        workflow.add_conditional_edges(
            "call_llm",
            self._route_after_llm,
            {
                "handle_tools": "handle_tools",
                "format_response": "format_response",
                "error": "format_response"
            }
        )
        
        workflow.add_conditional_edges(
            "handle_tools",
            self._route_after_tools,
            {
                "call_llm": "call_llm",
                "format_response": "format_response",
                "error": "format_response"
            }
        )
        
        workflow.add_edge("format_response", END)
        
        # Compile workflow with checkpointer (memory or database)
        checkpointer = self._get_checkpointer()
        graph = workflow.compile(checkpointer=checkpointer)
        
        self.logger.debug("LangGraph 工作流编译成功")
        return graph
    
    def _get_checkpointer(self):
        """
        Get appropriate checkpointer based on configuration.
        
        Returns:
            Checkpointer instance (MemorySaver or PostgreSQLCheckpointer)
        """
        # Check if database persistence is enabled
        if hasattr(self.config, 'database') and self.config.database.enabled:
            # Check if session storage is set to database
            if self.config.session.storage_type == "database":
                try:
                    from database import PostgreSQLCheckpointer
                    self.logger.info("Using PostgreSQL checkpointer for persistence")
                    return PostgreSQLCheckpointer()
                except Exception as e:
                    self.logger.warning(
                        f"Failed to initialize PostgreSQL checkpointer: {e}. "
                        f"Falling back to memory."
                    )
        
        # Default to memory saver
        self.logger.info("Using in-memory checkpointer")
        return MemorySaver()
    
    def _route_after_input(self, state: AgentState) -> str:
        """输入处理后的路由决策。"""
        if state.get("error_state"):
            self.logger.warning(f"输入处理出错: {state['error_state']}")
            return "error"
        
        if not state.get("should_continue", True):
            return "end"
        
        next_action = state.get("next_action")
        if next_action == "call_llm":
            return "call_llm"
        
        self.logger.warning(f"输入处理后出现意外的 next_action: {next_action}")
        return "error"
    
    def _route_after_llm(self, state: AgentState) -> str:
        """
        LLM 调用后的路由决策。
        
        🆕 优化逻辑: 支持多轮工具调用
        - 如果 LLM 返回工具调用 → 进入 handle_tools
        - 否则 → 进入 format_response 生成最终回复
        """
        if state.get("error_state"):
            self.logger.warning(f"LLM 调用出错: {state['error_state']}")
            return "error"
        
        next_action = state.get("next_action")
        
        # 检查是否需要调用工具
        if next_action == "handle_tools":
            tool_call_count = state.get("tool_call_count", 0)
            max_tool_iterations = 5  # 🆕 最大工具调用次数，防止无限循环
            
            if tool_call_count >= max_tool_iterations:
                self.logger.warning(f"⚠️ 已达到最大工具调用次数 ({max_tool_iterations})，强制结束")
                return "format_response"
            
            self.logger.info(f"🔧 第 {tool_call_count + 1} 轮工具调用")
            return "handle_tools"
        
        elif next_action == "format_response":
            return "format_response"
        
        self.logger.warning(f"LLM 调用后出现意外的 next_action: {next_action}")
        return "error"
    
    def _route_after_tools(self, state: AgentState) -> str:
        """
        工具处理后的路由决策。
        
        🆕 核心优化: 工具调用后返回 LLM 进行重新思考
        - 默认行为: 返回 call_llm，让 LLM 基于工具结果重新判断
        - LLM 会决定: 是否需要更多工具，还是已经有足够信息生成回复
        """
        if state.get("error_state"):
            self.logger.warning(f"工具处理出错: {state['error_state']}")
            # 即使工具失败，也返回 LLM 让它生成 fallback 回复
            return "call_llm"
        
        next_action = state.get("next_action")
        
        # 🆕 关键改动: 工具调用后，始终返回 call_llm 进行重新思考
        # LLM 会基于工具结果判断是否需要更多工具或直接生成回复
        if next_action == "call_llm":
            self.logger.info("🔄 工具调用完成，返回 LLM 重新思考")
            return "call_llm"
        
        # 兜底: 如果节点强制指定 format_response（不太可能）
        elif next_action == "format_response":
            self.logger.info("⚠️ 工具节点直接指定生成响应（罕见情况）")
            return "format_response"
        
        # 默认行为: 返回 LLM
        self.logger.info("🔄 工具调用完成，默认返回 LLM")
        return "call_llm"
    # 同步处理单条信息
    async def process_message(
        self,
        user_input: str,
        session_id: str,
        user_id: Optional[str] = None,
        model_config: Optional[Dict[str, Any]] = None,
        external_history: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        处理用户消息并返回代理的响应。
        
        Args:
            user_input: 用户输入消息
            session_id: 唯一会话标识符
            user_id: 可选的用户标识符
            model_config: 可选的模型配置覆盖
            external_history: 可选的外部历史消息列表
            
        Returns:
            包含代理响应和元数据的字典
        """
        try:
            self.logger.info(f"处理会话 {session_id} 的消息")
            
            # Create initial state
            initial_state = create_initial_state(
                session_id=session_id,
                user_input=user_input,
                user_id=user_id,
                model_config=model_config or {}
            )
            
            # 如果有外部历史，添加到 state（即使是空列表也要添加）
            if external_history is not None:
                initial_state["external_history"] = external_history
                self.logger.info(f"🔄 Added {len(external_history)} messages to initial_state['external_history']")
            else:
                self.logger.warning(f"⚠️ No external_history provided to process_message (None)")
            
            # Configure thread for session persistence
            thread_config = {"configurable": {"thread_id": session_id}}
            
            # Run the graph
            final_state = await self.graph.ainvoke(
                initial_state,
                config=thread_config
            )
            
            # Prepare response
            response = {
                "success": True,
                "response": final_state["agent_response"],
                "session_id": session_id,
                "message_count": len(final_state["messages"]),
                "timestamp": final_state["last_activity"].isoformat(),
                "metadata": {
                    "intent": final_state.get("current_intent"),
                    "tool_calls": len(final_state.get("tool_calls", [])),
                    "model": final_state["model_config"].get("model", "unknown"),
                    "error_state": final_state.get("error_state")
                }
            }
            
            self.logger.info(f"会话 {session_id} 的消息处理成功")
            return response
            
        except Exception as e:
            self.logger.error(f"处理消息时出错: {e}")
            return {
                "success": False,
                "response": "抱歉,处理您的请求时遇到了错误。",
                "session_id": session_id,
                "error": str(e),
                "timestamp": None,
                "metadata": {"error": True}
            }
    # 查询获取到历史信息
    async def get_conversation_history(
        self,
        session_id: str,
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        检索会话的对话历史。
        
        Args:
            session_id: 会话标识符
            limit: 可选的消息数量限制
            
        Returns:
            包含对话历史的字典
        """
        try:
            # Get state from memory
            thread_config = {"configurable": {"thread_id": session_id}}
            
            # Get current state (this would be the last saved state)
            # In a real implementation, we'd retrieve from the checkpointer
            state = await self.graph.aget_state(thread_config)
            
            if not state or not state.values:
                return {
                    "success": True,
                    "session_id": session_id,
                    "messages": [],
                    "message_count": 0
                }
            
            messages = state.values.get("messages", [])
            if limit:
                messages = messages[-limit:]
            
            return {
                "success": True,
                "session_id": session_id,
                "messages": [msg.dict() if hasattr(msg, 'dict') else msg for msg in messages],
                "message_count": len(messages),
                "last_activity": state.values.get("last_activity")
            }

        except Exception as e:
            self.logger.error(f"检索对话历史时出错: {e}")
            return {
                "success": False,
                "session_id": session_id,
                "error": str(e),
                "messages": [],
                "message_count": 0
            }
    # 流式处理单条信息
    async def process_message_stream(
        self,
        user_input: str,
        session_id: str,
        user_id: Optional[str] = None,
        model_config: Optional[Dict[str, Any]] = None,
        external_history: Optional[List[Dict]] = None  # 新增：外部历史参数
    ):
        """流式处理用户消息,作为异步生成器产生事件。

        产生字典事件(结构见 AgentNodes.stream_llm_call)。
        流式传输完成后,将完整的助手响应持久化到对话历史。
        """
        # Build initial state similar to process_message but manual step execution
        initial_state = create_initial_state(
            session_id=session_id,
            user_input=user_input,
            user_id=user_id,
            model_config=model_config or {}
        )
        
        # 添加外部历史到 state
        if external_history is not None:
            initial_state["external_history"] = external_history
            self.logger.info(f"🔄 [Stream] Added {len(external_history)} messages to initial_state['external_history']")
        else:
            self.logger.warning(f"⚠️ [Stream] No external_history provided to process_message_stream")
        
        accumulated_content = []  # 收集 delta 片段用于最终持久化
        
        try:
            # 步骤 1: process_input
            state = await self.nodes.process_input(initial_state)
            if state.get('error_state'):
                yield {"type": "error", "error": state['error_state']}
                return
            
            # 步骤 2: 流式 LLM 并累积内容
            external_history_for_llm = state.get("external_history")
            messages = self.nodes._prepare_llm_messages(state, external_history=external_history_for_llm)
            model = state["model_config"].get("model", self.config.llm.models.default)
            llm_config = prepare_llm_params(
                model=model,
                messages=messages,
                temperature=state.get("temperature", self.config.llm.temperature),
                max_tokens=state.get("max_tokens", self.config.llm.max_tokens)
            )
            
            async for event in self.nodes.stream_llm_call(messages, llm_config, session_id=session_id):
                # 收集 delta 片段
                if event.get("type") == "delta" and "content" in event:
                    accumulated_content.append(event["content"])
                yield event
            
            # 步骤 3: 将完整响应持久化到对话历史
            if accumulated_content:
                full_response = "".join(accumulated_content)
                
                # 使用助手消息更新状态
                state["messages"].append({
                    "role": "assistant",
                    "content": full_response
                })
                
                # 持久化到 checkpointer (LangGraph MemorySaver)
                thread_config = {"configurable": {"thread_id": session_id}}
                
                # 使用最终状态调用图以进行持久化
                try:
                    # 使用 ainvoke 通过 checkpointer 持久化最终状态
                    final_state = {
                        **state,
                        "next_action": "format_response",  # 跳到结束
                        "should_continue": False
                    }
                    
                    # 这将保存更新的状态,包括新的助手消息
                    await self.graph.ainvoke(final_state, config=thread_config)
                    
                    self.logger.debug(f"已将流式响应持久化到会话 {session_id} 历史")
                
                except Exception as persist_error:
                    self.logger.warning(f"持久化流式历史失败: {persist_error}")
                    # 非致命:流式传输已成功完成
        
        except asyncio.CancelledError:
            self.logger.info(f"会话 {session_id} 的流被取消")
            # 仍尝试持久化部分内容(如果有)
            if accumulated_content:
                try:
                    partial_response = "".join(accumulated_content)
                    state["messages"].append({
                        "role": "assistant",
                        "content": f"[已取消] {partial_response}"
                    })
                    thread_config = {"configurable": {"thread_id": session_id}}
                    await self.graph.ainvoke(state, config=thread_config)
                except Exception:
                    pass
            raise
        
        except Exception as e:
            self.logger.error(f"流式消息处理出错: {e}")
            yield {"type": "error", "error": str(e)}
    # 清除历史消息
    async def clear_conversation(self, session_id: str) -> Dict[str, Any]:
        """
        清除会话的对话历史。
        
        Args:
            session_id: 会话标识符
            
        Returns:
            指示成功/失败的字典
        """
        try:
            # 为会话创建新的空状态
            thread_config = {"configurable": {"thread_id": session_id}}
            
            # 在实际实现中,我们会清除 checkpointer 状态
            # 现在,我们只创建一个新的空状态
            empty_state = create_initial_state(
                session_id=session_id,
                user_input="",
                model_config={}
            )
            
            self.logger.info(f"会话 {session_id} 的对话已清除")
            return {
                "success": True,
                "session_id": session_id,
                "message": "对话历史已清除"
            }
            
        except Exception as e:
            self.logger.error(f"清除对话时出错: {e}")
            return {
                "success": False,
                "session_id": session_id,
                "error": str(e)
            }
    
    def get_available_tools(self) -> List[str]:
        """获取可用工具列表。"""
        return self.config.tools.enabled
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取当前模型配置。"""
        return {
            "provider": self.config.llm.provider.value,
            "default_model": self.config.llm.models.default,
            "available_models": {
                "default": self.config.llm.models.default,
                "fast": self.config.llm.models.fast,
                "creative": self.config.llm.models.creative
            },
            "temperature": self.config.llm.temperature,
            "max_tokens": self.config.llm.max_tokens
        }

# 创建语音助手实例的工厂函数
def create_voice_agent(config_path: Optional[str] = None, environment: str = "development") -> VoiceAgent:
    """
    创建语音代理实例的工厂函数。
    
    Args:
        config_path: 配置目录的可选路径
        environment: 要加载的环境配置
        
    Returns:
        已配置的 VoiceAgent 实例
    """
    try:
        # Load configuration
        if config_path:
            config_manager = ConfigManager(config_path)
        else:
            from pathlib import Path
            default_config_path = Path(__file__).parent.parent.parent / "config"
            config_manager = ConfigManager(default_config_path)
        
        config = config_manager.load_config(environment)
        
        # 创建并返回代理
        agent = VoiceAgent(config)
        logger.info(f"语音代理使用 {environment} 配置创建成功")
        return agent
        
    except Exception as e:
        logger.error(f"创建语音代理时出错: {e}")
        raise