"""
Test T0000027: RLM - Retry Mechanism on Failure
Module(s) Tested: RLM
Description: Test RLM retry mechanism on failure.
Success Criteria: The RLM correctly implements retry logic for failed requests.
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

class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        return super().default(obj)

async def test_rlm_retry_mechanism_on_failure():
    """Test RLM retry mechanism on failure."""
    test_code = "T0000027"
    test_name = "RLM - Retry Mechanism on Failure"
    try:
        print(f"Starting {test_name}...")
        
        # Initialize RLM module
        rlm = RateLimitingModule()
        print("RLM module initialized successfully")
        
        # Test 1: Retry mechanism initialization
        print("1. Testing retry mechanism initialization...")
        try:
            # Start the RLM module
            await rlm.start()
            
            # Test retry status
            retry_status = await rlm.get_retry_status()
            retry_init_success = isinstance(retry_status, dict) and "max_retries" in retry_status
            print(f"   Retry status: {'Passed' if retry_init_success else 'Failed'}")
            
            # Test retry configuration
            await rlm.configure_retry_settings(max_retries=5, base_delay=0.1, max_delay=1.0)
            updated_status = await rlm.get_retry_status()
            config_success = updated_status.get("max_retries") == 5
            print(f"   Retry configuration: {'Passed' if config_success else 'Failed'}")
            
            init_success = retry_init_success and config_success
            
        except Exception as e:
            print(f"   Retry mechanism initialization: Failed - {str(e)}")
            init_success = False
        
        # Test 2: Retry decision logic
        print("2. Testing retry decision logic...")
        try:
            # Test should_retry for different error types using the retry manager directly
            test_request_id = "test_retry_001"
            retry_manager = rlm.retry_manager
            
            # Test retry for rate limit error
            rate_limit_retry = retry_manager.should_retry(test_request_id, "rate_limit_exceeded")
            rate_limit_success = rate_limit_retry == True
            print(f"   Rate limit retry decision: {'Passed' if rate_limit_success else 'Failed'}")
            
            # Test retry for timeout error
            timeout_retry = retry_manager.should_retry(test_request_id, "timeout_error")
            timeout_success = timeout_retry == True
            print(f"   Timeout retry decision: {'Passed' if timeout_success else 'Failed'}")
            
            # Test retry for connection error
            connection_retry = retry_manager.should_retry(test_request_id, "connection_error")
            connection_success = connection_retry == True
            print(f"   Connection retry decision: {'Passed' if connection_success else 'Failed'}")
            
            # Test no retry for permission denied error (non-retryable)
            permission_retry = retry_manager.should_retry(test_request_id, "permission_denied")
            permission_success = permission_retry == False
            print(f"   Permission denied retry decision: {'Passed' if permission_success else 'Failed'}")
            
            decision_success = rate_limit_success and timeout_success and connection_success and permission_success
            
        except Exception as e:
            print(f"   Retry decision logic: Failed - {str(e)}")
            decision_success = False
        
        # Test 3: Retry delay calculation
        print("3. Testing retry delay calculation...")
        try:
            test_request_id = "test_delay_001"
            retry_manager = rlm.retry_manager
            
            # Test initial retry delay
            initial_delay = retry_manager.get_retry_delay(test_request_id)
            initial_delay_success = isinstance(initial_delay, (int, float)) and initial_delay >= 0
            print(f"   Initial retry delay: {'Passed' if initial_delay_success else 'Failed'}")
            
            # Increment retry count and test delay increase
            retry_manager.increment_retry_count(test_request_id)
            increased_delay = retry_manager.get_retry_delay(test_request_id)
            delay_increase_success = increased_delay > initial_delay
            print(f"   Delay increase: {'Passed' if delay_increase_success else 'Failed'}")
            
            # Test max delay limit (with some tolerance for jitter)
            for _ in range(5):  # Increment multiple times
                retry_manager.increment_retry_count(test_request_id)
            max_delay = retry_manager.get_retry_delay(test_request_id)
            # Allow some tolerance for jitter (max_delay + 10% jitter)
            max_delay_tolerance = retry_manager.max_delay * 1.1
            max_delay_success = max_delay <= max_delay_tolerance
            print(f"   Max delay limit: {'Passed' if max_delay_success else 'Failed'} (delay: {max_delay:.3f}, max: {max_delay_tolerance:.3f})")
            
            delay_success = initial_delay_success and delay_increase_success and max_delay_success
            
        except Exception as e:
            print(f"   Retry delay calculation: Failed - {str(e)}")
            delay_success = False
        
        # Test 4: Retry count management
        print("4. Testing retry count management...")
        try:
            test_request_id = "test_count_001"
            retry_manager = rlm.retry_manager
            
            # Test initial retry count
            initial_count = retry_manager.retry_counts.get(test_request_id, 0)
            initial_count_success = initial_count == 0
            print(f"   Initial retry count: {'Passed' if initial_count_success else 'Failed'}")
            
            # Test increment retry count
            retry_manager.increment_retry_count(test_request_id)
            incremented_count = retry_manager.retry_counts.get(test_request_id, 0)
            increment_success = incremented_count == 1
            print(f"   Increment retry count: {'Passed' if increment_success else 'Failed'}")
            
            # Test reset retry count
            retry_manager.reset_retry_count(test_request_id)
            reset_count = retry_manager.retry_counts.get(test_request_id, 0)
            reset_success = reset_count == 0
            print(f"   Reset retry count: {'Passed' if reset_success else 'Failed'}")
            
            count_success = initial_count_success and increment_success and reset_success
            
        except Exception as e:
            print(f"   Retry count management: Failed - {str(e)}")
            count_success = False
        
        # Test 5: Retry mechanism in rate-limited requests
        print("5. Testing retry mechanism in rate-limited requests...")
        try:
            # Create a test API call that fails
            async def failing_api_call(request_id: str, priority: str):
                raise Exception("Simulated API failure")
            
            async def success_callback(result, request):
                print(f"   Success callback called for {request.request_id}")
            
            async def error_callback(error, request):
                print(f"   Error callback called for {request.request_id}: {error}")
            
            # Test rate-limited request with retry
            test_request_id = "test_rate_limited_001"
            
            # Submit the request (it will be queued and processed asynchronously)
            await rlm.make_rate_limited_request(
                request_id=test_request_id,
                priority="A",
                api_call=failing_api_call,
                success_callback=success_callback,
                error_callback=error_callback
            )
            
            # Wait a bit for processing
            await asyncio.sleep(0.5)
            
            # Check if retry mechanism was triggered
            retry_status = await rlm.get_retry_status()
            retry_triggered = test_request_id in retry_status.get("retry_counts", {})
            rate_limited_success = retry_triggered
            print(f"   Rate-limited retry: {'Passed' if rate_limited_success else 'Failed'}")
            
        except Exception as e:
            print(f"   Rate-limited retry mechanism: Failed - {str(e)}")
            rate_limited_success = False
        
        # Test 6: Retry statistics and monitoring
        print("6. Testing retry statistics and monitoring...")
        try:
            # Get comprehensive status
            full_status = await rlm.get_status()
            status_success = isinstance(full_status, dict) and "retry_status" in full_status
            print(f"   Full status: {'Passed' if status_success else 'Failed'}")
            
            # Test retry statistics
            retry_stats = await rlm.get_retry_status()
            stats_success = isinstance(retry_stats, dict) and "max_retries" in retry_stats
            print(f"   Retry statistics: {'Passed' if stats_success else 'Failed'}")
            
            monitoring_success = status_success and stats_success
            
        except Exception as e:
            print(f"   Retry statistics and monitoring: Failed - {str(e)}")
            monitoring_success = False
        
        # Stop the RLM module
        await rlm.stop()
        
        # Calculate overall success
        tests = [
            init_success,
            decision_success,
            delay_success,
            count_success,
            rate_limited_success,
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
            "message": f"RLM retry mechanism tests: {successful_tests}/{total_tests} successful ({success_rate:.1f}% success rate)",
            "details": {
                "init_success": init_success,
                "decision_success": decision_success,
                "delay_success": delay_success,
                "count_success": count_success,
                "rate_limited_success": rate_limited_success,
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
    result = asyncio.run(test_rlm_retry_mechanism_on_failure())
    print(json.dumps(result, indent=2, cls=CustomJSONEncoder))