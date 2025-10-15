"""
Tests for MCP Tools

Tests tool registry, base classes, and concrete tool implementations.
"""

import pytest
from src.mcp import (
    ToolRegistry,
    get_tool_registry,
    Tool,
    ToolParameter,
    ToolParameterType,
    ToolResult,
    ToolExecutionError,
    CalculatorTool,
    TimeTool,
    WeatherTool,
    SearchTool,
)


class TestToolBase:
    """Tests for tool base classes and schemas."""
    
    def test_tool_parameter_creation(self):
        """Test creating tool parameters."""
        param = ToolParameter(
            name="test_param",
            type=ToolParameterType.STRING,
            description="A test parameter",
            required=True
        )
        
        assert param.name == "test_param"
        assert param.type == ToolParameterType.STRING
        assert param.description == "A test parameter"
        assert param.required is True
    
    def test_tool_result_success(self):
        """Test successful tool result."""
        result = ToolResult(
            success=True,
            data={"result": 42},
            metadata={"execution_time": 100}
        )
        
        assert result.success is True
        assert result.data["result"] == 42
        assert result.error is None
        assert result.metadata["execution_time"] == 100
    
    def test_tool_result_failure(self):
        """Test failed tool result."""
        result = ToolResult(
            success=False,
            error="Something went wrong"
        )
        
        assert result.success is False
        assert result.error == "Something went wrong"
        assert result.data is None


class TestCalculatorTool:
    """Tests for calculator tool."""
    
    @pytest.mark.asyncio
    async def test_calculator_basic_arithmetic(self):
        """Test basic arithmetic operations."""
        calc = CalculatorTool()
        
        # Addition
        result = await calc.execute(expression="2 + 2")
        assert result.success is True
        assert result.data["result"] == 4
        
        # Multiplication
        result = await calc.execute(expression="5 * 6")
        assert result.success is True
        assert result.data["result"] == 30
        
        # Division
        result = await calc.execute(expression="10 / 2")
        assert result.success is True
        assert result.data["result"] == 5.0
    
    @pytest.mark.asyncio
    async def test_calculator_complex_expression(self):
        """Test complex mathematical expressions."""
        calc = CalculatorTool()
        
        result = await calc.execute(expression="(10 + 5) * 2 - 8")
        assert result.success is True
        assert result.data["result"] == 22
    
    @pytest.mark.asyncio
    async def test_calculator_invalid_expression(self):
        """Test handling of invalid expressions."""
        calc = CalculatorTool()
        
        result = await calc.execute(expression="invalid")
        assert result.success is False
        assert result.error is not None
    
    def test_calculator_schema(self):
        """Test calculator OpenAI schema generation."""
        calc = CalculatorTool()
        schema = calc.to_openai_schema()
        
        assert schema["type"] == "function"
        assert schema["function"]["name"] == "calculator"
        assert "expression" in schema["function"]["parameters"]["properties"]
        assert "expression" in schema["function"]["parameters"]["required"]


class TestTimeTool:
    """Tests for time tool."""
    
    @pytest.mark.asyncio
    async def test_time_full_format(self):
        """Test full time format."""
        time_tool = TimeTool()
        
        result = await time_tool.execute(format="full")
        assert result.success is True
        assert "formatted" in result.data
        assert "iso" in result.data
        assert result.data["format_used"] == "full"
    
    @pytest.mark.asyncio
    async def test_time_date_only(self):
        """Test date-only format."""
        time_tool = TimeTool()
        
        result = await time_tool.execute(format="date")
        assert result.success is True
        assert len(result.data["formatted"]) == 10  # YYYY-MM-DD
        assert "-" in result.data["formatted"]
    
    @pytest.mark.asyncio
    async def test_time_timestamp(self):
        """Test timestamp format."""
        time_tool = TimeTool()
        
        result = await time_tool.execute(format="timestamp")
        assert result.success is True
        assert isinstance(result.data["formatted"], int)
        assert result.data["formatted"] > 0
    
    def test_time_tool_parameters(self):
        """Test time tool parameter definitions."""
        time_tool = TimeTool()
        
        assert len(time_tool.parameters) == 1
        assert time_tool.parameters[0].name == "format"
        assert time_tool.parameters[0].enum == ["full", "date", "time", "timestamp"]


class TestWeatherTool:
    """Tests for weather tool."""
    
    @pytest.mark.asyncio
    async def test_weather_basic(self):
        """Test basic weather query."""
        weather = WeatherTool()
        
        result = await weather.execute(location="London")
        assert result.success is True
        assert "temperature" in result.data
        assert "conditions" in result.data
        assert result.data["location"] == "London"
    
    @pytest.mark.asyncio
    async def test_weather_units(self):
        """Test temperature unit conversion."""
        weather = WeatherTool()
        
        # Celsius
        result_c = await weather.execute(location="Tokyo", units="celsius")
        assert result_c.success is True
        assert result_c.data["units"] == "celsius"
        
        # Fahrenheit
        result_f = await weather.execute(location="Tokyo", units="fahrenheit")
        assert result_f.success is True
        assert result_f.data["units"] == "fahrenheit"
        assert result_f.data["temperature"] > result_c.data["temperature"]  # F > C for same temp
    
    def test_weather_schema(self):
        """Test weather tool schema."""
        weather = WeatherTool()
        schema = weather.to_openai_schema()
        
        assert schema["function"]["name"] == "get_weather"
        params = schema["function"]["parameters"]["properties"]
        assert "location" in params
        assert "units" in params


class TestSearchTool:
    """Tests for search tool."""
    
    @pytest.mark.asyncio
    async def test_search_basic(self):
        """Test basic search query."""
        search = SearchTool()
        
        result = await search.execute(query="Python tutorial")
        assert result.success is True
        assert "results" in result.data
        assert result.data["query"] == "Python tutorial"
        assert len(result.data["results"]) > 0
    
    @pytest.mark.asyncio
    async def test_search_num_results(self):
        """Test controlling number of results."""
        search = SearchTool()
        
        result = await search.execute(query="test", num_results=3)
        assert result.success is True
        assert len(result.data["results"]) == 3
    
    @pytest.mark.asyncio
    async def test_search_result_structure(self):
        """Test search result structure."""
        search = SearchTool()
        
        result = await search.execute(query="AI news")
        assert result.success is True
        
        first_result = result.data["results"][0]
        assert "title" in first_result
        assert "snippet" in first_result
        assert "url" in first_result
        assert "rank" in first_result


class TestToolRegistry:
    """Tests for tool registry."""
    
    def setup_method(self):
        """Reset registry before each test."""
        registry = get_tool_registry()
        registry.clear()
    
    def test_registry_singleton(self):
        """Test registry is a singleton."""
        registry1 = get_tool_registry()
        registry2 = get_tool_registry()
        
        assert registry1 is registry2
    
    def test_register_tool(self):
        """Test registering a tool."""
        registry = get_tool_registry()
        calc = CalculatorTool()
        
        registry.register(calc)
        
        assert "calculator" in registry
        assert len(registry) == 1
        assert registry.get("calculator") is calc
    
    def test_register_duplicate_error(self):
        """Test registering duplicate tool raises error."""
        registry = get_tool_registry()
        calc1 = CalculatorTool()
        calc2 = CalculatorTool()
        
        registry.register(calc1)
        
        with pytest.raises(ValueError, match="already registered"):
            registry.register(calc2)
    
    def test_unregister_tool(self):
        """Test unregistering a tool."""
        registry = get_tool_registry()
        calc = CalculatorTool()
        
        registry.register(calc)
        assert "calculator" in registry
        
        registry.unregister("calculator")
        assert "calculator" not in registry
    
    def test_list_tools(self):
        """Test listing all tools."""
        registry = get_tool_registry()
        
        registry.register(CalculatorTool())
        registry.register(TimeTool())
        
        tools = registry.list_tools()
        assert len(tools) == 2
        
        tool_names = registry.list_tool_names()
        assert "calculator" in tool_names
        assert "get_time" in tool_names
    
    def test_get_schemas(self):
        """Test getting all tool schemas."""
        registry = get_tool_registry()
        
        registry.register(CalculatorTool())
        registry.register(TimeTool())
        
        schemas = registry.get_schemas()
        assert len(schemas) == 2
        assert all(s["type"] == "function" for s in schemas)
    
    @pytest.mark.asyncio
    async def test_execute_tool(self):
        """Test executing tool through registry."""
        registry = get_tool_registry()
        registry.register(CalculatorTool())
        
        result = await registry.execute("calculator", expression="5 + 5")
        
        assert result["success"] is True
        assert result["data"]["result"] == 10
    
    @pytest.mark.asyncio
    async def test_execute_nonexistent_tool(self):
        """Test executing non-existent tool raises error."""
        registry = get_tool_registry()
        
        with pytest.raises(ToolExecutionError, match="not found"):
            await registry.execute("nonexistent_tool")


class TestToolIntegration:
    """Integration tests for multiple tools."""
    
    def setup_method(self):
        """Set up registry with all tools."""
        registry = get_tool_registry()
        registry.clear()
        
        registry.register(CalculatorTool())
        registry.register(TimeTool())
        registry.register(WeatherTool())
        registry.register(SearchTool())
    
    def test_all_tools_registered(self):
        """Test all default tools can be registered."""
        registry = get_tool_registry()
        
        assert len(registry) == 4
        assert "calculator" in registry
        assert "get_time" in registry
        assert "get_weather" in registry
        assert "web_search" in registry
    
    @pytest.mark.asyncio
    async def test_execute_multiple_tools(self):
        """Test executing multiple tools in sequence."""
        registry = get_tool_registry()
        
        # Execute calculator
        calc_result = await registry.execute("calculator", expression="10 * 2")
        assert calc_result["success"] is True
        
        # Execute time tool
        time_result = await registry.execute("get_time", format="date")
        assert time_result["success"] is True
        
        # Execute weather tool
        weather_result = await registry.execute("get_weather", location="Tokyo")
        assert weather_result["success"] is True
    
    def test_all_tools_have_valid_schemas(self):
        """Test all tools generate valid OpenAI schemas."""
        registry = get_tool_registry()
        schemas = registry.get_schemas()
        
        for schema in schemas:
            assert "type" in schema
            assert schema["type"] == "function"
            assert "function" in schema
            assert "name" in schema["function"]
            assert "description" in schema["function"]
            assert "parameters" in schema["function"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
