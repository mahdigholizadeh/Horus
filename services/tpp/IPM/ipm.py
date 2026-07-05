"""
Input Processing Module (IPM) for TPP Microservice

This module handles input validation and processing:
- Input data validation
- JSON schema validation
- Text preprocessing
- Security checks
"""

import logging
import asyncio
import json
import re
from typing import Dict, Any, List, Optional
from datetime import datetime


class InputProcessingModule:
    """
    Input Processing Module
    
    Validates and processes input data for the TPP microservice.
    """
    
    def __init__(self):
        """Initialize the IPM module."""
        self.logger = logging.getLogger(__name__)
        self.module_name = "IPM"
        self.is_active = False
        
        # Validation configuration
        self.validation_config = {
            "max_text_length": 100000,
            "min_text_length": 1,
            "required_fields": ["message_text"],
            "optional_fields": ["request_id", "source_block", "metadata", "timestamp"],
            "forbidden_patterns": [r'<script>', r'javascript:', r'data:'],
            "max_file_size": 50 * 1024 * 1024  # 50MB
        }
        
        # Statistics
        self.stats = {
            "total_processed": 0,
            "valid_inputs": 0,
            "invalid_inputs": 0,
            "security_violations": 0,
            "last_activity": None
        }
        
        self.logger.info(f"{self.module_name} initialized successfully")
    
    async def start(self):
        """Start the IPM module."""
        try:
            self.is_active = True
            self.logger.info(f"{self.module_name} started successfully")
        except Exception as e:
            self.logger.error(f"Failed to start {self.module_name}: {e}")
            raise
    
    async def stop(self):
        """Stop the IPM module."""
        try:
            self.is_active = False
            self.logger.info(f"{self.module_name} stopped successfully")
        except Exception as e:
            self.logger.error(f"Failed to stop {self.module_name}: {e}")
            raise
    
    async def process_input(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process and validate input data."""
        try:
            self.stats["total_processed"] += 1
            self.stats["last_activity"] = datetime.now()
            
            # Validate input structure
            structure_validation = self._validate_structure(input_data)
            if not structure_validation["valid"]:
                self.stats["invalid_inputs"] += 1
                return structure_validation
            
            # Validate text content
            text_validation = self._validate_text_content(input_data.get("message_text", ""))
            if not text_validation["valid"]:
                self.stats["invalid_inputs"] += 1
                return text_validation
            
            # Security validation
            security_validation = self._validate_security(input_data)
            if not security_validation["valid"]:
                self.stats["security_violations"] += 1
                return security_validation
            
            # Process valid input
            processed_data = self._process_valid_input(input_data)
            
            self.stats["valid_inputs"] += 1
            
            return {
                "valid": True,
                "processed_data": processed_data,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error processing input: {e}")
            self.stats["invalid_inputs"] += 1
            return {
                "valid": False,
                "errors": [f"Processing error: {str(e)}"],
                "timestamp": datetime.now().isoformat()
            }
    
    def _validate_structure(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate input data structure."""
        try:
            errors = []
            
            # Check required fields
            for field in self.validation_config["required_fields"]:
                if field not in data:
                    errors.append(f"Missing required field: {field}")
                elif not data[field]:
                    errors.append(f"Empty required field: {field}")
            
            # Check data types
            if "message_text" in data and not isinstance(data["message_text"], str):
                errors.append("message_text must be a string")
            
            if "metadata" in data and not isinstance(data["metadata"], dict):
                errors.append("metadata must be a dictionary")
            
            return {
                "valid": len(errors) == 0,
                "errors": errors
            }
            
        except Exception as e:
            return {
                "valid": False,
                "errors": [f"Structure validation error: {str(e)}"]
            }
    
    def _validate_text_content(self, text: str) -> Dict[str, Any]:
        """Validate text content."""
        try:
            errors = []
            
            # Length validation
            if len(text) < self.validation_config["min_text_length"]:
                errors.append(f"Text too short (minimum {self.validation_config['min_text_length']} characters)")
            
            if len(text) > self.validation_config["max_text_length"]:
                errors.append(f"Text too long (maximum {self.validation_config['max_text_length']} characters)")
            
            # Content validation
            if not text.strip():
                errors.append("Text cannot be empty or only whitespace")
            
            return {
                "valid": len(errors) == 0,
                "errors": errors
            }
            
        except Exception as e:
            return {
                "valid": False,
                "errors": [f"Text validation error: {str(e)}"]
            }
    
    def _validate_security(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Perform security validation."""
        try:
            errors = []
            text = data.get("message_text", "")
            
            # Check for forbidden patterns
            for pattern in self.validation_config["forbidden_patterns"]:
                if re.search(pattern, text, re.IGNORECASE):
                    errors.append(f"Forbidden pattern detected: {pattern}")
            
            # Check for potential injection attempts
            if self._detect_injection_attempts(text):
                errors.append("Potential injection attempt detected")
            
            return {
                "valid": len(errors) == 0,
                "errors": errors
            }
            
        except Exception as e:
            return {
                "valid": False,
                "errors": [f"Security validation error: {str(e)}"]
            }
    
    def _detect_injection_attempts(self, text: str) -> bool:
        """Detect potential injection attempts."""
        try:
            # Simple injection detection patterns
            injection_patterns = [
                r'<script.*?>.*?</script>',
                r'javascript:',
                r'data:.*?base64',
                r'<iframe.*?>',
                r'<object.*?>',
                r'<embed.*?>'
            ]
            
            for pattern in injection_patterns:
                if re.search(pattern, text, re.IGNORECASE | re.DOTALL):
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error detecting injection attempts: {e}")
            return False
    
    def _process_valid_input(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process valid input data."""
        try:
            processed_data = data.copy()
            
            # Normalize message text
            if "message_text" in processed_data:
                processed_data["message_text"] = self._normalize_text(processed_data["message_text"])
            
            # Add processing metadata
            processed_data["ipm_processed"] = True
            processed_data["ipm_timestamp"] = datetime.now().isoformat()
            
            # Ensure request_id exists
            if "request_id" not in processed_data:
                processed_data["request_id"] = self._generate_request_id()
            
            return processed_data
            
        except Exception as e:
            self.logger.error(f"Error processing valid input: {e}")
            return data
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text."""
        try:
            # Remove excessive whitespace
            normalized = re.sub(r'\s+', ' ', text.strip())
            
            # Remove null bytes
            normalized = normalized.replace('\x00', '')
            
            return normalized
            
        except Exception as e:
            self.logger.error(f"Error normalizing text: {e}")
            return text
    
    def _generate_request_id(self) -> str:
        """Generate a request ID."""
        import uuid
        return f"tpp_req_{uuid.uuid4().hex[:12]}"
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status."""
        return {
            "module": self.module_name,
            "is_active": self.is_active,
            "statistics": self.stats,
            "configuration": self.validation_config,
            "timestamp": datetime.now().isoformat()
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        try:
            test_data = {"message_text": "Test message"}
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