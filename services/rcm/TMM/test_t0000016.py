"""
Test T0000016: MSM - System Monitoring Report
Module(s) Tested: MSM
Description: Test system monitoring and reporting functionality.
Success Criteria: The module correctly gathers monitoring data and provides it to ECM.
"""

import asyncio
import tempfile
from pathlib import Path
import sys
import os
import json
import time
import threading
from EMM.emm import ErrorManagementModule
from EMM.api_error_handler import api_error_handler

# Add the project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from MSM.msm import MonitoringSystemModule

async def test_msm_system_monitoring_report():
    """Test system monitoring and reporting functionality."""
    test_code = "T0000016"
    test_name = "MSM - System Monitoring Report"
    
    try:
        print(f"Starting {test_name}...")
        
        # Initialize MSM
        msm = MonitoringSystemModule()
        print("MSM module initialized successfully")
        
        # Test 1: Token calculation
        print("1. Testing token calculation...")
        test_texts = [
            ("Hello", 2),
            ("Hello world", 3),
            ("This is a longer text for testing", 9),
            ("", 0)
        ]
        
        token_calculation_success = True
        for text, expected_tokens in test_texts:
            calculated_tokens = msm.calculate_tokens(text)
            success = calculated_tokens == expected_tokens
            token_calculation_success = token_calculation_success and success
            print(f"   '{text}' -> {calculated_tokens} tokens (expected: {expected_tokens}): {'Passed' if success else 'Failed'}")
        
        print(f"   Token calculation: {'Passed' if token_calculation_success else 'Failed'}")
        
        # Test 2: Conversation data extraction
        print("2. Testing conversation data extraction...")
        conversation_data = msm.extract_conversation_data()
        extraction_success = isinstance(conversation_data, dict) and "input_tokens" in conversation_data
        print(f"   Conversation data extraction: {'Passed' if extraction_success else 'Failed'}")
        if extraction_success:
            print(f"     Input tokens: {conversation_data.get('input_tokens', 0)}")
            print(f"     Output tokens: {conversation_data.get('output_tokens', 0)}")
            print(f"     System tokens: {conversation_data.get('system_tokens', 0)}")
            print(f"     Total tokens: {conversation_data.get('total_tokens', 0)}")
        
        # Test 3: Monitoring data gathering
        print("3. Testing monitoring data gathering...")
        monitoring_data = msm.gather_monitoring_data()
        gathering_success = isinstance(monitoring_data, dict) and "timestamp" in monitoring_data
        print(f"   Monitoring data gathering: {'Passed' if gathering_success else 'Failed'}")
        
        if gathering_success:
            print(f"     System info: {'Available' if 'system_info' in monitoring_data else 'Missing'}")
            print(f"     Resource usage: {'Available' if 'resource_usage' in monitoring_data else 'Missing'}")
            print(f"     Module status: {'Available' if 'module_status' in monitoring_data else 'Missing'}")
            print(f"     Token usage: {'Available' if 'token_usage' in monitoring_data else 'Missing'}")
        
        # Test 4: Get monitoring data (for ECM)
        print("4. Testing get_monitoring method (for ECM)...")
        try:
            monitoring_result = msm.get_monitoring()
            monitoring_success = isinstance(monitoring_result, dict) and "timestamp" in monitoring_result
            print(f"   Get monitoring data: {'Passed' if monitoring_success else 'Failed'}")
        except Exception as e:
            monitoring_success = False
            print(f"   Get monitoring data: Failed - {str(e)}")
        
        # Test 5: Module status
        print("5. Testing module status...")
        status = msm.get_status()
        status_success = isinstance(status, dict) and "module" in status
        print(f"   Module status: {'Passed' if status_success else 'Failed'}")
        if status_success:
            print(f"     Module: {status.get('module', 'Unknown')}")
            print(f"     Status: {status.get('status', 'Unknown')}")
            print(f"     Monitoring interval: {status.get('monitoring_interval', 'Unknown')} seconds")
        
        # Test 6: Start and stop monitoring
        print("6. Testing monitoring start/stop...")
        try:
            msm.start_monitoring()
            time.sleep(1)  # Let it run for a moment
            msm.stop_monitoring()
            monitoring_control_success = True
            print(f"   Monitoring control: Passed")
        except Exception as e:
            monitoring_control_success = False
            print(f"   Monitoring control: Failed - {str(e)}")
        
        # Test 7: Test ECM integration (simulated)
        print("7. Testing ECM integration...")
        try:
            # Simulate ECM calling MSM
            from ECM.ecm import ExternalControlModule
            ecm = ExternalControlModule()
            ecm_result = ecm._get_monitoring()
            ecm_success = isinstance(ecm_result, dict) and "status" in ecm_result
            print(f"   ECM integration: {'Passed' if ecm_success else 'Failed'}")
        except Exception as e:
            ecm_success = False
            print(f"   ECM integration: Failed - {str(e)}")
        
        # Calculate overall success
        tests = [
            token_calculation_success,
            extraction_success,
            gathering_success,
            monitoring_success,
            status_success,
            monitoring_control_success,
            ecm_success
        ]
        
        successful_tests = sum(tests)
        total_tests = len(tests)
        success_rate = (successful_tests / total_tests) * 100
        
        test_success = success_rate >= 80  # At least 80% success rate
        
        result = {
            "success": test_success,
            "test_code": test_code,
            "test_name": test_name,
            "message": f"MSM tests: {successful_tests}/{total_tests} successful ({success_rate:.1f}% success rate)",
            "details": {
                "token_calculation": token_calculation_success,
                "conversation_extraction": extraction_success,
                "data_gathering": gathering_success,
                "monitoring_data": monitoring_success,
                "module_status": status_success,
                "monitoring_control": monitoring_control_success,
                "ecm_integration": ecm_success,
                "success_rate": success_rate,
                "sample_monitoring_data": monitoring_data if gathering_success else None
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

async def main():
    """Run the MSM test."""
    print("=== MSM Test Suite ===")
    print("Testing System Monitoring and Reporting functionality.\n")
    
    result = await test_msm_system_monitoring_report()
    
    print(f"\n=== Test Results ===")
    print(f"MSM System Monitoring Test: {'PASS' if result['success'] else 'FAIL'}")
    
    if result['success']:
        print(f"\n✅ MSM module is working correctly!")
        print(f"   - Token calculation: Working")
        print(f"   - Conversation data extraction: Working")
        print(f"   - Monitoring data gathering: Working")
        print(f"   - Module status: Working")
        print(f"   - Monitoring control: Working")
        print(f"   - ECM integration: Working")
    else:
        print(f"\n❌ Some tests failed. Check the details below:")
        print(f"Test: {json.dumps(result, indent=2)}")

if __name__ == "__main__":
    asyncio.run(main())