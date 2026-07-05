"""
Get Input Data and Verification Module (GIDVM)

Listens for incoming JSON request files from the TPP block, verifies data integrity, 
and stores them in priority-specific folders based on the priority flag.
"""

import json
import shutil
import logging
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, List
from datetime import datetime
import asyncio

# Import error management module
from EMM.emm import ErrorManagementModule
from EMM.api_error_handler import api_error_handler


class GetInputDataAndVerificationModule:
    """
    Get Input Data and Verification Module (GIDVM)
    
    Listens for incoming JSON request files from the TPP block, verifies data integrity, 
    and stores them in priority-specific folders based on the priority flag.
    """
    
    def __init__(self):
        """Initialize the GIDVM module."""
        self.processed_files = set()
        self.error_manager = ErrorManagementModule()
        self.logger = logging.getLogger(__name__)
        
        # Priority directories
        self.priority_dirs = {
            "A": Path("input/priority_a/"),
            "B": Path("input/priority_b/"),
            "C": Path("input/priority_c/"),
            "D": Path("input/priority_d/")
        }
        
        # Error codes will be generated dynamically by EMM
        
        # Ensure directories exist
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Ensure all priority directories exist."""
        for priority_dir in self.priority_dirs.values():
            priority_dir.mkdir(parents=True, exist_ok=True)
    
    def is_valid_json_file(self, file_path: Path) -> bool:
        """
        Check if a file is a valid JSON file for processing.
        
        Args:
            file_path: Path to the file to validate
            
        Returns:
            True if file is valid for processing, False otherwise
        """
        return (
            file_path.is_file() and
            file_path.suffix.lower() in [".json"] and
            file_path.name not in self.processed_files
        )
    
    def read_and_validate_json(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """
        Read and validate a JSON file.
        
        Args:
            file_path: Path to the JSON file to read
            
        Returns:
            Validated JSON data as dictionary, or None if validation fails
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Validate required fields
            if not isinstance(data, dict):
                error_msg = f"Invalid JSON structure in {file_path}: not a dictionary"
                self.error_manager.log_error_with_generation("GIDVM", "GetInputDataAndVerificationModule", "read_and_validate_json", error_msg, "001")
                return None
            
            if "priority_flag" not in data:
                error_msg = f"Missing priority_flag in {file_path}"
                self.error_manager.log_error_with_generation("GIDVM", "GetInputDataAndVerificationModule", "read_and_validate_json", error_msg, "002")
                return None
            
            priority = data["priority_flag"]
            if priority not in ["A", "B", "C", "D"]:
                error_msg = f"Invalid priority_flag '{priority}' in {file_path}"
                self.error_manager.log_error_with_generation("GIDVM", "GetInputDataAndVerificationModule", "read_and_validate_json", error_msg, "003")
                return None
            
            if "model" not in data:
                error_msg = f"Missing 'model' field in {file_path}"
                self.error_manager.log_error_with_generation("GIDVM", "GetInputDataAndVerificationModule", "read_and_validate_json", error_msg, "004")
                return None
            # Stricter: model must be a string
            if not isinstance(data["model"], str):
                error_msg = f"'model' field must be a string in {file_path}"
                self.error_manager.log_error_with_generation("GIDVM", "GetInputDataAndVerificationModule", "read_and_validate_json", error_msg, "008")
                return None
            
            if "messages" not in data:
                error_msg = f"Missing 'messages' field in {file_path}"
                self.error_manager.log_error_with_generation("GIDVM", "GetInputDataAndVerificationModule", "read_and_validate_json", error_msg, "005")
                return None
            # Stricter: messages must be a non-empty list of strings
            messages = data["messages"]
            if not isinstance(messages, list) or len(messages) == 0:
                error_msg = f"'messages' field must be a non-empty list in {file_path}"
                self.error_manager.log_error_with_generation("GIDVM", "GetInputDataAndVerificationModule", "read_and_validate_json", error_msg, "009")
                return None
            if not all(isinstance(m, str) for m in messages):
                error_msg = f"All elements of 'messages' must be strings in {file_path}"
                self.error_manager.log_error_with_generation("GIDVM", "GetInputDataAndVerificationModule", "read_and_validate_json", error_msg, "010")
                return None
            
            return data
            
        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON in {file_path}: {e}"
            self.error_manager.log_error_with_generation("GIDVM", "GetInputDataAndVerificationModule", "read_and_validate_json", error_msg, "006")
            return None
        except Exception as e:
            error_msg = f"Error reading {file_path}: {e}"
            self.error_manager.log_error_with_generation("GIDVM", "GetInputDataAndVerificationModule", "read_and_validate_json", error_msg, "007")
            return None
    
    def route_file_by_priority(self, file_path: Path, priority: str) -> bool:
        """
        Route the file to the appropriate priority directory.
        
        Args:
            file_path: Path to the file to route
            priority: Priority level (A, B, C, D)
            
        Returns:
            True if routing successful, False otherwise
        """
        try:
            priority_dir = self.priority_dirs[priority]
            destination = priority_dir / file_path.name
            
            # Copy the file to the priority directory
            shutil.copy2(file_path, destination)
            self.logger.info(f"Routed {file_path.name} to {destination}")
            return True
            
        except Exception as e:
            error_msg = f"Error routing {file_path} to priority {priority}: {e}"
            self.error_manager.log_error_with_generation("GIDVM", "GetInputDataAndVerificationModule", "route_file_by_priority", error_msg)
            return False
    
    async def process_file(self, file_path: Path) -> Optional[Tuple[Path, str]]:
        """
        Process a single JSON file.
        
        Args:
            file_path: Path to the JSON file to process
            
        Returns:
            Tuple of (routed_file_path, priority) if successful, None otherwise
        """
        if not self.is_valid_json_file(file_path):
            return None
        
        # Read and validate the JSON
        data = self.read_and_validate_json(file_path)
        if data is None:
            return None
        
        priority = data["priority_flag"]
        
        # Route the file to priority directory
        if not self.route_file_by_priority(file_path, priority):
            return None
        
        # Mark as processed
        self.processed_files.add(file_path.name)
        
        self.logger.info(f"Successfully processed {file_path.name} (Priority: {priority})")
        return self.priority_dirs[priority] / file_path.name, priority
    
    async def get_pending_files(self, input_directory: Path) -> List[Path]:
        """
        Get list of pending files to process.
        
        Args:
            input_directory: Directory to scan for files
            
        Returns:
            List of pending file paths
        """
        pending_files = []
        
        if not input_directory.exists():
            return pending_files
        
        for file_path in input_directory.iterdir():
            if self.is_valid_json_file(file_path):
                pending_files.append(file_path)
        
        return sorted(pending_files)  # Sort for consistent processing order
    
    async def cleanup_processed_files(self, max_age_hours: int = 24):
        """
        Clean up processed files older than specified age.
        
        Args:
            max_age_hours: Maximum age in hours before cleanup
        """
        cutoff_time = datetime.now().timestamp() - (max_age_hours * 3600)
        
        for priority_dir in self.priority_dirs.values():
            if not priority_dir.exists():
                continue
            
            for file_path in priority_dir.iterdir():
                if file_path.is_file():
                    try:
                        if file_path.stat().st_mtime < cutoff_time:
                            file_path.unlink()
                            self.logger.info(f"Cleaned up old file: {file_path}")
                    except Exception as e:
                        self.logger.warning(f"Could not clean up {file_path}: {e}")
    
    async def get_status(self) -> Dict[str, Any]:
        """
        Get the status of the GIDVM module.
        
        Returns:
            Dictionary containing module status information
        """
        return {
            "status": "active",
            "processed_files_count": len(self.processed_files),
            "priority_directories": {
                priority: str(dir_path) for priority, dir_path in self.priority_dirs.items()
            },
            "last_activity": datetime.now().isoformat()
        }
    
    async def start(self):
        """Start the GIDVM module."""
        self.logger.info("GIDVM module started")
    
    async def stop(self):
        """Stop the GIDVM module."""
        self.logger.info("GIDVM module stopped") 
    def log_error(self, error_message: str, class_name: str = "UnknownClass", function_name: str = "UnknownFunction", sub_function: str = "001"):
        """Log an error using EMM."""
        return self.error_manager.log_error_with_generation(
            "GIDVM", 
            class_name, 
            function_name, 
            error_message, 
            sub_function
        )
    
    def generate_error_code(self, class_name: str = "UnknownClass", function_name: str = "UnknownFunction", sub_function: str = "001") -> str:
        """Generate an error code using EMM."""
        return self.error_manager.generate_error_code("GIDVM", class_name, function_name, sub_function)
    
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
                "GIDVM",
                "GIDVM",
                "handle_api_error",
                f"API Error: {result.get('api_error_type', 'unknown')}",
                context=result
            )
            await api_error_handler.send_error_report_to_ccu(result)
            return result
        except Exception as e:
            self.error_manager.log_error_with_generation(
                "GIDVM",
                "GIDVM",
                "handle_api_error",
                f"Error handling API error: {str(e)}"
            )
            return {"success": False, "error": str(e)}


# Global instance and alias for compatibility
gidvm = GetInputDataAndVerificationModule()
GIDVM = GetInputDataAndVerificationModule  # Class alias
