"""
Test file for Background Tasks Module (BTM)

Tests all functionality including task management, scheduling, error handling, and statistics.
"""

import asyncio
import time
import logging
from pathlib import Path
from datetime import datetime, timedelta
import pytest

# Import the BTM module
import sys
from EMM.emm import ErrorManagementModule
from EMM.api_error_handler import api_error_handler
sys.path.append(str(Path(__file__).parent.parent))
from BTM.btm import BackgroundTasksModule, BackgroundTask


class TestBackgroundTasksModule:
    def __init__(self):
        self.error_manager = ErrorManagementModule()

    """Test class for BackgroundTasksModule."""
    
    def setup_method(self):
        """Set up test environment."""
        # Create a fresh instance for each test
        self.btm = BackgroundTasksModule()
        
        # Configure logging for tests
        logging.basicConfig(level=logging.INFO)
    
    def teardown_method(self):
        """Clean up after each test."""
        if hasattr(self, 'btm') and self.btm.is_running:
            asyncio.run(self.btm.stop())
    
    def test_initialization(self):
        """Test BTM initialization."""
        assert self.btm is not None
        assert self.btm.is_running == False
        assert len(self.btm.tasks) > 0  # Should have default tasks
        assert self.btm.check_interval == 60
        assert self.btm.max_concurrent_tasks == 5
    
    def test_add_task(self):
        """Test adding a new task."""
        def test_task():
            return "test completed"
        
        task = self.btm.add_task("test_task", test_task, 300)
        
        assert task.name == "test_task"
        assert task.interval == 300
        assert task.enabled == True
        assert "test_task" in self.btm.tasks
    
    def test_remove_task(self):
        """Test removing a task."""
        def test_task():
            return "test completed"
        
        self.btm.add_task("test_task", test_task, 300)
        assert "test_task" in self.btm.tasks
        
        result = self.btm.remove_task("test_task")
        assert result == True
        assert "test_task" not in self.btm.tasks
        
        # Test removing non-existent task
        result = self.btm.remove_task("non_existent")
        assert result == False
    
    def test_enable_disable_task(self):
        """Test enabling and disabling tasks."""
        def test_task():
            return "test completed"
        
        task = self.btm.add_task("test_task", test_task, 300)
        
        # Test disable
        result = self.btm.disable_task("test_task")
        assert result == True
        assert task.enabled == False
        
        # Test enable
        result = self.btm.enable_task("test_task")
        assert result == True
        assert task.enabled == True
        
        # Test non-existent task
        result = self.btm.enable_task("non_existent")
        assert result == False
    
    def test_task_scheduling(self):
        """Test task scheduling logic."""
        def test_task():
            return "test completed"
        
        task = self.btm.add_task("test_task", test_task, 60)
        
        # Initially should run
        assert task.should_run() == True
        
        # After marking as started, should not run again immediately
        task.mark_started()
        assert task.should_run() == False
        
        # After completion, should schedule next run
        task.mark_completed(1.0)
        assert task.next_run is not None
        assert task.next_run > datetime.now()
    
    def test_get_task_status(self):
        """Test getting task status."""
        def test_task():
            return "test completed"
        
        self.btm.add_task("test_task", test_task, 300)
        
        # Get status of specific task
        status = self.btm.get_task_status("test_task")
        assert status is not None
        assert status["name"] == "test_task"
        assert status["enabled"] == True
        assert status["interval"] == 300
        
        # Get status of non-existent task
        status = self.btm.get_task_status("non_existent")
        assert status is None
        
        # Get status of all tasks
        all_status = self.btm.get_task_status()
        assert isinstance(all_status, dict)
        assert "test_task" in all_status
    
    def test_get_module_status(self):
        """Test getting module status."""
        status = self.btm.get_module_status()
        
        assert "is_running" in status
        assert "total_tasks" in status
        assert "enabled_tasks" in status
        assert "running_tasks" in status
        assert "stats" in status
        assert "check_interval" in status
        assert "max_concurrent_tasks" in status
        
        assert status["is_running"] == False
        assert status["total_tasks"] > 0
        assert status["check_interval"] == 60
        assert status["max_concurrent_tasks"] == 5
    
    def test_update_config(self):
        """Test configuration updates."""
        self.btm.update_config(check_interval=30, max_concurrent_tasks=3)
        
        assert self.btm.check_interval == 30
        assert self.btm.max_concurrent_tasks == 3
    
    def test_task_list_methods(self):
        """Test task list methods."""
        def test_task():
            return "test completed"
        
        self.btm.add_task("test_task", test_task, 300)
        
        # Test get_task_list
        task_list = self.btm.get_task_list()
        assert "test_task" in task_list
        
        # Test get_enabled_tasks
        enabled_tasks = self.btm.get_enabled_tasks()
        assert "test_task" in enabled_tasks
        
        # Test get_running_tasks (should be empty initially)
        running_tasks = self.btm.get_running_tasks()
        assert len(running_tasks) == 0
    
    def test_reset_stats(self):
        """Test statistics reset methods."""
        def test_task():
            return "test completed"
        
        task = self.btm.add_task("test_task", test_task, 300)
        
        # Simulate some task runs
        task.run_count = 5
        task.last_duration = 2.5
        task.last_error = "test error"
        
        # Reset specific task stats
        self.btm.reset_task_stats("test_task")
        assert task.run_count == 0
        assert task.last_duration == 0
        assert task.last_error is None
        
        # Reset all task stats
        task.run_count = 3
        self.btm.reset_task_stats()
        assert task.run_count == 0
        
        # Reset module stats
        self.btm.stats["total_task_runs"] = 10
        self.btm.reset_module_stats()
        assert self.btm.stats["total_task_runs"] == 0
    
    @pytest.mark.asyncio
    async def test_start_stop(self):
        """Test starting and stopping the module."""
        # Start the module
        await self.btm.start()
        assert self.btm.is_running == True
        
        # Stop the module
        await self.btm.stop()
        assert self.btm.is_running == False
    
    @pytest.mark.asyncio
    async def test_task_execution(self):
        """Test actual task execution."""
        execution_results = []
        
        def test_task():
            execution_results.append("task_executed")
            return "test completed"
        
        # Add a task with short interval
        self.btm.add_task("test_task", test_task, 1)
        
        # Start the module
        await self.btm.start()
        
        # Wait for task to execute
        await asyncio.sleep(3)
        
        # Stop the module
        await self.btm.stop()
        
        # Check if task was executed
        assert len(execution_results) > 0
        assert "task_executed" in execution_results
    
    @pytest.mark.asyncio
    async def test_async_task_execution(self):
        """Test async task execution."""
        execution_results = []
        
        async def async_test_task():
            execution_results.append("async_task_executed")
            await asyncio.sleep(0.1)
            return "async test completed"
        
        # Add an async task
        self.btm.add_task("async_test_task", async_test_task, 1)
        
        # Start the module
        await self.btm.start()
        
        # Wait for task to execute
        await asyncio.sleep(3)
        
        # Stop the module
        await self.btm.stop()
        
        # Check if task was executed
        assert len(execution_results) > 0
        assert "async_task_executed" in execution_results
    
    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test error handling in task execution."""
        def failing_task():
            raise Exception("Test error")
        
        # Add a failing task
        self.btm.add_task("failing_task", failing_task, 1)
        
        # Start the module
        await self.btm.start()
        
        # Wait for task to execute
        await asyncio.sleep(3)
        
        # Stop the module
        await self.btm.stop()
        
        # Check that the task was marked as failed
        task = self.btm.tasks["failing_task"]
        assert task.last_error is not None
        assert "Test error" in task.last_error
    
    def test_custom_task_addition(self):
        """Test adding custom tasks."""
        def custom_task():
            return "custom task executed"
        
        task = self.btm.add_custom_task("custom_task", custom_task, 300)
        
        assert task.name == "custom_task"
        assert "custom_task" in self.btm.tasks
    
    def test_default_tasks(self):
        """Test that default tasks are properly initialized."""
        default_task_names = [
            "file_cleanup",
            "cache_cleanup", 
            "log_rotation",
            "database_maintenance",
            "memory_cleanup"
        ]
        
        for task_name in default_task_names:
            assert task_name in self.btm.tasks
            assert self.btm.tasks[task_name].enabled == True


    def log_error(self, error_message: str, class_name: str = "UnknownClass", function_name: str = "UnknownFunction", sub_function: str = "001"):
        """Log an error using EMM."""
        return self.error_manager.log_error_with_generation(
            "BTM", 
            class_name, 
            function_name, 
            error_message, 
            sub_function
        )
    
    def generate_error_code(self, class_name: str = "UnknownClass", function_name: str = "UnknownFunction", sub_function: str = "001") -> str:
        """Generate an error code using EMM."""
        return self.error_manager.generate_error_code("BTM", class_name, function_name, sub_function)
    
    async def handle_exception(self, exception: Exception, class_name: str = "UnknownClass", function_name: str = "UnknownFunction", context: dict = None):
        """Handle exceptions with comprehensive logging and recovery."""
        error_message = str(exception)
        
        # Log the error
        error_code = self.log_error(error_message, class_name, function_name)
        
        # Check if it's an API error
        if hasattr(exception, 'status_code') or 'api' in error_message.lower():
            return await self.handle_api_error(error_message, getattr(exception, 'status_code', None), context)
        
        # Return standard error response
        return {
            "success": False,
            "error_code": error_code,
            "error_message": error_message,
            "timestamp": datetime.now().isoformat()
        }

class TestBackgroundTask:
    """Test class for BackgroundTask."""
    
    def test_background_task_creation(self):
        """Test BackgroundTask creation."""
        def test_func():
            return "test"
        
        task = BackgroundTask("test_task", test_func, 300)
        
        assert task.name == "test_task"
        assert task.task_func == test_func
        assert task.interval == 300
        assert task.enabled == True
        assert task.last_run is None
        assert task.next_run is None
        assert task.run_count == 0
        assert task.is_running == False
    
    def test_task_scheduling(self):
        """Test task scheduling logic."""
        def test_func():
            return "test"
        
        task = BackgroundTask("test_task", test_func, 60)
        
        # Initially should run
        assert task.should_run() == True
        
        # After marking as started
        task.mark_started()
        assert task.is_running == True
        assert task.last_run is not None
        assert task.should_run() == False
        
        # After completion
        task.mark_completed(1.5, "test error")
        assert task.is_running == False
        assert task.last_duration == 1.5
        assert task.last_error == "test error"
        assert task.run_count == 1
        assert task.next_run is not None
        assert task.next_run > datetime.now()
    
    def test_task_disabled(self):
        """Test disabled task behavior."""
        def test_func():
            return "test"
        
        task = BackgroundTask("test_task", test_func, 60, enabled=False)
        
        assert task.enabled == False
        assert task.should_run() == False


def run_btm_tests():
    """Run all BTM tests."""
    print("🧪 Running BTM Module Tests...")
    
    # Create test instance
    test_instance = TestBackgroundTasksModule()
    
    # Run basic tests
    print("  ✓ Testing initialization...")
    test_instance.test_initialization()
    
    print("  ✓ Testing task management...")
    test_instance.test_add_task()
    test_instance.test_remove_task()
    test_instance.test_enable_disable_task()
    
    print("  ✓ Testing task scheduling...")
    test_instance.test_task_scheduling()
    
    print("  ✓ Testing status methods...")
    test_instance.test_get_task_status()
    test_instance.test_get_module_status()
    
    print("  ✓ Testing configuration...")
    test_instance.test_update_config()
    
    print("  ✓ Testing task lists...")
    test_instance.test_task_list_methods()
    
    print("  ✓ Testing statistics...")
    test_instance.test_reset_stats()
    
    print("  ✓ Testing default tasks...")
    test_instance.test_default_tasks()
    
    # Run async tests
    print("  ✓ Testing async operations...")
    asyncio.run(test_instance.test_start_stop())
    asyncio.run(test_instance.test_task_execution())
    asyncio.run(test_instance.test_async_task_execution())
    asyncio.run(test_instance.test_error_handling())
    
    print("  ✓ Testing custom tasks...")
    test_instance.test_custom_task_addition()
    
    # Test BackgroundTask class
    print("  ✓ Testing BackgroundTask class...")
    task_tester = TestBackgroundTask()
    task_tester.test_background_task_creation()
    task_tester.test_task_scheduling()
    task_tester.test_task_disabled()
    
    print("✅ All BTM tests passed!")


if __name__ == "__main__":
    run_btm_tests() 