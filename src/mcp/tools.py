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
    Web search tool with Tavily API integration.
    
    Tavily provides AI-optimized search results with high-quality snippets,
    relevance scores, and optional AI-generated answers.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize SearchTool with configuration.
        
        Args:
            config: Configuration dict with api_key, search_depth, etc.
        """
        self.config = config or {}
    
    @property
    def name(self) -> str:
        return "web_search"
    
    @property
    def description(self) -> str:
        return "Search the web for real-time information. Returns relevant search results with titles, snippets, URLs, and relevance scores. Supports both English and Chinese queries."
    
    @property
    def parameters(self):
        return [
            ToolParameter(
                name="query",
                type=ToolParameterType.STRING,
                description="Search query (e.g., 'latest AI news', 'Python tutorial', '人工智能最新进展')",
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
        """Perform web search using Tavily API."""
        import os
        
        try:
            # Limit results
            num_results = max(1, min(num_results, 10))
            
            # Get API key from config or environment
            api_key = self.config.get("api_key") or os.getenv("TAVILY_API_KEY")
            
            if not api_key:
                logger.warning("Tavily API key not found, using mock results")
                return self._mock_search(query, num_results)
            
            # Prepare Tavily API request
            search_depth = self.config.get("search_depth", "basic")
            tavily_url = "https://api.tavily.com/search"
            
            payload = {
                "api_key": api_key,
                "query": query,
                "search_depth": search_depth,
                "max_results": num_results,
                "include_answer": True,
                "include_raw_content": False,
                "include_images": False
            }
            
            logger.info(f"🔍 Calling Tavily API for query: {query[:50]}...")
            
            # Make API call
            async with httpx.AsyncClient(timeout=self.config.get("timeout", 15)) as client:
                response = await client.post(tavily_url, json=payload)
                response.raise_for_status()
                data = response.json()
            
            # Parse Tavily response
            results = []
            for item in data.get("results", []):
                results.append({
                    "title": item.get("title", ""),
                    "snippet": item.get("content", ""),
                    "url": item.get("url", ""),
                    "score": item.get("score", 0.0),
                    "published_date": item.get("published_date")
                })
            
            logger.info(f"✅ Tavily returned {len(results)} results")
            
            return ToolResult(
                success=True,
                data={
                    "query": query,
                    "ai_answer": data.get("answer"),  # AI-generated summary
                    "results": results,
                    "total_results": len(results)
                },
                metadata={
                    "source": "tavily",
                    "search_depth": search_depth,
                    "response_time": data.get("response_time", 0)
                }
            )
        
        except httpx.HTTPStatusError as e:
            logger.error(f"Tavily API HTTP error: {e.response.status_code} - {e.response.text}")
            return ToolResult(
                success=False,
                error=f"Search API error: {e.response.status_code}",
                metadata={"query": query, "status_code": e.response.status_code}
            )
        
        except httpx.TimeoutException:
            logger.error(f"Tavily API timeout for query: {query}")
            return ToolResult(
                success=False,
                error="Search request timed out",
                metadata={"query": query}
            )
        
        except Exception as e:
            logger.error(f"Search tool error: {e}")
            return ToolResult(
                success=False,
                error=f"Search failed: {str(e)}",
                metadata={"query": query}
            )
    
    def _mock_search(self, query: str, num_results: int) -> ToolResult:
        """Fallback mock search when API key is not available."""
        mock_results = [
            {
                "title": f"Result {i+1} for '{query}'",
                "snippet": f"This is a mock search result. Please configure TAVILY_API_KEY for real results.",
                "url": f"https://example.com/result{i+1}",
                "score": 0.5,
                "published_date": None
            }
            for i in range(num_results)
        ]
        
        return ToolResult(
            success=True,
            data={
                "query": query,
                "ai_answer": "Mock answer: Please configure Tavily API key for real search results.",
                "results": mock_results,
                "total_results": num_results
            },
            metadata={
                "source": "mock",
                "note": "Using mock data. Set TAVILY_API_KEY for real results."
            }
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
