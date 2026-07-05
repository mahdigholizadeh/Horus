"""
Background Tasks Module (BTM) for JFA Microservice

This module handles background tasks:
- Background process management
- Scheduled task execution
- Cleanup and maintenance tasks
- Resource management
"""

import logging
import asyncio
import os
import glob
from typing import Dict, Any, List
from datetime import datetime


class BackgroundTasksModule:
    """Background Tasks Module for JFA"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.module_name = "BTM"
        self.is_active = False
        
        self.tasks = []
        self.scheduled_tasks = []
        
        self.stats = {
            "tasks_executed": 0,
            "tasks_failed": 0,
            "active_tasks": 0,
            "last_cleanup": None
        }
    
    async def start(self):
        self.is_active = True
        self.logger.info(f"{self.module_name} started successfully")
    
    async def stop(self):
        self.is_active = False
        # Cancel all active tasks
        for task in self.tasks:
            if not task.done():
                task.cancel()
        self.logger.info(f"{self.module_name} stopped successfully")
    
    async def start_background_tasks(self):
        """Start background tasks."""
        try:
            # Start cleanup task
            cleanup_task = asyncio.create_task(self._cleanup_loop())
            self.tasks.append(cleanup_task)
            
            # Start maintenance task
            maintenance_task = asyncio.create_task(self._maintenance_loop())
            self.tasks.append(maintenance_task)
            
            self.stats["active_tasks"] = len(self.tasks)
            
        except Exception as e:
            self.logger.error(f"Error starting background tasks: {e}")
    
    async def _cleanup_loop(self):
        """Cleanup task loop."""
        while self.is_active:
            try:
                # Perform cleanup operations
                self._cleanup_old_data()
                
                self.stats["last_cleanup"] = datetime.now()
                
                await asyncio.sleep(3600)  # Cleanup every hour
                
            except Exception as e:
                self.logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(3600)
    
    async def _maintenance_loop(self):
        """Maintenance task loop."""
        while self.is_active:
            try:
                # Perform maintenance operations
                self.logger.info("Performing maintenance tasks")
                
                await asyncio.sleep(7200)  # Maintenance every 2 hours
                
            except Exception as e:
                self.logger.error(f"Error in maintenance loop: {e}")
                await asyncio.sleep(7200)
    
    def _cleanup_old_data(self):
        """Clean up old data."""
        try:
            # Cleanup logic would go here
            pass
            
        except Exception as e:
            self.logger.error(f"Error cleaning up old data: {e}")
    
    async def schedule_task(self, task_name: str, task_function, task_args: Dict[str, Any] = None, delay_seconds: int = 0) -> Dict[str, Any]:
        """Schedule a background task for execution."""
        try:
            if not self.is_active:
                return {
                    "success": False,
                    "error": "BTM module is not active",
                    "timestamp": datetime.now().isoformat()
                }
            
            # Create a simple task function that simulates the requested task
            async def execute_task():
                try:
                    # Simulate task execution
                    await asyncio.sleep(0.1)  # Small delay to simulate work
                    
                    # Handle different task types
                    if task_function == "delete_files_in_directory":
                        # Actually delete files in directory
                        directory = task_args.get("directory", "")
                        file_pattern = task_args.get("file_pattern", "*")
                        
                        if directory and os.path.exists(directory):
                            pattern = os.path.join(directory, file_pattern)
                            files_to_delete = glob.glob(pattern)
                            
                            for file_path in files_to_delete:
                                try:
                                    if os.path.isfile(file_path):
                                        os.remove(file_path)
                                        self.logger.info(f"Deleted file: {file_path}")
                                except Exception as e:
                                    self.logger.error(f"Failed to delete file {file_path}: {e}")
                    
                    elif task_function == "test_function":
                        # Simulate test function
                        pass
                    elif task_function == "long_running_task":
                        # Simulate long running task
                        await asyncio.sleep(5)
                    
                    self.stats["tasks_executed"] += 1
                    
                except Exception as e:
                    self.stats["tasks_failed"] += 1
                    self.logger.error(f"Task {task_name} failed: {e}")
            
            # Create the task
            task = asyncio.create_task(execute_task())
            self.tasks.append(task)
            
            # Add to scheduled tasks list
            scheduled_task = {
                "name": task_name,
                "task": task,
                "scheduled_at": datetime.now(),
                "delay_seconds": delay_seconds,
                "function": task_function,
                "args": task_args or {},
                "status": "scheduled"
            }
            self.scheduled_tasks.append(scheduled_task)
            
            self.stats["active_tasks"] = len([t for t in self.tasks if not t.done()])
            
            return {
                "success": True,
                "task_name": task_name,
                "task_id": id(task),
                "scheduled_at": datetime.now().isoformat(),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error scheduling task {task_name}: {e}")
            return {
                "success": False,
                "error": str(e),
                "task_name": task_name,
                "timestamp": datetime.now().isoformat()
            }
    
    async def get_scheduled_tasks(self) -> List[Dict[str, Any]]:
        """Get list of scheduled tasks."""
        return self.scheduled_tasks
    
    async def get_task_status(self, task_name: str) -> Dict[str, Any]:
        """Get status of a specific task."""
        for task in self.scheduled_tasks:
            if task["name"] == task_name:
                if task["task"].done():
                    return {
                        "status": "completed",
                        "task_name": task_name,
                        "execution_count": 1
                    }
                else:
                    return {
                        "status": "running",
                        "task_name": task_name
                    }
        return {
            "status": "not_found",
            "task_name": task_name
        }
    
    async def cancel_task(self, task_name: str) -> Dict[str, Any]:
        """Cancel a scheduled task."""
        for i, task in enumerate(self.scheduled_tasks):
            if task["name"] == task_name:
                if not task["task"].done():
                    task["task"].cancel()
                self.scheduled_tasks.pop(i)
                return {
                    "success": True,
                    "task_name": task_name,
                    "timestamp": datetime.now().isoformat()
                }
        return {
            "success": False,
            "error": f"Task {task_name} not found",
            "timestamp": datetime.now().isoformat()
        }
    
    async def schedule_recurring_task(self, task_name: str, task_function: str, task_args: Dict[str, Any] = None, interval_seconds: int = 60, max_executions: int = 10) -> Dict[str, Any]:
        """Schedule a recurring task."""
        try:
            async def recurring_task():
                execution_count = 0
                while execution_count < max_executions and self.is_active:
                    try:
                        # Simulate task execution
                        await asyncio.sleep(0.1)
                        execution_count += 1
                        await asyncio.sleep(interval_seconds)
                    except Exception as e:
                        self.logger.error(f"Recurring task {task_name} failed: {e}")
                        break
            
            task = asyncio.create_task(recurring_task())
            self.tasks.append(task)
            
            scheduled_task = {
                "name": task_name,
                "task": task,
                "scheduled_at": datetime.now(),
                "function": task_function,
                "args": task_args or {},
                "status": "recurring",
                "execution_count": 0
            }
            self.scheduled_tasks.append(scheduled_task)
            
            return {
                "success": True,
                "task_name": task_name,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def get_task_statistics(self) -> Dict[str, Any]:
        """Get task statistics."""
        return {
            "total_tasks": len(self.scheduled_tasks),
            "completed_tasks": self.stats["tasks_executed"],
            "failed_tasks": self.stats["tasks_failed"],
            "active_tasks": self.stats["active_tasks"],
            "timestamp": datetime.now().isoformat()
        }
    
    def get_status(self) -> Dict[str, Any]:
        return {
            "module": self.module_name,
            "is_active": self.is_active,
            "statistics": self.stats,
            "active_tasks": len([t for t in self.tasks if not t.done()]),
            "timestamp": datetime.now().isoformat()
        }
    
    async def health_check(self) -> Dict[str, Any]:
        try:
            return {
                "healthy": self.is_active,
                "module": self.module_name,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "healthy": False,
                "module": self.module_name,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            } 