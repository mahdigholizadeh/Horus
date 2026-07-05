"""
Input Validation Module (IVM) for RLA Microservice

This module handles comprehensive input validation:
- JSON schema validation
- Data type validation
- Content validation
- Format validation
- Security validation
"""

import json
import logging
import asyncio
import re
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import jsonschema
from pathlib import Path


class InputValidationModule:
    """
    Input Validation Module
    
    Responsible for comprehensive input validation:
    - JSON schema validation
    - Data type and format validation
    - Content and security validation
    - Protocol compliance validation
    """
    
    def __init__(self):
        """Initialize the IVM module."""
        self.logger = logging.getLogger(__name__)
        self.module_name = "IVM"
        self.is_active = False
        
        # Validation statistics
        self.stats = {
            "total_validations": 0,
            "successful_validations": 0,
            "failed_validations": 0,
            "schema_errors": 0,
            "type_errors": 0,
            "format_errors": 0,
            "security_errors": 0,
            "last_validation": None
        }
        
        # Schema definitions
        self.schemas = {
            "basic_request": {
                "type": "object",
                "properties": {
                    "request_id": {"type": "string"},
                    "timestamp": {"type": ["string", "number"]},
                    "content": {"type": "string"},
                    "message": {"type": "string"}
                },
                "additionalProperties": True
            },
            "chatbot_request": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "string"},
                    "message": {"type": "string", "maxLength": 10000},
                    "timestamp": {"type": ["string", "number"]},
                    "session_id": {"type": "string"},
                    "metadata": {"type": "object"}
                },
                "required": ["message"],
                "additionalProperties": True
            }
        }
        
        # Validation rules
        self.validation_rules = {
            "max_keys": 50,
            "max_string_length": 10000,
            "max_array_length": 1000,
            "max_nesting_depth": 10,
            "allowed_content_types": ["text/plain", "application/json"],
            "required_encoding": "utf-8"
        }
        
        # Security patterns
        self.security_patterns = {
            "script_injection": [
                r'<script[^>]*>',
                r'</script>',
                r'javascript:',
                r'vbscript:',
                r'on\w+\s*=',
                r'eval\s*\(',
                r'exec\s*\(',
                r'Function\s*\(',
                r'setTimeout\s*\(',
                r'setInterval\s*\('
            ],
            "sql_injection": [
                r'union\s+select',
                r'drop\s+table',
                r'delete\s+from',
                r'insert\s+into',
                r'update\s+set',
                r';\s*--',
                r';\s*/\*',
                r'\'\s*or\s*\'\s*=\s*\'',
                r'1\s*=\s*1',
                r'admin\'\s*--'
            ],
            "path_traversal": [
                r'\.\./',
                r'\.\.\\',
                r'%2e%2e%2f',
                r'%2e%2e%5c',
                r'/etc/passwd',
                r'/etc/shadow',
                r'c:\\windows\\',
                r'c:/windows/'
            ],
            "command_injection": [
                r';\s*rm\s',
                r';\s*del\s',
                r';\s*cat\s',
                r';\s*type\s',
                r'`[^`]*`',
                r'\$\([^)]*\)',
                r'&\s*rm\s',
                r'\|\s*rm\s'
            ]
        }
        
        self.logger.info(f"{self.module_name} initialized successfully")
    
    async def start(self):
        """Start the IVM module."""
        try:
            self.is_active = True
            self.logger.info(f"{self.module_name} started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start {self.module_name}: {e}")
            raise
    
    async def stop(self):
        """Stop the IVM module."""
        try:
            self.is_active = False
            self.logger.info(f"{self.module_name} stopped successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to stop {self.module_name}: {e}")
            raise
    
    async def validate_input(self, input_data: Any, schema_name: str = "basic_request") -> Dict[str, Any]:
        """
        Validate input data comprehensively.
        
        Args:
            input_data: The input data to validate
            schema_name: The schema to use for validation
            
        Returns:
            Validation result dictionary
        """
        try:
            start_time = datetime.now()
            self.stats["total_validations"] += 1
            
            errors = []
            
            # Step 1: Basic type validation
            if not isinstance(input_data, dict):
                errors.append(f"Expected dictionary, got {type(input_data).__name__}")
                self.stats["type_errors"] += 1
                return self._create_validation_result(False, errors)
            
            # Step 2: Schema validation
            schema_result = await self._validate_schema(input_data, schema_name)
            if not schema_result["valid"]:
                errors.extend(schema_result["errors"])
                self.stats["schema_errors"] += 1
            
            # Step 3: Format validation
            format_result = await self._validate_format(input_data)
            if not format_result["valid"]:
                errors.extend(format_result["errors"])
                self.stats["format_errors"] += 1
            
            # Step 4: Security validation
            security_result = await self._validate_security(input_data)
            if not security_result["valid"]:
                errors.extend(security_result["errors"])
                self.stats["security_errors"] += 1
            
            # Step 5: Business rule validation
            business_result = await self._validate_business_rules(input_data)
            if not business_result["valid"]:
                errors.extend(business_result["errors"])
            
            # Step 6: Content validation
            content_result = await self._validate_content(input_data)
            if not content_result["valid"]:
                errors.extend(content_result["errors"])
            
            # Determine final result
            valid = len(errors) == 0
            processing_time = (datetime.now() - start_time).total_seconds()
            
            if valid:
                self.stats["successful_validations"] += 1
            else:
                self.stats["failed_validations"] += 1
            
            self.stats["last_validation"] = datetime.now()
            
            return {
                "valid": valid,
                "errors": errors,
                "processing_time": processing_time,
                "validation_steps": {
                    "schema": schema_result["valid"],
                    "format": format_result["valid"],
                    "security": security_result["valid"],
                    "business_rules": business_result["valid"],
                    "content": content_result["valid"]
                },
                "validated_data": input_data if valid else None,
                "timestamp": datetime.now().isoformat(),
                "module": self.module_name
            }
            
        except Exception as e:
            self.logger.error(f"Input validation error: {e}")
            self.stats["failed_validations"] += 1
            return self._create_validation_result(False, [f"Validation exception: {str(e)}"])
    
    async def _validate_schema(self, data: Dict[str, Any], schema_name: str) -> Dict[str, Any]:
        """Validate data against JSON schema."""
        try:
            errors = []
            
            if schema_name not in self.schemas:
                errors.append(f"Unknown schema: {schema_name}")
                return {"valid": False, "errors": errors}
            
            schema = self.schemas[schema_name]
            
            try:
                jsonschema.validate(data, schema)
            except jsonschema.ValidationError as e:
                errors.append(f"Schema validation error: {e.message}")
            except jsonschema.SchemaError as e:
                errors.append(f"Schema error: {e.message}")
            
            return {"valid": len(errors) == 0, "errors": errors}
            
        except Exception as e:
            return {"valid": False, "errors": [f"Schema validation failed: {str(e)}"]}
    
    async def _validate_format(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate data format and structure."""
        try:
            errors = []
            
            # Check maximum keys
            if len(data) > self.validation_rules["max_keys"]:
                errors.append(f"Too many keys: {len(data)} (max: {self.validation_rules['max_keys']})")
            
            # Check nesting depth
            max_depth = self._get_max_nesting_depth(data)
            if max_depth > self.validation_rules["max_nesting_depth"]:
                errors.append(f"Nesting too deep: {max_depth} (max: {self.validation_rules['max_nesting_depth']})")
            
            # Validate data recursively
            structure_errors = self._validate_structure_recursive(data, "")
            errors.extend(structure_errors)
            
            # NEW: Check for excessive non-alphanumeric characters in message
            if "message" in data and isinstance(data["message"], str):
                msg = data["message"]
                non_alnum_ratio = sum(1 for c in msg if not c.isalnum() and not c.isspace()) / max(1, len(msg))
                if non_alnum_ratio > 0.25:
                    errors.append("Format error: excessive non-alphanumeric/symbol characters in message")
            
            return {"valid": len(errors) == 0, "errors": errors}
            
        except Exception as e:
            return {"valid": False, "errors": [f"Format validation failed: {str(e)}"]}
    
    async def _validate_security(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate data for security threats."""
        try:
            errors = []
            
            # Extract all text content
            text_content = self._extract_text_content(data)
            
            # Check for security patterns
            for pattern_type, patterns in self.security_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, text_content, re.IGNORECASE):
                        errors.append(f"Security threat detected: {pattern_type}")
                        break
            
            # Check for suspicious characters
            if self._contains_suspicious_characters(text_content):
                errors.append("Suspicious characters detected")
            
            # Check for encoding issues
            if self._has_encoding_issues(text_content):
                errors.append("Encoding issues detected")
            
            return {"valid": len(errors) == 0, "errors": errors}
            
        except Exception as e:
            return {"valid": False, "errors": [f"Security validation failed: {str(e)}"]}
    
    async def _validate_business_rules(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate business-specific rules."""
        try:
            errors = []
            
            # Check for required fields based on context
            if "message" in data:
                message = data["message"]
                if not isinstance(message, str):
                    errors.append("Message must be a string")
                elif len(message.strip()) == 0:
                    errors.append("Message cannot be empty")
            
            # Check timestamp format
            if "timestamp" in data:
                timestamp = data["timestamp"]
                if not self._is_valid_timestamp(timestamp):
                    errors.append("Invalid timestamp format")
            
            # Check request ID format
            if "request_id" in data:
                request_id = data["request_id"]
                if not self._is_valid_request_id(request_id):
                    errors.append("Invalid request ID format")
            
            # Check user ID format
            if "user_id" in data:
                user_id = data["user_id"]
                if not self._is_valid_user_id(user_id):
                    errors.append("Invalid user ID format")
            
            return {"valid": len(errors) == 0, "errors": errors}
            
        except Exception as e:
            return {"valid": False, "errors": [f"Business rule validation failed: {str(e)}"]}
    
    async def _validate_content(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate content quality and characteristics."""
        try:
            errors = []
            
            # Extract text content
            text_content = self._extract_text_content(data)
            
            # Check for empty content
            if len(text_content.strip()) == 0:
                errors.append("Content cannot be empty")
            
            # Check for excessive repetition
            if self._has_excessive_repetition(text_content):
                errors.append("Excessive content repetition detected")
            
            # Check for binary data
            if self._contains_binary_data(text_content):
                errors.append("Binary data detected in text content")
            
            # Check for valid language characters
            if not self._has_valid_language_characters(text_content):
                errors.append("Invalid language characters detected")
            
            # NEW: Check for gibberish/low-quality content in message
            if "message" in data and isinstance(data["message"], str):
                msg = data["message"]
                # Heuristic: if more than 30% of chars are not letters or spaces, flag as gibberish
                gibberish_ratio = sum(1 for c in msg if not c.isalpha() and not c.isspace()) / max(1, len(msg))
                if gibberish_ratio > 0.3:
                    errors.append("Content quality error: message appears to be gibberish or low quality")
                # Additional: if message is short and has few vowels, likely gibberish
                vowels = sum(1 for c in msg.lower() if c in 'aeiou')
                if len(msg) < 15 and vowels < 3:
                    errors.append("Content quality error: message appears to be gibberish or low quality (few vowels)")
            
            return {"valid": len(errors) == 0, "errors": errors}
            
        except Exception as e:
            return {"valid": False, "errors": [f"Content validation failed: {str(e)}"]}
    
    def _get_max_nesting_depth(self, obj, current_depth=0):
        """Get maximum nesting depth."""
        if isinstance(obj, dict):
            if not obj:
                return current_depth
            return max(self._get_max_nesting_depth(v, current_depth + 1) for v in obj.values())
        elif isinstance(obj, list):
            if not obj:
                return current_depth
            return max(self._get_max_nesting_depth(item, current_depth + 1) for item in obj)
        else:
            return current_depth
    
    def _validate_structure_recursive(self, obj, path=""):
        """Validate structure recursively."""
        errors = []
        
        if isinstance(obj, dict):
            for key, value in obj.items():
                if not isinstance(key, str):
                    errors.append(f"Dictionary key at '{path}' must be string")
                new_path = f"{path}.{key}" if path else key
                errors.extend(self._validate_structure_recursive(value, new_path))
        elif isinstance(obj, list):
            if len(obj) > self.validation_rules["max_array_length"]:
                errors.append(f"Array at '{path}' too long: {len(obj)} (max: {self.validation_rules['max_array_length']})")
            for i, item in enumerate(obj):
                errors.extend(self._validate_structure_recursive(item, f"{path}[{i}]"))
        elif isinstance(obj, str):
            if len(obj) > self.validation_rules["max_string_length"]:
                errors.append(f"String at '{path}' too long: {len(obj)} (max: {self.validation_rules['max_string_length']})")
        
        return errors
    
    def _extract_text_content(self, data: Dict[str, Any]) -> str:
        """Extract all text content from data."""
        def extract_recursive(obj):
            if isinstance(obj, str):
                return obj
            elif isinstance(obj, dict):
                return " ".join(extract_recursive(v) for v in obj.values())
            elif isinstance(obj, list):
                return " ".join(extract_recursive(item) for item in obj)
            else:
                return str(obj)
        
        return extract_recursive(data)
    
    def _contains_suspicious_characters(self, text: str) -> bool:
        """Check for suspicious characters."""
        # Check for control characters
        for char in text:
            if ord(char) < 32 and char not in ['\t', '\n', '\r']:
                return True
        
        # Check for unusual Unicode ranges
        suspicious_ranges = [
            (0x2000, 0x200F),  # General punctuation
            (0x202A, 0x202E),  # Directional marks
            (0xFFF0, 0xFFFF),  # Specials
        ]
        
        for char in text:
            char_code = ord(char)
            for start, end in suspicious_ranges:
                if start <= char_code <= end:
                    return True
        
        return False
    
    def _has_encoding_issues(self, text: str) -> bool:
        """Check for encoding issues."""
        try:
            # Try to encode/decode
            text.encode('utf-8').decode('utf-8')
            return False
        except UnicodeError:
            return True
    
    def _is_valid_timestamp(self, timestamp: Any) -> bool:
        """Validate timestamp format."""
        if isinstance(timestamp, (int, float)):
            return 0 < timestamp < 2147483647
        elif isinstance(timestamp, str):
            try:
                datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                return True
            except ValueError:
                return False
        return False
    
    def _is_valid_request_id(self, request_id: str) -> bool:
        """Validate request ID format."""
        pattern = r'^wsrid_0x[0-9A-Fa-f]{12}$'
        return bool(re.match(pattern, request_id))
    
    def _is_valid_user_id(self, user_id: str) -> bool:
        """Validate user ID format."""
        if not isinstance(user_id, str):
            return False
        if len(user_id) < 3 or len(user_id) > 50:
            return False
        # Allow alphanumeric, underscore, dash
        pattern = r'^[a-zA-Z0-9_-]+$'
        return bool(re.match(pattern, user_id))
    
    def _has_excessive_repetition(self, text: str) -> bool:
        """Check for excessive repetition."""
        words = text.split()
        if len(words) < 10:
            return False
        
        word_counts = {}
        for word in words:
            word_counts[word] = word_counts.get(word, 0) + 1
        
        max_count = max(word_counts.values())
        return max_count > len(words) * 0.4  # More than 40% repetition
    
    def _contains_binary_data(self, text: str) -> bool:
        """Check for binary data."""
        try:
            if '\x00' in text:
                return True
            
            printable_chars = sum(1 for c in text if c.isprintable())
            if len(text) > 0 and printable_chars / len(text) < 0.7:
                return True
            
            return False
        except Exception:
            return True
    
    def _has_valid_language_characters(self, text: str) -> bool:
        """Check for valid language characters."""
        # Allow common language ranges
        valid_ranges = [
            (0x20, 0x7E),      # Basic Latin
            (0xA0, 0xFF),      # Latin-1 Supplement
            (0x100, 0x17F),    # Latin Extended-A
            (0x180, 0x24F),    # Latin Extended-B
            (0x400, 0x4FF),    # Cyrillic
            (0x600, 0x6FF),    # Arabic
            (0x4E00, 0x9FFF),  # CJK Unified Ideographs
        ]
        
        for char in text:
            if char in ['\t', '\n', '\r', ' ']:
                continue
            
            char_code = ord(char)
            valid = False
            
            for start, end in valid_ranges:
                if start <= char_code <= end:
                    valid = True
                    break
            
            if not valid:
                return False
        
        return True
    
    def _create_validation_result(self, valid: bool, errors: List[str]) -> Dict[str, Any]:
        """Create a validation result."""
        return {
            "valid": valid,
            "errors": errors,
            "timestamp": datetime.now().isoformat(),
            "module": self.module_name
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the IVM module."""
        return {
            "module": self.module_name,
            "is_active": self.is_active,
            "statistics": self.stats,
            "validation_rules": self.validation_rules,
            "available_schemas": list(self.schemas.keys())
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        try:
            # Test basic functionality
            test_data = {"message": "test", "timestamp": datetime.now().isoformat()}
            result = await self.validate_input(test_data)
            
            return {
                "healthy": self.is_active and result["valid"],
                "module": self.module_name,
                "timestamp": datetime.now().isoformat(),
                "test_result": result["valid"],
                "statistics": self.stats
            }
            
        except Exception as e:
            return {
                "healthy": False,
                "module": self.module_name,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            } 