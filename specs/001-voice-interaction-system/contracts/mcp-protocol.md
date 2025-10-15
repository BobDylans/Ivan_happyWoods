# MCP Protocol Contracts

## Tool Registry Schema

### Tool Registration Request

```json
{
  "jsonrpc": "2.0",
  "method": "tools/register",
  "params": {
    "tool": {
      "name": "search_tool",
      "description": "Web search functionality",
      "category": "SEARCH",
      "functions": [
        {
          "name": "web_search",
          "description": "Search the web for information",
          "parameters": {
            "type": "object",
            "properties": {
              "query": {
                "type": "string",
                "description": "Search query"
              },
              "max_results": {
                "type": "integer",
                "default": 5,
                "minimum": 1,
                "maximum": 20
              }
            },
            "required": ["query"]
          },
          "returns": {
            "type": "object",
            "properties": {
              "results": {
                "type": "array",
                "items": {
                  "type": "object",
                  "properties": {
                    "title": {"type": "string"},
                    "url": {"type": "string"},
                    "snippet": {"type": "string"}
                  }
                }
              }
            }
          }
        }
      ]
    }
  },
  "id": 1
}
```

### Tool Registration Response

```json
{
  "jsonrpc": "2.0",
  "result": {
    "tool_id": "search_tool_v1",
    "status": "registered",
    "health_check_interval": 60
  },
  "id": 1
}
```

## Tool Execution Protocol

### Function Call Request

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "tool_name": "search_tool",
    "function_name": "web_search",
    "arguments": {
      "query": "artificial intelligence trends 2025",
      "max_results": 3
    },
    "call_id": "uuid-123-456-789",
    "timeout": 10
  },
  "id": 2
}
```

### Function Call Response (Success)

```json
{
  "jsonrpc": "2.0",
  "result": {
    "call_id": "uuid-123-456-789",
    "status": "completed",
    "data": {
      "results": [
        {
          "title": "AI Trends 2025: What to Expect",
          "url": "https://example.com/ai-trends-2025",
          "snippet": "Major trends in artificial intelligence for 2025 include..."
        }
      ]
    },
    "execution_time_ms": 1250
  },
  "id": 2
}
```

### Function Call Response (Error)

```json
{
  "jsonrpc": "2.0",
  "error": {
    "code": -32001,
    "message": "Tool execution failed",
    "data": {
      "call_id": "uuid-123-456-789",
      "error_type": "timeout",
      "details": "Search service did not respond within 10 seconds"
    }
  },
  "id": 2
}
```

## Predefined Tool Contracts

### Search Tool

```json
{
  "name": "search_tool",
  "description": "Web search and information retrieval",
  "category": "SEARCH",
  "functions": [
    {
      "name": "web_search",
      "description": "Search the internet for information",
      "parameters": {
        "type": "object",
        "properties": {
          "query": {"type": "string"},
          "max_results": {"type": "integer", "default": 5}
        },
        "required": ["query"]
      }
    },
    {
      "name": "news_search",
      "description": "Search for recent news articles",
      "parameters": {
        "type": "object",
        "properties": {
          "query": {"type": "string"},
          "days_back": {"type": "integer", "default": 7}
        },
        "required": ["query"]
      }
    }
  ]
}
```

### Calculator Tool

```json
{
  "name": "calculator",
  "description": "Mathematical calculations and computations",
  "category": "CALCULATION",
  "functions": [
    {
      "name": "calculate",
      "description": "Perform mathematical calculations",
      "parameters": {
        "type": "object",
        "properties": {
          "expression": {
            "type": "string",
            "description": "Mathematical expression to evaluate"
          }
        },
        "required": ["expression"]
      }
    },
    {
      "name": "convert_units",
      "description": "Convert between different units",
      "parameters": {
        "type": "object",
        "properties": {
          "value": {"type": "number"},
          "from_unit": {"type": "string"},
          "to_unit": {"type": "string"}
        },
        "required": ["value", "from_unit", "to_unit"]
      }
    }
  ]
}
```

### Image Generation Tool

```json
{
  "name": "image_generator",
  "description": "AI-powered image generation",
  "category": "AI_GENERATION", 
  "functions": [
    {
      "name": "generate_image",
      "description": "Generate image from text description",
      "parameters": {
        "type": "object",
        "properties": {
          "prompt": {"type": "string"},
          "style": {
            "type": "string",
            "enum": ["realistic", "artistic", "cartoon", "abstract"],
            "default": "realistic"
          },
          "size": {
            "type": "string",
            "enum": ["256x256", "512x512", "1024x1024"],
            "default": "512x512"
          }
        },
        "required": ["prompt"]
      }
    }
  ]
}
```

### Document Analysis Tool

```json
{
  "name": "document_analyzer",
  "description": "Document analysis and content extraction",
  "category": "ANALYSIS",
  "functions": [
    {
      "name": "analyze_document",
      "description": "Extract and analyze document content",
      "parameters": {
        "type": "object",
        "properties": {
          "document_url": {"type": "string"},
          "analysis_type": {
            "type": "string",
            "enum": ["summary", "keywords", "sentiment", "entities"],
            "default": "summary"
          }
        },
        "required": ["document_url"]
      }
    },
    {
      "name": "extract_text",
      "description": "Extract text from various document formats",
      "parameters": {
        "type": "object",
        "properties": {
          "document_url": {"type": "string"},
          "format": {
            "type": "string",
            "enum": ["pdf", "docx", "txt", "html"]
          }
        },
        "required": ["document_url"]
      }
    }
  ]
}
```

### Time Tool

```json
{
  "name": "time_tool",
  "description": "Time and date utilities",
  "category": "TIME",
  "functions": [
    {
      "name": "current_time",
      "description": "Get current time in specified timezone",
      "parameters": {
        "type": "object",
        "properties": {
          "timezone": {
            "type": "string",
            "default": "UTC"
          },
          "format": {
            "type": "string",
            "default": "ISO8601"
          }
        }
      }
    },
    {
      "name": "time_difference",
      "description": "Calculate time difference between two timestamps",
      "parameters": {
        "type": "object",
        "properties": {
          "start_time": {"type": "string"},
          "end_time": {"type": "string"},
          "unit": {
            "type": "string", 
            "enum": ["seconds", "minutes", "hours", "days"],
            "default": "hours"
          }
        },
        "required": ["start_time", "end_time"]
      }
    }
  ]
}
```

## Health Check Protocol

### Health Check Request

```json
{
  "jsonrpc": "2.0",
  "method": "health/check",
  "params": {
    "tool_name": "search_tool"
  },
  "id": 3
}
```

### Health Check Response

```json
{
  "jsonrpc": "2.0",
  "result": {
    "status": "healthy",
    "response_time_ms": 45,
    "version": "1.0.0",
    "capabilities": ["web_search", "news_search"],
    "last_error": null
  },
  "id": 3
}
```

## Error Codes

| Code | Message | Description |
|------|---------|-------------|
| -32000 | Server error | Generic server error |
| -32001 | Tool execution failed | Tool function execution error |
| -32002 | Tool not found | Requested tool is not registered |
| -32003 | Function not found | Tool function does not exist |
| -32004 | Invalid parameters | Function parameters validation failed |
| -32005 | Timeout | Tool execution exceeded timeout |
| -32006 | Service unavailable | External service dependency failed |
| -32007 | Rate limited | Too many requests to tool service |

## Message Flow Examples

### Successful Tool Call Sequence

1. Agent receives user request requiring external tool
2. Agent sends tool call request to MCP server
3. MCP server validates request and forwards to tool service
4. Tool service processes request and returns result
5. MCP server forwards result back to agent
6. Agent incorporates result into response to user

### Error Handling Sequence

1. Agent sends tool call request
2. Tool service is unavailable or times out
3. MCP server returns error response with details
4. Agent implements graceful degradation (inform user of limitation)
5. Agent provides alternative response or suggests retry

### Health Monitoring

1. MCP server periodically sends health check requests to all registered tools
2. Tools respond with status and performance metrics
3. MCP server updates tool availability status
4. Unavailable tools are marked for graceful degradation
5. Agent queries tool status before making calls