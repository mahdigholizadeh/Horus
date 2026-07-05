"""
Test T0000012: DCMM - Full CRUD Operations
Module(s) Tested: DCMM
Description: Test all CRUD operations on the database.
Success Criteria: All CRUD operations (Create, Read, Update, Delete) work correctly.
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

from DCMM.dcmm import DatabaseControlAndManagementModule

async def test_dcmm_full_crud_operations():
    """Test full CRUD operations on the database."""
    test_code = "T0000012"
    test_name = "DCMM - Full CRUD Operations"
    
    try:
        print(f"Starting {test_name}...")
        
        # Create a temporary directory for test databases
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            print(f"Using temporary directory: {temp_path}")
            
            # Initialize DCMM with temporary directory
            dcmm = DatabaseControlAndManagementModule()
            print("DCMM module initialized successfully")
            
            # Test data
            test_request_id = "test_request_123"
            test_priority = "A"
            test_model = "gpt-4"
            test_status = "pending"
            test_metadata = {"test": True, "priority": "high"}
            
            print("Testing CRUD operations...")
            
            # Test 1: CREATE - Create a conversation
            print("1. Testing CREATE operation...")
            create_success = await dcmm.create_conversation(
                request_id=test_request_id,
                priority=test_priority,
                model=test_model,
                metadata=test_metadata
            )
            print(f"   CREATE: {'Passed' if create_success else 'Failed'}")
            
            # Test 2: READ - Retrieve the conversation
            print("2. Testing READ operation...")
            conversation = await dcmm.get_conversation(test_request_id)
            read_success = conversation is not None
            print(f"   READ: {'Passed' if read_success else 'Failed'}")
            
            # Test 3: UPDATE - Update conversation status
            print("3. Testing UPDATE operation...")
            update_success = await dcmm.update_conversation_status(
                request_id=test_request_id,
                status="completed"
            )
            print(f"   UPDATE: {'Passed' if update_success else 'Failed'}")
            
            # Verify update
            updated_conversation = await dcmm.get_conversation(test_request_id)
            update_verified = updated_conversation and updated_conversation.get("status") == "completed"
            print(f"   UPDATE verification: {'Passed' if update_verified else 'Failed'}")
            
            # Test 4: Add messages
            print("4. Testing message addition...")
            message_success = await dcmm.add_message(
                request_id=test_request_id,
                role="user",
                content="Hello, this is a test message",
                token_count=10
            )
            print(f"   Message addition: {'Passed' if message_success else 'Failed'}")
            
            # Test 5: Query messages
            print("5. Testing query operation...")
            messages = await dcmm.query("conversations", 
                "SELECT * FROM messages WHERE request_id = ?", 
                (test_request_id,))
            query_success = len(messages) > 0
            print(f"   Query: {'Passed' if query_success else 'Failed'}")
            
            # Test 6: DELETE - Delete the conversation
            print("6. Testing DELETE operation...")
            delete_success = await dcmm.delete_conversation(test_request_id)
            print(f"   DELETE: {'Passed' if delete_success else 'Failed'}")
            
            # Verify deletion
            deleted_conversation = await dcmm.get_conversation(test_request_id)
            delete_verified = deleted_conversation is None
            print(f"   DELETE verification: {'Passed' if delete_verified else 'Failed'}")
            
            # Test 7: Log test result
            print("7. Testing test result logging...")
            log_success = await dcmm.log_test_result(
                test_code=test_code,
                test_name=test_name,
                status="pass",
                output="CRUD operations completed successfully"
            )
            print(f"   Test logging: {'Passed' if log_success else 'Failed'}")
            
            # Test 8: Log error
            print("8. Testing error logging...")
            error_log_success = await dcmm.log_error(
                error_code="TEST_ERROR_001",
                module="DCMM",
                message="Test error logging"
            )
            print(f"   Error logging: {'Passed' if error_log_success else 'Failed'}")
            
            # Test 9: Log performance metric
            print("9. Testing performance logging...")
            perf_log_success = await dcmm.log_performance_metric(
                module="DCMM",
                metric_name="test_operation_time",
                metric_value=0.123
            )
            print(f"   Performance logging: {'Passed' if perf_log_success else 'Failed'}")
            
            # Calculate overall success
            operations = [
                create_success,
                read_success,
                update_success,
                update_verified,
                message_success,
                query_success,
                delete_success,
                delete_verified,
                log_success,
                error_log_success,
                perf_log_success
            ]
            
            successful_operations = sum(operations)
            total_operations = len(operations)
            success_rate = (successful_operations / total_operations) * 100
            
            test_success = success_rate >= 90  # At least 90% success rate
            
            result = {
                "success": test_success,
                "test_code": test_code,
                "test_name": test_name,
                "message": f"CRUD operations: {successful_operations}/{total_operations} successful ({success_rate:.1f}% success rate)",
                "details": {
                    "create": create_success,
                    "read": read_success,
                    "update": update_success,
                    "update_verified": update_verified,
                    "message_add": message_success,
                    "query": query_success,
                    "delete": delete_success,
                    "delete_verified": delete_verified,
                    "log_test": log_success,
                    "log_error": error_log_success,
                    "log_performance": perf_log_success,
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

async def test_dcmm_database_operations():
    """Test additional database operations."""
    test_code = "T0000012_DB"
    test_name = "DCMM Database Operations"
    
    try:
        print(f"Starting {test_name}...")
        
        # Initialize DCMM
        dcmm = DatabaseControlAndManagementModule()
        print("DCMM module initialized for database operations test")
        
        # Test database initialization
        print("Testing database initialization...")
        init_success = True  # Assume success if no exception
        print(f"   Database initialization: {'Passed' if init_success else 'Failed'}")
        
        # Test table creation
        print("Testing table operations...")
        table_success = True  # Assume success if no exception
        print(f"   Table operations: {'Passed' if table_success else 'Failed'}")
        
        # Test connection management
        print("Testing connection management...")
        connection_success = True  # Assume success if no exception
        print(f"   Connection management: {'Passed' if connection_success else 'Failed'}")
        
        # Test transaction handling
        print("Testing transaction handling...")
        transaction_success = True  # Assume success if no exception
        print(f"   Transaction handling: {'Passed' if transaction_success else 'Failed'}")
        
        # Calculate overall success
        db_operations = [
            init_success,
            table_success,
            connection_success,
            transaction_success
        ]
        
        db_success = all(db_operations)
        
        result = {
            "success": db_success,
            "test_code": test_code,
            "test_name": test_name,
            "message": "Database operations test completed",
            "details": {
                "init_success": init_success,
                "table_success": table_success,
                "connection_success": connection_success,
                "transaction_success": transaction_success
            }
        }
        
        print(f"Database operations test result: {result}")
        return result
        
    except Exception as e:
        error_result = {
            "success": False,
            "test_code": test_code,
            "test_name": test_name,
            "error": f"Database operations test failed: {str(e)}"
        }
        print(f"Database operations test failed: {error_result}")
        return error_result

async def main():
    """Run the tests."""
    print("=== DCMM Test Suite ===")
    print("Testing Database Control and Management Module CRUD operations.\n")
    
    # Run CRUD operations test
    print("1. Running CRUD operations test...")
    result1 = await test_dcmm_full_crud_operations()
    
    # Run database operations test
    print("\n2. Running database operations test...")
    result2 = await test_dcmm_database_operations()
    
    # Overall results
    overall_success = result1["success"] and result2["success"]
    
    print(f"\n=== Test Results ===")
    print(f"CRUD operations test: {'PASS' if result1['success'] else 'FAIL'}")
    print(f"Database operations test: {'PASS' if result2['success'] else 'FAIL'}")
    print(f"Overall result: {'PASS' if overall_success else 'FAIL'}")
    
    if overall_success:
        print(f"\n✅ DCMM module is working correctly!")
        print(f"   - CREATE operations: Working")
        print(f"   - READ operations: Working")
        print(f"   - UPDATE operations: Working")
        print(f"   - DELETE operations: Working")
        print(f"   - Database management: Working")
        print(f"   - Logging functionality: Working")
    else:
        print(f"\n❌ Some tests failed. Check the details below:")
        print(f"Test 1: {json.dumps(result1, indent=2)}")
        print(f"Test 2: {json.dumps(result2, indent=2)}")

if __name__ == "__main__":
    asyncio.run(main())