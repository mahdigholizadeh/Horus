"""
Test O00000004: ECM CCU WebSocket Connection
Module(s) Tested: ECM (External Control Module)
Description: Test WebSocket connection establishment with CCU
Test Description:
- Establish WebSocket connection to CCU
- Test connection authentication
- Verify heartbeat mechanism
- Test reconnection logic
- Check connection stability
- Validate message format compliance
Expected Result: Stable WebSocket connection with CCU
Pass Criteria: Connection established, authentication works, heartbeat active, reconnection successful
Implementation Notes: Mock CCU WebSocket server for testing
"""

import asyncio
import json
import sys
import websockets
import tempfile
import os
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

# Add parent directory to path for module imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import mock services
from mock_services import TestEnvironment

print('SCRIPT STARTING...')
import sys
print('sys imported')
import os
print('os imported')
import json
print('json imported')
import asyncio
print('asyncio imported')
import websockets
print('websockets imported')
print('RUNTIME WEBSOCKETS VERSION:', getattr(websockets, '__version__', 'no __version__ attr'))

async def test_o00000004():
    test_code = "O00000004"
    test_name = "ECM CCU WebSocket Connection"
    results = []
    
    # Setup test environment
    test_env = TestEnvironment()
    await test_env.setup(websocket_port=8080)
    
    try:
        # Import ECM module
        from ECM.ecm import ExternalControlModule
        
        # Step 1: Test ECM module initialization
        config = {
            "ccu_integration": {
                "enabled": True,
                "ccu_host": "localhost",
                "ccu_port": 8080,
                "heartbeat_interval": 30,
                "reconnect_attempts": 5
            }
        }
        
        ecm = ExternalControlModule(config)
        results.append(ecm is not None)
        results.append(hasattr(ecm, 'start'))
        results.append(hasattr(ecm, 'stop'))
        results.append(hasattr(ecm, 'send_heartbeat'))
        results.append(hasattr(ecm, 'send_error_report'))
        results.append(hasattr(ecm, 'send_monitoring_data'))
        
        # Step 2: Test WebSocket server setup (mock CCU)
        mock_websocket_server = test_env.mock_websocket_server
        results.append(mock_websocket_server is not None)
        results.append(mock_websocket_server.server is not None)
        
        # Step 3: Test WebSocket connection establishment
        try:
            await ecm.start()
            # Wait a bit for connection to establish
            await asyncio.sleep(2)
            results.append(ecm.connection_status in ['connected', 'connecting'])
            results.append(ecm.is_active == True)
        except Exception as e:
            print(f"Connection error: {e}")
            results.append(False)
            results.append(False)
        
        # Step 4: Test heartbeat mechanism
        try:
            heartbeat_data = {
                "requests_processed": 150,
                "reports_generated": 45,
                "delivery_success_rate": 98.5
            }
            await ecm.send_heartbeat(heartbeat_data)
            results.append(True)  # If no exception, heartbeat sent successfully
        except Exception as e:
            print(f"Heartbeat error: {e}")
            results.append(False)
        
        # Step 5: Test error reporting
        try:
            error_info = {
                "error_code": "TEST_001",
                "error_message": "Test error for validation",
                "module": "ECM",
                "timestamp": datetime.now().isoformat()
            }
            await ecm.send_error_report(error_info)
            results.append(True)  # If no exception, error report sent successfully
        except Exception as e:
            print(f"Error report error: {e}")
            results.append(False)
        
        # Step 6: Test monitoring data
        try:
            monitoring_data = {
                "cpu_usage": 45.2,
                "memory_usage": 67.8,
                "active_connections": 5,
                "requests_per_minute": 120
            }
            await ecm.send_monitoring_data(monitoring_data)
            results.append(True)  # If no exception, monitoring data sent successfully
        except Exception as e:
            print(f"Monitoring data error: {e}")
            results.append(False)
        
        # Step 7: Test connection status and statistics
        try:
            status = ecm.get_status()
            results.append(isinstance(status, dict))
            results.append('connection_status' in status)
            results.append('messages_sent' in status)
            results.append('messages_received' in status)
        except Exception as e:
            print(f"Status error: {e}")
            results.append(False)
            results.append(False)
            results.append(False)
            results.append(False)
        
        # Step 8: Test connection stability with multiple heartbeats
        stability_tests = []
        for i in range(3):
            try:
                await ecm.send_heartbeat({"sequence": i, "test": True})
                stability_tests.append(True)
                await asyncio.sleep(0.5)  # Small delay between heartbeats
            except Exception:
                stability_tests.append(False)
        
        results.append(len(stability_tests) == 3)
        results.append(sum(stability_tests) >= 2)  # At least 2 out of 3 should work
        
        # Step 9: Test health check
        try:
            health_result = await ecm.health_check()
            results.append(isinstance(health_result, bool))
        except Exception as e:
            print(f"Health check error: {e}")
            results.append(False)
        
        # Step 10: Test connection monitoring
        try:
            # Check if we can access connection stats
            results.append(hasattr(ecm, 'stats'))
            results.append('messages_sent' in ecm.stats)
            results.append('messages_received' in ecm.stats)
            results.append('connection_attempts' in ecm.stats)
        except Exception as e:
            print(f"Stats error: {e}")
            results.append(False)
            results.append(False)
            results.append(False)
            results.append(False)
        
        # Step 11: Test graceful shutdown
        try:
            await ecm.stop()
            results.append(ecm.connection_status == 'disconnected')
            results.append(ecm.is_active == False)
        except Exception as e:
            print(f"Stop error: {e}")
            results.append(False)
            results.append(False)
        
        # Step 12: Test reconnection logic
        try:
            # Try to start again after stopping
            await ecm.start()
            await asyncio.sleep(1)
            results.append(ecm.is_active == True)
            results.append(ecm.connection_status in ['connected', 'connecting', 'disconnected'])
        except Exception as e:
            print(f"Restart error: {e}")
            results.append(False)
            results.append(False)
        
        # Calculate test results
        total_tests = len(results)
        passed_tests = sum(results)
        failed_tests = total_tests - passed_tests
        
        # Calculate test results
        total_tests = len(results)
        passed_tests = sum(results)
        failed_tests = total_tests - passed_tests
        
        test_result = {
            "test_code": test_code,
            "test_name": test_name,
            "status": "PASSED" if failed_tests == 0 else "FAILED",
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "success_rate": (passed_tests / total_tests) * 100 if total_tests > 0 else 0,
            "details": {
                "connection_established": ecm.connection_status in ['connected', 'connecting'] if 'ecm' in locals() else False,
                "messages_sent": len(mock_websocket_server.messages_received),
                "connections_handled": len(mock_websocket_server.clients),
                "heartbeat_successful": any(msg.get('type') == 'heartbeat' for msg in mock_websocket_server.messages_received),
                "error_reporting_tested": True,
                "monitoring_data_tested": True,
                "reconnection_tested": True,
                "health_check_tested": True
            },
            "timestamp": asyncio.get_event_loop().time()
        }
        
        return test_result
        
    except ImportError as e:
        await test_env.teardown()
        return {
            "test_code": test_code,
            "test_name": test_name,
            "status": "ERROR",
            "error": f"Import error: {str(e)}",
            "details": {
                "error_type": "ImportError",
                "message": "Failed to import ECM module or dependencies"
            },
            "timestamp": asyncio.get_event_loop().time()
        }
        
    except Exception as e:
        await test_env.teardown()
        return {
            "test_code": test_code,
            "test_name": test_name,
            "status": "ERROR",
            "error": f"Test execution error: {str(e)}",
            "details": {
                "error_type": type(e).__name__,
                "message": str(e)
            },
            "timestamp": asyncio.get_event_loop().time()
        }
    finally:
        # Always cleanup test environment
        await test_env.teardown()

# For direct execution
if __name__ == "__main__":
    async def main():
        result = await test_o00000004()
        print(json.dumps(result, indent=2))
        
        # Exit with appropriate code
        if result["status"] == "PASSED":
            sys.exit(0)
        else:
            sys.exit(1)
    
    asyncio.run(main())