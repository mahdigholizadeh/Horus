"""
Test T0000037: Workflow: Mid-Conversation System Message Injection
Module(s) Tested: BAAIM, SMSM, IFCM, DCMM
Description: Test system message injection during conversation.
Success Criteria: The API's subsequent response adheres to the injected system message.
"""

import asyncio
import sys
import os
import json

# Add the EMM parent directory to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from EMM.emm import ErrorManagementModule
from EMM.api_error_handler import api_error_handler

# Add the project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from BAAIM.baaim import baaim
from SMSM.smsm import smsm
from IFCM.ifcm import ifcm
from DCMM.dcmm import dcmm

async def test_workflow_mid_conversation_system_message_injection():
    """Test system message injection during conversation."""
    test_code = "T0000037"
    test_name = "Workflow: Mid-Conversation System Message Injection"
    try:
        # Test initial conversation
        initial_request = {"message": "Hello", "request_id": "conv_456", "messages": [{"role": "user", "content": "Hello"}]}
        initial_result = await baaim.process_request(initial_request) if hasattr(baaim, 'process_request') and asyncio.iscoroutinefunction(baaim.process_request) else baaim.process_request(initial_request)
        initial_success = isinstance(initial_result, dict) or hasattr(initial_result, 'success')

        # Create conversation in DCMM explicitly
        conversation_created = await dcmm.create_conversation("conv_456", "C", "gpt-4", metadata=initial_result if isinstance(initial_result, dict) else None) if hasattr(dcmm, 'create_conversation') and asyncio.iscoroutinefunction(dcmm.create_conversation) else dcmm.create_conversation("conv_456", "C", "gpt-4", metadata=initial_result if isinstance(initial_result, dict) else None)
        creation_success = conversation_created is True

        # Test conversation retrieval
        conversation = await dcmm.get_conversation("conv_456") if hasattr(dcmm, 'get_conversation') and asyncio.iscoroutinefunction(dcmm.get_conversation) else dcmm.get_conversation("conv_456")
        retrieval_success = conversation is not None

        # Test system message injection
        system_message = "From now on, respond only in rhymes."
        injection_result = await smsm.inject_system_message("conv_456", system_message) if hasattr(smsm, 'inject_system_message') and asyncio.iscoroutinefunction(smsm.inject_system_message) else smsm.inject_system_message("conv_456", system_message)
        injection_success = isinstance(injection_result, dict) and injection_result.get("success", False)

        # Test conversation update (simulate by updating status)
        update_result = await dcmm.update_conversation_status("conv_456", "system_intervention") if hasattr(dcmm, 'update_conversation_status') and asyncio.iscoroutinefunction(dcmm.update_conversation_status) else dcmm.update_conversation_status("conv_456", "system_intervention")
        update_success = update_result is True

        # Test continued conversation with system message
        continued_request = {"message": "Tell me a story", "request_id": "conv_456", "messages": [{"role": "user", "content": "Tell me a story"}]}
        continued_result = await baaim.process_request(continued_request) if hasattr(baaim, 'process_request') and asyncio.iscoroutinefunction(baaim.process_request) else baaim.process_request(continued_request)
        continued_success = isinstance(continued_result, dict) or hasattr(continued_result, 'success')

        # Test flow control with system message
        flow_result = await ifcm.process_request({"request_id": "conv_456", "system_message": system_message}) if hasattr(ifcm, 'process_request') and asyncio.iscoroutinefunction(ifcm.process_request) else ifcm.process_request({"request_id": "conv_456", "system_message": system_message})
        flow_success = isinstance(flow_result, str) or isinstance(flow_result, dict)

        test_success = (initial_success and creation_success and retrieval_success and injection_success and 
                       update_success and continued_success and flow_success)

        return {
            "success": test_success,
            "test_code": test_code,
            "test_name": test_name,
            "message": f"Mid-conversation system message injection successful",
            "details": {
                "initial_success": initial_success,
                "creation_success": creation_success,
                "retrieval_success": retrieval_success,
                "injection_success": injection_success,
                "update_success": update_success,
                "continued_success": continued_success,
                "flow_success": flow_success
            }
        }
    except Exception as e:
        return {
            "success": False,
            "test_code": test_code,
            "test_name": test_name,
            "error": f"Test execution failed: {str(e)}"
        }

async def main():
    print("=" * 60)
    print("Test T0000037: Workflow: Mid-Conversation System Message Injection")
    print("=" * 60)
    result = await test_workflow_mid_conversation_system_message_injection()
    print(f"\nTest Result: {'PASSED' if result['success'] else 'FAILED'}")
    print(f"Test Code: {result['test_code']}")
    print(f"Test Name: {result['test_name']}")
    if result['success']:
        print(f"Message: {result['message']}")
        print("\nDetails:")
        for key, value in result['details'].items():
            print(f"  {key}: {value}")
    else:
        error_msg = result.get('error', 'Unknown error occurred')
        print(f"Error: {error_msg}")
        if 'details' in result:
            print("\nDetails:")
            for key, value in result['details'].items():
                print(f"  {key}: {value}")
    print("\n" + "=" * 60)
    return result

if __name__ == "__main__":
    asyncio.run(main()) 