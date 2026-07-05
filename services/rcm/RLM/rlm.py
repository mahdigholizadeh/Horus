"""
Refined Rate Limiting Module (RLM) - Production Design

Implements sophisticated priority-based bandwidth allocation with real-time production constraints:
- Strict rate limiting: 480 requests per minute (8 RPS)
- Priority allocation: A (50% = 240), B (25% = 120), C (15% = 72), D (10% = 48)
- Separate FIFO queues per priority
- Bandwidth allocation per minute (MPM) and per second (MPS)
- Dynamic bandwidth reallocation from unused higher priorities
- Adaptive switching between MPM and MPS modes based on queue backlogs
- Thread-safe operations with proper locking
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional, List, Callable, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, deque
import threading
import heapq
import math

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from EMM.emm import ErrorManagementModule
from EMM.api_error_handler import api_error_handler


class PriorityRequest:
    """Represents a request with priority and timing information."""
    
    def __init__(self, request_id: str, priority: str, api_call: Callable, 
                 success_callback: Optional[Callable] = None, 
                 error_callback: Optional[Callable] = None,
                 metadata: Optional[Dict[str, Any]] = None):
        self.request_id = request_id
        self.priority = priority
        self.api_call = api_call
        self.success_callback = success_callback
        self.error_callback = error_callback
        self.metadata = metadata or {}
        self.timestamp = time.time()
        self.attempts = 0
        self.max_attempts = 3
        self.created_at = datetime.now()
    
    def __lt__(self, other):
        """Priority comparison for heapq."""
        priority_order = {"A": 0, "B": 1, "C": 2, "D": 3}
        if self.priority != other.priority:
            return priority_order.get(self.priority, 4) < priority_order.get(other.priority, 4)
        return self.timestamp < other.timestamp


class BandwidthTracker:
    """Tracks bandwidth usage with sliding window for both MPM and MPS modes."""
    
    def __init__(self, window_size: int = 60):
        self.window_size = window_size
        self.requests = deque()
        self.lock = threading.Lock()
    
    def add_request(self, timestamp: float = None):
        """Add a request timestamp."""
        if timestamp is None:
            timestamp = time.time()
        
        with self.lock:
            self.requests.append(timestamp)
            self._cleanup_old_requests(timestamp)
            logging.debug(f"RLM: Added request to bandwidth tracker (window: {self.window_size}s, total: {len(self.requests)})")
    
    def _cleanup_old_requests(self, current_time: float):
        """Remove requests outside the sliding window."""
        cutoff_time = current_time - self.window_size
        removed_count = 0
        while self.requests and self.requests[0] <= cutoff_time:
            self.requests.popleft()
            removed_count += 1
        if removed_count > 0:
            logging.debug(f"RLM: Cleaned up {removed_count} old requests from bandwidth tracker")
    
    def get_current_usage(self) -> int:
        """Get current usage within the window."""
        with self.lock:
            current_time = time.time()
            self._cleanup_old_requests(current_time)
            usage = len(self.requests)
            logging.debug(f"RLM: Current bandwidth usage: {usage} requests (window: {self.window_size}s)")
            return usage
    
    def get_usage_in_window(self, window_start: float, window_end: float) -> int:
        """Get usage in a specific time window."""
        with self.lock:
            count = 0
            for timestamp in self.requests:
                if window_start <= timestamp <= window_end:
                    count += 1
            return count


class PriorityQueue:
    """Thread-safe FIFO queue for a specific priority."""
    
    def __init__(self, priority: str):
        self.priority = priority
        self.queue = deque()
        self.lock = threading.Lock()
        self.stats = {
            "total_enqueued": 0,
            "total_dequeued": 0,
            "max_queue_size": 0,
            "current_wait_time": 0.0
        }
    
    def enqueue(self, request: PriorityRequest):
        """Add request to queue."""
        with self.lock:
            self.queue.append(request)
            self.stats["total_enqueued"] += 1
            self.stats["max_queue_size"] = max(self.stats["max_queue_size"], len(self.queue))
    
    def dequeue(self) -> Optional[PriorityRequest]:
        """Remove and return next request from queue."""
        with self.lock:
            if self.queue:
                request = self.queue.popleft()
                self.stats["total_dequeued"] += 1
                return request
            return None
    
    def peek(self) -> Optional[PriorityRequest]:
        """Peek at next request without removing it."""
        with self.lock:
            return self.queue[0] if self.queue else None
    
    def size(self) -> int:
        """Get current queue size."""
        with self.lock:
            return len(self.queue)
    
    def is_empty(self) -> bool:
        """Check if queue is empty."""
        with self.lock:
            return len(self.queue) == 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get queue statistics."""
        with self.lock:
            current_size = len(self.queue)
            return {
                "priority": self.priority,
                "current_size": current_size,
                "total_enqueued": self.stats["total_enqueued"],
                "total_dequeued": self.stats["total_dequeued"],
                "max_queue_size": self.stats["max_queue_size"],
                "is_empty": current_size == 0
            }


class AdaptiveBandwidthManager:
    """Manages adaptive bandwidth allocation with MPM/MPS mode switching."""
    
    def __init__(self, total_bandwidth: int = 480, time_window: int = 60, mps_to_mpm_threshold: int = 600):
        """
        Initialize bandwidth manager.
        
        Args:
            total_bandwidth: Total requests per minute (default: 480 = 8 RPS)
            time_window: Time window in seconds (default: 60)
            mps_to_mpm_threshold: Interval in seconds to check for MPS->MPM reversion (default: 600)
        """
        self.total_bandwidth = total_bandwidth
        self.time_window = time_window
        self.rps_limit = total_bandwidth / time_window  # 8 RPS
        
        # Priority allocations (percentages) - Updated per requirements
        self.priority_allocations = {
            "A": 0.50,  # 50% = 240 requests per minute
            "B": 0.25,  # 25% = 120 requests per minute
            "C": 0.15,  # 15% = 72 requests per minute
            "D": 0.10   # 10% = 48 requests per minute
        }
        
        # Priority queues
        self.priority_queues = {
            "A": PriorityQueue("A"),
            "B": PriorityQueue("B"),
            "C": PriorityQueue("C"),
            "D": PriorityQueue("D")
        }
        
        # Bandwidth trackers for MPM and MPS modes
        self.mpm_tracker = BandwidthTracker(60)  # Per minute
        self.mps_tracker = BandwidthTracker(1)   # Per second
        
        # Mode switching thresholds and timing
        self.mpm_to_mps_threshold = 8  # (TRQC + TRQD) > 8 * (TRQA + TRQB)
        self.mps_to_mpm_threshold = mps_to_mpm_threshold
        self.last_mode_check = time.time()
        
        # Current mode (True = MPS, False = MPM)
        self.current_mode = False  # Start in MPM mode
        self.mode_switch_pending = False
        self.mode_switch_time = None
        
        # Lock for thread safety
        self.lock = threading.Lock()
        
        # Statistics
        self.stats = {
            "total_requests": 0,
            "processed_requests": 0,
            "queued_requests": 0,
            "bandwidth_utilization": 0.0,
            "mode_switches": 0,
            "current_mode": "MPM",
            "last_mode_switch": None
        }
    
    def _get_priority_bandwidth_mpm(self, priority: str) -> int:
        """Get allocated bandwidth for a priority in MPM mode."""
        return int(self.total_bandwidth * self.priority_allocations[priority])
    
    def _get_priority_bandwidth_mps(self, priority: str) -> float:
        """Get allocated bandwidth for a priority in MPS mode (requests per second)."""
        return self.rps_limit * self.priority_allocations[priority]
    
    def _calculate_dynamic_bandwidth_mpm(self, priority: str) -> int:
        """Calculate dynamic bandwidth including reallocation from unused higher priorities."""
        allocated = self._get_priority_bandwidth_mpm(priority)
        used = self.mpm_tracker.get_current_usage()
        
        # Calculate priority-specific usage (simplified proportional approach)
        priority_usage = int(used * self.priority_allocations[priority])
        
        # Start with allocated bandwidth
        available = allocated - priority_usage
        
        # Calculate total unused bandwidth from all higher priorities
        total_unused_from_higher = 0
        for higher_priority in ["A", "B", "C", "D"]:
            if higher_priority == priority:
                break
                
            higher_allocated = self._get_priority_bandwidth_mpm(higher_priority)
            higher_usage = int(used * self.priority_allocations[higher_priority])
            higher_unused = max(0, higher_allocated - higher_usage)
            total_unused_from_higher += higher_unused
        
        # Add unused bandwidth from higher priorities
        available += total_unused_from_higher
        
        return max(0, available)
    
    def _calculate_dynamic_bandwidth_mps(self, priority: str) -> float:
        """Calculate dynamic bandwidth including reallocation from unused higher priorities in MPS mode."""
        allocated = self._get_priority_bandwidth_mps(priority)
        used = self.mps_tracker.get_current_usage()
        
        # Calculate priority-specific usage
        priority_usage = used * self.priority_allocations[priority]
        available = allocated - priority_usage
        
        # Add unused bandwidth from higher priorities
        total_unused_from_higher = 0
        for higher_priority in ["A", "B", "C", "D"]:
            if higher_priority == priority:
                break
                
            higher_allocated = self._get_priority_bandwidth_mps(higher_priority)
            higher_usage = used * self.priority_allocations[higher_priority]
            higher_unused = max(0, higher_allocated - higher_usage)
            total_unused_from_higher += higher_unused
        
        available += total_unused_from_higher
        
        return max(0, available)
    
    def _should_switch_to_mps(self) -> bool:
        """Check if we should switch to MPS mode based on queue backlogs."""
        trqa = self.priority_queues["A"].size()
        trqb = self.priority_queues["B"].size()
        trqc = self.priority_queues["C"].size()
        trqd = self.priority_queues["D"].size()
        
        # Formula: (TRQC + TRQD) > 8 * (TRQA + TRQB)
        return (trqc + trqd) > 8 * (trqa + trqb)
    
    def _should_switch_to_mpm(self) -> bool:
        """Check if we should switch back to MPM mode."""
        # Check more frequently (every 30 seconds instead of 600)
        current_time = time.time()
        if current_time - self.last_mode_check >= 30:  # Check every 30 seconds
            self.last_mode_check = current_time
            
            # Get current queue sizes
            trqa = self.priority_queues["A"].size()
            trqb = self.priority_queues["B"].size()
            trqc = self.priority_queues["C"].size()
            trqd = self.priority_queues["D"].size()
            
            # Check if the MPS condition is no longer met
            should_stay_mps = (trqc + trqd) > 8 * (trqa + trqb)
            
            logging.info(f"RLM: MPS reversion check - Queue sizes: A:{trqa} B:{trqb} C:{trqc} D:{trqd}, "
                        f"Condition: ({trqc}+{trqd}) > 8*({trqa}+{trqb}) = {trqc+trqd} > {8*(trqa+trqb)} = {should_stay_mps}")
            
            return not should_stay_mps
        return False
    
    def _switch_mode(self, new_mode: bool):
        """Switch between MPM and MPS modes with graceful transition."""
        if new_mode != self.current_mode:
            old_mode = "MPS" if self.current_mode else "MPM"
            self.current_mode = new_mode
            self.stats["mode_switches"] += 1
            self.stats["current_mode"] = "MPS" if new_mode else "MPM"
            self.stats["last_mode_switch"] = datetime.now()
            logging.info(f"RLM: Switched from {old_mode} to {'MPS' if new_mode else 'MPM'} mode (switch #{self.stats['mode_switches']})")
    
    def can_process_request(self, priority: str) -> bool:
        """
        Check if a request can be processed immediately.
        
        Args:
            priority: Request priority (A, B, C, D)
            
        Returns:
            True if request can be processed, False if it should be queued
        """
        with self.lock:
            # Check if we should switch modes
            if not self.current_mode and self._should_switch_to_mps():
                logging.info(f"RLM: Queue backlog detected, switching to MPS mode")
                self._switch_mode(True)
            elif self.current_mode and self._should_switch_to_mpm():
                logging.info(f"RLM: Queue backlog cleared, switching to MPM mode")
                self._switch_mode(False)
            
            if self.current_mode:  # MPS mode
                available = self._calculate_dynamic_bandwidth_mps(priority)
                logging.debug(f"RLM: MPS mode - Priority {priority} available bandwidth: {available:.2f}")
                return available > 0
            else:  # MPM mode
                available = self._calculate_dynamic_bandwidth_mpm(priority)
                logging.debug(f"RLM: MPM mode - Priority {priority} available bandwidth: {available}")
                return available > 0
    
    def add_request(self, priority: str):
        """Add a request to the bandwidth tracker."""
        timestamp = time.time()
        self.mpm_tracker.add_request(timestamp)
        self.mps_tracker.add_request(timestamp)
        self.stats["total_requests"] += 1
    
    def add_to_queue(self, request: PriorityRequest):
        """Add a request to the appropriate priority queue."""
        self.priority_queues[request.priority].enqueue(request)
        self.stats["queued_requests"] += 1
    
    def get_next_request(self) -> Optional[PriorityRequest]:
        """Get the next request to process based on priority and availability."""
        with self.lock:
            # Check each priority in order
            for priority in ["A", "B", "C", "D"]:
                if not self.priority_queues[priority].is_empty():
                    if self.current_mode:  # MPS mode
                        available_bw = self._calculate_dynamic_bandwidth_mps(priority)
                        if available_bw > 0:
                            request = self.priority_queues[priority].dequeue()
                            self.stats["queued_requests"] -= 1
                            logging.debug(f"RLM: Dequeued {request.request_id} (Priority: {priority}) - MPS mode, available BW: {available_bw:.2f}")
                            return request
                        else:
                            logging.debug(f"RLM: Insufficient MPS bandwidth for priority {priority}: {available_bw:.2f}")
                    else:  # MPM mode
                        available_bw = self._calculate_dynamic_bandwidth_mpm(priority)
                        if available_bw > 0:
                            request = self.priority_queues[priority].dequeue()
                            self.stats["queued_requests"] -= 1
                            logging.debug(f"RLM: Dequeued {request.request_id} (Priority: {priority}) - MPM mode, available BW: {available_bw}")
                            return request
                        else:
                            logging.debug(f"RLM: Insufficient MPM bandwidth for priority {priority}: {available_bw}")
            
            return None
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get status of all priority queues and bandwidth usage."""
        with self.lock:
            status = {
                "total_bandwidth": self.total_bandwidth,
                "rps_limit": self.rps_limit,
                "time_window": self.time_window,
                "priority_allocations": self.priority_allocations,
                "current_mode": self.stats["current_mode"],
                "mode_switches": self.stats["mode_switches"],
                "last_mode_switch": self.stats["last_mode_switch"],
                "queue_sizes": {},
                "bandwidth_usage": {},
                "available_bandwidth": {},
                "queue_stats": {}
            }
            
            for priority in ["A", "B", "C", "D"]:
                status["queue_sizes"][priority] = self.priority_queues[priority].size()
                status["queue_stats"][priority] = self.priority_queues[priority].get_stats()
                
                if self.current_mode:  # MPS mode
                    status["bandwidth_usage"][priority] = self.mps_tracker.get_current_usage() * self.priority_allocations[priority]
                    status["available_bandwidth"][priority] = self._calculate_dynamic_bandwidth_mps(priority)
                else:  # MPM mode
                    status["bandwidth_usage"][priority] = self.mpm_tracker.get_current_usage() * self.priority_allocations[priority]
                    status["available_bandwidth"][priority] = self._calculate_dynamic_bandwidth_mpm(priority)
            
            return status


class RetryManager:
    """Manages retry logic for failed requests."""
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 60.0):
        """
        Initialize retry manager.
        
        Args:
            max_retries: Maximum number of retry attempts
            base_delay: Base delay between retries in seconds
            max_delay: Maximum delay between retries in seconds
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.retry_counts = defaultdict(int)
        self.retry_timestamps = defaultdict(list)
        self.lock = threading.Lock()
        
        # Error patterns for intelligent retry decisions
        self.retryable_errors = {
            "rate_limit_exceeded": True,
            "timeout": True,
            "connection_error": True,
            "server_error": True,
            "temporary_unavailable": True,
            "quota_exceeded": True
        }
        
        self.non_retryable_errors = {
            "authentication_error": False,
            "authorization_error": False,
            "invalid_request": False,
            "not_found": False,
            "permission_denied": False
        }
    
    def should_retry(self, request_id: str, error: str) -> bool:
        """
        Determine if a request should be retried based on error type and retry count.
        
        Args:
            request_id: Unique identifier for the request
            error: Error message or type
            
        Returns:
            True if request should be retried, False otherwise
        """
        with self.lock:
            # Check if we've exceeded max retries
            if self.retry_counts[request_id] >= self.max_retries:
                return False
            
            # Check if error is retryable
            error_lower = error.lower()
            
            # Check non-retryable errors first
            for non_retryable in self.non_retryable_errors:
                if non_retryable in error_lower:
                    return False
            
            # Check retryable errors
            for retryable in self.retryable_errors:
                if retryable in error_lower:
                    return True
            
            # Default to retryable for unknown errors
            return True
    
    def get_retry_delay(self, request_id: str) -> float:
        """
        Calculate delay before next retry using exponential backoff.
        
        Args:
            request_id: Unique identifier for the request
            
        Returns:
            Delay in seconds before next retry
        """
        with self.lock:
            retry_count = self.retry_counts[request_id]
            delay = self.base_delay * (2 ** retry_count)  # Exponential backoff
            delay = min(delay, self.max_delay)  # Cap at max delay
            
            # Add jitter to prevent thundering herd
            jitter = delay * 0.1 * (hash(request_id) % 100) / 100
            return delay + jitter
    
    def increment_retry_count(self, request_id: str):
        """Increment retry count for a request."""
        with self.lock:
            self.retry_counts[request_id] += 1
            self.retry_timestamps[request_id].append(time.time())
    
    def reset_retry_count(self, request_id: str):
        """Reset retry count for a request."""
        with self.lock:
            self.retry_counts[request_id] = 0
            self.retry_timestamps[request_id] = []
    
    def get_status(self) -> Dict[str, Any]:
        """Get retry manager status."""
        with self.lock:
            return {
                "max_retries": self.max_retries,
                "base_delay": self.base_delay,
                "max_delay": self.max_delay,
                "active_retries": len(self.retry_counts),
                "retry_counts": dict(self.retry_counts)
            }


class RateLimitingModule:
    """Main rate limiting module with priority-based queue management."""
    
    def __init__(self, total_bandwidth: int = 480, time_window: int = 60, mps_to_mpm_threshold: int = 600):
        """Initialize the rate limiting module."""
        self.logger = logging.getLogger(__name__)
        self.error_manager = ErrorManagementModule()
        
        # Bandwidth management
        self.bandwidth_manager = AdaptiveBandwidthManager(total_bandwidth, time_window, mps_to_mpm_threshold)
        
        # Retry management
        self.retry_manager = RetryManager()
        
        # Processing state
        self.is_running = False
        self._stop_event = asyncio.Event()
        self._processing_task = None
        
        # Statistics
        self.stats = {
            "total_submitted": 0,
            "total_processed": 0,
            "total_successful": 0,
            "total_failed": 0,
            "total_retried": 0,
            "average_processing_time": 0.0,
            "start_time": None
        }
        
        # Logging
        self.logger.setLevel(logging.DEBUG)

    async def handle_api_error(self, error: Exception, context: str = "unknown") -> dict:
        # Log the error using EMM
        self.log_error_with_generation("RLM", "RateLimitingModule", "handle_api_error", str(error))
        return api_error_handler.handle_error(error, context, "RLM")

    def log_error_with_generation(self, module_name: str, class_name: str, function_name: str, error_message: str, error_code: str = None):
        """Log error with dynamic code generation using EMM."""
        if hasattr(self, 'error_manager'):
            self.error_manager.log_error_with_generation(module_name, class_name, function_name, error_message, error_code)
        else:
            self.logger.error(f"Error in {module_name}.{class_name}.{function_name}: {error_message}")

# Global instances
rlm = RateLimitingModule()
RLM = RateLimitingModule()

# Example usage and testing
if __name__ == "__main__":
    import asyncio
    import uuid
    
    async def test_api_call(request_id: str, priority: str):
        """Test API call that simulates processing time."""
        await asyncio.sleep(0.1)  # Simulate API call
        return f"Success: {request_id} (Priority: {priority})"
    
    async def success_callback(result, request):
        print(f"✅ Success: {result}")
    
    async def error_callback(error, request):
        print(f"❌ Error: {error}")
    
    async def test_rlm():
        """Test the rate limiting module."""
        rlm = RateLimitingModule(total_bandwidth=480, time_window=60)
        await rlm.start()
        
        # Submit test requests
        for i in range(100):
            request_id = str(uuid.uuid4())
            priority = ["A", "B", "C", "D"][i % 4]
            
            await rlm.make_rate_limited_request(
                request_id=request_id,
                priority=priority,
                api_call=lambda: test_api_call(request_id, priority),
                success_callback=success_callback,
                error_callback=error_callback
            )
        
        # Wait for processing
        await asyncio.sleep(10)
        
        # Get status
        status = await rlm.get_status()
        print(f"\n📊 Final Status:")
        print(f"Total Submitted: {status['module_stats']['total_submitted']}")
        print(f"Total Processed: {status['module_stats']['total_processed']}")
        print(f"Total Successful: {status['module_stats']['total_successful']}")
        print(f"Total Failed: {status['module_stats']['total_failed']}")
        print(f"Current Mode: {status['bandwidth_status']['current_mode']}")
        
        await rlm.stop()
    
    # Run the test
    asyncio.run(test_rlm())