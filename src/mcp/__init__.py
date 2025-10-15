"""
MCP (Model Context Protocol) Tools Package

This package provides tool integration for the voice agent system.
Tools allow the LLM to interact with external services and APIs.
"""

from .registry import ToolRegistry, get_tool_registry
from .base import Tool, ToolParameter, ToolParameterType, ToolResult, ToolExecutionError
from .tools import (
    CalculatorTool,
    TimeTool,
    WeatherTool,
    SearchTool,
)

__all__ = [
    "ToolRegistry",
    "get_tool_registry",
    "Tool",
    "ToolParameter",
    "ToolParameterType",
    "ToolResult",
    "ToolExecutionError",
    "CalculatorTool",
    "TimeTool",
    "WeatherTool",
    "SearchTool",
]
