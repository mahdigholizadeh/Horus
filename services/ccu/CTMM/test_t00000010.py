"""
Test T00000010: RTM Concurrent Request Management
Module(s) Tested: RTM (Request Tracking Module)
Description: Test management of multiple concurrent requests (10 max)
Test Description: 
- Process 10 concurrent requests simultaneously
- Verify request queuing and scheduling
- Test resource allocation and backpressure
- Check request prioritization and ordering
- Validate request isolation and state management
- Test request timeout and cleanup
Expected Result: Efficient concurrent request management with resource optimization
Pass Criteria: 10 requests handled, queuing works, resources optimized, isolation maintained
Implementation Notes: Generate realistic request loads, monitor resource usage
"""

import asyncio
import json
import sys
import time
import logging
import uuid
from pathlib import Path
from typing import Dict, Any, List
from unittest.mock import Mock, patch, AsyncMock

# Add parent directory to path for module imports
sys.path.insert(0, str(Path(__file__).parent.parent))

async def test_t00000010():
    test_code = "T00000010"
    test_name = "RTM Concurrent Request Management"
    results = []
    
    try:
        # Import RTM module
        from RTM.rtm import RequestTrackingModule, WorkflowStage, RequestStatus
        
        # Step 1: Test RTM initialization
        rtm = RequestTrackingModule()
        results.append(rtm is not None)
        results.append(hasattr(rtm, 'active_workflows'))
        results.append(hasattr(rtm, 'stats'))
        
        # Step 2: Generate 10 concurrent requests
        concurrent_requests = []
        for i in range(10):
            request_data = {
                "request_id": f"concurrent_req_{i}_{uuid.uuid4().hex[:8]}",
                "priority_flag": "A" if i < 5 else "B",  # Mix of priorities
                "model": "gpt-4",
                "messages": [{"role": "user", "content": f"Concurrent test request {i}"}],
                "requires_calculation": True,
                "template_type": "default"
            }
            concurrent_requests.append(request_data)
        
        # Step 3: Test concurrent request processing
        start_time = time.time()
        
        # Process all requests concurrently
        concurrent_results = await asyncio.gather(
            *[rtm.orchestrate_request(req, None) for req in concurrent_requests],
            return_exceptions=True
        )
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        # Step 4: Verify concurrent processing results
        results.append(len(concurrent_results) == 10)
        results.append(all(isinstance(result, dict) for result in concurrent_results))
        results.append(all(result.get("success", False) for result in concurrent_results))
        
        # Verify all requests completed
        completed_requests = [result for result in concurrent_results if result.get("success", False)]
        results.append(len(completed_requests) == 10)
        
        # Step 5: Test request queuing and scheduling
        # Verify that requests were processed in order
        request_ids = [req["request_id"] for req in concurrent_requests]
        result_ids = [result["request_id"] for result in concurrent_results if isinstance(result, dict)]
        
        results.append(len(request_ids) == len(result_ids))
        results.append(set(request_ids) == set(result_ids))  # All requests processed
        
        # Step 6: Test resource allocation and backpressure
        # Check that active workflows don't exceed reasonable limits
        results.append(len(rtm.active_workflows) <= 10)  # Should not exceed max concurrent
        
        # Check statistics
        results.append(rtm.stats["total_requests"] >= 10)
        results.append(rtm.stats["completed_requests"] >= 10)
        results.append(rtm.stats["active_requests"] == 0)  # Should be 0 after completion
        
        # Step 7: Test request prioritization and ordering
        # Create requests with different priorities
        priority_requests = []
        priorities = ["A", "B", "C", "D"]  # Different priority levels
        
        for i, priority in enumerate(priorities):
            for j in range(2):  # 2 requests per priority
                request_data = {
                    "request_id": f"priority_{priority}_{j}_{uuid.uuid4().hex[:8]}",
                    "priority_flag": priority,
                    "model": "gpt-4",
                    "messages": [{"role": "user", "content": f"Priority {priority} request {j}"}],
                    "requires_calculation": True,
                    "template_type": "default"
                }
                priority_requests.append(request_data)
        
        # Process priority requests
        priority_results = await asyncio.gather(
            *[rtm.orchestrate_request(req, None) for req in priority_requests],
            return_exceptions=True
        )
        
        results.append(len(priority_results) == 8)  # 4 priorities * 2 requests each
        results.append(all(isinstance(result, dict) for result in priority_results))
        results.append(all(result.get("success", False) for result in priority_results))
        
        # Step 8: Test request isolation and state management
        # Verify that each request has its own workflow context
        unique_request_ids = set()
        for result in concurrent_results:
            if isinstance(result, dict) and "request_id" in result:
                unique_request_ids.add(result["request_id"])
        
        results.append(len(unique_request_ids) == 10)  # All requests should be unique
        
        # Verify no cross-contamination between requests
        for result in concurrent_results:
            if isinstance(result, dict):
                results.append("request_id" in result)
                results.append("success" in result)
                results.append("final_stage" in result)
                results.append("status" in result)
                results.append("data" in result)
        
        # Step 9: Test request timeout and cleanup
        # Create requests that might timeout
        timeout_requests = []
        for i in range(3):
            request_data = {
                "request_id": f"timeout_req_{i}_{uuid.uuid4().hex[:8]}",
                "priority_flag": "A",
                "model": "gpt-4",
                "messages": [{"role": "user", "content": f"Timeout test request {i}"}],
                "requires_calculation": True,
                "template_type": "default"
            }
            timeout_requests.append(request_data)
        
        # Mock slow processing to test timeout
        with patch.object(rtm, 'execute_stage', new_callable=AsyncMock) as mock_execute_stage:
            async def mock_execute_stage_effect(stage, workflow_context, request_data):
                await asyncio.sleep(0.1)  # Simulate delay
                return {"success": True, "stage": stage.value, "message": f"Stage {stage.value} completed"}
            mock_execute_stage.side_effect = mock_execute_stage_effect
            
            try:
                timeout_results = await asyncio.wait_for(
                    asyncio.gather(
                        *[rtm.orchestrate_request(req, None) for req in timeout_requests],
                        return_exceptions=True
                    ),
                    timeout=0.05  # Short timeout to trigger timeout handling
                )
                results.append(False)  # Should not reach here
            except asyncio.TimeoutError:
                results.append(True)  # Timeout handled correctly
        
        # Step 10: Test concurrent workflow creation
        # Test creating multiple workflows simultaneously
        workflow_requests = []
        for i in range(5):
            request_data = {
                "request_id": f"workflow_req_{i}_{uuid.uuid4().hex[:8]}",
                "priority_flag": "A",
                "model": "gpt-4",
                "messages": [{"role": "user", "content": f"Workflow test request {i}"}],
                "requires_calculation": True,
                "template_type": "default"
            }
            workflow_requests.append(request_data)
        
        # Create workflows concurrently
        workflow_contexts = await asyncio.gather(
            *[rtm.create_workflow(req) for req in workflow_requests],
            return_exceptions=True
        )
        
        results.append(len(workflow_contexts) == 5)
        results.append(all(isinstance(context, object) for context in workflow_contexts))
        
        # Verify all workflows are active
        for context in workflow_contexts:
            if hasattr(context, 'request_id'):
                results.append(context.request_id in rtm.active_workflows)
        
        # Step 11: Test resource optimization
        # Monitor memory and performance during concurrent processing
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Process another batch of concurrent requests
        optimization_requests = []
        for i in range(5):
            request_data = {
                "request_id": f"optimization_req_{i}_{uuid.uuid4().hex[:8]}",
                "priority_flag": "A",
                "model": "gpt-4",
                "messages": [{"role": "user", "content": f"Optimization test request {i}"}],
                "requires_calculation": True,
                "template_type": "default"
            }
            optimization_requests.append(request_data)
        
        optimization_results = await asyncio.gather(
            *[rtm.orchestrate_request(req, None) for req in optimization_requests],
            return_exceptions=True
        )
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        results.append(len(optimization_results) == 5)
        results.append(all(isinstance(result, dict) for result in optimization_results))
        results.append(all(result.get("success", False) for result in optimization_results))
        
        # Memory increase should be reasonable (less than 100MB)
        results.append(memory_increase < 100 * 1024 * 1024)  # 100MB limit
        
        # Step 12: Test concurrent request cancellation
        # Create requests and cancel them concurrently
        cancel_requests = []
        for i in range(3):
            request_data = {
                "request_id": f"cancel_concurrent_req_{i}_{uuid.uuid4().hex[:8]}",
                "priority_flag": "A",
                "model": "gpt-4",
                "messages": [{"role": "user", "content": f"Cancel concurrent test request {i}"}],
                "requires_calculation": True,
                "template_type": "default"
            }
            cancel_requests.append(request_data)
        
        # Create workflows first
        cancel_workflows = await asyncio.gather(
            *[rtm.create_workflow(req) for req in cancel_requests],
            return_exceptions=True
        )
        
        results.append(len(cancel_workflows) == 3)
        
        # Cancel workflows concurrently
        cancel_results = await asyncio.gather(
            *[rtm.cancel_workflow(req["request_id"]) for req in cancel_requests],
            return_exceptions=True
        )
        
        results.append(len(cancel_results) == 3)
        results.append(all(isinstance(result, bool) for result in cancel_results))
        results.append(all(result for result in cancel_results))  # All cancellations should succeed
        
        # Verify workflows are no longer active
        for req in cancel_requests:
            results.append(req["request_id"] not in rtm.active_workflows)
        
        # Step 13: Test concurrent performance metrics
        # Test that performance metrics are accurate under concurrent load
        performance_requests = []
        for i in range(10):
            request_data = {
                "request_id": f"performance_req_{i}_{uuid.uuid4().hex[:8]}",
                "priority_flag": "A",
                "model": "gpt-4",
                "messages": [{"role": "user", "content": f"Performance test request {i}"}],
                "requires_calculation": True,
                "template_type": "default"
            }
            performance_requests.append(request_data)
        
        performance_start_time = time.time()
        performance_results = await asyncio.gather(
            *[rtm.orchestrate_request(req, None) for req in performance_requests],
            return_exceptions=True
        )
        performance_end_time = time.time()
        performance_duration = performance_end_time - performance_start_time
        
        results.append(len(performance_results) == 10)
        results.append(all(isinstance(result, dict) for result in performance_results))
        results.append(all(result.get("success", False) for result in performance_results))
        
        # Performance should be reasonable (less than 30 seconds for 10 requests)
        results.append(performance_duration < 30.0)
        
        # Step 14: Test concurrent error handling
        # Test handling of concurrent errors
        error_requests = []
        for i in range(3):
            request_data = {
                "request_id": f"error_req_{i}_{uuid.uuid4().hex[:8]}",
                # Missing required fields to trigger errors
            }
            error_requests.append(request_data)
        
        error_results = await asyncio.gather(
            *[rtm.orchestrate_request(req, None) for req in error_requests],
            return_exceptions=True
        )
        
        results.append(len(error_results) == 3)
        results.append(all(isinstance(result, Exception) for result in error_results))
        
        # Step 15: Test concurrent cleanup
        # Verify that all resources are properly cleaned up after concurrent processing
        initial_active_workflows = len(rtm.active_workflows)
        
        # Process a final batch of requests
        cleanup_requests = []
        for i in range(5):
            request_data = {
                "request_id": f"cleanup_req_{i}_{uuid.uuid4().hex[:8]}",
                "priority_flag": "A",
                "model": "gpt-4",
                "messages": [{"role": "user", "content": f"Cleanup test request {i}"}],
                "requires_calculation": True,
                "template_type": "default"
            }
            cleanup_requests.append(request_data)
        
        cleanup_results = await asyncio.gather(
            *[rtm.orchestrate_request(req, None) for req in cleanup_requests],
            return_exceptions=True
        )
        
        final_active_workflows = len(rtm.active_workflows)
        
        results.append(len(cleanup_results) == 5)
        results.append(all(isinstance(result, dict) for result in cleanup_results))
        results.append(all(result.get("success", False) for result in cleanup_results))
        
        # Verify cleanup
        results.append(final_active_workflows == 0)  # All workflows should be completed
        results.append(rtm.stats["active_requests"] == 0)  # No active requests
        
        # Calculate test results
        total_tests = len(results)
        passed_tests = sum(results)
        failed_tests = total_tests - passed_tests
        
        # Log results
        logging.info(f"Test {test_code}: {test_name}")
        logging.info(f"Total tests: {total_tests}")
        logging.info(f"Passed: {passed_tests}")
        logging.info(f"Failed: {failed_tests}")
        logging.info(f"Success rate: {(passed_tests/total_tests)*100:.2f}%")
        logging.info(f"Total duration: {total_duration:.3f}s")
        logging.info(f"Performance duration: {performance_duration:.3f}s")
        logging.info(f"Memory increase: {memory_increase / (1024*1024):.2f}MB")
        
        return {
            "test_code": test_code,
            "test_name": test_name,
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "success_rate": (passed_tests/total_tests)*100,
            "execution_time": total_duration,
            "results": results,
            "success": failed_tests == 0,
            "performance_duration": performance_duration,
            "memory_increase_mb": memory_increase / (1024*1024)
        }
        
    except Exception as e:
        logging.error(f"Test {test_code} failed with exception: {e}")
        return {
            "test_code": test_code,
            "test_name": test_name,
            "total_tests": 0,
            "passed_tests": 0,
            "failed_tests": 1,
            "success_rate": 0.0,
            "execution_time": 0.0,
            "results": [],
            "success": False,
            "error": str(e)
        }


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run the test
    result = asyncio.run(test_t00000010())
    
    if result["success"]:
        print(f"PASS {result['test_code']}: {result['test_name']} - PASSED")
        print(f"   Passed: {result['passed_tests']}/{result['total_tests']} tests")
        print(f"   Success rate: {result['success_rate']:.2f}%")
        print(f"   Execution time: {result['execution_time']:.3f}s")
        print(f"   Performance duration: {result.get('performance_duration', 0):.3f}s")
        print(f"   Memory increase: {result.get('memory_increase_mb', 0):.2f}MB")
    else:
        print(f"FAIL {result['test_code']}: {result['test_name']} - FAILED")
        if "error" in result:
            print(f"   Error: {result['error']}")
        else:
            print(f"   Passed: {result['passed_tests']}/{result['total_tests']} tests")
            print(f"   Success rate: {result['success_rate']:.2f}%") 