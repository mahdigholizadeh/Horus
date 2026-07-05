"""
JSON Data Processing Module (JDPM) for JFA Microservice

This module handles core JSON processing operations:
- JSON parsing and validation
- Template data extraction
- Data structure normalization
- Preprocessing for analysis
- Complex JSON manipulation
"""

import logging
import asyncio
import json
import copy
from typing import Dict, Any, List, Optional
from datetime import datetime
import re


class JSONDataProcessingModule:
    """
    JSON Data Processing Module
    
    Core module for JSON template processing and data manipulation
    specialized for JFA analysis workflows.
    """
    
    def __init__(self):
        """Initialize the JDPM module."""
        self.logger = logging.getLogger(__name__)
        self.module_name = "JDPM"
        self.is_active = False
        
        # JSON processing configuration
        self.processing_config = {
            "max_depth": 10,
            "max_size": 10 * 1024 * 1024,  # 10MB
            "strict_parsing": True,
            "normalize_keys": True,
            "preserve_order": True,
            "validate_encoding": True
        }
        
        # Template structure definitions
        self.template_structure = {
            "required_fields": ["id", "object", "created", "model", "choices"],
            "optional_fields": ["usage", "system_fingerprint"],
            "choices_required": ["message", "finish_reason"],
            "message_required": ["role", "content"],
            "jfa_specific": ["flag", "loca", "cust", "sinf"]
        }
        
        # Processing statistics
        self.stats = {
            "total_processed": 0,
            "successful_parsing": 0,
            "failed_parsing": 0,
            "templates_extracted": 0,
            "data_normalized": 0,
            "processing_time": 0.0,
            "last_activity": None
        }
        
        # Data processing metrics
        self.processing_metrics = {
            "json_parsing_rate": 0.0,
            "template_extraction_rate": 0.0,
            "normalization_rate": 0.0,
            "average_template_size": 0.0,
            "processing_speed": 0.0
        }
        
        self.logger.info(f"{self.module_name} initialized successfully")
    
    async def start(self):
        """Start the JDPM module."""
        try:
            self.is_active = True
            self.logger.info(f"{self.module_name} started successfully")
        except Exception as e:
            self.logger.error(f"Failed to start {self.module_name}: {e}")
            raise
    
    async def stop(self):
        """Stop the JDPM module."""
        try:
            self.is_active = False
            self.logger.info(f"{self.module_name} stopped successfully")
        except Exception as e:
            self.logger.error(f"Failed to stop {self.module_name}: {e}")
            raise
    
    async def process_json_data(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process JSON data for JFA analysis.
        
        Args:
            input_data: Raw input data containing JSON template
            
        Returns:
            Processed JSON data result
        """
        try:
            start_time = datetime.now()
            self.stats["total_processed"] += 1
            
            # Step 1: Parse and validate JSON structure
            parse_result = await self._parse_json_structure(input_data)
            if not parse_result["success"]:
                self.stats["failed_parsing"] += 1
                return parse_result
            
            # Step 2: Extract template data
            extraction_result = await self._extract_template_data(parse_result["parsed_data"])
            if not extraction_result["success"]:
                return extraction_result
            
            # Step 3: Normalize data structure
            normalization_result = await self._normalize_data_structure(extraction_result["template_data"])
            
            # Step 4: Prepare for analysis
            analysis_prep = await self._prepare_for_analysis(normalization_result["normalized_data"])
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Update statistics
            self.stats["successful_parsing"] += 1
            self.stats["templates_extracted"] += 1
            self.stats["data_normalized"] += 1
            self.stats["processing_time"] += processing_time
            self.stats["last_activity"] = datetime.now()
            
            # Update metrics
            await self._update_processing_metrics(processing_time, normalization_result["normalized_data"])
            
            return {
                "success": True,
                "processed_json": analysis_prep["prepared_data"],
                "parsing_result": parse_result,
                "extraction_result": extraction_result,
                "normalization_result": normalization_result,
                "processing_time": processing_time,
                "template_info": {
                    "template_id": extraction_result["template_data"].get("id", "unknown"),
                    "model": extraction_result["template_data"].get("model", "unknown"),
                    "created": extraction_result["template_data"].get("created", 0),
                    "size": len(str(input_data))
                },
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error processing JSON data: {e}")
            self.stats["failed_parsing"] += 1
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _parse_json_structure(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse and validate JSON structure."""
        try:
            # Handle different input formats
            if isinstance(input_data, str):
                # Parse JSON string
                parsed_data = json.loads(input_data)
            elif isinstance(input_data, dict):
                # Already a dictionary, make a deep copy
                parsed_data = copy.deepcopy(input_data)
            else:
                return {
                    "success": False,
                    "error": "Invalid input data type"
                }
            
            # Validate JSON structure
            validation_result = self._validate_json_structure(parsed_data)
            if not validation_result["valid"]:
                return {
                    "success": False,
                    "error": "JSON structure validation failed",
                    "details": validation_result["errors"]
                }
            
            # Check size limits
            json_size = len(str(parsed_data))
            if json_size > self.processing_config["max_size"]:
                return {
                    "success": False,
                    "error": f"JSON size {json_size} exceeds maximum {self.processing_config['max_size']}"
                }
            
            return {
                "success": True,
                "parsed_data": parsed_data,
                "validation_result": validation_result,
                "size": json_size
            }
            
        except json.JSONDecodeError as e:
            return {
                "success": False,
                "error": f"JSON decode error: {str(e)}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"JSON parsing error: {str(e)}"
            }
    
    def _validate_json_structure(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate JSON structure for JFA requirements."""
        try:
            errors = []
            
            # Check required top-level fields
            for field in self.template_structure["required_fields"]:
                if field not in data:
                    errors.append(f"Missing required field: {field}")
            
            # Check choices structure if present
            if "choices" in data:
                choices = data["choices"]
                
                # Check required choices fields
                for field in self.template_structure["choices_required"]:
                    if field not in choices:
                        errors.append(f"Missing required choices field: {field}")
                
                # Check message structure if present
                if "message" in choices:
                    message = choices["message"]
                    for field in self.template_structure["message_required"]:
                        if field not in message:
                            errors.append(f"Missing required message field: {field}")
            
            # Check data types
            if "id" in data and not isinstance(data["id"], str):
                errors.append("Field 'id' must be string")
            
            if "created" in data and not isinstance(data["created"], (int, float)):
                errors.append("Field 'created' must be number")
            
            if "model" in data and not isinstance(data["model"], str):
                errors.append("Field 'model' must be string")
            
            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "structure_score": max(0, 100 - len(errors) * 10)
            }
            
        except Exception as e:
            return {
                "valid": False,
                "errors": [f"Structure validation error: {str(e)}"],
                "structure_score": 0
            }
    
    async def _extract_template_data(self, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract template data for JFA processing."""
        try:
            # Extract basic template information
            template_data = {
                "id": parsed_data.get("id", ""),
                "object": parsed_data.get("object", ""),
                "created": parsed_data.get("created", 0),
                "model": parsed_data.get("model", ""),
                "usage": parsed_data.get("usage", {})
            }
            
            # Extract choices data
            choices = parsed_data.get("choices", {})
            if choices:
                template_data["choices"] = choices
                
                # Extract message data
                message = choices.get("message", {})
                if message:
                    template_data["message"] = {
                        "role": message.get("role", ""),
                        "content": message.get("content", "")
                    }
                
                # Extract JFA-specific data
                jfa_data = {}
                for field in self.template_structure["jfa_specific"]:
                    if field in choices:
                        jfa_data[field] = choices[field]
                
                if jfa_data:
                    template_data["jfa_data"] = jfa_data
            
            return {
                "success": True,
                "template_data": template_data,
                "extraction_stats": {
                    "fields_extracted": len(template_data),
                    "jfa_fields": len(template_data.get("jfa_data", {})),
                    "has_choices": "choices" in template_data,
                    "has_message": "message" in template_data
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Template extraction error: {str(e)}"
            }
    
    async def _normalize_data_structure(self, template_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize data structure for consistent processing."""
        try:
            normalized_data = copy.deepcopy(template_data)
            
            # Normalize string fields
            string_fields = ["id", "object", "model"]
            for field in string_fields:
                if field in normalized_data and normalized_data[field]:
                    normalized_data[field] = str(normalized_data[field]).strip()
            
            # Normalize numeric fields
            if "created" in normalized_data:
                try:
                    normalized_data["created"] = int(normalized_data["created"])
                except (ValueError, TypeError):
                    normalized_data["created"] = 0
            
            # Normalize JFA data if present
            if "jfa_data" in normalized_data:
                normalized_jfa = await self._normalize_jfa_data(normalized_data["jfa_data"])
                normalized_data["jfa_data"] = normalized_jfa["normalized_jfa"]
            
            # Add normalization metadata
            normalization_metadata = {
                "normalized_at": datetime.now().isoformat(),
                "normalization_rules_applied": ["string_trim", "numeric_conversion", "jfa_normalization"],
                "data_quality_score": self._calculate_data_quality_score(normalized_data)
            }
            
            return {
                "success": True,
                "normalized_data": normalized_data,
                "normalization_metadata": normalization_metadata,
                "normalization_stats": {
                    "fields_normalized": len(normalized_data),
                    "quality_score": normalization_metadata["data_quality_score"]
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Data normalization error: {str(e)}"
            }
    
    async def _normalize_jfa_data(self, jfa_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize JFA-specific data fields."""
        try:
            normalized_jfa = {}
            
            # Normalize flag data
            if "flag" in jfa_data:
                flag_data = jfa_data["flag"]
                normalized_flag = {}
                flag_fields = ["vald", "calc", "plat", "mpsz", "econ", "rcon", "mode"]
                
                for field in flag_fields:
                    if field in flag_data:
                        try:
                            normalized_flag[field] = int(flag_data[field])
                        except (ValueError, TypeError):
                            normalized_flag[field] = 0
                
                normalized_jfa["flag"] = normalized_flag
            
            # Normalize location data
            if "loca" in jfa_data:
                loca_data = jfa_data["loca"]
                normalized_loca = {}
                
                # String fields
                string_fields = ["Ecit", "Fcit"]
                for field in string_fields:
                    if field in loca_data:
                        normalized_loca[field] = str(loca_data[field]).strip()
                
                # Numeric fields
                numeric_fields = ["lat", "lng"]
                for field in numeric_fields:
                    if field in loca_data:
                        try:
                            normalized_loca[field] = float(loca_data[field])
                        except (ValueError, TypeError):
                            normalized_loca[field] = 0.0
                
                normalized_jfa["loca"] = normalized_loca
            
            # Normalize customer data
            if "cust" in jfa_data:
                cust_data = jfa_data["cust"]
                normalized_cust = {}
                cust_fields = ["mode", "need", "npsz"]
                
                for field in cust_fields:
                    if field in cust_data:
                        try:
                            normalized_cust[field] = int(cust_data[field])
                        except (ValueError, TypeError):
                            normalized_cust[field] = 0
                
                normalized_jfa["cust"] = normalized_cust
            
            # Normalize solar information data
            if "sinf" in jfa_data:
                sinf_data = jfa_data["sinf"]
                normalized_sinf = {}
                
                # All sinf fields are integers
                sinf_fields = [
                    "mfreg", "mled", "mlcd", "mtele", "mlamp", "mpump", "mcool", "mcamd",
                    "mpc", "mpri", "mwel", "mmlo", "nfreg", "nled", "nlcd", "ntele",
                    "nlamp", "npump", "ncool", "ncamd", "npc", "npri", "nwel", "nmlo"
                ]
                
                for field in sinf_fields:
                    if field in sinf_data:
                        try:
                            normalized_sinf[field] = int(sinf_data[field])
                        except (ValueError, TypeError):
                            normalized_sinf[field] = 0
                
                normalized_jfa["sinf"] = normalized_sinf
            
            return {
                "success": True,
                "normalized_jfa": normalized_jfa
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"JFA data normalization error: {str(e)}"
            }
    
    def _calculate_data_quality_score(self, data: Dict[str, Any]) -> float:
        """Calculate data quality score (0-100)."""
        try:
            score = 100.0
            
            # Check for missing required fields
            required_fields = ["id", "model", "created"]
            for field in required_fields:
                if field not in data or not data[field]:
                    score -= 20
            
            # Check for JFA data presence
            if "jfa_data" not in data:
                score -= 30
            else:
                jfa_data = data["jfa_data"]
                required_jfa = ["flag", "loca", "cust", "sinf"]
                for field in required_jfa:
                    if field not in jfa_data:
                        score -= 10
            
            # Check message data
            if "message" not in data:
                score -= 10
            
            return max(0.0, score)
            
        except Exception as e:
            self.logger.error(f"Error calculating data quality score: {e}")
            return 0.0
    
    async def _prepare_for_analysis(self, normalized_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare normalized data for analysis."""
        try:
            prepared_data = copy.deepcopy(normalized_data)
            
            # Add analysis metadata
            analysis_metadata = {
                "prepared_at": datetime.now().isoformat(),
                "data_ready": True,
                "analysis_flags": {
                    "has_template": True,
                    "has_jfa_data": "jfa_data" in prepared_data,
                    "validation_ready": True,
                    "binary_ready": "jfa_data" in prepared_data
                }
            }
            
            prepared_data["analysis_metadata"] = analysis_metadata
            
            return {
                "success": True,
                "prepared_data": prepared_data,
                "preparation_stats": {
                    "data_ready": True,
                    "metadata_added": True,
                    "flags_set": len(analysis_metadata["analysis_flags"])
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Analysis preparation error: {str(e)}"
            }
    
    async def _update_processing_metrics(self, processing_time: float, normalized_data: Dict[str, Any]):
        """Update processing metrics."""
        try:
            # Update processing speed
            total_processed = self.stats["total_processed"]
            current_speed = self.processing_metrics["processing_speed"]
            new_speed = 1.0 / processing_time if processing_time > 0 else 0
            self.processing_metrics["processing_speed"] = (
                (current_speed * (total_processed - 1) + new_speed) / total_processed
            )
            
            # Update template size average
            template_size = len(str(normalized_data))
            current_avg_size = self.processing_metrics["average_template_size"]
            self.processing_metrics["average_template_size"] = (
                (current_avg_size * (total_processed - 1) + template_size) / total_processed
            )
            
            # Update success rates
            if total_processed > 0:
                self.processing_metrics["json_parsing_rate"] = (
                    self.stats["successful_parsing"] / total_processed
                )
                self.processing_metrics["template_extraction_rate"] = (
                    self.stats["templates_extracted"] / total_processed
                )
                self.processing_metrics["normalization_rate"] = (
                    self.stats["data_normalized"] / total_processed
                )
            
        except Exception as e:
            self.logger.error(f"Error updating processing metrics: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of the JDPM module."""
        return {
            "module": self.module_name,
            "is_active": self.is_active,
            "statistics": self.stats,
            "processing_metrics": self.processing_metrics,
            "configuration": self.processing_config,
            "template_structure": self.template_structure,
            "timestamp": datetime.now().isoformat()
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        try:
            # Test with sample JSON data
            test_data = {
                "id": "test-001",
                "object": "chat.completion",
                "created": int(datetime.now().timestamp()),
                "model": "gpt-4",
                "choices": {
                    "message": {
                        "role": "assistant",
                        "content": "test content"
                    },
                    "finish_reason": "stop"
                }
            }
            
            start_time = datetime.now()
            result = await self.process_json_data(test_data)
            test_time = (datetime.now() - start_time).total_seconds()
            
            return {
                "healthy": self.is_active and result["success"],
                "module": self.module_name,
                "timestamp": datetime.now().isoformat(),
                "test_performance": test_time,
                "statistics": self.stats,
                "processing_capabilities": {
                    "json_parsing": True,
                    "template_extraction": True,
                    "data_normalization": True,
                    "jfa_processing": True
                }
            }
            
        except Exception as e:
            return {
                "healthy": False,
                "module": self.module_name,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            } 