"""
Request Management Module (RMM) for OCM

This is the most critical module in OCM that orchestrates the complete lifecycle of an outgoing request.
It manages the workflow from when a request enters OCM until it is successfully dispatched to the web server,
coordinating actions of all other modules. Based on IFCM from RCM but adapted for output-oriented workflow.
"""

import asyncio
import logging
import json
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import uuid
import hashlib
from pathlib import Path
import queue

class RequestStatus(Enum):
    """Request processing status."""
    RECEIVED = "received"
    VALIDATING = "validating" 
    QUEUED = "queued"
    PROCESSING = "processing"
    REPORT_GENERATING = "report_generating"
    REPORT_VALIDATING = "report_validating"
    READY_TO_SEND = "ready_to_send"
    SENDING = "sending"
    AWAITING_ACKNOWLEDGMENT = "awaiting_acknowledgment"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRY = "retry"

class RequestPriority(Enum):
    """Request priority levels."""
    A = "A"  # Highest priority - 40% bandwidth
    B = "B"  # High priority - 30% bandwidth
    C = "C"  # Medium priority - 20% bandwidth
    D = "D"  # Low priority - 10% bandwidth

class RequestType(Enum):
    """Types of requests processed by OCM."""
    API_RESPONSE = "api_response"      # Direct API response from RCM
    TD_REPORT = "td_report"           # Report from TD microservice
    SYSTEM_NOTIFICATION = "system_notification"

@dataclass
class RequestInfo:
    """Information about a request being processed."""
    request_id: str
    request_type: RequestType
    priority: RequestPriority
    status: RequestStatus
    source_module: str  # RCMIM, TDIM, etc.
    
    # Timing information
    received_at: datetime
    queued_at: Optional[datetime] = None
    processing_started: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    
    # Content information
    content_type: str = ""  # JSON, HTML, PDF, etc.
    content_size: int = 0
    content_hash: str = ""
    
    # Delivery information
    destination: str = ""
    delivery_attempts: int = 0
    max_delivery_attempts: int = 3
    last_error: str = ""
    
    # Report information (for TD reports)
    report_format: List[str] = None  # ["HTML", "PDF"]
    template_used: str = ""
    
    # Metadata
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.report_format is None:
            self.report_format = []
        if self.metadata is None:
            self.metadata = {}

class RequestManagementModule:
    """
    Request Management Module (RMM)
    
    Orchestrates the complete lifecycle of outgoing requests:
    - Receives requests from RCMIM and TDIM
    - Manages priority queues (A, B, C, D)
    - Coordinates with all other modules
    - Tracks delivery status and acknowledgments
    - Implements retry logic and error handling
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the RMM module."""
        self.logger = logging.getLogger(__name__)
        self.module_name = "RMM"
        self.is_active = False
        
        # Configuration
        self.config = config
        self.priority_config = config.get('priority_management', {})
        self.ack_config = config.get('acknowledgment_protocol', {})
        
        # Priority queues
        self.priority_queues = {
            RequestPriority.A: asyncio.Queue(),
            RequestPriority.B: asyncio.Queue(),
            RequestPriority.C: asyncio.Queue(),
            RequestPriority.D: asyncio.Queue()
        }
        
        # Request tracking
        self.active_requests = {}  # request_id -> RequestInfo
        self.completed_requests = {}  # request_id -> RequestInfo (last 1000)
        self.max_completed_history = 1000
        
        # Processing tasks
        self.processing_tasks = []
        self.processing_enabled = True
        
        # Statistics
        self.stats = {
            'requests_received': 0,
            'requests_processed': 0,
            'requests_delivered': 0,
            'requests_failed': 0,
            'reports_generated': 0,
            'average_processing_time': 0.0,
            'queue_sizes': {'A': 0, 'B': 0, 'C': 0, 'D': 0},
            'delivery_success_rate': 100.0,
            'total_requests_processed': 0,
            'successful_deliveries': 0,
            'failed_deliveries': 0,
            'last_activity': None,
            'processing_times': [],
            'error_count': 0,
            'retry_count': 0
        }
        
        # Module references (injected by main service)
        self.modules = {}
        
        self.logger.info(f"{self.module_name} initialized with priority levels: {list(self.priority_queues.keys())}")
    
    def set_module_references(self, modules: Dict[str, Any]):
        """Set references to other modules."""
        self.modules = modules
    
    async def start(self):
        """Start the RMM module."""
        try:
            self.is_active = True
            self.processing_enabled = True
            
            # Start priority queue processors
            await self._start_priority_processors()
            
            # Start request lifecycle monitor
            asyncio.create_task(self._request_lifecycle_monitor())
            
            # Start delivery acknowledgment monitor
            asyncio.create_task(self._acknowledgment_monitor())
            
            # Start statistics updater
            asyncio.create_task(self._update_statistics())
            
            self.logger.info("RMM started successfully - request processing enabled")
            
        except Exception as e:
            self.logger.error(f"Failed to start RMM: {e}")
            raise
    
    async def stop(self):
        """Stop the RMM module gracefully."""
        try:
            self.is_active = False
            self.processing_enabled = False
            
            # Cancel all processing tasks
            for task in self.processing_tasks:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            
            self.logger.info("RMM stopped successfully")
            
        except Exception as e:
            self.logger.error(f"Error stopping RMM: {e}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        # Check if module is active and processing is enabled
        is_healthy = (
            self.is_active and
            self.processing_enabled and
            len(self.processing_tasks) > 0
        )
        
        # Check queue health
        total_queue_size = sum(self.stats['queue_sizes'].values())
        queue_health = "healthy" if total_queue_size < 100 else "warning" if total_queue_size < 500 else "critical"
        
        # Check processing health
        active_processors = len([task for task in self.processing_tasks if not task.done()])
        processing_health = "healthy" if active_processors > 0 else "critical"
        
        return {
            'healthy': is_healthy,
            'active': self.is_active,
            'module': 'rmm',
            'queue_health': queue_health,
            'processing_health': processing_health,
            'total_queue_size': total_queue_size,
            'active_processors': active_processors,
            'active_requests': len(self.active_requests),
            'completed_requests': len(self.completed_requests)
        }
    
    async def _start_priority_processors(self):
        """Start processors for each priority queue."""
        # Bandwidth allocation based on priority
        bandwidth_allocation = self.priority_config.get('bandwidth_allocation', {
            'A': 40, 'B': 30, 'C': 20, 'D': 10
        })
        
        for priority in RequestPriority:
            allocation = bandwidth_allocation.get(priority.value, 10)
            # Create multiple processors based on bandwidth allocation
            processor_count = max(1, allocation // 10)  # At least 1 processor per priority
            
            for i in range(processor_count):
                task = asyncio.create_task(
                    self._priority_queue_processor(priority, f"processor_{i}")
                )
                self.processing_tasks.append(task)
        
        self.logger.info(f"Started {len(self.processing_tasks)} priority queue processors")
    
    async def _priority_queue_processor(self, priority: RequestPriority, processor_id: str):
        """Process requests from a specific priority queue."""
        queue = self.priority_queues[priority]
        
        while self.is_active and self.processing_enabled:
            try:
                # Wait for a request with timeout
                request_info = await asyncio.wait_for(queue.get(), timeout=1.0)
                
                # Process the request
                await self._process_request(request_info, processor_id)
                
                # Mark queue task as done
                queue.task_done()
                
            except asyncio.TimeoutError:
                # No request available, continue
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in priority processor {priority.value}:{processor_id}: {e}")
                await asyncio.sleep(1)
    
    async def _process_request(self, request_info: RequestInfo, processor_id: str):
        """Process a single request through its lifecycle."""
        try:
            self.logger.info(f"Processing request {request_info.request_id} (Priority: {request_info.priority.value}, Processor: {processor_id})")
            
            request_info.status = RequestStatus.PROCESSING
            request_info.processing_started = datetime.now()
            
            # Process based on request type
            if request_info.request_type == RequestType.API_RESPONSE:
                await self._process_api_response(request_info)
            elif request_info.request_type == RequestType.TD_REPORT:
                await self._process_td_report(request_info)
            elif request_info.request_type == RequestType.SYSTEM_NOTIFICATION:
                await self._process_system_notification(request_info)
            
            # Update statistics
            self.stats['requests_processed'] += 1
            
        except Exception as e:
            request_info.status = RequestStatus.FAILED
            request_info.last_error = str(e)
            self.stats['requests_failed'] += 1
            self.logger.error(f"Failed to process request {request_info.request_id}: {e}")
            
            # Send error report to CCU
            if 'ECM' in self.modules:
                await self.modules['ECM'].send_error_report({
                    'request_id': request_info.request_id,
                    'error': str(e),
                    'module': 'RMM'
                })
    
    async def _process_api_response(self, request_info: RequestInfo):
        """Process API response from RCM."""
        try:
            # For API responses, we mainly need validation and sending
            request_info.status = RequestStatus.VALIDATING
            
            # Validate output if OCVM is available
            if 'OCVM' in self.modules:
                validation_result = await self.modules['OCVM'].validate_api_response(request_info)
                if not validation_result:
                    raise ValueError("API response validation failed")
            
            request_info.status = RequestStatus.READY_TO_SEND
            
            # Send the response
            await self._send_request(request_info)
            
        except Exception as e:
            self.logger.error(f"Error processing API response {request_info.request_id}: {e}")
            raise
    
    async def _process_td_report(self, request_info: RequestInfo):
        """Process TD report for generation and delivery."""
        try:
            request_info.status = RequestStatus.REPORT_GENERATING
            
            # Generate HTML report if HRPM is available
            if 'HRPM' in self.modules and "HTML" in request_info.report_format:
                html_content = await self.modules['HRPM'].generate_report(request_info)
                request_info.metadata['html_content'] = html_content
            
            # Generate PDF report if PRFPM is available
            if 'PRFPM' in self.modules and "PDF" in request_info.report_format:
                pdf_content = await self.modules['PRFPM'].generate_pdf_report(request_info)
                request_info.metadata['pdf_content'] = pdf_content
            
            request_info.status = RequestStatus.REPORT_VALIDATING
            
            # Validate generated reports if OCVM is available
            if 'OCVM' in self.modules:
                validation_result = await self.modules['OCVM'].validate_report(request_info)
                if not validation_result:
                    raise ValueError("Report validation failed")
            
            request_info.status = RequestStatus.READY_TO_SEND
            self.stats['reports_generated'] += 1
            
            # Send the report
            await self._send_request(request_info)
            
        except Exception as e:
            self.logger.error(f"Error processing TD report {request_info.request_id}: {e}")
            raise
    
    async def _process_system_notification(self, request_info: RequestInfo):
        """Process system notification."""
        try:
            # System notifications are typically simple and don't require complex processing
            request_info.status = RequestStatus.READY_TO_SEND
            await self._send_request(request_info)
            
        except Exception as e:
            self.logger.error(f"Error processing system notification {request_info.request_id}: {e}")
            raise
    
    async def _send_request(self, request_info: RequestInfo):
        """Send request using Data Sender Module."""
        try:
            request_info.status = RequestStatus.SENDING
            
            if 'DSM' not in self.modules:
                raise ValueError("Data Sender Module not available")
            
            # Send the request
            delivery_result = await self.modules['DSM'].send_data(request_info)
            
            if delivery_result.get('success', False):
                request_info.status = RequestStatus.AWAITING_ACKNOWLEDGMENT
                request_info.sent_at = datetime.now()
                request_info.delivery_attempts += 1
                
                # Start acknowledgment wait
                asyncio.create_task(self._wait_for_acknowledgment(request_info))
            else:
                raise ValueError(f"Failed to send request: {delivery_result.get('error', 'Unknown error')}")
                
        except Exception as e:
            self.logger.error(f"Error sending request {request_info.request_id}: {e}")
            
            # Check if retry is possible
            if request_info.delivery_attempts < request_info.max_delivery_attempts:
                request_info.status = RequestStatus.RETRY
                # Requeue for retry after delay
                asyncio.create_task(self._retry_request(request_info))
            else:
                request_info.status = RequestStatus.FAILED
                request_info.last_error = str(e)
    
    async def _wait_for_acknowledgment(self, request_info: RequestInfo):
        """Wait for delivery acknowledgment with timeout."""
        try:
            timeout = self.ack_config.get('timeout_seconds', 30)
            
            # Wait for acknowledgment
            await asyncio.sleep(timeout)
            
            # Check if acknowledgment was received
            if request_info.status == RequestStatus.AWAITING_ACKNOWLEDGMENT:
                # No acknowledgment received within timeout
                if request_info.delivery_attempts < request_info.max_delivery_attempts:
                    request_info.status = RequestStatus.RETRY
                    await self._retry_request(request_info)
                else:
                    request_info.status = RequestStatus.FAILED
                    request_info.last_error = "Acknowledgment timeout"
                    self.stats['requests_failed'] += 1
            
        except Exception as e:
            self.logger.error(f"Error waiting for acknowledgment {request_info.request_id}: {e}")
    
    async def _retry_request(self, request_info: RequestInfo):
        """Retry a failed request after delay."""
        try:
            retry_delay = 5 * request_info.delivery_attempts  # Exponential backoff
            await asyncio.sleep(retry_delay)
            
            # Re-queue the request for processing
            priority_queue = self.priority_queues[request_info.priority]
            await priority_queue.put(request_info)
            
            self.logger.info(f"Retrying request {request_info.request_id} (attempt {request_info.delivery_attempts + 1})")
            
        except Exception as e:
            self.logger.error(f"Error retrying request {request_info.request_id}: {e}")
    
    async def _request_lifecycle_monitor(self):
        """Monitor request lifecycle and cleanup old requests."""
        while self.is_active:
            try:
                current_time = datetime.now()
                
                # Check for stuck requests
                for request_id, request_info in list(self.active_requests.items()):
                    # Check if request is stuck (processing for too long)
                    if request_info.processing_started:
                        processing_time = current_time - request_info.processing_started
                        if processing_time > timedelta(minutes=10):  # 10 minutes timeout
                            self.logger.warning(f"Request {request_id} stuck in processing, marking as failed")
                            request_info.status = RequestStatus.FAILED
                            request_info.last_error = "Processing timeout"
                            await self._move_to_completed(request_info)
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                self.logger.error(f"Error in request lifecycle monitor: {e}")
                await asyncio.sleep(60)
    
    async def _acknowledgment_monitor(self):
        """Monitor and process delivery acknowledgments."""
        while self.is_active:
            try:
                # This would typically process acknowledgments from the web server
                # For now, we'll simulate some acknowledgments
                await asyncio.sleep(10)
                
            except Exception as e:
                self.logger.error(f"Error in acknowledgment monitor: {e}")
                await asyncio.sleep(10)
    
    async def _update_statistics(self):
        """Update module statistics."""
        while self.is_active:
            try:
                # Update queue sizes
                for priority in RequestPriority:
                    self.stats['queue_sizes'][priority.value] = self.priority_queues[priority].qsize()
                
                # Update total requests processed
                self.stats['total_requests_processed'] = self.stats['requests_processed']
                
                # Update successful and failed deliveries
                self.stats['successful_deliveries'] = self.stats['requests_delivered']
                self.stats['failed_deliveries'] = self.stats['requests_failed']
                
                # Calculate delivery success rate
                total_requests = self.stats['requests_delivered'] + self.stats['requests_failed']
                if total_requests > 0:
                    self.stats['delivery_success_rate'] = (self.stats['requests_delivered'] / total_requests) * 100
                
                # Calculate average processing time
                if self.stats['processing_times']:
                    self.stats['average_processing_time'] = sum(self.stats['processing_times']) / len(self.stats['processing_times'])
                
                # Update last activity
                self.stats['last_activity'] = datetime.now().isoformat()
                
                await asyncio.sleep(30)  # Update every 30 seconds
                
            except Exception as e:
                self.logger.error(f"Error updating statistics: {e}")
                await asyncio.sleep(30)
    
    # Public API methods
    
    async def submit_request(self, request_data: Dict[str, Any]) -> str:
        """Submit a new request for processing."""
        try:
            # Create request info
            request_info = RequestInfo(
                request_id=request_data.get('request_id', str(uuid.uuid4())),
                request_type=RequestType(request_data.get('request_type', 'api_response')),
                priority=RequestPriority(request_data.get('priority', 'C')),
                status=RequestStatus.RECEIVED,
                source_module=request_data.get('source_module', 'Unknown'),
                received_at=datetime.now(),
                content_type=request_data.get('content_type', ''),
                content_size=request_data.get('content_size', 0),
                content_hash=request_data.get('content_hash', ''),
                destination=request_data.get('destination', ''),
                max_delivery_attempts=request_data.get('max_delivery_attempts', 3),
                metadata=request_data.get('metadata', {})
            )
            
            # Add to active requests
            self.active_requests[request_info.request_id] = request_info
            
            # Queue for processing
            request_info.status = RequestStatus.QUEUED
            request_info.queued_at = datetime.now()
            
            priority_queue = self.priority_queues[request_info.priority]
            await priority_queue.put(request_info)
            
            self.stats['requests_received'] += 1
            self.stats['last_activity'] = datetime.now().isoformat()
            
            self.logger.info(f"Request {request_info.request_id} submitted with priority {request_info.priority.value}")
            
            return request_info.request_id
            
        except Exception as e:
            self.logger.error(f"Error submitting request: {e}")
            raise
    
    async def get_request_status(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific request."""
        request_info = self.active_requests.get(request_id) or self.completed_requests.get(request_id)
        
        if request_info:
            return asdict(request_info)
        return None
    
    async def process_acknowledgment(self, request_id: str, ack_data: Dict[str, Any]):
        """Process delivery acknowledgment."""
        try:
            request_info = self.active_requests.get(request_id)
            
            if not request_info:
                self.logger.warning(f"Acknowledgment received for unknown request: {request_id}")
                return
            
            if request_info.status == RequestStatus.AWAITING_ACKNOWLEDGMENT:
                # Validate acknowledgment
                if self.ack_config.get('checksum_validation', True):
                    expected_checksum = request_info.content_hash
                    received_checksum = ack_data.get('checksum', '')
                    
                    if expected_checksum != received_checksum:
                        self.logger.error(f"Checksum mismatch for request {request_id}")
                        request_info.status = RequestStatus.FAILED
                        request_info.last_error = "Checksum validation failed"
                        return
                
                # Mark as delivered
                request_info.status = RequestStatus.DELIVERED
                request_info.delivered_at = datetime.now()
                self.stats['requests_delivered'] += 1
                self.stats['last_activity'] = datetime.now().isoformat()
                
                # Calculate and track processing time
                if request_info.received_at and request_info.delivered_at:
                    processing_time = (request_info.delivered_at - request_info.received_at).total_seconds()
                    self.stats['processing_times'].append(processing_time)
                    # Keep only last 100 processing times to avoid memory issues
                    if len(self.stats['processing_times']) > 100:
                        self.stats['processing_times'] = self.stats['processing_times'][-100:]
                
                # Move to completed requests
                await self._move_to_completed(request_info)
                
                # Notify CCU
                if 'ECM' in self.modules:
                    await self.modules['ECM'].send_report_delivered(request_id, {
                        'delivery_time': request_info.delivered_at.isoformat(),
                        'delivery_attempts': request_info.delivery_attempts
                    })
                
                self.logger.info(f"Request {request_id} delivered successfully")
            
        except Exception as e:
            self.logger.error(f"Error processing acknowledgment for {request_id}: {e}")
    
    async def _move_to_completed(self, request_info: RequestInfo):
        """Move request from active to completed."""
        try:
            # Remove from active requests
            if request_info.request_id in self.active_requests:
                del self.active_requests[request_info.request_id]
            
            # Add to completed requests
            self.completed_requests[request_info.request_id] = request_info
            
            # Maintain history limit
            if len(self.completed_requests) > self.max_completed_history:
                # Remove oldest entries
                oldest_requests = sorted(
                    self.completed_requests.items(),
                    key=lambda x: x[1].received_at
                )
                
                for request_id, _ in oldest_requests[:len(self.completed_requests) - self.max_completed_history]:
                    del self.completed_requests[request_id]
            
        except Exception as e:
            self.logger.error(f"Error moving request to completed: {e}")
    
    def get_queue_stats(self) -> Dict[str, int]:
        """Get current queue statistics."""
        return {
            priority.value: queue.qsize()
            for priority, queue in self.priority_queues.items()
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Get current RMM status."""
        return {
            'module': self.module_name,
            'active': self.is_active,
            'processing_enabled': self.processing_enabled,
            'active_requests': len(self.active_requests),
            'completed_requests': len(self.completed_requests),
            'processing_tasks': len([task for task in self.processing_tasks if not task.done()]),
            'queue_stats': self.get_queue_stats(),
            'stats': self.stats.copy()
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive statistics for the RMM module."""
        return {
            'requests_received': self.stats['requests_received'],
            'requests_processed': self.stats['requests_processed'],
            'requests_delivered': self.stats['requests_delivered'],
            'requests_failed': self.stats['requests_failed'],
            'total_requests_processed': self.stats['total_requests_processed'],
            'reports_generated': self.stats['reports_generated'],
            'successful_deliveries': self.stats['successful_deliveries'],
            'failed_deliveries': self.stats['failed_deliveries'],
            'average_processing_time': self.stats['average_processing_time'],
            'queue_sizes': self.stats['queue_sizes'],
            'delivery_success_rate': self.stats['delivery_success_rate'],
            'active_requests': len(self.active_requests),
            'completed_requests': len(self.completed_requests),
            'last_activity': self.stats['last_activity'],
            'error_count': self.stats['error_count'],
            'retry_count': self.stats['retry_count']
        } 