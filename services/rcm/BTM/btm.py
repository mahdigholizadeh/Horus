"""
Background Tasks Module (BTM)

Runs automated, periodic tasks such as cleaning up old files, clearing stale cache entries, and other maintenance operations.
"""

import asyncio
import logging
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
import time
import threading

# Import error management module
from EMM.emm import ErrorManagementModule
from EMM.api_error_handler import api_error_handler


class BackgroundTask:
    """Represents a background task with scheduling information."""
    
    def __init__(self, name: str, task_func: Callable, interval: int, enabled: bool = True):
        self.name = name
        self.task_func = task_func
        self.interval = interval  # seconds
        self.enabled = enabled
        self.last_run = None
        self.next_run = None
        self.run_count = 0
        self.last_duration = 0
        self.last_error = None
        self.is_running = False
    
    def should_run(self) -> bool:
        """Check if the task should run now."""
        if not self.enabled:
            return False
        
        if self.next_run is None:
            return True
        
        return datetime.now() >= self.next_run
    
    def update_schedule(self):
        """Update the next run time."""
        self.next_run = datetime.now() + timedelta(seconds=self.interval)
    
    def mark_started(self):
        """Mark task as started."""
        self.is_running = True
        self.last_run = datetime.now()
    
    def mark_completed(self, duration: float, error: str = None):
        """Mark task as completed."""
        self.is_running = False
        self.last_duration = duration
        self.last_error = error
        self.run_count += 1
        self.update_schedule()


class BackgroundTasksModule:
    """
    Background Tasks Module (BTM)
    
    Runs automated, periodic tasks for maintenance operations.
    """
    
    def __init__(self):
        """Initialize the BTM module."""
        self.logger = logging.getLogger(__name__)
        self.error_manager = ErrorManagementModule()
        
        # Task management
        self.tasks = {}
        self.task_thread = None
        self.is_running = False
        
        # Configuration
        self.check_interval = 60  # seconds
        self.max_concurrent_tasks = 5
        
        # Statistics
        self.stats = {
            "total_task_runs": 0,
            "successful_runs": 0,
            "failed_runs": 0,
            "total_runtime": 0,
            "last_activity": None
        }
        
        # Error codes now generated dynamically by EMM
        
        # Initialize default tasks
        self._initialize_default_tasks()
    
    def _initialize_default_tasks(self):
        """Initialize default background tasks."""
        # File cleanup task
        self.add_task(
            "file_cleanup",
            self._cleanup_old_files,
            interval=3600  # 1 hour
        )
        
        # Cache cleanup task
        self.add_task(
            "cache_cleanup",
            self._cleanup_stale_cache,
            interval=1800  # 30 minutes
        )
        
        # Log rotation task
        self.add_task(
            "log_rotation",
            self._rotate_logs,
            interval=86400  # 24 hours
        )
        
        # Database maintenance task
        self.add_task(
            "database_maintenance",
            self._maintain_database,
            interval=7200  # 2 hours
        )
        
        # Memory cleanup task
        self.add_task(
            "memory_cleanup",
            self._cleanup_memory,
            interval=300  # 5 minutes
        )
    
    def add_task(self, name: str, task_func: Callable, interval: int, enabled: bool = True) -> BackgroundTask:
        """
        Add a new background task.
        
        Args:
            name: Task name
            task_func: Task function to execute
            interval: Execution interval in seconds
            enabled: Whether the task is enabled
            
        Returns:
            BackgroundTask instance
        """
        task = BackgroundTask(name, task_func, interval, enabled)
        self.tasks[name] = task
        self.logger.info(f"Added background task: {name} (interval: {interval}s)")
        return task
    
    def remove_task(self, name: str) -> bool:
        """
        Remove a background task.
        
        Args:
            name: Task name
            
        Returns:
            True if task was removed, False if not found
        """
        if name in self.tasks:
            del self.tasks[name]
            self.logger.info(f"Removed background task: {name}")
            return True
        return False
    
    def enable_task(self, name: str) -> bool:
        """
        Enable a background task.
        
        Args:
            name: Task name
            
        Returns:
            True if task was enabled, False if not found
        """
        if name in self.tasks:
            self.tasks[name].enabled = True
            self.logger.info(f"Enabled background task: {name}")
            return True
        return False
    
    def disable_task(self, name: str) -> bool:
        """
        Disable a background task.
        
        Args:
            name: Task name
            
        Returns:
            True if task was disabled, False if not found
        """
        if name in self.tasks:
            self.tasks[name].enabled = False
            self.logger.info(f"Disabled background task: {name}")
            return True
        return False
    
    async def start(self):
        """Start the BTM module."""
        self.is_running = True
        self.task_thread = asyncio.create_task(self._task_scheduler())
        self.logger.info("BTM module started")
    
    async def stop(self):
        """Stop the BTM module."""
        self.is_running = False
        if self.task_thread:
            self.task_thread.cancel()
            try:
                await self.task_thread
            except asyncio.CancelledError:
                pass
        self.logger.info("BTM module stopped")
    
    async def _task_scheduler(self):
        """Main task scheduler loop."""
        while self.is_running:
            try:
                await self._check_and_run_tasks()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                error_msg = f"Error in task scheduler: {e}"
                self.error_manager.log_error_with_generation("BTM", "UnknownClass", "UnknownFunction", error_msg)
                await asyncio.sleep(10)  # Wait before retrying
    
    async def _check_and_run_tasks(self):
        """Check and run tasks that are due."""
        tasks_to_run = []
        
        # Find tasks that should run
        for task in self.tasks.values():
            if task.should_run() and not task.is_running:
                tasks_to_run.append(task)
        
        # Limit concurrent tasks
        if len(tasks_to_run) > self.max_concurrent_tasks:
            tasks_to_run = tasks_to_run[:self.max_concurrent_tasks]
        
        # Run tasks concurrently
        if tasks_to_run:
            self.logger.info(f"Running {len(tasks_to_run)} background tasks")
            await asyncio.gather(*[self._run_task(task) for task in tasks_to_run])
    
    async def _run_task(self, task: BackgroundTask):
        """Run a single background task."""
        start_time = time.time()
        task.mark_started()
        
        try:
            # Run the task
            if asyncio.iscoroutinefunction(task.task_func):
                await task.task_func()
            else:
                # Run sync function in thread pool
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, task.task_func)
            
            # Mark as successful
            duration = time.time() - start_time
            task.mark_completed(duration)
            self.stats["successful_runs"] += 1
            self.stats["total_task_runs"] += 1
            self.stats["total_runtime"] += duration
            self.stats["last_activity"] = datetime.now()
            
            self.logger.info(f"Task {task.name} completed successfully in {duration:.2f}s")
            
        except Exception as e:
            # Mark as failed
            duration = time.time() - start_time
            error_msg = str(e)
            task.mark_completed(duration, error_msg)
            self.stats["failed_runs"] += 1
            self.stats["total_task_runs"] += 1
            self.stats["total_runtime"] += duration
            self.stats["last_activity"] = datetime.now()
            
            self.logger.error(f"Task {task.name} failed: {error_msg}")
            self.error_manager.log_error_with_generation("BTM", "UnknownClass", "UnknownFunction", f"Task {task.name} failed: {error_msg}")
    
    def get_task_status(self, name: str = None) -> Dict[str, Any]:
        """
        Get status of tasks.
        
        Args:
            name: Specific task name, or None for all tasks
            
        Returns:
            Task status information
        """
        if name:
            if name in self.tasks:
                task = self.tasks[name]
                return {
                    "name": task.name,
                    "enabled": task.enabled,
                    "is_running": task.is_running,
                    "last_run": task.last_run.isoformat() if task.last_run else None,
                    "next_run": task.next_run.isoformat() if task.next_run else None,
                    "run_count": task.run_count,
                    "last_duration": task.last_duration,
                    "last_error": task.last_error,
                    "interval": task.interval
                }
            return None
        
        return {
            name: {
                "enabled": task.enabled,
                "is_running": task.is_running,
                "last_run": task.last_run.isoformat() if task.last_run else None,
                "next_run": task.next_run.isoformat() if task.next_run else None,
                "run_count": task.run_count,
                "last_duration": task.last_duration,
                "last_error": task.last_error,
                "interval": task.interval
            }
            for name, task in self.tasks.items()
        }
    
    def get_module_status(self) -> Dict[str, Any]:
        """Get overall module status."""
        return {
            "is_running": self.is_running,
            "total_tasks": len(self.tasks),
            "enabled_tasks": len([t for t in self.tasks.values() if t.enabled]),
            "running_tasks": len([t for t in self.tasks.values() if t.is_running]),
            "stats": self.stats.copy(),
            "check_interval": self.check_interval,
            "max_concurrent_tasks": self.max_concurrent_tasks
        }
    
    def update_config(self, **kwargs):
        """
        Update module configuration.
        
        Args:
            **kwargs: Configuration parameters to update
        """
        if "check_interval" in kwargs:
            self.check_interval = kwargs["check_interval"]
        if "max_concurrent_tasks" in kwargs:
            self.max_concurrent_tasks = kwargs["max_concurrent_tasks"]
        
        self.logger.info(f"Updated BTM configuration: {kwargs}")
    
    # Default task implementations
    async def _cleanup_old_files(self):
        """Clean up old temporary files."""
        try:
            base_dir = Path(__file__).parent.parent
            temp_dir = base_dir / "temp"
            
            if not temp_dir.exists():
                return
            
            # Remove files older than 24 hours
            cutoff_time = datetime.now() - timedelta(hours=24)
            removed_count = 0
            
            for file_path in temp_dir.rglob("*"):
                if file_path.is_file():
                    if datetime.fromtimestamp(file_path.stat().st_mtime) < cutoff_time:
                        try:
                            file_path.unlink()
                            removed_count += 1
                        except Exception as e:
                            self.logger.warning(f"Could not remove {file_path}: {e}")
            
            if removed_count > 0:
                self.logger.info(f"Cleaned up {removed_count} old files")
                
        except Exception as e:
            self.logger.error(f"Error in file cleanup: {e}")
            raise
    
    async def _cleanup_stale_cache(self):
        """Clean up stale cache entries."""
        try:
            # This would integrate with the cache system
            # For now, just log the action
            self.logger.info("Cache cleanup task executed")
            
        except Exception as e:
            self.logger.error(f"Error in cache cleanup: {e}")
            raise
    
    async def _rotate_logs(self):
        """Rotate log files."""
        try:
            # This would integrate with the logging system
            # For now, just log the action
            self.logger.info("Log rotation task executed")
            
        except Exception as e:
            self.logger.error(f"Error in log rotation: {e}")
            raise
    
    async def _maintain_database(self):
        """Perform database maintenance tasks."""
        try:
            # This would integrate with the database system
            # For now, just log the action
            self.logger.info("Database maintenance task executed")
            
        except Exception as e:
            self.logger.error(f"Error in database maintenance: {e}")
            raise
    
    async def _cleanup_memory(self):
        """Clean up memory usage."""
        try:
            import gc
            gc.collect()
            self.logger.info("Memory cleanup task executed")
            
        except Exception as e:
            self.logger.error(f"Error in memory cleanup: {e}")
            raise
    
    def add_custom_task(self, name: str, task_func: Callable, interval: int, enabled: bool = True) -> BackgroundTask:
        """
        Add a custom background task.
        
        Args:
            name: Task name
            task_func: Task function (can be sync or async)
            interval: Execution interval in seconds
            enabled: Whether the task is enabled
            
        Returns:
            BackgroundTask instance
        """
        return self.add_task(name, task_func, interval, enabled)
    
    def get_task_list(self) -> List[str]:
        """Get list of all task names."""
        return list(self.tasks.keys())
    
    def get_running_tasks(self) -> List[str]:
        """Get list of currently running task names."""
        return [name for name, task in self.tasks.items() if task.is_running]
    
    def get_enabled_tasks(self) -> List[str]:
        """Get list of enabled task names."""
        return [name for name, task in self.tasks.items() if task.enabled]
    
    def reset_task_stats(self, task_name: str = None):
        """
        Reset statistics for a task or all tasks.
        
        Args:
            task_name: Specific task name, or None for all tasks
        """
        if task_name:
            if task_name in self.tasks:
                task = self.tasks[task_name]
                task.run_count = 0
                task.last_duration = 0
                task.last_error = None
                self.logger.info(f"Reset stats for task: {task_name}")
        else:
            for task in self.tasks.values():
                task.run_count = 0
                task.last_duration = 0
                task.last_error = None
            self.logger.info("Reset stats for all tasks")
    
    def reset_module_stats(self):
        """Reset overall module statistics."""
        self.stats = {
            "total_task_runs": 0,
            "successful_runs": 0,
            "failed_runs": 0,
            "total_runtime": 0,
            "last_activity": None
        }
        self.logger.info("Reset module statistics")

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
        error_code = self.log_error(error_message, class_name, function_name)
        if hasattr(exception, 'status_code') or 'api' in error_message.lower():
            return await self.handle_api_error(error_message, getattr(exception, 'status_code', None), context)
        return {
            "success": False,
            "error_code": error_code,
            "error_message": error_message,
            "timestamp": datetime.now().isoformat()
        }

    async def handle_api_error(self, error_response: str, status_code: int = None, context: dict = None) -> dict:
        """Handle API errors using the centralized API error handler."""
        try:
            result = await api_error_handler.handle_api_error(error_response, status_code, context)
            self.error_manager.log_error_with_generation(
                "BTM",
                "BTM",
                "handle_api_error",
                f"API Error: {result.get('api_error_type', 'unknown')}",
                context=result
            )
            await api_error_handler.send_error_report_to_ccu(result)
            return result
        except Exception as e:
            self.error_manager.log_error_with_generation(
                "BTM",
                "BTM",
                "handle_api_error",
                f"Error handling API error: {str(e)}"
            )
            return {"success": False, "error": str(e)}


# Global instance and alias for compatibility
btm = BackgroundTasksModule()
BTM = BackgroundTasksModule  # Class alias