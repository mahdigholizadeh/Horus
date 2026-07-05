"""
Test T0000028: Test retry mechanism on API failures
Module(s) Tested: RLM, AACM
Description: Test retry mechanism on API failures.
Success Criteria: The module correctly retries failed requests with appropriate delays.
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

from RLM.rlm import RateLimitingModule
from AACM.aacm import AsynchronousAPICommunicationModule

class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        return super().default(obj)

async def test_retry_mechanism_on_api_failures():
    """Test retry mechanism on API failures."""
    test_code = "T0000028"
    test_name = "Test retry mechanism on API failures"
    try:
        print(f"Starting {test_name}...")
        
        # Initialize modules
        rlm = RateLimitingModule()
        aacm = AsynchronousAPICommunicationModule()
        print("Modules initialized successfully")
        
        # Test 1: RLM retry configuration for API failures
        print("1. Testing RLM retry configuration for API failures...")
        try:
            # Start RLM module
            await rlm.start()
            
            # Configure retry settings for API failures
            await rlm.configure_retry_settings(max_retries=3, base_delay=0.1, max_delay=1.0)
            retry_status = await rlm.get_retry_status()
            config_success = retry_status.get("max_retries") == 3
            print(f"   Retry configuration: {'Passed' if config_success else 'Failed'}")
            
            # Test retry manager for API-specific errors
            retry_manager = rlm.retry_manager
            api_error_retry = retry_manager.should_retry("test_api_request", "rate_limit_exceeded")
            api_error_success = api_error_retry == True
            print(f"   API error retry decision: {'Passed' if api_error_success else 'Failed'}")
            
            config_success = config_success and api_error_success
            
        except Exception as e:
            print(f"   RLM retry configuration: Failed - {str(e)}")
            config_success = False
        
        # Test 2: AACM API failure handling
        print("2. Testing AACM API failure handling...")
        try:
            # Test AACM status
            aacm_status = await aacm.get_status()
            aacm_status_success = isinstance(aacm_status, dict) and "status" in aacm_status
            print(f"   AACM status: {'Passed' if aacm_status_success else 'Failed'}")
            
            # Test AACM request tracking
            request_status = await aacm.get_request_status("test_request")
            request_status_success = isinstance(request_status, dict) or request_status is None
            print(f"   Request status tracking: {'Passed' if request_status_success else 'Failed'}")
            
            aacm_success = aacm_status_success and request_status_success
            
        except Exception as e:
            print(f"   AACM API failure handling: Failed - {str(e)}")
            aacm_success = False
        
        # Test 3: API failure simulation with retry
        print("3. Testing API failure simulation with retry...")
        try:
            # Create a failing API call
            async def failing_api_call(request_id: str, priority: str):
                raise Exception("API rate limit exceeded")
            
            async def success_callback(result, request):
                print(f"   Success callback called for {request.request_id}")
            
            async def error_callback(error, request):
                print(f"   Error callback called for {request.request_id}: {error}")
            
            # Submit request that will fail
            test_request_id = "test_api_failure_001"
            await rlm.make_rate_limited_request(
                request_id=test_request_id,
                priority="A",
                api_call=failing_api_call,
                success_callback=success_callback,
                error_callback=error_callback
            )
            
            # Wait for processing
            await asyncio.sleep(0.5)
            
            # Check if retry was triggered
            retry_status = await rlm.get_retry_status()
            retry_triggered = test_request_id in retry_status.get("retry_counts", {})
            api_failure_success = retry_triggered
            print(f"   API failure retry: {'Passed' if api_failure_success else 'Failed'}")
            
        except Exception as e:
            print(f"   API failure simulation: Failed - {str(e)}")
            api_failure_success = False
        
        # Test 4: Different API error types and retry behavior
        print("4. Testing different API error types and retry behavior...")
        try:
            retry_manager = rlm.retry_manager
            
            # Test rate limit error
            rate_limit_retry = retry_manager.should_retry("test_rate_limit", "rate_limit_exceeded")
            rate_limit_success = rate_limit_retry == True
            print(f"   Rate limit error retry: {'Passed' if rate_limit_success else 'Failed'}")
            
            # Test timeout error
            timeout_retry = retry_manager.should_retry("test_timeout", "timeout_error")
            timeout_success = timeout_retry == True
            print(f"   Timeout error retry: {'Passed' if timeout_success else 'Failed'}")
            
            # Test server error
            server_retry = retry_manager.should_retry("test_server", "server_error")
            server_success = server_retry == True
            print(f"   Server error retry: {'Passed' if server_success else 'Failed'}")
            
            # Test authentication error (should not retry)
            auth_retry = retry_manager.should_retry("test_auth", "authentication_error")
            auth_success = auth_retry == False
            print(f"   Authentication error retry: {'Passed' if auth_success else 'Failed'}")
            
            error_types_success = rate_limit_success and timeout_success and server_success and auth_success
            
        except Exception as e:
            print(f"   API error types: Failed - {str(e)}")
            error_types_success = False
        
        # Test 5: Retry delay calculation for API failures
        print("5. Testing retry delay calculation for API failures...")
        try:
            test_request_id = "test_api_delay_001"
            retry_manager = rlm.retry_manager
            
            # Test initial delay for API failure
            initial_delay = retry_manager.get_retry_delay(test_request_id)
            initial_delay_success = isinstance(initial_delay, (int, float)) and initial_delay >= 0
            print(f"   Initial API failure delay: {'Passed' if initial_delay_success else 'Failed'}")
            
            # Simulate multiple API failures
            for i in range(3):
                retry_manager.increment_retry_count(test_request_id)
                delay = retry_manager.get_retry_delay(test_request_id)
                print(f"   Retry {i+1} delay: {delay:.3f}s")
            
            # Check if delay increases with retries
            final_delay = retry_manager.get_retry_delay(test_request_id)
            delay_increase_success = final_delay > initial_delay
            print(f"   Delay increase with retries: {'Passed' if delay_increase_success else 'Failed'}")
            
            delay_success = initial_delay_success and delay_increase_success
            
        except Exception as e:
            print(f"   Retry delay calculation: Failed - {str(e)}")
            delay_success = False
        
        # Test 6: API failure statistics and monitoring
        print("6. Testing API failure statistics and monitoring...")
        try:
            # Get RLM status with retry information
            rlm_status = await rlm.get_status()
            rlm_stats_success = isinstance(rlm_status, dict) and "retry_status" in rlm_status
            print(f"   RLM retry statistics: {'Passed' if rlm_stats_success else 'Failed'}")
            
            # Get AACM status
            aacm_stats = await aacm.get_status()
            aacm_stats_success = isinstance(aacm_stats, dict) and "statistics" in aacm_stats
            print(f"   AACM statistics: {'Passed' if aacm_stats_success else 'Failed'}")
            
            monitoring_success = rlm_stats_success and aacm_stats_success
            
        except Exception as e:
            print(f"   API failure statistics: Failed - {str(e)}")
            monitoring_success = False
        
        # Stop RLM module
        await rlm.stop()
        
        # Calculate overall success
        tests = [
            config_success,
            aacm_success,
            api_failure_success,
            error_types_success,
            delay_success,
            monitoring_success
        ]
        
        successful_tests = sum(tests)
        total_tests = len(tests)
        success_rate = (successful_tests / total_tests) * 100
        
        test_success = success_rate >= 80  # At least 80% success rate
        
        result = {
            "success": test_success,
            "test_code": test_code,
            "test_name": test_name,
            "message": f"API failure retry mechanism tests: {successful_tests}/{total_tests} successful ({success_rate:.1f}% success rate)",
            "details": {
                "config_success": config_success,
                "aacm_success": aacm_success,
                "api_failure_success": api_failure_success,
                "error_types_success": error_types_success,
                "delay_success": delay_success,
                "monitoring_success": monitoring_success,
                "success_rate": success_rate,
                "retry_status": await rlm.get_retry_status() if 'rlm' in locals() else None
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
    result = asyncio.run(test_retry_mechanism_on_api_failures())
    print(json.dumps(result, indent=2, cls=CustomJSONEncoder))