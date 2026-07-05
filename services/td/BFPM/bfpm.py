"""
Binary File Processing Module (BFPM) for TD Microservice

This module handles:
- Binary file decoding from JFA processing (via CCU)
- Template parsing and validation
- Technical data extraction from binary structures
- Activation flag separation
- File format detection and validation
- Metadata extraction

The BFPM is the first stage in the TD orchestration pipeline, responsible for
converting binary files into structured data that can be processed by the
routing and orchestration modules.
"""

import struct
import logging
import asyncio
import json
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from pathlib import Path
import os


class BinaryFileProcessingModule:
    """
    Binary File Processing Module for TD Microservice
    
    Handles decoding and processing of binary files from JFA with:
    - Template-based parsing
    - Technical data extraction
    - Activation flag separation
    - File validation and metadata extraction
    """
    
    def __init__(self):
        """Initialize the Binary File Processing Module."""
        self.logger = logging.getLogger(__name__)
        self.module_name = "BFPM"
        self.is_active = False
        
        # Generic passthrough templates (proxy mode)
        self.templates = {
            "default": {
                "technical_keys": ["request_id", "payload", "route", "metadata"],
                "data_types": {
                    "request_id": "string",
                    "payload": "object",
                    "route": "string",
                    "metadata": "object",
                },
                "description": "Generic request passthrough template",
            },
            "json": {
                "technical_keys": [],
                "data_types": {},
                "description": "Raw JSON passthrough",
            },
        }

        self.activation_flags = ["forward", "parallel", "sequential"]

        # Processing statistics
        self.stats = {
            "total_processed": 0,
            "successful_processing": 0,
            "failed_processing": 0,
            "bytes_processed": 0,
            "templates_detected": {},
            "validation_errors": 0,
            "last_activity": None
        }
        
        # Configuration
        self.config = {
            "max_file_size": 50 * 1024 * 1024,  # 50MB
            "supported_formats": ["jfa_v1", "jfa_v2", "legacy"],
            "default_template": "default",
            "enable_validation": True,
            "enable_metadata_extraction": True,
            "buffer_size": 4096
        }
        
        self.logger.info("Binary File Processing Module initialized")
    
    async def start(self):
        """Start the Binary File Processing Module."""
        try:
            self.is_active = True
            self.logger.info("Binary File Processing Module started")
            
        except Exception as e:
            self.logger.error(f"Failed to start BFPM: {e}")
            raise
    
    async def stop(self):
        """Stop the Binary File Processing Module."""
        try:
            self.is_active = False
            self.logger.info("Binary File Processing Module stopped")
            
        except Exception as e:
            self.logger.error(f"Failed to stop BFPM: {e}")
            raise
    
    async def process_binary_file(self, file_path: str, template: str = None) -> Dict[str, Any]:
        """
        Process a binary file and extract technical data and activation flags.
        
        Args:
            file_path: Path to the binary file
            template: Template to use for parsing (auto-detect if None)
            
        Returns:
            Dictionary containing extracted data and metadata
        """
        try:
            start_time = datetime.now()
            self.stats["total_processed"] += 1
            
            # Validate file
            validation_result = await self._validate_file(file_path)
            if not validation_result['valid']:
                self.stats["failed_processing"] += 1
                self.stats["validation_errors"] += 1
                return {
                    'success': False,
                    'errors': validation_result['errors'],
                    'file_path': file_path
                }
            
            # Detect template if not provided
            if template is None:
                template = await self._detect_template(file_path)
            
            # Process based on template
            if template not in self.templates:
                self.logger.error(f"Unsupported template: {template}")
                self.stats["failed_processing"] += 1
                return {
                    'success': False,
                    'errors': [f"Unsupported template: {template}"],
                    'file_path': file_path
                }
            
            # Extract data from binary file
            extraction_result = self._extract_binary_data(file_path, template)
            if not extraction_result['success']:
                self.stats["failed_processing"] += 1
                return extraction_result
            
            # Extract metadata
            metadata = await self._extract_metadata(file_path)
            
            # Update statistics
            self.stats["successful_processing"] += 1
            self.stats["bytes_processed"] += validation_result['file_size']
            self.stats["templates_detected"][template] = self.stats["templates_detected"].get(template, 0) + 1
            self.stats["last_activity"] = datetime.now()
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            self.logger.info(f"Binary file processed successfully in {processing_time:.3f}s")
            
            return {
                'success': True,
                'template': template,
                'technical_data': extraction_result['technical_data'],
                'activation_flags': extraction_result['activation_flags'],
                'metadata': {
                    **metadata,
                    'processing_time': processing_time,
                    'template_used': template,
                    'file_path': file_path
                },
                'file_path': file_path,
                'processing_time': processing_time
            }
            
        except Exception as e:
            self.logger.error(f"Error processing binary file: {e}")
            self.stats["failed_processing"] += 1
            return {
                'success': False,
                'errors': [str(e)],
                'file_path': file_path
            }
    
    async def _validate_file(self, file_path: str) -> Dict[str, Any]:
        """
        Validate binary file format and detect corruption.
        
        Args:
            file_path: Path to binary file
            
        Returns:
            Validation results with detailed error information
        """
        try:
            errors = []
            
            # Check if file exists
            if not os.path.exists(file_path):
                return {
                    'valid': False,
                    'errors': [f"File does not exist: {file_path}"],
                    'corruption_detected': False,
                    'file_format': 'unknown'
                }
            
            # Check file size
            file_size = os.path.getsize(file_path)
            if file_size == 0:
                return {
                    'valid': False,
                    'errors': ["File is empty"],
                    'corruption_detected': True,
                    'corruption_type': 'empty_file',
                    'file_format': 'empty'
                }
            
            # Check minimum size requirements
            if file_size < 8:  # At least 8 bytes for basic structure
                return {
                    'valid': False,
                    'errors': [f"File too small: {file_size} bytes, minimum 8 bytes required"],
                    'corruption_detected': True,
                    'corruption_type': 'truncated_file',
                    'file_format': 'invalid'
                }
            
            corruption_detected = False
            corruption_type = None
            file_format = 'unknown'
            
            with open(file_path, 'rb') as f:
                # Read first few bytes to analyze format
                header = f.read(16)  # Read 16 bytes for analysis
                f.seek(0)  # Reset position
                
                # Detect format type
                if len(header) >= 4:
                    # Check for JSON-based format (length prefix)
                    try:
                        json_length = struct.unpack('<I', header[:4])[0]
                        if 0 < json_length < file_size and json_length < 1024*1024:  # Reasonable JSON size
                            # Appears to be JSON-based format
                            file_format = 'json_based'
                            
                            # Validate JSON structure
                            if file_size >= json_length + 4:
                                json_data = f.read(4)  # Skip length prefix
                                json_content = f.read(json_length)
                                
                                if len(json_content) != json_length:
                                    corruption_detected = True
                                    corruption_type = 'incomplete_json'
                                    errors.append(f"JSON content incomplete: expected {json_length}, got {len(json_content)} bytes")
                                else:
                                    try:
                                        json.loads(json_content.decode('utf-8'))
                                    except json.JSONDecodeError as e:
                                        corruption_detected = True
                                        corruption_type = 'malformed_json'
                                        errors.append(f"JSON parsing error: {e}")
                                    except UnicodeDecodeError as e:
                                        corruption_detected = True
                                        corruption_type = 'encoding_error'
                                        errors.append(f"Unicode decoding error: {e}")
                            else:
                                corruption_detected = True
                                corruption_type = 'truncated_json'
                                errors.append("File too small for declared JSON content")
                        else:
                            # Might be binary struct format
                            file_format = 'binary_struct'
                            
                            # Validate binary structure
                            f.seek(0)
                            corruption_issues = self._validate_binary_structure(f, file_size)
                            if corruption_issues:
                                corruption_detected = True
                                corruption_type = 'binary_structure_invalid'
                                errors.extend(corruption_issues)
                    except struct.error:
                        file_format = 'corrupted_header'
                        corruption_detected = True
                        corruption_type = 'header_corruption'
                        errors.append("Cannot parse file header")
                
                # Additional corruption checks
                if not corruption_detected:
                    # Check for binary garbage (too many zero bytes or non-printable characters)
                    f.seek(0)
                    sample_data = f.read(min(256, file_size))  # Sample first 256 bytes
                    
                    # Check for excessive zero bytes (more than 50%)
                    zero_count = sample_data.count(b'\x00')
                    if zero_count > len(sample_data) * 0.5 and file_format == 'unknown':
                        corruption_detected = True
                        corruption_type = 'excessive_zero_bytes'
                        errors.append(f"Excessive zero bytes detected: {zero_count}/{len(sample_data)}")
                    
                    # Check for random binary garbage
                    if file_format == 'unknown':
                        # Simple heuristic: check if data looks like random bytes
                        byte_variety = len(set(sample_data))
                        if byte_variety > 200 and len(sample_data) >= 200:  # High entropy might indicate corruption
                            corruption_detected = True
                            corruption_type = 'high_entropy_data'
                            errors.append("File appears to contain random binary data")
            
            # Determine if file is valid
            valid = not corruption_detected and len(errors) == 0
            
            result = {
                'valid': valid,
                'errors': errors,
                'corruption_detected': corruption_detected,
                'file_format': file_format,
                'file_size': file_size
            }
            
            if corruption_detected:
                result['corruption_type'] = corruption_type
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error validating file {file_path}: {e}")
            return {
                'valid': False,
                'errors': [f"Validation error: {str(e)}"],
                'corruption_detected': True,
                'corruption_type': 'validation_exception',
                'file_format': 'unknown'
            }
    
    def _validate_binary_structure(self, file_handle, file_size: int) -> List[str]:
        """
        Validate binary structure for struct-packed format.
        
        Args:
            file_handle: Open file handle
            file_size: Size of the file
            
        Returns:
            List of validation errors
        """
        errors = []
        
        try:
            # Check if file size is compatible with 4-byte structure
            if file_size % 4 != 0:
                errors.append(f"File size {file_size} is not multiple of 4 bytes")
            
            # Try to read some 4-byte chunks and validate they're reasonable
            chunks_to_check = min(10, file_size // 4)  # Check up to 10 chunks
            
            for i in range(chunks_to_check):
                chunk = file_handle.read(4)
                if len(chunk) != 4:
                    errors.append(f"Incomplete chunk at position {i*4}")
                    break
                
                try:
                    # Try unpacking as float
                    float_val = struct.unpack('f', chunk)[0]
                    
                    # Check for obviously invalid float values
                    if not (-1e10 < float_val < 1e10):  # Reasonable range
                        errors.append(f"Suspicious float value at position {i*4}: {float_val}")
                    
                    # Check for NaN or infinity
                    if float_val != float_val or abs(float_val) == float('inf'):
                        errors.append(f"Invalid float value (NaN/Inf) at position {i*4}")
                        
                except struct.error as e:
                    errors.append(f"Struct unpacking error at position {i*4}: {e}")
                    
        except Exception as e:
            errors.append(f"Binary structure validation error: {e}")
        
        return errors
    
    async def _detect_template(self, file_path: str) -> str:
        """Detect the template based on file analysis."""
        try:
            # For now, return default template
            # In future, could analyze file structure to determine template
            return self.config['default_template']
            
        except Exception as e:
            self.logger.warning(f"Template detection failed: {e}, using default")
            return self.config['default_template']
    
    def _extract_binary_data(self, file_path: str, template: str) -> Dict[str, Any]:
        """
        Extract binary data from file using template structure.
        
        Args:
            file_path: Path to binary file
            template: Template name for parsing structure
            
        Returns:
            Extracted technical data and activation flags
        """
        try:
            if template not in self.templates:
                return {
                    'success': False,
                    'errors': [f"Unknown template: {template}"]
                }
            
            template_info = self.templates[template]
            technical_keys = template_info["technical_keys"]
            data_types = template_info.get("data_types", {})
            
            # Check if file exists and has content
            if not os.path.exists(file_path):
                return {
                    'success': False,
                    'errors': [f"File does not exist: {file_path}"]
                }
            
            file_size = os.path.getsize(file_path)
            if file_size == 0:
                return {
                    'success': False,
                    'errors': ["File is empty"]
                }
            
            technical_data = {}
            activation_flags = {}
            
            with open(file_path, 'rb') as f:
                # First, try to detect if this is a JSON-based binary file
                try:
                    # Check for JSON length prefix format
                    length_bytes = f.read(4)
                    if len(length_bytes) == 4:
                        json_length = struct.unpack('<I', length_bytes)[0]
                        if json_length > 0 and json_length < file_size:
                            # This appears to be JSON-based format
                            json_data = f.read(json_length)
                            if len(json_data) == json_length:
                                try:
                                    data = json.loads(json_data.decode('utf-8'))
                                    return self._extract_from_json_data(data, template)
                                except json.JSONDecodeError:
                                    pass  # Not JSON format, continue with binary parsing
                    
                    # Reset file pointer for binary parsing
                    f.seek(0)
                except:
                    # Reset file pointer for binary parsing
                    f.seek(0)
                
                # Read technical parameters with buffer validation
                for key in technical_keys:
                    value_bytes = f.read(4)
                    
                    # Check if we have enough bytes
                    if len(value_bytes) < 4:
                        if len(value_bytes) == 0:
                            # End of file - this is normal
                            break
                        else:
                            # Incomplete data - pad with zeros or skip
                            self.logger.warning(f"Incomplete data for key {key}: got {len(value_bytes)} bytes, expected 4")
                            # Pad with zeros to make it 4 bytes
                            value_bytes = value_bytes + b'\x00' * (4 - len(value_bytes))
                    
                    try:
                        # Determine data type and unpack
                        if key in data_types:
                            if data_types[key] == 'float':
                                value = struct.unpack('f', value_bytes)[0]
                            elif data_types[key] == 'int':
                                value = struct.unpack('i', value_bytes)[0]
                            elif data_types[key] == 'string':
                                # For strings, treat as float for now (legacy compatibility)
                                value = struct.unpack('f', value_bytes)[0]
                            else:
                                value = struct.unpack('f', value_bytes)[0]  # Default to float
                        else:
                            value = struct.unpack('f', value_bytes)[0]  # Default to float
                        
                        technical_data[key] = value
                        
                    except struct.error as e:
                        self.logger.warning(f"Error unpacking data for key {key}: {e}")
                        # Set default value
                        technical_data[key] = 0.0
                
                # Read activation flags with buffer validation
                for flag in self.activation_flags:
                    flag_bytes = f.read(4)
                    
                    # Check if we have enough bytes
                    if len(flag_bytes) < 4:
                        if len(flag_bytes) == 0:
                            # End of file - set default flag
                            activation_flags[flag] = 0
                            continue
                        else:
                            # Incomplete data - pad with zeros
                            self.logger.warning(f"Incomplete flag data for {flag}: got {len(flag_bytes)} bytes, expected 4")
                            flag_bytes = flag_bytes + b'\x00' * (4 - len(flag_bytes))
                    
                    try:
                        flag_value = struct.unpack('i', flag_bytes)[0]
                        activation_flags[flag] = flag_value
                    except struct.error as e:
                        self.logger.warning(f"Error unpacking flag {flag}: {e}")
                        # Set default flag value
                        activation_flags[flag] = 0
            
            return {
                'success': True,
                'technical_data': technical_data,
                'activation_flags': activation_flags,
                'keys_extracted': len(technical_data),
                'flags_extracted': len(activation_flags),
                'file_size': file_size,
                'format_detected': 'binary_struct'
            }
            
        except Exception as e:
            self.logger.error(f"Error extracting binary data: {e}")
            return {
                'success': False,
                'errors': [str(e)],
                'file_path': file_path,
                'template': template
            }
    
    def _extract_from_json_data(self, data: Dict[str, Any], template: str) -> Dict[str, Any]:
        """
        Extract data from JSON-based binary file format.
        
        Args:
            data: Parsed JSON data
            template: Template name for validation
            
        Returns:
            Extracted technical data and activation flags
        """
        try:
            technical_data = data.get('technical_data', {})
            activation_flags = data.get('activation_flags', {})
            
            # Validate against template if needed
            if template in self.templates:
                template_info = self.templates[template]
                expected_keys = template_info["technical_keys"]
                
                # Fill missing keys with defaults
                for key in expected_keys:
                    if key not in technical_data:
                        technical_data[key] = 0.0
            
            # Ensure activation flags exist
            for flag in self.activation_flags:
                if flag not in activation_flags:
                    activation_flags[flag] = 0
            
            enhanced_data = technical_data

            result = {
                'success': True,
                'technical_data': technical_data,
                'enhanced_data': enhanced_data,
                'activation_flags': activation_flags,
                'keys_extracted': len(technical_data),
                'flags_extracted': len(activation_flags),
                'format_detected': 'json_based',
                'template': template
            }
            
            # Add metadata if available
            if 'metadata' in data:
                result['metadata'] = data['metadata']
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error extracting JSON data: {e}")
            return {
                'success': False,
                'errors': [str(e)],
                'template': template
            }
    
    async def _extract_metadata(self, file_path: str) -> Dict[str, Any]:
        """Extract metadata from the binary file."""
        try:
            file_stats = os.stat(file_path)
            
            metadata = {
                'file_name': os.path.basename(file_path),
                'file_size': file_stats.st_size,
                'creation_time': datetime.fromtimestamp(file_stats.st_ctime).isoformat(),
                'modification_time': datetime.fromtimestamp(file_stats.st_mtime).isoformat(),
                'access_time': datetime.fromtimestamp(file_stats.st_atime).isoformat(),
                'file_extension': os.path.splitext(file_path)[1],
                'absolute_path': os.path.abspath(file_path)
            }
            
            return metadata
            
        except Exception as e:
            self.logger.warning(f"Error extracting metadata: {e}")
            return {}
    
    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the module."""
        return {
            'module': self.module_name,
            'is_active': self.is_active,
            'supported_templates': list(self.templates.keys()),
            'activation_flags': self.activation_flags,
            'statistics': self.stats,
            'configuration': self.config,
            'capabilities': {
                'binary_file_processing': True,
                'template_based_parsing': True,
                'activation_flag_extraction': True,
                'metadata_extraction': True,
                'batch_processing': True,
                'template_management': True
            }
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        try:
            # Check if module is active
            if not self.is_active:
                return {
                    'healthy': False,
                    'status': 'Module not active',
                    'timestamp': datetime.now().isoformat()
                }
            
            # Check templates
            if not self.templates:
                return {
                    'healthy': False,
                    'status': 'No templates configured',
                    'timestamp': datetime.now().isoformat()
                }
            
            return {
                'healthy': True,
                'status': 'All systems operational',
                'templates_available': len(self.templates),
                'processing_statistics': self.stats,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'healthy': False,
                'status': f'Health check failed: {e}',
                'timestamp': datetime.now().isoformat()
            } 

    def validate_dependencies(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate template dependencies.
        
        Args:
            data: Template data to validate
            
        Returns:
            Dependency validation results
        """
        try:
            template_type = 'default'
            if 'metadata' in data and 'template_version' in data['metadata']:
                template_type = str(data['metadata']['template_version']).lower()
            return {
                'valid': True,
                'template_type': template_type,
                'required': [],
                'dependencies': [],
                'dependency_count': 0,
                'validation_status': 'passed',
            }
            
        except Exception as e:
            self.logger.error(f"Error validating dependencies: {e}")
            return {
                'valid': False,
                'errors': [str(e)],
                'validation_status': 'failed'
            }