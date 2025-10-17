"""
Session History Manager

Manages conversation history for each session in memory.
Provides automatic cleanup of expired sessions.
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import threading

logger = logging.getLogger(__name__)


class SessionHistoryManager:
    """
    Manages conversation history for multiple sessions in memory.
    
    Features:
    - Store messages per session
    - Automatic cleanup of expired sessions
    - Thread-safe operations
    - Configurable history limits
    """
    
    def __init__(self, max_history: int = 20, ttl_hours: int = 24):
        """
        Initialize the session history manager.
        
        Args:
            max_history: Maximum number of messages to keep per session
            ttl_hours: Time-to-live for sessions in hours
        """
        self._sessions: Dict[str, List[Dict]] = {}
        self._last_activity: Dict[str, datetime] = {}
        self.max_history = max_history
        self.ttl = timedelta(hours=ttl_hours)
        self._lock = threading.Lock()
        
        logger.info(f"SessionHistoryManager initialized: max_history={max_history}, ttl={ttl_hours}h")
    
    def add_message(self, session_id: str, role: str, content: str):
        """
        Add a message to the session history.
        
        Args:
            session_id: Unique session identifier
            role: Message role ('user' or 'assistant')
            content: Message content
        """
        with self._lock:
            # Initialize session if not exists
            if session_id not in self._sessions:
                self._sessions[session_id] = []
                logger.debug(f"Created new session: {session_id}")
            
            # Add message
            message = {
                "role": role,
                "content": content,
                "timestamp": datetime.now().isoformat()
            }
            self._sessions[session_id].append(message)
            
            # Update last activity
            self._last_activity[session_id] = datetime.now()
            
            # Trim history if needed
            if len(self._sessions[session_id]) > self.max_history:
                removed = len(self._sessions[session_id]) - self.max_history
                self._sessions[session_id] = self._sessions[session_id][-self.max_history:]
                logger.debug(f"Trimmed {removed} old messages from session {session_id}")
            
            logger.debug(f"Added {role} message to session {session_id}, total: {len(self._sessions[session_id])}")
    
    def get_history(self, session_id: str, limit: Optional[int] = None) -> List[Dict]:
        """
        Get conversation history for a session.
        
        Args:
            session_id: Unique session identifier
            limit: Optional limit on number of messages to return (most recent)
        
        Returns:
            List of message dictionaries with 'role' and 'content'
        """
        with self._lock:
            if session_id not in self._sessions:
                logger.debug(f"No history found for session {session_id}")
                return []
            
            # Update last activity
            self._last_activity[session_id] = datetime.now()
            
            history = self._sessions[session_id]
            
            # Apply limit if specified
            if limit and limit > 0:
                history = history[-limit:]
            
            logger.debug(f"Retrieved {len(history)} messages for session {session_id}")
            return history.copy()
    
    def clear_session(self, session_id: str):
        """
        Clear all history for a specific session.
        
        Args:
            session_id: Unique session identifier
        """
        with self._lock:
            if session_id in self._sessions:
                msg_count = len(self._sessions[session_id])
                del self._sessions[session_id]
                if session_id in self._last_activity:
                    del self._last_activity[session_id]
                logger.info(f"Cleared session {session_id} ({msg_count} messages)")
            else:
                logger.debug(f"Session {session_id} not found, nothing to clear")
    
    def cleanup_expired(self):
        """
        Remove expired sessions based on TTL.
        
        Returns:
            Number of sessions cleaned up
        """
        with self._lock:
            now = datetime.now()
            expired = []
            
            for session_id, last_activity in self._last_activity.items():
                if now - last_activity > self.ttl:
                    expired.append(session_id)
            
            # Remove expired sessions
            for session_id in expired:
                msg_count = len(self._sessions.get(session_id, []))
                if session_id in self._sessions:
                    del self._sessions[session_id]
                if session_id in self._last_activity:
                    del self._last_activity[session_id]
                logger.info(f"Cleaned up expired session {session_id} ({msg_count} messages)")
            
            if expired:
                logger.info(f"Cleaned up {len(expired)} expired sessions")
            
            return len(expired)
    
    def get_stats(self) -> Dict:
        """
        Get statistics about current sessions.
        
        Returns:
            Dictionary with session statistics
        """
        with self._lock:
            total_messages = sum(len(msgs) for msgs in self._sessions.values())
            return {
                "total_sessions": len(self._sessions),
                "total_messages": total_messages,
                "avg_messages_per_session": total_messages / len(self._sessions) if self._sessions else 0,
                "oldest_activity": min(self._last_activity.values()) if self._last_activity else None,
                "newest_activity": max(self._last_activity.values()) if self._last_activity else None,
            }
    
    def __len__(self):
        """Return number of active sessions."""
        return len(self._sessions)

