"""
MCP Tool Implementations

Concrete tool implementations for various functionalities.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict
import httpx

from .base import Tool, ToolParameter, ToolParameterType, ToolResult, ToolExecutionError

logger = logging.getLogger(__name__)

# 这里是说明这个计算器 MCP是也是集成了Tool这个接口
class CalculatorTool(Tool):
    """
    Calculator tool for mathematical expressions.
    
    Evaluates mathematical expressions safely.
    """
    
    # 在这里定义好当前MCP的名字，描述和执行方法（excute），其默认返回的类型是固定的
    @property
    def name(self) -> str:
        return "calculator"
    
    @property
    def description(self) -> str:
        return "Evaluate mathematical expressions. Supports basic arithmetic (+, -, *, /), exponents (**), and parentheses."
    
    @property
    def parameters(self):
        return [
            ToolParameter(
                name="expression",
                type=ToolParameterType.STRING,
                description="Mathematical expression to evaluate (e.g., '2 + 2', '(10 * 5) / 2')",
                required=True
            )
        ]
    
    async def execute(self, expression: str, **kwargs) -> ToolResult:
        """Execute calculator operation."""
        try:
            # Safe evaluation using limited builtins
            allowed_names = {
                'abs': abs,
                'round': round,
                'min': min,
                'max': max,
                'sum': sum,
                'pow': pow,
            }
            
            # Remove any potentially dangerous characters
            if any(char in expression for char in ['_', 'import', 'exec', 'eval', 'open', 'file']):
                raise ValueError("Expression contains forbidden characters or keywords")
            
            # Evaluate expression
            result = eval(expression, {"__builtins__": {}}, allowed_names)
            
            return ToolResult(
                success=True,
                data={"result": result, "expression": expression},
                metadata={"type": type(result).__name__}
            )
        
        except Exception as e:
            logger.error(f"Calculator error: {e}")
            return ToolResult(
                success=False,
                error=f"Failed to evaluate expression: {str(e)}",
                metadata={"expression": expression}
            )

# 同样是继承自Tool类，实现方法基本一致
class TimeTool(Tool):
    """
    Time/date information tool.
    
    Provides current time, date, and timezone information.
    """
    
    @property
    def name(self) -> str:
        return "get_time"
    
    @property
    def description(self) -> str:
        return "Get current date and time information. Optionally format the output."
    
    @property
    def parameters(self):
        return [
            ToolParameter(
                name="format",
                type=ToolParameterType.STRING,
                description="Output format: 'full' (date + time), 'date' (date only), 'time' (time only), 'timestamp' (unix timestamp)",
                required=False,
                enum=["full", "date", "time", "timestamp"],
                default="full"
            )
        ]
    
    async def execute(self, format: str = "full", **kwargs) -> ToolResult:
        """Get current time information."""
        try:
            now = datetime.now()
            
            if format == "date":
                result = now.strftime("%Y-%m-%d")
            elif format == "time":
                result = now.strftime("%H:%M:%S")
            elif format == "timestamp":
                result = int(now.timestamp())
            else:  # full
                result = now.strftime("%Y-%m-%d %H:%M:%S")
            
            return ToolResult(
                success=True,
                data={
                    "formatted": result,
                    "iso": now.isoformat(),
                    "format_used": format
                },
                metadata={
                    "timezone": "local",
                    "day_of_week": now.strftime("%A")
                }
            )
        
        except Exception as e:
            logger.error(f"Time tool error: {e}")
            return ToolResult(
                success=False,
                error=f"Failed to get time: {str(e)}"
            )


class WeatherTool(Tool):
    """
    Weather information tool (mock implementation).
    
    In production, this would connect to a real weather API.
    Currently returns mock data for demonstration.
    """
    
    @property
    def name(self) -> str:
        return "get_weather"
    
    @property
    def description(self) -> str:
        return "Get current weather information for a location. Returns temperature, conditions, and forecast."
    
    @property
    def parameters(self):
        return [
            ToolParameter(
                name="location",
                type=ToolParameterType.STRING,
                description="City name or location (e.g., 'New York', 'London, UK')",
                required=True
            ),
            ToolParameter(
                name="units",
                type=ToolParameterType.STRING,
                description="Temperature units: 'celsius' or 'fahrenheit'",
                required=False,
                enum=["celsius", "fahrenheit"],
                default="celsius"
            )
        ]
    
    async def execute(self, location: str, units: str = "celsius", **kwargs) -> ToolResult:
        """Get weather information."""
        try:
            # Mock weather data (in production, call real API)
            # Example: OpenWeatherMap, Weather API, etc.
            
            # Simulate API call delay
            await asyncio.sleep(0.1)
            
            # Mock response based on location
            temp_c = 22  # Default temperature
            if "london" in location.lower():
                temp_c = 15
            elif "tokyo" in location.lower():
                temp_c = 25
            elif "sydney" in location.lower():
                temp_c = 28
            
            temp = temp_c if units == "celsius" else (temp_c * 9/5) + 32
            
            return ToolResult(
                success=True,
                data={
                    "location": location,
                    "temperature": round(temp, 1),
                    "units": units,
                    "conditions": "Partly Cloudy",
                    "humidity": 65,
                    "wind_speed": 12,
                    "description": f"Mock weather data for {location}"
                },
                metadata={
                    "source": "mock",
                    "note": "This is simulated data. Connect to real weather API for production."
                }
            )
        
        except Exception as e:
            logger.error(f"Weather tool error: {e}")
            return ToolResult(
                success=False,
                error=f"Failed to get weather: {str(e)}",
                metadata={"location": location}
            )


class SearchTool(Tool):
    """
    Web search tool (mock implementation).
    
    In production, this would connect to a search API (Google, Bing, DuckDuckGo).
    Currently returns mock search results.
    """
    
    @property
    def name(self) -> str:
        return "web_search"
    
    @property
    def description(self) -> str:
        return "Search the web for information. Returns relevant search results with titles and snippets."
    
    @property
    def parameters(self):
        return [
            ToolParameter(
                name="query",
                type=ToolParameterType.STRING,
                description="Search query (e.g., 'latest AI news', 'Python tutorial')",
                required=True
            ),
            ToolParameter(
                name="num_results",
                type=ToolParameterType.INTEGER,
                description="Number of results to return (1-10)",
                required=False,
                default=5
            )
        ]
    
    async def execute(self, query: str, num_results: int = 5, **kwargs) -> ToolResult:
        """Perform web search."""
        try:
            # Limit results
            num_results = max(1, min(num_results, 10))
            
            # Simulate API call delay
            await asyncio.sleep(0.2)
            
            # Mock search results
            mock_results = [
                {
                    "title": f"Result {i+1} for '{query}'",
                    "snippet": f"This is a mock search result snippet for query: {query}. "
                               f"In production, this would return real search results.",
                    "url": f"https://example.com/result{i+1}",
                    "rank": i + 1
                }
                for i in range(num_results)
            ]
            
            return ToolResult(
                success=True,
                data={
                    "query": query,
                    "results": mock_results,
                    "total_results": num_results
                },
                metadata={
                    "source": "mock",
                    "note": "These are simulated results. Connect to real search API for production.",
                    "search_time_ms": 200
                }
            )
        
        except Exception as e:
            logger.error(f"Search tool error: {e}")
            return ToolResult(
                success=False,
                error=f"Search failed: {str(e)}",
                metadata={"query": query}
            )


# 创建这些工具的基本实现类
def create_default_tools():
    """
    Create instances of all default tools.
    
    Returns:
        List of tool instances
    """
    return [
        CalculatorTool(),
        TimeTool(),
        WeatherTool(),
        SearchTool(),
    ]
