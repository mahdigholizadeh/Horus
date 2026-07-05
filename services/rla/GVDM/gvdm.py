"""
Gateway Validation Data Module (GVDM) for RLA Microservice

This module handles core gateway validation operations:
- JSON schema validation
- Data integrity checks
- Gateway-level validation logic
- Protocol validation
- Input sanitization
"""

import json
import logging
import asyncio
import re
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
from pathlib import Path
import hashlib
import uuid


class GatewayValidationDataModule:
    """
    Gateway Validation Data Module
    
    Handles all core validation operations for the RLA gateway:
    - JSON validation and parsing
    - Data integrity verification
    - Protocol-level validation
    - Input sanitization
    """
    
    def __init__(self):
        """Initialize the GVDM module."""
        self.logger = logging.getLogger(__name__)
        self.module_name = "GVDM"
        self.is_active = False
        
        # Validation statistics
        self.stats = {
            "total_validations": 0,
            "successful_validations": 0,
            "failed_validations": 0,
            "schema_errors": 0,
            "format_errors": 0,
            "encoding_errors": 0,
            "last_validation": None
        }
        
        # Validation rules
        self.validation_rules = {
            "max_json_size": 10 * 1024 * 1024,  # 10MB
            "required_fields": [],
            "allowed_types": [str, int, float, bool, list, dict],
            "max_nesting_depth": 10,
            "max_array_length": 1000,
            "max_string_length": 100000,
            "field_types": {}  # NEW: expected types for specific fields
        }
        
        # Protocol constants
        self.protocol_markers = {
            "activation_key": 0b1001110100110111,  # 0x9D37
            "handshake_start": 0xBB7F73DF,  # R1
            "handshake_end": 0xBB7578DF,    # R2
            "success_ack": 0b1011111111111111  # 0xBFFF
        }
        
        self.logger.info(f"{self.module_name} initialized successfully")
    
    async def start(self):
        """Start the GVDM module."""
        try:
            self.is_active = True
            self.logger.info(f"{self.module_name} started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start {self.module_name}: {e}")
            raise
    
    async def stop(self):
        """Stop the GVDM module."""
        try:
            self.is_active = False
            self.logger.info(f"{self.module_name} stopped successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to stop {self.module_name}: {e}")
            raise
    
    async def validate_json_data(self, json_data: Union[str, bytes, Dict]) -> Dict[str, Any]:
        """
        Validate JSON data comprehensively.
        
        Args:
            json_data: Raw JSON data to validate
            
        Returns:
            Validation result dictionary
        """
        try:
            start_time = datetime.now()
            self.stats["total_validations"] += 1
            
            # Step 1: Parse JSON if it's a string or bytes
            if isinstance(json_data, (str, bytes)):
                parsed_data = await self._parse_json_string(json_data)
                if parsed_data is None:
                    self.stats["failed_validations"] += 1
                    return self._create_validation_result(False, ["JSON parsing failed"])
            else:
                parsed_data = json_data
            
            # Step 2: Basic structure validation
            structure_result = await self._validate_structure(parsed_data)
            if not structure_result["valid"]:
                self.stats["failed_validations"] += 1
                return structure_result
            
            # Step 3: Content validation
            content_result = await self._validate_content(parsed_data)
            if not content_result["valid"]:
                self.stats["failed_validations"] += 1
                return content_result
            
            # Step 4: Protocol validation
            protocol_result = await self._validate_protocol(parsed_data)
            if not protocol_result["valid"]:
                self.stats["failed_validations"] += 1
                return protocol_result
            
            # Step 5: Security validation
            security_result = await self._validate_security(parsed_data)
            if not security_result["valid"]:
                self.stats["failed_validations"] += 1
                return security_result
            
            # Success
            processing_time = (datetime.now() - start_time).total_seconds()
            self.stats["successful_validations"] += 1
            self.stats["last_validation"] = datetime.now()
            
            return self._create_validation_result(
                True, 
                [], 
                extra_data={
                    "parsed_data": parsed_data,
                    "processing_time": processing_time,
                    "validation_timestamp": datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            self.logger.error(f"Validation error: {e}")
            self.stats["failed_validations"] += 1
            return self._create_validation_result(False, [f"Validation exception: {str(e)}"])
    
    async def _parse_json_string(self, json_string: Union[str, bytes]) -> Optional[Dict]:
        """Parse JSON string/bytes into dictionary."""
        try:
            if isinstance(json_string, bytes):
                # Try UTF-8 decoding
                try:
                    json_string = json_string.decode('utf-8')
                except UnicodeDecodeError:
                    self.stats["encoding_errors"] += 1
                    self.logger.error("Failed to decode bytes as UTF-8")
                    return None
            
            # Parse JSON
            parsed = json.loads(json_string)
            return parsed
            
        except json.JSONDecodeError as e:
            self.stats["format_errors"] += 1
            self.logger.error(f"JSON decode error: {e}")
            return None
        except Exception as e:
            self.logger.error(f"JSON parsing error: {e}")
            return None
    
    async def _validate_structure(self, data: Dict) -> Dict[str, Any]:
        """Validate the basic structure of the JSON data."""
        try:
            errors = []
            
            # Check if it's a dictionary
            if not isinstance(data, dict):
                errors.append(f"Expected dictionary, got {type(data).__name__}")
                return self._create_validation_result(False, errors)
            
            # Check size limits
            data_size = len(json.dumps(data))
            if data_size > self.validation_rules["max_json_size"]:
                errors.append(f"JSON size ({data_size}) exceeds maximum ({self.validation_rules['max_json_size']})")
            
            # Check nesting depth
            max_depth = self._get_max_nesting_depth(data)
            if max_depth > self.validation_rules["max_nesting_depth"]:
                errors.append(f"Nesting depth ({max_depth}) exceeds maximum ({self.validation_rules['max_nesting_depth']})")
            
            # Check required fields
            for field in self.validation_rules["required_fields"]:
                if field not in data:
                    errors.append(f"Required field '{field}' missing")
            
            # Check data types
            type_errors = self._validate_data_types(data)
            errors.extend(type_errors)
            
            return self._create_validation_result(len(errors) == 0, errors)
            
        except Exception as e:
            self.logger.error(f"Structure validation error: {e}")
            return self._create_validation_result(False, [f"Structure validation failed: {str(e)}"])
    
    async def _validate_content(self, data: Dict) -> Dict[str, Any]:
        """Validate the content of the JSON data."""
        try:
            errors = []
            
            # Check for suspicious patterns
            text_content = self._extract_text_content(data)
            
            # Check for potentially malicious content
            if self._contains_suspicious_patterns(text_content):
                errors.append("Suspicious content patterns detected")
            
            # Check for excessive repetition
            if self._has_excessive_repetition(text_content):
                errors.append("Excessive content repetition detected")
            
            # Check for binary data in text fields
            if self._contains_binary_data(text_content):
                errors.append("Binary data detected in text content")
            
            # Validate URLs if present
            url_errors = self._validate_urls(data)
            errors.extend(url_errors)
            
            return self._create_validation_result(len(errors) == 0, errors)
            
        except Exception as e:
            self.logger.error(f"Content validation error: {e}")
            return self._create_validation_result(False, [f"Content validation failed: {str(e)}"])
    
    async def _validate_protocol(self, data: Dict) -> Dict[str, Any]:
        """Validate protocol-specific requirements."""
        try:
            errors = []
            
            # Check for protocol markers (if present)
            if "protocol_version" in data:
                if not isinstance(data["protocol_version"], str):
                    errors.append("Protocol version must be a string")
            
            # Check for request ID format
            if "request_id" in data:
                if not self._is_valid_request_id(data["request_id"]):
                    errors.append("Invalid request ID format")
            
            # Check for timestamp format
            if "timestamp" in data:
                if not self._is_valid_timestamp(data["timestamp"]):
                    errors.append("Invalid timestamp format")
            
            return self._create_validation_result(len(errors) == 0, errors)
            
        except Exception as e:
            self.logger.error(f"Protocol validation error: {e}")
            return self._create_validation_result(False, [f"Protocol validation failed: {str(e)}"])
    
    async def _validate_security(self, data: Dict) -> Dict[str, Any]:
        """Validate security-related aspects."""
        try:
            errors = []
            
            # Check for script injection attempts
            if self._contains_script_injection(data):
                errors.append("Script injection attempt detected")
            
            # Check for SQL injection patterns
            if self._contains_sql_injection(data):
                errors.append("SQL injection attempt detected")
            
            # Check for path traversal attempts
            if self._contains_path_traversal(data):
                errors.append("Path traversal attempt detected")
            
            # Check for excessive data
            if self._has_excessive_data(data):
                errors.append("Excessive data detected (possible DoS attempt)")
            
            return self._create_validation_result(len(errors) == 0, errors)
            
        except Exception as e:
            self.logger.error(f"Security validation error: {e}")
            return self._create_validation_result(False, [f"Security validation failed: {str(e)}"])
    
    def _get_max_nesting_depth(self, obj, current_depth=0):
        """Get maximum nesting depth of a nested structure."""
        if isinstance(obj, dict):
            return max([self._get_max_nesting_depth(v, current_depth + 1) for v in obj.values()] or [current_depth])
        elif isinstance(obj, list):
            return max([self._get_max_nesting_depth(item, current_depth + 1) for item in obj] or [current_depth])
        else:
            return current_depth
    
    def _validate_data_types(self, data: Dict) -> List[str]:
        """Validate data types recursively, including field_types if specified."""
        errors = []
        field_types = self.validation_rules.get("field_types", {})
        required_fields = self.validation_rules.get("required_fields", [])

        def validate_recursive(obj, path=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if not isinstance(key, str):
                        errors.append(f"Dictionary key at '{path}' must be string, got {type(key).__name__}")
                    # Check for expected type if this is a required field
                    if key in field_types:
                        expected_type = field_types[key]
                        if not isinstance(value, expected_type):
                            errors.append(f"Invalid type for field '{key}': expected {expected_type.__name__}, got {type(value).__name__}")
                    validate_recursive(value, f"{path}.{key}" if path else key)
            elif isinstance(obj, list):
                if len(obj) > self.validation_rules["max_array_length"]:
                    errors.append(f"Array at '{path}' exceeds maximum length ({self.validation_rules['max_array_length']})")
                for i, item in enumerate(obj):
                    validate_recursive(item, f"{path}[{i}]")
            elif isinstance(obj, str):
                if len(obj) > self.validation_rules["max_string_length"]:
                    errors.append(f"String at '{path}' exceeds maximum length ({self.validation_rules['max_string_length']})")
            elif type(obj) not in self.validation_rules["allowed_types"]:
                errors.append(f"Invalid type at '{path}': {type(obj).__name__}")

        validate_recursive(data)
        return errors
    
    def _extract_text_content(self, data: Dict) -> str:
        """Extract all text content from the data structure."""
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
    
    def _contains_suspicious_patterns(self, text: str) -> bool:
        """Check for suspicious patterns in text."""
        suspicious_patterns = [
            r'<script[^>]*>.*?</script>',
            r'javascript:',
            r'vbscript:',
            r'onload\s*=',
            r'onerror\s*=',
            r'eval\s*\(',
            r'exec\s*\(',
            r'system\s*\(',
            r'import\s+os',
            r'__import__',
            r'\.\./',
            r'\.\.\\',
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False
    
    def _has_excessive_repetition(self, text: str) -> bool:
        """Check for excessive repetition in text."""
        words = text.split()
        if len(words) < 10:
            return False
        
        # Check for repeated words
        word_counts = {}
        for word in words:
            word_counts[word] = word_counts.get(word, 0) + 1
        
        max_count = max(word_counts.values())
        return max_count > len(words) * 0.5  # More than 50% repetition
    
    def _contains_binary_data(self, text: str) -> bool:
        """Check for binary data in text."""
        try:
            # Check for null bytes
            if '\x00' in text:
                return True
            
            # Check for high ratio of non-printable characters
            printable_chars = sum(1 for c in text if c.isprintable())
            if len(text) > 0 and printable_chars / len(text) < 0.8:
                return True
            
            return False
        except Exception:
            return True
    
    def _validate_urls(self, data: Dict) -> List[str]:
        """Validate URLs in the data."""
        errors = []
        url_pattern = re.compile(
            r'https?://(?:[-\w.])+(?::[0-9]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:\w)*)?)?',
            re.IGNORECASE
        )
        
        def check_urls(obj, path=""):
            if isinstance(obj, str):
                urls = url_pattern.findall(obj)
                for url in urls:
                    if not self._is_safe_url(url):
                        errors.append(f"Unsafe URL detected at '{path}': {url}")
            elif isinstance(obj, dict):
                for key, value in obj.items():
                    check_urls(value, f"{path}.{key}" if path else key)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    check_urls(item, f"{path}[{i}]")
        
        check_urls(data)
        return errors
    
    def _is_safe_url(self, url: str) -> bool:
        """Check if URL is safe."""
        # Basic URL safety checks
        unsafe_schemes = ['javascript:', 'vbscript:', 'file:', 'ftp:']
        unsafe_domains = ['localhost', '127.0.0.1', '0.0.0.0', '192.168.', '10.', '172.']
        
        url_lower = url.lower()
        
        # Check for unsafe schemes
        for scheme in unsafe_schemes:
            if url_lower.startswith(scheme):
                return False
        
        # Check for unsafe domains
        for domain in unsafe_domains:
            if domain in url_lower:
                return False
        
        return True
    
    def _is_valid_request_id(self, request_id: str) -> bool:
        """Validate request ID format."""
        # Check for wsrid_0x<12-digit-hex> format
        pattern = r'^wsrid_0x[0-9A-Fa-f]{12}$'
        return bool(re.match(pattern, request_id))
    
    def _is_valid_timestamp(self, timestamp: Any) -> bool:
        """Validate timestamp format."""
        if isinstance(timestamp, (int, float)):
            # Unix timestamp
            return 0 < timestamp < 2147483647  # Valid range
        elif isinstance(timestamp, str):
            # ISO format
            try:
                datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                return True
            except ValueError:
                return False
        return False
    
    def _contains_script_injection(self, data: Dict) -> bool:
        """Check for script injection attempts."""
        text = self._extract_text_content(data)
        script_patterns = [
            r'<script[^>]*>',
            r'</script>',
            r'javascript:',
            r'vbscript:',
            r'onload\s*=',
            r'onerror\s*=',
            r'onclick\s*=',
            r'onmouseover\s*=',
        ]
        
        for pattern in script_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False
    
    def _contains_sql_injection(self, data: Dict) -> bool:
        """Check for SQL injection attempts."""
        text = self._extract_text_content(data)
        sql_patterns = [
            r'union\s+select',
            r'drop\s+table',
            r'delete\s+from',
            r'insert\s+into',
            r'update\s+set',
            r';\s*--',
            r';\s*/\*',
            r'\'\s*or\s*\'\s*=\s*\'',
            r'admin\'\s*--',
            r'1\s*=\s*1',
        ]
        
        for pattern in sql_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False
    
    def _contains_path_traversal(self, data: Dict) -> bool:
        """Check for path traversal attempts."""
        text = self._extract_text_content(data)
        path_patterns = [
            r'\.\./',
            r'\.\.\\',
            r'%2e%2e%2f',
            r'%2e%2e%5c',
            r'/etc/passwd',
            r'/etc/shadow',
            r'c:\\windows\\',
            r'c:/windows/',
        ]
        
        for pattern in path_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False
    
    def _has_excessive_data(self, data: Dict) -> bool:
        """Check for excessive data that might indicate DoS attempt."""
        # Check total size
        total_size = len(json.dumps(data))
        if total_size > self.validation_rules["max_json_size"]:
            return True
        
        # Check for excessive arrays
        def check_arrays(obj):
            if isinstance(obj, list):
                if len(obj) > self.validation_rules["max_array_length"]:
                    return True
                for item in obj:
                    if check_arrays(item):
                        return True
            elif isinstance(obj, dict):
                for value in obj.values():
                    if check_arrays(value):
                        return True
            return False
        
        return check_arrays(data)
    
    def _create_validation_result(self, valid: bool, errors: List[str], extra_data: Dict = None) -> Dict[str, Any]:
        """Create a standardized validation result."""
        result = {
            "valid": valid,
            "errors": errors,
            "timestamp": datetime.now().isoformat(),
            "module": self.module_name
        }
        
        if extra_data:
            result.update(extra_data)
        
        return result
    
    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the GVDM module."""
        return {
            "module": self.module_name,
            "is_active": self.is_active,
            "statistics": self.stats,
            "validation_rules": self.validation_rules,
            "protocol_markers": self.protocol_markers
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        return {
            "healthy": self.is_active,
            "module": self.module_name,
            "timestamp": datetime.now().isoformat(),
            "statistics": self.stats
        } 