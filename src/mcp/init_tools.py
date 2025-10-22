"""
MCP Tool Initialization

Initialize and register default tools for the agent system.
"""

import logging
from typing import List, Optional, Dict, Any

from .registry import get_tool_registry
from .tools import (
    CalculatorTool,
    TimeTool,
    WeatherTool,
    SearchTool,
)
from .voice_tools import create_voice_tools

logger = logging.getLogger(__name__)


def initialize_default_tools(config: Optional[Dict[str, Any]] = None) -> List[str]:
    """
    Initialize and register all default MCP tools.
    
    Args:
        config: Configuration dictionary (optional)
    
    Returns:
        List of registered tool names
    """
    registry = get_tool_registry()
    
    # Get search tool config
    search_tool_config = {}
    if config and "tools" in config and "search_tool" in config["tools"]:
        search_tool_config = config["tools"]["search_tool"]
        logger.info(f"🔧 Configuring SearchTool with Tavily API")
    
    tools_to_register = [
        CalculatorTool(),
        TimeTool(),
        WeatherTool(),
        SearchTool(config=search_tool_config),  # Pass config to SearchTool
    ] + create_voice_tools()
    
    registered_names = []
    
    for tool in tools_to_register:
        try:
            registry.register(tool)
            registered_names.append(tool.name)
            logger.info(f"Registered MCP tool: {tool.name}")
        except ValueError as e:
            # Tool already registered
            logger.debug(f"Tool {tool.name} already registered: {e}")
            registered_names.append(tool.name)
        except Exception as e:
            logger.error(f"Failed to register tool {tool.name}: {e}")
    
    logger.info(f"Initialized {len(registered_names)} MCP tools")
    return registered_names


def get_available_tool_schemas():
    """
    Get OpenAI-compatible schemas for all registered tools.
    
    Returns:
        List of tool schemas in OpenAI function calling format
    """
    registry = get_tool_registry()
    return registry.get_schemas()


def list_available_tools() -> List[str]:
    """
    Get list of all available tool names.
    
    Returns:
        List of tool names
    """
    registry = get_tool_registry()
    return registry.list_tool_names()
