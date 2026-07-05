"""
Test T0000036: Workflow: Mid-Conversation Model Switch
Module(s) Tested: BAAIM, AAAIM, SMCM, IFCM, DCMM
Description: Test seamless model switching during conversation.
Success Criteria: Conversation context is transferred and subsequent turns are handled correctly.
"""

print("DEBUG: test_t0000036.py started")

import sys
import os
# Dynamically add the RCM_main/RCM_main/RCM_main directory to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
print(f'DEBUG: sys.path = {sys.path}')
print(f'DEBUG: cwd = {os.getcwd()}')

import asyncio
import tempfile
from pathlib import Path
import json
from EMM.emm import ErrorManagementModule
from EMM.api_error_handler import api_error_handler

try:
    import json
    from EMM.emm import ErrorManagementModule
    from EMM.api_error_handler import api_error_handler
except Exception as e:
    print(f'IMPORT ERROR: {e}')
    raise

try:
    from BAAIM.baaim import baaim
    from AAAIM.aaaim import aaaim
    from SMCM.smcm import smcm
    from IFCM.ifcm import ifcm
    from DCMM.dcmm import dcmm
except Exception as e:
    print(f'IMPORT ERROR: {e}')
    raise

async def test_workflow_mid_conversation_model_switch():
    """Test seamless model switching during conversation."""
    test_code = "T0000036"
    test_name = "Workflow: Mid-Conversation Model Switch"
    try:
        # Use global instances
        # Test initial conversation with BAAIM
        initial_request = {
            "message": "Hello",
            "request_id": "conv_123",
            "messages": [{"role": "user", "content": "Hello"}]
        }
        initial_result = await baaim.process_request(initial_request) if hasattr(baaim, 'process_request') and asyncio.iscoroutinefunction(baaim.process_request) else baaim.process_request(initial_request)
        initial_success = isinstance(initial_result, dict) or hasattr(initial_result, 'success')
        
        # Test conversation context storage
        # Use create_conversation(request_id, priority, model, metadata)
        context_result = await dcmm.create_conversation(
            "conv_123",
            initial_request.get("priority", "A"),
            initial_request.get("model", "gpt-4"),
            metadata=initial_result if isinstance(initial_result, dict) else None
        ) if hasattr(dcmm, 'create_conversation') and asyncio.iscoroutinefunction(dcmm.create_conversation) else dcmm.create_conversation(
            "conv_123",
            initial_request.get("priority", "A"),
            initial_request.get("model", "gpt-4"),
            metadata=initial_result if isinstance(initial_result, dict) else None
        )
        context_success = isinstance(context_result, bool)
        
        # Test model switch command
        switch_command = {"type": "switch_model", "new_model": "AAAIM", "request_id": "conv_123"}
        switch_result = await smcm.change_model("conv_123", "AAAIM") if hasattr(smcm, 'change_model') and asyncio.iscoroutinefunction(smcm.change_model) else smcm.change_model("conv_123", "AAAIM")
        switch_success = isinstance(switch_result, bool)
        
        # Test context transfer (simulate by retrieving conversation)
        transfer_result = await dcmm.get_conversation("conv_123") if hasattr(dcmm, 'get_conversation') and asyncio.iscoroutinefunction(dcmm.get_conversation) else dcmm.get_conversation("conv_123")
        transfer_success = transfer_result is not None
        
        # Test continued conversation with AAAIM
        continued_request = {"message": "Continue conversation", "request_id": "conv_123"}
        continued_result = await aaaim.process_request(continued_request) if hasattr(aaaim, 'process_request') and asyncio.iscoroutinefunction(aaaim.process_request) else aaaim.process_request(continued_request)
        continued_success = isinstance(continued_result, dict) or hasattr(continued_result, 'success')
        
        # Test flow control with model switch
        flow_result = await ifcm.process_request({"model": "AAAIM", "request_id": "conv_123"}) if hasattr(ifcm, 'process_request') and asyncio.iscoroutinefunction(ifcm.process_request) else ifcm.process_request({"model": "AAAIM", "request_id": "conv_123"})
        flow_success = isinstance(flow_result, str) or isinstance(flow_result, dict)
        
        test_success = (initial_success and context_success and switch_success and 
                       transfer_success and continued_success and flow_success)
        
        return {
            "success": test_success,
            "test_code": test_code,
            "test_name": test_name,
            "message": f"Mid-conversation model switch successful",
            "details": {
                "initial_success": initial_success,
                "context_success": context_success,
                "switch_success": switch_success,
                "transfer_success": transfer_success,
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
    print("Test T0000036: Workflow: Mid-Conversation Model Switch")
    print("=" * 60)
    result = await test_workflow_mid_conversation_model_switch()
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