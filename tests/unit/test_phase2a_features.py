"""
Tests for Phase 2A features:
- True streaming cancellation
- Streaming history persistence
- API Key authentication
"""
import pytest
import asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient
from unittest.mock import Mock, patch, AsyncMock

# Note: These tests require the app to be running or mocked


class TestStreamingCancellation:
    """Tests for true streaming cancellation functionality."""
    
    @pytest.mark.asyncio
    async def test_websocket_cancel_stops_streaming(self):
        """Test that cancel message stops ongoing streaming."""
        # This would need actual WebSocket client testing
        # Placeholder for implementation
        pass
    
    @pytest.mark.asyncio
    async def test_stream_manager_registration(self):
        """Test that streaming tasks are properly registered."""
        from src.api.stream_manager import StreamTaskManager
        
        manager = StreamTaskManager()
        
        # Create mock task
        async def mock_stream():
            await asyncio.sleep(1)
        
        task = asyncio.create_task(mock_stream())
        await manager.register_task("test-session", task)
        
        assert manager.get_active_count() == 1
        
        # Cancel
        cancelled = await manager.cancel_task("test-session")
        assert cancelled is True
        
        # Verify task was cancelled
        with pytest.raises(asyncio.CancelledError):
            await task
    
    @pytest.mark.asyncio
    async def test_cancel_nonexistent_session(self):
        """Test cancelling a session that doesn't exist."""
        from src.api.stream_manager import StreamTaskManager
        
        manager = StreamTaskManager()
        cancelled = await manager.cancel_task("nonexistent-session")
        assert cancelled is False


class TestStreamingHistoryPersistence:
    """Tests for streaming history persistence functionality."""
    
    @pytest.mark.asyncio
    async def test_streaming_response_persisted_to_history(self):
        """Test that streamed response appears in conversation history."""
        # This would test the full flow:
        # 1. Send streaming message
        # 2. Collect all deltas
        # 3. Query history
        # 4. Verify assembled message is present
        pass
    
    @pytest.mark.asyncio
    async def test_cancelled_stream_partial_persistence(self):
        """Test that partially streamed content is marked as cancelled."""
        # Verify cancelled streams save partial content with [Cancelled] marker
        pass


class TestAPIKeyAuthentication:
    """Tests for API Key authentication middleware."""
    
    def test_missing_api_key_returns_401(self):
        """Test that missing API key returns 401."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from src.api.auth import APIKeyMiddleware
        import os
        
        os.environ["API_KEY_ENABLED"] = "true"
        os.environ["API_KEYS"] = "test-key"
        
        app = FastAPI()
        app.add_middleware(APIKeyMiddleware)
        
        @app.get("/protected")
        async def protected_route():
            return {"message": "success"}
        
        client = TestClient(app)
        
        response = client.get("/protected")
        assert response.status_code == 401
        assert "api key" in response.json()["detail"].lower()
    
    def test_invalid_api_key_returns_403(self):
        """Test that invalid API key is rejected."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from src.api.auth import APIKeyMiddleware
        import os
        
        os.environ["API_KEYS"] = "valid-key-123"
        os.environ["API_KEY_ENABLED"] = "true"
        
        app = FastAPI()
        app.add_middleware(APIKeyMiddleware)
        
        @app.get("/protected")
        async def protected_route():
            return {"message": "success"}
        
        client = TestClient(app)
        
        response = client.get("/protected", headers={"X-API-Key": "invalid-key"})
        assert response.status_code == 403
    
    def test_valid_api_key_grants_access(self):
        """Test that valid API key allows access."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from src.api.auth import APIKeyMiddleware
        import os
        
        os.environ["API_KEYS"] = "valid-key-123,another-key"
        os.environ["API_KEY_ENABLED"] = "true"
        
        app = FastAPI()
        app.add_middleware(APIKeyMiddleware)
        
        @app.get("/protected")
        async def protected_route():
            return {"message": "success"}
        
        client = TestClient(app)
        
        response = client.get("/protected", headers={"X-API-Key": "valid-key-123"})
        assert response.status_code == 200
        assert response.json()["message"] == "success"
    
    def test_health_endpoint_exempt_from_auth(self):
        """Test that health endpoint doesn't require API key."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from src.api.auth import APIKeyMiddleware
        import os
        
        os.environ["API_KEY_ENABLED"] = "true"
        os.environ["API_KEYS"] = "some-key"
        
        app = FastAPI()
        app.add_middleware(APIKeyMiddleware)
        
        @app.get("/health")
        async def health():
            return {"status": "healthy"}
        
        client = TestClient(app)
        
        # Should work without API key
        response = client.get("/health")
        assert response.status_code == 200
    
    def test_auth_disabled_allows_all_requests(self):
        """Test that disabling auth allows all requests through."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from src.api.auth import APIKeyMiddleware
        import os
        
        os.environ["API_KEY_ENABLED"] = "false"
        
        app = FastAPI()
        app.add_middleware(APIKeyMiddleware)
        
        @app.get("/protected")
        async def protected_route():
            return {"message": "success"}
        
        client = TestClient(app)
        
        # Should work without API key when disabled
        response = client.get("/protected")
        assert response.status_code == 200


class TestEventProtocol:
    """Tests for event versioning and protocol compliance."""
    
    def test_streaming_events_include_version(self):
        """Test that streaming events include version, id, timestamp fields."""
        from src.api.event_utils import (
            create_start_event, create_delta_event, create_end_event,
            create_error_event, create_tool_calls_event, create_cancelled_event,
            validate_event
        )
        
        # Test start event
        start_event = create_start_event(session_id="test_123", model="gpt-4")
        assert "version" in start_event
        assert start_event["version"] == "1.0"
        assert "id" in start_event
        assert start_event["id"].startswith("evt_")
        assert "timestamp" in start_event
        assert start_event["type"] == "start"
        assert start_event["session_id"] == "test_123"
        assert start_event["model"] == "gpt-4"
        assert validate_event(start_event)
        
        # Test delta event
        delta_event = create_delta_event(content="Hello", session_id="test_123")
        assert delta_event["version"] == "1.0"
        assert delta_event["id"].startswith("evt_")
        assert "timestamp" in delta_event
        assert delta_event["type"] == "delta"
        assert delta_event["content"] == "Hello"
        assert validate_event(delta_event)
        
        # Test end event
        end_event = create_end_event(content="Full response", session_id="test_123")
        assert end_event["version"] == "1.0"
        assert end_event["id"].startswith("evt_")
        assert "timestamp" in end_event
        assert end_event["type"] == "end"
        assert end_event["content"] == "Full response"
        assert validate_event(end_event)
        
        # Test error event
        error_event = create_error_event(error="Something failed", session_id="test_123", error_code="ERR_500")
        assert error_event["version"] == "1.0"
        assert error_event["type"] == "error"
        assert error_event["error"] == "Something failed"
        assert error_event["error_code"] == "ERR_500"
        assert validate_event(error_event)
        
        # Test tool_calls event
        tool_calls_event = create_tool_calls_event(
            tool_calls=[{"name": "search", "args": {"q": "test"}}],
            session_id="test_123"
        )
        assert tool_calls_event["version"] == "1.0"
        assert tool_calls_event["type"] == "tool_calls"
        assert len(tool_calls_event["tool_calls"]) == 1
        assert validate_event(tool_calls_event)
        
        # Test cancelled event
        cancelled_event = create_cancelled_event(session_id="test_123", reason="User cancelled")
        assert cancelled_event["version"] == "1.0"
        assert cancelled_event["type"] == "cancelled"
        assert cancelled_event["reason"] == "User cancelled"
        assert validate_event(cancelled_event)
    
    def test_event_ids_are_unique(self):
        """Test that each event gets a unique ID."""
        from src.api.event_utils import create_delta_event
        
        event1 = create_delta_event("content1")
        event2 = create_delta_event("content2")
        event3 = create_delta_event("content3")
        
        assert event1["id"] != event2["id"]
        assert event2["id"] != event3["id"]
        assert event1["id"] != event3["id"]
    
    def test_event_validation_rejects_invalid(self):
        """Test that event validation rejects malformed events."""
        from src.api.event_utils import validate_event
        
        # Missing required fields
        assert not validate_event({"type": "delta"})
        assert not validate_event({"version": "1.0", "id": "evt_123"})
        
        # Invalid type
        assert not validate_event({
            "version": "1.0",
            "id": "evt_123",
            "timestamp": "2025-10-14T10:00:00Z",
            "type": "invalid_type"
        })
        
        # Invalid ID format
        assert not validate_event({
            "version": "1.0",
            "id": "bad_id",
            "timestamp": "2025-10-14T10:00:00Z",
            "type": "delta"
        })


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
