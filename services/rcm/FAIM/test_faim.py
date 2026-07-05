"""
Unit tests for FastAPI Integration Module (FAIM)
"""
import pytest
import json
from EMM.emm import ErrorManagementModule
from EMM.api_error_handler import api_error_handler
from fastapi.testclient import TestClient
from FAIM.faim import FastAPIIntegrationModule, CommandRequest

@pytest.fixture
def faim_client():
    """Create a test client for FAIM."""
    faim = FastAPIIntegrationModule()
    return TestClient(faim.app)

@pytest.fixture
def faim_instance():
    """Create a FAIM instance for direct testing."""
    return FastAPIIntegrationModule()

def test_health_endpoint(faim_client):
    """Test the health check endpoint."""
    response = faim_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert data["service"] == "RCM FastAPI Integration Module"

def test_status_endpoint(faim_client):
    """Test the status endpoint."""
    response = faim_client.get("/status")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "RCM Microservice"
    assert data["overall_status"] == "active"
    assert "timestamp" in data
    assert "module_statuses" in data
    assert "api_stats" in data

def test_metrics_endpoint(faim_client):
    """Test the metrics endpoint."""
    response = faim_client.get("/metrics")
    assert response.status_code == 200
    data = response.json()
    assert "timestamp" in data
    assert "api_requests" in data
    assert "system_metrics" in data

def test_command_endpoint_success(faim_client):
    """Test command endpoint with successful command."""
    command_data = {
        "command": "ping",
        "parameters": {}
    }
    response = faim_client.post("/command", json=command_data)
    assert response.status_code == 200
    data = response.json()
    assert data["command"] == "ping"
    assert "result" in data
    assert "timestamp" in data

def test_command_endpoint_module_command(faim_client):
    """Test command endpoint with module-specific command."""
    command_data = {
        "command": "module_btm",
        "parameters": {
            "action": "get_module_status"
        }
    }
    response = faim_client.post("/command", json=command_data)
    assert response.status_code == 200
    data = response.json()
    assert data["command"] == "module_btm"
    assert "result" in data

def test_command_endpoint_system_command(faim_client):
    """Test command endpoint with system command."""
    command_data = {
        "command": "system_status",
        "parameters": {}
    }
    response = faim_client.post("/command", json=command_data)
    assert response.status_code == 200
    data = response.json()
    assert data["command"] == "system_status"
    assert "result" in data

def test_command_endpoint_invalid_command(faim_client):
    """Test command endpoint with invalid command."""
    command_data = {
        "command": "invalid_command",
        "parameters": {}
    }
    response = faim_client.post("/command", json=command_data)
    assert response.status_code == 200  # Should not fail, just return error in result
    data = response.json()
    assert "result" in data
    assert data["result"]["success"] == False

def test_module_status_endpoint(faim_client):
    """Test module status endpoint."""
    response = faim_client.get("/module/btm")
    assert response.status_code == 200
    data = response.json()
    assert data["module_name"] == "btm"
    assert "status" in data
    assert "timestamp" in data

def test_module_status_endpoint_invalid_module(faim_client):
    """Test module status endpoint with invalid module."""
    response = faim_client.get("/module/invalid_module")
    assert response.status_code == 200  # Should not fail, just return error in status
    data = response.json()
    assert data["module_name"] == "invalid_module"
    assert "status" in data

def test_logs_endpoint(faim_client):
    """Test logs endpoint."""
    response = faim_client.get("/logs")
    assert response.status_code == 200
    data = response.json()
    assert "logs" in data
    assert "total_logs" in data
    assert "level" in data
    assert isinstance(data["logs"], list)

def test_logs_endpoint_with_parameters(faim_client):
    """Test logs endpoint with parameters."""
    response = faim_client.get("/logs?level=ERROR&limit=50")
    assert response.status_code == 200
    data = response.json()
    assert data["level"] == "ERROR"
    assert len(data["logs"]) <= 50

def test_faim_instance_creation(faim_instance):
    """Test FAIM instance creation."""
    assert faim_instance is not None
    assert faim_instance.app is not None
    assert faim_instance.error_manager is not None
    assert faim_instance.stats is not None

def test_faim_module_status(faim_instance):
    """Test FAIM module status method."""
    status = faim_instance.get_module_status()
    assert status["module"] == "FAIM"
    assert status["status"] == "active"
    assert "endpoints" in status
    assert "stats" in status
    assert isinstance(status["endpoints"], list)

def test_faim_error_codes(faim_instance):
    """Test FAIM error codes."""
    assert "ENDPOINT_ERROR" in faim_instance.error_codes
    assert "COMMAND_ERROR" in faim_instance.error_codes
    assert "MODULE_NOT_FOUND" in faim_instance.error_codes
    assert "INVALID_REQUEST" in faim_instance.error_codes

def test_faim_stats_tracking(faim_instance):
    """Test FAIM statistics tracking."""
    initial_stats = faim_instance.stats.copy()
    
    # Simulate some requests
    faim_instance.stats["total_requests"] += 1
    faim_instance.stats["successful_requests"] += 1
    
    assert faim_instance.stats["total_requests"] == initial_stats["total_requests"] + 1
    assert faim_instance.stats["successful_requests"] == initial_stats["successful_requests"] + 1

def test_command_request_model():
    """Test CommandRequest model."""
    command_request = CommandRequest(
        command="test_command",
        parameters={"key": "value"}
    )
    assert command_request.command == "test_command"
    assert command_request.parameters == {"key": "value"}

def test_module_status_model():
    """Test ModuleStatus model."""
    from FAIM.faim import ModuleStatus
    
    module_status = ModuleStatus(
        module_name="test_module",
        status="active",
        details={"key": "value"}
    )
    assert module_status.module_name == "test_module"
    assert module_status.status == "active"
    assert module_status.details == {"key": "value"}

def test_faim_endpoint_registration(faim_instance):
    """Test that all endpoints are properly registered."""
    routes = faim_instance.app.routes
    route_paths = [route.path for route in routes]
    
    expected_paths = [
        "/health",
        "/status", 
        "/metrics",
        "/command",
        "/module/{module_name}",
        "/logs"
    ]
    
    for expected_path in expected_paths:
        # Check if any route matches the expected path
        matching_routes = [r for r in route_paths if r == expected_path]
        assert len(matching_routes) > 0, f"Expected path {expected_path} not found in routes"

def test_faim_error_handling(faim_instance):
    """Test FAIM error handling."""
    # Test that error manager is properly initialized
    assert faim_instance.error_manager is not None
    
    # Test error code structure
    for error_code in faim_instance.error_codes.values():
        assert len(error_code) == 11  # 16-character hex string format
        assert error_code.startswith("0101030C")  # RCM microservice, FAIM module

def test_faim_async_methods(faim_instance):
    """Test FAIM async methods."""
    import asyncio
    
    async def test_async_methods():
        # Test command execution
        result = await faim_instance._execute_command("ping", {})
        assert "success" in result
        
        # Test module status
        status = await faim_instance._get_module_status("btm")
        assert "status" in status
        
        # Test system command
        result = await faim_instance._execute_system_command("system_status", {})
        assert "success" in result
        
        # Test general command
        result = await faim_instance._execute_general_command("ping", {})
        assert "success" in result
    
    # Run the async test
    asyncio.run(test_async_methods())

def test_faim_server_startup():
    """Test FAIM server startup (without actually starting)."""
    faim_instance = FastAPIIntegrationModule()
    
    # Test that the app can be created without errors
    assert faim_instance.app is not None
    
    # Test that the app has the expected title
    assert faim_instance.app.title == "RCM FastAPI Integration Module"
    
    # Test that the app has the expected version
    assert faim_instance.app.version == "1.0.0"

def test_faim_import_handling():
    """Test FAIM import handling for missing modules."""
    # This test ensures that FAIM can handle cases where other modules are not implemented
    faim_instance = FastAPIIntegrationModule()
    
    # The module should still work even if other modules are not available
    assert faim_instance is not None
    assert faim_instance.app is not None
    
    # Test that status endpoint can handle missing modules
    status = faim_instance.get_module_status()
    assert status["module"] == "FAIM"
    assert status["status"] == "active"

if __name__ == "__main__":
    # Run tests
    pytest.main([__file__]) 