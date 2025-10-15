# Phase 2D Implementation: MCP Tool Integration

## Overview

Phase 2D implements a Model Context Protocol (MCP) tool integration system that allows the LLM agent to call external tools for enhanced functionality. This implementation provides a flexible, extensible framework for tool registration, execution, and schema management.

## Architecture

### Component Structure

```
src/mcp/
├── __init__.py         # Package exports
├── base.py             # Abstract base classes
├── registry.py         # Tool registry (singleton)
├── tools.py            # Concrete tool implementations
└── init_tools.py       # Initialization helpers
```

### Key Components

#### 1. Tool Base Class (`base.py`)

Abstract base class defining the tool interface:

```python
class Tool(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...
    
    @property
    @abstractmethod
    def description(self) -> str: ...
    
    @property
    @abstractmethod
    def parameters(self) -> List[ToolParameter]: ...
    
    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult: ...
    
    def to_openai_schema(self) -> Dict[str, Any]: ...
```

**Supporting Models:**

- `ToolParameter`: Name, type, description, required, enum, default
- `ToolParameterType`: STRING, NUMBER, INTEGER, BOOLEAN, OBJECT, ARRAY
- `ToolResult`: Success flag, data, error message, metadata
- `ToolExecutionError`: Custom exception for tool execution failures

#### 2. Tool Registry (`registry.py`)

Singleton pattern for centralized tool management:

```python
class ToolRegistry:
    @classmethod
    def get_instance(cls) -> "ToolRegistry": ...
    
    def register(self, tool: Tool) -> None: ...
    def unregister(self, tool_name: str) -> None: ...
    async def execute(self, tool_name: str, **kwargs) -> Dict[str, Any]: ...
    def get_schemas(self) -> List[Dict[str, Any]]: ...
    def list_tools(self) -> List[Tool]: ...
    def list_tool_names(self) -> List[str]: ...
```

**Features:**

- Thread-safe singleton instance
- Duplicate registration prevention
- Tool name-based lookup
- OpenAI-compatible schema generation

#### 3. Tool Implementations (`tools.py`)

Four concrete tool implementations:

##### CalculatorTool
- **Purpose**: Safe mathematical expression evaluation
- **Parameters**: `expression` (string)
- **Security**: 
  - Empty `__builtins__` dictionary
  - Whitelist of allowed functions: abs, round, min, max, sum, pow
  - Forbidden keyword detection (import, exec, eval, open, file, compile)
- **Example**: `2 + 2 * (10 / 5)` → `6.0`

##### TimeTool (get_time)
- **Purpose**: Current date/time information
- **Parameters**: `format` (enum: full/date/time/timestamp)
- **Formats**:
  - `full`: "2025-10-14 09:30:45"
  - `date`: "2025-10-14"
  - `time`: "09:30:45"
  - `timestamp`: 1728901845
- **Output**: Includes formatted, ISO, and format_used fields

##### WeatherTool (get_weather)
- **Purpose**: Weather information (currently mock)
- **Parameters**: 
  - `location` (string, required)
  - `units` (enum: celsius/fahrenheit, default: celsius)
- **Mock Implementation**: 
  - Simulates API delay (0.1-0.2s)
  - Returns location-based temperature variations
  - Includes temperature, conditions, humidity, wind_speed
- **Production TODO**: Integrate OpenWeatherMap or Weather API

##### SearchTool (web_search)
- **Purpose**: Web search results (currently mock)
- **Parameters**: 
  - `query` (string, required)
  - `num_results` (integer, default: 5, max: 10)
- **Mock Implementation**:
  - Simulates search delay (0.1-0.3s)
  - Returns array of results with title/snippet/url/rank
- **Production TODO**: Integrate Google Custom Search, Bing API, or DuckDuckGo

## Integration Points

### 1. Agent Integration (`agent/nodes.py`)

Updated `_execute_tool_call()` to route through MCP registry:

```python
def _execute_tool_call(state: AgentState, tool_call) -> Dict[str, Any]:
    tool_name = tool_call["name"]
    
    # Name mapping for legacy compatibility
    name_mapping = {
        "search_tool": "web_search",
        "calculator": "calculator",
        "time_tool": "get_time",
        "weather_tool": "get_weather"
    }
    
    mcp_name = name_mapping.get(tool_name, tool_name)
    
    try:
        from src.mcp import get_tool_registry
        registry = get_tool_registry()
        result = await registry.execute(mcp_name, **tool_call.get("args", {}))
        return result
    except:
        # Fallback to placeholder response
        return placeholder_result
```

### 2. API Integration (`api/main.py`)

Tool initialization in application startup:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    from src.mcp.init_tools import initialize_default_tools
    registered_tools = initialize_default_tools()
    logger.info(f"Initialized {len(registered_tools)} MCP tools")
    
    yield
    
    # Shutdown
    ...
```

### 3. API Endpoints (`api/routes.py`)

Three new endpoints for tool management:

#### GET /api/v1/tools/
List all available tools with parameters:

```json
{
  "success": true,
  "tools": [
    {
      "name": "calculator",
      "description": "Evaluate mathematical expressions...",
      "parameters": [
        {
          "name": "expression",
          "type": "STRING",
          "description": "Mathematical expression...",
          "required": true,
          "default": null
        }
      ]
    }
  ],
  "total": 4
}
```

#### GET /api/v1/tools/schemas
Get OpenAI-compatible function calling schemas:

```json
{
  "success": true,
  "schemas": [
    {
      "type": "function",
      "function": {
        "name": "calculator",
        "description": "Evaluate mathematical expressions...",
        "parameters": {
          "type": "object",
          "properties": {
            "expression": {
              "type": "string",
              "description": "Mathematical expression..."
            }
          },
          "required": ["expression"]
        }
      }
    }
  ],
  "total": 4
}
```

#### POST /api/v1/tools/execute/{tool_name}
Manually execute a tool (for testing/debugging):

```json
// Request: POST /api/v1/tools/execute/calculator
{
  "expression": "2 + 2"
}

// Response
{
  "success": true,
  "tool": "calculator",
  "result": {
    "success": true,
    "data": {
      "expression": "2 + 2",
      "result": 4
    },
    "error": null,
    "metadata": {"execution_time": 0.001}
  }
}
```

## OpenAI Schema Compatibility

The `to_openai_schema()` method generates schemas compatible with OpenAI's function calling API:

```python
{
    "type": "function",
    "function": {
        "name": "tool_name",
        "description": "Tool description",
        "parameters": {
            "type": "object",
            "properties": {
                "param_name": {
                    "type": "string",  # or number, integer, boolean, object, array
                    "description": "Parameter description",
                    "enum": ["value1", "value2"],  # optional
                    "default": "default_value"      # optional
                }
            },
            "required": ["param1", "param2"]
        }
    }
}
```

## Testing

### Test Coverage

**Total Tests**: 35 (28 MCP + 7 endpoint tests)
**Pass Rate**: 100%

#### Unit Tests (`tests/unit/test_mcp_tools.py`)

- **TestToolBase** (3 tests): Parameter creation, result structures
- **TestCalculatorTool** (4 tests): Arithmetic, complex expressions, invalid input, schema
- **TestTimeTool** (4 tests): All format types, parameter validation
- **TestWeatherTool** (3 tests): Basic functionality, unit conversion, schema
- **TestSearchTool** (3 tests): Basic search, result limits, structure validation
- **TestToolRegistry** (8 tests): Singleton, registration, execution, schemas, errors
- **TestToolIntegration** (3 tests): Multi-tool registration, execution, schema validation

#### Endpoint Tests (`tests/unit/test_tools_endpoints.py`)

- List tools endpoint
- Get schemas endpoint
- Execute calculator
- Execute time tool
- Execute weather tool
- Invalid tool handling
- Security validation (forbidden expressions)

### Test Execution

```bash
# Run MCP tests only
python -m pytest tests/unit/test_mcp_tools.py -v

# Run endpoint tests only
python -m pytest tests/unit/test_tools_endpoints.py -v

# Run all tests
python -m pytest tests/ -v
```

## Security Considerations

### Calculator Tool Security

1. **Empty Builtins**: Evaluates with `{"__builtins__": {}}`
2. **Whitelist Approach**: Only allows specific functions (abs, round, min, max, sum, pow)
3. **Keyword Filtering**: Blocks dangerous keywords (import, exec, eval, open, file, compile)
4. **Error Handling**: Returns safe error messages without exposing internals

**Blocked Examples:**
- `import os` → Rejected (forbidden keyword)
- `__import__('os')` → Rejected (no __import__ in allowed names)
- `open('file.txt')` → Rejected (forbidden keyword)

**Allowed Examples:**
- `2 + 2 * 3` → 8
- `pow(2, 10)` → 1024
- `round(3.14159, 2)` → 3.14
- `max([1, 5, 3])` → 5

## Extension Guide

### Adding a New Tool

1. **Create Tool Class** (in `tools.py` or separate file):

```python
from src.mcp.base import Tool, ToolParameter, ToolParameterType, ToolResult

class ImageGenerationTool(Tool):
    @property
    def name(self) -> str:
        return "generate_image"
    
    @property
    def description(self) -> str:
        return "Generate an image from text description using DALL-E"
    
    @property
    def parameters(self):
        return [
            ToolParameter(
                name="prompt",
                type=ToolParameterType.STRING,
                description="Text description of image to generate",
                required=True
            ),
            ToolParameter(
                name="size",
                type=ToolParameterType.STRING,
                description="Image size",
                required=False,
                enum=["256x256", "512x512", "1024x1024"],
                default="512x512"
            )
        ]
    
    async def execute(self, prompt: str, size: str = "512x512", **kwargs) -> ToolResult:
        try:
            # Call DALL-E API
            image_url = await self._generate_image(prompt, size)
            
            return ToolResult(
                success=True,
                data={"image_url": image_url, "prompt": prompt, "size": size}
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Image generation failed: {str(e)}"
            )
```

2. **Register in `init_tools.py`**:

```python
def initialize_default_tools() -> List[str]:
    tools_to_register = [
        CalculatorTool(),
        TimeTool(),
        WeatherTool(),
        SearchTool(),
        ImageGenerationTool(),  # Add new tool
    ]
    ...
```

3. **Export in `__init__.py`**:

```python
from .tools import (
    CalculatorTool,
    TimeTool,
    WeatherTool,
    SearchTool,
    ImageGenerationTool,  # Add export
)

__all__ = [
    # ... existing exports ...
    "ImageGenerationTool",
]
```

4. **Add Tests**:

```python
class TestImageGenerationTool:
    @pytest.mark.asyncio
    async def test_image_generation_basic(self):
        tool = ImageGenerationTool()
        result = await tool.execute(prompt="A sunset over mountains")
        
        assert result.success is True
        assert "image_url" in result.data
        assert result.data["prompt"] == "A sunset over mountains"
```

## Performance Considerations

### Async Execution

All tool execution is asynchronous:

```python
async def execute(self, **kwargs) -> ToolResult:
    # Allows concurrent tool calls
    # Non-blocking I/O for API calls
```

### Mock Tool Delays

Current mock implementations simulate realistic API delays:

- WeatherTool: 0.1-0.2s
- SearchTool: 0.1-0.3s

Replace with actual API calls for production.

### Registry Lookup

Tool lookup is O(1) via dictionary:

```python
self._tools[tool_name]  # Fast name-based lookup
```

## Future Enhancements

### Short-term (Phase 3)

1. **Real API Integration**:
   - OpenWeatherMap for weather
   - Google Custom Search for web search
   - Configuration management for API keys

2. **Additional Tools**:
   - Document analysis (PDF, DOCX)
   - Image analysis (vision models)
   - Email sending
   - Calendar operations

3. **Tool Analytics**:
   - Execution time tracking
   - Success/failure rates
   - Usage statistics per tool

### Long-term (Phase 4+)

1. **Dynamic Tool Loading**:
   - Load tools from plugins
   - Hot-reload tool updates
   - Version management

2. **Tool Composition**:
   - Chain multiple tools
   - Parallel execution
   - Conditional logic

3. **Advanced Security**:
   - Rate limiting per tool
   - Resource usage monitoring
   - Sandboxed execution environments

## Configuration

### Environment Variables

```bash
# API Keys for production tools
OPENWEATHER_API_KEY=your_key_here
GOOGLE_SEARCH_API_KEY=your_key_here
GOOGLE_SEARCH_CX=your_cx_here

# Tool Settings
MCP_CALCULATOR_TIMEOUT=5  # seconds
MCP_SEARCH_TIMEOUT=10     # seconds
MCP_MAX_CONCURRENT_TOOLS=5
```

### Configuration Model (Future)

```python
class MCPConfig(BaseModel):
    calculator_timeout: int = 5
    search_timeout: int = 10
    weather_timeout: int = 10
    max_concurrent_tools: int = 5
    enable_caching: bool = True
    cache_ttl: int = 300  # seconds
```

## API Documentation

### OpenAPI Specification

The MCP tools are automatically documented in the OpenAPI spec:

```yaml
/api/v1/tools/:
  get:
    summary: List all available MCP tools
    responses:
      200:
        description: Tool list with parameters
        
/api/v1/tools/schemas:
  get:
    summary: Get OpenAI-compatible function schemas
    responses:
      200:
        description: Function calling schemas

/api/v1/tools/execute/{tool_name}:
  post:
    summary: Execute a specific tool
    parameters:
      - name: tool_name
        in: path
        required: true
    requestBody:
      description: Tool parameters
    responses:
      200:
        description: Tool execution result
```

## Troubleshooting

### Common Issues

1. **ImportError: cannot import name 'get_tool_registry' from 'mcp'**
   - **Cause**: System `mcp` package conflicts with our `src.mcp`
   - **Solution**: Use absolute imports: `from src.mcp import get_tool_registry`

2. **Tool 'X' not found**
   - **Cause**: Tool not registered during startup
   - **Solution**: Check `initialize_default_tools()` is called in `lifespan()`

3. **Calculator security error: "Forbidden keyword"**
   - **Cause**: Expression contains blocked keywords
   - **Solution**: Remove import/exec/eval statements from expression

4. **TestClient doesn't initialize tools**
   - **Cause**: TestClient doesn't trigger lifespan events
   - **Solution**: Manually call `initialize_default_tools()` in test setup

## Related Documentation

- [Phase 2A Implementation](./phase2a-implementation.md) - Streaming & Auth
- [Phase 2C Implementation](./phase2c-implementation.md) - Event Protocol
- [API Reference](../specs/001-voice-interaction-system/contracts/openapi.partial.yaml)
- [Agent Architecture](../specs/001-voice-interaction-system/architecture.md)

## Changelog

### 2025-10-14 - Phase 2D Complete
- ✅ Implemented MCP tool framework (base.py, registry.py)
- ✅ Created 4 concrete tools (Calculator, Time, Weather, Search)
- ✅ Integrated with agent nodes for tool calling
- ✅ Added 3 API endpoints (/tools, /schemas, /execute)
- ✅ Comprehensive testing (35 tests, 100% pass rate)
- ✅ OpenAI schema compatibility
- ✅ Security hardening for calculator tool
- ⏳ TODO: Real API integration for Weather & Search tools
