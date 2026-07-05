"""
API Error Handler Module for TPP Microservice

Comprehensive error handling for TPP text processing operations with mapping to internal error codes
and automated recovery strategies. Integrates with EMM for centralized error management.
"""

import asyncio
import logging
import json
import re
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from enum import Enum

from EMM.emm import ErrorManagementModule


class TPPErrorType(Enum):
    """TPP-specific error types."""
    # Text Processing Errors
    TEXT_TOO_LONG = "text_too_long"
    INVALID_TEXT_FORMAT = "invalid_text_format"
    LANGUAGE_DETECTION_FAILED = "language_detection_failed"
    ENCODING_ERROR = "encoding_error"
    
    # Spam Filtering Errors
    SPAM_LIST_LOAD_ERROR = "spam_list_load_error"
    SPAM_FILTER_ERROR = "spam_filter_error"
    WORD_LIST_CORRUPT = "word_list_corrupt"
    
    # Language Processing Errors
    UNSUPPORTED_LANGUAGE = "unsupported_language"
    TRANSLATION_ERROR = "translation_error"
    ALPHABET_PROCESSING_ERROR = "alphabet_processing_error"
    
    # File Processing Errors
    FILE_READ_ERROR = "file_read_error"
    FILE_WRITE_ERROR = "file_write_error"
    BATCH_PROCESSING_ERROR = "batch_processing_error"
    
    # Configuration Errors
    INVALID_CONFIGURATION = "invalid_configuration"
    MODULE_NOT_AVAILABLE = "module_not_available"
    PROCESSING_MODE_ERROR = "processing_mode_error"
    
    # General Errors
    PROCESSING_TIMEOUT = "processing_timeout"
    MEMORY_ERROR = "memory_error"
    UNKNOWN_ERROR = "unknown_error"


class TPPAPIErrorHandler:
    """
    TPP API Error Handler
    
    Maps TPP processing errors to internal error codes and provides
    automated recovery strategies with EMM integration.
    """
    
    def __init__(self):
        """Initialize the TPP API Error Handler."""
        self.logger = logging.getLogger(__name__)
        self.error_manager = ErrorManagementModule()
        
        # Error recovery strategies
        self.recovery_strategies = {
            TPPErrorType.TEXT_TOO_LONG: self._handle_text_too_long,
            TPPErrorType.INVALID_TEXT_FORMAT: self._handle_invalid_format,
            TPPErrorType.LANGUAGE_DETECTION_FAILED: self._handle_language_detection_failed,
            TPPErrorType.ENCODING_ERROR: self._handle_encoding_error,
            TPPErrorType.SPAM_LIST_LOAD_ERROR: self._handle_spam_list_error,
            TPPErrorType.SPAM_FILTER_ERROR: self._handle_spam_filter_error,
            TPPErrorType.WORD_LIST_CORRUPT: self._handle_word_list_corrupt,
            TPPErrorType.UNSUPPORTED_LANGUAGE: self._handle_unsupported_language,
            TPPErrorType.TRANSLATION_ERROR: self._handle_translation_error,
            TPPErrorType.ALPHABET_PROCESSING_ERROR: self._handle_alphabet_error,
            TPPErrorType.FILE_READ_ERROR: self._handle_file_read_error,
            TPPErrorType.FILE_WRITE_ERROR: self._handle_file_write_error,
            TPPErrorType.BATCH_PROCESSING_ERROR: self._handle_batch_error,
            TPPErrorType.INVALID_CONFIGURATION: self._handle_invalid_config,
            TPPErrorType.MODULE_NOT_AVAILABLE: self._handle_module_unavailable,
            TPPErrorType.PROCESSING_MODE_ERROR: self._handle_processing_mode_error,
            TPPErrorType.PROCESSING_TIMEOUT: self._handle_timeout,
            TPPErrorType.MEMORY_ERROR: self._handle_memory_error,
            TPPErrorType.UNKNOWN_ERROR: self._handle_unknown_error
        }
        
        # Error code mapping to internal codes
        self.error_code_mapping = {
            TPPErrorType.TEXT_TOO_LONG: "01010201001001",  # TPP specific error codes
            TPPErrorType.INVALID_TEXT_FORMAT: "01010201002001",
            TPPErrorType.LANGUAGE_DETECTION_FAILED: "01010201003001",
            TPPErrorType.ENCODING_ERROR: "01010201004001",
            TPPErrorType.SPAM_LIST_LOAD_ERROR: "01010202001001",
            TPPErrorType.SPAM_FILTER_ERROR: "01010202002001",
            TPPErrorType.WORD_LIST_CORRUPT: "01010202003001",
            TPPErrorType.UNSUPPORTED_LANGUAGE: "01010203001001",
            TPPErrorType.TRANSLATION_ERROR: "01010203002001",
            TPPErrorType.ALPHABET_PROCESSING_ERROR: "01010203003001",
            TPPErrorType.FILE_READ_ERROR: "01010204001001",
            TPPErrorType.FILE_WRITE_ERROR: "01010204002001",
            TPPErrorType.BATCH_PROCESSING_ERROR: "01010204003001",
            TPPErrorType.INVALID_CONFIGURATION: "01010205001001",
            TPPErrorType.MODULE_NOT_AVAILABLE: "01010205002001",
            TPPErrorType.PROCESSING_MODE_ERROR: "01010205003001",
            TPPErrorType.PROCESSING_TIMEOUT: "01010206001001",
            TPPErrorType.MEMORY_ERROR: "01010206002001",
            TPPErrorType.UNKNOWN_ERROR: "01010206999001"
        }
        
        # Statistics
        self.stats = {
            "total_errors_handled": 0,
            "successful_recoveries": 0,
            "failed_recoveries": 0,
            "error_counts_by_type": {},
            "last_error": None
        }

    def handle_error(self, error: Exception, context: str = "unknown", module: str = "TPP") -> Dict[str, Any]:
        """
        Handle TPP processing errors with recovery strategies.
        
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
            internal_code = self.error_code_mapping.get(error_type, "01010206999001")
            
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

    def _classify_error(self, error: Exception) -> TPPErrorType:
        """Classify error into TPP-specific error type."""
        error_message = str(error).lower()
        error_class = error.__class__.__name__
        
        # Text processing errors
        if "text too long" in error_message or "length exceeds" in error_message:
            return TPPErrorType.TEXT_TOO_LONG
        elif "invalid format" in error_message or "format error" in error_message:
            return TPPErrorType.INVALID_TEXT_FORMAT
        elif "language detection" in error_message or "detect language" in error_message:
            return TPPErrorType.LANGUAGE_DETECTION_FAILED
        elif "encoding" in error_message or "decode" in error_message or "encode" in error_message:
            return TPPErrorType.ENCODING_ERROR
            
        # Spam filtering errors
        elif "spam list" in error_message or "word list" in error_message:
            if "load" in error_message or "read" in error_message:
                return TPPErrorType.SPAM_LIST_LOAD_ERROR
            elif "corrupt" in error_message:
                return TPPErrorType.WORD_LIST_CORRUPT
            else:
                return TPPErrorType.SPAM_FILTER_ERROR
        elif "spam filter" in error_message or "filter error" in error_message:
            return TPPErrorType.SPAM_FILTER_ERROR
            
        # Language processing errors
        elif "unsupported language" in error_message or "language not supported" in error_message:
            return TPPErrorType.UNSUPPORTED_LANGUAGE
        elif "translation" in error_message:
            return TPPErrorType.TRANSLATION_ERROR
        elif "alphabet" in error_message or "persian alphabet" in error_message:
            return TPPErrorType.ALPHABET_PROCESSING_ERROR
            
        # File processing errors
        elif "file not found" in error_message or "no such file" in error_message:
            return TPPErrorType.FILE_READ_ERROR
        elif "permission denied" in error_message and "write" in error_message:
            return TPPErrorType.FILE_WRITE_ERROR
        elif "batch" in error_message and "error" in error_message:
            return TPPErrorType.BATCH_PROCESSING_ERROR
            
        # Configuration errors
        elif "configuration" in error_message or "config" in error_message:
            return TPPErrorType.INVALID_CONFIGURATION
        elif "module not available" in error_message or "not available" in error_message:
            return TPPErrorType.MODULE_NOT_AVAILABLE
        elif "processing mode" in error_message:
            return TPPErrorType.PROCESSING_MODE_ERROR
            
        # General errors
        elif "timeout" in error_message or error_class == "TimeoutError":
            return TPPErrorType.PROCESSING_TIMEOUT
        elif "memory" in error_message or error_class == "MemoryError":
            return TPPErrorType.MEMORY_ERROR
        else:
            return TPPErrorType.UNKNOWN_ERROR

    def _attempt_recovery(self, error_type: TPPErrorType, error: Exception, context: str) -> Dict[str, Any]:
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
    def _handle_text_too_long(self, error: Exception, context: str) -> Dict[str, Any]:
        """Handle text too long error by truncating."""
        return {
            "success": True,
            "message": "Text should be truncated to maximum allowed length",
            "data": {"suggested_max_length": 100000, "action": "truncate"}
        }

    def _handle_invalid_format(self, error: Exception, context: str) -> Dict[str, Any]:
        """Handle invalid text format error."""
        return {
            "success": True,
            "message": "Text format should be validated and cleaned",
            "data": {"action": "format_cleanup", "encoding": "utf-8"}
        }

    def _handle_language_detection_failed(self, error: Exception, context: str) -> Dict[str, Any]:
        """Handle language detection failure."""
        return {
            "success": True,
            "message": "Fallback to default language (Persian)",
            "data": {"fallback_language": "persian", "action": "use_default"}
        }

    def _handle_encoding_error(self, error: Exception, context: str) -> Dict[str, Any]:
        """Handle text encoding error."""
        return {
            "success": True,
            "message": "Retry with UTF-8 encoding and error handling",
            "data": {"encoding": "utf-8", "errors": "ignore", "action": "re_encode"}
        }

    def _handle_spam_list_error(self, error: Exception, context: str) -> Dict[str, Any]:
        """Handle spam list loading error."""
        return {
            "success": True,
            "message": "Use default spam word lists",
            "data": {"action": "use_default_lists", "reload": True}
        }

    def _handle_spam_filter_error(self, error: Exception, context: str) -> Dict[str, Any]:
        """Handle spam filtering error."""
        return {
            "success": True,
            "message": "Continue processing without spam filtering",
            "data": {"action": "skip_spam_filter", "warning": "spam_filter_disabled"}
        }

    def _handle_word_list_corrupt(self, error: Exception, context: str) -> Dict[str, Any]:
        """Handle corrupt word list error."""
        return {
            "success": True,
            "message": "Regenerate word lists from backup",
            "data": {"action": "regenerate_lists", "source": "backup"}
        }

    def _handle_unsupported_language(self, error: Exception, context: str) -> Dict[str, Any]:
        """Handle unsupported language error."""
        return {
            "success": True,
            "message": "Process as multilingual text",
            "data": {"action": "multilingual_mode", "fallback": "persian"}
        }

    def _handle_translation_error(self, error: Exception, context: str) -> Dict[str, Any]:
        """Handle translation error."""
        return {
            "success": False,
            "message": "Translation service unavailable",
            "error": "translation_service_down"
        }

    def _handle_alphabet_error(self, error: Exception, context: str) -> Dict[str, Any]:
        """Handle alphabet processing error."""
        return {
            "success": True,
            "message": "Use basic text processing without alphabet organization",
            "data": {"action": "basic_processing", "alphabet_mode": False}
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
            "data": {"action": "use_temp_dir", "fallback_path": "/tmp/tpp_output"}
        }

    def _handle_batch_error(self, error: Exception, context: str) -> Dict[str, Any]:
        """Handle batch processing error."""
        return {
            "success": True,
            "message": "Process files individually",
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

    def _handle_processing_mode_error(self, error: Exception, context: str) -> Dict[str, Any]:
        """Handle processing mode error."""
        return {
            "success": True,
            "message": "Fallback to Persian processing mode",
            "data": {"action": "persian_mode", "mode": "persian"}
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
            "message": "Process text in smaller chunks",
            "data": {"action": "chunk_processing", "chunk_size": 10000}
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
api_error_handler = TPPAPIErrorHandler() 