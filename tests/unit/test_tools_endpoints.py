"""
Tests for MCP tools API endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from src.api.main import app
from src.mcp.init_tools import initialize_default_tools


class TestToolsEndpoints:
    """Test tools API endpoints."""
    
    def setup_method(self):
        """Setup test client."""
        # Initialize tools before testing
        initialize_default_tools()
        
        self.client = TestClient(app)
        self.headers = {"X-API-Key": "test_api_key_12345"}
    
    def test_list_tools(self):
        """Test listing all available tools."""
        response = self.client.get("/api/v1/tools/", headers=self.headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "tools" in data
        assert "total" in data
        assert data["total"] > 0
        
        # Check tool structure
        if data["tools"]:
            tool = data["tools"][0]
            assert "name" in tool
            assert "description" in tool
            assert "parameters" in tool
    
    def test_get_tool_schemas(self):
        """Test getting OpenAI-compatible schemas."""
        response = self.client.get("/api/v1/tools/schemas", headers=self.headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "schemas" in data
        assert "total" in data
        assert data["total"] > 0
        
        # Check schema structure (OpenAI format)
        if data["schemas"]:
            schema = data["schemas"][0]
            assert "type" in schema
            assert schema["type"] == "function"
            assert "function" in schema
            assert "name" in schema["function"]
            assert "description" in schema["function"]
            assert "parameters" in schema["function"]
    
    def test_execute_calculator_tool(self):
        """Test executing calculator tool."""
        response = self.client.post(
            "/api/v1/tools/execute/calculator",
            json={"expression": "2 + 2"},
            headers=self.headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["tool"] == "calculator"
        assert "result" in data
        assert data["result"]["success"] is True
        # Result is in data field as a dict with expression and result
        assert data["result"]["data"]["result"] == 4
    
    def test_execute_time_tool(self):
        """Test executing time tool."""
        response = self.client.post(
            "/api/v1/tools/execute/get_time",
            json={"format": "date"},
            headers=self.headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["tool"] == "get_time"
        assert "result" in data
        assert data["result"]["success"] is True
        # Check for formatted field
        assert "formatted" in data["result"]["data"]
    
    @pytest.mark.asyncio
    async def test_execute_weather_tool(self):
        """Test executing weather tool (mock)."""
        response = self.client.post(
            "/api/v1/tools/execute/get_weather",
            json={"location": "Beijing"},
            headers=self.headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["tool"] == "get_weather"
        assert "result" in data
        assert data["result"]["success"] is True
        assert "location" in data["result"]["data"]
        assert "temperature" in data["result"]["data"]
    
    def test_execute_invalid_tool(self):
        """Test executing non-existent tool."""
        response = self.client.post(
            "/api/v1/tools/execute/nonexistent_tool",
            json={},
            headers=self.headers
        )
        
        assert response.status_code == 200  # Returns 200 with error in body
        data = response.json()
        
        assert data["success"] is False
        assert "error" in data
    
    def test_execute_calculator_with_invalid_expression(self):
        """Test calculator with invalid expression."""
        response = self.client.post(
            "/api/v1/tools/execute/calculator",
            json={"expression": "import os"},
            headers=self.headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should fail due to forbidden keyword
        assert data["success"] is False or data["result"]["success"] is False
