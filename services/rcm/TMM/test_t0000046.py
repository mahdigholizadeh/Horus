"""
Test T0000046: BTM - Background Tasks Module Comprehensive
Module(s) Tested: BTM
Description: Test comprehensive background task functionality.
Success Criteria: The module correctly schedules and executes background tasks without interfering with main operations.
"""

import asyncio
import tempfile
from pathlib import Path
import sys
import os
import json

# Add the project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from BTM.btm import BTM

async def test_btm_background_tasks_comprehensive():
    """Test comprehensive background task functionality."""
    test_code = "T0000046"
    test_name = "BTM - Background Tasks Module Comprehensive"
    try:
        # Initialize module
        btm = BTM()
        
        # Test task management
        task_list = btm.get_task_list()
        task_list_success = isinstance(task_list, list) and len(task_list) > 0
        
        # Test task status
        task_status = btm.get_task_status()
        task_status_success = isinstance(task_status, dict)
        
        # Test module status
        module_status = btm.get_module_status()
        module_status_success = isinstance(module_status, dict)
        
        # Test task enable/disable
        if task_list:
            first_task = task_list[0]
            disable_result = btm.disable_task(first_task)
            enable_result = btm.enable_task(first_task)
            task_control_success = isinstance(disable_result, bool) and isinstance(enable_result, bool)
        else:
            task_control_success = False
        
        # Test custom task addition
        def test_task():
            return "test_task_executed"
        
        custom_task = btm.add_custom_task("test_task", test_task, 60)
        custom_task_success = custom_task is not None
        
        # Test running tasks list
        running_tasks = btm.get_running_tasks()
        running_tasks_success = isinstance(running_tasks, list)
        
        # Test enabled tasks list
        enabled_tasks = btm.get_enabled_tasks()
        enabled_tasks_success = isinstance(enabled_tasks, list)
        
        # Test module start/stop
        try:
            await btm.start()
            await asyncio.sleep(0.1)  # Brief running
            await btm.stop()
            lifecycle_success = True
        except Exception as e:
            print(f"[DEBUG] Exception in start/stop: {e}")
            lifecycle_success = False
        
        # Clean up custom task
        if custom_task_success:
            btm.remove_task("test_task")
        
        test_success = (task_list_success and task_status_success and module_status_success and 
                       task_control_success and custom_task_success and running_tasks_success and 
                       enabled_tasks_success and lifecycle_success)
        
        return {
            "success": test_success,
            "test_code": test_code,
            "test_name": test_name,
            "message": f"Background tasks module comprehensive successful",
            "details": {
                "task_list_success": task_list_success,
                "task_status_success": task_status_success,
                "module_status_success": module_status_success,
                "task_control_success": task_control_success,
                "custom_task_success": custom_task_success,
                "running_tasks_success": running_tasks_success,
                "enabled_tasks_success": enabled_tasks_success,
                "lifecycle_success": lifecycle_success
            }
        }
    except Exception as e:
        print(f"[DEBUG] Exception in test_btm_background_tasks_comprehensive: {e}")
        return {
            "success": False,
            "test_code": test_code,
            "test_name": test_name,
            "error": f"Test execution failed: {str(e)}"
        }

async def main():
    print("=" * 60)
    print("Test T0000046: BTM - Background Tasks Module Comprehensive")
    print("=" * 60)
    result = await test_btm_background_tasks_comprehensive()
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