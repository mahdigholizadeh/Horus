"""
test_o00000028: DCM Request Storage and Retrieval

Objective: Test request data storage and retrieval operations
Test Description:
- Store request data in appropriate partitions
- Test data retrieval by priority
- Verify data integrity
- Check query performance
- Test data indexing
- Validate data consistency
"""

import asyncio
import tempfile
import os
import shutil
from datetime import datetime
from typing import Dict, Any

# Import DCM module
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from DCM.dcm import DatabaseControlModule, Priority, RequestStatus

async def test_o00000028_request_storage_and_retrieval():
    """Test DCM Request Storage and Retrieval functionality."""
    
    # Setup
    config = {
        'database': {
            'type': 'sqlite',
            'path': ':memory:',  # Use in-memory database for testing
            'priority_partitions': True,
            'backup_enabled': True,
            'backup_interval': 60,
            'max_backups': 5
        },
        'logging': {
            'level': 'DEBUG'
        }
    }
    
    db_path, temp_dir = create_temp_db_path()
    dcm = await create_dcm_instance(config, db_path)
    
    try:
        # Test data
        test_requests = [
            {
                'request_id': 'req_001',
                'priority': Priority.A,
                'status': RequestStatus.PENDING,
                'request_type': 'report_generation',
                'source_module': 'TDIM',
                'data': {'route': 'forward', 'parameters': {'param1': 'value1'}},
                'metadata': {'user_id': 'user1', 'session_id': 'sess1'}
            },
            {
                'request_id': 'req_002',
                'priority': Priority.B,
                'status': RequestStatus.PROCESSING,
                'request_type': 'data_processing',
                'source_module': 'RCMIM',
                'data': {'data_type': 'json', 'content': {'key': 'value'}},
                'metadata': {'user_id': 'user2', 'session_id': 'sess2'}
            },
            {
                'request_id': 'req_003',
                'priority': Priority.C,
                'status': RequestStatus.COMPLETED,
                'request_type': 'report_delivery',
                'source_module': 'DSM',
                'data': {'delivery_method': 'https', 'destination': 'server1'},
                'metadata': {'user_id': 'user3', 'session_id': 'sess3'}
            }
        ]
        
        # Store requests
        for req in test_requests:
            success = await dcm.insert_request(
                request_id=req['request_id'],
                priority=req['priority'],
                status=req['status'],
                request_type=req['request_type'],
                source_module=req['source_module'],
                data=req['data'],
                metadata=req['metadata']
            )
            assert success, f"Failed to store request {req['request_id']}"
        
        # Wait for the operation queue to be processed
        await asyncio.sleep(0.1)
        
        # Test retrieval by request ID
        for req in test_requests:
            retrieved = await dcm.get_request(req['request_id'])
            assert retrieved is not None, f"Failed to retrieve request {req['request_id']}"
            assert retrieved['request_id'] == req['request_id']
            assert retrieved['priority'] == req['priority'].value
            assert retrieved['status'] == req['status'].value
            assert retrieved['request_type'] == req['request_type']
            assert retrieved['source_module'] == req['source_module']
            assert retrieved['data'] == req['data']
            assert retrieved['metadata'] == req['metadata']
        
        # Test retrieval by priority
        for priority in [Priority.A, Priority.B, Priority.C]:
            requests = await dcm.get_requests_by_priority(priority)
            assert len(requests) > 0, f"No requests found for priority {priority.value}"
            
            for req in requests:
                assert req['priority'] == priority.value, f"Wrong priority for request {req['request_id']}"
        
        # Test retrieval by status
        pending_requests = await dcm.get_requests_by_priority(Priority.A, RequestStatus.PENDING)
        assert len(pending_requests) == 1, "Should have 1 pending request for priority A"
        
        processing_requests = await dcm.get_requests_by_priority(Priority.B, RequestStatus.PROCESSING)
        assert len(processing_requests) == 1, "Should have 1 processing request for priority B"
        
        completed_requests = await dcm.get_requests_by_priority(Priority.C, RequestStatus.COMPLETED)
        assert len(completed_requests) == 1, "Should have 1 completed request for priority C"
        
        # Test data integrity
        for req in test_requests:
            retrieved = await dcm.get_request(req['request_id'])
            # Verify data structure integrity
            assert 'request_id' in retrieved
            assert 'created_at' in retrieved
            assert 'updated_at' in retrieved
            assert retrieved['created_at'] <= retrieved['updated_at']
        
        # Test performance with multiple requests
        start_time = datetime.now()
        for i in range(100):
            await dcm.insert_request(
                request_id=f'perf_req_{i:03d}',
                priority=Priority.D,
                status=RequestStatus.PENDING,
                request_type='performance_test',
                source_module='TEST',
                data={'test_id': i},
                metadata={'test_metadata': f'value_{i}'}
            )
        end_time = datetime.now()
        
        # Performance should be reasonable (less than 1 second for 100 requests)
        duration = (end_time - start_time).total_seconds()
        assert duration < 1.0, f"Performance test took too long: {duration:.2f} seconds"
        
        print(f"✓ test_o00000028: DCM Request Storage and Retrieval - PASSED")
        print(f"  - Stored and retrieved {len(test_requests)} test requests")
        print(f"  - Verified data integrity across all priorities")
        print(f"  - Performance test: {duration:.3f} seconds for 100 requests")
        
    finally:
        await dcm.stop()
        # Cleanup
        try:
            shutil.rmtree(temp_dir)
        except Exception:
            pass

def create_temp_db_path():
    """Create temporary database path for testing."""
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, 'test_ocm.db')
    return db_path, temp_dir

async def create_dcm_instance(config, db_path):
    """Create DCM instance for testing."""
    # Update config to use temp path
    config['database']['path'] = db_path
    dcm = DatabaseControlModule(config)
    await dcm.start()
    return dcm

if __name__ == "__main__":
    asyncio.run(test_o00000028_request_storage_and_retrieval()) 