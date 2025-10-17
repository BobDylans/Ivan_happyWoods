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


class CalculatorTool(Tool):
    """
    Calculator tool for mathematical expressions.
    
    Evaluates mathematical expressions safely.
    """
    
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
    Web search tool using Tavily API.
    
    Tavily provides AI-optimized search results with high quality content.
    """
    
    # Hardcoded API key (TODO: Move to environment variables)
    TAVILY_API_KEY = "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"
    
    @property
    def name(self) -> str:
        return "web_search"
    
    @property
    def description(self) -> str:
        return "Search the web for information using Tavily API. Returns relevant search results with titles, snippets, and URLs."
    
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
        """Perform web search using Tavily API."""
        try:
            import httpx
            
            # Limit results
            num_results = max(1, min(num_results, 10))
            
            # Tavily API endpoint
            url = "https://api.tavily.com/search"
            
            # Prepare request payload
            payload = {
                "api_key": self.TAVILY_API_KEY,
                "query": query,
                "max_results": num_results,
                "search_depth": "basic",  # or "advanced" for deeper search
                "include_answer": True,   # Get AI-generated answer
                "include_raw_content": False,
                "include_images": False
            }
            
            # Make async HTTP request
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
            
            # Extract results
            results = []
            for i, result in enumerate(data.get("results", []), 1):
                results.append({
                    "title": result.get("title", "No title"),
                    "snippet": result.get("content", "No content available"),
                    "url": result.get("url", ""),
                    "score": result.get("score", 0),
                    "rank": i
                })
            
            # Get AI-generated answer if available
            ai_answer = data.get("answer", "")
            
            return ToolResult(
                success=True,
                data={
                    "query": query,
                    "results": results,
                    "total_results": len(results),
                    "ai_answer": ai_answer  # AI-generated summary answer
                },
                metadata={
                    "source": "tavily",
                    "search_depth": "basic",
                    "response_time": data.get("response_time", 0)
                }
            )
        
        except httpx.HTTPStatusError as e:
            logger.error(f"Tavily API HTTP error: {e.response.status_code} - {e.response.text}")
            return ToolResult(
                success=False,
                error=f"Search API error: {e.response.status_code}",
                metadata={"query": query, "error_detail": str(e)}
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


# Factory function to create all default tools
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
