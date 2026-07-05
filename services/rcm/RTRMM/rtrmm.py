"""
Request Tracking and Response Mapping Module (RTRMM)

Implements a client-side system for tracking requests and mapping API responses back to their original requests using the unique Request ID.
"""

import asyncio
import logging
import json
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
import uuid
import time

# Import error management module
from EMM.emm import ErrorManagementModule
from EMM.api_error_handler import api_error_handler


class RequestTracker:
    """Tracks individual requests and their states."""
    
    def __init__(self, request_id: str):
        self.request_id = request_id
        self.status = "pending"
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.start_time = None
        self.end_time = None
        self.error = None
        self.response_data = None
        self.attempts = 0
        self.max_attempts = 3
        self.metadata = {}
    
    def start_processing(self):
        """Mark request as started."""
        self.status = "processing"
        self.start_time = datetime.now()
        self.updated_at = datetime.now()
    
    def complete_processing(self, response_data: Dict[str, Any]):
        """Mark request as completed."""
        self.status = "completed"
        self.end_time = datetime.now()
        self.updated_at = datetime.now()
        self.response_data = response_data
    
    def fail_processing(self, error: str):
        """Mark request as failed."""
        self.status = "failed"
        self.end_time = datetime.now()
        self.updated_at = datetime.now()
        self.error = error
    
    def retry_processing(self):
        """Increment retry count."""
        self.attempts += 1
        self.updated_at = datetime.now()
        if self.attempts >= self.max_attempts:
            self.status = "failed"
            self.error = "Max retry attempts exceeded"
    
    def get_processing_time(self) -> Optional[float]:
        """Get total processing time in seconds."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert tracker to dictionary."""
        return {
            "request_id": self.request_id,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "processing_time": self.get_processing_time(),
            "error": self.error,
            "attempts": self.attempts,
            "max_attempts": self.max_attempts,
            "metadata": self.metadata
        }


class RequestTrackingAndResponseMappingModule:
    """
    Request Tracking and Response Mapping Module (RTRMM)
    
    Implements a client-side system for tracking requests and mapping API responses.
    """
    
    def __init__(self):
        """Initialize the RTRMM module."""
        self.logger = logging.getLogger(__name__)
        self.error_manager = ErrorManagementModule()
        
        # Request tracking storage
        self.active_requests = {}
        self.completed_requests = {}
        self.failed_requests = {}
        
        # Response mapping
        self.response_mapping = {}
        
        # Callbacks
        self.completion_callbacks = {}
        self.error_callbacks = {}
        
        # Statistics
        self.stats = {
            "total_requests": 0,
            "active_requests": 0,
            "completed_requests": 0,
            "failed_requests": 0,
            "average_processing_time": 0,
            "total_processing_time": 0
        }
        
        # Error codes now generated dynamically by EMM
        
        # Cleanup settings
        self.cleanup_interval = 3600  # 1 hour
        self.retention_days = 7
        
        # Start cleanup task
        self.cleanup_task = None
    
    async def start(self):
        """Start the RTRMM module."""
        self.cleanup_task = asyncio.create_task(self._cleanup_loop())
        self.logger.info("RTRMM module started")
    
    async def stop(self):
        """Stop the RTRMM module."""
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
        self.logger.info("RTRMM module stopped")
    
    async def _cleanup_loop(self):
        """Periodic cleanup of old requests."""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                await self._cleanup_old_requests()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(60)  # Wait before retrying
    
    async def _cleanup_old_requests(self):
        """Clean up old completed and failed requests."""
        cutoff_date = datetime.now() - timedelta(days=self.retention_days)
        
        # Clean up completed requests
        old_completed = [
            req_id for req_id, tracker in self.completed_requests.items()
            if tracker.updated_at < cutoff_date
        ]
        for req_id in old_completed:
            del self.completed_requests[req_id]
        
        # Clean up failed requests
        old_failed = [
            req_id for req_id, tracker in self.failed_requests.items()
            if tracker.updated_at < cutoff_date
        ]
        for req_id in old_failed:
            del self.failed_requests[req_id]
        
        if old_completed or old_failed:
            self.logger.info(f"Cleaned up {len(old_completed)} completed and {len(old_failed)} failed requests")
    
    async def create_request(self, request_id: str, metadata: Dict[str, Any] = None) -> RequestTracker:
        """
        Create a new request tracker.
        
        Args:
            request_id: Unique request identifier
            metadata: Additional metadata for the request
            
        Returns:
            RequestTracker instance
        """
        if request_id in self.active_requests:
            raise ValueError(f"Request {request_id} already exists")
        
        tracker = RequestTracker(request_id)
        if metadata:
            tracker.metadata = metadata
        
        self.active_requests[request_id] = tracker
        self.stats["total_requests"] += 1
        self.stats["active_requests"] += 1
        
        self.logger.info(f"Created request tracker for {request_id}")
        return tracker
    
    async def start_request_processing(self, request_id: str) -> bool:
        """
        Mark a request as started processing.
        
        Args:
            request_id: Request identifier
            
        Returns:
            True if successful, False otherwise
        """
        if request_id not in self.active_requests:
            self.logger.error(f"Request {request_id} not found")
            return False
        
        tracker = self.active_requests[request_id]
        tracker.start_processing()
        
        self.logger.info(f"Started processing request {request_id}")
        return True
    
    async def complete_request(self, request_id: str, response_data: Dict[str, Any]) -> bool:
        """
        Mark a request as completed with response data.
        
        Args:
            request_id: Request identifier
            response_data: Response data from API
            
        Returns:
            True if successful, False otherwise
        """
        if request_id not in self.active_requests:
            self.logger.error(f"Request {request_id} not found")
            return False
        
        tracker = self.active_requests[request_id]
        tracker.complete_processing(response_data)
        
        # Move to completed requests
        self.completed_requests[request_id] = tracker
        del self.active_requests[request_id]
        
        # Update statistics
        self.stats["active_requests"] -= 1
        self.stats["completed_requests"] += 1
        
        processing_time = tracker.get_processing_time()
        if processing_time:
            self.stats["total_processing_time"] += processing_time
            self.stats["average_processing_time"] = (
                self.stats["total_processing_time"] / self.stats["completed_requests"]
            )
        
        # Store response mapping
        self.response_mapping[request_id] = response_data
        
        # Call completion callback
        await self._call_completion_callback(request_id, response_data)
        
        self.logger.info(f"Completed request {request_id}")
        return True
    
    async def fail_request(self, request_id: str, error: str) -> bool:
        """
        Mark a request as failed.
        
        Args:
            request_id: Request identifier
            error: Error message
            
        Returns:
            True if successful, False otherwise
        """
        if request_id not in self.active_requests:
            self.logger.error(f"Request {request_id} not found")
            return False
        
        tracker = self.active_requests[request_id]
        tracker.fail_processing(error)
        
        # Move to failed requests
        self.failed_requests[request_id] = tracker
        del self.active_requests[request_id]
        
        # Update statistics
        self.stats["active_requests"] -= 1
        self.stats["failed_requests"] += 1
        
        # Call error callback
        await self._call_error_callback(request_id, error)
        
        self.logger.error(f"Failed request {request_id}: {error}")
        return True
    
    async def retry_request(self, request_id: str) -> bool:
        """
        Retry a failed request.
        
        Args:
            request_id: Request identifier
            
        Returns:
            True if successful, False otherwise
        """
        if request_id not in self.failed_requests:
            self.logger.error(f"Failed request {request_id} not found")
            return False
        
        tracker = self.failed_requests[request_id]
        tracker.retry_processing()
        
        if tracker.status == "failed":
            # Max retries exceeded, keep in failed
            self.logger.warning(f"Max retries exceeded for request {request_id}")
            return False
        
        # Move back to active requests
        self.active_requests[request_id] = tracker
        del self.failed_requests[request_id]
        
        # Update statistics
        self.stats["active_requests"] += 1
        self.stats["failed_requests"] -= 1
        
        self.logger.info(f"Retrying request {request_id} (attempt {tracker.attempts})")
        return True
    
    async def get_request_status(self, request_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the status of a specific request.
        
        Args:
            request_id: Request identifier
            
        Returns:
            Request status or None if not found
        """
        # Check active requests
        if request_id in self.active_requests:
            tracker = self.active_requests[request_id]
            return {
                "status": "active",
                **tracker.to_dict()
            }
        
        # Check completed requests
        if request_id in self.completed_requests:
            tracker = self.completed_requests[request_id]
            return {
                "status": "completed",
                **tracker.to_dict(),
                "response_data": tracker.response_data
            }
        
        # Check failed requests
        if request_id in self.failed_requests:
            tracker = self.failed_requests[request_id]
            return {
                "status": "failed",
                **tracker.to_dict()
            }
        
        return None
    
    async def get_response_data(self, request_id: str) -> Optional[Dict[str, Any]]:
        """
        Get response data for a completed request.
        
        Args:
            request_id: Request identifier
            
        Returns:
            Response data or None if not found
        """
        return self.response_mapping.get(request_id)
    
    def set_completion_callback(self, request_id: str, callback: Callable[[str, Dict[str, Any]], None]):
        """
        Set a callback for when a request completes.
        
        Args:
            request_id: Request identifier
            callback: Function to call on completion
        """
        self.completion_callbacks[request_id] = callback
    
    def set_error_callback(self, request_id: str, callback: Callable[[str, str], None]):
        """
        Set a callback for when a request fails.
        
        Args:
            request_id: Request identifier
            callback: Function to call on error
        """
        self.error_callbacks[request_id] = callback
    
    async def _call_completion_callback(self, request_id: str, response_data: Dict[str, Any]):
        """Safely call completion callback."""
        if request_id in self.completion_callbacks:
            try:
                callback = self.completion_callbacks[request_id]
                callback(request_id, response_data)
            except Exception as e:
                error_msg = f"Error in completion callback for {request_id}: {e}"
                self.error_manager.log_error_with_generation("RTRMM", "UnknownClass", "UnknownFunction", error_msg)
    
    async def _call_error_callback(self, request_id: str, error: str):
        """Safely call error callback."""
        if request_id in self.error_callbacks:
            try:
                callback = self.error_callbacks[request_id]
                callback(request_id, error)
            except Exception as e:
                error_msg = f"Error in error callback for {request_id}: {e}"
                self.error_manager.log_error_with_generation("RTRMM", "UnknownClass", "UnknownFunction", error_msg)
    
    async def get_statistics(self) -> Dict[str, Any]:
        """
        Get detailed statistics about request tracking.
        
        Returns:
            Dictionary with tracking statistics
        """
        return {
            **self.stats,
            "request_counts": {
                "active": len(self.active_requests),
                "completed": len(self.completed_requests),
                "failed": len(self.failed_requests)
            },
            "response_mapping_count": len(self.response_mapping),
            "callback_counts": {
                "completion_callbacks": len(self.completion_callbacks),
                "error_callbacks": len(self.error_callbacks)
            }
        }
    
    async def get_status(self) -> Dict[str, Any]:
        """
        Get the status of the RTRMM module.
        
        Returns:
            Dictionary containing module status information
        """
        stats = await self.get_statistics()
        
        return {
            "status": "active",
            "statistics": stats,
            "cleanup_settings": {
                "interval_seconds": self.cleanup_interval,
                "retention_days": self.retention_days
            },
            "last_activity": datetime.now().isoformat()
        } 

    def log_error(self, error_message: str, class_name: str = "UnknownClass", function_name: str = "UnknownFunction", sub_function: str = "001"):
        """Log an error using EMM."""
        return self.error_manager.log_error_with_generation(
            "RTRMM", 
            class_name, 
            function_name, 
            error_message, 
            sub_function
        )

    def generate_error_code(self, class_name: str = "UnknownClass", function_name: str = "UnknownFunction", sub_function: str = "001") -> str:
        """Generate an error code using EMM."""
        return self.error_manager.generate_error_code("RTRMM", class_name, function_name, sub_function)

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
                "RTRMM",
                "RTRMM",
                "handle_api_error",
                f"API Error: {result.get('api_error_type', 'unknown')}",
                context=result
            )
            await api_error_handler.send_error_report_to_ccu(result)
            return result
        except Exception as e:
            self.error_manager.log_error_with_generation(
                "RTRMM",
                "RTRMM",
                "handle_api_error",
                f"Error handling API error: {str(e)}"
            )
            return {"success": False, "error": str(e)} 

# Global instance and alias for compatibility
rtrmm = RequestTrackingAndResponseMappingModule()
RTRMM = RequestTrackingAndResponseMappingModule  # Class alias
