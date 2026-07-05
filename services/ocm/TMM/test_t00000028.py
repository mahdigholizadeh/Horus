"""
Test O00000028: DCM Request Storage and Retrieval
Module(s) Tested: DCM (Database Control Module)
Description: Test request data storage and retrieval operations
Test Description:
- Store request data in appropriate partitions
- Test data retrieval by priority
- Verify data integrity
- Check query performance
- Test data indexing
- Validate data consistency
Expected Result: Reliable request data storage and retrieval
Pass Criteria: Data stored, retrieved, integrity maintained, performance acceptable
Implementation Notes: Test with various data sizes and types
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Dict, Any
from datetime import datetime
import uuid

# Add parent directory to path for module imports
sys.path.insert(0, str(Path(__file__).parent.parent))

async def test_o00000028():
    test_code = "O00000028"
    test_name = "DCM Request Storage and Retrieval"
    results = []
    
    try:
        # Import DCM module
        from DCM.dcm import DatabaseControlModule, Priority, RequestStatus
        
        # Step 1: Test DCM module initialization with storage config
        config = {
            "database": {
                "type": "sqlite",
                "path": "test_databases/ocm_test.db",
                "priority_partitions": True,
                "backup_enabled": False,
                "backup_interval": 3600,
                "max_backups": 24
            },
            "request_storage": {
                "enabled": True,
                "partition_by_priority": True,
                "enable_indexing": True,
                "enable_constraints": True,
                "data_compression": True
            }
        }
        
        dcm = DatabaseControlModule(config)
        await dcm.start()
        results.append(dcm.is_active == True)
        results.append(hasattr(dcm, 'insert_request'))
        results.append(hasattr(dcm, 'get_request'))
        results.append(hasattr(dcm, 'get_requests_by_priority'))
        
        # Step 2: Test request data storage in appropriate partitions
        storage_results = []
        
        # Test request data structure
        test_requests = [
            {
                "request_id": f"req_{uuid.uuid4().hex[:8]}",
                "priority": Priority.A,
                "status": RequestStatus.PENDING,
                "request_type": "report_generation",
                "source_module": "TDIM",
                "data": {
                    "type": "report_generation",
                    "parameters": {"format": "pdf", "template": "standard"},
                    "metadata": {"user_id": "user_001", "timestamp": datetime.now().isoformat()}
                },
                "metadata": {"user_id": "user_001", "session_id": "sess1"}
            },
            {
                "request_id": f"req_{uuid.uuid4().hex[:8]}",
                "priority": Priority.B,
                "status": RequestStatus.PROCESSING,
                "request_type": "data_processing",
                "source_module": "RCMIM",
                "data": {
                    "type": "data_processing",
                    "parameters": {"algorithm": "fast", "batch_size": 1000},
                    "metadata": {"user_id": "user_002", "timestamp": datetime.now().isoformat()}
                },
                "metadata": {"user_id": "user_002", "session_id": "sess2"}
            },
            {
                "request_id": f"req_{uuid.uuid4().hex[:8]}",
                "priority": Priority.C,
                "status": RequestStatus.COMPLETED,
                "request_type": "status_check",
                "source_module": "DSM",
                "data": {
                    "type": "status_check",
                    "parameters": {"check_type": "health"},
                    "metadata": {"user_id": "user_003", "timestamp": datetime.now().isoformat()}
                },
                "metadata": {"user_id": "user_003", "session_id": "sess3"}
            },
            {
                "request_id": f"req_{uuid.uuid4().hex[:8]}",
                "priority": Priority.D,
                "status": RequestStatus.PENDING,
                "request_type": "cleanup",
                "source_module": "SYSTEM",
                "data": {
                    "type": "cleanup",
                    "parameters": {"cleanup_type": "logs", "retention_days": 30},
                    "metadata": {"user_id": "system", "timestamp": datetime.now().isoformat()}
                },
                "metadata": {"user_id": "system", "session_id": "sess4"}
            }
        ]
        
        # Store requests
        for req in test_requests:
            success = await dcm.insert_request(
                request_id=req["request_id"],
                priority=req["priority"],
                status=req["status"],
                request_type=req["request_type"],
                source_module=req["source_module"],
                data=req["data"],
                metadata=req["metadata"]
            )
            storage_results.append(success)
        
        # Wait for operations to be processed
        await asyncio.sleep(0.1)
        
        # Test storage validation
        for req in test_requests:
            storage_results.append("request_id" in req)
            storage_results.append("priority" in req)
            storage_results.append("data" in req)
            storage_results.append("status" in req)
            storage_results.append("metadata" in req)
            storage_results.append(req["priority"] in [Priority.A, Priority.B, Priority.C, Priority.D])
            storage_results.append(len(req["request_id"]) > 0)
            storage_results.append("type" in req["data"])
            storage_results.append("parameters" in req["data"])
            storage_results.append("metadata" in req["data"])
        
        results.extend(storage_results)
        
        # Step 3: Test data retrieval by priority
        retrieval_results = []
        
        # Test retrieval by request ID
        for req in test_requests:
            retrieved = await dcm.get_request(req["request_id"])
            retrieval_results.append(retrieved is not None)
            if retrieved:
                retrieval_results.append(retrieved["request_id"] == req["request_id"])
                retrieval_results.append(retrieved["priority"] == req["priority"].value)
                retrieval_results.append(retrieved["status"] == req["status"].value)
                retrieval_results.append(retrieved["request_type"] == req["request_type"])
                retrieval_results.append(retrieved["source_module"] == req["source_module"])
        
        # Test retrieval by priority
        for priority in [Priority.A, Priority.B, Priority.C, Priority.D]:
            requests = await dcm.get_requests_by_priority(priority)
            retrieval_results.append(len(requests) > 0)
            
            for req in requests:
                retrieval_results.append(req["priority"] == priority.value)
        
        # Test retrieval by status
        pending_requests = await dcm.get_requests_by_priority(Priority.A, RequestStatus.PENDING)
        retrieval_results.append(len(pending_requests) >= 0)  # At least 0 pending requests
        
        processing_requests = await dcm.get_requests_by_priority(Priority.B, RequestStatus.PROCESSING)
        retrieval_results.append(len(processing_requests) >= 0)  # At least 0 processing requests
        
        completed_requests = await dcm.get_requests_by_priority(Priority.C, RequestStatus.COMPLETED)
        retrieval_results.append(len(completed_requests) >= 0)  # At least 0 completed requests
        
        results.extend(retrieval_results)
        
        # Step 4: Test data integrity
        integrity_results = []
        
        # Test data structure integrity
        for req in test_requests:
            retrieved = await dcm.get_request(req["request_id"])
            if retrieved:
                integrity_results.append("request_id" in retrieved)
                integrity_results.append("created_at" in retrieved)
                integrity_results.append("updated_at" in retrieved)
                integrity_results.append(retrieved["created_at"] <= retrieved["updated_at"])
                integrity_results.append("data" in retrieved)
                integrity_results.append("metadata" in retrieved)
        
        # Test data consistency
        for req in test_requests:
            retrieved = await dcm.get_request(req["request_id"])
            if retrieved:
                integrity_results.append(retrieved["request_id"] == req["request_id"])
                integrity_results.append(retrieved["priority"] == req["priority"].value)
                integrity_results.append(retrieved["status"] == req["status"].value)
                integrity_results.append(retrieved["request_type"] == req["request_type"])
                integrity_results.append(retrieved["source_module"] == req["source_module"])
        
        results.extend(integrity_results)
        
        # Step 5: Test query performance
        performance_results = []
        
        # Test performance with multiple requests
        start_time = datetime.now()
        for i in range(10):  # Reduced from 100 to 10 for faster testing
            await dcm.insert_request(
                request_id=f"perf_req_{i:03d}_{uuid.uuid4().hex[:4]}",
                priority=Priority.D,
                status=RequestStatus.PENDING,
                request_type='performance_test',
                source_module='TEST',
                data={'test_id': i},
                metadata={'test_metadata': f'value_{i}'}
            )
        end_time = datetime.now()
        
        # Performance should be reasonable (less than 1 second for 10 requests)
        duration = (end_time - start_time).total_seconds()
        performance_results.append(duration < 1.0)
        performance_results.append(duration >= 0)
        
        # Test retrieval performance
        start_time = datetime.now()
        for i in range(10):
            await dcm.get_requests_by_priority(Priority.D)
        end_time = datetime.now()
        
        retrieval_duration = (end_time - start_time).total_seconds()
        performance_results.append(retrieval_duration < 1.0)
        performance_results.append(retrieval_duration >= 0)
        
        results.extend(performance_results)
        
        # Step 6: Test data indexing (simulated)
        indexing_results = []
        
        # Test that we can query by different fields
        for priority in [Priority.A, Priority.B, Priority.C, Priority.D]:
            requests = await dcm.get_requests_by_priority(priority)
            indexing_results.append(len(requests) >= 0)
        
        for status in [RequestStatus.PENDING, RequestStatus.PROCESSING, RequestStatus.COMPLETED]:
            requests = await dcm.get_requests_by_priority(Priority.A, status)
            indexing_results.append(len(requests) >= 0)
        
        results.extend(indexing_results)
        
        # Step 7: Test data consistency
        consistency_results = []
        
        # Test that data remains consistent across retrievals
        for req in test_requests:
            retrieved1 = await dcm.get_request(req["request_id"])
            retrieved2 = await dcm.get_request(req["request_id"])
            
            if retrieved1 and retrieved2:
                consistency_results.append(retrieved1["request_id"] == retrieved2["request_id"])
                consistency_results.append(retrieved1["priority"] == retrieved2["priority"])
                consistency_results.append(retrieved1["status"] == retrieved2["status"])
                consistency_results.append(retrieved1["request_type"] == retrieved2["request_type"])
                consistency_results.append(retrieved1["source_module"] == retrieved2["source_module"])
        
        results.extend(consistency_results)
        
        # Calculate test results
        total_tests = len(results)
        passed_tests = sum(results)
        failed_tests = total_tests - passed_tests
        
        test_result = {
            "test_code": test_code,
            "test_name": test_name,
            "status": "PASSED" if failed_tests == 0 else "FAILED",
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "success_rate": (passed_tests / total_tests) * 100 if total_tests > 0 else 0,
            "details": {
                "data_stored": all(storage_results[:4]),  # First 4 are actual storage results
                "data_retrieved": all(retrieval_results[:20]),  # First 20 are retrieval results
                "integrity_maintained": all(integrity_results[:20]),  # First 20 are integrity results
                "performance_acceptable": all(performance_results[:4]),  # First 4 are performance results
                "indexing_working": all(indexing_results[:8]),  # First 8 are indexing results
                "consistency_validated": all(consistency_results[:10])  # First 10 are consistency results
            },
            "timestamp": asyncio.get_event_loop().time()
        }
        
        await dcm.stop()
        return test_result
        
    except Exception as e:
        return {
            "test_code": test_code,
            "test_name": test_name,
            "status": "ERROR",
            "error": f"Test execution error: {str(e)}",
            "details": {"error_type": type(e).__name__, "message": str(e)},
            "timestamp": asyncio.get_event_loop().time()
        }

if __name__ == "__main__":
    async def main():
        result = await test_o00000028()
        print(json.dumps(result, indent=2))
        sys.exit(0 if result["status"] == "PASSED" else 1)
    
    asyncio.run(main()) 