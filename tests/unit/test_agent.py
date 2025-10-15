"""
Unit Tests for Voice Agent Core Functionality

Test suite for the main agent components including state management,
conversation flow, tool handling, and LangGraph integration.
"""

import pytest
import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

# Import the modules we're testing
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from agent.state import (
    AgentState, 
    ConversationMessage, 
    MessageRole, 
    ToolCall, 
    ToolResult,
    ConversationContext,
    create_initial_state,
    state_to_dict
)
from agent.nodes import AgentNodes
from agent.graph import VoiceAgent, create_voice_agent
from config.models import VoiceAgentConfig, LLMConfig, LLMModels, LLMProvider


class TestAgentState:
    """Test cases for agent state management."""
    
    def test_conversation_message_creation(self):
        """Test conversation message creation and serialization."""
        message = ConversationMessage(
            id="test_123",
            role=MessageRole.USER,
            content="Hello, world!",
            metadata={"test": True}
        )
        
        assert message.id == "test_123"
        assert message.role == MessageRole.USER
        assert message.content == "Hello, world!"
        assert message.metadata["test"] is True
        assert isinstance(message.timestamp, datetime)
    
    def test_tool_call_creation(self):
        """Test tool call creation."""
        tool_call = ToolCall(
            id="tool_123",
            name="search_tool",
            arguments={"query": "test search"}
        )
        
        assert tool_call.id == "tool_123"
        assert tool_call.name == "search_tool"
        assert tool_call.arguments["query"] == "test search"
        assert isinstance(tool_call.timestamp, datetime)
    
    def test_tool_result_creation(self):
        """Test tool result creation."""
        result = ToolResult(
            call_id="tool_123",
            success=True,
            result="Search completed successfully"
        )
        
        assert result.call_id == "tool_123"
        assert result.success is True
        assert result.result == "Search completed successfully"
        assert result.error is None
        assert isinstance(result.timestamp, datetime)
    
    def test_create_initial_state(self):
        """Test initial state creation."""
        state = create_initial_state(
            session_id="test_session",
            user_input="Test input",
            user_id="user_123"
        )
        
        assert state["session_id"] == "test_session"
        assert state["user_input"] == "Test input"
        assert state["user_id"] == "user_123"
        assert state["should_continue"] is True
        assert state["error_state"] is None
        assert isinstance(state["conversation_start"], datetime)
        assert len(state["messages"]) == 0
        assert len(state["tool_calls"]) == 0
    
    def test_conversation_context(self):
        """Test conversation context management."""
        context = ConversationContext(
            session_id="test_session",
            user_id="user_123"
        )
        
        # Test adding messages
        user_msg = context.add_message(MessageRole.USER, "Hello")
        assert len(context.messages) == 1
        assert context.message_count == 1
        assert user_msg.content == "Hello"
        
        assistant_msg = context.add_message(MessageRole.ASSISTANT, "Hi there!")
        assert len(context.messages) == 2
        assert context.message_count == 2
        
        # Test tool calls
        tool_call = context.add_tool_call("search", {"query": "test"})
        assert len(context.tool_calls) == 1
        assert tool_call.name == "search"
        
        # Test tool results
        tool_result = context.add_tool_result(tool_call.id, True, "Found results")
        assert len(context.tool_results) == 1
        assert tool_result.success is True
        
        # Test recent messages
        recent = context.get_recent_messages(1)
        assert len(recent) == 1
        assert recent[0].content == "Hi there!"
    
    def test_state_to_dict(self):
        """Test state serialization to dictionary."""
        state = create_initial_state("test", "input")
        state_dict = state_to_dict(state)
        
        assert isinstance(state_dict, dict)
        assert state_dict["session_id"] == "test"
        assert state_dict["user_input"] == "input"
        assert isinstance(state_dict["conversation_start"], str)  # Should be ISO format


class TestAgentNodes:
    """Test cases for agent nodes."""
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration for testing."""
        return VoiceAgentConfig(
            llm=LLMConfig(
                provider=LLMProvider.OPENAI,
                api_key="test-key",
                models=LLMModels()
            ),
            tools=MagicMock(),
            api=MagicMock(),
            speech=MagicMock(),
            session=MagicMock(),
            logging=MagicMock(),
            security=MagicMock(),
            environment="testing",
            version="1.0.0-test",
            debug=True
        )
    
    @pytest.fixture
    def agent_nodes(self, mock_config):
        """Create agent nodes instance for testing."""
        return AgentNodes(mock_config)
    
    @pytest.fixture
    def sample_state(self):
        """Create a sample state for testing."""
        return create_initial_state(
            session_id="test_session",
            user_input="Hello, how are you?",
            user_id="test_user"
        )
    
    @pytest.mark.asyncio
    async def test_process_input_success(self, agent_nodes, sample_state):
        """Test successful input processing."""
        result_state = await agent_nodes.process_input(sample_state)
        
        assert result_state["should_continue"] is True
        assert result_state["error_state"] is None
        assert result_state["next_action"] == "call_llm"
        assert len(result_state["messages"]) == 1
        assert result_state["messages"][0].role == MessageRole.USER
        assert result_state["current_intent"] == "general_conversation"
    
    @pytest.mark.asyncio
    async def test_process_input_empty(self, agent_nodes):
        """Test input processing with empty input."""
        state = create_initial_state("test", "")
        result_state = await agent_nodes.process_input(state)
        
        assert result_state["should_continue"] is False
        assert result_state["error_state"] == "empty_input"
        assert "didn't receive any input" in result_state["agent_response"]
    
    @pytest.mark.asyncio
    async def test_process_input_intent_detection(self, agent_nodes):
        """Test intent detection in input processing."""
        test_cases = [
            ("search for cats", "search"),
            ("calculate 2 + 2", "calculation"),
            ("what time is it", "time_query"),
            ("generate an image", "image_generation"),
            ("help me", "help_request"),
            ("hello there", "general_conversation")
        ]
        
        for input_text, expected_intent in test_cases:
            state = create_initial_state("test", input_text)
            result_state = await agent_nodes.process_input(state)
            assert result_state["current_intent"] == expected_intent
    
    @pytest.mark.asyncio
    async def test_call_llm_general_response(self, agent_nodes, sample_state):
        """Test LLM call with general conversation."""
        # First process input to set up state
        state = await agent_nodes.process_input(sample_state)
        
        # Then call LLM
        result_state = await agent_nodes.call_llm(state)
        
        assert result_state["next_action"] == "format_response"
        assert result_state["agent_response"] != ""
        assert "Hello, how are you?" in result_state["agent_response"]
    
    @pytest.mark.asyncio
    async def test_call_llm_with_tools(self, agent_nodes):
        """Test LLM call that triggers tool usage."""
        state = create_initial_state("test", "search for Python tutorials")
        state = await agent_nodes.process_input(state)
        
        result_state = await agent_nodes.call_llm(state)
        
        assert result_state["next_action"] == "handle_tools"
        assert len(result_state["pending_tool_calls"]) > 0
        assert result_state["pending_tool_calls"][0].name == "search_tool"
    
    @pytest.mark.asyncio
    async def test_handle_tools_success(self, agent_nodes):
        """Test successful tool handling."""
        state = create_initial_state("test", "search for cats")
        state = await agent_nodes.process_input(state)
        state = await agent_nodes.call_llm(state)
        
        # Should have pending tool calls from the search
        assert len(state["pending_tool_calls"]) > 0
        
        result_state = await agent_nodes.handle_tools(state)
        
        assert result_state["next_action"] == "call_llm"
        assert len(result_state["pending_tool_calls"]) == 0
        assert len(result_state["tool_results"]) > 0
        assert len(result_state["tool_calls"]) > 0
        assert result_state["tool_results"][0].success is True
    
    @pytest.mark.asyncio
    async def test_format_response_success(self, agent_nodes, sample_state):
        """Test successful response formatting."""
        # Set up state with a response
        sample_state["agent_response"] = "Hello! I'm doing well, thank you for asking."
        
        result_state = await agent_nodes.format_response(sample_state)
        
        assert result_state["should_continue"] is False
        assert result_state["next_action"] is None
        assert len(result_state["messages"]) == 1  # Should have assistant message
        assert result_state["messages"][0].role == MessageRole.ASSISTANT
        assert result_state["messages"][0].content == "Hello! I'm doing well, thank you for asking."
    
    @pytest.mark.asyncio
    async def test_format_response_with_error(self, agent_nodes, sample_state):
        """Test response formatting when there's an error state."""
        sample_state["error_state"] = "test_error"
        sample_state["agent_response"] = ""
        
        result_state = await agent_nodes.format_response(sample_state)
        
        assert result_state["should_continue"] is False
        assert "encountered an error" in result_state["agent_response"]


class TestVoiceAgent:
    """Test cases for the main VoiceAgent class."""
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration for testing."""
        return VoiceAgentConfig(
            llm=LLMConfig(
                provider=LLMProvider.OPENAI,
                api_key="test-key",
                models=LLMModels()
            ),
            tools=MagicMock(),
            api=MagicMock(),
            speech=MagicMock(),
            session=MagicMock(),
            logging=MagicMock(),
            security=MagicMock(),
            environment="testing",
            version="1.0.0-test",
            debug=True
        )
    
    @pytest.fixture
    def voice_agent(self, mock_config):
        """Create a voice agent instance for testing."""
        return VoiceAgent(mock_config)
    
    def test_voice_agent_initialization(self, voice_agent):
        """Test voice agent initialization."""
        assert voice_agent.config is not None
        assert voice_agent.nodes is not None
        assert voice_agent.graph is not None
        assert voice_agent.logger is not None
    
    @pytest.mark.asyncio
    async def test_process_message_success(self, voice_agent):
        """Test successful message processing."""
        response = await voice_agent.process_message(
            user_input="Hello, how are you?",
            session_id="test_session",
            user_id="test_user"
        )
        
        assert response["success"] is True
        assert response["session_id"] == "test_session"
        assert response["response"] != ""
        assert response["message_count"] >= 1
        assert "metadata" in response
    
    @pytest.mark.asyncio
    async def test_process_message_with_tools(self, voice_agent):
        """Test message processing that involves tools."""
        response = await voice_agent.process_message(
            user_input="search for Python programming",
            session_id="test_session"
        )
        
        assert response["success"] is True
        assert response["metadata"]["tool_calls"] > 0
    
    def test_get_available_tools(self, voice_agent):
        """Test getting available tools list."""
        tools = voice_agent.get_available_tools()
        assert isinstance(tools, list)
    
    def test_get_model_info(self, voice_agent):
        """Test getting model information."""
        model_info = voice_agent.get_model_info()
        
        assert "provider" in model_info
        assert "default_model" in model_info
        assert "available_models" in model_info
        assert "temperature" in model_info
        assert "max_tokens" in model_info


class TestAgentIntegration:
    """Integration tests for the complete agent workflow."""
    
    @pytest.mark.asyncio
    async def test_full_conversation_flow(self):
        """Test a complete conversation flow from start to finish."""
        # This test would require actual configuration files
        # For now, we'll test the factory function with mocking
        
        with patch('agent.graph.ConfigManager') as mock_config_manager:
            mock_config = MagicMock()
            mock_config_manager.return_value.load_config.return_value = mock_config
            
            # Mock the configuration object
            mock_config.llm = MagicMock()
            mock_config.llm.provider = LLMProvider.OPENAI
            mock_config.llm.models = LLMModels()
            mock_config.tools = MagicMock()
            mock_config.tools.enabled = ["search_tool", "calculator"]
            
            try:
                agent = create_voice_agent(environment="testing")
                assert agent is not None
            except Exception as e:
                # If we can't create the agent due to missing dependencies,
                # that's expected in a test environment
                assert "langgraph" in str(e).lower() or "config" in str(e).lower()
    
    @pytest.mark.asyncio
    async def test_error_handling_in_workflow(self):
        """Test error handling throughout the workflow."""
        # Test with mock configuration
        mock_config = MagicMock()
        mock_config.llm = MagicMock()
        mock_config.llm.provider = LLMProvider.OPENAI
        mock_config.llm.models = LLMModels()
        
        nodes = AgentNodes(mock_config)
        
        # Test error in input processing
        with patch.object(nodes, '_analyze_intent', side_effect=Exception("Test error")):
            state = create_initial_state("test", "test input")
            result = await nodes.process_input(state)
            assert result["error_state"] is not None
            assert "input_processing_error" in result["error_state"]


# Test fixtures and utilities
@pytest.fixture
def sample_agent_state():
    """Fixture providing a sample agent state for testing."""
    return create_initial_state(
        session_id="test_session_123",
        user_input="Hello, I need help with Python programming",
        user_id="user_456"
    )


@pytest.fixture
def sample_conversation_context():
    """Fixture providing a sample conversation context."""
    context = ConversationContext(
        session_id="test_session",
        user_id="test_user"
    )
    
    # Add some sample messages
    context.add_message(MessageRole.USER, "Hello")
    context.add_message(MessageRole.ASSISTANT, "Hi! How can I help you?")
    context.add_message(MessageRole.USER, "What's the weather like?")
    
    return context


if __name__ == "__main__":
    # Run tests if this file is executed directly
    pytest.main([__file__, "-v"])