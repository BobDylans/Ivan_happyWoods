"""
MCP Tool Initialization

Initialize and register default tools for the agent system.
"""

import logging
from typing import List, Optional, Dict, Any

from .registry import ToolRegistry
from .tools import (
    CalculatorTool,
    TimeTool,
    WeatherTool,
    SearchTool,
)
from .voice_tools import create_voice_tools

logger = logging.getLogger(__name__)


def initialize_default_tools(
    registry: ToolRegistry = None,
    config: Optional[Dict[str, Any]] = None
) -> List[str]:
    """
    Initialize and register all default MCP tools.
    
    Args:
        registry: ToolRegistry instance (required, no longer uses global state)
        config: Configuration dictionary (optional)
    
    Returns:
        List of registered tool names
    """
    import os
    
    if registry is None:
        raise ValueError("ToolRegistry must be provided. Global registry is deprecated.")
    
    # Get search tool config from multiple sources
    search_tool_config = {}
    
    # 1. Try to get from nested config structure
    if config and "tools" in config and "search_tool" in config["tools"]:
        search_tool_config = config["tools"]["search_tool"]
        logger.info(f"🔧 Configuring SearchTool from config.tools.search_tool")
    
    # 2. Try direct environment variable (TAVILY_API_KEY)
    tavily_key = os.getenv("TAVILY_API_KEY")
    if tavily_key:
        search_tool_config["api_key"] = tavily_key
        logger.info(f"🔧 Configuring SearchTool with TAVILY_API_KEY from environment")
    
    # 3. Try VOICE_AGENT_TOOLS__SEARCH_TOOL__API_KEY
    if not search_tool_config.get("api_key"):
        nested_key = os.getenv("VOICE_AGENT_TOOLS__SEARCH_TOOL__API_KEY")
        if nested_key:
            search_tool_config["api_key"] = nested_key
            logger.info(f"🔧 Configuring SearchTool with VOICE_AGENT_TOOLS__SEARCH_TOOL__API_KEY")
    
    # 4. Set default timeout and search depth if not configured
    search_tool_config.setdefault("timeout", int(os.getenv("VOICE_AGENT_TOOLS__SEARCH_TOOL__TIMEOUT", "15")))
    search_tool_config.setdefault("search_depth", os.getenv("VOICE_AGENT_TOOLS__SEARCH_TOOL__DEPTH", "basic"))
    
    if search_tool_config.get("api_key"):
        logger.info(f"✅ SearchTool configured with API key: {search_tool_config['api_key'][:10]}...")
    else:
        logger.warning(f"⚠️ No Tavily API key found, SearchTool will use mock results")
    
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


def get_available_tool_schemas(registry: ToolRegistry):
    """
    Get OpenAI-compatible schemas for all registered tools.
    
    Args:
        registry: ToolRegistry instance
    
    Returns:
        List of tool schemas in OpenAI function calling format
    """
    return registry.get_schemas()


def list_available_tools(registry: ToolRegistry) -> List[str]:
    """
    Get list of all available tool names.
    
    Args:
        registry: ToolRegistry instance
    
    Returns:
        List of tool names
    """
    return registry.list_tool_names()
