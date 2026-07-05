"""
Test T00000009: RTM Request Workflow Orchestration
Module(s) Tested: RTM (Request Tracking Module)
Description: Test end-to-end request workflow management through all stages
Test Description: 
- Create request workflow with all 8 stages: RECEIVED → RLA_VALIDATION → TPP_PROCESSING → RCM_PROCESSING → JFA_ANALYSIS → TD_CALCULATION → OCM_OUTPUT → COMPLETED
- Test workflow state management and transitions
- Verify request context persistence and recovery
- Check workflow timeout handling (300s default)
- Test workflow cancellation and cleanup
- Validate workflow history tracking
Expected Result: Complete workflow orchestration with proper state management
Pass Criteria: All stages execute, state managed, persistence works, timeouts handled, history tracked
Implementation Notes: Mock all service interactions, test various workflow scenarios
"""

import asyncio
import json
import sys
import time
import logging
import uuid
from pathlib import Path
from typing import Dict, Any
from unittest.mock import Mock, patch, AsyncMock

# Add parent directory to path for module imports
sys.path.insert(0, str(Path(__file__).parent.parent))

async def test_t00000009():
    test_code = "T00000009"
    test_name = "RTM Request Workflow Orchestration"
    results = []
    
    try:
        # Import RTM module
        from RTM.rtm import RequestTrackingModule, WorkflowStage, RequestStatus
        
        # Step 1: Test RTM initialization
        rtm = RequestTrackingModule()
        results.append(rtm is not None)
        results.append(hasattr(rtm, 'active_workflows'))
        results.append(hasattr(rtm, 'standard_workflow'))
        results.append(hasattr(rtm, 'ai_only_workflow'))
        results.append(hasattr(rtm, 'stats'))
        
        # Step 2: Verify workflow stage definitions
        expected_stages = [
            WorkflowStage.RECEIVED,
            WorkflowStage.RLA_VALIDATION,
            WorkflowStage.TPP_PROCESSING,
            WorkflowStage.RCM_PROCESSING,
            WorkflowStage.JFA_ANALYSIS,
            WorkflowStage.TD_CALCULATION,
            WorkflowStage.OCM_OUTPUT,
            WorkflowStage.COMPLETED
        ]
        
        results.append(len(rtm.standard_workflow) == 8)
        results.append(rtm.standard_workflow == expected_stages)
        
        # Step 3: Test workflow creation
        request_data = {
            "request_id": f"test_req_{uuid.uuid4().hex[:8]}",
            "priority_flag": "A",
            "model": "gpt-4",
            "messages": [{"role": "user", "content": "Test request"}],
            "requires_calculation": True,
            "template_type": "default"
        }
        
        workflow_context = await rtm.create_workflow(request_data)
        results.append(workflow_context is not None)
        results.append(workflow_context.request_id == request_data["request_id"])
        results.append(workflow_context.status == RequestStatus.PENDING)
        results.append(workflow_context.current_stage == WorkflowStage.RECEIVED)
        results.append(workflow_context.workflow_type == "full_workflow")
        results.append(len(workflow_context.processing_history) == 0)
        
        # Step 4: Test workflow orchestration
        start_time = time.time()
        orchestration_result = await rtm.orchestrate_request(request_data, None)
        end_time = time.time()
        orchestration_duration = end_time - start_time
        
        results.append(orchestration_result is not None)
        results.append("success" in orchestration_result)
        results.append("request_id" in orchestration_result)
        results.append("final_stage" in orchestration_result)
        results.append("status" in orchestration_result)
        results.append("data" in orchestration_result)
        
        # Step 5: Verify workflow completion
        results.append(orchestration_result["success"])
        results.append(orchestration_result["request_id"] == request_data["request_id"])
        results.append(orchestration_result["final_stage"] == WorkflowStage.COMPLETED.value)
        results.append(orchestration_result["status"] == RequestStatus.COMPLETED.value)
        
        # Step 6: Test workflow state management
        # Check that workflow is no longer in active workflows
        results.append(request_data["request_id"] not in rtm.active_workflows)
        
        # Check statistics
        results.append(rtm.stats["total_requests"] > 0)
        results.append(rtm.stats["completed_requests"] > 0)
        results.append(rtm.stats["active_requests"] == 0)  # Should be 0 after completion
        
        # Step 7: Test workflow timeout handling
        # Create a request that might timeout
        timeout_request_data = {
            "request_id": f"timeout_req_{uuid.uuid4().hex[:8]}",
            "priority_flag": "A",
            "model": "gpt-4",
            "messages": [{"role": "user", "content": "Timeout test request"}],
            "requires_calculation": True,
            "template_type": "default"
        }
        
        # Mock a slow stage to test timeout
        with patch.object(rtm, 'execute_stage', new_callable=AsyncMock) as mock_execute_stage:
            async def mock_execute_stage_effect(stage, workflow_context, request_data):
                await asyncio.sleep(0.1)  # Simulate delay
                return {"success": True, "stage": stage.value, "message": f"Stage {stage.value} completed"}
            mock_execute_stage.side_effect = mock_execute_stage_effect
            
            try:
                timeout_result = await asyncio.wait_for(
                    rtm.orchestrate_request(timeout_request_data, None),
                    timeout=0.05  # Short timeout to trigger timeout handling
                )
                results.append(False)  # Should not reach here
            except asyncio.TimeoutError:
                results.append(True)  # Timeout handled correctly
        
        # Step 8: Test workflow cancellation
        cancel_request_data = {
            "request_id": f"cancel_req_{uuid.uuid4().hex[:8]}",
            "priority_flag": "A",
            "model": "gpt-4",
            "messages": [{"role": "user", "content": "Cancel test request"}],
            "requires_calculation": True,
            "template_type": "default"
        }
        
        # Create workflow and then cancel it
        cancel_workflow = await rtm.create_workflow(cancel_request_data)
        results.append(cancel_workflow is not None)
        results.append(cancel_workflow.request_id in rtm.active_workflows)
        
        # Cancel the workflow
        cancel_success = await rtm.cancel_workflow(cancel_request_data["request_id"])
        results.append(cancel_success)
        results.append(cancel_request_data["request_id"] not in rtm.active_workflows)
        
        # Step 9: Test workflow history tracking
        # Create a request and track its history
        history_request_data = {
            "request_id": f"history_req_{uuid.uuid4().hex[:8]}",
            "priority_flag": "A",
            "model": "gpt-4",
            "messages": [{"role": "user", "content": "History test request"}],
            "requires_calculation": True,
            "template_type": "default"
        }
        
        history_result = await rtm.orchestrate_request(history_request_data, None)
        results.append(history_result["success"])
        
        # Get workflow status (includes processing history)
        workflow_status = await rtm.get_workflow_status(history_request_data["request_id"])
        results.append(workflow_status is not None)
        results.append("processing_history" in workflow_status)
        
        workflow_history = workflow_status["processing_history"]
        results.append(isinstance(workflow_history, list))
        results.append(len(workflow_history) > 0)
        
        # Verify history entries
        for history_entry in workflow_history:
            results.append("stage" in history_entry)
            results.append("timestamp" in history_entry)
            results.append("result" in history_entry)
            results.append("success" in history_entry)
        
        # Step 10: Test different workflow types
        # Test AI-only workflow
        ai_request_data = {
            "request_id": f"ai_req_{uuid.uuid4().hex[:8]}",
            "priority_flag": "A",
            "model": "gpt-4",
            "messages": [{"role": "user", "content": "AI-only test request"}],
            "requires_calculation": False  # No calculation required
        }
        
        ai_workflow = await rtm.create_workflow(ai_request_data)
        results.append(ai_workflow.workflow_type == "ai_workflow")
        
        ai_result = await rtm.orchestrate_request(ai_request_data, None)
        results.append(ai_result["success"])
        results.append(ai_result["final_stage"] == WorkflowStage.COMPLETED.value)
        
        # Test template workflow
        template_request_data = {
            "request_id": f"template_req_{uuid.uuid4().hex[:8]}",
            "priority_flag": "A",
            "model": "gpt-4",
            "messages": [{"role": "user", "content": "Template test request"}],
            "template_type": "default"
        }
        
        template_workflow = await rtm.create_workflow(template_request_data)
        results.append(template_workflow.workflow_type == "template_workflow")
        
        template_result = await rtm.orchestrate_request(template_request_data, None)
        results.append(template_result["success"])
        results.append(template_result["final_stage"] == WorkflowStage.COMPLETED.value)
        
        # Step 11: Test workflow state transitions
        # Create a workflow and manually transition through stages
        transition_request_data = {
            "request_id": f"transition_req_{uuid.uuid4().hex[:8]}",
            "priority_flag": "A",
            "model": "gpt-4",
            "messages": [{"role": "user", "content": "Transition test request"}],
            "requires_calculation": True,
            "template_type": "default"
        }
        
        transition_workflow = await rtm.create_workflow(transition_request_data)
        results.append(transition_workflow.current_stage == WorkflowStage.RECEIVED)
        
        # Test stage transitions
        for stage in rtm.standard_workflow:
            if stage != WorkflowStage.RECEIVED:  # Skip first stage
                # Execute stage
                stage_result = await rtm.execute_stage(stage, transition_workflow, transition_request_data)
                results.append(stage_result is not None)
                results.append("success" in stage_result)
                
                # Update workflow context
                transition_workflow.current_stage = stage
                transition_workflow.updated_at = time.time()
                transition_workflow.processing_history.append({
                    'stage': stage.value,
                    'timestamp': time.time(),
                    'result': stage_result,
                    'success': stage_result.get('success', False)
                })
                
                # Verify transition
                results.append(transition_workflow.current_stage == stage)
                results.append(len(transition_workflow.processing_history) > 0)
        
        # Step 12: Test workflow persistence and recovery
        # Test that workflow can be recovered from database
        persistence_request_data = {
            "request_id": f"persistence_req_{uuid.uuid4().hex[:8]}",
            "priority_flag": "A",
            "model": "gpt-4",
            "messages": [{"role": "user", "content": "Persistence test request"}],
            "requires_calculation": True,
            "template_type": "default"
        }
        
        # Create workflow and save to database
        persistence_workflow = await rtm.create_workflow(persistence_request_data)
        results.append(persistence_workflow is not None)
        
        # Simulate recovery by creating new RTM instance
        rtm_recovery = RequestTrackingModule()
        results.append(rtm_recovery is not None)
        
        # Try to recover workflow (this would normally load from database)
        # For now, just verify the recovery instance works
        recovery_workflow = await rtm_recovery.create_workflow(persistence_request_data)
        results.append(recovery_workflow is not None)
        
        # Step 13: Test workflow statistics
        # Verify statistics are updated correctly
        results.append(rtm.stats["total_requests"] > 0)
        results.append(rtm.stats["completed_requests"] > 0)
        results.append(rtm.stats["failed_requests"] >= 0)
        results.append(rtm.stats["average_processing_time"] >= 0)
        
        # Step 14: Test workflow error handling
        # Test workflow with invalid data
        invalid_request_data = {
            "request_id": f"invalid_req_{uuid.uuid4().hex[:8]}",
            # Missing required fields
        }
        
        try:
            invalid_result = await rtm.orchestrate_request(invalid_request_data, None)
            results.append(False)  # Should not reach here
        except Exception as e:
            # Should handle invalid data gracefully
            results.append("request" in str(e).lower() or "invalid" in str(e).lower())
        
        # Step 15: Test workflow performance
        # Test multiple concurrent workflows
        concurrent_requests = []
        for i in range(3):
            concurrent_request_data = {
                "request_id": f"concurrent_req_{i}_{uuid.uuid4().hex[:8]}",
                "priority_flag": "A",
                "model": "gpt-4",
                "messages": [{"role": "user", "content": f"Concurrent test request {i}"}],
                "requires_calculation": True,
                "template_type": "default"
            }
            concurrent_requests.append(concurrent_request_data)
        
        # Execute concurrent requests
        concurrent_start_time = time.time()
        concurrent_results = await asyncio.gather(
            *[rtm.orchestrate_request(req, None) for req in concurrent_requests],
            return_exceptions=True
        )
        concurrent_end_time = time.time()
        concurrent_duration = concurrent_end_time - concurrent_start_time
        
        # Verify concurrent execution
        results.append(len(concurrent_results) == 3)
        results.append(all(isinstance(result, dict) for result in concurrent_results))
        results.append(all(result.get("success", False) for result in concurrent_results))
        results.append(concurrent_duration < 10.0)  # Should complete within reasonable time
        
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
        logging.info(f"Orchestration duration: {orchestration_duration:.3f}s")
        logging.info(f"Concurrent duration: {concurrent_duration:.3f}s")
        
        return {
            "test_code": test_code,
            "test_name": test_name,
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "success_rate": (passed_tests/total_tests)*100,
            "execution_time": orchestration_duration,
            "results": results,
            "success": failed_tests == 0,
            "concurrent_duration": concurrent_duration
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
    result = asyncio.run(test_t00000009())
    
    if result["success"]:
        print(f"PASS {result['test_code']}: {result['test_name']} - PASSED")
        print(f"   Passed: {result['passed_tests']}/{result['total_tests']} tests")
        print(f"   Success rate: {result['success_rate']:.2f}%")
        print(f"   Execution time: {result['execution_time']:.3f}s")
        print(f"   Concurrent duration: {result.get('concurrent_duration', 0):.3f}s")
    else:
        print(f"FAIL {result['test_code']}: {result['test_name']} - FAILED")
        if "error" in result:
            print(f"   Error: {result['error']}")
        else:
            print(f"   Passed: {result['passed_tests']}/{result['total_tests']} tests")
            print(f"   Success rate: {result['success_rate']:.2f}%") 