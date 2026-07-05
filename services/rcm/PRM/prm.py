"""
Priority Routing Module (PRM)

Routes incoming files to the appropriate processing queue or folder based on the priority_flag (A, B, C, D).
"""

import asyncio
import logging
import json
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import re

# Import error management module
from EMM.emm import ErrorManagementModule
from EMM.api_error_handler import api_error_handler


class PriorityRouter:
    """Routes files based on priority information."""
    
    def __init__(self, priority_directories: Dict[str, Path]):
        self.priority_directories = priority_directories
        self.priority_patterns = {
            "A": r"priority[_-]?a",
            "B": r"priority[_-]?b", 
            "C": r"priority[_-]?c",
            "D": r"priority[_-]?d"
        }
    
    def extract_priority_from_filename(self, filename: str) -> Optional[str]:
        """
        Extract priority from filename patterns.
        
        Args:
            filename: Name of the file
            
        Returns:
            Priority letter (A, B, C, D) or None
        """
        filename_lower = filename.lower()
        
        for priority, pattern in self.priority_patterns.items():
            if re.search(pattern, filename_lower):
                return priority
        
        return None
    
    def extract_priority_from_content(self, content: Dict[str, Any]) -> Optional[str]:
        """
        Extract priority from file content.
        
        Args:
            content: JSON content of the file
            
        Returns:
            Priority letter (A, B, C, D) or None
        """
        # Check for priority_flag field
        if "priority_flag" in content:
            priority = content["priority_flag"].upper()
            if priority in ["A", "B", "C", "D"]:
                return priority
        
        # Check for priority field
        if "priority" in content:
            priority = content["priority"].upper()
            if priority in ["A", "B", "C", "D"]:
                return priority
        
        # Check for urgency field
        if "urgency" in content:
            urgency = content["urgency"].lower()
            urgency_mapping = {
                "high": "A",
                "medium": "B", 
                "low": "C",
                "background": "D"
            }
            if urgency in urgency_mapping:
                return urgency_mapping[urgency]
        
        return None


class PriorityRoutingModule:
    """
    Priority Routing Module (PRM)
    
    Routes incoming files to the appropriate processing queue or folder based on the priority_flag.
    """
    
    def __init__(self):
        """Initialize the PRM module."""
        self.logger = logging.getLogger(__name__)
        self.error_manager = ErrorManagementModule()
        
        # Priority directories
        self.priority_directories = {
            "A": Path("input/priority_a/"),
            "B": Path("input/priority_b/"),
            "C": Path("input/priority_c/"),
            "D": Path("input/priority_d/")
        }
        
        # Default priority if none found
        self.default_priority = "C"
        
        # Router instance
        self.router = PriorityRouter(self.priority_directories)
        
        # Routing statistics
        self.stats = {
            "files_routed": 0,
            "files_failed": 0,
            "priority_breakdown": {"A": 0, "B": 0, "C": 0, "D": 0},
            "last_activity": None
        }
        
        # Ensure directories exist
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Ensure all priority directories exist."""
        for directory in self.priority_directories.values():
            directory.mkdir(parents=True, exist_ok=True)
    
    async def route_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """
        Route a file to the appropriate priority directory.
        
        Args:
            file_path: Path to the file to route
            
        Returns:
            Routing result or None if failed
        """
        try:
            self.logger.info(f"Routing file: {file_path}")
            
            # Check if file exists
            if not file_path.exists():
                raise FileNotFoundError(f"File {file_path} not found")
            
            # Read and parse JSON content
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = json.load(f)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON in {file_path}: {e}")
            
            # Determine priority
            priority = await self._determine_priority(file_path, content)
            
            # Route to appropriate directory
            result = await self._route_to_directory(file_path, priority)
            
            # Update statistics
            self.stats["files_routed"] += 1
            self.stats["priority_breakdown"][priority] += 1
            self.stats["last_activity"] = datetime.now().isoformat()
            
            self.logger.info(f"Successfully routed {file_path.name} to priority {priority}")
            return result
            
        except Exception as e:
            error_msg = f"Error routing file {file_path}: {e}"
            self.log_error(error_msg, "PriorityRoutingModule", "route_file")
            self.stats["files_failed"] += 1
            return None
    
    async def _determine_priority(self, file_path: Path, content: Dict[str, Any]) -> str:
        """
        Determine the priority for a file.
        
        Args:
            file_path: Path to the file
            content: JSON content of the file
            
        Returns:
            Priority letter (A, B, C, D)
        """
        # First, try to extract from content
        priority = self.router.extract_priority_from_content(content)
        if priority:
            return priority
        
        # Then, try to extract from filename
        priority = self.router.extract_priority_from_filename(file_path.name)
        if priority:
            return priority
        
        # If no priority found, use default
        self.logger.warning(f"No priority found for {file_path.name}, using default: {self.default_priority}")
        return self.default_priority
    
    async def _route_to_directory(self, file_path: Path, priority: str) -> Dict[str, Any]:
        """
        Route file to the appropriate priority directory.
        
        Args:
            file_path: Path to the file
            priority: Priority letter (A, B, C, D)
            
        Returns:
            Routing result
        """
        if priority not in self.priority_directories:
            raise ValueError(f"Invalid priority: {priority}")
        
        target_directory = self.priority_directories[priority]
        
        # Ensure target directory exists
        target_directory.mkdir(parents=True, exist_ok=True)
        
        # Create target path
        target_path = target_directory / file_path.name
        
        # Handle filename conflicts
        counter = 1
        original_target_path = target_path
        while target_path.exists():
            stem = original_target_path.stem
            suffix = original_target_path.suffix
            target_path = target_directory / f"{stem}_{counter}{suffix}"
            counter += 1
        
        # Move file to target directory
        try:
            shutil.move(str(file_path), str(target_path))
        except Exception as e:
            raise RuntimeError(f"Failed to move file to {target_path}: {e}")
        
        return {
            "original_path": str(file_path),
            "target_path": str(target_path),
            "priority": priority,
            "timestamp": datetime.now().isoformat()
        }
    
    async def route_multiple_files(self, file_paths: List[Path]) -> Dict[str, Any]:
        """
        Route multiple files at once.
        
        Args:
            file_paths: List of file paths to route
            
        Returns:
            Summary of routing results
        """
        results = {
            "successful": [],
            "failed": [],
            "summary": {
                "total": len(file_paths),
                "successful": 0,
                "failed": 0,
                "priority_breakdown": {"A": 0, "B": 0, "C": 0, "D": 0}
            }
        }
        
        for file_path in file_paths:
            try:
                result = await self.route_file(file_path)
                if result:
                    results["successful"].append(result)
                    results["summary"]["successful"] += 1
                    results["summary"]["priority_breakdown"][result["priority"]] += 1
                else:
                    results["failed"].append(str(file_path))
                    results["summary"]["failed"] += 1
            except Exception as e:
                results["failed"].append(str(file_path))
                results["summary"]["failed"] += 1
                self.logger.error(f"Failed to route {file_path}: {e}")
        
        return results
    
    async def get_priority_queue_status(self) -> Dict[str, Any]:
        """
        Get status of priority queues.
        
        Returns:
            Dictionary with queue status information
        """
        queue_status = {}
        
        for priority, directory in self.priority_directories.items():
            try:
                if directory.exists():
                    file_count = len(list(directory.glob("*.json")))
                    queue_status[priority] = {
                        "directory": str(directory),
                        "file_count": file_count,
                        "exists": True
                    }
                else:
                    queue_status[priority] = {
                        "directory": str(directory),
                        "file_count": 0,
                        "exists": False
                    }
            except Exception as e:
                queue_status[priority] = {
                    "directory": str(directory),
                    "file_count": 0,
                    "exists": False,
                    "error": str(e)
                }
        
        return queue_status
    
    async def cleanup_empty_queues(self) -> Dict[str, int]:
        """
        Clean up empty priority queues.
        
        Returns:
            Dictionary with cleanup statistics
        """
        cleanup_stats = {"directories_cleaned": 0, "errors": 0}
        
        for priority, directory in self.priority_directories.items():
            try:
                if directory.exists():
                    # Check if directory is empty (only .gitkeep files allowed)
                    files = list(directory.glob("*"))
                    non_gitkeep_files = [f for f in files if f.name != ".gitkeep"]
                    
                    if not non_gitkeep_files:
                        # Directory is effectively empty
                        self.logger.debug(f"Priority {priority} directory is empty")
                        cleanup_stats["directories_cleaned"] += 1
            except Exception as e:
                self.logger.warning(f"Error checking directory {directory}: {e}")
                cleanup_stats["errors"] += 1
        
        return cleanup_stats
    
    async def get_status(self) -> Dict[str, Any]:
        """
        Get the status of the PRM module.
        
        Returns:
            Dictionary containing module status information
        """
        queue_status = await self.get_priority_queue_status()
        
        return {
            "status": "active",
            "statistics": self.stats,
            "priority_queues": queue_status,
            "default_priority": self.default_priority,
            "last_activity": datetime.now().isoformat()
        }
    
    async def start(self):
        """Start the PRM module."""
        self.logger.info("PRM module started")
    
    async def stop(self):
        """Stop the PRM module."""
        self.logger.info("PRM module stopped") 

    def log_error(self, error_message: str, class_name: str = "UnknownClass", function_name: str = "UnknownFunction", sub_function: str = "001"):
        """Log an error using EMM."""
        return self.error_manager.log_error_with_generation(
            "PRM", 
            class_name, 
            function_name, 
            error_message, 
            sub_function
        )

    def generate_error_code(self, class_name: str = "UnknownClass", function_name: str = "UnknownFunction", sub_function: str = "001") -> str:
        """Generate an error code using EMM."""
        return self.error_manager.generate_error_code("PRM", class_name, function_name, sub_function)

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
                "PRM",
                "PRM",
                "handle_api_error",
                f"API Error: {result.get('api_error_type', 'unknown')}",
                context=result
            )
            await api_error_handler.send_error_report_to_ccu(result)
            return result
        except Exception as e:
            self.error_manager.log_error_with_generation(
                "PRM",
                "PRM",
                "handle_api_error",
                f"Error handling API error: {str(e)}"
            )
            return {"success": False, "error": str(e)} 

# Global instance and alias for compatibility
prm = PriorityRoutingModule()
PRM = PriorityRoutingModule  # Class alias 