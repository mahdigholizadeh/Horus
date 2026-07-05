"""
Test T00000013: BTM (Background Tasks Module) Unit Test
Module(s) Tested: BTM
Description: To ensure that background tasks (e.g., log cleanup, temporary file deletion) can be scheduled and executed without blocking.
Success Criteria: Scheduling call returns immediately, scheduled task executes and deletes dummy file.
"""

import asyncio
import json
import sys
import tempfile
import os
import time
import shutil
from pathlib import Path
from typing import Dict, Any
import importlib

# Add parent directory to path for module imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from BTM.btm import BackgroundTasksModule

if "BTM.btm" in sys.modules:
    importlib.reload(sys.modules["BTM.btm"])

async def test_t00000013():
    test_code = "T00000013"
    test_name = "BTM - Background Tasks Module Unit Test"
    results = []
    
    # Clean up temp files and directories before running the test
    temp_dir = Path("temp")
    if temp_dir.exists():
        try:
            shutil.rmtree(temp_dir)
        except Exception:
            pass
    
    btm = BackgroundTasksModule()
    await btm.start()
    
    try:
        # Step 1: Schedule a background task to delete files in a temporary directory
        temp_dir = tempfile.mkdtemp()
        
        # Create a dummy file in the temporary directory
        dummy_file_path = os.path.join(temp_dir, "dummy_file.txt")
        with open(dummy_file_path, 'w') as f:
            f.write("This is a dummy file for testing BTM")
        
        # Verify dummy file exists
        results.append(os.path.exists(dummy_file_path))
        
        # Schedule cleanup task
        schedule_start_time = time.time()
        schedule_result = await btm.schedule_task(
            task_name="cleanup_test_files",
            task_function="delete_files_in_directory",
            task_args={"directory": temp_dir, "file_pattern": "*.txt"},
            delay_seconds=2
        )
        schedule_end_time = time.time()
        
        # Step 2: Verify scheduling call returns immediately (should not block)
        scheduling_time = schedule_end_time - schedule_start_time
        results.append(scheduling_time < 1.0)  # Should return quickly
        results.append(schedule_result.get("success", False))
        
        # Check if task was scheduled
        scheduled_tasks = await btm.get_scheduled_tasks()
        results.append(len(scheduled_tasks) > 0)
        
        # Wait for task to execute
        await asyncio.sleep(3)
        
        # Step 3: Verify that after the scheduled execution time, the dummy file should be deleted
        results.append(not os.path.exists(dummy_file_path))
        
        # Test task status
        task_status = await btm.get_task_status("cleanup_test_files")
        results.append(task_status.get("status") in ["completed", "finished"])
        
        # Test multiple task scheduling
        task_ids = []
        for i in range(3):
            task_id = f"test_task_{i}"
            schedule_result = await btm.schedule_task(
                task_name=task_id,
                task_function="test_function",
                task_args={"index": i},
                delay_seconds=1
            )
            task_ids.append(task_id)
            results.append(schedule_result.get("success", False))
        
        # Wait for tasks to complete
        await asyncio.sleep(2)
        
        # Check all tasks completed
        for task_id in task_ids:
            status = await btm.get_task_status(task_id)
            results.append(status.get("status") in ["completed", "finished"])
        
        # Test task cancellation
        cancel_task_id = "cancel_test_task"
        await btm.schedule_task(
            task_name=cancel_task_id,
            task_function="long_running_task",
            task_args={"duration": 10},
            delay_seconds=1
        )
        
        # Cancel the task before it starts
        await asyncio.sleep(0.5)
        cancel_result = await btm.cancel_task(cancel_task_id)
        results.append(cancel_result.get("success", False))
        
        # Test recurring task
        recurring_result = await btm.schedule_recurring_task(
            task_name="recurring_test",
            task_function="test_recurring_function",
            task_args={"counter": 0},
            interval_seconds=1,
            max_executions=3
        )
        results.append(recurring_result.get("success", False))
        
        # Wait for recurring task to execute
        await asyncio.sleep(4)
        
        # Check recurring task status
        recurring_status = await btm.get_task_status("recurring_test")
        results.append(recurring_status.get("execution_count", 0) >= 1)
        
        # Test task statistics
        stats = await btm.get_task_statistics()
        results.append(isinstance(stats, dict))
        results.append("total_tasks" in stats)
        results.append("completed_tasks" in stats)
        results.append("failed_tasks" in stats)
        
        # Clean up temporary directory
        try:
            os.rmdir(temp_dir)
        except:
            pass
        
        success = all(results)
        
        return {
            "success": success,
            "test_code": test_code,
            "test_name": test_name,
            "message": "BTM unit test passed" if success else "BTM unit test failed",
            "details": {
                "dummy_file_created": results[0],
                "scheduling_non_blocking": results[1],
                "task_scheduled_successfully": results[2],
                "scheduled_tasks_listed": results[3],
                "dummy_file_deleted": results[4],
                "task_status_tracked": results[5],
                "multiple_tasks_scheduled": results[6],
                "multiple_tasks_scheduled_2": results[7],
                "multiple_tasks_scheduled_3": results[8],
                "multiple_tasks_completed_1": results[9],
                "multiple_tasks_completed_2": results[10],
                "multiple_tasks_completed_3": results[11],
                "task_cancellation_works": results[12],
                "recurring_task_scheduled": results[13],
                "recurring_task_executed": results[14],
                "task_statistics_generated": results[15],
                "statistics_has_total": results[16],
                "statistics_has_completed": results[17],
                "statistics_has_failed": results[18],
                "results": results
            }
        }
        
    finally:
        await btm.stop()