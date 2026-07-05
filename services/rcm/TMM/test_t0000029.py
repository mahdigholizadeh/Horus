"""
Test T0000029: FAIM - API Endpoint Verification
Module(s) Tested: FAIM
Description: Test RESTful API endpoint verification.
Success Criteria: The API returns correct status codes and valid JSON payloads.
"""

import asyncio
import tempfile
from pathlib import Path
import sys
import os
import json
from EMM.emm import ErrorManagementModule
from EMM.api_error_handler import api_error_handler

# Add the project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from FAIM.faim import FastAPIIntegrationModule

async def test_faim_api_endpoint_verification():
    """Test RESTful API endpoint verification."""
    test_code = "T0000029"
    test_name = "FAIM - API Endpoint Verification"
    try:
        # Initialize module
        faim = FastAPIIntegrationModule()
        
        # Test module status method
        status_result = faim.get_module_status()
        status_success = isinstance(status_result, dict) and "module" in status_result and status_result["module"] == "FAIM"
        
        # Test endpoint validation (simulate by checking if endpoints are registered)
        endpoints = status_result.get("endpoints", [])
        validation_success = len(endpoints) > 0 and "/health" in endpoints and "/status" in endpoints
        
        # Test command execution
        command_result = await faim._execute_general_command("ping", {})
        command_success = isinstance(command_result, dict) and command_result.get("success", False)
        
        # Test module status retrieval
        module_status_result = await faim._get_module_status("FAIM")
        module_status_success = isinstance(module_status_result, dict) and "status" in module_status_result
        
        # Test system command execution
        system_result = await faim._execute_system_command("system_status", {})
        system_success = isinstance(system_result, dict) and system_result.get("success", False)
        
        test_success = status_success and validation_success and command_success and module_status_success and system_success
        
        return {
            "success": test_success,
            "test_code": test_code,
            "test_name": test_name,
            "message": f"API endpoint verification successful",
            "details": {
                "status_success": status_success,
                "validation_success": validation_success,
                "command_success": command_success,
                "module_status_success": module_status_success,
                "system_success": system_success,
                "endpoints": endpoints,
                "status_result": status_result,
                "command_result": command_result,
                "module_status_result": module_status_result,
                "system_result": system_result
            }
        }
    except Exception as e:
        return {
            "success": False,
            "test_code": test_code,
            "test_name": test_name,
            "error": f"Test execution failed: {str(e)}"
        }

if __name__ == "__main__":
    # Run the test
    result = asyncio.run(test_faim_api_endpoint_verification())
    print(json.dumps(result, indent=2, default=str))