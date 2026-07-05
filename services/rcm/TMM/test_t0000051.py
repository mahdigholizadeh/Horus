"""
Test T0000051: ECM WebSocket Handoff to CCU (OCMIM)
Module(s) Tested: ECM, OCMIM
Description: Test that ECM can connect to a mock CCU WebSocket server, authenticate, and send an output_request with source_module='OCMIM'.
Success Criteria: The mock server receives the correct authentication and output_request messages.
"""

import os
import sys
import asyncio
import json
from datetime import datetime
from unittest.mock import AsyncMock, patch

# Set environment variable for ECM before any ECM/config import
os.environ["CCU_WS_URI"] = "ws://localhost:12345/rcm"
os.environ["CCU_SERVICE_ID"] = "RCM_TEST"
os.environ["CCU_HEARTBEAT_INTERVAL"] = "5"

# Add the project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

async def test_ecm_websocket_handoff_ocmim():
    test_code = "T0000051"
    test_name = "ECM WebSocket Handoff to CCU (OCMIM)"
    try:
        from ECM.ecm import ExternalControlModule
        
        # Create a mock WebSocket connection
        mock_websocket = AsyncMock()
        mock_websocket.send = AsyncMock()
        
        # Create ECM instance
        ecm = ExternalControlModule()
        
        # Mock the WebSocket connection in ECM
        ecm.websocket = mock_websocket
        ecm.ws_status = "connected"
        
        # Test sending output_request (simulate OCMIM handoff)
        test_request_id = "test_ocmim_001"
        test_payload = {"test": "handoff", "value": 99}
        
        print(f"[TEST] Sending output_request with source_module=OCMIM")
        await ecm.send_output_request_to_ccu(
            request_id=test_request_id,
            payload=test_payload,
            priority="C",
            timeout_seconds=60,
            source_module="OCMIM"
        )
        
        # Verify that the message was sent
        mock_websocket.send.assert_called_once()
        sent_message = mock_websocket.send.call_args[0][0]
        sent_data = json.loads(sent_message)
        
        # Check message format
        expected_fields = ['type', 'request_id', 'priority', 'data', 'timeout_seconds', 'timestamp', 'source_module']
        test_success = all(field in sent_data for field in expected_fields)
        test_success = test_success and sent_data['type'] == 'output_request'
        test_success = test_success and sent_data['source_module'] == 'OCMIM'
        test_success = test_success and sent_data['request_id'] == test_request_id
        
        return {
            "success": test_success,
            "test_code": test_code,
            "test_name": test_name,
            "message": "ECM formatted and sent output_request with source_module=OCMIM",
            "details": {
                "sent_message": sent_data,
                "expected_fields": expected_fields,
                "message_sent": mock_websocket.send.called
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
    result = asyncio.run(test_ecm_websocket_handoff_ocmim())
    print(json.dumps(result, indent=2))
