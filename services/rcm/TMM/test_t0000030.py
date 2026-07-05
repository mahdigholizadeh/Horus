"""
Test T0000030: BTM - Automated Cleanup Task
Module(s) Tested: BTM
Description: Test automated cleanup functionality.
Success Criteria: The module correctly manages background tasks and cleanup operations.
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

from BTM.btm import BackgroundTasksModule

async def test_btm_automated_cleanup_task():
    """Test automated cleanup functionality."""
    test_code = "T0000030"
    test_name = "BTM - Automated Cleanup Task"
    try:
        # Initialize module
        btm = BackgroundTasksModule()
        
        # Test module status
        status_result = btm.get_module_status()
        status_success = isinstance(status_result, dict) and "is_running" in status_result
        
        # Test task management
        task_list = btm.get_task_list()
        task_management_success = isinstance(task_list, list) and len(task_list) > 0
        
        # Test task status retrieval
        task_status = btm.get_task_status()
        task_status_success = isinstance(task_status, dict) and len(task_status) > 0
        
        # Test custom task addition
        async def test_cleanup_task():
            """Test cleanup task function."""
            return True
        
        custom_task = btm.add_custom_task("test_cleanup", test_cleanup_task, 60)
        custom_task_success = custom_task is not None and custom_task.name == "test_cleanup"
        
        # Test task enable/disable
        disable_result = btm.disable_task("test_cleanup")
        enable_result = btm.enable_task("test_cleanup")
        task_control_success = disable_result and enable_result
        
        # Test cleanup task execution (run one of the default tasks)
        try:
            await btm._cleanup_old_files()
            cleanup_execution_success = True
        except Exception as e:
            cleanup_execution_success = False
        
        # Test memory cleanup
        try:
            await btm._cleanup_memory()
            memory_cleanup_success = True
        except Exception as e:
            memory_cleanup_success = False
        
        # Test task removal
        remove_result = btm.remove_task("test_cleanup")
        task_removal_success = remove_result
        
        test_success = (status_success and task_management_success and task_status_success and 
                       custom_task_success and task_control_success and cleanup_execution_success and 
                       memory_cleanup_success and task_removal_success)
        
        return {
            "success": test_success,
            "test_code": test_code,
            "test_name": test_name,
            "message": f"Automated cleanup task successful",
            "details": {
                "status_success": status_success,
                "task_management_success": task_management_success,
                "task_status_success": task_status_success,
                "custom_task_success": custom_task_success,
                "task_control_success": task_control_success,
                "cleanup_execution_success": cleanup_execution_success,
                "memory_cleanup_success": memory_cleanup_success,
                "task_removal_success": task_removal_success,
                "task_list": task_list,
                "task_count": len(task_list),
                "status_result": status_result,
                "task_status": task_status
            }
        }
    except Exception as e:
        return {
            "success": False,
            "test_code": test_code,
            "test_name": test_name,
            "error": f"Test execution failed: {str(e)}"
        }

if __name__ == "__main__":
    # Run the test
    result = asyncio.run(test_btm_automated_cleanup_task())
    print(json.dumps(result, indent=2, default=str))