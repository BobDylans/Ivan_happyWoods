"""
MCP Tool Registry

Central registry for managing and discovering available tools.
"""

import logging
from typing import Dict, List, Optional, Type
from .base import Tool, ToolExecutionError

logger = logging.getLogger(__name__)


class ToolRegistry:
    """
    Registry for managing MCP tools.
    
    Provides tool registration, discovery, and execution management.
    Singleton pattern ensures single global registry instance.
    """
    
    _instance: Optional["ToolRegistry"] = None
    
    def __init__(self):
        """Initialize the tool registry."""
        self._tools: Dict[str, Tool] = {}
        logger.info("Tool registry initialized")
    
    @classmethod
    def get_instance(cls) -> "ToolRegistry":
        """Get singleton registry instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def register(self, tool: Tool) -> None:
        """
        Register a tool with the registry.
        
        Args:
            tool: Tool instance to register
        
        Raises:
            ValueError: If tool with same name already registered
        """
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' is already registered")
        
        self._tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name}")
    
    def register_class(self, tool_class: Type[Tool]) -> None:
        """
        Instantiate and register a tool class.
        
        Args:
            tool_class: Tool class to instantiate and register
        """
        tool = tool_class()
        self.register(tool)
    
    def unregister(self, tool_name: str) -> None:
        """
        Unregister a tool from the registry.
        
        Args:
            tool_name: Name of tool to unregister
        """
        if tool_name in self._tools:
            del self._tools[tool_name]
            logger.info(f"Unregistered tool: {tool_name}")
    
    def get(self, tool_name: str) -> Optional[Tool]:
        """
        Get a tool by name.
        
        Args:
            tool_name: Name of tool to retrieve
        
        Returns:
            Tool instance or None if not found
        """
        return self._tools.get(tool_name)
    
    def list_tools(self) -> List[Tool]:
        """
        Get list of all registered tools.
        
        Returns:
            List of registered tool instances
        """
        return list(self._tools.values())
    
    def list_tool_names(self) -> List[str]:
        """
        Get list of registered tool names.
        
        Returns:
            List of tool names
        """
        return list(self._tools.keys())
    
    def get_schemas(self) -> List[Dict]:
        """
        Get OpenAI function calling schemas for all tools.
        
        Returns:
            List of tool schemas in OpenAI format
        """
        return [tool.to_openai_schema() for tool in self._tools.values()]
    
    async def execute(self, tool_name: str, **kwargs) -> Dict:
        """
        Execute a tool by name.
        
        Args:
            tool_name: Name of tool to execute
            **kwargs: Tool parameters
        
        Returns:
            Tool execution result as dict
        
        Raises:
            ToolExecutionError: If tool not found or execution fails
        """
        tool = self.get(tool_name)
        if tool is None:
            raise ToolExecutionError(
                message=f"Tool '{tool_name}' not found",
                tool_name=tool_name,
                details={"available_tools": self.list_tool_names()}
            )
        
        try:
            logger.debug(f"Executing tool: {tool_name} with params: {kwargs}")
            result = await tool.execute(**kwargs)
            return result.model_dump()
        except Exception as e:
            logger.error(f"Tool execution failed: {tool_name}", exc_info=True)
            if isinstance(e, ToolExecutionError):
                raise
            raise ToolExecutionError(
                message=str(e),
                tool_name=tool_name,
                details={"params": kwargs}
            )
    
    def clear(self) -> None:
        """Clear all registered tools."""
        self._tools.clear()
        logger.info("Tool registry cleared")
    
    def __len__(self) -> int:
        """Get number of registered tools."""
        return len(self._tools)
    
    def __contains__(self, tool_name: str) -> bool:
        """Check if tool is registered."""
        return tool_name in self._tools
    
    def __repr__(self) -> str:
        return f"<ToolRegistry: {len(self)} tools registered>"


# Global registry instance accessor
def get_tool_registry() -> ToolRegistry:
    """
    Get the global tool registry instance.
    
    Returns:
        Singleton ToolRegistry instance
    """
    return ToolRegistry.get_instance()
