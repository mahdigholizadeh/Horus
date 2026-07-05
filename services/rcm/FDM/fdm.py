"""
File Detection Module (FDM)

Actively monitors input directories for new JSON files to be processed.
"""

import asyncio
import logging
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
import time
import os

from EMM.emm import ErrorManagementModule
from EMM.api_error_handler import api_error_handler


class FileDetector:
    """Detects and tracks files in monitored directories."""
    
    def __init__(self, directory: Path, file_pattern: str = "*.json"):
        self.directory = directory
        self.file_pattern = file_pattern
        self.known_files = set()
        self.file_sizes = {}
        self.last_modified = {}
    
    def scan_for_new_files(self) -> List[Path]:
        """
        Scan directory for new files.
        
        Returns:
            List of new file paths
        """
        new_files = []
        
        if not self.directory.exists():
            return new_files
        
        for file_path in self.directory.glob(self.file_pattern):
            file_key = str(file_path)
            
            # Check if file is new or modified
            if file_key not in self.known_files:
                new_files.append(file_path)
                self.known_files.add(file_key)
                self.file_sizes[file_key] = file_path.stat().st_size
                self.last_modified[file_key] = file_path.stat().st_mtime
            else:
                # Check if file was modified
                current_size = file_path.stat().st_size
                current_mtime = file_path.stat().st_mtime
                
                if (current_size != self.file_sizes.get(file_key, 0) or 
                    current_mtime != self.last_modified.get(file_key, 0)):
                    new_files.append(file_path)
                    self.file_sizes[file_key] = current_size
                    self.last_modified[file_key] = current_mtime
        
        return new_files
    
    def get_file_info(self, file_path: Path) -> Dict[str, Any]:
        """
        Get information about a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            File information dictionary
        """
        try:
            stat = file_path.stat()
            return {
                "path": str(file_path),
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "created": datetime.fromtimestamp(stat.st_ctime).isoformat()
            }
        except Exception as e:
            return {"path": str(file_path), "error": str(e)}


    def log_error(self, error_message: str, class_name: str = "UnknownClass", function_name: str = "UnknownFunction", sub_function: str = "001"):
        """Log an error using EMM."""
        return self.error_manager.log_error_with_generation(
            "FDM", 
            class_name, 
            function_name, 
            error_message, 
            sub_function
        )
    
    def generate_error_code(self, class_name: str = "UnknownClass", function_name: str = "UnknownFunction", sub_function: str = "001") -> str:
        """Generate an error code using EMM."""
        return self.error_manager.generate_error_code("FDM", class_name, function_name, sub_function)
    
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

class FileDetectionModule:
    """
    File Detection Module (FDM)
    
    Actively monitors input directories for new JSON files to be processed.
    """
    
    def __init__(self):
        """Initialize the FDM module."""
        self.logger = logging.getLogger(__name__)
        self.error_manager = ErrorManagementModule()
        
        # Monitoring configuration
        self.scan_interval = 1.0  # seconds
        self.watch_directories = {
            "input": Path("input/"),
            "priority_a": Path("input/priority_a/"),
            "priority_b": Path("input/priority_b/"),
            "priority_c": Path("input/priority_c/"),
            "priority_d": Path("input/priority_d/")
        }
        
        # File detectors for each directory
        self.detectors = {}
        for name, directory in self.watch_directories.items():
            self.detectors[name] = FileDetector(directory)
        
        # Callback for new file detection
        self.new_file_callback = None
        
        # Monitoring state
        self.is_monitoring = False
        self.monitoring_task = None
        
        # Statistics
        self.stats = {
            "files_detected": 0,
            "files_processed": 0,
            "files_failed": 0,
            "last_scan": None
        }
        
        # Error codes for this module (Module code: 05 for FDM)
        # Error codes now generated dynamically by EMM
        
        # Ensure directories exist
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Ensure all monitored directories exist."""
        for directory in self.watch_directories.values():
            directory.mkdir(parents=True, exist_ok=True)
    
    def set_new_file_callback(self, callback: Callable[[Path, Dict[str, Any]], None]):
        """
        Set callback function for new file detection.
        
        Args:
            callback: Function to call when new file is detected
        """
        self.new_file_callback = callback
    
    async def start_monitoring(self):
        """Start monitoring for new files."""
        if self.is_monitoring:
            self.logger.warning("File monitoring is already active")
            return
        
        self.is_monitoring = True
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        self.logger.info("File monitoring started")
    
    async def stop_monitoring(self):
        """Stop monitoring for new files."""
        if not self.is_monitoring:
            return
        
        self.is_monitoring = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("File monitoring stopped")
    
    async def _monitoring_loop(self):
        """Main monitoring loop."""
        while self.is_monitoring:
            try:
                await self._scan_all_directories()
                await asyncio.sleep(self.scan_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                error_msg = f"Error in monitoring loop: {e}"
                self.error_manager.log_error_with_generation("FDM", "UnknownClass", "UnknownFunction", error_msg)
                await asyncio.sleep(5)  # Wait before retrying
    
    async def _scan_all_directories(self):
        """Scan all monitored directories for new files."""
        self.stats["last_scan"] = datetime.now().isoformat()
        
        for directory_name, detector in self.detectors.items():
            try:
                new_files = detector.scan_for_new_files()
                
                for file_path in new_files:
                    await self._handle_new_file(file_path, directory_name)
                    
            except Exception as e:
                error_msg = f"Error scanning directory {directory_name}: {e}"
                self.error_manager.log_error_with_generation("FDM", "UnknownClass", "UnknownFunction", error_msg)
    
    async def _handle_new_file(self, file_path: Path, directory_name: str):
        """
        Handle a newly detected file.
        
        Args:
            file_path: Path to the new file
            directory_name: Name of the directory where file was found
        """
        try:
            self.logger.info(f"New file detected: {file_path} in {directory_name}")
            self.stats["files_detected"] += 1
            
            # Get file information
            detector = self.detectors[directory_name]
            file_info = detector.get_file_info(file_path)
            
            # Validate file
            if await self._validate_file(file_path):
                self.stats["files_processed"] += 1
                
                # Call callback if set
                if self.new_file_callback:
                    await asyncio.create_task(
                        self._call_callback_safe(file_path, file_info)
                    )
                else:
                    self.logger.warning("No callback set for new file detection")
            else:
                self.stats["files_failed"] += 1
                
        except Exception as e:
            error_msg = f"Error handling new file {file_path}: {e}"
            self.error_manager.log_error_with_generation("FDM", "UnknownClass", "UnknownFunction", error_msg)
            self.stats["files_failed"] += 1
    
    async def _validate_file(self, file_path: Path) -> bool:
        """
        Validate a detected file.
        
        Args:
            file_path: Path to the file to validate
            
        Returns:
            True if file is valid, False otherwise
        """
        try:
            # Check if file exists and is readable
            if not file_path.exists():
                return False
            
            # Check if it's a JSON file
            if not file_path.suffix.lower() == '.json':
                return False
            
            # Try to read and parse JSON
            with open(file_path, 'r', encoding='utf-8') as f:
                json.load(f)
            
            return True
            
        except Exception as e:
            self.logger.warning(f"File validation failed for {file_path}: {e}")
            return False
    
    async def _call_callback_safe(self, file_path: Path, file_info: Dict[str, Any]):
        """
        Safely call the new file callback.
        
        Args:
            file_path: Path to the file
            file_info: File information
        """
        try:
            if self.new_file_callback:
                self.new_file_callback(file_path, file_info)
        except Exception as e:
            error_msg = f"Error in new file callback: {e}"
            self.error_manager.log_error_with_generation("FDM", "UnknownClass", "UnknownFunction", error_msg)
    
    async def scan_once(self) -> Dict[str, List[Path]]:
        """
        Perform a single scan of all directories.
        
        Returns:
            Dictionary mapping directory names to lists of new files
        """
        results = {}
        
        for directory_name, detector in self.detectors.items():
            try:
                new_files = detector.scan_for_new_files()
                results[directory_name] = new_files
                
                for file_path in new_files:
                    await self._handle_new_file(file_path, directory_name)
                    
            except Exception as e:
                error_msg = f"Error in single scan of {directory_name}: {e}"
                self.error_manager.log_error_with_generation("FDM", "UnknownClass", "UnknownFunction", error_msg)
                results[directory_name] = []
        
        return results
    
    async def get_directory_status(self, directory_name: str) -> Optional[Dict[str, Any]]:
        """
        Get status of a specific directory.
        
        Args:
            directory_name: Name of the directory
            
        Returns:
            Directory status or None if not found
        """
        if directory_name not in self.detectors:
            return None
        
        detector = self.detectors[directory_name]
        directory = detector.directory
        
        try:
            if not directory.exists():
                return {
                    "exists": False,
                    "path": str(directory),
                    "error": "Directory not found"
                }
            
            # Count files
            file_count = len(list(directory.glob("*.json")))
            
            return {
                "exists": True,
                "path": str(directory),
                "file_count": file_count,
                "known_files": len(detector.known_files),
                "last_scan": self.stats["last_scan"]
            }
            
        except Exception as e:
            return {
                "exists": False,
                "path": str(directory),
                "error": str(e)
            }
    
    async def get_status(self) -> Dict[str, Any]:
        """
        Get the status of the FDM module.
        
        Returns:
            Dictionary containing module status information
        """
        directory_statuses = {}
        for directory_name in self.detectors.keys():
            directory_statuses[directory_name] = await self.get_directory_status(directory_name)
        
        return {
            "status": "active" if self.is_monitoring else "inactive",
            "is_monitoring": self.is_monitoring,
            "scan_interval": self.scan_interval,
            "statistics": self.stats,
            "directories": directory_statuses,
            "last_activity": datetime.now().isoformat()
        }
    
    async def start(self):
        """Start the FDM module."""
        await self.start_monitoring()
        self.logger.info("FDM module started")
    
    async def stop(self):
        """Stop the FDM module."""
        await self.stop_monitoring()
        self.logger.info("FDM module stopped")

    def log_error(self, error_message: str, class_name: str = "UnknownClass", function_name: str = "UnknownFunction", sub_function: str = "001"):
        """Log an error using EMM."""
        return self.error_manager.log_error_with_generation(
            "FDM", 
            class_name, 
            function_name, 
            error_message, 
            sub_function
        )
    
    def generate_error_code(self, class_name: str = "UnknownClass", function_name: str = "UnknownFunction", sub_function: str = "001") -> str:
        """Generate an error code using EMM."""
        return self.error_manager.generate_error_code("FDM", class_name, function_name, sub_function)
    
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
                "FDM",
                "FDM",
                "handle_api_error",
                f"API Error: {result.get('api_error_type', 'unknown')}",
                context=result
            )
            await api_error_handler.send_error_report_to_ccu(result)
            return result
        except Exception as e:
            self.error_manager.log_error_with_generation(
                "FDM",
                "FDM",
                "handle_api_error",
                f"Error handling API error: {str(e)}"
            )
            return {"success": False, "error": str(e)}


# Global instance and alias for compatibility
fdm = FileDetectionModule()
FDM = FileDetectionModule  # Class alias 