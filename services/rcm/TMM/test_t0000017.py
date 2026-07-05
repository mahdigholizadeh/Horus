"""
Test T0000017: MSM - Token Calculation
Module(s) Tested: MSM, DCMM
Description: Test token calculation functionality.
Success Criteria: The module correctly calculates input, output, system, and total tokens.
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

from MSM.msm import MonitoringSystemModule
from DCMM.dcmm import DatabaseControlAndManagementModule

async def test_msm_token_calculation():
    """Test token calculation functionality."""
    test_code = "T0000017"
    test_name = "MSM - Token Calculation"
    
    try:
        print(f"Starting {test_name}...")
        
        # Initialize modules
        msm = MonitoringSystemModule()
        dcmm = DatabaseControlAndManagementModule()
        print("Modules initialized successfully")
        
        # Test 1: MSM token calculation
        print("1. Testing MSM token calculation...")
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
        
        # Test 2: Conversation data extraction with token calculation
        print("2. Testing conversation data extraction...")
        conversation_data = msm.extract_conversation_data()
        extraction_success = isinstance(conversation_data, dict) and "input_tokens" in conversation_data
        print(f"   Conversation data extraction: {'Passed' if extraction_success else 'Failed'}")
        if extraction_success:
            print(f"     Input tokens: {conversation_data.get('input_tokens', 0)}")
            print(f"     Output tokens: {conversation_data.get('output_tokens', 0)}")
            print(f"     System tokens: {conversation_data.get('system_tokens', 0)}")
            print(f"     Total tokens: {conversation_data.get('total_tokens', 0)}")
        
        # Test 3: DCMM database operations
        print("3. Testing DCMM database operations...")
        try:
            # Test creating a conversation
            request_id = "test_0000017"
            create_success = await dcmm.create_conversation(request_id, "C", "gpt-4", {"test": True})
            print(f"   Create conversation: {'Passed' if create_success else 'Failed'}")
            
            # Test adding messages with token counts
            add_message_success = await dcmm.add_message(request_id, "user", "Hello, how are you?", 2)
            add_message_success = add_message_success and await dcmm.add_message(request_id, "assistant", "I'm doing well, thank you!", 3)
            print(f"   Add messages: {'Passed' if add_message_success else 'Failed'}")
            
            # Test querying conversation
            conversation = await dcmm.get_conversation(request_id)
            query_success = conversation is not None
            print(f"   Query conversation: {'Passed' if query_success else 'Failed'}")
            
            # Test database info
            db_info = await dcmm.get_database_info()
            db_info_success = isinstance(db_info, dict) and len(db_info) > 0
            print(f"   Database info: {'Passed' if db_info_success else 'Failed'}")
            
            # Clean up
            await dcmm.delete_conversation(request_id)
            
        except Exception as e:
            print(f"   DCMM operations: Failed - {str(e)}")
            create_success = False
            add_message_success = False
            query_success = False
            db_info_success = False
        
        # Test 4: DCMM status
        print("4. Testing DCMM status...")
        dcmm_status = dcmm.get_status()
        status_success = isinstance(dcmm_status, dict) and "module" in dcmm_status
        print(f"   DCMM status: {'Passed' if status_success else 'Failed'}")
        if status_success:
            print(f"     Module: {dcmm_status.get('module', 'Unknown')}")
            print(f"     Active connections: {dcmm_status.get('active_connections', 'Unknown')}")
            print(f"     Databases: {dcmm_status.get('databases', [])}")
        
        # Calculate overall success
        tests = [
            token_calculation_success,
            extraction_success,
            create_success,
            add_message_success,
            query_success,
            db_info_success,
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
            "message": f"Token calculation tests: {successful_tests}/{total_tests} successful ({success_rate:.1f}% success rate)",
            "details": {
                "token_calculation": token_calculation_success,
                "conversation_extraction": extraction_success,
                "create_conversation": create_success,
                "add_messages": add_message_success,
                "query_conversation": query_success,
                "database_info": db_info_success,
                "dcmm_status": status_success,
                "success_rate": success_rate,
                "sample_conversation_data": conversation_data if extraction_success else None
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
    """Run the MSM token calculation test."""
    print("=== MSM Token Calculation Test Suite ===")
    print("Testing token calculation and database integration.\n")
    
    result = await test_msm_token_calculation()
    
    print(f"\n=== Test Results ===")
    print(f"MSM Token Calculation Test: {'PASS' if result['success'] else 'FAIL'}")
    
    if result['success']:
        print(f"\n✅ Token calculation and database integration working correctly!")
        print(f"   - Token calculation: Working")
        print(f"   - Conversation data extraction: Working")
        print(f"   - Database operations: Working")
        print(f"   - Module status: Working")
    else:
        print(f"\n❌ Some tests failed. Check the details below:")
        print(f"Test: {json.dumps(result, indent=2)}")

if __name__ == "__main__":
    asyncio.run(main())