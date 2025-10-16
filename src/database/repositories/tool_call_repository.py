"""
ToolCall Repository

Data access layer for tool execution records.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from uuid import UUID

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import ToolCall

logger = logging.getLogger(__name__)


class ToolCallRepository:
    """Repository for tool call CRUD operations."""
    
    def __init__(self, session: AsyncSession):
        """
        Initialize repository with database session.
        
        Args:
            session: AsyncSession instance
        """
        self.session = session
    
    async def save_tool_call(
        self,
        session_id: str,
        tool_name: str,
        parameters: Dict[str, Any],
        result: Dict[str, Any],
        execution_time_ms: Optional[int] = None,
        message_id: Optional[UUID] = None,
        webhook_url: Optional[str] = None,
        response_status: Optional[int] = None,
        response_time_ms: Optional[int] = None
    ) -> ToolCall:
        """
        Save a tool execution record.
        
        Args:
            session_id: Session identifier
            tool_name: Name of the tool
            parameters: Tool input parameters
            result: Tool execution result
            execution_time_ms: Execution time in milliseconds
            message_id: Optional related message ID
            webhook_url: Optional webhook URL (for n8n tools)
            response_status: Optional HTTP response status
            response_time_ms: Optional response time
            
        Returns:
            Created ToolCall object
        """
        new_tool_call = ToolCall(
            session_id=session_id,
            message_id=message_id,
            tool_name=tool_name,
            parameters=parameters,
            result=result,
            execution_time_ms=execution_time_ms,
            webhook_url=webhook_url,
            response_status=response_status,
            response_time_ms=response_time_ms
        )
        
        self.session.add(new_tool_call)
        await self.session.flush()
        
        logger.debug(f"Saved tool call: {tool_name} for session {session_id}")
        return new_tool_call
    
    async def get_tool_calls(
        self,
        session_id: str,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[ToolCall]:
        """
        Get tool calls for a session.
        
        Args:
            session_id: Session identifier
            limit: Maximum number of tool calls to return
            offset: Number of tool calls to skip
            
        Returns:
            List of ToolCall objects
        """
        query = select(ToolCall).where(ToolCall.session_id == session_id)
        query = query.order_by(ToolCall.timestamp.desc())
        
        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def get_tool_statistics(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        tool_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get tool usage statistics.
        
        Args:
            start_time: Optional start timestamp filter
            end_time: Optional end timestamp filter
            tool_name: Optional tool name filter
            
        Returns:
            Dictionary with statistics
        """
        # Base query
        base_query = select(ToolCall)
        
        # Apply filters
        conditions = []
        if start_time:
            conditions.append(ToolCall.timestamp >= start_time)
        if end_time:
            conditions.append(ToolCall.timestamp <= end_time)
        if tool_name:
            conditions.append(ToolCall.tool_name == tool_name)
        
        if conditions:
            base_query = base_query.where(and_(*conditions))
        
        # Total calls
        count_result = await self.session.execute(
            select(func.count(ToolCall.call_id)).select_from(base_query.subquery())
        )
        total_calls = count_result.scalar_one()
        
        # Average execution time
        avg_time_result = await self.session.execute(
            select(func.avg(ToolCall.execution_time_ms)).select_from(base_query.subquery())
        )
        avg_execution_time = avg_time_result.scalar_one() or 0
        
        # Calls by tool
        tools_query = select(
            ToolCall.tool_name,
            func.count(ToolCall.call_id).label('count'),
            func.avg(ToolCall.execution_time_ms).label('avg_time')
        )
        
        if conditions:
            tools_query = tools_query.where(and_(*conditions))
        
        tools_query = tools_query.group_by(ToolCall.tool_name).order_by(func.count(ToolCall.call_id).desc())
        
        tools_result = await self.session.execute(tools_query)
        tools_stats = [
            {
                "tool_name": row.tool_name,
                "count": row.count,
                "avg_execution_time_ms": float(row.avg_time) if row.avg_time else 0
            }
            for row in tools_result
        ]
        
        return {
            "total_calls": total_calls,
            "avg_execution_time_ms": float(avg_execution_time),
            "tools": tools_stats
        }
    
    async def get_recent_tool_calls(
        self,
        tool_name: Optional[str] = None,
        limit: int = 10
    ) -> List[ToolCall]:
        """
        Get recent tool calls.
        
        Args:
            tool_name: Optional tool name filter
            limit: Maximum number of tool calls to return
            
        Returns:
            List of ToolCall objects
        """
        query = select(ToolCall)
        
        if tool_name:
            query = query.where(ToolCall.tool_name == tool_name)
        
        query = query.order_by(ToolCall.timestamp.desc()).limit(limit)
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def get_failed_tool_calls(
        self,
        hours: int = 24,
        limit: int = 100
    ) -> List[ToolCall]:
        """
        Get recent failed tool calls.
        
        Args:
            hours: Number of hours to look back
            limit: Maximum number of tool calls to return
            
        Returns:
            List of failed ToolCall objects
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        # Failed calls have success=False in result
        result = await self.session.execute(
            select(ToolCall)
            .where(
                and_(
                    ToolCall.timestamp >= cutoff_time,
                    ToolCall.result['success'].astext == 'false'
                )
            )
            .order_by(ToolCall.timestamp.desc())
            .limit(limit)
        )
        
        return list(result.scalars().all())

