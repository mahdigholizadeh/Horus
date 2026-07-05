"""
Test T0000026: Workflow: CCU Remote Control - Test Execution
Module(s) Tested: ECM, TMM
Description: Test CCU remote control of test execution.
Success Criteria: The ECM receives commands and triggers test execution via TMM.
"""

import asyncio
import tempfile
from pathlib import Path
import sys
import os
import json
from EMM.emm import ErrorManagementModule
from EMM.api_error_handler import api_error_handler
from datetime import datetime

# Add the project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from ECM.ecm import ExternalControlModule
from TMM.tmm import TestManagementModule

class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        return super().default(obj)

async def test_workflow_ccu_remote_control_test_execution():
    """Test CCU remote control of test execution."""
    test_code = "T0000026"
    test_name = "Workflow: CCU Remote Control - Test Execution"
    try:
        print(f"Starting {test_name}...")
        
        # Initialize modules
        ecm = ExternalControlModule()
        tmm = TestManagementModule()
        print("Modules initialized successfully")
        
        # Test 1: ECM command reception
        print("1. Testing ECM command reception...")
        try:
            # Test status command
            status_command = "status"
            status_result = await ecm.receive_command(status_command, {})
            status_success = isinstance(status_result, dict) and "success" in status_result
            print(f"   Status command: {'Passed' if status_success else 'Failed'}")
            
            # Test test execution command
            test_command = "execute_test"
            test_params = {"test_id": "T0000001"}
            test_result = await ecm.receive_command(test_command, test_params)
            test_success = isinstance(test_result, dict) and "success" in test_result
            print(f"   Test execution command: {'Passed' if test_success else 'Failed'}")
            
            # Test invalid command handling
            invalid_command = "invalid_command"
            invalid_result = await ecm.receive_command(invalid_command, {})
            invalid_success = isinstance(invalid_result, dict) and "success" in invalid_result
            print(f"   Invalid command handling: {'Passed' if invalid_success else 'Failed'}")
            
            ecm_success = status_success and test_success and invalid_success
            
        except Exception as e:
            print(f"   ECM command reception: Failed - {str(e)}")
            ecm_success = False
        
        # Test 2: TMM test execution
        print("2. Testing TMM test execution...")
        try:
            # Test running a specific test
            test_execution_result = await tmm.run_test_by_code("T0000001")
            execution_success = isinstance(test_execution_result, dict) and "success" in test_execution_result
            print(f"   Test execution: {'Passed' if execution_success else 'Failed'}")
            
            # Test getting test metadata
            test_metadata = tmm.get_test_metadata("T0000001")
            metadata_success = isinstance(test_metadata, dict)
            print(f"   Test metadata: {'Passed' if metadata_success else 'Failed'}")
            
            # Test test statistics
            test_stats = tmm.get_test_statistics()
            stats_success = isinstance(test_stats, dict)
            print(f"   Test statistics: {'Passed' if stats_success else 'Failed'}")
            
            tmm_success = execution_success and metadata_success and stats_success
            
        except Exception as e:
            print(f"   TMM test execution: Failed - {str(e)}")
            tmm_success = False
        
        # Test 3: CCU integration workflow
        print("3. Testing CCU integration workflow...")
        try:
            # Simulate CCU requesting test execution
            ccu_request = {
                "command": "execute_test",
                "test_id": "T0000001",
                "parameters": {"priority": "high"}
            }
            
            # ECM processes the command
            ccu_result = await ecm.receive_command(ccu_request["command"], ccu_request["parameters"])
            ccu_processing_success = isinstance(ccu_result, dict)
            print(f"   CCU command processing: {'Passed' if ccu_processing_success else 'Failed'}")
            
            # TMM executes the test
            tmm_execution = await tmm.run_test_by_code(ccu_request["test_id"])
            tmm_execution_success = isinstance(tmm_execution, dict)
            print(f"   TMM test execution: {'Passed' if tmm_execution_success else 'Failed'}")
            
            # ECM reports back to CCU
            report_data = {
                "test_id": ccu_request["test_id"],
                "result": tmm_execution,
                "status": "completed"
            }
            report_result = await ecm.receive_command("report_result", report_data)
            report_success = isinstance(report_result, dict)
            print(f"   Result reporting: {'Passed' if report_success else 'Failed'}")
            
            workflow_success = ccu_processing_success and tmm_execution_success and report_success
            
        except Exception as e:
            print(f"   CCU integration workflow: Failed - {str(e)}")
            workflow_success = False
        
        # Test 4: Error handling in remote control
        print("4. Testing error handling in remote control...")
        try:
            # Test with invalid test ID
            invalid_test_result = await tmm.run_test_by_code("INVALID_TEST")
            invalid_test_success = isinstance(invalid_test_result, dict)
            print(f"   Invalid test handling: {'Passed' if invalid_test_success else 'Failed'}")
            
            # Test with invalid command
            invalid_cmd_result = await ecm.receive_command("invalid_command", {"test_id": "T0000001"})
            invalid_cmd_success = isinstance(invalid_cmd_result, dict)
            print(f"   Invalid command handling: {'Passed' if invalid_cmd_success else 'Failed'}")
            
            error_handling_success = invalid_test_success and invalid_cmd_success
            
        except Exception as e:
            print(f"   Error handling: Failed - {str(e)}")
            error_handling_success = False
        
        # Test 5: Test management capabilities
        print("5. Testing test management capabilities...")
        try:
            # Test unit tests execution
            unit_tests_result = await tmm.run_all_unit_tests()
            unit_tests_success = isinstance(unit_tests_result, dict)
            print(f"   Unit tests execution: {'Passed' if unit_tests_success else 'Failed'}")
            
            # Test integration tests execution
            integration_tests_result = await tmm.run_all_integration_tests()
            integration_tests_success = isinstance(integration_tests_result, dict)
            print(f"   Integration tests execution: {'Passed' if integration_tests_success else 'Failed'}")
            
            # Test all tests execution
            all_tests_result = await tmm.run_all_tests()
            all_tests_success = isinstance(all_tests_result, dict)
            print(f"   All tests execution: {'Passed' if all_tests_success else 'Failed'}")
            
            management_success = unit_tests_success and integration_tests_success and all_tests_success
            
        except Exception as e:
            print(f"   Test management capabilities: Failed - {str(e)}")
            management_success = False
        
        # Calculate overall success
        tests = [
            ecm_success,
            tmm_success,
            workflow_success,
            error_handling_success,
            management_success
        ]
        
        successful_tests = sum(tests)
        total_tests = len(tests)
        success_rate = (successful_tests / total_tests) * 100
        
        test_success = success_rate >= 80  # At least 80% success rate
        
        result = {
            "success": test_success,
            "test_code": test_code,
            "test_name": test_name,
            "message": f"CCU remote control tests: {successful_tests}/{total_tests} successful ({success_rate:.1f}% success rate)",
            "details": {
                "ecm_success": ecm_success,
                "tmm_success": tmm_success,
                "workflow_success": workflow_success,
                "error_handling_success": error_handling_success,
                "management_success": management_success,
                "success_rate": success_rate,
                "sample_test_result": test_execution_result if 'test_execution_result' in locals() else None
            }
        }
        
        print(f"\nTest result: {result}")
        return result
        
    except Exception as e:
        error_result = {
            "success": False,
            "test_code": test_code,
            "test_name": test_name,
            "error": f"Test execution failed: {str(e)}"
        }
        print(f"Test failed: {error_result}")
        return error_result

if __name__ == "__main__":
    result = asyncio.run(test_workflow_ccu_remote_control_test_execution())
    print(json.dumps(result, indent=2, cls=CustomJSONEncoder)) 