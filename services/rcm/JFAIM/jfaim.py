"""
JFA Interaction Module (JFAIM) - Updated for Refactored JFA

Manages the handoff of processed data to the refactored JFA (JSON Fulfillment & Analysis) microservice.
Now communicates directly with JFA via API endpoints instead of file operations.
"""

import json
import logging
import os
import shutil
import aiohttp
import asyncio
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
from pathlib import Path
from EMM.emm import ErrorManagementModule
from EMM.api_error_handler import api_error_handler

# Import other modules for integration
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from DCMM.dcmm import DatabaseControlAndManagementModule
from FOM.fom import FileOutputModule
from ECM.ecm import ecm


class JFAInteractionModule:
    """
    JFA Interaction Module (JFAIM) - Updated for Refactored JFA
    
    Responsibilities:
    - Process JSON templates from API responses
    - Extract and validate JFA-specific data
    - Communicate directly with JFA microservice via API
    - Handle binary data generation and validation
    - Track JFA processing status and results
    - Manage integration with refactored JFA system
    """
    MODULE_CODE = "17"  # Unique code for JFAIM
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize the JFAIM module.
        
        Args:
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
        self.error_manager = ErrorManagementModule()
        self.dcmm = DatabaseControlAndManagementModule()
        self.fom = FileOutputModule()
        
        # JFA API configuration
        self.jfa_api_config = {
            "base_url": "http://localhost:8001",
            "timeout": 30,
            "retry_attempts": 3,
            "retry_delay": 1
        }
        
        # Statistics
        self.stats = {
            "total_jfa_requests": 0,
            "successful_processing": 0,
            "failed_processing": 0,
            "templates_processed": 0,
            "binary_files_generated": 0,
            "analyses_completed": 0,
            "api_calls_made": 0,
            "api_errors": 0,
            "last_activity": None
        }
        
        # JFA template types
        self.template_types = {
            "ofgssc": "Off-grid Solar System Calculation",
            "ongssc": "On-grid Solar System Calculation", 
            "hssc": "Hybrid Solar System Calculation",
            "lssppc": "Large Scale Solar Power Plant Calculation",
            "pec": "Power Economics Calculation",
            "rcp": "Rent Contract Processing",
            "dgc": "Diesel Generator Calculation",
            "nggc": "Natural Gas Generator Calculation",
            "lggc": "Liquid Gas Generator Calculation",
            "upssc": "UPS System Calculation",
            "epc": "Energy Performance Calculation",
            "cas": "Customer Analysis System"
        }
        
        # JFA processing status
        self.processing_status = {}
        
        # HTTP session for API calls
        self.session = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """
        Get or create HTTP session for API calls.
        
        Returns:
            aiohttp.ClientSession
        """
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=self.jfa_api_config["timeout"])
            self.session = aiohttp.ClientSession(timeout=timeout)
        return self.session
    
    async def _make_api_call(self, endpoint: str, method: str = "GET", data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Make API call to JFA microservice.
        
        Args:
            endpoint: API endpoint
            method: HTTP method
            data: Request data
            
        Returns:
            API response
        """
        try:
            session = await self._get_session()
            url = f"{self.jfa_api_config['base_url']}{endpoint}"
            
            self.stats["api_calls_made"] += 1
            
            if method.upper() == "GET":
                async with session.get(url) as response:
                    return await response.json()
            elif method.upper() == "POST":
                async with session.post(url, json=data) as response:
                    return await response.json()
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
                
        except Exception as e:
            self.stats["api_errors"] += 1
            error_msg = f"API call failed to {endpoint}: {e}"
            self.logger.error(error_msg)
            self.log_error(error_msg, "JFAInteractionModule", "_make_api_call")
            raise
    
    def validate_jfa_template(self, template_data: Dict[str, Any]) -> bool:
        """
        Validate a JFA template for required fields and structure.
        
        Args:
            template_data: Template data to validate
            
        Returns:
            True if valid, False otherwise
        """
        try:
            # Check required top-level fields
            required_fields = ["id", "object", "created", "model", "choices", "usage"]
            for field in required_fields:
                if field not in template_data:
                    self.logger.error(f"JFAIM: Missing required field '{field}' in template")
                    return False
            
            # Check choices structure
            choices = template_data.get("choices", {})
            if not isinstance(choices, dict):
                self.logger.error("JFAIM: 'choices' field must be an object")
                return False
            
            # Check message structure
            message = choices.get("message", {})
            if not isinstance(message, dict):
                self.logger.error("JFAIM: 'message' field must be an object")
                return False
            
            # Check required message fields
            if "role" not in message or "content" not in message:
                self.logger.error("JFAIM: Missing 'role' or 'content' in message")
                return False
            
            # Check usage structure
            usage = template_data.get("usage", {})
            if not isinstance(usage, dict):
                self.logger.error("JFAIM: 'usage' field must be an object")
                return False
            
            return True
            
        except Exception as e:
            error_msg = f"Error validating JFA template: {e}"
            self.logger.error(error_msg)
            self.log_error(error_msg, "JFAInteractionModule", "validate_jfa_template")
            return False
    
    async def process_jfa_template(self, template_data: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """
        Process a JFA template and extract relevant data.
        
        Args:
            template_data: Template data to process
            request_id: Request identifier
            
        Returns:
            Dictionary with processing results
        """
        try:
            # Validate template
            if not self.validate_jfa_template(template_data):
                return {"success": False, "error": "Template validation failed"}
            
            # Extract basic information
            template_id = template_data.get("id", "")
            model = template_data.get("model", "")
            created = template_data.get("created", 0)
            
            # Extract choices data
            choices = template_data.get("choices", {})
            message = choices.get("message", {})
            content = message.get("content", "")
            role = message.get("role", "")
            
            # Extract usage information
            usage = template_data.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            total_tokens = usage.get("total_tokens", 0)
            
            # Determine template type from content
            template_type = self._determine_template_type(content)
            
            # Create processing result
            result = {
                "success": True,
                "request_id": request_id,
                "template_id": template_id,
                "template_type": template_type,
                "model": model,
                "created": created,
                "role": role,
                "content": content,
                "usage": {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": total_tokens
                },
                "processing_timestamp": datetime.now().isoformat()
            }
            
            # Update statistics
            self.stats["total_jfa_requests"] += 1
            self.stats["successful_processing"] += 1
            self.stats["templates_processed"] += 1
            self.stats["last_activity"] = datetime.now()
            
            # Store processing status
            self.processing_status[request_id] = {
                "status": "processed",
                "template_type": template_type,
                "timestamp": datetime.now().isoformat()
            }
            
            self.logger.info(f"JFAIM: Successfully processed template for request {request_id}")
            return result
            
        except Exception as e:
            error_msg = f"Error processing JFA template for request {request_id}: {e}"
            self.logger.error(error_msg)
            self.log_error(error_msg, "JFAInteractionModule", "process_jfa_template")
            self.stats["total_jfa_requests"] += 1
            self.stats["failed_processing"] += 1
            return {"success": False, "error": error_msg}
    
    def _determine_template_type(self, content: str) -> str:
        """
        Determine the template type from content analysis.
        
        Args:
            content: Template content
            
        Returns:
            Template type identifier
        """
        try:
            content_lower = content.lower()
            
            # Check for specific keywords to determine template type
            if "off-grid" in content_lower or "offgrid" in content_lower:
                return "ofgssc"
            elif "on-grid" in content_lower or "ongrid" in content_lower:
                return "ongssc"
            elif "hybrid" in content_lower:
                return "hssc"
            elif "large scale" in content_lower or "power plant" in content_lower:
                return "lssppc"
            elif "economics" in content_lower or "economic" in content_lower:
                return "pec"
            elif "rent" in content_lower or "contract" in content_lower:
                return "rcp"
            elif "diesel" in content_lower:
                return "dgc"
            elif "natural gas" in content_lower:
                return "nggc"
            elif "liquid gas" in content_lower:
                return "lggc"
            elif "ups" in content_lower:
                return "upssc"
            elif "performance" in content_lower:
                return "epc"
            elif "customer" in content_lower and "analysis" in content_lower:
                return "cas"
            else:
                return "unknown"
                
        except Exception as e:
            self.logger.error(f"Error determining template type: {e}")
            return "unknown"
    
    async def send_to_jfa_microservice(self, template_data: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """
        Send template data to JFA microservice via CCU (WebSocket handoff).
        """
        try:
            # Prepare request data
            request_data = {
                "template_data": template_data,
                "request_id": request_id,
                "priority": "normal"
            }
            # Use ECM to send to CCU (source_module='JFAIM')
            await ecm.send_output_request_to_ccu(request_id, request_data, priority="C", timeout_seconds=300, source_module="JFAIM")
            self.logger.info(f"JFAIM: Sent handoff to CCU for request {request_id}")
            return {"success": True, "handoff": "sent_to_ccu"}
        except Exception as e:
            error_msg = f"Error sending data to CCU for request {request_id}: {e}"
            self.logger.error(error_msg)
            self.log_error(error_msg, "JFAInteractionModule", "send_to_jfa_microservice")
            self.stats["failed_processing"] += 1
            return {"success": False, "error": error_msg}
    
    async def process_complete_jfa_workflow(self, template_data: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """
        Process complete JFA workflow: template processing and JFA microservice communication.
        
        Args:
            template_data: Template data to process
            request_id: Request identifier
            
        Returns:
            Dictionary with complete workflow results
        """
        try:
            # Step 1: Process template
            template_result = await self.process_jfa_template(template_data, request_id)
            if not template_result["success"]:
                return template_result
            
            # Step 2: Send to JFA microservice
            jfa_result = await self.send_to_jfa_microservice(template_data, request_id)
            
            # Combine results
            result = {
                "success": jfa_result.get("success", False),
                "request_id": request_id,
                "template_processing": template_result,
                "jfa_processing": jfa_result,
                "workflow_timestamp": datetime.now().isoformat()
            }
            
            # Log to database
            await self.dcmm.log_test_result(
                test_code="JFA_WORKFLOW",
                test_name=f"JFA Workflow - {request_id}",
                status="pass" if result["success"] else "fail",
                output=json.dumps(result, indent=2),
                execution_time=datetime.now().timestamp()
            )
            
            return result
            
        except Exception as e:
            error_msg = f"Error in complete JFA workflow for request {request_id}: {e}"
            self.logger.error(error_msg)
            self.log_error(error_msg, "JFAInteractionModule", "process_complete_jfa_workflow")
            return {"success": False, "error": error_msg}
    
    async def check_jfa_service_status(self) -> Dict[str, Any]:
        """
        Check the status of the JFA microservice.
        
        Returns:
            Dictionary with JFA service status
        """
        try:
            response = await self._make_api_call("/health")
            return response
        except Exception as e:
            error_msg = f"Error checking JFA service status: {e}"
            self.logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    async def get_jfa_statistics(self) -> Dict[str, Any]:
        """
        Get statistics from the JFA microservice.
        
        Returns:
            Dictionary with JFA statistics
        """
        try:
            response = await self._make_api_call("/stats")
            return response
        except Exception as e:
            error_msg = f"Error getting JFA statistics: {e}"
            self.logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    def get_jfa_status(self, request_id: str) -> Dict[str, Any]:
        """
        Get JFA processing status for a request.
        
        Args:
            request_id: Request identifier
            
        Returns:
            Dictionary with JFA status information
        """
        return self.processing_status.get(request_id, {
            "status": "not_found",
            "template_type": None,
            "timestamp": None
        })
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the JFAIM module.
        
        Returns:
            Dictionary with module status information
        """
        return {
            "module": "JFAIM",
            "template_types": list(self.template_types.keys()),
            "jfa_api_config": self.jfa_api_config,
            "stats": self.stats.copy(),
            "processing_status": self.processing_status.copy()
        }
    
    def reset_stats(self):
        """Reset module statistics."""
        self.stats = {
            "total_jfa_requests": 0,
            "successful_processing": 0,
            "failed_processing": 0,
            "templates_processed": 0,
            "binary_files_generated": 0,
            "analyses_completed": 0,
            "api_calls_made": 0,
            "api_errors": 0,
            "last_activity": None
        }
        self.processing_status.clear()
        self.logger.info("JFAIM: Statistics reset")
    
    async def start(self):
        """Start the JFAIM module."""
        try:
            # Test connection to JFA microservice
            status = await self.check_jfa_service_status()
            if status.get("success", False):
                self.logger.info("JFAIM: Successfully connected to JFA microservice")
            else:
                self.logger.warning("JFAIM: Could not connect to JFA microservice")
            
            self.logger.info("JFAIM: Module started")
        except Exception as e:
            self.logger.error(f"JFAIM: Error starting module: {e}")
    
    async def stop(self):
        """Stop the JFAIM module."""
        try:
            if self.session and not self.session.closed:
                await self.session.close()
            self.logger.info("JFAIM: Module stopped")
        except Exception as e:
            self.logger.error(f"JFAIM: Error stopping module: {e}")

    def log_error(self, error_message: str, class_name: str = "UnknownClass", function_name: str = "UnknownFunction", sub_function: str = "001"):
        """Log an error using EMM."""
        return self.error_manager.log_error_with_generation(
            "JFAIM", 
            class_name, 
            function_name, 
            error_message, 
            sub_function
        )

    def generate_error_code(self, class_name: str = "UnknownClass", function_name: str = "UnknownFunction", sub_function: str = "001") -> str:
        """Generate an error code using EMM."""
        return self.error_manager.generate_error_code("JFAIM", class_name, function_name, sub_function)

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
                "JFAIM",
                "JFAIM",
                "handle_api_error",
                f"API Error: {result.get('api_error_type', 'unknown')}",
                context=result
            )
            await api_error_handler.send_error_report_to_ccu(result)
            return result
        except Exception as e:
            self.error_manager.log_error_with_generation(
                "JFAIM",
                "JFAIM",
                "handle_api_error",
                f"Error handling API error: {str(e)}"
            )
            return {"success": False, "error": str(e)}


# Global instance and alias for compatibility
jfaim = JFAInteractionModule()
JFAIM = JFAInteractionModule  # Class alias 