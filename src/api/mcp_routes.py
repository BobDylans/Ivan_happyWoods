"""
MCP Tools API Routes

FastAPI endpoints for MCP tool management and execution.
"""

import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from src.mcp import (
    get_tool_registry,
    initialize_default_tools,
    get_available_tool_schemas,
    list_available_tools,
    ToolExecutionError
)
from .auth import get_api_key

logger = logging.getLogger(__name__)

# 创建路由
mcp_router = APIRouter(prefix="/mcp", tags=["MCP Tools"])


# 请求/响应模型
class ToolExecuteRequest(BaseModel):
    """工具执行请求"""
    tool_name: str = Field(..., description="工具名称")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="工具参数")


class ToolExecuteResponse(BaseModel):
    """工具执行响应"""
    success: bool = Field(..., description="执行是否成功")
    data: Optional[Any] = Field(default=None, description="执行结果数据")
    error: Optional[str] = Field(default=None, description="错误信息")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")


class ToolInfo(BaseModel):
    """工具信息"""
    name: str = Field(..., description="工具名称")
    description: str = Field(..., description="工具描述")
    parameters: List[Dict[str, Any]] = Field(..., description="工具参数")


class ToolListResponse(BaseModel):
    """工具列表响应"""
    tools: List[ToolInfo] = Field(..., description="工具列表")
    total: int = Field(..., description="工具总数")


@mcp_router.get(
    "/tools",
    response_model=ToolListResponse,
    summary="获取所有MCP工具",
    description="列出所有已注册的MCP工具及其信息"
)
async def list_tools(api_key: str = Depends(get_api_key)):
    """
    获取所有MCP工具列表
    
    返回所有已注册的工具及其详细信息，包括名称、描述和参数。
    """
    try:
        registry = get_tool_registry()
        tools = registry.list_tools()
        
        tool_infos = []
        for tool in tools:
            tool_info = ToolInfo(
                name=tool.name,
                description=tool.description,
                parameters=[
                    {
                        "name": param.name,
                        "type": param.type,
                        "description": param.description,
                        "required": param.required,
                        "enum": param.enum,
                        "default": param.default
                    }
                    for param in tool.parameters
                ]
            )
            tool_infos.append(tool_info)
        
        return ToolListResponse(
            tools=tool_infos,
            total=len(tool_infos)
        )
    
    except Exception as e:
        logger.error(f"获取工具列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取工具列表失败: {str(e)}")


@mcp_router.get(
    "/tools/schemas",
    summary="获取工具模式",
    description="获取所有工具的OpenAI function calling模式"
)
async def get_tool_schemas(api_key: str = Depends(get_api_key)):
    """
    获取所有工具的OpenAI function calling模式
    
    返回符合OpenAI function calling规范的工具模式，可直接用于LLM工具调用。
    """
    try:
        schemas = get_available_tool_schemas()
        return {
            "schemas": schemas,
            "total": len(schemas)
        }
    
    except Exception as e:
        logger.error(f"获取工具模式失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取工具模式失败: {str(e)}")


@mcp_router.get(
    "/tools/{tool_name}",
    response_model=ToolInfo,
    summary="获取特定工具信息",
    description="获取指定工具的详细信息"
)
async def get_tool_info(tool_name: str, api_key: str = Depends(get_api_key)):
    """
    获取特定工具的信息
    
    Args:
        tool_name: 工具名称
    
    Returns:
        工具详细信息
    """
    try:
        registry = get_tool_registry()
        tool = registry.get_tool(tool_name)
        
        if not tool:
            raise HTTPException(status_code=404, detail=f"工具 '{tool_name}' 不存在")
        
        return ToolInfo(
            name=tool.name,
            description=tool.description,
            parameters=[
                {
                    "name": param.name,
                    "type": param.type,
                    "description": param.description,
                    "required": param.required,
                    "enum": param.enum,
                    "default": param.default
                }
                for param in tool.parameters
            ]
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取工具信息失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取工具信息失败: {str(e)}")


@mcp_router.post(
    "/tools/{tool_name}/execute",
    response_model=ToolExecuteResponse,
    summary="执行MCP工具",
    description="执行指定的MCP工具并返回结果"
)
async def execute_tool(
    tool_name: str,
    request: ToolExecuteRequest,
    api_key: str = Depends(get_api_key)
):
    """
    执行MCP工具
    
    Args:
        tool_name: 工具名称
        request: 执行请求（包含参数）
    
    Returns:
        工具执行结果
    """
    try:
        registry = get_tool_registry()
        tool = registry.get_tool(tool_name)
        
        if not tool:
            raise HTTPException(status_code=404, detail=f"工具 '{tool_name}' 不存在")
        
        # 验证工具名称是否匹配
        if request.tool_name != tool_name:
            raise HTTPException(
                status_code=400, 
                detail=f"请求中的工具名称 '{request.tool_name}' 与URL中的 '{tool_name}' 不匹配"
            )
        
        logger.info(f"执行工具: {tool_name}, 参数: {request.arguments}")
        
        # 执行工具
        result = await tool.execute(**request.arguments)
        
        return ToolExecuteResponse(
            success=result.success,
            data=result.data,
            error=result.error,
            metadata=result.metadata
        )
    
    except ToolExecutionError as e:
        logger.error(f"工具执行错误: {e}")
        return ToolExecuteResponse(
            success=False,
            error=str(e),
            metadata={"tool_name": tool_name, "error_type": "ToolExecutionError"}
        )
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"工具执行异常: {e}")
        raise HTTPException(status_code=500, detail=f"工具执行异常: {str(e)}")


@mcp_router.post(
    "/tools/initialize",
    summary="初始化MCP工具",
    description="初始化并注册所有默认MCP工具"
)
async def initialize_tools(api_key: str = Depends(get_api_key)):
    """
    初始化MCP工具
    
    注册所有默认工具到工具注册表中。
    """
    try:
        registered_tools = initialize_default_tools()
        
        return {
            "success": True,
            "message": f"成功初始化 {len(registered_tools)} 个工具",
            "registered_tools": registered_tools,
            "total": len(registered_tools)
        }
    
    except Exception as e:
        logger.error(f"初始化工具失败: {e}")
        raise HTTPException(status_code=500, detail=f"初始化工具失败: {str(e)}")


@mcp_router.get(
    "/status",
    summary="MCP服务状态",
    description="获取MCP工具服务状态"
)
async def get_mcp_status(api_key: str = Depends(get_api_key)):
    """
    获取MCP服务状态
    
    返回工具注册表状态和可用工具数量。
    """
    try:
        registry = get_tool_registry()
        tool_names = registry.list_tool_names()
        
        return {
            "status": "healthy",
            "total_tools": len(tool_names),
            "available_tools": tool_names,
            "registry_initialized": True
        }
    
    except Exception as e:
        logger.error(f"获取MCP状态失败: {e}")
        return {
            "status": "error",
            "error": str(e),
            "total_tools": 0,
            "available_tools": [],
            "registry_initialized": False
        }


# 便捷的批量执行端点
@mcp_router.post(
    "/tools/batch-execute",
    summary="批量执行工具",
    description="批量执行多个工具"
)
async def batch_execute_tools(
    requests: List[ToolExecuteRequest],
    api_key: str = Depends(get_api_key)
):
    """
    批量执行工具
    
    Args:
        requests: 工具执行请求列表
    
    Returns:
        批量执行结果
    """
    try:
        registry = get_tool_registry()
        results = []
        
        for request in requests:
            try:
                tool = registry.get_tool(request.tool_name)
                if not tool:
                    results.append({
                        "tool_name": request.tool_name,
                        "success": False,
                        "error": f"工具 '{request.tool_name}' 不存在"
                    })
                    continue
                
                result = await tool.execute(**request.arguments)
                results.append({
                    "tool_name": request.tool_name,
                    "success": result.success,
                    "data": result.data,
                    "error": result.error,
                    "metadata": result.metadata
                })
            
            except Exception as e:
                results.append({
                    "tool_name": request.tool_name,
                    "success": False,
                    "error": str(e)
                })
        
        return {
            "results": results,
            "total": len(results),
            "successful": sum(1 for r in results if r["success"]),
            "failed": sum(1 for r in results if not r["success"])
        }
    
    except Exception as e:
        logger.error(f"批量执行工具失败: {e}")
        raise HTTPException(status_code=500, detail=f"批量执行工具失败: {str(e)}")
