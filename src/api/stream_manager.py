"""
Stream task manager for tracking and cancelling streaming sessions.
Enables true cancellation of ongoing LLM streaming requests.
"""
import asyncio
from typing import Dict, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class StreamTaskManager:
    """Manages active streaming tasks per session for cancellation support."""
    
    def __init__(self):
        self._tasks: Dict[str, asyncio.Task] = {}
        self._lock = asyncio.Lock()
    
    async def register_task(self, session_id: str, task: asyncio.Task) -> None:
        """Register a streaming task for a session."""
        async with self._lock:
            # Cancel existing task if any
            if session_id in self._tasks:
                old_task = self._tasks[session_id]
                if not old_task.done():
                    logger.info(f"Cancelling previous stream task for session {session_id}")
                    old_task.cancel()
                    try:
                        await old_task
                    except asyncio.CancelledError:
                        pass
            
            self._tasks[session_id] = task
            logger.debug(f"Registered stream task for session {session_id}")
    
    async def cancel_task(self, session_id: str) -> bool:
        """
        Cancel the streaming task for a session.
        
        Returns:
            True if task was found and cancelled, False otherwise.
        """
        async with self._lock:
            task = self._tasks.get(session_id)
            if task and not task.done():
                logger.info(f"Cancelling stream task for session {session_id}")
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    logger.debug(f"Stream task cancelled successfully for {session_id}")
                    pass
                return True
            return False
    
    async def unregister_task(self, session_id: str) -> None:
        """Remove a task from tracking (called on normal completion)."""
        async with self._lock:
            if session_id in self._tasks:
                del self._tasks[session_id]
                logger.debug(f"Unregistered stream task for session {session_id}")
    
    def get_active_count(self) -> int:
        """Get count of active streaming sessions."""
        return len([t for t in self._tasks.values() if not t.done()])
    
    async def cleanup_completed(self) -> int:
        """Remove completed tasks from registry. Returns count removed."""
        async with self._lock:
            completed = [sid for sid, task in self._tasks.items() if task.done()]
            for sid in completed:
                del self._tasks[sid]
            if completed:
                logger.debug(f"Cleaned up {len(completed)} completed tasks")
            return len(completed)


# Global instance
_stream_manager: Optional[StreamTaskManager] = None


def get_stream_manager() -> StreamTaskManager:
    """Get or create the global stream manager instance."""
    global _stream_manager
    if _stream_manager is None:
        _stream_manager = StreamTaskManager()
    return _stream_manager
