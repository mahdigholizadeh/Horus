"""
File Interface Module (FIM) for JFA Microservice

This module handles file operations:
- File reading and writing
- Data persistence and retrieval
- File format handling
- Backup and recovery operations
"""

import logging
import asyncio
import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import aiofiles


class FileInterfaceModule:
    """File Interface Module for JFA"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.module_name = "FIM"
        self.is_active = False
        
        self.stats = {
            "files_read": 0,
            "files_written": 0,
            "total_operations": 0,
            "failed_operations": 0,
            "last_activity": None
        }
    
    async def start(self):
        self.is_active = True
        self.logger.info(f"{self.module_name} started successfully")
    
    async def stop(self):
        self.is_active = False
        self.logger.info(f"{self.module_name} stopped successfully")
    
    async def read_file(self, file_path: str) -> Dict[str, Any]:
        """Read file content."""
        try:
            self.stats["total_operations"] += 1
            
            path = Path(file_path)
            if not path.exists():
                return {"success": False, "error": f"File not found: {file_path}"}
            
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                content = await f.read()
            
            # Try to parse as JSON
            try:
                data = json.loads(content)
                content_type = "json"
            except json.JSONDecodeError:
                data = content
                content_type = "text"
            
            self.stats["files_read"] += 1
            self.stats["last_activity"] = datetime.now()
            
            return {
                "success": True,
                "data": data,
                "content_type": content_type,
                "file_size": path.stat().st_size,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error reading file {file_path}: {e}")
            self.stats["failed_operations"] += 1
            return {"success": False, "error": str(e)}
    
    async def write_file(self, file_path: str, data: Any) -> Dict[str, Any]:
        """Write data to file."""
        try:
            self.stats["total_operations"] += 1
            
            path = Path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            
            # Convert data to string
            if isinstance(data, (dict, list)):
                content = json.dumps(data, indent=2, ensure_ascii=False)
            else:
                content = str(data)
            
            async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
                await f.write(content)
            
            self.stats["files_written"] += 1
            self.stats["last_activity"] = datetime.now()
            
            return {
                "success": True,
                "file_path": file_path,
                "bytes_written": len(content),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error writing file {file_path}: {e}")
            self.stats["failed_operations"] += 1
            return {"success": False, "error": str(e)}
    
    async def write_binary_file(self, file_path: str, data: bytes) -> Dict[str, Any]:
        """Write binary data to file."""
        try:
            self.stats["total_operations"] += 1
            
            path = Path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(data)
            
            self.stats["files_written"] += 1
            self.stats["last_activity"] = datetime.now()
            
            return {
                "success": True,
                "file_path": file_path,
                "file_size": path.stat().st_size,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error writing binary file {file_path}: {e}")
            self.stats["failed_operations"] += 1
            return {"success": False, "error": str(e)}
    
    async def read_binary_file(self, file_path: str) -> Dict[str, Any]:
        """Read binary data from file."""
        try:
            self.stats["total_operations"] += 1
            
            path = Path(file_path)
            if not path.exists():
                return {"success": False, "error": f"File not found: {file_path}"}
            
            async with aiofiles.open(file_path, 'rb') as f:
                data = await f.read()
            
            self.stats["files_read"] += 1
            self.stats["last_activity"] = datetime.now()
            
            return {
                "success": True,
                "data": data,
                "file_size": path.stat().st_size,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error reading binary file {file_path}: {e}")
            self.stats["failed_operations"] += 1
            return {"success": False, "error": str(e)}
    
    def get_status(self) -> Dict[str, Any]:
        return {
            "module": self.module_name,
            "is_active": self.is_active,
            "statistics": self.stats,
            "timestamp": datetime.now().isoformat()
        }
    
    async def health_check(self) -> Dict[str, Any]:
        try:
            # Test file operations
            test_data = {"test": "data", "timestamp": datetime.now().isoformat()}
            test_file = "test_fim.json"
            
            # Test write
            write_result = await self.write_file(test_file, test_data)
            if not write_result["success"]:
                return {
                    "healthy": False,
                    "module": self.module_name,
                    "error": "Write test failed",
                    "timestamp": datetime.now().isoformat()
                }
            
            # Test read
            read_result = await self.read_file(test_file)
            if not read_result["success"]:
                return {
                    "healthy": False,
                    "module": self.module_name,
                    "error": "Read test failed",
                    "timestamp": datetime.now().isoformat()
                }
            
            # Clean up
            try:
                os.remove(test_file)
            except:
                pass
            
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