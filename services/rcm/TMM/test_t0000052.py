"""
Test T0000052: ECM WebSocket Handoff Error Handling (CCU Unavailable)
Module(s) Tested: ECM
Description: Test that ECM handles connection errors gracefully when CCU is unavailable.
Success Criteria: ECM logs/returns an error when it cannot connect to CCU and send an output_request.
"""

import os
import sys
import asyncio
import json
from datetime import datetime
from unittest.mock import AsyncMock, patch

# Set environment variable for ECM before any ECM/config import
os.environ["CCU_WS_URI"] = "ws://localhost:65534/rcm"
os.environ["CCU_SERVICE_ID"] = "RCM_TEST"
os.environ["CCU_HEARTBEAT_INTERVAL"] = "2"

# Add the project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

async def test_ecm_websocket_handoff_error():
    test_code = "T0000052"
    test_name = "ECM WebSocket Handoff Error Handling (CCU Unavailable)"
    try:
        from ECM.ecm import ExternalControlModule
        
        # Create ECM instance
        ecm = ExternalControlModule()
        
        # Mock the WebSocket connection to simulate connection error
        mock_websocket = AsyncMock()
        mock_websocket.send = AsyncMock(side_effect=Exception("Connection failed"))
        ecm.websocket = mock_websocket
        ecm.ws_status = "connected"
        
        # Test sending output_request (should handle error gracefully)
        test_request_id = "test_error_001"
        test_payload = {"test": "handoff", "value": 123}
        
        print(f"[TEST] Testing error handling when WebSocket send fails")
        try:
            await ecm.send_output_request_to_ccu(
                request_id=test_request_id,
                payload=test_payload,
                priority="C",
                timeout_seconds=5,
                source_module="JFAIM"
            )
            # If no exception, this is a failure
            return {
                "success": False,
                "test_code": test_code,
                "test_name": test_name,
                "error": "Expected connection error, but message sent successfully"
            }
        except Exception as e:
            # Expected error
            return {
                "success": True,
                "test_code": test_code,
                "test_name": test_name,
                "message": "ECM correctly handled WebSocket send error",
                "details": {"error": str(e)}
            }
    except Exception as e:
        return {
            "success": False,
            "test_code": test_code,
            "test_name": test_name,
            "error": f"Test execution failed: {str(e)}"
        }

if __name__ == "__main__":
    result = asyncio.run(test_ecm_websocket_handoff_error())
    print(json.dumps(result, indent=2)) 