"""
OCM Interaction Module (OCMIM)

Manages the handoff of user-facing responses to the OCM (Output Control Manager) block, which handles delivery to the end-user/website.
When the API returns a direct response intended for the user, this module creates a new JSON file containing the API response payload and the original Request ID.
"""

import json
import logging
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
from EMM.emm import ErrorManagementModule
from EMM.api_error_handler import api_error_handler

# Import other modules for integration
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from DCMM.dcmm import DatabaseControlAndManagementModule
from FOM.fom import FileOutputModule
from ECM.ecm import ecm


class OCMInteractionModule:
    """
    OCM Interaction Module (OCMIM)
    
    Responsibilities:
    - Handoff user-facing responses to the OCM block
    - Manage response delivery to end-users/websites
    - Handle response formatting and validation
    - Track delivery status and user interactions
    - Integrate with OCM block for seamless delivery
    - Manage response caching and retry mechanisms
    """
    MODULE_CODE = "18"  # Unique code for OCMIM
    
    def __init__(self, ocm_output_dir: Optional[Path] = None, logger: Optional[logging.Logger] = None):
        """
        Initialize the OCMIM module.
        
        Args:
            ocm_output_dir: Output directory for OCM files
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
        self.error_manager = ErrorManagementModule()
        self.dcmm = DatabaseControlAndManagementModule()
        self.fom = FileOutputModule()
        
        # Error codes for this module
        
        # Statistics
        self.stats = {
            "total_handoffs": 0,
            "successful_handoffs": 0,
            "failed_handoffs": 0,
            "responses_delivered": 0,
            "cache_hits": 0,
            "retry_attempts": 0,
            "last_activity": None
        }
        
        # OCM system paths
        self.ocm_output_dir = ocm_output_dir or Path("ocm_output")
        self.ocm_output_dir.mkdir(parents=True, exist_ok=True)
        
        # Response cache
        self.response_cache: Dict[str, Dict[str, Any]] = {}
        
        # Delivery status tracking
        self.delivery_status: Dict[str, Dict[str, Any]] = {}
        
        # Response templates
        self.response_templates = {
            "success": {
                "status": "success",
                "message": "Request processed successfully",
                "data": {}
            },
            "error": {
                "status": "error",
                "message": "An error occurred",
                "error_code": "",
                "details": {}
            },
            "pending": {
                "status": "pending",
                "message": "Request is being processed",
                "estimated_completion": ""
            }
        }
    
    def validate_response(self, api_response: Dict[str, Any]) -> bool:
        """
        Validate an API response for OCM handoff.
        
        Args:
            api_response: API response to validate
            
        Returns:
            True if valid, False otherwise
        """
        try:
            # Check if response is not empty
            if not api_response:
                self.logger.error("OCMIM: API response is empty")
                return False
            
            # Check for required fields based on response type
            if "status" in api_response:
                status = api_response["status"]
                if status not in ["success", "error", "pending"]:
                    self.logger.error(f"OCMIM: Invalid status '{status}' in response")
                    return False
            
            # Check response size (reasonable limit)
            response_str = json.dumps(api_response)
            if len(response_str) > 1000000:  # 1MB limit
                self.logger.error("OCMIM: Response too large for handoff")
                return False
            
            # Check for potentially harmful content
            harmful_patterns = ["<script>", "javascript:", "eval(", "exec("]
            response_lower = response_str.lower()
            for pattern in harmful_patterns:
                if pattern in response_lower:
                    self.logger.error(f"OCMIM: Response contains potentially harmful content: {pattern}")
                    return False
            
            return True
            
        except Exception as e:
            error_msg = f"Error validating response: {e}"
            self.logger.error(error_msg)
            self.log_error(error_msg, "OCMInteractionModule", "validate_response")
            return False
    
    def format_response_for_ocm(self, request_id: str, api_response: Dict[str, Any], 
                               response_type: str = "success") -> Dict[str, Any]:
        """
        Format API response for OCM handoff.
        
        Args:
            request_id: Request identifier
            api_response: API response data
            response_type: Type of response (success, error, pending)
            
        Returns:
            Formatted response for OCM
        """
        try:
            # Get base template
            template = self.response_templates.get(response_type, self.response_templates["success"])
            
            # Create formatted response
            formatted_response = {
                "request_id": request_id,
                "response_type": response_type,
                "timestamp": datetime.now().isoformat(),
                "ocm_metadata": {
                    "module": "OCMIM",
                    "version": "1.0",
                    "handoff_id": f"ocm_{request_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                },
                "payload": api_response,
                "template": template.copy()
            }
            
            # Update template with actual data
            if response_type == "success":
                formatted_response["template"]["data"] = api_response
            elif response_type == "error":
                formatted_response["template"]["error_code"] = api_response.get("error_code", "UNKNOWN_ERROR")
                formatted_response["template"]["details"] = api_response.get("details", {})
            elif response_type == "pending":
                formatted_response["template"]["estimated_completion"] = api_response.get("estimated_completion", "")
            
            return formatted_response
            
        except Exception as e:
            error_msg = f"Error formatting response for OCM: {e}"
            self.logger.error(error_msg)
            self.log_error(error_msg, "OCMInteractionModule", "format_response_for_ocm")
            return self.response_templates["error"]
    
    async def handoff_response(self, request_id: str, api_response: Dict[str, Any], response_type: str = "success") -> Dict[str, Any]:
        """
        Handoff the API response to the OCM block via CCU (WebSocket handoff).
        """
        try:
            # Validate response
            if not self.validate_response(api_response):
                return {"success": False, "error": "Response validation failed"}

            # Format response for OCM
            formatted_response = self.format_response_for_ocm(request_id, api_response, response_type)

            # Use ECM to send to CCU (source_module='OCMIM')
            await ecm.send_output_request_to_ccu(request_id, formatted_response, priority="C", timeout_seconds=300, source_module="OCMIM")
            self.logger.info(f"OCMIM: Sent handoff to CCU for request {request_id}")
            # Cache response (optional, for local tracking)
            self.response_cache[request_id] = {
                "response": formatted_response,
                "timestamp": datetime.now().isoformat(),
                "response_type": response_type
            }
            # Update delivery status
            self.delivery_status[request_id] = {
                "status": "handed_off",
                "response_type": response_type,
                "timestamp": datetime.now().isoformat(),
                "retry_count": 0
            }
            # Update statistics
            self.stats["total_handoffs"] += 1
            self.stats["successful_handoffs"] += 1
            self.stats["last_activity"] = datetime.now()
            # Log to database
            await self.dcmm.log_test_result(
                test_code="OCM_HANDOFF",
                test_name=f"OCM Handoff - {request_id}",
                status="pass",
                output=json.dumps(formatted_response, indent=2),
                execution_time=datetime.now().timestamp()
            )
            return {
                "success": True,
                "handoff": "sent_to_ccu",
                "request_id": request_id,
                "response_type": response_type
            }
        except Exception as e:
            error_msg = f"Error handing off response to CCU for request {request_id}: {e}"
            self.logger.error(error_msg)
            self.log_error(error_msg, "OCMInteractionModule", "handoff_response")
            self.stats["total_handoffs"] += 1
            self.stats["failed_handoffs"] += 1
            return {"success": False, "error": error_msg}
    
    async def deliver_response(self, request_id: str, delivery_method: str = "file") -> Dict[str, Any]:
        """
        Deliver response to end-user through specified method.
        
        Args:
            request_id: Request identifier
            delivery_method: Method of delivery (file, api, websocket, etc.)
            
        Returns:
            Dictionary with delivery results
        """
        try:
            # Check if response exists in cache
            if request_id not in self.response_cache:
                return {"success": False, "error": "Response not found in cache"}
            
            cached_response = self.response_cache[request_id]
            
            # Update delivery status
            self.delivery_status[request_id]["status"] = "delivering"
            self.delivery_status[request_id]["delivery_method"] = delivery_method
            self.delivery_status[request_id]["delivery_timestamp"] = datetime.now().isoformat()
            
            # Simulate delivery based on method
            if delivery_method == "file":
                # File is already created, just update status
                delivery_result = {"method": "file", "file_path": cached_response["file_path"]}
            elif delivery_method == "api":
                # Simulate API delivery
                delivery_result = {"method": "api", "endpoint": f"/api/responses/{request_id}"}
            elif delivery_method == "websocket":
                # Simulate WebSocket delivery
                delivery_result = {"method": "websocket", "channel": f"response_{request_id}"}
            else:
                delivery_result = {"method": delivery_method, "status": "unknown"}
            
            # Update delivery status
            self.delivery_status[request_id]["status"] = "delivered"
            self.delivery_status[request_id]["delivery_result"] = delivery_result
            
            # Update statistics
            self.stats["responses_delivered"] += 1
            self.stats["last_activity"] = datetime.now()
            
            self.logger.info(f"OCMIM: Successfully delivered response for request {request_id} via {delivery_method}")
            return {
                "success": True,
                "request_id": request_id,
                "delivery_method": delivery_method,
                "delivery_result": delivery_result
            }
            
        except Exception as e:
            error_msg = f"Error delivering response for request {request_id}: {e}"
            self.logger.error(error_msg)
            self.log_error(error_msg, "OCMInteractionModule", "deliver_response")
            return {"success": False, "error": error_msg}
    
    async def retry_delivery(self, request_id: str, max_retries: int = 3) -> Dict[str, Any]:
        """
        Retry delivery of a response.
        
        Args:
            request_id: Request identifier
            max_retries: Maximum number of retry attempts
            
        Returns:
            Dictionary with retry results
        """
        try:
            if request_id not in self.delivery_status:
                return {"success": False, "error": "Request not found in delivery status"}
            
            status = self.delivery_status[request_id]
            current_retries = status.get("retry_count", 0)
            
            if current_retries >= max_retries:
                return {"success": False, "error": "Maximum retry attempts exceeded"}
            
            # Increment retry count
            status["retry_count"] = current_retries + 1
            status["last_retry"] = datetime.now().isoformat()
            
            # Attempt delivery
            delivery_result = await self.deliver_response(request_id, status.get("delivery_method", "file"))
            
            # Update statistics
            self.stats["retry_attempts"] += 1
            
            if delivery_result["success"]:
                status["status"] = "delivered"
                self.logger.info(f"OCMIM: Retry successful for request {request_id}")
            else:
                status["status"] = "retry_failed"
                self.logger.warning(f"OCMIM: Retry failed for request {request_id}")
            
            return delivery_result
            
        except Exception as e:
            error_msg = f"Error retrying delivery for request {request_id}: {e}"
            self.logger.error(error_msg)
            self.log_error(error_msg, "OCMInteractionModule", "retry_delivery")
            return {"success": False, "error": error_msg}
    
    def get_cached_response(self, request_id: str) -> Optional[Dict[str, Any]]:
        """
        Get cached response for a request.
        
        Args:
            request_id: Request identifier
            
        Returns:
            Cached response or None if not found
        """
        cached = self.response_cache.get(request_id)
        if cached:
            self.stats["cache_hits"] += 1
            return cached
        return None
    
    def get_delivery_status(self, request_id: str) -> Dict[str, Any]:
        """
        Get delivery status for a request.
        
        Args:
            request_id: Request identifier
            
        Returns:
            Dictionary with delivery status
        """
        return self.delivery_status.get(request_id, {
            "status": "not_found",
            "request_id": request_id
        })
    
    def clear_cache(self, request_id: Optional[str] = None):
        """
        Clear response cache.
        
        Args:
            request_id: Specific request ID to clear, or None to clear all
        """
        if request_id:
            if request_id in self.response_cache:
                del self.response_cache[request_id]
                self.logger.info(f"OCMIM: Cleared cache for request {request_id}")
        else:
            self.response_cache.clear()
            self.logger.info("OCMIM: Cleared all cached responses")
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the OCMIM module.
        
        Returns:
            Dictionary with module status information
        """
        return {
            "module": "OCMIM",
            "output_directory": str(self.ocm_output_dir),
            "cached_responses": len(self.response_cache),
            "active_deliveries": len([s for s in self.delivery_status.values() if s["status"] == "delivering"]),
            "stats": self.stats.copy()
        }
    
    def reset_stats(self):
        """Reset module statistics."""
        self.stats = {
            "total_handoffs": 0,
            "successful_handoffs": 0,
            "failed_handoffs": 0,
            "responses_delivered": 0,
            "cache_hits": 0,
            "retry_attempts": 0,
            "last_activity": None
        }
        self.logger.info("OCMIM: Statistics reset")
    
    async def start(self):
        """Start the OCMIM module."""
        self.logger.info("OCMIM: Module started")
    
    async def stop(self):
        """Stop the OCMIM module."""
        self.logger.info("OCMIM: Module stopped")

    def log_error(self, error_message: str, class_name: str = "UnknownClass", function_name: str = "UnknownFunction", sub_function: str = "001"):
        """Log an error using EMM."""
        return self.error_manager.log_error_with_generation(
            "OCMIM", 
            class_name, 
            function_name, 
            error_message, 
            sub_function
        )

    def generate_error_code(self, class_name: str = "UnknownClass", function_name: str = "UnknownFunction", sub_function: str = "001") -> str:
        """Generate an error code using EMM."""
        return self.error_manager.generate_error_code("OCMIM", class_name, function_name, sub_function)

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
            # Assuming api_error_handler is defined elsewhere or needs to be imported
            # For now, we'll simulate its existence and call its methods
            # In a real scenario, this would be a separate module or imported directly
            # For demonstration, we'll create a dummy object
            class DummyAPIErrHandler:
                async def handle_api_error(self, err_resp: str, sc: int, ctx: dict):
                    return {"success": False, "api_error_type": "dummy_api_error", "details": {"error_response": err_resp, "status_code": sc, "context": ctx}}
                async def send_error_report_to_ccu(self, result: dict):
                    self.logger.warning(f"Dummy CCU: Sending error report: {result}")

            api_error_handler = DummyAPIErrHandler()

            result = await api_error_handler.handle_api_error(error_response, status_code, context)
            self.error_manager.log_error_with_generation(
                "OCMIM",
                "OCMIM",
                "handle_api_error",
                f"API Error: {result.get('api_error_type', 'unknown')}",
                context=result
            )
            await api_error_handler.send_error_report_to_ccu(result)
            return result
        except Exception as e:
            self.error_manager.log_error_with_generation(
                "OCMIM",
                "OCMIM",
                "handle_api_error",
                f"Error handling API error: {str(e)}"
            )
            return {"success": False, "error": str(e)}


# Global instance and alias for compatibility
ocmim = OCMInteractionModule()
OCMIM = OCMInteractionModule  # Class alias 