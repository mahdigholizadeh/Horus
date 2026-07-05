"""
API Error Handler Module for JFA Microservice

Comprehensive error handling for JFA JSON analysis and template validation operations
with mapping to internal error codes and automated recovery strategies.
Integrates with EMM for centralized error management.
"""

import asyncio
import logging
import json
import re
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from enum import Enum

from EMM.emm import ErrorManagementModule


class JFAErrorType(Enum):
    """JFA-specific error types."""
    # Template Processing Errors
    TEMPLATE_TOO_LARGE = "template_too_large"
    INVALID_JSON_FORMAT = "invalid_json_format"
    TEMPLATE_STRUCTURE_ERROR = "template_structure_error"
    TEMPLATE_VALIDATION_FAILED = "template_validation_failed"
    
    # Binary Generation Errors
    BINARY_GENERATION_FAILED = "binary_generation_failed"
    COMPRESSION_ERROR = "compression_error"
    BINARY_FORMAT_ERROR = "binary_format_error"
    CHECKSUM_VALIDATION_FAILED = "checksum_validation_failed"
    
    # Data Analysis Errors
    ANALYSIS_FAILED = "analysis_failed"
    PATTERN_DETECTION_ERROR = "pattern_detection_error"
    ANOMALY_DETECTION_ERROR = "anomaly_detection_error"
    DEEP_ANALYSIS_ERROR = "deep_analysis_error"
    
    # Validation Rule Errors
    VALIDATION_RULE_ERROR = "validation_rule_error"
    CUSTOM_VALIDATOR_ERROR = "custom_validator_error"
    RULE_CONFLICT_ERROR = "rule_conflict_error"
    
    # File Processing Errors
    FILE_READ_ERROR = "file_read_error"
    FILE_WRITE_ERROR = "file_write_error"
    BATCH_PROCESSING_ERROR = "batch_processing_error"
    
    # Configuration Errors
    INVALID_CONFIGURATION = "invalid_configuration"
    MODULE_NOT_AVAILABLE = "module_not_available"
    ANALYSIS_MODE_ERROR = "analysis_mode_error"
    
    # General Errors
    PROCESSING_TIMEOUT = "processing_timeout"
    MEMORY_ERROR = "memory_error"
    UNKNOWN_ERROR = "unknown_error"


class JFAAPIErrorHandler:
    """
    JFA API Error Handler
    
    Maps JFA processing errors to internal error codes and provides
    automated recovery strategies with EMM integration.
    """
    
    def __init__(self):
        """Initialize the JFA API Error Handler."""
        self.logger = logging.getLogger(__name__)
        self.error_manager = ErrorManagementModule()
        
        # Error recovery strategies
        self.recovery_strategies = {
            JFAErrorType.TEMPLATE_TOO_LARGE: self._handle_template_too_large,
            JFAErrorType.INVALID_JSON_FORMAT: self._handle_invalid_json,
            JFAErrorType.TEMPLATE_STRUCTURE_ERROR: self._handle_structure_error,
            JFAErrorType.TEMPLATE_VALIDATION_FAILED: self._handle_validation_failed,
            JFAErrorType.BINARY_GENERATION_FAILED: self._handle_binary_generation_failed,
            JFAErrorType.COMPRESSION_ERROR: self._handle_compression_error,
            JFAErrorType.BINARY_FORMAT_ERROR: self._handle_binary_format_error,
            JFAErrorType.CHECKSUM_VALIDATION_FAILED: self._handle_checksum_failed,
            JFAErrorType.ANALYSIS_FAILED: self._handle_analysis_failed,
            JFAErrorType.PATTERN_DETECTION_ERROR: self._handle_pattern_detection_error,
            JFAErrorType.ANOMALY_DETECTION_ERROR: self._handle_anomaly_detection_error,
            JFAErrorType.DEEP_ANALYSIS_ERROR: self._handle_deep_analysis_error,
            JFAErrorType.VALIDATION_RULE_ERROR: self._handle_validation_rule_error,
            JFAErrorType.CUSTOM_VALIDATOR_ERROR: self._handle_custom_validator_error,
            JFAErrorType.RULE_CONFLICT_ERROR: self._handle_rule_conflict_error,
            JFAErrorType.FILE_READ_ERROR: self._handle_file_read_error,
            JFAErrorType.FILE_WRITE_ERROR: self._handle_file_write_error,
            JFAErrorType.BATCH_PROCESSING_ERROR: self._handle_batch_error,
            JFAErrorType.INVALID_CONFIGURATION: self._handle_invalid_config,
            JFAErrorType.MODULE_NOT_AVAILABLE: self._handle_module_unavailable,
            JFAErrorType.ANALYSIS_MODE_ERROR: self._handle_analysis_mode_error,
            JFAErrorType.PROCESSING_TIMEOUT: self._handle_timeout,
            JFAErrorType.MEMORY_ERROR: self._handle_memory_error,
            JFAErrorType.UNKNOWN_ERROR: self._handle_unknown_error
        }
        
        # Error code mapping to internal codes
        self.error_code_mapping = {
            JFAErrorType.TEMPLATE_TOO_LARGE: "01010401001001",  # JFA specific error codes
            JFAErrorType.INVALID_JSON_FORMAT: "01010401002001",
            JFAErrorType.TEMPLATE_STRUCTURE_ERROR: "01010401003001",
            JFAErrorType.TEMPLATE_VALIDATION_FAILED: "01010401004001",
            JFAErrorType.BINARY_GENERATION_FAILED: "01010402001001",
            JFAErrorType.COMPRESSION_ERROR: "01010402002001",
            JFAErrorType.BINARY_FORMAT_ERROR: "01010402003001",
            JFAErrorType.CHECKSUM_VALIDATION_FAILED: "01010402004001",
            JFAErrorType.ANALYSIS_FAILED: "01010403001001",
            JFAErrorType.PATTERN_DETECTION_ERROR: "01010403002001",
            JFAErrorType.ANOMALY_DETECTION_ERROR: "01010403003001",
            JFAErrorType.DEEP_ANALYSIS_ERROR: "01010403004001",
            JFAErrorType.VALIDATION_RULE_ERROR: "01010404001001",
            JFAErrorType.CUSTOM_VALIDATOR_ERROR: "01010404002001",
            JFAErrorType.RULE_CONFLICT_ERROR: "01010404003001",
            JFAErrorType.FILE_READ_ERROR: "01010405001001",
            JFAErrorType.FILE_WRITE_ERROR: "01010405002001",
            JFAErrorType.BATCH_PROCESSING_ERROR: "01010405003001",
            JFAErrorType.INVALID_CONFIGURATION: "01010406001001",
            JFAErrorType.MODULE_NOT_AVAILABLE: "01010406002001",
            JFAErrorType.ANALYSIS_MODE_ERROR: "01010406003001",
            JFAErrorType.PROCESSING_TIMEOUT: "01010407001001",
            JFAErrorType.MEMORY_ERROR: "01010407002001",
            JFAErrorType.UNKNOWN_ERROR: "01010407999001"
        }
        
        # Statistics
        self.stats = {
            "total_errors_handled": 0,
            "successful_recoveries": 0,
            "failed_recoveries": 0,
            "error_counts_by_type": {},
            "last_error": None
        }

    def handle_error(self, error: Exception, context: str = "unknown", module: str = "JFA") -> Dict[str, Any]:
        """
        Handle JFA processing errors with recovery strategies.
        
        Args:
            error: The exception that occurred
            context: Context where the error occurred
            module: Module name where error occurred
            
        Returns:
            Dictionary with error handling results
        """
        try:
            self.stats["total_errors_handled"] += 1
            self.stats["last_error"] = datetime.now()
            
            # Classify error type
            error_type = self._classify_error(error)
            
            # Update statistics
            if error_type not in self.stats["error_counts_by_type"]:
                self.stats["error_counts_by_type"][error_type] = 0
            self.stats["error_counts_by_type"][error_type] += 1
            
            # Get internal error code
            internal_code = self.error_code_mapping.get(error_type, "01010407999001")
            
            # Log error with EMM
            self.error_manager.log_error_with_generation(
                module,
                error.__class__.__name__,
                context,
                str(error),
                internal_code
            )
            
            # Attempt recovery
            recovery_result = self._attempt_recovery(error_type, error, context)
            
            # Create response
            response = {
                "error_handled": True,
                "error_type": error_type.value,
                "internal_code": internal_code,
                "original_error": str(error),
                "context": context,
                "module": module,
                "timestamp": datetime.now().isoformat(),
                "recovery_attempted": recovery_result["attempted"],
                "recovery_successful": recovery_result["successful"],
                "recovery_message": recovery_result.get("message", "")
            }
            
            if recovery_result["successful"]:
                self.stats["successful_recoveries"] += 1
                response["recovery_data"] = recovery_result.get("data")
            else:
                self.stats["failed_recoveries"] += 1
                response["recovery_error"] = recovery_result.get("error")
            
            return response
            
        except Exception as handler_error:
            self.logger.error(f"Error handler itself failed: {handler_error}")
            return {
                "error_handled": False,
                "error_type": "handler_error",
                "original_error": str(error),
                "handler_error": str(handler_error),
                "timestamp": datetime.now().isoformat()
            }

    def _classify_error(self, error: Exception) -> JFAErrorType:
        """Classify error into JFA-specific error type."""
        error_message = str(error).lower()
        error_class = error.__class__.__name__
        
        # Template processing errors
        if "template too large" in error_message or "size exceeds" in error_message:
            return JFAErrorType.TEMPLATE_TOO_LARGE
        elif "json" in error_message and ("invalid" in error_message or "malformed" in error_message):
            return JFAErrorType.INVALID_JSON_FORMAT
        elif "structure" in error_message or "schema" in error_message:
            return JFAErrorType.TEMPLATE_STRUCTURE_ERROR
        elif "validation failed" in error_message or "validation error" in error_message:
            return JFAErrorType.TEMPLATE_VALIDATION_FAILED
            
        # Binary generation errors
        elif "binary generation" in error_message or "binary data" in error_message:
            return JFAErrorType.BINARY_GENERATION_FAILED
        elif "compression" in error_message and "error" in error_message:
            return JFAErrorType.COMPRESSION_ERROR
        elif "binary format" in error_message or "format error" in error_message:
            return JFAErrorType.BINARY_FORMAT_ERROR
        elif "checksum" in error_message and ("failed" in error_message or "mismatch" in error_message):
            return JFAErrorType.CHECKSUM_VALIDATION_FAILED
            
        # Analysis errors
        elif "analysis failed" in error_message or "analysis error" in error_message:
            return JFAErrorType.ANALYSIS_FAILED
        elif "pattern detection" in error_message:
            return JFAErrorType.PATTERN_DETECTION_ERROR
        elif "anomaly detection" in error_message:
            return JFAErrorType.ANOMALY_DETECTION_ERROR
        elif "deep analysis" in error_message:
            return JFAErrorType.DEEP_ANALYSIS_ERROR
            
        # Validation rule errors
        elif "validation rule" in error_message:
            return JFAErrorType.VALIDATION_RULE_ERROR
        elif "custom validator" in error_message:
            return JFAErrorType.CUSTOM_VALIDATOR_ERROR
        elif "rule conflict" in error_message:
            return JFAErrorType.RULE_CONFLICT_ERROR
            
        # File processing errors
        elif "file not found" in error_message or "no such file" in error_message:
            return JFAErrorType.FILE_READ_ERROR
        elif "permission denied" in error_message and "write" in error_message:
            return JFAErrorType.FILE_WRITE_ERROR
        elif "batch" in error_message and "error" in error_message:
            return JFAErrorType.BATCH_PROCESSING_ERROR
            
        # Configuration errors
        elif "configuration" in error_message or "config" in error_message:
            return JFAErrorType.INVALID_CONFIGURATION
        elif "module not available" in error_message or "not available" in error_message:
            return JFAErrorType.MODULE_NOT_AVAILABLE
        elif "analysis mode" in error_message:
            return JFAErrorType.ANALYSIS_MODE_ERROR
            
        # General errors
        elif "timeout" in error_message or error_class == "TimeoutError":
            return JFAErrorType.PROCESSING_TIMEOUT
        elif "memory" in error_message or error_class == "MemoryError":
            return JFAErrorType.MEMORY_ERROR
        else:
            return JFAErrorType.UNKNOWN_ERROR

    def _attempt_recovery(self, error_type: JFAErrorType, error: Exception, context: str) -> Dict[str, Any]:
        """Attempt error recovery using registered strategies."""
        try:
            if error_type in self.recovery_strategies:
                recovery_func = self.recovery_strategies[error_type]
                result = recovery_func(error, context)
                return {
                    "attempted": True,
                    "successful": result.get("success", False),
                    "message": result.get("message", ""),
                    "data": result.get("data"),
                    "error": result.get("error")
                }
            else:
                return {
                    "attempted": False,
                    "successful": False,
                    "message": f"No recovery strategy for {error_type.value}"
                }
        except Exception as recovery_error:
            return {
                "attempted": True,
                "successful": False,
                "error": str(recovery_error),
                "message": "Recovery attempt failed"
            }

    # Recovery strategy methods
    def _handle_template_too_large(self, error: Exception, context: str) -> Dict[str, Any]:
        """Handle template too large error."""
        return {
            "success": True,
            "message": "Template should be split into smaller chunks",
            "data": {"suggested_max_size": 10485760, "action": "split_template"}
        }

    def _handle_invalid_json(self, error: Exception, context: str) -> Dict[str, Any]:
        """Handle invalid JSON format error."""
        return {
            "success": True,
            "message": "JSON should be validated and repaired",
            "data": {"action": "json_repair", "validate": True}
        }

    def _handle_structure_error(self, error: Exception, context: str) -> Dict[str, Any]:
        """Handle template structure error."""
        return {
            "success": True,
            "message": "Use template repair with structure validation",
            "data": {"action": "structure_repair", "validate_schema": True}
        }

    def _handle_validation_failed(self, error: Exception, context: str) -> Dict[str, Any]:
        """Handle template validation failure."""
        return {
            "success": True,
            "message": "Continue with reduced validation strictness",
            "data": {"action": "reduce_strictness", "strictness": "medium"}
        }

    def _handle_binary_generation_failed(self, error: Exception, context: str) -> Dict[str, Any]:
        """Handle binary generation failure."""
        return {
            "success": True,
            "message": "Retry with simplified binary format",
            "data": {"action": "simplify_format", "format": "basic"}
        }

    def _handle_compression_error(self, error: Exception, context: str) -> Dict[str, Any]:
        """Handle compression error."""
        return {
            "success": True,
            "message": "Generate binary without compression",
            "data": {"action": "disable_compression", "compression": False}
        }

    def _handle_binary_format_error(self, error: Exception, context: str) -> Dict[str, Any]:
        """Handle binary format error."""
        return {
            "success": True,
            "message": "Use default binary format",
            "data": {"action": "use_default_format", "format": "jfa_v1"}
        }

    def _handle_checksum_failed(self, error: Exception, context: str) -> Dict[str, Any]:
        """Handle checksum validation failure."""
        return {
            "success": True,
            "message": "Regenerate binary with new checksum",
            "data": {"action": "regenerate_binary", "validate_checksum": True}
        }

    def _handle_analysis_failed(self, error: Exception, context: str) -> Dict[str, Any]:
        """Handle general analysis failure."""
        return {
            "success": True,
            "message": "Retry with basic analysis mode",
            "data": {"action": "basic_analysis", "mode": "basic"}
        }

    def _handle_pattern_detection_error(self, error: Exception, context: str) -> Dict[str, Any]:
        """Handle pattern detection error."""
        return {
            "success": True,
            "message": "Continue analysis without pattern detection",
            "data": {"action": "skip_pattern_detection", "pattern_detection": False}
        }

    def _handle_anomaly_detection_error(self, error: Exception, context: str) -> Dict[str, Any]:
        """Handle anomaly detection error."""
        return {
            "success": True,
            "message": "Continue analysis without anomaly detection",
            "data": {"action": "skip_anomaly_detection", "anomaly_detection": False}
        }

    def _handle_deep_analysis_error(self, error: Exception, context: str) -> Dict[str, Any]:
        """Handle deep analysis error."""
        return {
            "success": True,
            "message": "Fall back to standard analysis",
            "data": {"action": "standard_analysis", "deep_analysis": False}
        }

    def _handle_validation_rule_error(self, error: Exception, context: str) -> Dict[str, Any]:
        """Handle validation rule error."""
        return {
            "success": True,
            "message": "Use default validation rules",
            "data": {"action": "use_default_rules", "rules": "default"}
        }

    def _handle_custom_validator_error(self, error: Exception, context: str) -> Dict[str, Any]:
        """Handle custom validator error."""
        return {
            "success": True,
            "message": "Disable custom validators and use built-in validation",
            "data": {"action": "disable_custom_validators", "custom_validators": False}
        }

    def _handle_rule_conflict_error(self, error: Exception, context: str) -> Dict[str, Any]:
        """Handle validation rule conflict error."""
        return {
            "success": True,
            "message": "Resolve conflicts by using priority-based rules",
            "data": {"action": "resolve_conflicts", "priority": "built_in_first"}
        }

    def _handle_file_read_error(self, error: Exception, context: str) -> Dict[str, Any]:
        """Handle file read error."""
        return {
            "success": False,
            "message": "File not accessible",
            "error": "file_access_denied"
        }

    def _handle_file_write_error(self, error: Exception, context: str) -> Dict[str, Any]:
        """Handle file write error."""
        return {
            "success": True,
            "message": "Use temporary directory for output",
            "data": {"action": "use_temp_dir", "fallback_path": "/tmp/jfa_output"}
        }

    def _handle_batch_error(self, error: Exception, context: str) -> Dict[str, Any]:
        """Handle batch processing error."""
        return {
            "success": True,
            "message": "Process templates individually",
            "data": {"action": "individual_processing", "batch_disabled": True}
        }

    def _handle_invalid_config(self, error: Exception, context: str) -> Dict[str, Any]:
        """Handle invalid configuration error."""
        return {
            "success": True,
            "message": "Use default configuration",
            "data": {"action": "use_defaults", "config_reset": True}
        }

    def _handle_module_unavailable(self, error: Exception, context: str) -> Dict[str, Any]:
        """Handle module not available error."""
        return {
            "success": False,
            "message": "Required module not available",
            "error": "module_dependency_missing"
        }

    def _handle_analysis_mode_error(self, error: Exception, context: str) -> Dict[str, Any]:
        """Handle analysis mode error."""
        return {
            "success": True,
            "message": "Fallback to comprehensive analysis mode",
            "data": {"action": "comprehensive_mode", "mode": "comprehensive"}
        }

    def _handle_timeout(self, error: Exception, context: str) -> Dict[str, Any]:
        """Handle processing timeout error."""
        return {
            "success": True,
            "message": "Reduce analysis complexity and retry",
            "data": {"action": "simplify_analysis", "timeout_extended": True}
        }

    def _handle_memory_error(self, error: Exception, context: str) -> Dict[str, Any]:
        """Handle memory error."""
        return {
            "success": True,
            "message": "Process template in smaller chunks",
            "data": {"action": "chunk_processing", "chunk_size": 1048576}  # 1MB chunks
        }

    def _handle_unknown_error(self, error: Exception, context: str) -> Dict[str, Any]:
        """Handle unknown error."""
        return {
            "success": False,
            "message": "Unknown error occurred",
            "error": "unknown_error_type"
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get error handler statistics."""
        return self.stats.copy()

    def reset_stats(self):
        """Reset error handler statistics."""
        self.stats = {
            "total_errors_handled": 0,
            "successful_recoveries": 0,
            "failed_recoveries": 0,
            "error_counts_by_type": {},
            "last_error": None
        }

# Global instance
api_error_handler = JFAAPIErrorHandler() 