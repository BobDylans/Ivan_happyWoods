"""
MCP Tool Base Classes

Defines the base classes and types for MCP tool implementations.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field
from enum import Enum


class ToolParameterType(str, Enum):
    """Parameter types for tool inputs."""
    STRING = "string"
    NUMBER = "number"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    OBJECT = "object"
    ARRAY = "array"


class ToolParameter(BaseModel):
    """
    Tool parameter definition.
    
    Describes an input parameter for a tool following OpenAI function calling schema.
    """
    name: str = Field(..., description="Parameter name")
    type: ToolParameterType = Field(..., description="Parameter type")
    description: str = Field(..., description="Parameter description")
    required: bool = Field(default=False, description="Whether parameter is required")
    enum: Optional[List[str]] = Field(default=None, description="Allowed values")
    default: Optional[Any] = Field(default=None, description="Default value")
    
    class Config:
        use_enum_values = True


class ToolResult(BaseModel):
    """
    Result from tool execution.
    
    Contains the output data, success status, and optional error information.
    """
    success: bool = Field(..., description="Whether execution succeeded")
    data: Optional[Any] = Field(default=None, description="Result data")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": {"result": "42"},
                "error": None,
                "metadata": {"execution_time_ms": 123}
            }
        }


class ToolExecutionError(Exception):
    """Exception raised during tool execution."""
    
    def __init__(self, message: str, tool_name: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.tool_name = tool_name
        self.details = details or {}
        super().__init__(f"{tool_name}: {message}")


class Tool(ABC):
    """
    Abstract base class for MCP tools.
    
    All tools must inherit from this class and implement the required methods.
    Tools follow the OpenAI function calling specification for parameter schemas.
    """
    
    def __init__(self):
        """Initialize the tool."""
        self._validate_schema()
    
    @property
    @abstractmethod
    def name(self) -> str:
        """
        Unique tool name.
        
        Should be lowercase with underscores (snake_case).
        Example: "web_search", "calculator", "image_generator"
        """
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """
        Human-readable description of what the tool does.
        
        This is shown to the LLM to help it decide when to use the tool.
        Should be clear and concise (1-2 sentences).
        """
        pass
    
    @property
    @abstractmethod
    def parameters(self) -> List[ToolParameter]:
        """
        List of parameters the tool accepts.
        
        Each parameter defines its name, type, description, and whether it's required.
        """
        pass
    
    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """
        Execute the tool with provided parameters.
        
        Args:
            **kwargs: Tool parameters as keyword arguments
        
        Returns:
            ToolResult: Result of the tool execution
        
        Raises:
            ToolExecutionError: If execution fails
        """
        pass
    
    def to_openai_schema(self) -> Dict[str, Any]:
        """
        Convert tool definition to OpenAI function calling schema.
        
        Returns:
            Dict containing the tool schema in OpenAI format
        """
        properties = {}
        required = []
        
        for param in self.parameters:
            properties[param.name] = {
                "type": param.type,
                "description": param.description,
            }
            if param.enum:
                properties[param.name]["enum"] = param.enum
            if param.default is not None:
                properties[param.name]["default"] = param.default
            
            if param.required:
                required.append(param.name)
        
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        }
    
    def _validate_schema(self):
        """Validate tool schema is correctly defined."""
        if not self.name:
            raise ValueError(f"{self.__class__.__name__}: Tool name cannot be empty")
        
        if not self.description:
            raise ValueError(f"{self.name}: Tool description cannot be empty")
        
        # Validate parameter names are unique
        param_names = [p.name for p in self.parameters]
        if len(param_names) != len(set(param_names)):
            raise ValueError(f"{self.name}: Duplicate parameter names found")
    
    def __repr__(self) -> str:
        return f"<Tool: {self.name}>"
