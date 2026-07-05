"""
Debug version of Test O00000005 to identify failing tests
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

# Add parent directory to path for module imports
sys.path.insert(0, str(Path(__file__).parent.parent))

async def debug_test_o00000005():
    test_code = "O00000005"
    test_name = "ECM Service Registration"
    results = []
    test_names = []
    
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
        
        test_names.append("ECM module is not None")
        results.append(ecm is not None)
        
        test_names.append("ECM has start method")
        results.append(hasattr(ecm, 'start'))
        
        test_names.append("ECM has stop method")
        results.append(hasattr(ecm, 'stop'))
        
        test_names.append("ECM has send_message method")
        results.append(hasattr(ecm, 'send_message'))
        
        test_names.append("ECM has get_status method")
        results.append(hasattr(ecm, 'get_status'))
        
        # Step 2: Test ECM module configuration
        test_names.append("ECM ccu_host is localhost")
        results.append(ecm.ccu_host == 'localhost')
        
        test_names.append("ECM ccu_port is 8081")
        results.append(ecm.ccu_port == 8081)
        
        test_names.append("ECM heartbeat_interval is 30")
        results.append(ecm.heartbeat_interval == 30)
        
        test_names.append("ECM reconnect_attempts is 5")
        results.append(ecm.reconnect_attempts == 5)
        
        test_names.append("ECM connection_status is disconnected")
        status_check = ecm.connection_status == 'disconnected' or ecm.connection_status.value == 'disconnected'
        results.append(status_check)
        
        # Step 3: Test ECM module status and statistics
        try:
            status = ecm.get_status()
            test_names.append("get_status returns dict")
            results.append(isinstance(status, dict))
            
            test_names.append("status has connection_status")
            results.append('connection_status' in status)
            
            test_names.append("status has messages_sent")
            results.append('messages_sent' in status)
            
            test_names.append("status has messages_received")
            results.append('messages_received' in status)
            
            test_names.append("status has commands_processed")
            results.append('commands_processed' in status)
        except Exception as e:
            print(f"Error in status test: {e}")
            for i in range(5):
                test_names.append(f"status test {i+1}")
                results.append(False)
        
        # Step 4: Test ECM module health check
        try:
            health_result = await ecm.health_check()
            test_names.append("health_check returns dict")
            results.append(isinstance(health_result, dict))
            
            test_names.append("health_result has healthy")
            results.append('healthy' in health_result)
            
            test_names.append("health_result has connection_status")
            results.append('connection_status' in health_result)
        except Exception as e:
            print(f"Error in health check: {e}")
            for i in range(3):
                test_names.append(f"health check test {i+1}")
                results.append(False)
        
        # Step 5: Test ECM module statistics
        test_names.append("ECM stats is dict")
        results.append(isinstance(ecm.stats, dict))
        
        test_names.append("stats has messages_sent")
        results.append('messages_sent' in ecm.stats)
        
        test_names.append("stats has messages_received")
        results.append('messages_received' in ecm.stats)
        
        test_names.append("stats has commands_processed")
        results.append('commands_processed' in ecm.stats)
        
        test_names.append("stats has certificate_updates")
        results.append('certificate_updates' in ecm.stats)
        
        # Step 6: Test ECM module start and stop
        try:
            # Test starting the module
            await ecm.start()
            test_names.append("ECM start sets is_active to True")
            results.append(ecm.is_active == True)
            
            test_names.append("ECM start sets valid connection_status")
            status_valid = ecm.connection_status in ['connected', 'connecting', 'disconnected'] or ecm.connection_status.value in ['connected', 'connecting', 'disconnected']
            results.append(status_valid)
            
            # Test stopping the module
            await ecm.stop()
            test_names.append("ECM stop sets is_active to False")
            results.append(ecm.is_active == False)
            
            test_names.append("ECM stop sets connection_status to disconnected")
            stop_status = ecm.connection_status == 'disconnected' or ecm.connection_status.value == 'disconnected'
            results.append(stop_status)
            
        except Exception as e:
            print(f"Error in start/stop test: {e}")
            for i in range(4):
                test_names.append(f"start/stop test {i+1}")
                results.append(False)
        
        # Step 7: Test ECM module message sending
        try:
            test_names.append("ECM has _send_message method")
            results.append(hasattr(ecm, '_send_message'))
            
            test_names.append("_send_message is callable")
            results.append(callable(ecm._send_message))
            
            test_names.append("ECM has send_heartbeat method")
            results.append(hasattr(ecm, 'send_heartbeat'))
            
            test_names.append("ECM has send_report_delivered method")
            results.append(hasattr(ecm, 'send_report_delivered'))
            
            test_names.append("ECM has send_error_report method")
            results.append(hasattr(ecm, 'send_error_report'))
            
            test_names.append("ECM has send_monitoring_data method")
            results.append(hasattr(ecm, 'send_monitoring_data'))
            
        except Exception as e:
            print(f"Error in message sending test: {e}")
            for i in range(6):
                test_names.append(f"message sending test {i+1}")
                results.append(False)
        
        # Print results with test names
        print(f"\nTest Results for {test_name}:")
        print("=" * 50)
        for i, (name, result) in enumerate(zip(test_names, results)):
            status = "PASS" if result else "FAIL"
            print(f"{i+1:2d}. {status}: {name}")
        
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
        
    except Exception as e:
        print(f"Error in test: {e}")
        import traceback
        traceback.print_exc()
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

if __name__ == "__main__":
    asyncio.run(debug_test_o00000005()) 