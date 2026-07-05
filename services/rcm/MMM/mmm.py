"""
Memory Management Module (MMM)

Monitors RAM usage. If memory consumption exceeds a predefined threshold, this module will automatically spill overflow data (e.g., request queues, caches) to disk.
"""

import asyncio
import logging
import psutil
import json
import pickle
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
import threading
import time
from collections import deque

# Import error management module
from EMM.emm import ErrorManagementModule
from EMM.api_error_handler import api_error_handler


class MemoryMonitor:
    """Monitors system memory usage."""
    
    def __init__(self):
        self.process = psutil.Process()
        self.last_check = None
        self.memory_history = []
        self.max_history_size = 100
    
    def get_memory_usage(self) -> Dict[str, Any]:
        """
        Get current memory usage.
        
        Returns:
            Dictionary with memory usage information
        """
        # Get system memory
        system_memory = psutil.virtual_memory()
        
        # Get process memory
        process_memory = self.process.memory_info()
        
        memory_info = {
            "system": {
                "total": system_memory.total,
                "available": system_memory.available,
                "used": system_memory.used,
                "percent": system_memory.percent
            },
            "process": {
                "rss": process_memory.rss,  # Resident Set Size
                "vms": process_memory.vms,  # Virtual Memory Size
                "percent": self.process.memory_percent()
            },
            "timestamp": datetime.now().isoformat()
        }
        
        # Update history
        self.memory_history.append(memory_info)
        if len(self.memory_history) > self.max_history_size:
            self.memory_history.pop(0)
        
        self.last_check = datetime.now()
        return memory_info
    
    def get_memory_trend(self) -> Dict[str, Any]:
        """
        Get memory usage trend.
        
        Returns:
            Dictionary with memory trend information
        """
        if len(self.memory_history) < 2:
            return {"trend": "insufficient_data"}
        
        recent = self.memory_history[-1]["system"]["percent"]
        older = self.memory_history[0]["system"]["percent"]
        
        if recent > older + 5:
            trend = "increasing"
        elif recent < older - 5:
            trend = "decreasing"
        else:
            trend = "stable"
        
        return {
            "trend": trend,
            "current_percent": recent,
            "change": recent - older,
            "history_size": len(self.memory_history)
        }


class RequestQueue:
    """FIFO queue for managing RCM requests in memory."""
    
    def __init__(self):
        self.queue = deque()
        self.lock = threading.Lock()
        self.request_counter = 0
    
    def add_request(self, request_data: Dict[str, Any]) -> str:
        """
        Add a request to the queue.
        
        Args:
            request_data: Request data to add
            
        Returns:
            Request ID
        """
        with self.lock:
            request_id = f"req_{self.request_counter}_{int(time.time())}"
            self.request_counter += 1
            
            request_entry = {
                "id": request_id,
                "data": request_data,
                "timestamp": datetime.now().isoformat(),
                "status": "queued"
            }
            
            self.queue.append(request_entry)
            return request_id
    
    def get_oldest_request(self) -> Optional[Dict[str, Any]]:
        """
        Get the oldest request from the queue (FIFO).
        
        Returns:
            Oldest request or None if queue is empty
        """
        with self.lock:
            if self.queue:
                return self.queue.popleft()
            return None
    
    def get_newest_request(self) -> Optional[Dict[str, Any]]:
        """
        Get the newest request from the queue (for spilling).
        
        Returns:
            Newest request or None if queue is empty
        """
        with self.lock:
            if self.queue:
                return self.queue.pop()
            return None
    
    def get_queue_size(self) -> int:
        """Get current queue size."""
        with self.lock:
            return len(self.queue)
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get queue status information."""
        with self.lock:
            return {
                "size": len(self.queue),
                "oldest_timestamp": self.queue[0]["timestamp"] if self.queue else None,
                "newest_timestamp": self.queue[-1]["timestamp"] if self.queue else None,
                "total_requests": self.request_counter
            }


class DiskSpillManager:
    """Manages spilling data to disk when memory is low."""
    
    def __init__(self, spill_directory: Path):
        self.spill_directory = spill_directory
        self.spill_directory.mkdir(parents=True, exist_ok=True)
        self.spilled_data = {}
        self.lock = threading.Lock()
    
    def spill_data(self, key: str, data: Any) -> bool:
        """
        Spill data to disk using JSON format.
        
        Args:
            key: Unique identifier for the data
            data: Data to spill
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self.lock:
                file_path = self.spill_directory / f"{key}.spill"
                
                # Use JSON format for compatibility with DRM
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, default=str)
                
                self.spilled_data[key] = {
                    "file_path": str(file_path),
                    "size": file_path.stat().st_size,
                    "timestamp": datetime.now().isoformat()
                }
                
                return True
                
        except Exception as e:
            logging.error(f"Failed to spill data {key}: {e}")
            return False
    
    def restore_data(self, key: str) -> Optional[Any]:
        """
        Restore data from disk using JSON format.
        
        Args:
            key: Unique identifier for the data
            
        Returns:
            Restored data or None if failed
        """
        try:
            with self.lock:
                if key not in self.spilled_data:
                    return None
                
                file_path = Path(self.spilled_data[key]["file_path"])
                
                if not file_path.exists():
                    del self.spilled_data[key]
                    return None
                
                # Use JSON format for compatibility
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Remove spilled data after successful restore
                file_path.unlink()
                del self.spilled_data[key]
                
                return data
                
        except Exception as e:
            logging.error(f"Failed to restore data {key}: {e}")
            return None
    
    def cleanup_old_spills(self, max_age_hours: int = 24):
        """
        Clean up old spilled data.
        
        Args:
            max_age_hours: Maximum age in hours
        """
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        with self.lock:
            keys_to_remove = []
            
            for key, info in self.spilled_data.items():
                spill_time = datetime.fromisoformat(info["timestamp"])
                if spill_time < cutoff_time:
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                try:
                    file_path = Path(self.spilled_data[key]["file_path"])
                    if file_path.exists():
                        file_path.unlink()
                    del self.spilled_data[key]
                except Exception as e:
                    logging.warning(f"Failed to cleanup spilled data {key}: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get spill manager status.
        
        Returns:
            Dictionary with spill manager status
        """
        total_size = sum(info["size"] for info in self.spilled_data.values())
        
        return {
            "spill_directory": str(self.spill_directory),
            "spilled_files": len(self.spilled_data),
            "total_size_bytes": total_size,
            "spilled_data": self.spilled_data.copy()
        }


class MemoryManagementModule:
    """
    Memory Management Module (MMM)
    
    Monitors RAM usage and automatically spills overflow data to disk.
    Uses 40% threshold as per requirements.
    """
    
    def __init__(self):
        """Initialize the MMM module."""
        self.logger = logging.getLogger(__name__)
        self.error_manager = ErrorManagementModule()
        
        # Memory monitoring
        self.memory_monitor = MemoryMonitor()
        
        # Request queue for FIFO management
        self.request_queue = RequestQueue()
        
        # Disk spill management
        self.spill_manager = DiskSpillManager(Path("cache/"))
        
        # Configuration - Updated to 40% threshold
        self.memory_threshold_percent = 40.0  # Alert when system memory > 40%
        self.process_threshold_percent = 35.0  # Alert when process memory > 35%
        self.critical_threshold_percent = 50.0  # Critical threshold
        self.restore_threshold_percent = 30.0  # Restore when below 30%
        
        # Monitoring state
        self.is_monitoring = False
        self.monitoring_task = None
        self.cleanup_task = None
        
        # Callbacks for memory events
        self.memory_callbacks = {
            "high_memory": [],
            "critical_memory": [],
            "memory_restored": []
        }
        
        # Statistics
        self.stats = {
            "memory_checks": 0,
            "high_memory_events": 0,
            "critical_memory_events": 0,
            "data_spills": 0,
            "data_restores": 0,
            "requests_spilled": 0,
            "requests_restored": 0,
            "last_alert": None
        }
        
        # Error codes now generated dynamically by EMM
        self.check_interval = 5.0  # seconds
        self.cleanup_interval = 3600.0  # 1 hour
    
    async def start(self):
        """Start the MMM module."""
        self.is_monitoring = True
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        self.cleanup_task = asyncio.create_task(self._cleanup_loop())
        self.logger.info("MMM module started with 40% threshold")
    
    async def stop(self):
        """Stop the MMM module."""
        self.is_monitoring = False
        
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("MMM module stopped")
    
    async def _monitoring_loop(self):
        """Main memory monitoring loop."""
        while self.is_monitoring:
            try:
                await self._check_memory_usage()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                error_msg = f"Error in monitoring loop: {e}"
                self.log_error(error_msg, "MemoryManagementModule", "_monitoring_loop")
                await asyncio.sleep(10)  # Wait before retrying
    
    async def _cleanup_loop(self):
        """Periodic cleanup of old spilled data."""
        while self.is_monitoring:
            try:
                await asyncio.sleep(self.cleanup_interval)
                self.spill_manager.cleanup_old_spills()
            except asyncio.CancelledError:
                break
            except Exception as e:
                error_msg = f"Error in cleanup loop: {e}"
                self.log_error(error_msg, "MemoryManagementModule", "_cleanup_loop")
                await asyncio.sleep(60)
    
    async def _check_memory_usage(self):
        """Check current memory usage and take action if needed."""
        self.stats["memory_checks"] += 1
        
        memory_info = self.memory_monitor.get_memory_usage()
        system_percent = memory_info["system"]["percent"]
        process_percent = memory_info["process"]["percent"]
        
        # Check for critical memory usage
        if system_percent > self.critical_threshold_percent:
            await self._handle_critical_memory(memory_info)
        # Check for high memory usage
        elif system_percent > self.memory_threshold_percent or process_percent > self.process_threshold_percent:
            await self._handle_high_memory(memory_info)
        # Check if memory has been restored
        elif system_percent < self.restore_threshold_percent:
            await self._handle_memory_restored(memory_info)
    
    async def _handle_high_memory(self, memory_info: Dict[str, Any]):
        """Handle high memory usage - spill newest requests to disk."""
        self.stats["high_memory_events"] += 1
        self.stats["last_alert"] = datetime.now().isoformat()
        
        self.logger.warning(f"High memory usage detected: System {memory_info['system']['percent']:.1f}%, Process {memory_info['process']['percent']:.1f}%")
        
        # Spill newest requests to disk (FIFO - newest first)
        await self._spill_newest_requests()
        
        # Call high memory callbacks
        for callback in self.memory_callbacks["high_memory"]:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(memory_info)
                else:
                    callback(memory_info)
            except Exception as e:
                error_msg = f"Error in high memory callback: {e}"
                self.log_error(error_msg, "MemoryManagementModule", "_handle_high_memory")
    
    async def _handle_critical_memory(self, memory_info: Dict[str, Any]):
        """Handle critical memory usage - aggressive spilling."""
        self.stats["critical_memory_events"] += 1
        self.stats["last_alert"] = datetime.now().isoformat()
        
        self.logger.critical(f"Critical memory usage detected: System {memory_info['system']['percent']:.1f}%, Process {memory_info['process']['percent']:.1f}%")
        
        # Aggressive spilling of requests
        await self._spill_newest_requests(aggressive=True)
        
        # Call critical memory callbacks
        for callback in self.memory_callbacks["critical_memory"]:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(memory_info)
                else:
                    callback(memory_info)
            except Exception as e:
                error_msg = f"Error in critical memory callback: {e}"
                self.log_error(error_msg, "MemoryManagementModule", "_handle_critical_memory")
    
    async def _handle_memory_restored(self, memory_info: Dict[str, Any]):
        """Handle memory restoration - restore spilled requests."""
        self.logger.info(f"Memory usage restored: System {memory_info['system']['percent']:.1f}%, Process {memory_info['process']['percent']:.1f}%")
        
        # Restore spilled requests (FIFO - oldest first)
        await self._restore_spilled_requests()
        
        # Call memory restored callbacks
        for callback in self.memory_callbacks["memory_restored"]:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(memory_info)
                else:
                    callback(memory_info)
            except Exception as e:
                error_msg = f"Error in memory restored callback: {e}"
                self.log_error(error_msg, "MemoryManagementModule", "_handle_memory_restored")
    
    async def _spill_newest_requests(self, aggressive: bool = False):
        """Spill newest requests to disk (FIFO - newest first)."""
        try:
            queue_size = self.request_queue.get_queue_size()
            if queue_size == 0:
                return
            
            # Calculate how many requests to spill
            if aggressive:
                spill_count = max(1, queue_size // 2)  # Spill half in critical mode
            else:
                spill_count = max(1, queue_size // 4)  # Spill quarter in high memory mode
            
            spilled_count = 0
            for _ in range(spill_count):
                request = self.request_queue.get_newest_request()
                if request is None:
                    break
                
                # Spill to disk
                success = await self.spill_data(f"request_{request['id']}", request)
                if success:
                    spilled_count += 1
                    self.stats["requests_spilled"] += 1
                    self.logger.info(f"Spilled request {request['id']} to disk")
            
            self.logger.info(f"Spilled {spilled_count} newest requests to disk")
            
        except Exception as e:
            error_msg = f"Error spilling newest requests: {e}"
            self.log_error(error_msg, "MemoryManagementModule", "_spill_newest_requests")
    
    async def _restore_spilled_requests(self):
        """Restore spilled requests from disk (FIFO - oldest first)."""
        try:
            # Get all spill files
            spill_files = list(self.spill_manager.spill_directory.glob("*.spill"))
            if not spill_files:
                return
            
            # Sort by creation time (oldest first)
            spill_files.sort(key=lambda x: x.stat().st_ctime)
            
            restored_count = 0
            for spill_file in spill_files:
                try:
                    # Extract request ID from filename
                    request_id = spill_file.stem.replace("request_", "")
                    
                    # Restore from disk
                    data = await self.restore_data(request_id)
                    if data is not None:
                        # Add back to queue (at the end for FIFO)
                        self.request_queue.queue.append(data)
                        restored_count += 1
                        self.stats["requests_restored"] += 1
                        self.logger.info(f"Restored request {request_id} from disk")
                        
                        # Limit restoration to avoid memory issues
                        if restored_count >= 10:  # Restore max 10 at a time
                            break
                            
                except Exception as e:
                    self.logger.error(f"Failed to restore request from {spill_file}: {e}")
            
            self.logger.info(f"Restored {restored_count} spilled requests from disk")
            
        except Exception as e:
            error_msg = f"Error restoring spilled requests: {e}"
            self.log_error(error_msg, "MemoryManagementModule", "_restore_spilled_requests")
    
    async def spill_data(self, key: str, data: Any) -> bool:
        """
        Spill data to disk.
        
        Args:
            key: Unique identifier for the data
            data: Data to spill
            
        Returns:
            True if successful, False otherwise
        """
        try:
            success = self.spill_manager.spill_data(key, data)
            if success:
                self.stats["data_spills"] += 1
                self.logger.info(f"Spilled data {key} to disk")
            return success
        except Exception as e:
            error_msg = f"Error spilling data for key {key}: {e}"
            self.log_error(error_msg, "MemoryManagementModule", "spill_data")
            return False
    
    async def restore_data(self, key: str) -> Optional[Any]:
        """
        Restore data from disk.
        
        Args:
            key: Unique identifier for the data
            
        Returns:
            Restored data or None if failed
        """
        try:
            data = self.spill_manager.restore_data(key)
            if data is not None:
                self.stats["data_restores"] += 1
                self.logger.info(f"Restored data {key} from disk")
            return data
        except Exception as e:
            error_msg = f"Error restoring data for key {key}: {e}"
            self.log_error(error_msg, "MemoryManagementModule", "restore_data")
            return None
    
    def add_request(self, request_data: Dict[str, Any]) -> str:
        """
        Add a new request to the queue.
        
        Args:
            request_data: Request data to add
            
        Returns:
            Request ID
        """
        return self.request_queue.add_request(request_data)
    
    def get_oldest_request(self) -> Optional[Dict[str, Any]]:
        """
        Get the oldest request from the queue (FIFO).
        
        Returns:
            Oldest request or None if queue is empty
        """
        return self.request_queue.get_oldest_request()
    
    def get_queue_status(self) -> Dict[str, Any]:
        """
        Get queue status information.
        
        Returns:
            Dictionary with queue status
        """
        return self.request_queue.get_queue_status()
    
    def add_memory_callback(self, event_type: str, callback: Callable):
        """
        Add a callback for memory events.
        
        Args:
            event_type: Type of event (high_memory, critical_memory, memory_restored)
            callback: Function to call when event occurs
        """
        if event_type in self.memory_callbacks:
            self.memory_callbacks[event_type].append(callback)
    
    async def configure_thresholds(self, memory_threshold: float, process_threshold: float, critical_threshold: float, restore_threshold: float):
        """
        Configure memory thresholds.
        
        Args:
            memory_threshold: System memory threshold percentage
            process_threshold: Process memory threshold percentage
            critical_threshold: Critical memory threshold percentage
            restore_threshold: Memory restoration threshold percentage
        """
        self.memory_threshold_percent = memory_threshold
        self.process_threshold_percent = process_threshold
        self.critical_threshold_percent = critical_threshold
        self.restore_threshold_percent = restore_threshold
        
        self.logger.info(f"Configured memory thresholds: System={memory_threshold}%, Process={process_threshold}%, Critical={critical_threshold}%, Restore={restore_threshold}%")
    
    async def get_memory_status(self) -> Dict[str, Any]:
        """
        Get current memory status.
        
        Returns:
            Dictionary with memory status information
        """
        memory_info = self.memory_monitor.get_memory_usage()
        memory_trend = self.memory_monitor.get_memory_trend()
        spill_status = self.spill_manager.get_status()
        queue_status = self.get_queue_status()
        
        return {
            "current_usage": memory_info,
            "trend": memory_trend,
            "thresholds": {
                "memory_threshold": self.memory_threshold_percent,
                "process_threshold": self.process_threshold_percent,
                "critical_threshold": self.critical_threshold_percent,
                "restore_threshold": self.restore_threshold_percent
            },
            "spill_status": spill_status,
            "queue_status": queue_status,
            "statistics": self.stats
        }
    
    async def get_status(self) -> Dict[str, Any]:
        """
        Get the status of the MMM module.
        
        Returns:
            Dictionary containing module status information
        """
        memory_status = await self.get_memory_status()
        
        return {
            "status": "active" if self.is_monitoring else "inactive",
            "is_monitoring": self.is_monitoring,
            "check_interval": self.check_interval,
            "memory_status": memory_status,
            "callback_counts": {
                event_type: len(callbacks) for event_type, callbacks in self.memory_callbacks.items()
            },
            "last_activity": datetime.now().isoformat()
        }

    def log_error(self, error_message: str, class_name: str = "UnknownClass", function_name: str = "UnknownFunction", sub_function: str = "001"):
        """Log an error using EMM."""
        return self.error_manager.log_error_with_generation(
            "MMM", 
            class_name, 
            function_name, 
            error_message, 
            sub_function
        )

    def generate_error_code(self, class_name: str = "UnknownClass", function_name: str = "UnknownFunction", sub_function: str = "001") -> str:
        """Generate an error code using EMM."""
        return self.error_manager.generate_error_code("MMM", class_name, function_name, sub_function)

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
                "MMM",
                "MMM",
                "handle_api_error",
                f"API Error: {result.get('api_error_type', 'unknown')}",
                context=result
            )
            await api_error_handler.send_error_report_to_ccu(result)
            return result
        except Exception as e:
            self.error_manager.log_error_with_generation(
                "MMM",
                "MMM",
                "handle_api_error",
                f"Error handling API error: {str(e)}"
            )
            return {"success": False, "error": str(e)}


# Global instance and alias for compatibility
mmm = MemoryManagementModule()
MMM = MemoryManagementModule  # Class alias