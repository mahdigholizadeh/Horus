"""
Background Task Module (BTM) for OCM

This module is responsible for handling asynchronous, non-blocking, and long-running tasks
within the OCM microservice. It manages task queues, scheduling, and execution monitoring
to ensure efficient background processing without blocking main operations.
"""

import asyncio
import logging
import json
from typing import Dict, Any, Optional, List, Callable, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import uuid
import time
from concurrent.futures import ThreadPoolExecutor
import threading

class TaskStatus(Enum):
    """Background task status."""
    PENDING = "pending"
    RUNNING = "running" 
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"

class TaskPriority(Enum):
    """Task priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class BackgroundTask:
    """Information about a background task."""
    task_id: str
    name: str
    function: str
    parameters: Dict[str, Any]
    priority: TaskPriority
    status: TaskStatus
    
    # Scheduling information
    created_at: datetime
    scheduled_for: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Execution details
    max_retries: int = 3
    retry_count: int = 0
    retry_delay: int = 60  # seconds
    timeout: Optional[int] = None  # seconds
    
    # Results and errors
    result: Any = None
    error_message: str = ""
    execution_time: float = 0.0
    
    # Dependencies and metadata
    depends_on: List[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.depends_on is None:
            self.depends_on = []
        if self.metadata is None:
            self.metadata = {}

class BackgroundTaskModule:
    """
    Background Task Module (BTM)
    
    Manages background tasks for OCM:
    - Task queue management with priorities
    - Asynchronous task execution
    - Task scheduling and dependencies
    - Retry logic and error handling
    - Long-running task monitoring
    - Task result storage and retrieval
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the BTM module."""
        self.logger = logging.getLogger(__name__)
        self.module_name = "BTM"
        self.is_active = False
        
        # Configuration
        self.config = config
        self.btm_config = config.get('background_tasks', {})
        
        # Task execution settings
        self.max_concurrent_tasks = self.btm_config.get('max_concurrent_tasks', 10)
        self.task_timeout_default = self.btm_config.get('task_timeout_default', 300)  # 5 minutes
        self.cleanup_interval = self.btm_config.get('cleanup_interval', 3600)  # 1 hour
        self.max_completed_tasks = self.btm_config.get('max_completed_tasks', 1000)
        
        # Task queues by priority
        self.task_queues = {
            TaskPriority.CRITICAL: asyncio.Queue(),
            TaskPriority.HIGH: asyncio.Queue(),
            TaskPriority.MEDIUM: asyncio.Queue(),
            TaskPriority.LOW: asyncio.Queue()
        }
        
        # Task storage
        self.pending_tasks = {}  # task_id -> BackgroundTask
        self.running_tasks = {}  # task_id -> BackgroundTask
        self.completed_tasks = {}  # task_id -> BackgroundTask (limited history)
        self.scheduled_tasks = {}  # task_id -> BackgroundTask (future tasks)
        
        # Task executors
        self.executor = ThreadPoolExecutor(max_workers=self.max_concurrent_tasks)
        self.running_futures = {}  # task_id -> asyncio.Task
        
        # Available task functions
        self.task_functions = {}
        
        # Statistics
        self.stats = {
            'tasks_created': 0,
            'tasks_completed': 0,
            'tasks_failed': 0,
            'tasks_retried': 0,
            'tasks_cancelled': 0,
            'average_execution_time': 0.0,
            'concurrent_tasks': 0,
            'queue_sizes': {
                'critical': 0,
                'high': 0,
                'medium': 0,
                'low': 0
            }
        }
        
        # Register built-in task functions
        self._register_builtin_tasks()
        
        self.logger.info(f"{self.module_name} initialized - max concurrent tasks: {self.max_concurrent_tasks}")
    
    async def start(self):
        """Start the BTM module."""
        try:
            self.is_active = True
            
            # Start task processors for each priority level
            asyncio.create_task(self._task_processor(TaskPriority.CRITICAL))
            asyncio.create_task(self._task_processor(TaskPriority.HIGH))
            asyncio.create_task(self._task_processor(TaskPriority.MEDIUM))
            asyncio.create_task(self._task_processor(TaskPriority.LOW))
            
            # Start task scheduler
            asyncio.create_task(self._task_scheduler())
            
            # Start cleanup task
            asyncio.create_task(self._cleanup_tasks())
            
            # Start statistics updater
            asyncio.create_task(self._update_statistics())
            
            self.logger.info("BTM started successfully - background task processing enabled")
            
        except Exception as e:
            self.logger.error(f"Failed to start BTM: {e}")
            raise
    
    async def stop(self):
        """Stop the BTM module gracefully."""
        try:
            self.is_active = False
            
            # Cancel all running tasks
            for task_id, future in self.running_futures.items():
                if not future.done():
                    future.cancel()
                    # Update task status
                    if task_id in self.running_tasks:
                        self.running_tasks[task_id].status = TaskStatus.CANCELLED
                        self.running_tasks[task_id].completed_at = datetime.now()
            
            # Shutdown thread pool executor
            self.executor.shutdown(wait=True)
            
            self.logger.info("BTM stopped successfully")
            
        except Exception as e:
            self.logger.error(f"Error stopping BTM: {e}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        is_healthy = (
            self.is_active and
            len(self.running_tasks) <= self.max_concurrent_tasks and
            not self.executor._shutdown
        )
        
        return {
            'healthy': is_healthy,
            'is_active': self.is_active,
            'module': 'btm'
        }
    
    def _register_builtin_tasks(self):
        """Register built-in task functions."""
        self.task_functions = {
            'report_cleanup': self._task_report_cleanup,
            'database_backup': self._task_database_backup,
            'certificate_validation': self._task_certificate_validation,
            'log_rotation': self._task_log_rotation,
            'metrics_aggregation': self._task_metrics_aggregation,
            'health_check_all_modules': self._task_health_check_all_modules,
            'cache_cleanup': self._task_cache_cleanup,
            'error_analysis': self._task_error_analysis,
            'performance_monitoring': self._task_performance_monitoring,
            'template_update': self._task_template_update
        }
    
    def register_task_function(self, name: str, function: Callable):
        """Register a custom task function."""
        self.task_functions[name] = function
        self.logger.info(f"Registered task function: {name}")
    
    async def create_task(self, 
                         name: str,
                         function: str,
                         parameters: Dict[str, Any] = None,
                         priority: TaskPriority = TaskPriority.MEDIUM,
                         schedule_for: Optional[datetime] = None,
                         max_retries: int = 3,
                         timeout: Optional[int] = None,
                         depends_on: List[str] = None,
                         metadata: Dict[str, Any] = None) -> str:
        """Create a new background task."""
        try:
            task_id = str(uuid.uuid4())
            
            # Create task object
            task = BackgroundTask(
                task_id=task_id,
                name=name,
                function=function,
                parameters=parameters or {},
                priority=priority,
                status=TaskStatus.PENDING,
                created_at=datetime.now(),
                scheduled_for=schedule_for,
                max_retries=max_retries,
                timeout=timeout or self.task_timeout_default,
                depends_on=depends_on or [],
                metadata=metadata or {}
            )
            
            # Store task
            if schedule_for and schedule_for > datetime.now():
                # Future scheduled task
                self.scheduled_tasks[task_id] = task
            else:
                # Immediate task
                self.pending_tasks[task_id] = task
                await self._queue_task(task)
            
            self.stats['tasks_created'] += 1
            
            self.logger.info(f"Created background task: {name} (ID: {task_id})")
            return task_id
            
        except Exception as e:
            self.logger.error(f"Failed to create task: {e}")
            raise
    
    async def _queue_task(self, task: BackgroundTask):
        """Queue a task for execution."""
        try:
            # Check dependencies
            if not await self._check_dependencies(task):
                self.logger.info(f"Task {task.task_id} waiting for dependencies")
                return False
            
            # Queue based on priority
            queue = self.task_queues[task.priority]
            await queue.put(task)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to queue task {task.task_id}: {e}")
            return False
    
    async def _check_dependencies(self, task: BackgroundTask) -> bool:
        """Check if task dependencies are satisfied."""
        if not task.depends_on:
            return True
        
        for dep_task_id in task.depends_on:
            # Check if dependency is completed
            if dep_task_id not in self.completed_tasks:
                return False
            
            # Check if dependency completed successfully
            dep_task = self.completed_tasks[dep_task_id]
            if dep_task.status != TaskStatus.COMPLETED:
                return False
        
        return True
    
    async def _task_processor(self, priority: TaskPriority):
        """Process tasks from a specific priority queue."""
        queue = self.task_queues[priority]
        
        while self.is_active:
            try:
                # Wait for task with timeout
                task = await asyncio.wait_for(queue.get(), timeout=1.0)
                
                # Check if we have capacity
                if len(self.running_tasks) >= self.max_concurrent_tasks:
                    # Re-queue task and wait
                    await queue.put(task)
                    await asyncio.sleep(1)
                    continue
                
                # Execute task
                await self._execute_task(task)
                
            except asyncio.TimeoutError:
                # No tasks available, continue
                continue
            except Exception as e:
                self.logger.error(f"Error in task processor for {priority.value}: {e}")
                await asyncio.sleep(1)
    
    async def _execute_task(self, task: BackgroundTask):
        """Execute a background task."""
        try:
            # Move to running
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now()
            
            if task.task_id in self.pending_tasks:
                del self.pending_tasks[task.task_id]
            
            self.running_tasks[task.task_id] = task
            
            self.logger.info(f"Executing task: {task.name} (ID: {task.task_id})")
            
            # Get task function
            if task.function not in self.task_functions:
                raise ValueError(f"Unknown task function: {task.function}")
            
            task_func = self.task_functions[task.function]
            
            # Create and start execution future
            future = asyncio.create_task(self._run_task_with_timeout(task, task_func))
            self.running_futures[task.task_id] = future
            
            # Don't await here - let it run in background
            
        except Exception as e:
            # Mark task as failed
            task.status = TaskStatus.FAILED
            task.error_message = str(e)
            task.completed_at = datetime.now()
            
            await self._move_task_to_completed(task)
            
            self.logger.error(f"Failed to execute task {task.task_id}: {e}")
    
    async def _run_task_with_timeout(self, task: BackgroundTask, task_func: Callable):
        """Run task function with timeout and error handling."""
        try:
            start_time = time.time()
            
            # Execute task function
            if task.timeout:
                result = await asyncio.wait_for(
                    task_func(task.parameters), 
                    timeout=task.timeout
                )
            else:
                result = await task_func(task.parameters)
            
            # Task completed successfully
            end_time = time.time()
            task.execution_time = end_time - start_time
            task.result = result
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
            
            self.stats['tasks_completed'] += 1
            
            self.logger.info(f"Task completed: {task.name} (ID: {task.task_id}) in {task.execution_time:.2f}s")
            
        except asyncio.TimeoutError:
            # Task timed out
            task.status = TaskStatus.FAILED
            task.error_message = f"Task timed out after {task.timeout} seconds"
            task.completed_at = datetime.now()
            
            self.logger.error(f"Task timed out: {task.name} (ID: {task.task_id})")
            
        except asyncio.CancelledError:
            # Task was cancelled
            task.status = TaskStatus.CANCELLED
            task.completed_at = datetime.now()
            
            self.logger.info(f"Task cancelled: {task.name} (ID: {task.task_id})")
            
        except Exception as e:
            # Task failed
            task.status = TaskStatus.FAILED
            task.error_message = str(e)
            task.completed_at = datetime.now()
            
            self.logger.error(f"Task failed: {task.name} (ID: {task.task_id}): {e}")
        
        finally:
            # Clean up
            if task.task_id in self.running_futures:
                del self.running_futures[task.task_id]
            
            # Check if task should be retried
            if (task.status == TaskStatus.FAILED and 
                task.retry_count < task.max_retries):
                await self._retry_task(task)
            else:
                await self._move_task_to_completed(task)
    
    async def _retry_task(self, task: BackgroundTask):
        """Retry a failed task."""
        try:
            task.retry_count += 1
            task.status = TaskStatus.RETRYING
            
            self.stats['tasks_retried'] += 1
            
            # Schedule retry with delay
            retry_delay = task.retry_delay * task.retry_count  # Exponential backoff
            retry_time = datetime.now() + timedelta(seconds=retry_delay)
            task.scheduled_for = retry_time
            
            # Move to scheduled tasks
            if task.task_id in self.running_tasks:
                del self.running_tasks[task.task_id]
            
            self.scheduled_tasks[task.task_id] = task
            
            self.logger.info(f"Retrying task {task.task_id} in {retry_delay} seconds (attempt {task.retry_count})")
            
        except Exception as e:
            self.logger.error(f"Failed to schedule retry for task {task.task_id}: {e}")
            await self._move_task_to_completed(task)
    
    async def _move_task_to_completed(self, task: BackgroundTask):
        """Move task to completed storage."""
        try:
            # Remove from running tasks
            if task.task_id in self.running_tasks:
                del self.running_tasks[task.task_id]
            
            # Add to completed tasks
            self.completed_tasks[task.task_id] = task
            
            # Update statistics based on final status
            if task.status == TaskStatus.FAILED:
                self.stats['tasks_failed'] += 1
            elif task.status == TaskStatus.CANCELLED:
                self.stats['tasks_cancelled'] += 1
            
            # Maintain completed task history limit
            if len(self.completed_tasks) > self.max_completed_tasks:
                # Remove oldest completed tasks
                oldest_tasks = sorted(
                    self.completed_tasks.items(),
                    key=lambda x: x[1].completed_at or x[1].created_at
                )
                
                tasks_to_remove = len(self.completed_tasks) - self.max_completed_tasks
                for task_id, _ in oldest_tasks[:tasks_to_remove]:
                    del self.completed_tasks[task_id]
            
        except Exception as e:
            self.logger.error(f"Error moving task to completed: {e}")
    
    async def _task_scheduler(self):
        """Schedule future tasks for execution."""
        while self.is_active:
            try:
                current_time = datetime.now()
                
                # Check scheduled tasks
                ready_tasks = []
                for task_id, task in self.scheduled_tasks.items():
                    if task.scheduled_for and task.scheduled_for <= current_time:
                        ready_tasks.append(task_id)
                
                # Move ready tasks to pending
                for task_id in ready_tasks:
                    task = self.scheduled_tasks[task_id]
                    del self.scheduled_tasks[task_id]
                    
                    # Reset status and queue
                    task.status = TaskStatus.PENDING
                    self.pending_tasks[task_id] = task
                    
                    if await self._queue_task(task):
                        self.logger.info(f"Scheduled task ready for execution: {task.name}")
                
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                self.logger.error(f"Error in task scheduler: {e}")
                await asyncio.sleep(10)
    
    async def _cleanup_tasks(self):
        """Cleanup old completed tasks and handle stuck tasks."""
        while self.is_active:
            try:
                current_time = datetime.now()
                
                # Check for stuck running tasks
                stuck_tasks = []
                for task_id, task in self.running_tasks.items():
                    if task.started_at:
                        running_time = current_time - task.started_at
                        max_running_time = timedelta(seconds=task.timeout * 2) if task.timeout else timedelta(hours=1)
                        
                        if running_time > max_running_time:
                            stuck_tasks.append(task_id)
                
                # Cancel stuck tasks
                for task_id in stuck_tasks:
                    future = self.running_futures.get(task_id)
                    if future and not future.done():
                        future.cancel()
                    
                    task = self.running_tasks[task_id]
                    task.status = TaskStatus.FAILED
                    task.error_message = "Task stuck - force cancelled"
                    task.completed_at = current_time
                    
                    await self._move_task_to_completed(task)
                    
                    self.logger.warning(f"Cancelled stuck task: {task.name} (ID: {task_id})")
                
                await asyncio.sleep(self.cleanup_interval)
                
            except Exception as e:
                self.logger.error(f"Error in task cleanup: {e}")
                await asyncio.sleep(self.cleanup_interval)
    
    async def _update_statistics(self):
        """Update task statistics."""
        while self.is_active:
            try:
                # Update queue sizes
                for priority in TaskPriority:
                    self.stats['queue_sizes'][priority.value] = self.task_queues[priority].qsize()
                
                # Update concurrent tasks count
                self.stats['concurrent_tasks'] = len(self.running_tasks)
                
                # Update average execution time
                if self.stats['tasks_completed'] > 0:
                    total_time = sum(
                        task.execution_time for task in self.completed_tasks.values()
                        if task.status == TaskStatus.COMPLETED and task.execution_time > 0
                    )
                    self.stats['average_execution_time'] = total_time / self.stats['tasks_completed']
                
                await asyncio.sleep(30)  # Update every 30 seconds
                
            except Exception as e:
                self.logger.error(f"Error updating statistics: {e}")
                await asyncio.sleep(30)
    
    # Built-in Task Functions
    
    async def _task_report_cleanup(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Clean up old generated reports."""
        try:
            # Simulate report cleanup
            await asyncio.sleep(1)
            
            return {
                'status': 'success',
                'reports_cleaned': parameters.get('count', 10),
                'disk_space_freed': '50MB'
            }
        except Exception as e:
            raise Exception(f"Report cleanup failed: {e}")
    
    async def _task_database_backup(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Perform database backup."""
        try:
            # Simulate database backup
            await asyncio.sleep(5)
            
            return {
                'status': 'success',
                'backup_file': f"ocm_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db",
                'backup_size': '10MB'
            }
        except Exception as e:
            raise Exception(f"Database backup failed: {e}")
    
    async def _task_certificate_validation(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Validate SSL certificates."""
        try:
            # Simulate certificate validation
            await asyncio.sleep(2)
            
            return {
                'status': 'success',
                'certificates_checked': 3,
                'expiry_warnings': 0,
                'next_expiry': '2024-12-31'
            }
        except Exception as e:
            raise Exception(f"Certificate validation failed: {e}")
    
    async def _task_log_rotation(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Rotate log files."""
        try:
            # Simulate log rotation
            await asyncio.sleep(1)
            
            return {
                'status': 'success',
                'files_rotated': 3,
                'old_logs_archived': True
            }
        except Exception as e:
            raise Exception(f"Log rotation failed: {e}")
    
    async def _task_metrics_aggregation(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Aggregate performance metrics."""
        try:
            # Simulate metrics aggregation
            await asyncio.sleep(3)
            
            return {
                'status': 'success',
                'metrics_processed': 1000,
                'time_period': '1hour'
            }
        except Exception as e:
            raise Exception(f"Metrics aggregation failed: {e}")
    
    async def _task_health_check_all_modules(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Perform health check on all modules."""
        try:
            # Simulate module health checks
            await asyncio.sleep(2)
            
            return {
                'status': 'success',
                'modules_checked': 13,
                'healthy_modules': 13,
                'warnings': 0
            }
        except Exception as e:
            raise Exception(f"Module health check failed: {e}")
    
    async def _task_cache_cleanup(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Clean up cached data."""
        try:
            # Simulate cache cleanup
            await asyncio.sleep(1)
            
            return {
                'status': 'success',
                'cache_entries_removed': 250,
                'memory_freed': '25MB'
            }
        except Exception as e:
            raise Exception(f"Cache cleanup failed: {e}")
    
    async def _task_error_analysis(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze error patterns."""
        try:
            # Simulate error analysis
            await asyncio.sleep(4)
            
            return {
                'status': 'success',
                'errors_analyzed': 50,
                'patterns_found': 3,
                'recommendations': ['Increase timeout', 'Add retry logic']
            }
        except Exception as e:
            raise Exception(f"Error analysis failed: {e}")
    
    async def _task_performance_monitoring(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Monitor system performance."""
        try:
            # Simulate performance monitoring
            await asyncio.sleep(2)
            
            return {
                'status': 'success',
                'cpu_usage': '45%',
                'memory_usage': '62%',
                'active_connections': 12
            }
        except Exception as e:
            raise Exception(f"Performance monitoring failed: {e}")
    
    async def _task_template_update(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Update report templates."""
        try:
            # Simulate template update
            await asyncio.sleep(3)
            
            return {
                'status': 'success',
                'templates_updated': parameters.get('count', 5),
                'cache_refreshed': True
            }
        except Exception as e:
            raise Exception(f"Template update failed: {e}")
    
    # Public API Methods
    
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a specific task."""
        try:
            # Check running tasks
            if task_id in self.running_tasks:
                future = self.running_futures.get(task_id)
                if future and not future.done():
                    future.cancel()
                
                task = self.running_tasks[task_id]
                task.status = TaskStatus.CANCELLED
                task.completed_at = datetime.now()
                
                await self._move_task_to_completed(task)
                return True
            
            # Check pending tasks
            if task_id in self.pending_tasks:
                task = self.pending_tasks[task_id]
                del self.pending_tasks[task_id]
                
                task.status = TaskStatus.CANCELLED
                task.completed_at = datetime.now()
                
                self.completed_tasks[task_id] = task
                return True
            
            # Check scheduled tasks
            if task_id in self.scheduled_tasks:
                task = self.scheduled_tasks[task_id]
                del self.scheduled_tasks[task_id]
                
                task.status = TaskStatus.CANCELLED
                task.completed_at = datetime.now()
                
                self.completed_tasks[task_id] = task
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to cancel task {task_id}: {e}")
            return False
    
    def get_task_info(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific task."""
        task = (self.pending_tasks.get(task_id) or
                self.running_tasks.get(task_id) or
                self.completed_tasks.get(task_id) or
                self.scheduled_tasks.get(task_id))
        
        if task:
            return asdict(task)
        return None
    
    def get_tasks_by_status(self, status: TaskStatus) -> List[Dict[str, Any]]:
        """Get all tasks with a specific status."""
        tasks = []
        
        # Search in all task collections
        all_tasks = {
            **self.pending_tasks,
            **self.running_tasks,
            **self.completed_tasks,
            **self.scheduled_tasks
        }
        
        for task in all_tasks.values():
            if task.status == status:
                tasks.append(asdict(task))
        
        return tasks
    
    async def process_pending_tasks(self):
        """Process any pending tasks (called by main service)."""
        # This method is called by the main OCM service
        # The actual processing is handled by the task processors
        pass
    
    def get_status(self) -> Dict[str, Any]:
        """Get current BTM status."""
        return {
            'module': self.module_name,
            'active': self.is_active,
            'max_concurrent_tasks': self.max_concurrent_tasks,
            'task_counts': {
                'pending': len(self.pending_tasks),
                'running': len(self.running_tasks),
                'completed': len(self.completed_tasks),
                'scheduled': len(self.scheduled_tasks)
            },
            'registered_functions': list(self.task_functions.keys()),
            'stats': self.stats.copy()
        } 