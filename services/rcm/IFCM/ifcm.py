"""
Internal Flow Control Module (IFCM)

Core workflow engine for the RCM microservice that orchestrates the entire lifecycle of a request.
Manages step-by-step processing, module invocation, data flow, error handling, and request monitoring.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Callable, Union
from datetime import datetime, timedelta
import uuid
from enum import Enum
from dataclasses import dataclass, asdict
import json
from pathlib import Path

from EMM.emm import ErrorManagementModule
from EMM.api_error_handler import api_error_handler

# Import other modules for orchestration
try:
    from GIDVM.gidvm import gidvm
    from PBRPM.pbrpm import pbrpm
    from AACM.aacm import aacm
    from FBWM.fbwm import fbwm
    from FDM.fdm import fdm
    from PRM.prm import prm
    from RTRMM.rtrmm import rtrmm
    from RLM.rlm import rlm
    from MMM.mmm import mmm
    from DRM.drm import drm
    from BTM.btm import btm
    from ECM.ecm import ecm
    from AAAIM.aaaim import aaaim
    from BAAIM.baaim import baaim
    from SAAIM.saaim import saaim
    from SODVM.sodvm import sodvm
    from DCMM.dcmm import dcmm
    from TMM.tmm import tmm
    from EMM.emm import emm
    from MSM.msm import msm
    from SMSM.smsm import smsm
    from SMCM.smcm import smcm
    from JFAIM.jfaim import jfaim
    from OCMIM.ocmim import ocmim
except ImportError:
    # Handle case where modules are not yet implemented
    pass


class RequestStatus(Enum):
    """Enumeration for request status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class ProcessingStep(Enum):
    """Enumeration for processing steps."""
    INPUT_VERIFICATION = "input_verification"
    PRIORITY_ROUTING = "priority_routing"
    API_SELECTION = "api_selection"
    API_CALL = "api_call"
    RESPONSE_VERIFICATION = "response_verification"
    OUTPUT_GENERATION = "output_generation"
    HANDOFF = "handoff"


@dataclass
class RequestContext:
    """Data class for request context."""
    request_id: str
    priority: str
    status: RequestStatus
    current_step: ProcessingStep
    start_time: datetime
    last_update: datetime
    retry_count: int = 0
    max_retries: int = 3
    error_message: Optional[str] = None
    data: Dict[str, Any] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.data is None:
            self.data = {}
        if self.metadata is None:
            self.metadata = {}


class InternalFlowControlModule:
    """
    Internal Flow Control Module (IFCM)
    
    Core workflow engine that orchestrates the entire lifecycle of a request:
    - Manages step-by-step processing of each request by unique ID
    - Invokes other modules in correct sequence
    - Handles data flow between modules
    - Implements comprehensive error handling and recovery logic
    - Monitors status of each active request
    - Manages tasks not tied to specific requests
    """
    
    def __init__(self):
        """Initialize the IFCM module."""
        self.logger = logging.getLogger(__name__)
        self.error_manager = ErrorManagementModule()
        
        # Request tracking
        self.active_requests: Dict[str, RequestContext] = {}
        self.completed_requests: Dict[str, RequestContext] = {}
        self.failed_requests: Dict[str, RequestContext] = {}
        
        # Module references
        self.modules = {}
        self._initialize_modules()
        
        # Configuration
        self.max_concurrent_requests = 10
        self.request_timeout = 300  # 5 minutes
        self.retry_delay = 5  # seconds
        
        # Statistics
        self.stats = {
            "total_requests": 0,
            "active_requests": 0,
            "completed_requests": 0,
            "failed_requests": 0,
            "average_processing_time": 0,
            "last_activity": None
        }
        
        # Error codes will be generated dynamically by EMM
        
        # Processing workflow definition
        self.workflow_steps = [
            ProcessingStep.INPUT_VERIFICATION,
            ProcessingStep.PRIORITY_ROUTING,
            ProcessingStep.API_SELECTION,
            ProcessingStep.API_CALL,
            ProcessingStep.RESPONSE_VERIFICATION,
            ProcessingStep.OUTPUT_GENERATION,
            ProcessingStep.HANDOFF
        ]
        
        # Step handlers
        self.step_handlers = {
            ProcessingStep.INPUT_VERIFICATION: self._handle_input_verification,
            ProcessingStep.PRIORITY_ROUTING: self._handle_priority_routing,
            ProcessingStep.API_SELECTION: self._handle_api_selection,
            ProcessingStep.API_CALL: self._handle_api_call,
            ProcessingStep.RESPONSE_VERIFICATION: self._handle_response_verification,
            ProcessingStep.OUTPUT_GENERATION: self._handle_output_generation,
            ProcessingStep.HANDOFF: self._handle_handoff
        }
    
    def _initialize_modules(self):
        """Initialize module references."""
        module_mapping = {
            "gidvm": "GIDVM",
            "pbrpm": "PBRPM",
            "aacm": "AACM",
            "fbwm": "FBWM",
            "fdm": "FDM",
            "prm": "PRM",
            "rtrmm": "RTRMM",
            "rlm": "RLM",
            "mmm": "MMM",
            "drm": "DRM",
            "btm": "BTM",
            "ecm": "ECM",
            "aaaim": "AAAIM",
            "baaim": "BAAIM",
            "saaim": "SAAIM",
            "sodvm": "SODVM",
            "dcmm": "DCMM",
            "tmm": "TMM",
            "emm": "EMM",
            "msm": "MSM",
            "smsm": "SMSM",
            "smcm": "SMCM",
            "jfaim": "JFAIM",
            "ocmim": "OCMIM"
        }
        
        for var_name, module_name in module_mapping.items():
            try:
                if var_name in globals():
                    self.modules[module_name] = globals()[var_name]
            except Exception as e:
                self.logger.warning(f"Could not initialize {module_name}: {e}")
    
    async def process_request(self, request_data: Dict[str, Any], priority: str = "C") -> str:
        """
        Process a new request through the complete workflow.
        
        Args:
            request_data: Request data dictionary
            priority: Request priority (A, B, C, D)
            
        Returns:
            Request ID for tracking
        """
        request_id = str(uuid.uuid4())
        
        # Create request context
        context = RequestContext(
            request_id=request_id,
            priority=priority,
            status=RequestStatus.PENDING,
            current_step=ProcessingStep.INPUT_VERIFICATION,
            start_time=datetime.now(),
            last_update=datetime.now(),
            data=request_data.copy(),
            metadata={
                "priority": priority,
                "original_data": request_data.copy()
            }
        )
        
        # Add to active requests
        self.active_requests[request_id] = context
        self.stats["total_requests"] += 1
        self.stats["active_requests"] += 1
        self.stats["last_activity"] = datetime.now()
        
        self.logger.info(f"Started processing request {request_id} with priority {priority}")
        
        # Start processing in background
        asyncio.create_task(self._process_request_workflow(context))
        
        return request_id
    
    async def _process_request_workflow(self, context: RequestContext):
        """Process a request through the complete workflow."""
        try:
            context.status = RequestStatus.PROCESSING
            context.last_update = datetime.now()
            
            # Process through each step
            for step in self.workflow_steps:
                context.current_step = step
                context.last_update = datetime.now()
                
                self.logger.info(f"Processing request {context.request_id} at step {step.value}")
                
                # Execute step handler
                handler = self.step_handlers.get(step)
                if handler:
                    success = await handler(context)
                    if not success:
                        await self._handle_step_failure(context, step)
                        return
                else:
                    self.logger.warning(f"No handler found for step {step.value}")
                
                # Check for timeout
                if (datetime.now() - context.start_time).total_seconds() > self.request_timeout:
                    await self._handle_request_timeout(context)
                    return
            
            # Workflow completed successfully
            await self._handle_request_completion(context)
            
        except Exception as e:
            await self._handle_request_error(context, str(e))
    
    async def _handle_input_verification(self, context: RequestContext) -> bool:
        """Handle input verification step."""
        try:
            # Use GIDVM for input verification
            if "GIDVM" in self.modules:
                gidvm_module = self.modules["GIDVM"]
                if hasattr(gidvm_module, 'verify_input'):
                    result = await gidvm_module.verify_input(context.data)
                    if not result:
                        context.error_message = "Input verification failed"
                        return False
                else:
                    # Basic verification
                    if not context.data:
                        context.error_message = "No request data provided"
                        return False
            
            self.logger.info(f"Input verification passed for request {context.request_id}")
            return True
            
        except Exception as e:
            context.error_message = f"Input verification error: {e}"
            return False
    
    async def _handle_priority_routing(self, context: RequestContext) -> bool:
        """Handle priority routing step."""
        try:
            # Use PRM for priority routing
            if "PRM" in self.modules:
                prm_module = self.modules["PRM"]
                if hasattr(prm_module, 'route_request'):
                    route_result = await prm_module.route_request(context.data, context.priority)
                    context.metadata["routing_info"] = route_result
                else:
                    # Basic routing
                    context.metadata["routing_info"] = {"priority": context.priority}
            
            self.logger.info(f"Priority routing completed for request {context.request_id}")
            return True
            
        except Exception as e:
            context.error_message = f"Priority routing error: {e}"
            return False
    
    async def _handle_api_selection(self, context: RequestContext) -> bool:
        """Handle API selection step."""
        try:
            # Determine which API module to use based on request data
            api_type = context.data.get("api_type", "basic")
            
            if api_type == "agentic" and "AAAIM" in self.modules:
                context.metadata["selected_api"] = "AAAIM"
            elif api_type == "special" and "SAAIM" in self.modules:
                context.metadata["selected_api"] = "SAAIM"
            else:
                context.metadata["selected_api"] = "BAAIM"
            
            self.logger.info(f"API selection completed for request {context.request_id}: {context.metadata['selected_api']}")
            return True
            
        except Exception as e:
            context.error_message = f"API selection error: {e}"
            return False
    
    async def _handle_api_call(self, context: RequestContext) -> bool:
        """Handle API call step."""
        try:
            selected_api = context.metadata.get("selected_api", "BAAIM")
            
            if selected_api in self.modules:
                api_module = self.modules[selected_api]
                if hasattr(api_module, 'process_request'):
                    response = await api_module.process_request(context.data)
                    context.data["api_response"] = response
                    context.metadata["api_used"] = selected_api
                else:
                    # Mock response for testing
                    context.data["api_response"] = {
                        "status": "success",
                        "response": "Mock API response",
                        "timestamp": datetime.now().isoformat()
                    }
                    context.metadata["api_used"] = selected_api
            else:
                context.error_message = f"API module {selected_api} not available"
                return False
            
            self.logger.info(f"API call completed for request {context.request_id}")
            return True
            
        except Exception as e:
            context.error_message = f"API call error: {e}"
            return False
    
    async def _handle_response_verification(self, context: RequestContext) -> bool:
        """Handle response verification step."""
        try:
            # Use SODVM for response verification
            if "SODVM" in self.modules:
                sodvm_module = self.modules["SODVM"]
                if hasattr(sodvm_module, 'verify_response'):
                    verification_result = await sodvm_module.verify_response(context.data.get("api_response"))
                    if not verification_result:
                        context.error_message = "Response verification failed"
                        return False
                else:
                    # Basic verification
                    response = context.data.get("api_response")
                    if not response or "status" not in response:
                        context.error_message = "Invalid API response"
                        return False
            
            self.logger.info(f"Response verification completed for request {context.request_id}")
            return True
            
        except Exception as e:
            context.error_message = f"Response verification error: {e}"
            return False
    
    async def _handle_output_generation(self, context: RequestContext) -> bool:
        """Handle output generation step."""
        try:
            # Generate output based on response type
            response = context.data.get("api_response", {})
            
            if response.get("type") == "json_template":
                context.metadata["output_type"] = "jfa_handoff"
            else:
                context.metadata["output_type"] = "ocm_handoff"
            
            self.logger.info(f"Output generation completed for request {context.request_id}")
            return True
            
        except Exception as e:
            context.error_message = f"Output generation error: {e}"
            return False
    
    async def _handle_handoff(self, context: RequestContext) -> bool:
        """Handle handoff step."""
        try:
            output_type = context.metadata.get("output_type", "ocm_handoff")

            if output_type == "jfa_handoff" and "JFAIM" in self.modules:
                jfaim_module = self.modules["JFAIM"]
                if hasattr(jfaim_module, 'handoff_response'):
                    await jfaim_module.handoff_response(context.request_id, context.data.get("api_response", {}), response_type="success")
            elif "OCMIM" in self.modules:
                ocmim_module = self.modules["OCMIM"]
                if hasattr(ocmim_module, 'handoff_response'):
                    await ocmim_module.handoff_response(context.request_id, context.data.get("api_response", {}), response_type="success")

            self.logger.info(f"Handoff completed for request {context.request_id}")
            return True

        except Exception as e:
            context.error_message = f"Handoff error: {e}"
            return False
    
    async def _handle_step_failure(self, context: RequestContext, step: ProcessingStep):
        """Handle step failure with retry logic."""
        context.retry_count += 1
        
        if context.retry_count <= context.max_retries:
            context.status = RequestStatus.RETRYING
            context.last_update = datetime.now()
            
            self.logger.warning(f"Step {step.value} failed for request {context.request_id}, retrying ({context.retry_count}/{context.max_retries})")
            
            # Wait before retry
            await asyncio.sleep(self.retry_delay)
            
            # Retry the step
            handler = self.step_handlers.get(step)
            if handler:
                success = await handler(context)
                if success:
                    context.status = RequestStatus.PROCESSING
                    return
        
        # Max retries exceeded
        await self._handle_request_error(context, f"Step {step.value} failed after {context.max_retries} retries")
    
    async def _handle_request_timeout(self, context: RequestContext):
        """Handle request timeout."""
        context.status = RequestStatus.FAILED
        context.error_message = f"Request timed out after {self.request_timeout} seconds"
        context.last_update = datetime.now()
        
        self.logger.error(f"Request {context.request_id} timed out")
        self.log_error_with_generation("IFCM", "InternalFlowControlModule", "_handle_request_timeout", context.error_message)
        
        await self._finalize_request(context)
    
    async def _handle_request_error(self, context: RequestContext, error_message: str):
        """Handle request error."""
        context.status = RequestStatus.FAILED
        context.error_message = error_message
        context.last_update = datetime.now()
        
        self.logger.error(f"Request {context.request_id} failed: {error_message}")
        self.log_error_with_generation("IFCM", "InternalFlowControlModule", "_handle_request_error", error_message)
        
        await self._finalize_request(context)
    
    async def _handle_request_completion(self, context: RequestContext):
        """Handle successful request completion."""
        context.status = RequestStatus.COMPLETED
        context.last_update = datetime.now()
        
        processing_time = (context.last_update - context.start_time).total_seconds()
        self.logger.info(f"Request {context.request_id} completed successfully in {processing_time:.2f}s")
        
        await self._finalize_request(context)
    
    async def _finalize_request(self, context: RequestContext):
        """Finalize request processing."""
        # Remove from active requests
        if context.request_id in self.active_requests:
            del self.active_requests[context.request_id]
            self.stats["active_requests"] -= 1
        
        # Add to appropriate completed/failed list
        if context.status == RequestStatus.COMPLETED:
            self.completed_requests[context.request_id] = context
            self.stats["completed_requests"] += 1
        else:
            self.failed_requests[context.request_id] = context
            self.stats["failed_requests"] += 1
        
        # Update average processing time
        if context.status == RequestStatus.COMPLETED:
            processing_time = (context.last_update - context.start_time).total_seconds()
            total_completed = self.stats["completed_requests"]
            current_avg = self.stats["average_processing_time"]
            self.stats["average_processing_time"] = (current_avg * (total_completed - 1) + processing_time) / total_completed
        
        self.stats["last_activity"] = datetime.now()
    
    def get_request_status(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific request."""
        # Check active requests
        if request_id in self.active_requests:
            context = self.active_requests[request_id]
            return asdict(context)
        
        # Check completed requests
        if request_id in self.completed_requests:
            context = self.completed_requests[request_id]
            return asdict(context)
        
        # Check failed requests
        if request_id in self.failed_requests:
            context = self.failed_requests[request_id]
            return asdict(context)
        
        return None
    
    def get_all_request_statuses(self) -> Dict[str, Any]:
        """Get status of all requests."""
        return {
            "active_requests": {rid: asdict(ctx) for rid, ctx in self.active_requests.items()},
            "completed_requests": {rid: asdict(ctx) for rid, ctx in self.completed_requests.items()},
            "failed_requests": {rid: asdict(ctx) for rid, ctx in self.failed_requests.items()},
            "stats": self.stats.copy()
        }
    
    def get_module_status(self) -> Dict[str, Any]:
        """Get IFCM module status."""
        return {
            "module": "IFCM",
            "status": "active",
            "active_requests_count": len(self.active_requests),
            "completed_requests_count": len(self.completed_requests),
            "failed_requests_count": len(self.failed_requests),
            "available_modules": list(self.modules.keys()),
            "workflow_steps": [step.value for step in self.workflow_steps],
            "stats": self.stats.copy(),
            "last_activity": self.stats["last_activity"]
        }
    
    async def cancel_request(self, request_id: str) -> bool:
        """Cancel an active request."""
        if request_id in self.active_requests:
            context = self.active_requests[request_id]
            context.status = RequestStatus.CANCELLED
            context.last_update = datetime.now()
            
            self.logger.info(f"Request {request_id} cancelled")
            await self._finalize_request(context)
            return True
        
        return False
    
    async def retry_request(self, request_id: str) -> bool:
        """Retry a failed request."""
        if request_id in self.failed_requests:
            context = self.failed_requests[request_id]
            
            # Reset context for retry
            context.status = RequestStatus.PENDING
            context.current_step = ProcessingStep.INPUT_VERIFICATION
            context.retry_count = 0
            context.error_message = None
            context.start_time = datetime.now()
            context.last_update = datetime.now()
            
            # Move back to active requests
            del self.failed_requests[request_id]
            self.active_requests[request_id] = context
            self.stats["failed_requests"] -= 1
            self.stats["active_requests"] += 1
            
            self.logger.info(f"Retrying request {request_id}")
            
            # Start processing again
            asyncio.create_task(self._process_request_workflow(context))
            return True
        
        return False
    
    def cleanup_old_requests(self, max_age_hours: int = 24):
        """Clean up old completed/failed requests."""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        # Clean completed requests
        old_completed = [rid for rid, ctx in self.completed_requests.items() 
                        if ctx.last_update < cutoff_time]
        for rid in old_completed:
            del self.completed_requests[rid]
        
        # Clean failed requests
        old_failed = [rid for rid, ctx in self.failed_requests.items() 
                     if ctx.last_update < cutoff_time]
        for rid in old_failed:
            del self.failed_requests[rid]
        
        if old_completed or old_failed:
            self.logger.info(f"Cleaned up {len(old_completed)} completed and {len(old_failed)} failed requests")

    def log_error_with_generation(self, module_name: str, class_name: str, function_name: str, error_message: str, error_code: str = None):
        """Log error with dynamic code generation using EMM."""
        if hasattr(self, 'error_manager'):
            self.error_manager.log_error_with_generation(module_name, class_name, function_name, error_message, error_code)
        else:
            self.logger.error(f"Error in {module_name}.{class_name}.{function_name}: {error_message}")

    async def handle_api_error(self, error: Exception, context: str = "unknown") -> dict:
        return api_error_handler.handle_error(error, context, "IFCM")

# Global instances
ifcm = InternalFlowControlModule()
IFCM = InternalFlowControlModule() 