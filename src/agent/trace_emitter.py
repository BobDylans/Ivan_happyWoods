"""
执行流程追踪事件发射器

提供统一的事件发射接口，支持 Graph 层（调度级）和 Node 层（执行级）事件。
前端可通过这些事件实时展示 AI 的思考和执行过程。
"""

import time
from typing import Any, Dict, Optional


class TraceEmitter:
    """
    执行流程追踪事件发射器
    
    职责：
    - Graph 层：发射节点生命周期、路由决策、工作流状态事件
    - Node 层：发射思考阶段、工具调用、LLM 生成等执行细节事件
    
    事件格式：
    {
        "level": "graph" | "node",
        "type": "事件类型",
        "timestamp": 相对毫秒数,
        "session_id": "会话ID",
        "data": { ... }  # 事件特定数据
    }
    """
    
    def __init__(self):
        """初始化事件发射器，记录起始时间"""
        self.start_time = time.time()
    
    def _now(self) -> float:
        """获取相对时间戳（毫秒）"""
        return (time.time() - self.start_time) * 1000
    
    def _emit(self, level: str, event_type: str, session_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        统一事件发射方法
        
        Args:
            level: 事件层级 ("graph" 或 "node")
            event_type: 事件类型
            session_id: 会话ID
            data: 事件特定数据
            
        Returns:
            格式化的事件字典
        """
        return {
            "level": level,
            "type": event_type,
            "timestamp": self._now(),
            "session_id": session_id,
            "data": data
        }
    
    # ============================================================
    # Graph 层事件（调度级别）
    # ============================================================
    
    def workflow_started(self, session_id: str, user_input: str) -> Dict[str, Any]:
        """
        工作流开始事件
        
        前端展示：显示整体进度条开始
        """
        return self._emit("graph", "workflow_started", session_id, {
            "user_input": user_input[:100] + "..." if len(user_input) > 100 else user_input
        })
    
    def node_started(self, node_name: str, session_id: str) -> Dict[str, Any]:
        """
        节点开始执行事件
        
        前端展示：节点状态指示器变为"进行中"（蓝色/加载动画）
        """
        # 节点显示名称映射（更友好）
        node_display_names = {
            "process_input": "处理输入",
            "call_llm": "调用大模型",
            "handle_tools": "执行工具",
            "format_response": "格式化响应"
        }
        
        return self._emit("graph", "node_started", session_id, {
            "node": node_name,
            "display_name": node_display_names.get(node_name, node_name)
        })
    
    def node_finished(self, node_name: str, session_id: str, duration_ms: float) -> Dict[str, Any]:
        """
        节点完成事件
        
        前端展示：节点状态指示器变为"已完成"（绿色/✓），显示耗时
        """
        node_display_names = {
            "process_input": "处理输入",
            "call_llm": "调用大模型",
            "handle_tools": "执行工具",
            "format_response": "格式化响应"
        }
        
        return self._emit("graph", "node_finished", session_id, {
            "node": node_name,
            "display_name": node_display_names.get(node_name, node_name),
            "duration_ms": round(duration_ms, 2)
        })
    
    def route_decision(self, from_node: str, to_node: str, reason: str, session_id: str) -> Dict[str, Any]:
        """
        路由决策事件
        
        前端展示：时间线上显示箭头和决策原因
        """
        return self._emit("graph", "route_decision", session_id, {
            "from": from_node,
            "to": to_node,
            "reason": reason
        })
    
    def workflow_complete(self, session_id: str, total_duration_ms: float) -> Dict[str, Any]:
        """
        工作流完成事件
        
        前端展示：整体进度条完成，显示总耗时
        """
        return self._emit("graph", "workflow_complete", session_id, {
            "total_duration_ms": round(total_duration_ms, 2)
        })
    
    # ============================================================
    # Node 层事件（执行级别）
    # ============================================================
    
    def thinking_phase(self, phase: str, node_name: str, session_id: str, details: Optional[str] = None) -> Dict[str, Any]:
        """
        思考阶段事件
        
        前端展示：在节点卡片内显示当前子阶段（如"准备调用"、"构建消息"）
        
        Args:
            phase: 阶段名称（如"验证输入"、"准备LLM调用"）
            node_name: 所属节点名称
            session_id: 会话ID
            details: 可选的详细信息
        """
        return self._emit("node", "thinking_phase", session_id, {
            "phase": phase,
            "node": node_name,
            "details": details
        })
    
    def tool_call_pending(self, tool_name: str, args: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """
        工具调用排队事件
        
        前端展示：显示工具卡片（灰色/待执行状态），显示参数
        """
        # 参数简化（避免过长）
        simplified_args = {}
        for key, value in args.items():
            if isinstance(value, str) and len(value) > 100:
                simplified_args[key] = value[:100] + "..."
            else:
                simplified_args[key] = value
        
        return self._emit("node", "tool_call_pending", session_id, {
            "tool": tool_name,
            "args": simplified_args
        })
    
    def tool_executing(self, tool_name: str, session_id: str) -> Dict[str, Any]:
        """
        工具执行中事件
        
        前端展示：工具卡片变为"执行中"（蓝色/加载动画）
        """
        return self._emit("node", "tool_executing", session_id, {
            "tool": tool_name
        })
    
    def tool_result(self, tool_name: str, success: bool, result_summary: str, session_id: str, duration_ms: Optional[float] = None) -> Dict[str, Any]:
        """
        工具执行结果事件
        
        前端展示：工具卡片变为"完成/失败"（绿色✓/红色✗），显示结果摘要
        
        Args:
            tool_name: 工具名称
            success: 是否成功
            result_summary: 结果摘要（简短描述）
            session_id: 会话ID
            duration_ms: 执行耗时（可选）
        """
        return self._emit("node", "tool_result", session_id, {
            "tool": tool_name,
            "success": success,
            "summary": result_summary[:200] if len(result_summary) > 200 else result_summary,
            "duration_ms": round(duration_ms, 2) if duration_ms else None
        })
    
    def llm_streaming(self, phase: str, session_id: str, details: Optional[str] = None) -> Dict[str, Any]:
        """
        LLM 生成流式阶段事件（与现有 delta 事件配合）
        
        前端展示：在 LLM 生成区域显示阶段提示（如"模型思考中..."）
        
        Args:
            phase: 流式阶段（如"开始生成"、"检测工具调用"、"递归调用中"）
            session_id: 会话ID
            details: 可选的详细信息
        """
        return self._emit("node", "llm_streaming", session_id, {
            "phase": phase,
            "details": details
        })
    
    def token_usage(self, prompt_tokens: int, completion_tokens: int, session_id: str) -> Dict[str, Any]:
        """
        Token 使用统计事件（可选）
        
        前端展示：在统计面板显示 Token 消耗
        """
        return self._emit("node", "token_usage", session_id, {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens
        })
