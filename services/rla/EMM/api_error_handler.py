"""
API Error Handler Module for RLA Microservice

Comprehensive error handling for RLA gateway control and rate limiting operations
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


class RLAErrorType(Enum):
    """RLA-specific error types."""
    # Gateway Control Errors
    GATEWAY_ACTIVATION_FAILED = "gateway_activation_failed"
    GATEWAY_DEACTIVATION_FAILED = "gateway_deactivation_failed"
    ENDPOINT_UNAVAILABLE = "endpoint_unavailable"
    PORT_BINDING_ERROR = "port_binding_error"
    
    # Rate Limiting Errors
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    RATE_LIMIT_CONFIG_ERROR = "rate_limit_config_error"
    RATE_LIMIT_CACHE_ERROR = "rate_limit_cache_error"
    RATE_LIMIT_CALCULATION_ERROR = "rate_limit_calculation_error"
    
    # Spam Detection Errors
    SPAM_DETECTION_FAILED = "spam_detection_failed"
    SPAM_THRESHOLD_ERROR = "spam_threshold_error"
    SPAM_VALIDATION_ERROR = "spam_validation_error"
    
    # SSL Certificate Errors
    SSL_CERTIFICATE_ERROR = "ssl_certificate_error"
    SSL_CERTIFICATE_EXPIRED = "ssl_certificate_expired"
    SSL_CERTIFICATE_INVALID = "ssl_certificate_invalid"
    SSL_RELOAD_FAILED = "ssl_reload_failed"
    
    # Validation Errors
    REQUEST_VALIDATION_FAILED = "request_validation_failed"
    INPUT_VALIDATION_ERROR = "input_validation_error"
    SCHEMA_VALIDATION_ERROR = "schema_validation_error"
    
    # Network and Connection Errors
    CONNECTION_ERROR = "connection_error"
    NETWORK_TIMEOUT = "network_timeout"
    SOCKET_ERROR = "socket_error"
    
    # Configuration Errors
    INVALID_CONFIGURATION = "invalid_configuration"
    GATEWAY_CONFIG_ERROR = "gateway_config_error"
    ENDPOINT_CONFIG_ERROR = "endpoint_config_error"
    
    # General Errors
    PROCESSING_TIMEOUT = "processing_timeout"
    MEMORY_ERROR = "memory_error"
    MODULE_NOT_AVAILABLE = "module_not_available"
    UNKNOWN_ERROR = "unknown_error"


class RLAAPIErrorHandler:
    """
    RLA API Error Handler
    
    Maps RLA processing errors to internal error codes and provides
    automated recovery strategies with EMM integration.
    """
    
    def __init__(self):
        """Initialize the RLA API Error Handler."""
        self.logger = logging.getLogger(__name__)
        self.error_manager = ErrorManagementModule()
        
        # Error recovery strategies
        self.recovery_strategies = {
            RLAErrorType.GATEWAY_ACTIVATION_FAILED: self._handle_gateway_activation_failed,
            RLAErrorType.GATEWAY_DEACTIVATION_FAILED: self._handle_gateway_deactivation_failed,
            RLAErrorType.ENDPOINT_UNAVAILABLE: self._handle_endpoint_unavailable,
            RLAErrorType.PORT_BINDING_ERROR: self._handle_port_binding_error,
            RLAErrorType.RATE_LIMIT_EXCEEDED: self._handle_rate_limit_exceeded,
            RLAErrorType.RATE_LIMIT_CONFIG_ERROR: self._handle_rate_limit_config_error,
            RLAErrorType.RATE_LIMIT_CACHE_ERROR: self._handle_rate_limit_cache_error,
            RLAErrorType.RATE_LIMIT_CALCULATION_ERROR: self._handle_rate_limit_calculation_error,
            RLAErrorType.SPAM_DETECTION_FAILED: self._handle_spam_detection_failed,
            RLAErrorType.SPAM_THRESHOLD_ERROR: self._handle_spam_threshold_error,
            RLAErrorType.SPAM_VALIDATION_ERROR: self._handle_spam_validation_error,
            RLAErrorType.SSL_CERTIFICATE_ERROR: self._handle_ssl_certificate_error,
            RLAErrorType.SSL_CERTIFICATE_EXPIRED: self._handle_ssl_certificate_expired,
            RLAErrorType.SSL_CERTIFICATE_INVALID: self._handle_ssl_certificate_invalid,
            RLAErrorType.SSL_RELOAD_FAILED: self._handle_ssl_reload_failed,
            RLAErrorType.REQUEST_VALIDATION_FAILED: self._handle_request_validation_failed,
            RLAErrorType.INPUT_VALIDATION_ERROR: self._handle_input_validation_error,
            RLAErrorType.SCHEMA_VALIDATION_ERROR: self._handle_schema_validation_error,
            RLAErrorType.CONNECTION_ERROR: self._handle_connection_error,
            RLAErrorType.NETWORK_TIMEOUT: self._handle_network_timeout,
            RLAErrorType.SOCKET_ERROR: self._handle_socket_error,
            RLAErrorType.INVALID_CONFIGURATION: self._handle_invalid_config,
            RLAErrorType.GATEWAY_CONFIG_ERROR: self._handle_gateway_config_error,
            RLAErrorType.ENDPOINT_CONFIG_ERROR: self._handle_endpoint_config_error,
            RLAErrorType.PROCESSING_TIMEOUT: self._handle_timeout,
            RLAErrorType.MEMORY_ERROR: self._handle_memory_error,
            RLAErrorType.MODULE_NOT_AVAILABLE: self._handle_module_unavailable,
            RLAErrorType.UNKNOWN_ERROR: self._handle_unknown_error
        }
        
        # Error code mapping to internal codes
        self.error_code_mapping = {
            RLAErrorType.GATEWAY_ACTIVATION_FAILED: "01010101001001",  # RLA specific error codes
            RLAErrorType.GATEWAY_DEACTIVATION_FAILED: "01010101002001",
            RLAErrorType.ENDPOINT_UNAVAILABLE: "01010101003001",
            RLAErrorType.PORT_BINDING_ERROR: "01010101004001",
            RLAErrorType.RATE_LIMIT_EXCEEDED: "01010102001001",
            RLAErrorType.RATE_LIMIT_CONFIG_ERROR: "01010102002001",
            RLAErrorType.RATE_LIMIT_CACHE_ERROR: "01010102003001",
            RLAErrorType.RATE_LIMIT_CALCULATION_ERROR: "01010102004001",
            RLAErrorType.SPAM_DETECTION_FAILED: "01010103001001",
            RLAErrorType.SPAM_THRESHOLD_ERROR: "01010103002001",
            RLAErrorType.SPAM_VALIDATION_ERROR: "01010103003001",
            RLAErrorType.SSL_CERTIFICATE_ERROR: "01010104001001",
            RLAErrorType.SSL_CERTIFICATE_EXPIRED: "01010104002001",
            RLAErrorType.SSL_CERTIFICATE_INVALID: "01010104003001",
            RLAErrorType.SSL_RELOAD_FAILED: "01010104004001",
            RLAErrorType.REQUEST_VALIDATION_FAILED: "01010105001001",
            RLAErrorType.INPUT_VALIDATION_ERROR: "01010105002001",
            RLAErrorType.SCHEMA_VALIDATION_ERROR: "01010105003001",
            RLAErrorType.CONNECTION_ERROR: "01010106001001",
            RLAErrorType.NETWORK_TIMEOUT: "01010106002001",
            RLAErrorType.SOCKET_ERROR: "01010106003001",
            RLAErrorType.INVALID_CONFIGURATION: "01010107001001",
            RLAErrorType.GATEWAY_CONFIG_ERROR: "01010107002001",
            RLAErrorType.ENDPOINT_CONFIG_ERROR: "01010107003001",
            RLAErrorType.PROCESSING_TIMEOUT: "01010108001001",
            RLAErrorType.MEMORY_ERROR: "01010108002001",
            RLAErrorType.MODULE_NOT_AVAILABLE: "01010108003001",
            RLAErrorType.UNKNOWN_ERROR: "01010108999001"
        }
        
        # Statistics
        self.stats = {
            "total_errors_handled": 0,
            "successful_recoveries": 0,
            "failed_recoveries": 0,
            "error_counts_by_type": {},
            "last_error": None
        }

    def handle_error(self, error: Exception, context: str = "unknown", module: str = "RLA") -> Dict[str, Any]:
        """
        Handle RLA processing errors with recovery strategies.
        
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
            internal_code = self.error_code_mapping.get(error_type, "01010108999001")
            
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

    def _classify_error(self, error: Exception) -> RLAErrorType:
        """Classify error into RLA-specific error type."""
        error_message = str(error).lower()
        error_class = error.__class__.__name__
        
        # Gateway control errors
        if "gateway activation" in error_message and "failed" in error_message:
            return RLAErrorType.GATEWAY_ACTIVATION_FAILED
        elif "gateway deactivation" in error_message and "failed" in error_message:
            return RLAErrorType.GATEWAY_DEACTIVATION_FAILED
        elif "endpoint unavailable" in error_message or "endpoint not available" in error_message:
            return RLAErrorType.ENDPOINT_UNAVAILABLE
        elif "port" in error_message and ("binding" in error_message or "already in use" in error_message):
            return RLAErrorType.PORT_BINDING_ERROR
            
        # Rate limiting errors
        elif "rate limit exceeded" in error_message or "too many requests" in error_message:
            return RLAErrorType.RATE_LIMIT_EXCEEDED
        elif "rate limit config" in error_message or "rate limiting configuration" in error_message:
            return RLAErrorType.RATE_LIMIT_CONFIG_ERROR
        elif "rate limit cache" in error_message:
            return RLAErrorType.RATE_LIMIT_CACHE_ERROR
        elif "rate limit calculation" in error_message:
            return RLAErrorType.RATE_LIMIT_CALCULATION_ERROR
            
        # Spam detection errors
        elif "spam detection" in error_message and "failed" in error_message:
            return RLAErrorType.SPAM_DETECTION_FAILED
        elif "spam threshold" in error_message:
            return RLAErrorType.SPAM_THRESHOLD_ERROR
        elif "spam validation" in error_message:
            return RLAErrorType.SPAM_VALIDATION_ERROR
            
        # SSL certificate errors
        elif "ssl certificate" in error_message and "expired" in error_message:
            return RLAErrorType.SSL_CERTIFICATE_EXPIRED
        elif "ssl certificate" in error_message and "invalid" in error_message:
            return RLAErrorType.SSL_CERTIFICATE_INVALID
        elif "ssl reload" in error_message and "failed" in error_message:
            return RLAErrorType.SSL_RELOAD_FAILED
        elif "ssl certificate" in error_message:
            return RLAErrorType.SSL_CERTIFICATE_ERROR
            
        # Validation errors
        elif "request validation" in error_message and "failed" in error_message:
            return RLAErrorType.REQUEST_VALIDATION_FAILED
        elif "input validation" in error_message:
            return RLAErrorType.INPUT_VALIDATION_ERROR
        elif "schema validation" in error_message:
            return RLAErrorType.SCHEMA_VALIDATION_ERROR
            
        # Network and connection errors
        elif "connection" in error_message and ("refused" in error_message or "failed" in error_message):
            return RLAErrorType.CONNECTION_ERROR
        elif "network timeout" in error_message or "request timeout" in error_message:
            return RLAErrorType.NETWORK_TIMEOUT
        elif "socket" in error_message and "error" in error_message:
            return RLAErrorType.SOCKET_ERROR
            
        # Configuration errors
        elif "gateway config" in error_message:
            return RLAErrorType.GATEWAY_CONFIG_ERROR
        elif "endpoint config" in error_message:
            return RLAErrorType.ENDPOINT_CONFIG_ERROR
        elif "configuration" in error_message or "config" in error_message:
            return RLAErrorType.INVALID_CONFIGURATION
            
        # General errors
        elif "timeout" in error_message or error_class == "TimeoutError":
            return RLAErrorType.PROCESSING_TIMEOUT
        elif "memory" in error_message or error_class == "MemoryError":
            return RLAErrorType.MEMORY_ERROR
        elif "module not available" in error_message or "not available" in error_message:
            return RLAErrorType.MODULE_NOT_AVAILABLE
        else:
            return RLAErrorType.UNKNOWN_ERROR

    def _attempt_recovery(self, error_type: RLAErrorType, error: Exception, context: str) -> Dict[str, Any]:
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
    def _handle_gateway_activation_failed(self, error: Exception, context: str) -> Dict[str, Any]:
        """Handle gateway activation failure."""
        return {
            "success": True,
            "message": "Retry gateway activation with fallback configuration",
            "data": {"action": "retry_activation", "use_fallback_config": True}
        }

    def _handle_gateway_deactivation_failed(self, error: Exception, context: str) -> Dict[str, Any]:
        """Handle gateway deactivation failure."""
        return {
            "success": True,
            "message": "Force gateway shutdown",
            "data": {"action": "force_shutdown", "cleanup_resources": True}
        }

    def _handle_endpoint_unavailable(self, error: Exception, context: str) -> Dict[str, Any]:
        """Handle endpoint unavailable error."""
        return {
            "success": True,
            "message": "Use alternative endpoint or fallback port",
            "data": {"action": "use_alternative", "fallback_ports": [3813, 3814]}
        }

    def _handle_port_binding_error(self, error: Exception, context: str) -> Dict[str, Any]:
        """Handle port binding error."""
        return {
            "success": True,
            "message": "Try alternative port for gateway binding",
            "data": {"action": "try_alternative_port", "port_range": [3812, 3820]}
        }

    def _handle_rate_limit_exceeded(self, error: Exception, context: str) -> Dict[str, Any]:
        """Handle rate limit exceeded error."""
        return {
            "success": True,
            "message": "Apply rate limiting and queue request",
            "data": {"action": "queue_request", "delay_seconds": 60}
        }

    def _handle_rate_limit_config_error(self, error: Exception, context: str) -> Dict[str, Any]:
        """Handle rate limit configuration error."""
        return {
            "success": True,
            "message": "Use default rate limiting configuration",
            "data": {"action": "use_default_config", "default_limits": {"per_minute": 60, "per_hour": 1000}}
        }

    def _handle_rate_limit_cache_error(self, error: Exception, context: str) -> Dict[str, Any]:
        """Handle rate limit cache error."""
        return {
            "success": True,
            "message": "Clear rate limit cache and restart tracking",
            "data": {"action": "clear_cache", "restart_tracking": True}
        }

    def _handle_rate_limit_calculation_error(self, error: Exception, context: str) -> Dict[str, Any]:
        """Handle rate limit calculation error."""
        return {
            "success": True,
            "message": "Use simplified rate limiting calculation",
            "data": {"action": "simplified_calculation", "method": "basic"}
        }

    def _handle_spam_detection_failed(self, error: Exception, context: str) -> Dict[str, Any]:
        """Handle spam detection failure."""
        return {
            "success": True,
            "message": "Continue processing without spam detection",
            "data": {"action": "skip_spam_detection", "log_warning": True}
        }

    def _handle_spam_threshold_error(self, error: Exception, context: str) -> Dict[str, Any]:
        """Handle spam threshold error."""
        return {
            "success": True,
            "message": "Use default spam detection threshold",
            "data": {"action": "use_default_threshold", "threshold": 0.8}
        }

    def _handle_spam_validation_error(self, error: Exception, context: str) -> Dict[str, Any]:
        """Handle spam validation error."""
        return {
            "success": True,
            "message": "Use relaxed spam validation rules",
            "data": {"action": "relaxed_validation", "strictness": "medium"}
        }

    def _handle_ssl_certificate_error(self, error: Exception, context: str) -> Dict[str, Any]:
        """Handle SSL certificate error."""
        return {
            "success": True,
            "message": "Fall back to HTTP or use backup certificate",
            "data": {"action": "fallback_certificate", "use_backup": True}
        }

    def _handle_ssl_certificate_expired(self, error: Exception, context: str) -> Dict[str, Any]:
        """Handle SSL certificate expired error."""
        return {
            "success": True,
            "message": "Request new SSL certificate from CCU",
            "data": {"action": "request_new_certificate", "notify_ccu": True}
        }

    def _handle_ssl_certificate_invalid(self, error: Exception, context: str) -> Dict[str, Any]:
        """Handle SSL certificate invalid error."""
        return {
            "success": True,
            "message": "Generate self-signed certificate as fallback",
            "data": {"action": "generate_self_signed", "temporary": True}
        }

    def _handle_ssl_reload_failed(self, error: Exception, context: str) -> Dict[str, Any]:
        """Handle SSL certificate reload failure."""
        return {
            "success": True,
            "message": "Continue with existing certificate",
            "data": {"action": "use_existing_certificate", "schedule_retry": True}
        }

    def _handle_request_validation_failed(self, error: Exception, context: str) -> Dict[str, Any]:
        """Handle request validation failure."""
        return {
            "success": True,
            "message": "Apply data sanitization and retry validation",
            "data": {"action": "sanitize_and_retry", "sanitization_level": "basic"}
        }

    def _handle_input_validation_error(self, error: Exception, context: str) -> Dict[str, Any]:
        """Handle input validation error."""
        return {
            "success": True,
            "message": "Use relaxed input validation rules",
            "data": {"action": "relaxed_validation", "allow_partial": True}
        }

    def _handle_schema_validation_error(self, error: Exception, context: str) -> Dict[str, Any]:
        """Handle schema validation error."""
        return {
            "success": True,
            "message": "Use schema repair and continue processing",
            "data": {"action": "schema_repair", "repair_mode": "auto"}
        }

    def _handle_connection_error(self, error: Exception, context: str) -> Dict[str, Any]:
        """Handle connection error."""
        return {
            "success": True,
            "message": "Retry connection with exponential backoff",
            "data": {"action": "retry_with_backoff", "max_retries": 3}
        }

    def _handle_network_timeout(self, error: Exception, context: str) -> Dict[str, Any]:
        """Handle network timeout error."""
        return {
            "success": True,
            "message": "Extend timeout and retry request",
            "data": {"action": "extend_timeout", "timeout_multiplier": 2.0}
        }

    def _handle_socket_error(self, error: Exception, context: str) -> Dict[str, Any]:
        """Handle socket error."""
        return {
            "success": True,
            "message": "Recreate socket connection",
            "data": {"action": "recreate_socket", "reset_connection": True}
        }

    def _handle_invalid_config(self, error: Exception, context: str) -> Dict[str, Any]:
        """Handle invalid configuration error."""
        return {
            "success": True,
            "message": "Use default configuration",
            "data": {"action": "use_defaults", "config_reset": True}
        }

    def _handle_gateway_config_error(self, error: Exception, context: str) -> Dict[str, Any]:
        """Handle gateway configuration error."""
        return {
            "success": True,
            "message": "Use default gateway configuration",
            "data": {"action": "default_gateway_config", "ports": {"activation": 3812, "data": 3781}}
        }

    def _handle_endpoint_config_error(self, error: Exception, context: str) -> Dict[str, Any]:
        """Handle endpoint configuration error."""
        return {
            "success": True,
            "message": "Use standard endpoint configuration",
            "data": {"action": "standard_endpoints", "health_check": True}
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
            "message": "Clear caches and reduce memory usage",
            "data": {"action": "memory_optimization", "clear_caches": True}
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
api_error_handler = RLAAPIErrorHandler() 