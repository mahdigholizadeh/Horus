"""
Output Processing Module (OPM) for TPP Microservice

This module handles output generation and formatting:
- Final output data structure creation
- TPP_flag addition (legacy compatibility)
- Metadata enrichment
- Response formatting
"""

import logging
import asyncio
import json
from typing import Dict, Any, List, Optional
from datetime import datetime


class OutputProcessingModule:
    """
    Output Processing Module
    
    Handles final output generation and formatting for TPP processed data.
    """
    
    def __init__(self):
        """Initialize the OPM module."""
        self.logger = logging.getLogger(__name__)
        self.module_name = "OPM"
        self.is_active = False
        
        # Output configuration
        self.output_config = {
            "add_tpp_flag": True,
            "tpp_flag_value": 1,
            "include_metadata": True,
            "include_processing_stats": True,
            "include_timestamp": True,
            "preserve_original_fields": True
        }
        
        # Statistics
        self.stats = {
            "total_generated": 0,
            "successful_outputs": 0,
            "failed_outputs": 0,
            "total_processing_time": 0.0,
            "last_activity": None
        }
        
        self.logger.info(f"{self.module_name} initialized successfully")
    
    async def start(self):
        """Start the OPM module."""
        try:
            self.is_active = True
            self.logger.info(f"{self.module_name} started successfully")
        except Exception as e:
            self.logger.error(f"Failed to start {self.module_name}: {e}")
            raise
    
    async def stop(self):
        """Stop the OPM module."""
        try:
            self.is_active = False
            self.logger.info(f"{self.module_name} stopped successfully")
        except Exception as e:
            self.logger.error(f"Failed to stop {self.module_name}: {e}")
            raise
    
    async def generate_output(self, original_data: Dict[str, Any], filter_result: Dict[str, Any], 
                            processing_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate final output data structure.
        
        Args:
            original_data: Original input data
            filter_result: Result from text filtering
            processing_metadata: Processing metadata
            
        Returns:
            Final output data structure
        """
        try:
            start_time = datetime.now()
            
            # Start with original data structure
            output_data = original_data.copy() if self.output_config["preserve_original_fields"] else {}
            
            # Update message_text with filtered text
            if filter_result.get("success", False):
                output_data["message_text"] = filter_result["filtered_text"]
            else:
                # If filtering failed, keep original text
                output_data["message_text"] = original_data.get("message_text", "")
            
            # Add TPP flag (legacy compatibility)
            if self.output_config["add_tpp_flag"]:
                output_data["TPP_flag"] = self.output_config["tpp_flag_value"]
            
            # Add processing metadata
            if self.output_config["include_metadata"]:
                output_data["tpp_metadata"] = self._create_processing_metadata(
                    filter_result, processing_metadata
                )
            
            # Add processing statistics
            if self.output_config["include_processing_stats"]:
                output_data["tpp_processing_stats"] = self._create_processing_stats(filter_result)
            
            # Add timestamp
            if self.output_config["include_timestamp"]:
                output_data["tpp_processed_at"] = datetime.now().isoformat()
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Update statistics
            self.stats["total_generated"] += 1
            self.stats["successful_outputs"] += 1
            self.stats["total_processing_time"] += processing_time
            self.stats["last_activity"] = datetime.now()
            
            return {
                "success": True,
                "output_data": output_data,
                "processing_time": processing_time,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error generating output: {e}")
            self.stats["failed_outputs"] += 1
            
            # Return original data on error
            return {
                "success": False,
                "output_data": original_data,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def _create_processing_metadata(self, filter_result: Dict[str, Any], 
                                  processing_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Create processing metadata."""
        try:
            metadata = {
                "service": "TPP",
                "version": "1.0.0",
                "processed_at": datetime.now().isoformat(),
                "language": processing_metadata.get("language", "unknown"),
                "spam_detected": filter_result.get("spam_detected", False),
                "processing_pipeline": ["input_validation", "language_detection", "text_processing", "spam_filtering", "output_generation"]
            }
            
            # Add language-specific metadata
            if processing_metadata.get("language") == "fa":
                metadata["persian_processing"] = True
                metadata["alphabet_filtering"] = True
            
            # Add filter method information
            if "filter_details" in filter_result:
                metadata["filter_method"] = filter_result["filter_details"].get("filter_method", "unknown")
            
            return metadata
            
        except Exception as e:
            self.logger.error(f"Error creating processing metadata: {e}")
            return {
                "service": "TPP",
                "error": str(e),
                "processed_at": datetime.now().isoformat()
            }
    
    def _create_processing_stats(self, filter_result: Dict[str, Any]) -> Dict[str, Any]:
        """Create processing statistics."""
        try:
            stats = {}
            
            # Extract statistics from filter result
            if "statistics" in filter_result:
                filter_stats = filter_result["statistics"]
                stats.update({
                    "original_word_count": filter_stats.get("original_word_count", 0),
                    "final_word_count": filter_stats.get("final_word_count", 0),
                    "words_removed": filter_stats.get("words_removed", 0),
                    "reduction_percentage": filter_stats.get("reduction_percentage", 0.0),
                    "original_character_count": filter_stats.get("original_length", 0),
                    "final_character_count": filter_stats.get("final_length", 0),
                    "characters_removed": filter_stats.get("characters_removed", 0)
                })
            
            # Add processing time information
            stats["processing_time"] = filter_result.get("processing_time", 0.0)
            
            # Add spam analysis information
            if "spam_analysis" in filter_result:
                spam_analysis = filter_result["spam_analysis"]
                stats.update({
                    "spam_words_found": spam_analysis.get("spam_words_count", 0),
                    "spam_percentage": spam_analysis.get("spam_percentage", 0.0),
                    "spam_severity": spam_analysis.get("severity", "clean")
                })
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error creating processing stats: {e}")
            return {"error": str(e)}
    
    async def format_json_output(self, output_data: Dict[str, Any], 
                               format_options: Dict[str, Any] = None) -> str:
        """Format output as JSON string."""
        try:
            options = format_options or {}
            
            # Default JSON formatting options
            json_options = {
                "ensure_ascii": False,
                "indent": options.get("indent", 4),
                "separators": (',', ': '),
                "sort_keys": options.get("sort_keys", False)
            }
            
            return json.dumps(output_data, **json_options)
            
        except Exception as e:
            self.logger.error(f"Error formatting JSON output: {e}")
            return json.dumps({"error": str(e)}, ensure_ascii=False, indent=2)
    
    async def format_text_output(self, output_data: Dict[str, Any]) -> str:
        """Format output as plain text."""
        try:
            return output_data.get("message_text", "")
            
        except Exception as e:
            self.logger.error(f"Error formatting text output: {e}")
            return f"Error formatting text: {str(e)}"
    
    async def create_legacy_output(self, original_data: Dict[str, Any], filtered_text: str) -> Dict[str, Any]:
        """Create legacy-compatible output (similar to original TPP)."""
        try:
            # Create output in original TPP format
            output_data = original_data.copy()
            output_data["message_text"] = filtered_text
            output_data["TPP_flag"] = 1
            
            return {
                "success": True,
                "output_data": output_data,
                "legacy_format": True,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error creating legacy output: {e}")
            return {
                "success": False,
                "output_data": original_data,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def batch_generate_outputs(self, batch_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate outputs for multiple items."""
        try:
            results = []
            
            for item in batch_data:
                original_data = item.get("original_data", {})
                filter_result = item.get("filter_result", {})
                processing_metadata = item.get("processing_metadata", {})
                
                result = await self.generate_output(original_data, filter_result, processing_metadata)
                results.append(result)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error in batch output generation: {e}")
            raise
    
    async def validate_output(self, output_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate generated output."""
        try:
            validation_result = {
                "valid": True,
                "errors": [],
                "warnings": []
            }
            
            # Check required fields
            required_fields = ["message_text"]
            for field in required_fields:
                if field not in output_data:
                    validation_result["valid"] = False
                    validation_result["errors"].append(f"Missing required field: {field}")
            
            # Check TPP flag if enabled
            if self.output_config["add_tpp_flag"] and "TPP_flag" not in output_data:
                validation_result["warnings"].append("TPP_flag not found in output")
            
            # Check data types
            if "message_text" in output_data and not isinstance(output_data["message_text"], str):
                validation_result["valid"] = False
                validation_result["errors"].append("message_text must be a string")
            
            return validation_result
            
        except Exception as e:
            return {
                "valid": False,
                "errors": [f"Validation error: {str(e)}"],
                "warnings": []
            }
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status."""
        return {
            "module": self.module_name,
            "is_active": self.is_active,
            "statistics": self.stats,
            "configuration": self.output_config,
            "timestamp": datetime.now().isoformat()
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        try:
            # Test output generation
            test_original = {"message_text": "Test message", "request_id": "test123"}
            test_filter = {"success": True, "filtered_text": "Test message", "spam_detected": False}
            test_metadata = {"language": "en"}
            
            result = await self.generate_output(test_original, test_filter, test_metadata)
            
            return {
                "healthy": self.is_active and result["success"],
                "module": self.module_name,
                "timestamp": datetime.now().isoformat(),
                "test_result": result["success"]
            }
            
        except Exception as e:
            return {
                "healthy": False,
                "module": self.module_name,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            } 