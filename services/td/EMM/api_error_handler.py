"""
API Error Handler Module for TD Microservice

Comprehensive error handling for TD orchestration and calculation coordination operations
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


class TDErrorType(Enum):
    """TD-specific error types."""
    # Orchestration Errors
    ORCHESTRATION_FAILED = "orchestration_failed"
    ORCHESTRATION_TIMEOUT = "orchestration_timeout"
    ORCHESTRATION_CANCELLED = "orchestration_cancelled"
    CONCURRENT_LIMIT_EXCEEDED = "concurrent_limit_exceeded"
    
    # Binary Processing Errors
    BINARY_FILE_READ_ERROR = "binary_file_read_error"
    BINARY_FORMAT_ERROR = "binary_format_error"
    BINARY_VALIDATION_FAILED = "binary_validation_failed"
    BINARY_PROCESSING_TIMEOUT = "binary_processing_timeout"
    
    # Calculation Block Errors
    CALCULATION_BLOCK_ERROR = "calculation_block_error"
    CALCULATION_BLOCK_TIMEOUT = "calculation_block_timeout"
    CALCULATION_BLOCK_UNAVAILABLE = "calculation_block_unavailable"
    CALCULATION_RESULT_INVALID = "calculation_result_invalid"
    
    # Result Aggregation Errors
    AGGREGATION_FAILED = "aggregation_failed"
    AGGREGATION_FORMAT_ERROR = "aggregation_format_error"
    OCM_INTERFACE_ERROR = "ocm_interface_error"
    RESULT_FORMATTING_ERROR = "result_formatting_error"
    
    # Configuration Errors
    INVALID_ORCHESTRATION_CONFIG = "invalid_orchestration_config"
    CALCULATION_CONFIG_ERROR = "calculation_config_error"
    PERFORMANCE_CONFIG_ERROR = "performance_config_error"
    
    # Resource Management Errors
    RESOURCE_EXHAUSTED = "resource_exhausted"
    CALCULATION_QUEUE_FULL = "calculation_queue_full"
    ORCHESTRATION_QUEUE_FULL = "orchestration_queue_full"
    
    # File Processing Errors
    FILE_READ_ERROR = "file_read_error"
    FILE_WRITE_ERROR = "file_write_error"
    BATCH_PROCESSING_ERROR = "batch_processing_error"
    
    # General Errors
    PROCESSING_TIMEOUT = "processing_timeout"
    MEMORY_ERROR = "memory_error"
    MODULE_NOT_AVAILABLE = "module_not_available"
    UNKNOWN_ERROR = "unknown_error"


class TDAPIErrorHandler:
    """
    TD API Error Handler
    
    Maps TD processing errors to internal error codes and provides
    automated recovery strategies with EMM integration.
    """
    
    def __init__(self):
        """Initialize the TD API Error Handler."""
        self.logger = logging.getLogger(__name__)
        self.error_manager = ErrorManagementModule()
        
        # Error recovery strategies
        self.recovery_strategies = {
            TDErrorType.ORCHESTRATION_FAILED: self._handle_orchestration_failed,
            TDErrorType.ORCHESTRATION_TIMEOUT: self._handle_orchestration_timeout,
            TDErrorType.ORCHESTRATION_CANCELLED: self._handle_orchestration_cancelled,
            TDErrorType.CONCURRENT_LIMIT_EXCEEDED: self._handle_concurrent_limit_exceeded,
            TDErrorType.BINARY_FILE_READ_ERROR: self._handle_binary_file_read_error,
            TDErrorType.BINARY_FORMAT_ERROR: self._handle_binary_format_error,
            TDErrorType.BINARY_VALIDATION_FAILED: self._handle_binary_validation_failed,
            TDErrorType.BINARY_PROCESSING_TIMEOUT: self._handle_binary_processing_timeout,
            TDErrorType.CALCULATION_BLOCK_ERROR: self._handle_calculation_block_error,
            TDErrorType.CALCULATION_BLOCK_TIMEOUT: self._handle_calculation_block_timeout,
            TDErrorType.CALCULATION_BLOCK_UNAVAILABLE: self._handle_calculation_block_unavailable,
            TDErrorType.CALCULATION_RESULT_INVALID: self._handle_calculation_result_invalid,
            TDErrorType.AGGREGATION_FAILED: self._handle_aggregation_failed,
            TDErrorType.AGGREGATION_FORMAT_ERROR: self._handle_aggregation_format_error,
            TDErrorType.OCM_INTERFACE_ERROR: self._handle_ocm_interface_error,
            TDErrorType.RESULT_FORMATTING_ERROR: self._handle_result_formatting_error,
            TDErrorType.INVALID_ORCHESTRATION_CONFIG: self._handle_invalid_orchestration_config,
            TDErrorType.CALCULATION_CONFIG_ERROR: self._handle_calculation_config_error,
            TDErrorType.PERFORMANCE_CONFIG_ERROR: self._handle_performance_config_error,
            TDErrorType.RESOURCE_EXHAUSTED: self._handle_resource_exhausted,
            TDErrorType.CALCULATION_QUEUE_FULL: self._handle_calculation_queue_full,
            TDErrorType.ORCHESTRATION_QUEUE_FULL: self._handle_orchestration_queue_full,
            TDErrorType.FILE_READ_ERROR: self._handle_file_read_error,
            TDErrorType.FILE_WRITE_ERROR: self._handle_file_write_error,
            TDErrorType.BATCH_PROCESSING_ERROR: self._handle_batch_error,
            TDErrorType.PROCESSING_TIMEOUT: self._handle_timeout,
            TDErrorType.MEMORY_ERROR: self._handle_memory_error,
            TDErrorType.MODULE_NOT_AVAILABLE: self._handle_module_unavailable,
            TDErrorType.UNKNOWN_ERROR: self._handle_unknown_error
        }
        
        # Error code mapping to internal codes
        self.error_code_mapping = {
            TDErrorType.ORCHESTRATION_FAILED: "01010501001001",  # TD specific error codes
            TDErrorType.ORCHESTRATION_TIMEOUT: "01010501002001",
            TDErrorType.ORCHESTRATION_CANCELLED: "01010501003001",
            TDErrorType.CONCURRENT_LIMIT_EXCEEDED: "01010501004001",
            TDErrorType.BINARY_FILE_READ_ERROR: "01010502001001",
            TDErrorType.BINARY_FORMAT_ERROR: "01010502002001",
            TDErrorType.BINARY_VALIDATION_FAILED: "01010502003001",
            TDErrorType.BINARY_PROCESSING_TIMEOUT: "01010502004001",
            TDErrorType.CALCULATION_BLOCK_ERROR: "01010503001001",
            TDErrorType.CALCULATION_BLOCK_TIMEOUT: "01010503002001",
            TDErrorType.CALCULATION_BLOCK_UNAVAILABLE: "01010503003001",
            TDErrorType.CALCULATION_RESULT_INVALID: "01010503004001",
            TDErrorType.AGGREGATION_FAILED: "01010504001001",
            TDErrorType.AGGREGATION_FORMAT_ERROR: "01010504002001",
            TDErrorType.OCM_INTERFACE_ERROR: "01010504003001",
            TDErrorType.RESULT_FORMATTING_ERROR: "01010504004001",
            TDErrorType.INVALID_ORCHESTRATION_CONFIG: "01010505001001",
            TDErrorType.CALCULATION_CONFIG_ERROR: "01010505002001",
            TDErrorType.PERFORMANCE_CONFIG_ERROR: "01010505003001",
            TDErrorType.RESOURCE_EXHAUSTED: "01010506001001",
            TDErrorType.CALCULATION_QUEUE_FULL: "01010506002001",
            TDErrorType.ORCHESTRATION_QUEUE_FULL: "01010506003001",
            TDErrorType.FILE_READ_ERROR: "01010507001001",
            TDErrorType.FILE_WRITE_ERROR: "01010507002001",
            TDErrorType.BATCH_PROCESSING_ERROR: "01010507003001",
            TDErrorType.PROCESSING_TIMEOUT: "01010508001001",
            TDErrorType.MEMORY_ERROR: "01010508002001",
            TDErrorType.MODULE_NOT_AVAILABLE: "01010508003001",
            TDErrorType.UNKNOWN_ERROR: "01010508999001"
        }
        
        # Statistics
        self.stats = {
            "total_errors_handled": 0,
            "successful_recoveries": 0,
            "failed_recoveries": 0,
            "error_counts_by_type": {},
            "last_error": None
        }

    def handle_error(self, error: Exception, context: str = "unknown", module: str = "TD") -> Dict[str, Any]:
        """
        Handle TD processing errors with recovery strategies.
        
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
            internal_code = self.error_code_mapping.get(error_type, "01010508999001")
            
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

    def _classify_error(self, error: Exception) -> TDErrorType:
        """Classify error into TD-specific error type."""
        error_message = str(error).lower()
        error_class = error.__class__.__name__
        
        # Orchestration errors
        if "orchestration failed" in error_message or "orchestration error" in error_message:
            return TDErrorType.ORCHESTRATION_FAILED
        elif "orchestration timeout" in error_message:
            return TDErrorType.ORCHESTRATION_TIMEOUT
        elif "orchestration cancelled" in error_message or "orchestration canceled" in error_message:
            return TDErrorType.ORCHESTRATION_CANCELLED
        elif "concurrent limit" in error_message or "too many concurrent" in error_message:
            return TDErrorType.CONCURRENT_LIMIT_EXCEEDED
            
        # Binary processing errors
        elif "binary file" in error_message and ("read" in error_message or "not found" in error_message):
            return TDErrorType.BINARY_FILE_READ_ERROR
        elif "binary format" in error_message or "format error" in error_message:
            return TDErrorType.BINARY_FORMAT_ERROR
        elif "binary validation" in error_message and "failed" in error_message:
            return TDErrorType.BINARY_VALIDATION_FAILED
        elif "binary processing" in error_message and "timeout" in error_message:
            return TDErrorType.BINARY_PROCESSING_TIMEOUT
            
        # Calculation block errors
        elif "calculation block" in error_message and "error" in error_message:
            return TDErrorType.CALCULATION_BLOCK_ERROR
        elif "calculation" in error_message and "timeout" in error_message:
            return TDErrorType.CALCULATION_BLOCK_TIMEOUT
        elif "calculation block" in error_message and ("unavailable" in error_message or "not available" in error_message):
            return TDErrorType.CALCULATION_BLOCK_UNAVAILABLE
        elif "calculation result" in error_message and ("invalid" in error_message or "error" in error_message):
            return TDErrorType.CALCULATION_RESULT_INVALID
            
        # Aggregation errors
        elif "aggregation failed" in error_message or "aggregation error" in error_message:
            return TDErrorType.AGGREGATION_FAILED
        elif "aggregation format" in error_message:
            return TDErrorType.AGGREGATION_FORMAT_ERROR
        elif "ocm interface" in error_message or "ocm error" in error_message:
            return TDErrorType.OCM_INTERFACE_ERROR
        elif "result formatting" in error_message:
            return TDErrorType.RESULT_FORMATTING_ERROR
            
        # Configuration errors
        elif "orchestration config" in error_message or "orchestration configuration" in error_message:
            return TDErrorType.INVALID_ORCHESTRATION_CONFIG
        elif "calculation config" in error_message:
            return TDErrorType.CALCULATION_CONFIG_ERROR
        elif "performance config" in error_message:
            return TDErrorType.PERFORMANCE_CONFIG_ERROR
            
        # Resource management errors
        elif "resource exhausted" in error_message or "resources unavailable" in error_message:
            return TDErrorType.RESOURCE_EXHAUSTED
        elif "calculation queue" in error_message and "full" in error_message:
            return TDErrorType.CALCULATION_QUEUE_FULL
        elif "orchestration queue" in error_message and "full" in error_message:
            return TDErrorType.ORCHESTRATION_QUEUE_FULL
            
        # File processing errors
        elif "file not found" in error_message or "no such file" in error_message:
            return TDErrorType.FILE_READ_ERROR
        elif "permission denied" in error_message and "write" in error_message:
            return TDErrorType.FILE_WRITE_ERROR
        elif "batch" in error_message and "error" in error_message:
            return TDErrorType.BATCH_PROCESSING_ERROR
            
        # General errors
        elif "timeout" in error_message or error_class == "TimeoutError":
            return TDErrorType.PROCESSING_TIMEOUT
        elif "memory" in error_message or error_class == "MemoryError":
            return TDErrorType.MEMORY_ERROR
        elif "module not available" in error_message or "not available" in error_message:
            return TDErrorType.MODULE_NOT_AVAILABLE
        else:
            return TDErrorType.UNKNOWN_ERROR

    def _attempt_recovery(self, error_type: TDErrorType, error: Exception, context: str) -> Dict[str, Any]:
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
    def _handle_orchestration_failed(self, error: Exception, context: str) -> Dict[str, Any]:
        """Handle orchestration failure."""
        return {
            "success": True,
            "message": "Retry orchestration with reduced complexity",
            "data": {"action": "retry_orchestration", "complexity": "reduced"}
        }

    def _handle_orchestration_timeout(self, error: Exception, context: str) -> Dict[str, Any]:
        """Handle orchestration timeout."""
        return {
            "success": True,
            "message": "Extend timeout and retry orchestration",
            "data": {"action": "extend_timeout", "timeout_multiplier": 2.0}
        }

    def _handle_orchestration_cancelled(self, error: Exception, context: str) -> Dict[str, Any]:
        """Handle orchestration cancellation."""
        return {
            "success": True,
            "message": "Clean up orchestration resources",
            "data": {"action": "cleanup_resources", "notify_cleanup": True}
        }

    def _handle_concurrent_limit_exceeded(self, error: Exception, context: str) -> Dict[str, Any]:
        """Handle concurrent limit exceeded."""
        return {
            "success": True,
            "message": "Queue orchestration for later execution",
            "data": {"action": "queue_for_later", "priority": "normal"}
        }

    def _handle_binary_file_read_error(self, error: Exception, context: str) -> Dict[str, Any]:
        """Handle binary file read error."""
        return {
            "success": False,
            "message": "Binary file not accessible",
            "error": "file_access_denied"
        }

    def _handle_binary_format_error(self, error: Exception, context: str) -> Dict[str, Any]:
        """Handle binary format error."""
        return {
            "success": True,
            "message": "Try alternative binary format parsers",
            "data": {"action": "try_alternative_parsers", "formats": ["jfa_v1", "jfa_v2", "legacy"]}
        }

    def _handle_binary_validation_failed(self, error: Exception, context: str) -> Dict[str, Any]:
        """Handle binary validation failure."""
        return {
            "success": True,
            "message": "Continue processing with validation warnings",
            "data": {"action": "continue_with_warnings", "validation": "relaxed"}
        }

    def _handle_binary_processing_timeout(self, error: Exception, context: str) -> Dict[str, Any]:
        """Handle binary processing timeout."""
        return {
            "success": True,
            "message": "Split binary into smaller chunks for processing",
            "data": {"action": "split_binary", "chunk_size": 1048576}  # 1MB chunks
        }

    def _handle_calculation_block_error(self, error: Exception, context: str) -> Dict[str, Any]:
        """Handle calculation block error."""
        return {
            "success": True,
            "message": "Skip failed calculation block and continue",
            "data": {"action": "skip_block", "continue_orchestration": True}
        }

    def _handle_calculation_block_timeout(self, error: Exception, context: str) -> Dict[str, Any]:
        """Handle calculation block timeout."""
        return {
            "success": True,
            "message": "Cancel timed out calculation and continue with others",
            "data": {"action": "cancel_and_continue", "timeout_action": "skip"}
        }

    def _handle_calculation_block_unavailable(self, error: Exception, context: str) -> Dict[str, Any]:
        """Handle calculation block unavailable error."""
        return {
            "success": True,
            "message": "Use alternative calculation block if available",
            "data": {"action": "use_alternative", "alternative_routes": ["forward", "parallel"]}
        }

    def _handle_calculation_result_invalid(self, error: Exception, context: str) -> Dict[str, Any]:
        """Handle invalid calculation result."""
        return {
            "success": True,
            "message": "Mark result as invalid and continue aggregation",
            "data": {"action": "mark_invalid", "include_in_aggregation": False}
        }

    def _handle_aggregation_failed(self, error: Exception, context: str) -> Dict[str, Any]:
        """Handle aggregation failure."""
        return {
            "success": True,
            "message": "Use simple aggregation mode",
            "data": {"action": "simple_aggregation", "mode": "basic"}
        }

    def _handle_aggregation_format_error(self, error: Exception, context: str) -> Dict[str, Any]:
        """Handle aggregation format error."""
        return {
            "success": True,
            "message": "Use default aggregation format",
            "data": {"action": "use_default_format", "format": "json"}
        }

    def _handle_ocm_interface_error(self, error: Exception, context: str) -> Dict[str, Any]:
        """Handle OCM interface error."""
        return {
            "success": True,
            "message": "Save results to file for manual OCM delivery",
            "data": {"action": "save_to_file", "fallback_delivery": True}
        }

    def _handle_result_formatting_error(self, error: Exception, context: str) -> Dict[str, Any]:
        """Handle result formatting error."""
        return {
            "success": True,
            "message": "Use raw result format",
            "data": {"action": "raw_format", "format": "unformatted"}
        }

    def _handle_invalid_orchestration_config(self, error: Exception, context: str) -> Dict[str, Any]:
        """Handle invalid orchestration configuration."""
        return {
            "success": True,
            "message": "Use default orchestration configuration",
            "data": {"action": "use_default_config", "config_reset": True}
        }

    def _handle_calculation_config_error(self, error: Exception, context: str) -> Dict[str, Any]:
        """Handle calculation configuration error."""
        return {
            "success": True,
            "message": "Use default calculation settings",
            "data": {"action": "default_calculation_settings", "reset_config": True}
        }

    def _handle_performance_config_error(self, error: Exception, context: str) -> Dict[str, Any]:
        """Handle performance configuration error."""
        return {
            "success": True,
            "message": "Use balanced performance settings",
            "data": {"action": "balanced_performance", "mode": "balanced"}
        }

    def _handle_resource_exhausted(self, error: Exception, context: str) -> Dict[str, Any]:
        """Handle resource exhausted error."""
        return {
            "success": True,
            "message": "Queue orchestration until resources are available",
            "data": {"action": "queue_until_resources_available", "retry_delay": 30}
        }

    def _handle_calculation_queue_full(self, error: Exception, context: str) -> Dict[str, Any]:
        """Handle calculation queue full error."""
        return {
            "success": True,
            "message": "Wait and retry calculation submission",
            "data": {"action": "wait_and_retry", "retry_delay": 10}
        }

    def _handle_orchestration_queue_full(self, error: Exception, context: str) -> Dict[str, Any]:
        """Handle orchestration queue full error."""
        return {
            "success": True,
            "message": "Defer orchestration to lower priority queue",
            "data": {"action": "defer_to_low_priority", "priority": "low"}
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
            "data": {"action": "use_temp_dir", "fallback_path": "/tmp/td_output"}
        }

    def _handle_batch_error(self, error: Exception, context: str) -> Dict[str, Any]:
        """Handle batch processing error."""
        return {
            "success": True,
            "message": "Process files individually",
            "data": {"action": "individual_processing", "batch_disabled": True}
        }

    def _handle_timeout(self, error: Exception, context: str) -> Dict[str, Any]:
        """Handle processing timeout error."""
        return {
            "success": True,
            "message": "Reduce processing complexity and retry",
            "data": {"action": "simplify_processing", "timeout_extended": True}
        }

    def _handle_memory_error(self, error: Exception, context: str) -> Dict[str, Any]:
        """Handle memory error."""
        return {
            "success": True,
            "message": "Reduce concurrent orchestrations and clear cache",
            "data": {"action": "reduce_concurrency", "clear_cache": True}
        }

    def _handle_module_unavailable(self, error: Exception, context: str) -> Dict[str, Any]:
        """Handle module not available error."""
        return {
            "success": False,
            "message": "Required module not available",
            "error": "module_dependency_missing"
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
api_error_handler = TDAPIErrorHandler() 