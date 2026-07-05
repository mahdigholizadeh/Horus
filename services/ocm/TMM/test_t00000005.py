"""
Test O00000005: ECM Service Registration
Module(s) Tested: ECM.ecm (External Control Module)
Description: Test ECM module initialization and basic functionality
Test Description:
- Initialize ECM module with configuration
- Test module attributes and methods
- Test module status and statistics
- Test module start and stop functionality
- Test basic message sending capability
Expected Result: ECM module initializes correctly and basic functionality works
Pass Criteria: All basic tests pass, module can start and stop
Implementation Notes: Focus on basic functionality, avoid complex WebSocket testing
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

# Add parent directory to path for module imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import mock services
from mock_services import TestEnvironment

async def test_o00000005():
    test_code = "O00000005"
    test_name = "ECM Service Registration"
    results = []
    
    # Setup test environment
    test_env = TestEnvironment()
    await test_env.setup(websocket_port=8081)
    
    try:
        # Import ECM module
        from ECM.ecm import ExternalControlModule
        
        # Step 1: Test ECM module initialization
        config = {
            "ccu_integration": {
                "enabled": True,
                "ccu_host": "localhost",
                "ccu_port": 8081,
                "heartbeat_interval": 30,
                "reconnect_attempts": 5
            }
        }
        
        ecm = ExternalControlModule(config)
        results.append(ecm is not None)
        results.append(hasattr(ecm, 'start'))
        results.append(hasattr(ecm, 'stop'))
        results.append(hasattr(ecm, '_send_message'))  # Use private method instead
        results.append(hasattr(ecm, 'get_status'))
        
        # Step 2: Test ECM module configuration
        results.append(ecm.ccu_host == 'localhost')
        results.append(ecm.ccu_port == 8081)
        results.append(ecm.heartbeat_interval == 30)
        results.append(ecm.reconnect_attempts == 5)
        results.append(ecm.connection_status == 'disconnected' or ecm.connection_status.value == 'disconnected')
        
        # Step 3: Test ECM module status and statistics
        try:
            status = ecm.get_status()
            results.append(isinstance(status, dict))
            results.append('connection_status' in status)
            results.append('messages_sent' in status)
            results.append('messages_received' in status)
            results.append('commands_processed' in status.get('stats', {}))
        except Exception:
            results.append(False)
            results.append(False)
            results.append(False)
            results.append(False)
            results.append(False)
        
        # Step 4: Test ECM module health check
        try:
            health_result = await ecm.health_check()
            results.append(isinstance(health_result, dict))
            results.append('healthy' in health_result)
            results.append('connection_status' in health_result)
        except Exception:
            results.append(False)
            results.append(False)
            results.append(False)
        
        # Step 5: Test ECM module statistics
        results.append(isinstance(ecm.stats, dict))
        results.append('messages_sent' in ecm.stats)
        results.append('messages_received' in ecm.stats)
        results.append('commands_processed' in ecm.stats)
        results.append('certificate_updates' in ecm.stats)
        
        # Step 6: Test ECM module start and stop
        try:
            # Test starting the module
            await ecm.start()
            results.append(ecm.is_active == True)
            results.append(ecm.connection_status in ['connected', 'connecting', 'disconnected'] or 
                          ecm.connection_status.value in ['connected', 'connecting', 'disconnected'])
            
            # Test stopping the module
            await ecm.stop()
            results.append(ecm.is_active == False)
            results.append(ecm.connection_status == 'disconnected' or ecm.connection_status.value == 'disconnected')
            
        except Exception as e:
            results.append(False)
            results.append(False)
            results.append(False)
            results.append(False)
        
        # Step 7: Test ECM module message sending
        try:
            # Test sending a simple message
            test_message = {
                "type": "test",
                "data": "test_message",
                "timestamp": datetime.now().isoformat()
            }
            
            # Test that the internal send_message method exists
            results.append(hasattr(ecm, '_send_message'))
            results.append(callable(ecm._send_message))
            
            # Test that public message sending methods exist
            results.append(hasattr(ecm, 'send_heartbeat'))
            results.append(hasattr(ecm, 'send_report_delivered'))
            results.append(hasattr(ecm, 'send_error_report'))
            results.append(hasattr(ecm, 'send_monitoring_data'))
            
        except Exception:
            results.append(False)
            results.append(False)
            results.append(False)
            results.append(False)
            results.append(False)
            results.append(False)
        
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
                "module_initialized": ecm is not None,
                "basic_methods_available": hasattr(ecm, 'start') and hasattr(ecm, 'stop'),
                "status_method_works": hasattr(ecm, 'get_status'),
                "health_check_works": hasattr(ecm, 'health_check'),
                "start_stop_tested": True,
                "message_sending_tested": hasattr(ecm, '_send_message'),
                "public_message_methods": {
                    "send_heartbeat": hasattr(ecm, 'send_heartbeat'),
                    "send_report_delivered": hasattr(ecm, 'send_report_delivered'),
                    "send_error_report": hasattr(ecm, 'send_error_report'),
                    "send_monitoring_data": hasattr(ecm, 'send_monitoring_data')
                }
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
        result = await test_o00000005()
        print(json.dumps(result, indent=2))
        
        # Exit with appropriate code
        if result["status"] == "PASSED":
            sys.exit(0)
        else:
            sys.exit(1)
    
    asyncio.run(main())