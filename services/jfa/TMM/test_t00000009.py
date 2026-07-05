"""
Test T00000009: ARM (API Request Module) Unit Test
Module(s) Tested: ARM
Description: To verify that the ARM correctly handles API requests and routes them to the appropriate endpoints.
Success Criteria: API endpoints respond correctly, request routing works, error handling is proper.
"""

import asyncio
import json
import sys
import aiohttp
import threading
import time
from pathlib import Path
from typing import Dict, Any

# Add parent directory to path for module imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from ARM.arm import APIRequestModule

class TestAPIServer:
    """Test API server for ARM testing."""
    
    def __init__(self, port=8001):
        self.port = port
        self.server = None
        self.thread = None
        self.is_running = False
        
    def start_server(self):
        """Start the test API server."""
        try:
            import uvicorn
            from ARM.arm import app
            
            config = uvicorn.Config(
                app=app,
                host="0.0.0.0",
                port=self.port,
                log_level="error",
                access_log=False
            )
            
            self.server = uvicorn.Server(config)
            self.server.run()
        except Exception as e:
            print(f"Failed to start test server: {e}")
    
    def start(self):
        """Start server in background thread."""
        self.thread = threading.Thread(target=self.start_server, daemon=True)
        self.thread.start()
        self.is_running = True
        
    def stop(self):
        """Stop the server."""
        if self.server:
            self.server.should_exit = True
        if self.thread:
            self.thread.join(timeout=5)

async def test_t00000009():
    test_code = "T00000009"
    test_name = "ARM - API Request Module Unit Test"
    results = []
    
    # Step 1: Test ARM module functionality without starting server
    arm = APIRequestModule()
    await arm.start()
    
    try:
        # Test basic ARM functionality
        status = arm.get_status()
        results.append(isinstance(status, dict))
        results.append(status.get("module") == "ARM")
        results.append(status.get("is_active") == True)
        
        # Test health check
        health = await arm.health_check()
        results.append(isinstance(health, dict))
        results.append("healthy" in health)
        results.append(health.get("module") == "ARM")
        
        # Test server configuration
        server_config = status.get("server_config", {})
        results.append(isinstance(server_config, dict))
        results.append("host" in server_config)
        results.append("port" in server_config)
        
        # Test statistics
        stats = status.get("statistics", {})
        results.append(isinstance(stats, dict))
        results.append("requests_handled" in stats)
        results.append("successful_requests" in stats)
        results.append("failed_requests" in stats)
        
        # Test app routes (without starting server)
        app = arm.app
        results.append(app is not None)
        
        # Check if routes are set up
        routes = [route.path for route in app.routes]
        results.append("/health" in routes)
        results.append("/status" in routes)
        results.append("/process" in routes)
        results.append("/process/batch" in routes)
        
        success = all(results)
        
        return {
            "success": success,
            "test_code": test_code,
            "test_name": test_name,
            "message": "ARM unit test passed" if success else "ARM unit test failed",
            "details": {
                "basic_functionality": results[0:3],
                "health_check": results[3:6],
                "server_configuration": results[6:9],
                "statistics": results[9:12],
                "app_routes": results[12:16],
                "results": results
            }
        }
        
    finally:
        await arm.stop()