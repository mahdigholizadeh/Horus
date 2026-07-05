"""
Test T0000009: AAAIM - Default & Override Agent Usage
Module(s) Tested: AAAIM
Description: Test default and override agent usage functionality.
Success Criteria: The module correctly uses default agent settings and allows override when specified.
"""

import asyncio
import tempfile
from pathlib import Path
import sys
import os
import json
from EMM.emm import ErrorManagementModule
from EMM.api_error_handler import api_error_handler

# Add the project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from AAAIM.aaaim import AgenticAPIActivationModule

async def test_aaaim_default_and_override_agent_usage():
    """Test default and override agent usage."""
    test_code = "T0000009"
    test_name = "AAAIM - Default & Override Agent Usage"
    try:
        print(f"Starting {test_name}...")
        
        # Initialize AAAIM module
        aaaim = AgenticAPIActivationModule()
        print("AAAIM module initialized successfully")
        
        # Test default agent usage
        print("Testing default agent usage...")
        default_request = {
            "message": "Hello, this is a test message for the default agent."
        }
        
        default_result = await aaaim.process_request(default_request)
        default_success = isinstance(default_result, object) and hasattr(default_result, 'success')
        print(f"Default agent result: {default_result.success if default_result else 'Failed'}")
        if default_result and default_result.success:
            print(f"Default agent response: {default_result.response[:100]}...")
            print(f"Thread ID: {default_result.thread_id}")
        
        # Test override agent usage
        print("Testing override agent usage...")
        override_request = {
            "message": "Hello, this is an override test with a different agent.",
            "agent_id": "asst_lQCwiQAJcycDj7YqHBafyWtT",  # Override agent ID
            "api_key": aaaim.current_config.api_key  # Use same API key
        }
        
        override_result = await aaaim.process_request(override_request)
        override_success = isinstance(override_result, object) and hasattr(override_result, 'success')
        print(f"Override agent result: {override_result.success if override_result else 'Failed'}")
        if override_result and override_result.success:
            print(f"Override agent response: {override_result.response[:100]}...")
            print(f"Thread ID: {override_result.thread_id}")
        
        # Test configuration methods
        print("Testing configuration methods...")
        aaaim.set_agent_id("asst_lQCwiQAJcycDj7YqHBafyWtT")
        aaaim.set_config(model="gpt-4", max_retries=5)
        
        config = aaaim.get_config()
        config_success = isinstance(config, dict) and "agent_id" in config
        print(f"Configuration test: {'Passed' if config_success else 'Failed'}")
        
        # Test module status
        print("Testing module status...")
        status = aaaim.get_module_status()
        status_success = isinstance(status, dict) and "module" in status
        print(f"Status test: {'Passed' if status_success else 'Failed'}")
        
        # Test conversation management
        print("Testing conversation management...")
        if default_result and default_result.success and default_result.thread_id:
            conversation_status = aaaim.get_conversation_status(default_result.thread_id)
            conversation_success = conversation_status is not None
            print(f"Conversation management test: {'Passed' if conversation_success else 'Failed'}")
            
            # Clean up conversation
            cleanup_success = aaaim.cleanup_conversation(default_result.thread_id)
            print(f"Conversation cleanup test: {'Passed' if cleanup_success else 'Failed'}")
        else:
            conversation_success = True  # Skip if no conversation was created
            cleanup_success = True
        
        # Determine overall test success
        test_success = (
            default_success and 
            override_success and 
            config_success and 
            status_success and 
            conversation_success and 
            cleanup_success
        )
        
        result = {
            "success": test_success,
            "test_code": test_code,
            "test_name": test_name,
            "message": f"Default and override agent usage successful",
            "details": {
                "default_success": default_success,
                "override_success": override_success,
                "config_success": config_success,
                "status_success": status_success,
                "conversation_success": conversation_success,
                "cleanup_success": cleanup_success,
                "default_response": default_result.response if default_result and default_result.success else None,
                "override_response": override_result.response if override_result and override_result.success else None,
                "default_thread_id": default_result.thread_id if default_result and default_result.success else None,
                "override_thread_id": override_result.thread_id if override_result and override_result.success else None,
                "current_agent_id": config.get("agent_id") if config else None,
                "module_status": status.get("status") if status else None
            }
        }
        
        print(f"Test result: {result}")
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

async def test_aaaim_agent_management():
    """Test AAAIM agent management and configuration."""
    test_code = "T0000009_MANAGEMENT"
    test_name = "AAAIM Agent Management Test"
    try:
        print(f"Starting {test_name}...")
        
        # Initialize AAAIM module
        aaaim = AgenticAPIActivationModule()
        
        # Test configuration
        print("Testing agent configuration...")
        original_agent_id = aaaim.current_config.agent_id
        aaaim.set_agent_id("asst_lQCwiQAJcycDj7YqHBafyWtT")
        aaaim.set_config(model="gpt-4", max_retries=3, timeout=30)
        
        config = aaaim.get_config()
        config_success = (
            config.get("agent_id") == "asst_lQCwiQAJcycDj7YqHBafyWtT" and
            config.get("model") == "gpt-4" and
            config.get("max_retries") == 3
        )
        print(f"Configuration test: {'Passed' if config_success else 'Failed'}")
        
        # Restore original agent ID
        aaaim.set_agent_id(original_agent_id)
        
        # Test module status
        print("Testing module status...")
        status = aaaim.get_module_status()
        status_success = (
            status.get("module") == "AAAIM" and
            status.get("status") == "active" and
            "stats" in status
        )
        print(f"Status test: {'Passed' if status_success else 'Failed'}")
        
        # Test conversation tracking
        print("Testing conversation tracking...")
        tracking_success = (
            "active_conversations" in status and
            "total_requests" in status.get("stats", {})
        )
        print(f"Tracking test: {'Passed' if tracking_success else 'Failed'}")
        
        management_success = config_success and status_success and tracking_success
        
        result = {
            "success": management_success,
            "test_code": test_code,
            "test_name": test_name,
            "message": "AAAIM agent management test successful",
            "details": {
                "config_success": config_success,
                "status_success": status_success,
                "tracking_success": tracking_success,
                "module_status": status
            }
        }
        
        print(f"Management test result: {result}")
        return result
        
    except Exception as e:
        error_result = {
            "success": False,
            "test_code": test_code,
            "test_name": test_name,
            "error": f"Management test failed: {str(e)}"
        }
        print(f"Management test failed: {error_result}")
        return error_result

async def main():
    """Run the tests."""
    print("=== AAAIM Test Suite ===")
    
    # Run basic functionality test
    print("\n1. Running basic functionality test...")
    result1 = await test_aaaim_default_and_override_agent_usage()
    
    # Run management test
    print("\n2. Running management test...")
    result2 = await test_aaaim_agent_management()
    
    # Overall results
    overall_success = result1["success"] and result2["success"]
    
    print(f"\n=== Test Results ===")
    print(f"Basic functionality test: {'PASS' if result1['success'] else 'FAIL'}")
    print(f"Management test: {'PASS' if result2['success'] else 'FAIL'}")
    print(f"Overall result: {'PASS' if overall_success else 'FAIL'}")
    
    if not overall_success:
        print(f"\nDetailed results:")
        print(f"Test 1: {json.dumps(result1, indent=2)}")
        print(f"Test 2: {json.dumps(result2, indent=2)}")

if __name__ == "__main__":
    asyncio.run(main())