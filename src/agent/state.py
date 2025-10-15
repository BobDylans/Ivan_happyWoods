"""
Agent State Management

Defines the state structures for managing conversation history, context,
and data flow through the LangGraph-based conversation agent.
"""

from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
from typing_extensions import TypedDict


class MessageRole(str, Enum):
    """Message roles in conversation."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class ConversationMessage(BaseModel):
    """A single message in the conversation."""
    id: str = Field(..., description="Unique message identifier")
    role: MessageRole = Field(..., description="Message role")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(default_factory=datetime.now, description="Message timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ToolCall(BaseModel):
    """Represents a tool call made by the agent."""
    id: str = Field(..., description="Unique tool call identifier")
    name: str = Field(..., description="Tool name")
    arguments: Dict[str, Any] = Field(..., description="Tool arguments")
    timestamp: datetime = Field(default_factory=datetime.now, description="Call timestamp")


class ToolResult(BaseModel):
    """Represents the result of a tool call."""
    call_id: str = Field(..., description="Corresponding tool call ID")
    success: bool = Field(..., description="Whether the tool call succeeded")
    result: Any = Field(..., description="Tool execution result")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    timestamp: datetime = Field(default_factory=datetime.now, description="Result timestamp")


class AgentState(TypedDict):
    """
    State structure for the conversation agent.
    
    This state is passed through all nodes in the LangGraph workflow,
    maintaining conversation history, context, and execution results.
    """
    # Core conversation data
    messages: List[ConversationMessage]
    user_input: str
    agent_response: str
    
    # Session information
    session_id: str
    user_id: Optional[str]
    conversation_start: datetime
    last_activity: datetime
    
    # Tool interaction
    tool_calls: List[ToolCall]
    tool_results: List[ToolResult]
    pending_tool_calls: List[ToolCall]
    
    # Processing context
    current_intent: Optional[str]
    context_variables: Dict[str, Any]
    
    # Flow control
    next_action: Optional[str]
    should_continue: bool
    error_state: Optional[str]
    
    # Configuration
    model_config: Dict[str, Any]
    temperature: float
    max_tokens: int


class ConversationContext(BaseModel):
    """Extended context for conversation management."""
    
    # Session metadata
    session_id: str = Field(..., description="Unique session identifier")
    user_id: Optional[str] = Field(default=None, description="User identifier")
    created_at: datetime = Field(default_factory=datetime.now, description="Session creation time")
    updated_at: datetime = Field(default_factory=datetime.now, description="Last update time")
    
    # Conversation history
    messages: List[ConversationMessage] = Field(default_factory=list, description="Message history")
    message_count: int = Field(default=0, description="Total message count")
    
    # State tracking
    current_intent: Optional[str] = Field(default=None, description="Current conversation intent")
    context_variables: Dict[str, Any] = Field(default_factory=dict, description="Context variables")
    
    # Tool tracking
    tool_calls: List[ToolCall] = Field(default_factory=list, description="Tool call history")
    tool_results: List[ToolResult] = Field(default_factory=list, description="Tool result history")
    
    # Configuration
    active_tools: List[str] = Field(default_factory=list, description="Currently available tools")
    preferences: Dict[str, Any] = Field(default_factory=dict, description="User preferences")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    def add_message(self, role: MessageRole, content: str, metadata: Optional[Dict[str, Any]] = None) -> ConversationMessage:
        """Add a new message to the conversation."""
        message = ConversationMessage(
            id=f"msg_{len(self.messages) + 1}_{int(datetime.now().timestamp())}",
            role=role,
            content=content,
            metadata=metadata or {}
        )
        self.messages.append(message)
        self.message_count += 1
        self.updated_at = datetime.now()
        return message
    
    def add_tool_call(self, name: str, arguments: Dict[str, Any]) -> ToolCall:
        """Record a tool call."""
        tool_call = ToolCall(
            id=f"tool_{len(self.tool_calls) + 1}_{int(datetime.now().timestamp())}",
            name=name,
            arguments=arguments
        )
        self.tool_calls.append(tool_call)
        self.updated_at = datetime.now()
        return tool_call
    
    def add_tool_result(self, call_id: str, success: bool, result: Any, error: Optional[str] = None) -> ToolResult:
        """Record a tool result."""
        tool_result = ToolResult(
            call_id=call_id,
            success=success,
            result=result,
            error=error
        )
        self.tool_results.append(tool_result)
        self.updated_at = datetime.now()
        return tool_result
    
    def get_recent_messages(self, count: int = 10) -> List[ConversationMessage]:
        """Get the most recent messages."""
        return self.messages[-count:] if self.messages else []
    
    def clear_history(self, keep_count: int = 0) -> None:
        """Clear conversation history, optionally keeping recent messages."""
        if keep_count > 0:
            self.messages = self.messages[-keep_count:]
        else:
            self.messages = []
        self.message_count = len(self.messages)
        self.updated_at = datetime.now()


def create_initial_state(
    session_id: str,
    user_input: str,
    user_id: Optional[str] = None,
    model_config: Optional[Dict[str, Any]] = None
) -> AgentState:
    """Create an initial agent state for a new conversation turn."""
    now = datetime.now()
    
    return AgentState(
        # Core conversation data
        messages=[],
        user_input=user_input,
        agent_response="",
        
        # Session information
        session_id=session_id,
        user_id=user_id,
        conversation_start=now,
        last_activity=now,
        
        # Tool interaction
        tool_calls=[],
        tool_results=[],
        pending_tool_calls=[],
        
        # Processing context
        current_intent=None,
        context_variables={},
        
        # Flow control
        next_action=None,
        should_continue=True,
        error_state=None,
        
        # Configuration
        model_config=model_config or {},
        temperature=0.7,
        max_tokens=1500
    )


def state_to_dict(state: AgentState) -> Dict[str, Any]:
    """Convert AgentState to a serializable dictionary."""
    return {
        "messages": [msg.dict() if hasattr(msg, 'dict') else msg for msg in state["messages"]],
        "user_input": state["user_input"],
        "agent_response": state["agent_response"],
        "session_id": state["session_id"],
        "user_id": state["user_id"],
        "conversation_start": state["conversation_start"].isoformat() if isinstance(state["conversation_start"], datetime) else state["conversation_start"],
        "last_activity": state["last_activity"].isoformat() if isinstance(state["last_activity"], datetime) else state["last_activity"],
        "tool_calls": [call.dict() if hasattr(call, 'dict') else call for call in state["tool_calls"]],
        "tool_results": [result.dict() if hasattr(result, 'dict') else result for result in state["tool_results"]],
        "pending_tool_calls": [call.dict() if hasattr(call, 'dict') else call for call in state["pending_tool_calls"]],
        "current_intent": state["current_intent"],
        "context_variables": state["context_variables"],
        "next_action": state["next_action"],
        "should_continue": state["should_continue"],
        "error_state": state["error_state"],
        "model_config": state["model_config"],
        "temperature": state["temperature"],
        "max_tokens": state["max_tokens"]
    }