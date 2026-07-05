"""
Priority-based Request Processing Module (PBRPM)

Responsible for fetching and processing request files according to their assigned priority level.
"""

import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import heapq

from EMM.emm import ErrorManagementModule
from EMM.api_error_handler import api_error_handler


class PriorityRequest:
    """Represents a request with priority information."""
    
    def __init__(self, file_path: Path, priority: str, timestamp: float):
        self.file_path = file_path
        self.priority = priority
        self.timestamp = timestamp
        self.request_id = file_path.stem
    
    def __lt__(self, other):
        """Priority comparison for heapq."""
        priority_order = {"A": 0, "B": 1, "C": 2, "D": 3}
        if self.priority != other.priority:
            return priority_order.get(self.priority, 4) < priority_order.get(other.priority, 4)
        return self.timestamp < other.timestamp


    def log_error(self, error_message: str, class_name: str = "UnknownClass", function_name: str = "UnknownFunction", sub_function: str = "001"):
        """Log an error using EMM."""
        return self.error_manager.log_error_with_generation(
            "PBRPM", 
            class_name, 
            function_name, 
            error_message, 
            sub_function
        )
    
    def generate_error_code(self, class_name: str = "UnknownClass", function_name: str = "UnknownFunction", sub_function: str = "001") -> str:
        """Generate an error code using EMM."""
        return self.error_manager.generate_error_code("PBRPM", class_name, function_name, sub_function)
    
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

class PriorityBasedRequestProcessingModule:
    """
    Priority-based Request Processing Module (PBRPM)
    
    Responsible for fetching and processing request files according to their assigned priority level.
    """
    
    def __init__(self):
        """Initialize the PBRPM module."""
        self.logger = logging.getLogger(__name__)
        self.error_manager = ErrorManagementModule()
        
        # Priority directories
        self.priority_dirs = {
            "A": Path("input/priority_a/"),
            "B": Path("input/priority_b/"),
            "C": Path("input/priority_c/"),
            "D": Path("input/priority_d/")
        }
        
        # Priority queue for processing
        self.priority_queue = []
        self.processing_queue = []
        self.completed_requests = set()
        
        # Error codes for this module (Module code: 02 for PBRPM)
        # Error codes now generated dynamically by EMM
        
        # Ensure directories exist
        self._ensure_directories()

    def _ensure_directories(self):
        """Ensure all priority directories exist."""
        for priority_dir in self.priority_dirs.values():
            priority_dir.mkdir(parents=True, exist_ok=True)

    async def handle_api_error(self, error: Exception, context: str = "unknown") -> dict:
        return api_error_handler.handle_error(error, context, "PBRPM")

    async def scan_priority_directories(self) -> List[PriorityRequest]:
        """
        Scan all priority directories for new files.
        
        Returns:
            List of PriorityRequest objects sorted by priority
        """
        requests = []
        
        for priority, directory in self.priority_dirs.items():
            if not directory.exists():
                continue
            
            for file_path in directory.glob("*.json"):
                if file_path.name not in self.completed_requests:
                    # Get file modification time
                    timestamp = file_path.stat().st_mtime
                    priority_request = PriorityRequest(file_path, priority, timestamp)
                    requests.append(priority_request)
        
        # Sort by priority (A first, then B, C, D)
        requests.sort()
        return requests
    
    async def add_to_priority_queue(self, requests: List[PriorityRequest]):
        """
        Add requests to the priority queue.
        
        Args:
            requests: List of PriorityRequest objects
        """
        for request in requests:
            if request.request_id not in [r.request_id for r in self.priority_queue]:
                heapq.heappush(self.priority_queue, request)
                self.logger.info(f"Added request {request.request_id} (Priority: {request.priority}) to queue")
    
    async def get_next_request(self) -> Optional[PriorityRequest]:
        """
        Get the next request from the priority queue.
        
        Returns:
            Next PriorityRequest or None if queue is empty
        """
        if not self.priority_queue:
            return None
        
        return heapq.heappop(self.priority_queue)
    
    async def process_request(self, request: PriorityRequest) -> bool:
        """
        Process a single request.
        
        Args:
            request: PriorityRequest to process
            
        Returns:
            True if processing successful, False otherwise
        """
        try:
            self.logger.info(f"Processing request {request.request_id} (Priority: {request.priority})")
            
            # Move to processing queue
            self.processing_queue.append(request)
            
            # Simulate processing time based on priority
            processing_times = {"A": 0.1, "B": 0.2, "C": 0.3, "D": 0.5}
            await asyncio.sleep(processing_times.get(request.priority, 0.3))
            
            # Mark as completed
            self.completed_requests.add(request.request_id)
            self.processing_queue.remove(request)
            
            self.logger.info(f"Completed processing request {request.request_id}")
            return True
            
        except Exception as e:
            error_msg = f"Error processing request {request.request_id}: {e}"
            self.error_manager.log_error_with_generation("PBRPM", "UnknownClass", "UnknownFunction", error_msg)
            return False
    
    async def process_all_pending_requests(self) -> Dict[str, int]:
        """
        Process all pending requests in priority order.
        
        Returns:
            Dictionary with processing statistics
        """
        stats = {"processed": 0, "failed": 0, "total": 0}
        
        # Scan for new requests
        new_requests = await self.scan_priority_directories()
        await self.add_to_priority_queue(new_requests)
        
        stats["total"] = len(self.priority_queue)
        
        # Process all requests in priority order
        while self.priority_queue:
            request = await self.get_next_request()
            if request:
                success = await self.process_request(request)
                if success:
                    stats["processed"] += 1
                else:
                    stats["failed"] += 1
        
        return stats
    
    async def get_queue_status(self) -> Dict[str, Any]:
        """
        Get the current status of the priority queue.
        
        Returns:
            Dictionary containing queue status information
        """
        return {
            "queue_size": len(self.priority_queue),
            "processing_count": len(self.processing_queue),
            "completed_count": len(self.completed_requests),
            "priority_breakdown": {
                priority: len([r for r in self.priority_queue if r.priority == priority])
                for priority in ["A", "B", "C", "D"]
            },
            "last_activity": datetime.now().isoformat()
        }
    
    async def get_status(self) -> Dict[str, Any]:
        """
        Get the status of the PBRPM module.
        
        Returns:
            Dictionary containing module status information
        """
        queue_status = await self.get_queue_status()
        
        return {
            "status": "active",
            "priority_directories": {
                priority: str(dir_path) for priority, dir_path in self.priority_dirs.items()
            },
            "queue_status": queue_status,
            "last_activity": datetime.now().isoformat()
        }
    
    async def start(self):
        """Start the PBRPM module."""
        self.logger.info("PBRPM module started")
    
    async def stop(self):
        """Stop the PBRPM module."""
        self.logger.info("PBRPM module stopped")

# Global instances
pbrpm = PriorityBasedRequestProcessingModule()
PBRPM = PriorityBasedRequestProcessingModule()