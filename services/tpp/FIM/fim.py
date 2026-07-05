"""
File Interface Module (FIM) for TPP Microservice

This module handles file operations:
- File reading and writing
- JSON file processing
- Input/output file management
- File format validation
"""

import logging
import asyncio
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
import os


class FileInterfaceModule:
    """
    File Interface Module
    
    Handles file operations for TPP microservice.
    """
    
    def __init__(self):
        """Initialize the FIM module."""
        self.logger = logging.getLogger(__name__)
        self.module_name = "FIM"
        self.is_active = False
        
        # File operation statistics
        self.stats = {
            "files_read": 0,
            "files_written": 0,
            "total_bytes_read": 0,
            "total_bytes_written": 0,
            "last_activity": None
        }
        
        self.logger.info(f"{self.module_name} initialized successfully")
    
    async def start(self):
        """Start the FIM module."""
        try:
            self.is_active = True
            self.logger.info(f"{self.module_name} started successfully")
        except Exception as e:
            self.logger.error(f"Failed to start {self.module_name}: {e}")
            raise
    
    async def stop(self):
        """Stop the FIM module."""
        try:
            self.is_active = False
            self.logger.info(f"{self.module_name} stopped successfully")
        except Exception as e:
            self.logger.error(f"Failed to stop {self.module_name}: {e}")
            raise
    
    async def read_file(self, file_path: str) -> Dict[str, Any]:
        """Read file and return content."""
        try:
            path = Path(file_path)
            
            if not path.exists():
                return {"error": f"File not found: {file_path}"}
            
            with open(path, 'r', encoding='utf-8') as f:
                if path.suffix.lower() == '.json':
                    content = json.load(f)
                else:
                    content = {"message_text": f.read()}
            
            # Update statistics
            self.stats["files_read"] += 1
            self.stats["total_bytes_read"] += path.stat().st_size
            self.stats["last_activity"] = datetime.now()
            
            return content
            
        except Exception as e:
            self.logger.error(f"Error reading file {file_path}: {e}")
            return {"error": str(e)}
    
    async def write_file(self, file_path: str, data: Dict[str, Any]) -> bool:
        """Write data to file."""
        try:
            path = Path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(path, 'w', encoding='utf-8') as f:
                if path.suffix.lower() == '.json':
                    json.dump(data, f, ensure_ascii=False, indent=4)
                else:
                    f.write(str(data.get("message_text", "")))
            
            # Update statistics
            self.stats["files_written"] += 1
            self.stats["total_bytes_written"] += path.stat().st_size
            self.stats["last_activity"] = datetime.now()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error writing file {file_path}: {e}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status."""
        return {
            "module": self.module_name,
            "is_active": self.is_active,
            "statistics": self.stats,
            "timestamp": datetime.now().isoformat()
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        try:
            return {
                "healthy": self.is_active,
                "module": self.module_name,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "healthy": False,
                "module": self.module_name,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            } 