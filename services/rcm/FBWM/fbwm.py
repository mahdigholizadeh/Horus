"""
File-based Workflow Module (FBWM)

Processes JSON request files, including automatic routing to the correct internal workflow 
and cleaning up temporary files after processing.
"""

import asyncio
import logging
import json
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import tempfile

from EMM.emm import ErrorManagementModule
from EMM.api_error_handler import api_error_handler


class FileWorkflow:
    """Represents a file workflow with processing state."""
    
    def __init__(self, file_path: Path, request_id: str):
        self.file_path = file_path
        self.request_id = request_id
        self.status = "pending"
        self.start_time = None
        self.end_time = None
        self.error = None
        self.temp_files = []
    
    def start_processing(self):
        """Mark workflow as started."""
        self.status = "processing"
        self.start_time = datetime.now()
    
    def complete_processing(self):
        """Mark workflow as completed."""
        self.status = "completed"
        self.end_time = datetime.now()
    
    def fail_processing(self, error: str):
        """Mark workflow as failed."""
        self.status = "failed"
        self.end_time = datetime.now()
        self.error = error
    
    def add_temp_file(self, temp_path: Path):
        """Add a temporary file to track for cleanup."""
        self.temp_files.append(temp_path)


    def log_error(self, error_message: str, class_name: str = "UnknownClass", function_name: str = "UnknownFunction", sub_function: str = "001"):
        """Log an error using EMM."""
        return self.error_manager.log_error_with_generation(
            "FBWM", 
            class_name, 
            function_name, 
            error_message, 
            sub_function
        )
    
    def generate_error_code(self, class_name: str = "UnknownClass", function_name: str = "UnknownFunction", sub_function: str = "001") -> str:
        """Generate an error code using EMM."""
        return self.error_manager.generate_error_code("FBWM", class_name, function_name, sub_function)
    
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

    async def handle_api_error(self, error_response: str, status_code: int = None, context: dict = None) -> dict:
        """Handle API errors using the centralized API error handler."""
        try:
            result = await api_error_handler.handle_api_error(error_response, status_code, context)
            self.error_manager.log_error_with_generation(
                "FBWM",
                "FBWM",
                "handle_api_error",
                f"API Error: {result.get('api_error_type', 'unknown')}",
                context=result
            )
            await api_error_handler.send_error_report_to_ccu(result)
            return result
        except Exception as e:
            self.error_manager.log_error_with_generation(
                "FBWM",
                "FBWM",
                "handle_api_error",
                f"Error handling API error: {str(e)}"
            )
            return {"success": False, "error": str(e)}


class FileBasedWorkflowModule:
    """
    File-based Workflow Module (FBWM)
    
    Processes JSON request files, including automatic routing and cleanup.
    """
    
    def __init__(self):
        """Initialize the FBWM module."""
        self.logger = logging.getLogger(__name__)
        self.error_manager = ErrorManagementModule()
        
        # Directory structure
        self.input_dir = Path("input/")
        self.output_dir = Path("output/")
        self.temp_dir = Path("temp/")
        self.error_dir = Path("error/")
        self.archive_dir = Path("archive/")
        
        # Workflow tracking
        self.active_workflows = {}
        self.completed_workflows = {}
        self.failed_workflows = {}
        
        # Error codes for this module (Module code: 04 for FBWM)
        # Error codes now generated dynamically by EMM
        
        # File retention settings
        self.temp_file_retention_hours = 24
        self.archive_retention_days = 7
        
        # Ensure directories exist
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Ensure all required directories exist."""
        for directory in [self.input_dir, self.output_dir, self.temp_dir, 
                         self.error_dir, self.archive_dir]:
            directory.mkdir(parents=True, exist_ok=True)
    
    async def process_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """
        Process a single JSON file through the workflow.
        
        Args:
            file_path: Path to the JSON file to process
            
        Returns:
            Processing result or None if failed
        """
        request_id = file_path.stem
        
        # Create workflow
        workflow = FileWorkflow(file_path, request_id)
        self.active_workflows[request_id] = workflow
        
        try:
            self.logger.info(f"Starting workflow for file {file_path.name}")
            workflow.start_processing()
            
            # Validate file exists
            if not file_path.exists():
                raise FileNotFoundError(f"File {file_path} not found")
            
            # Read and validate JSON
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON in {file_path}: {e}")
            
            # Extract request information
            request_data = await self._extract_request_data(data)
            
            # Route to appropriate workflow
            routing_result = await self._route_request(request_data)
            
            # Process the request
            processing_result = await self._process_request(request_data, routing_result)
            
            # Clean up temporary files
            await self._cleanup_temp_files(workflow)
            
            # Archive original file
            await self._archive_file(file_path)
            
            # Mark as completed
            workflow.complete_processing()
            self.completed_workflows[request_id] = workflow
            
            self.logger.info(f"Workflow completed for {file_path.name}")
            return processing_result
            
        except Exception as e:
            error_msg = f"Error processing file {file_path.name}: {e}"
            self.error_manager.log_error_with_generation("FBWM", "UnknownClass", "UnknownFunction", error_msg)
            
            workflow.fail_processing(str(e))
            self.failed_workflows[request_id] = workflow
            
            # Move to error directory
            await self._move_to_error_directory(file_path)
            
            return None
        
        finally:
            # Remove from active workflows
            if request_id in self.active_workflows:
                del self.active_workflows[request_id]
    
    async def _extract_request_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract and validate request data from JSON.
        
        Args:
            data: JSON data from file
            
        Returns:
            Extracted request data
        """
        required_fields = ["request_ID", "priority_flag", "messages"]
        
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")
        
        return {
            "request_id": data["request_ID"],
            "priority": data["priority_flag"],
            "messages": data["messages"],
            "attempts_number": data.get("attempts_number", 1),
            "model": data.get("model", "gpt-4.1-nano"),
            "api_key": data.get("api_key"),
            "temperature": data.get("temperature", 0.7),
            "max_tokens": data.get("max_tokens", 1000)
        }
    
    async def _route_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Route request to appropriate workflow based on content.
        
        Args:
            request_data: Extracted request data
            
        Returns:
            Routing information
        """
        priority = request_data["priority"]
        messages = request_data["messages"]
        
        # Determine workflow type based on content
        workflow_type = "standard"
        
        # Check if this is a template fulfillment request
        if any("template" in msg.get("content", "").lower() for msg in messages):
            workflow_type = "template_fulfillment"
        
        # Check if this is an agent request
        if any("agent" in msg.get("content", "").lower() for msg in messages):
            workflow_type = "agent"
        
        # Check if this is a special model request
        if request_data.get("model") and "special" in request_data["model"].lower():
            workflow_type = "special"
        
        return {
            "workflow_type": workflow_type,
            "priority": priority,
            "target_module": self._get_target_module(workflow_type)
        }
    
    def _get_target_module(self, workflow_type: str) -> str:
        """
        Get target module based on workflow type.
        
        Args:
            workflow_type: Type of workflow
            
        Returns:
            Target module name
        """
        module_mapping = {
            "standard": "BAAIM",
            "template_fulfillment": "JFAIM",
            "agent": "AAAIM",
            "special": "SAAIM"
        }
        
        return module_mapping.get(workflow_type, "BAAIM")
    
    async def _process_request(self, request_data: Dict[str, Any], routing: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process the request through the appropriate module.
        
        Args:
            request_data: Request data
            routing: Routing information
            
        Returns:
            Processing result
        """
        # This would integrate with other modules
        # For now, return a mock result
        return {
            "request_id": request_data["request_id"],
            "workflow_type": routing["workflow_type"],
            "target_module": routing["target_module"],
            "status": "processed",
            "timestamp": datetime.now().isoformat()
        }
    
    async def _cleanup_temp_files(self, workflow: FileWorkflow):
        """
        Clean up temporary files for a workflow.
        
        Args:
            workflow: Workflow object
        """
        for temp_file in workflow.temp_files:
            try:
                if temp_file.exists():
                    temp_file.unlink()
                    self.logger.debug(f"Cleaned up temp file: {temp_file}")
            except Exception as e:
                self.logger.warning(f"Failed to clean up temp file {temp_file}: {e}")
    
    async def _archive_file(self, file_path: Path):
        """
        Archive the original file after processing.
        
        Args:
            file_path: Path to the file to archive
        """
        try:
            archive_path = self.archive_dir / f"{file_path.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            shutil.move(str(file_path), str(archive_path))
            self.logger.debug(f"Archived file: {file_path} -> {archive_path}")
        except Exception as e:
            self.logger.warning(f"Failed to archive file {file_path}: {e}")
    
    async def _move_to_error_directory(self, file_path: Path):
        """
        Move failed file to error directory.
        
        Args:
            file_path: Path to the failed file
        """
        try:
            error_path = self.error_dir / file_path.name
            shutil.move(str(file_path), str(error_path))
            self.logger.debug(f"Moved failed file to error directory: {error_path}")
        except Exception as e:
            self.logger.warning(f"Failed to move file to error directory: {e}")
    
    async def cleanup_old_files(self):
        """Clean up old temporary and archived files."""
        now = datetime.now()
        
        # Clean up old temp files
        temp_retention = timedelta(hours=self.temp_file_retention_hours)
        for temp_file in self.temp_dir.glob("*"):
            if temp_file.is_file():
                file_age = now - datetime.fromtimestamp(temp_file.stat().st_mtime)
                if file_age > temp_retention:
                    try:
                        temp_file.unlink()
                        self.logger.debug(f"Cleaned up old temp file: {temp_file}")
                    except Exception as e:
                        self.logger.warning(f"Failed to clean up old temp file {temp_file}: {e}")
        
        # Clean up old archived files
        archive_retention = timedelta(days=self.archive_retention_days)
        for archive_file in self.archive_dir.glob("*"):
            if archive_file.is_file():
                file_age = now - datetime.fromtimestamp(archive_file.stat().st_mtime)
                if file_age > archive_retention:
                    try:
                        archive_file.unlink()
                        self.logger.debug(f"Cleaned up old archive file: {archive_file}")
                    except Exception as e:
                        self.logger.warning(f"Failed to clean up old archive file {archive_file}: {e}")
    
    async def get_status(self) -> Dict[str, Any]:
        """
        Get the status of the FBWM module.
        
        Returns:
            Dictionary containing module status information
        """
        return {
            "status": "active",
            "active_workflows": len(self.active_workflows),
            "completed_workflows": len(self.completed_workflows),
            "failed_workflows": len(self.failed_workflows),
            "directories": {
                "input": str(self.input_dir),
                "output": str(self.output_dir),
                "temp": str(self.temp_dir),
                "error": str(self.error_dir),
                "archive": str(self.archive_dir)
            },
            "last_activity": datetime.now().isoformat()
        }
    
    async def get_workflow_status(self, request_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the status of a specific workflow.
        
        Args:
            request_id: Request identifier
            
        Returns:
            Workflow status or None if not found
        """
        if request_id in self.active_workflows:
            workflow = self.active_workflows[request_id]
            return {
                "status": workflow.status,
                "start_time": workflow.start_time.isoformat() if workflow.start_time else None,
                "file_path": str(workflow.file_path)
            }
        elif request_id in self.completed_workflows:
            workflow = self.completed_workflows[request_id]
            return {
                "status": workflow.status,
                "start_time": workflow.start_time.isoformat() if workflow.start_time else None,
                "end_time": workflow.end_time.isoformat() if workflow.end_time else None,
                "file_path": str(workflow.file_path)
            }
        elif request_id in self.failed_workflows:
            workflow = self.failed_workflows[request_id]
            return {
                "status": workflow.status,
                "start_time": workflow.start_time.isoformat() if workflow.start_time else None,
                "end_time": workflow.end_time.isoformat() if workflow.end_time else None,
                "error": workflow.error,
                "file_path": str(workflow.file_path)
            }
        
        return None
    
    async def start(self):
        """Start the FBWM module."""
        self.logger.info("FBWM module started")
    
    async def stop(self):
        """Stop the FBWM module."""
        self.logger.info("FBWM module stopped") 

# Global instance and alias for compatibility
fbwm = FileBasedWorkflowModule()
FBWM = FileBasedWorkflowModule  # Class alias 