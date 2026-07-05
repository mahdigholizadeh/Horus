"""
File Output Module (FOM)

Handles saving processed responses and error logs to appropriate output directories.
Manages file organization, naming conventions, and output directory structure.
"""

import os
import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
# Import error management module
from EMM.emm import ErrorManagementModule
from EMM.api_error_handler import api_error_handler

class FileOutputModule:
    """
    File Output Module (FOM)
    
    Responsibilities:
    - Saves processed responses to appropriate output directories
    - Manages error logs and debug information
    - Organizes files by priority, timestamp, and type
    - Ensures proper file naming and directory structure
    - Handles file backup and cleanup operations
    """
    MODULE_CODE = "13"  # Unique code for FOM
    
    def __init__(self, base_output_dir: str = "RCM_RESPONSE_OUTPUT", logger: Optional[logging.Logger] = None):
        """
        Initialize the File Output Module.
        
        Args:
            base_output_dir: Base directory for all output files
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
        self.error_manager = ErrorManagementModule()
        self.base_output_dir = Path(base_output_dir)
        
        # Create directory structure
        self.directories = {
            "responses": self.base_output_dir / "responses",
            "errors": self.base_output_dir / "errors",
            "logs": self.base_output_dir / "logs",
            "debug": self.base_output_dir / "debug",
            "temp": self.base_output_dir / "temp"
        }
        
        # Error codes for this module
        
        # Statistics
        self.stats = {
            "files_written": 0,
            "files_read": 0,
            "files_deleted": 0,
            "errors_logged": 0,
            "total_bytes_written": 0
        }
        
        # Initialize directories
        self._create_directories()
    
    def _create_directories(self):
        """Create all necessary output directories."""
        try:
            for dir_name, dir_path in self.directories.items():
                dir_path.mkdir(parents=True, exist_ok=True)
                self.logger.info(f"FOM: Created directory {dir_path}")
        except Exception as e:
            error_msg = f"Failed to create directories: {e}"
            self.logger.error(error_msg)
            self.log_error(error_msg, "FileOutputModule", "_create_directories")
    
    def save_response(self, response_data: Dict[str, Any], request_id: str, 
                     priority: str = "D", timestamp: Optional[str] = None) -> str:
        """
        Save a processed response to the appropriate output directory.
        
        Args:
            response_data: The response data to save
            request_id: Unique identifier for the request
            priority: Priority level (A, B, C, D)
            timestamp: Optional timestamp (defaults to current time)
            
        Returns:
            Path to the saved file
        """
        try:
            # Generate timestamp if not provided
            if not timestamp:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Create filename
            filename = f"response_{priority}_{request_id}_{timestamp}.json"
            file_path = self.directories["responses"] / filename
            
            # Save the response
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(response_data, f, ensure_ascii=False, indent=2)
            
            # Update statistics
            self.stats["files_written"] += 1
            self.stats["total_bytes_written"] += file_path.stat().st_size
            
            self.logger.info(f"FOM: Saved response to {file_path}")
            return str(file_path)
            
        except Exception as e:
            error_msg = f"Failed to save response for request {request_id}: {e}"
            self.logger.error(error_msg)
            self.log_error(error_msg, "FileOutputModule", "save_response")
            return ""
    
    def save_error_log(self, error_data: Dict[str, Any], request_id: str, 
                      error_type: str = "general") -> str:
        """
        Save error information to the errors directory.
        
        Args:
            error_data: Error information to save
            request_id: Associated request ID
            error_type: Type of error (general, validation, api, etc.)
            
        Returns:
            Path to the saved error file
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"error_{error_type}_{request_id}_{timestamp}.json"
            file_path = self.directories["errors"] / filename
            
            # Add metadata to error data
            error_data["metadata"] = {
                "request_id": request_id,
                "error_type": error_type,
                "timestamp": timestamp,
                "module": "FOM"
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(error_data, f, ensure_ascii=False, indent=2)
            
            self.stats["files_written"] += 1
            self.stats["errors_logged"] += 1
            
            self.logger.info(f"FOM: Saved error log to {file_path}")
            return str(file_path)
            
        except Exception as e:
            error_msg = f"Failed to save error log for request {request_id}: {e}"
            self.logger.error(error_msg)
            self.log_error(error_msg, "FileOutputModule", "save_error_log")
            return ""
    
    def save_debug_info(self, debug_data: Dict[str, Any], request_id: str, 
                       debug_type: str = "general") -> str:
        """
        Save debug information to the debug directory.
        
        Args:
            debug_data: Debug information to save
            request_id: Associated request ID
            debug_type: Type of debug info (performance, validation, etc.)
            
        Returns:
            Path to the saved debug file
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"debug_{debug_type}_{request_id}_{timestamp}.json"
            file_path = self.directories["debug"] / filename
            
            # Add metadata
            debug_data["metadata"] = {
                "request_id": request_id,
                "debug_type": debug_type,
                "timestamp": timestamp,
                "module": "FOM"
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(debug_data, f, ensure_ascii=False, indent=2)
            
            self.stats["files_written"] += 1
            
            self.logger.info(f"FOM: Saved debug info to {file_path}")
            return str(file_path)
            
        except Exception as e:
            error_msg = f"Failed to save debug info for request {request_id}: {e}"
            self.logger.error(error_msg)
            self.log_error(error_msg, "FileOutputModule", "save_debug_info")
            return ""
    
    def read_response(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Read a response file and return its contents.
        
        Args:
            file_path: Path to the response file
            
        Returns:
            Response data or None if failed
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.stats["files_read"] += 1
            self.logger.info(f"FOM: Read response from {file_path}")
            return data
            
        except Exception as e:
            error_msg = f"Failed to read response from {file_path}: {e}"
            self.logger.error(error_msg)
            self.log_error(error_msg, "FileOutputModule", "read_response")
            return None
    
    def list_responses(self, priority: Optional[str] = None, 
                      limit: int = 100) -> List[Dict[str, Any]]:
        """
        List response files with optional filtering.
        
        Args:
            priority: Filter by priority (A, B, C, D)
            limit: Maximum number of files to return
            
        Returns:
            List of file information dictionaries
        """
        try:
            response_dir = self.directories["responses"]
            files = []
            
            for file_path in response_dir.glob("response_*.json"):
                if priority and not file_path.name.startswith(f"response_{priority}_"):
                    continue
                
                stat = file_path.stat()
                files.append({
                    "name": file_path.name,
                    "path": str(file_path),
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "priority": file_path.name.split("_")[1] if "_" in file_path.name else "unknown"
                })
            
            # Sort by modification time (newest first)
            files.sort(key=lambda x: x["modified"], reverse=True)
            
            return files[:limit]
            
        except Exception as e:
            error_msg = f"Failed to list responses: {e}"
            self.logger.error(error_msg)
            self.log_error(error_msg, "FileOutputModule", "list_responses")
            return []
    
    def delete_file(self, file_path: str) -> bool:
        """
        Delete a file from the output directories.
        
        Args:
            file_path: Path to the file to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            path = Path(file_path)
            if path.exists():
                path.unlink()
                self.stats["files_deleted"] += 1
                self.logger.info(f"FOM: Deleted file {file_path}")
                return True
            else:
                self.logger.warning(f"FOM: File {file_path} does not exist")
                return False
                
        except Exception as e:
            error_msg = f"Failed to delete file {file_path}: {e}"
            self.logger.error(error_msg)
            self.log_error(error_msg, "FileOutputModule", "delete_file")
            return False
    
    def cleanup_old_files(self, days_old: int = 30, 
                         file_types: Optional[List[str]] = None) -> int:
        """
        Clean up old files from output directories.
        
        Args:
            days_old: Delete files older than this many days
            file_types: List of file types to clean (responses, errors, debug, logs)
            
        Returns:
            Number of files deleted
        """
        try:
            if file_types is None:
                file_types = ["responses", "errors", "debug", "logs"]
            
            cutoff_time = datetime.now().timestamp() - (days_old * 24 * 3600)
            deleted_count = 0
            
            for file_type in file_types:
                if file_type in self.directories:
                    dir_path = self.directories[file_type]
                    for file_path in dir_path.glob("*.json"):
                        if file_path.stat().st_mtime < cutoff_time:
                            if self.delete_file(str(file_path)):
                                deleted_count += 1
            
            self.logger.info(f"FOM: Cleaned up {deleted_count} old files")
            return deleted_count
            
        except Exception as e:
            error_msg = f"Failed to cleanup old files: {e}"
            self.logger.error(error_msg)
            self.log_error(error_msg, "FileOutputModule", "cleanup_old_files")
            return 0
    
    def backup_directory(self, backup_dir: str) -> bool:
        """
        Create a backup of the output directory.
        
        Args:
            backup_dir: Path to the backup directory
            
        Returns:
            True if successful, False otherwise
        """
        try:
            backup_path = Path(backup_dir)
            backup_path.mkdir(parents=True, exist_ok=True)
            
            shutil.copytree(self.base_output_dir, backup_path / self.base_output_dir.name, 
                           dirs_exist_ok=True)
            
            self.logger.info(f"FOM: Created backup at {backup_path}")
            return True
            
        except Exception as e:
            error_msg = f"Failed to create backup: {e}"
            self.logger.error(error_msg)
            self.log_error(error_msg, "FileOutputModule", "backup_directory")
            return False
    
    def get_directory_info(self) -> Dict[str, Any]:
        """
        Get information about output directories.
        
        Returns:
            Dictionary with directory information
        """
        info = {}
        for dir_name, dir_path in self.directories.items():
            try:
                if dir_path.exists():
                    file_count = len(list(dir_path.glob("*.json")))
                    total_size = sum(f.stat().st_size for f in dir_path.glob("*.json"))
                    info[dir_name] = {
                        "path": str(dir_path),
                        "file_count": file_count,
                        "total_size": total_size,
                        "exists": True
                    }
                else:
                    info[dir_name] = {
                        "path": str(dir_path),
                        "file_count": 0,
                        "total_size": 0,
                        "exists": False
                    }
            except Exception as e:
                info[dir_name] = {
                    "path": str(dir_path),
                    "error": str(e),
                    "exists": False
                }
        
        return info
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the FOM module.
        
        Returns:
            Dictionary with module status information
        """
        return {
            "module": "FOM",
            "base_directory": str(self.base_output_dir),
            "directories": self.get_directory_info(),
            "stats": self.stats.copy()
        }
    
    def reset_stats(self):
        """Reset module statistics."""
        self.stats = {
            "files_written": 0,
            "files_read": 0,
            "files_deleted": 0,
            "errors_logged": 0,
            "total_bytes_written": 0
        }
        self.logger.info("FOM: Statistics reset")

    def log_error(self, error_message: str, class_name: str = "UnknownClass", function_name: str = "UnknownFunction", sub_function: str = "001"):
        """Log an error using EMM."""
        return self.error_manager.log_error_with_generation(
            "FOM", 
            class_name, 
            function_name, 
            error_message, 
            sub_function
        )

    def generate_error_code(self, class_name: str = "UnknownClass", function_name: str = "UnknownFunction", sub_function: str = "001") -> str:
        """Generate an error code using EMM."""
        return self.error_manager.generate_error_code("FOM", class_name, function_name, sub_function)

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
                "FOM",
                "FOM",
                "handle_api_error",
                f"API Error: {result.get('api_error_type', 'unknown')}",
                context=result
            )
            await api_error_handler.send_error_report_to_ccu(result)
            return result
        except Exception as e:
            self.error_manager.log_error_with_generation(
                "FOM",
                "FOM",
                "handle_api_error",
                f"Error handling API error: {str(e)}"
            )
            return {"success": False, "error": str(e)}


# Global instance and alias for compatibility
fom = FileOutputModule()
FOM = FileOutputModule  # Class alias 