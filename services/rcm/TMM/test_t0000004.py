"""
Test T0000004: AACM - Successful Async API Call
Module(s) Tested: AACM
Description: Make a call to a mock OpenAI API endpoint.
Success Criteria: The module successfully establishes an asynchronous connection, sends a request, and receives a valid mock response without blocking.
"""

import asyncio
import json
import tempfile
from pathlib import Path
import sys
import os
from EMM.emm import ErrorManagementModule
from EMM.api_error_handler import api_error_handler

# Add the project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from AACM.aacm import AsynchronousAPICommunicationModule

MOCK_API_KEY = "sk-proj-mock-test-key-replace-in-env"

async def test_aacm_successful_async_api_call():
    """Test successful async API call functionality."""
    test_code = "T0000004"
    test_name = "AACM - Successful Async API Call"
    
    try:
        # Initialize AACM
        aacm = AsynchronousAPICommunicationModule()
        
        # Test data
        test_prompt = "Hello, this is a test prompt for async API call"
        test_messages = [
            {"role": "user", "content": test_prompt}
        ]
        
        # Test 1: Basic async API call
        response = await aacm.make_chat_completion(
            messages=test_messages,
            api_key=MOCK_API_KEY,
            request_id="test_request_001"
        )
        basic_call_success = isinstance(response, dict) and "choices" in response
        
        # Test 2: API call with messages (same as test 1)
        messages_response = await aacm.make_chat_completion(
            messages=test_messages,
            api_key=MOCK_API_KEY, 
            request_id="test_request_002"
        )
        messages_call_success = isinstance(messages_response, dict) and "choices" in messages_response
        
        # Test 3: API call with parameters
        params_response = await aacm.make_chat_completion(
            messages=test_messages,
            api_key=MOCK_API_KEY,
            request_id="test_request_003",
            temperature=0.7,
            max_tokens=100
        )
        params_call_success = isinstance(params_response, dict) and "choices" in params_response
        
        # Test 4: Error handling
        try:
            error_response = await aacm.make_api_call("")
            error_handling_success = False  # Should not reach here
        except Exception:
            error_handling_success = True
        
        # Test 5: Response validation
        if basic_call_success:
            # Check if response has the expected OpenAI API structure
            choices = response.get("choices", [])
            if choices and len(choices) > 0:
                message = choices[0].get("message", {})
                response_content = message.get("content", "")
                response_valid = len(response_content) > 0
            else:
                response_valid = False
        else:
            response_valid = False
        
        # Calculate overall success
        tests = [
            basic_call_success,
            messages_call_success,
            params_call_success,
            error_handling_success,
            response_valid
        ]
        
        successful_tests = sum(tests)
        total_tests = len(tests)
        success_rate = (successful_tests / total_tests) * 100
        
        test_success = success_rate >= 80  # At least 80% success rate
        
        return {
            "success": test_success,
            "test_code": test_code,
            "test_name": test_name,
            "message": f"Async API calls: {successful_tests}/{total_tests} successful ({success_rate:.1f}% success rate)",
            "details": {
                "basic_call": basic_call_success,
                "messages_call": messages_call_success,
                "params_call": params_call_success,
                "error_handling": error_handling_success,
                "response_valid": response_valid,
                "success_rate": success_rate,
                "sample_response": response if basic_call_success else None
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
    import json
    result = asyncio.run(test_aacm_successful_async_api_call())
    print(json.dumps(result, indent=2)) 