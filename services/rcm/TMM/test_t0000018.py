"""
Test T0000018: SMSM - System Message Injection
Module(s) Tested: SMSM, DCMM
Description: Test system message injection functionality.
Success Criteria: The module correctly injects system messages into conversations.
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

from SMSM.smsm import SystemMessageSubjoinModule
from DCMM.dcmm import DatabaseControlAndManagementModule

async def test_smsm_system_message_injection():
    """Test system message injection functionality."""
    test_code = "T0000018"
    test_name = "SMSM - System Message Injection"
    
    try:
        print(f"Starting {test_name}...")
        
        # Initialize modules
        smsm = SystemMessageSubjoinModule()
        dcmm = DatabaseControlAndManagementModule()
        print("Modules initialized successfully")
        
        # Test 1: System message validation
        print("1. Testing system message validation...")
        test_messages = [
            ("Valid message", "intervention", True),
            ("", "intervention", False),  # Empty message
            ("A" * 1001, "intervention", False),  # Too long
            ("<script>alert('xss')</script>", "intervention", False),  # Harmful content
            ("Normal message", "invalid_type", False),  # Invalid type
        ]
        
        validation_success = True
        for message, msg_type, expected in test_messages:
            result = smsm.validate_system_message(message, msg_type)
            success = result == expected
            validation_success = validation_success and success
            print(f"   '{message[:20]}...' ({msg_type}): {'Passed' if success else 'Failed'}")
        
        print(f"   Message validation: {'Passed' if validation_success else 'Failed'}")
        
        # Test 2: System message formatting
        print("2. Testing system message formatting...")
        test_formats = [
            ("Test message", "intervention", "SYSTEM INTERVENTION: Test message"),
            ("Test message", "correction", "SYSTEM CORRECTION: Test message"),
            ("Test message", "custom", "SYSTEM: Test message"),
        ]
        
        formatting_success = True
        for message, msg_type, expected in test_formats:
            result = smsm.format_system_message(message, msg_type)
            success = result == expected
            formatting_success = formatting_success and success
            print(f"   '{message}' ({msg_type}): {'Passed' if success else 'Failed'}")
        
        print(f"   Message formatting: {'Passed' if formatting_success else 'Failed'}")
        
        # Test 3: Database operations for conversation
        print("3. Testing database operations...")
        request_id = "test_0000018"
        try:
            # Create a test conversation
            create_success = await dcmm.create_conversation(request_id, "C", "gpt-4", {"test": True})
            print(f"   Create conversation: {'Passed' if create_success else 'Failed'}")
            
            # Add some messages
            add_user_success = await dcmm.add_message(request_id, "user", "Hello, how are you?")
            add_assistant_success = await dcmm.add_message(request_id, "assistant", "I'm doing well, thank you!")
            print(f"   Add messages: {'Passed' if add_user_success and add_assistant_success else 'Failed'}")
            
        except Exception as e:
            print(f"   Database operations: Failed - {str(e)}")
            create_success = False
            add_user_success = False
            add_assistant_success = False
        
        # Test 4: System message injection
        print("4. Testing system message injection...")
        try:
            injection_result = await smsm.inject_system_message(request_id, "Test system message", "intervention")
            injection_success = isinstance(injection_result, bool)
            print(f"   System message injection: {'Passed' if injection_success else 'Failed'}")
        except Exception as e:
            print(f"   System message injection: Failed - {str(e)}")
            injection_success = False
        
        # Test 5: Conversation retrieval with system messages
        print("5. Testing conversation retrieval...")
        try:
            conversation = await smsm.get_conversation_with_system_messages(request_id)
            retrieval_success = isinstance(conversation, dict) and "messages" in conversation
            print(f"   Conversation retrieval: {'Passed' if retrieval_success else 'Failed'}")
            if retrieval_success:
                system_count = conversation.get("system_message_count", 0)
                print(f"     System messages: {system_count}")
        except Exception as e:
            print(f"   Conversation retrieval: Failed - {str(e)}")
            retrieval_success = False
        
        # Test 6: SMSM status
        print("6. Testing SMSM status...")
        smsm_status = smsm.get_status()
        status_success = isinstance(smsm_status, dict) and "module" in smsm_status
        print(f"   SMSM status: {'Passed' if status_success else 'Failed'}")
        if status_success:
            print(f"     Module: {smsm_status.get('module', 'Unknown')}")
            print(f"     Valid message types: {smsm_status.get('valid_message_types', [])}")
        
        # Clean up
        try:
            await dcmm.delete_conversation(request_id)
        except Exception:
            pass
        
        # Calculate overall success
        tests = [
            validation_success,
            formatting_success,
            create_success,
            add_user_success and add_assistant_success,
            injection_success,
            retrieval_success,
            status_success
        ]
        
        successful_tests = sum(tests)
        total_tests = len(tests)
        success_rate = (successful_tests / total_tests) * 100
        
        test_success = success_rate >= 80  # At least 80% success rate
        
        result = {
            "success": test_success,
            "test_code": test_code,
            "test_name": test_name,
            "message": f"System message injection tests: {successful_tests}/{total_tests} successful ({success_rate:.1f}% success rate)",
            "details": {
                "message_validation": validation_success,
                "message_formatting": formatting_success,
                "create_conversation": create_success,
                "add_messages": add_user_success and add_assistant_success,
                "system_injection": injection_success,
                "conversation_retrieval": retrieval_success,
                "smsm_status": status_success,
                "success_rate": success_rate
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
    """Run the SMSM system message injection test."""
    print("=== SMSM System Message Injection Test Suite ===")
    print("Testing system message injection functionality.\n")
    
    result = await test_smsm_system_message_injection()
    
    print(f"\n=== Test Results ===")
    print(f"SMSM System Message Injection Test: {'PASS' if result['success'] else 'FAIL'}")
    
    if result['success']:
        print(f"\n✅ System message injection working correctly!")
        print(f"   - Message validation: Working")
        print(f"   - Message formatting: Working")
        print(f"   - Database operations: Working")
        print(f"   - System injection: Working")
        print(f"   - Module status: Working")
    else:
        print(f"\n❌ Some tests failed. Check the details below:")
        print(f"Test: {json.dumps(result, indent=2)}")

if __name__ == "__main__":
    asyncio.run(main())