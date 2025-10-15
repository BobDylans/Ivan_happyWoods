"""
Integration Tests for Phase 2C Event Protocol

Tests end-to-end event versioning through the full stack.
"""

import pytest
import json
from unittest.mock import Mock, AsyncMock, patch


class TestEventProtocolIntegration:
    """Integration tests for versioned event protocol."""
    
    @pytest.mark.asyncio
    async def test_agent_stream_produces_versioned_events(self):
        """Test that agent streaming produces properly versioned events."""
        # This test verifies event structure without needing full agent setup
        from src.api.event_utils import (
            create_start_event, create_delta_event, create_end_event
        )
        
        # Simulate agent streaming
        async def simulated_agent_stream(session_id):
            yield create_start_event(session_id=session_id, model="gpt-4")
            yield create_delta_event("Hello ", session_id=session_id)
            yield create_delta_event("world", session_id=session_id)
            yield create_end_event("Hello world", session_id=session_id)
        
        events = []
        async for event in simulated_agent_stream("test_123"):
            events.append(event)
        
        # Verify we got all events
        assert len(events) == 4
        
        # Verify all events are versioned
        for event in events:
            assert "version" in event
            assert event["version"] == "1.0"
            assert "id" in event
            assert event["id"].startswith("evt_")
            assert "timestamp" in event
            assert "type" in event
            assert "session_id" in event
            assert event["session_id"] == "test_123"
        
        # Verify event types
        assert events[0]["type"] == "start"
        assert events[1]["type"] == "delta"
        assert events[2]["type"] == "delta"
        assert events[3]["type"] == "end"
        
        # Verify content
        assert events[1]["content"] == "Hello "
        assert events[2]["content"] == "world"
        assert events[3]["content"] == "Hello world"
    
    def test_event_serialization_for_sse(self):
        """Test that versioned events serialize correctly for SSE."""
        from src.api.event_utils import create_delta_event
        
        event = create_delta_event("Test content", session_id="sess_123")
        
        # SSE format: data: <json>\n\n
        sse_line = f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        
        # Verify it's valid SSE format
        assert sse_line.startswith("data: ")
        assert sse_line.endswith("\n\n")
        
        # Verify JSON is valid
        json_part = sse_line[6:-2]  # Strip "data: " and "\n\n"
        parsed = json.loads(json_part)
        
        assert parsed["version"] == "1.0"
        assert parsed["type"] == "delta"
        assert parsed["content"] == "Test content"
        assert parsed["session_id"] == "sess_123"
    
    def test_event_serialization_for_websocket(self):
        """Test that versioned events serialize correctly for WebSocket."""
        from src.api.event_utils import create_error_event
        
        event = create_error_event(
            error="Connection timeout",
            session_id="sess_456",
            error_code="TIMEOUT"
        )
        
        # WebSocket typically sends JSON directly
        json_str = json.dumps(event)
        parsed = json.loads(json_str)
        
        assert parsed["version"] == "1.0"
        assert parsed["type"] == "error"
        assert parsed["error"] == "Connection timeout"
        assert parsed["error_code"] == "TIMEOUT"
        assert parsed["session_id"] == "sess_456"
    
    def test_legacy_client_compatibility(self):
        """Test that versioned events don't break legacy clients."""
        from src.api.event_utils import create_delta_event
        
        event = create_delta_event("Legacy test", session_id="sess_789")
        
        # Legacy client only checks 'type' and 'content'
        assert event["type"] == "delta"  # Old field still present
        assert event["content"] == "Legacy test"  # Old field still present
        
        # New fields are additive
        assert "version" in event
        assert "id" in event
        assert "timestamp" in event
        
        # Legacy code that ignores unknown fields should work
        legacy_handler = {
            "delta": lambda e: e["content"].upper(),
            "error": lambda e: f"Error: {e.get('error', 'Unknown')}"
        }
        
        result = legacy_handler[event["type"]](event)
        assert result == "LEGACY TEST"
    
    def test_event_ordering_preserved(self):
        """Test that event IDs and timestamps maintain chronological order."""
        from src.api.event_utils import create_delta_event
        import time
        
        events = []
        for i in range(5):
            event = create_delta_event(f"Chunk {i}", session_id="sess_order")
            events.append(event)
            time.sleep(0.001)  # Small delay to ensure different timestamps
        
        # Verify IDs are unique
        ids = [e["id"] for e in events]
        assert len(ids) == len(set(ids)), "Event IDs should be unique"
        
        # Verify timestamps are in chronological order
        timestamps = [e["timestamp"] for e in events]
        sorted_timestamps = sorted(timestamps)
        assert timestamps == sorted_timestamps, "Timestamps should be chronological"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
