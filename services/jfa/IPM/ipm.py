"""
Input Processing Module (IPM) for JFA Microservice

This module handles input processing operations:
- Input validation and sanitization
- Format conversion and preprocessing
- Security checks and input filtering
- Data transformation and normalization
"""

import logging
import asyncio
import json
from typing import Dict, Any, List, Optional
from datetime import datetime


class InputProcessingModule:
    """Input Processing Module for JFA"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.module_name = "IPM"
        self.is_active = False
        
        self.stats = {
            "total_processed": 0,
            "successful_processing": 0,
            "failed_processing": 0,
            "last_activity": None
        }
    
    async def start(self):
        self.is_active = True
        self.logger.info(f"{self.module_name} started successfully")
    
    async def stop(self):
        self.is_active = False
        self.logger.info(f"{self.module_name} stopped successfully")
    
    async def process_input(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process and validate input data."""
        try:
            self.stats["total_processed"] += 1
            
            # Basic validation
            if not input_data:
                return {"valid": False, "error": "Empty input data"}
            
            # Security checks
            security_result = await self._security_check(input_data)
            if not security_result["safe"]:
                error_msg = "; ".join(security_result["issues"])
                return {"valid": False, "error": error_msg}
            
            # Format validation
            format_result = await self._validate_format(input_data)
            if not format_result["valid"]:
                error_msg = "; ".join(format_result["errors"])
                return {"valid": False, "error": error_msg}
            
            # Preprocessing
            processed_data = await self._preprocess_data(input_data)
            
            self.stats["successful_processing"] += 1
            self.stats["last_activity"] = datetime.now()
            
            return {
                "valid": True,
                "processed_data": processed_data,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error processing input: {e}")
            self.stats["failed_processing"] += 1
            return {"valid": False, "error": str(e)}
    
    async def _security_check(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Perform security checks on input data."""
        try:
            issues = []
            
            # Check for suspicious patterns
            data_str = str(data)
            if len(data_str) > 10 * 1024 * 1024:  # 10MB limit
                issues.append("Input data too large")
            
            # Check for SQL injection patterns
            sql_patterns = [
                "';", "--", "/*", "*/", "union", "select", "drop", "delete", 
                "insert", "update", "create", "alter", "exec", "execute"
            ]
            for pattern in sql_patterns:
                if pattern in data_str.lower():
                    issues.append(f"SQL injection pattern detected: {pattern}")
            
            # Check for XSS patterns
            xss_patterns = ["<script>", "javascript:", "onload=", "onerror=", "onclick="]
            for pattern in xss_patterns:
                if pattern in data_str.lower():
                    issues.append(f"XSS pattern detected: {pattern}")
            
            # Check for command injection patterns
            command_patterns = [
                "rm -rf", "del /", "format c:", "shutdown", "reboot", 
                "system(", "exec(", "eval(", "os.system", "subprocess"
            ]
            for pattern in command_patterns:
                if pattern in data_str.lower():
                    issues.append(f"Command injection pattern detected: {pattern}")
            
            # Check for other dangerous patterns
            dangerous_patterns = ["eval(", "exec(", "compile("]
            for pattern in dangerous_patterns:
                if pattern in data_str.lower():
                    issues.append(f"Dangerous pattern detected: {pattern}")
            
            return {"safe": len(issues) == 0, "issues": issues}
            
        except Exception as e:
            return {"safe": False, "issues": [f"Security check error: {str(e)}"]}
    
    async def _validate_format(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate input format."""
        try:
            errors = []
            
            # Check if it's a dictionary
            if not isinstance(data, dict):
                errors.append("Input must be a dictionary")
                return {"valid": False, "errors": errors}
            
            # Check for required structure
            if "template_data" not in data and "id" not in data:
                errors.append("Missing required fields: template_data or id")
            
            return {"valid": len(errors) == 0, "errors": errors}
            
        except Exception as e:
            return {"valid": False, "errors": [f"Format validation error: {str(e)}"]}
    
    async def _preprocess_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Preprocess input data."""
        try:
            processed_data = data.copy()
            
            # Normalize string fields
            for key, value in processed_data.items():
                if isinstance(value, str):
                    processed_data[key] = value.strip()
            
            # Add processing metadata
            processed_data["_processing_metadata"] = {
                "processed_at": datetime.now().isoformat(),
                "processed_by": self.module_name
            }
            
            return processed_data
            
        except Exception as e:
            self.logger.error(f"Error preprocessing data: {e}")
            return data
    
    def get_status(self) -> Dict[str, Any]:
        return {
            "module": self.module_name,
            "is_active": self.is_active,
            "statistics": self.stats,
            "timestamp": datetime.now().isoformat()
        }
    
    async def health_check(self) -> Dict[str, Any]:
        try:
            test_data = {"id": "test-001", "test": "data"}
            result = await self.process_input(test_data)
            
            return {
                "healthy": self.is_active and result["valid"],
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