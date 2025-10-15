"""
Event Protocol Utilities

Utilities for creating versioned streaming events with consistent structure.
"""

import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List


# Current event protocol version
EVENT_PROTOCOL_VERSION = "1.0"


def create_event(
    event_type: str,
    data: Optional[Dict[str, Any]] = None,
    session_id: Optional[str] = None,
    error: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a versioned streaming event.
    
    All events include:
    - version: Protocol version (e.g., "1.0")
    - id: Unique event ID (UUID)
    - timestamp: ISO 8601 timestamp
    - type: Event type (start, delta, end, error, tool_calls, cancelled)
    - Additional type-specific data
    
    Args:
        event_type: Type of event (start, delta, end, error, tool_calls, cancelled)
        data: Optional event-specific data
        session_id: Optional session identifier
        error: Optional error message (for error events)
    
    Returns:
        Dictionary containing the versioned event
    
    Example:
        >>> create_event("delta", {"content": "Hello"}, session_id="sess_123")
        {
            "version": "1.0",
            "id": "evt_abc123...",
            "timestamp": "2025-10-14T10:30:00.123456Z",
            "type": "delta",
            "content": "Hello",
            "session_id": "sess_123"
        }
    """
    event = {
        "version": EVENT_PROTOCOL_VERSION,
        "id": f"evt_{uuid.uuid4().hex[:16]}",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "type": event_type,
    }
    
    # Add session_id if provided
    if session_id:
        event["session_id"] = session_id
    
    # Add error if provided
    if error:
        event["error"] = error
    
    # Merge additional data
    if data:
        event.update(data)
    
    return event


def create_start_event(session_id: Optional[str] = None, model: Optional[str] = None) -> Dict[str, Any]:
    """Create a 'start' event indicating stream beginning."""
    data = {}
    if model:
        data["model"] = model
    return create_event("start", data=data, session_id=session_id)


def create_delta_event(
    content: str,
    session_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Create a 'delta' event with incremental content."""
    data = {"content": content}
    if metadata:
        data["metadata"] = metadata
    return create_event("delta", data=data, session_id=session_id)


def create_end_event(
    content: str,
    session_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Create an 'end' event indicating stream completion."""
    data = {"content": content}
    if metadata:
        data["metadata"] = metadata
    return create_event("end", data=data, session_id=session_id)


def create_error_event(
    error: str,
    session_id: Optional[str] = None,
    error_code: Optional[str] = None
) -> Dict[str, Any]:
    """Create an 'error' event."""
    data = {}
    if error_code:
        data["error_code"] = error_code
    return create_event("error", data=data, session_id=session_id, error=error)


def create_tool_calls_event(
    tool_calls: List[Dict[str, Any]],
    session_id: Optional[str] = None
) -> Dict[str, Any]:
    """Create a 'tool_calls' event."""
    return create_event("tool_calls", data={"tool_calls": tool_calls}, session_id=session_id)


def create_cancelled_event(
    session_id: Optional[str] = None,
    reason: Optional[str] = None
) -> Dict[str, Any]:
    """Create a 'cancelled' event."""
    data = {}
    if reason:
        data["reason"] = reason
    return create_event("cancelled", data=data, session_id=session_id)


def validate_event(event: Dict[str, Any]) -> bool:
    """
    Validate that an event conforms to the protocol.
    
    Args:
        event: Event dictionary to validate
    
    Returns:
        True if valid, False otherwise
    """
    required_fields = ["version", "id", "timestamp", "type"]
    
    # Check all required fields exist
    if not all(field in event for field in required_fields):
        return False
    
    # Check version format
    if not isinstance(event["version"], str):
        return False
    
    # Check ID format (should start with evt_)
    if not isinstance(event["id"], str) or not event["id"].startswith("evt_"):
        return False
    
    # Check timestamp is ISO format string
    if not isinstance(event["timestamp"], str):
        return False
    
    # Check type is valid
    valid_types = ["start", "delta", "end", "error", "tool_calls", "cancelled"]
    if event["type"] not in valid_types:
        return False
    
    return True
