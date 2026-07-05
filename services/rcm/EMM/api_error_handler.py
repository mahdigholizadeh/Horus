"""
API Error Handler Module

Comprehensive error handling for OpenAI API errors with mapping to internal error codes
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


class APIErrorType(Enum):
    """OpenAI API error types."""
    # Authentication Errors (401)
    INVALID_AUTHENTICATION = "401_invalid_auth"
    INCORRECT_API_KEY = "401_incorrect_key"
    NOT_ORGANIZATION_MEMBER = "401_not_org_member"
    
    # Authorization Errors (403)
    COUNTRY_NOT_SUPPORTED = "403_country_not_supported"
    
    # Rate Limit Errors (429)
    RATE_LIMIT_REACHED = "429_rate_limit"
    QUOTA_EXCEEDED = "429_quota_exceeded"
    
    # Server Errors (500, 503)
    SERVER_ERROR = "500_server_error"
    ENGINE_OVERLOADED = "503_engine_overloaded"
    SLOW_DOWN = "503_slow_down"
    
    # Python Library Errors
    API_CONNECTION_ERROR = "connection_error"
    API_TIMEOUT_ERROR = "timeout_error"
    AUTHENTICATION_ERROR = "auth_error"
    BAD_REQUEST_ERROR = "bad_request"
    CONFLICT_ERROR = "conflict_error"
    INTERNAL_SERVER_ERROR = "internal_server_error"
    NOT_FOUND_ERROR = "not_found_error"
    PERMISSION_DENIED_ERROR = "permission_denied"
    RATE_LIMIT_ERROR = "rate_limit_error"
    UNPROCESSABLE_ENTITY_ERROR = "unprocessable_entity"


class APIErrorHandler:
    """
    Comprehensive API Error Handler
    
    Maps OpenAI API errors to internal error codes and provides
    automated recovery strategies with EMM integration.
    """
    
    def __init__(self):
        """Initialize the API Error Handler."""
        self.logger = logging.getLogger(__name__)
        self.error_manager = ErrorManagementModule()
        
        # API Error Code Mapping (OpenAI -> Internal)
        self.api_error_mapping = {
            # HTTP Status Code Errors
            "401": {
                "invalid_request_error": APIErrorType.INVALID_AUTHENTICATION,
                "invalid_api_key": APIErrorType.INCORRECT_API_KEY,
                "default": APIErrorType.INVALID_AUTHENTICATION
            },
            "403": {
                "default": APIErrorType.COUNTRY_NOT_SUPPORTED
            },
            "429": {
                "rate_limit_exceeded": APIErrorType.RATE_LIMIT_REACHED,
                "quota_exceeded": APIErrorType.QUOTA_EXCEEDED,
                "default": APIErrorType.RATE_LIMIT_REACHED
            },
            "500": {
                "default": APIErrorType.SERVER_ERROR
            },
            "503": {
                "engine_overloaded": APIErrorType.ENGINE_OVERLOADED,
                "slow_down": APIErrorType.SLOW_DOWN,
                "default": APIErrorType.ENGINE_OVERLOADED
            }
        }
        
        # Python Library Error Mapping
        self.python_error_mapping = {
            "APIConnectionError": APIErrorType.API_CONNECTION_ERROR,
            "APITimeoutError": APIErrorType.API_TIMEOUT_ERROR,
            "AuthenticationError": APIErrorType.AUTHENTICATION_ERROR,
            "BadRequestError": APIErrorType.BAD_REQUEST_ERROR,
            "ConflictError": APIErrorType.CONFLICT_ERROR,
            "InternalServerError": APIErrorType.INTERNAL_SERVER_ERROR,
            "NotFoundError": APIErrorType.NOT_FOUND_ERROR,
            "PermissionDeniedError": APIErrorType.PERMISSION_DENIED_ERROR,
            "RateLimitError": APIErrorType.RATE_LIMIT_ERROR,
            "UnprocessableEntityError": APIErrorType.UNPROCESSABLE_ENTITY_ERROR
        }
        
        # Error Recovery Strategies
        self.recovery_strategies = {
            APIErrorType.INVALID_AUTHENTICATION: self._handle_invalid_auth,
            APIErrorType.INCORRECT_API_KEY: self._handle_incorrect_api_key,
            APIErrorType.NOT_ORGANIZATION_MEMBER: self._handle_not_org_member,
            APIErrorType.COUNTRY_NOT_SUPPORTED: self._handle_country_not_supported,
            APIErrorType.RATE_LIMIT_REACHED: self._handle_rate_limit,
            APIErrorType.QUOTA_EXCEEDED: self._handle_quota_exceeded,
            APIErrorType.SERVER_ERROR: self._handle_server_error,
            APIErrorType.ENGINE_OVERLOADED: self._handle_engine_overloaded,
            APIErrorType.SLOW_DOWN: self._handle_slow_down,
            APIErrorType.API_CONNECTION_ERROR: self._handle_connection_error,
            APIErrorType.API_TIMEOUT_ERROR: self._handle_timeout_error,
            APIErrorType.AUTHENTICATION_ERROR: self._handle_auth_error,
            APIErrorType.BAD_REQUEST_ERROR: self._handle_bad_request,
            APIErrorType.CONFLICT_ERROR: self._handle_conflict_error,
            APIErrorType.INTERNAL_SERVER_ERROR: self._handle_internal_server_error,
            APIErrorType.NOT_FOUND_ERROR: self._handle_not_found,
            APIErrorType.PERMISSION_DENIED_ERROR: self._handle_permission_denied,
            APIErrorType.RATE_LIMIT_ERROR: self._handle_rate_limit_error,
            APIErrorType.UNPROCESSABLE_ENTITY_ERROR: self._handle_unprocessable_entity
        }
        
        # Retry Configuration
        self.retry_config = {
            APIErrorType.RATE_LIMIT_REACHED: {"max_retries": 3, "base_delay": 5, "max_delay": 60},
            APIErrorType.QUOTA_EXCEEDED: {"max_retries": 1, "base_delay": 0, "max_delay": 0},
            APIErrorType.SERVER_ERROR: {"max_retries": 3, "base_delay": 2, "max_delay": 30},
            APIErrorType.ENGINE_OVERLOADED: {"max_retries": 5, "base_delay": 10, "max_delay": 120},
            APIErrorType.SLOW_DOWN: {"max_retries": 3, "base_delay": 15, "max_delay": 300},
            APIErrorType.API_CONNECTION_ERROR: {"max_retries": 3, "base_delay": 1, "max_delay": 10},
            APIErrorType.API_TIMEOUT_ERROR: {"max_retries": 2, "base_delay": 2, "max_delay": 10},
            APIErrorType.BAD_REQUEST_ERROR: {"max_retries": 0, "base_delay": 0, "max_delay": 0},
            APIErrorType.CONFLICT_ERROR: {"max_retries": 1, "base_delay": 1, "max_delay": 5},
            APIErrorType.INTERNAL_SERVER_ERROR: {"max_retries": 3, "base_delay": 2, "max_delay": 30},
            APIErrorType.UNPROCESSABLE_ENTITY_ERROR: {"max_retries": 1, "base_delay": 1, "max_delay": 5}
        }
        
        # Statistics
        self.stats = {
            "total_errors": 0,
            "errors_by_type": {},
            "successful_recoveries": 0,
            "failed_recoveries": 0,
            "retry_attempts": 0,
            "last_error": None
        }
    
    def parse_api_error(self, error_response: str, status_code: Optional[int] = None) -> Tuple[APIErrorType, Dict[str, Any]]:
        """
        Parse API error response and determine error type.
        
        Args:
            error_response: Error response string or dict
            status_code: HTTP status code if available
            
        Returns:
            Tuple of (APIErrorType, error_details)
        """
        try:
            # Parse error response
            if isinstance(error_response, str):
                # Try to extract JSON from string
                json_match = re.search(r'\{.*\}', error_response, re.DOTALL)
                if json_match:
                    error_data = json.loads(json_match.group())
                else:
                    error_data = {"error": {"message": error_response}}
            else:
                error_data = error_response
            
            # Extract error details
            error_info = error_data.get("error", {})
            error_type = error_info.get("type", "")
            error_code = error_info.get("code", "")
            error_message = error_info.get("message", "")
            
            # Determine API error type
            api_error_type = self._determine_error_type(status_code, error_type, error_code, error_message)
            
            # Create error details
            error_details = {
                "status_code": status_code,
                "error_type": error_type,
                "error_code": error_code,
                "error_message": error_message,
                "raw_response": error_response,
                "timestamp": datetime.now().isoformat()
            }
            
            return api_error_type, error_details
            
        except Exception as e:
            self.logger.error(f"Error parsing API error: {e}")
            return APIErrorType.SERVER_ERROR, {
                "status_code": status_code,
                "error_message": str(error_response),
                "parse_error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def _determine_error_type(self, status_code: Optional[int], error_type: str, error_code: str, error_message: str) -> APIErrorType:
        """Determine the specific API error type."""
        
        # Check for specific error codes first
        if error_code == "invalid_api_key":
            return APIErrorType.INCORRECT_API_KEY
        elif error_code == "rate_limit_exceeded":
            return APIErrorType.RATE_LIMIT_REACHED
        elif error_code == "quota_exceeded":
            return APIErrorType.QUOTA_EXCEEDED
        
        # Check status code mapping
        if status_code and str(status_code) in self.api_error_mapping:
            status_mapping = self.api_error_mapping[str(status_code)]
            if error_type in status_mapping:
                return status_mapping[error_type]
            else:
                return status_mapping.get("default", APIErrorType.SERVER_ERROR)
        
        # Check error message patterns
        error_message_lower = error_message.lower()
        if "authentication" in error_message_lower or "invalid" in error_message_lower:
            return APIErrorType.INVALID_AUTHENTICATION
        elif "rate limit" in error_message_lower:
            return APIErrorType.RATE_LIMIT_REACHED
        elif "quota" in error_message_lower or "billing" in error_message_lower:
            return APIErrorType.QUOTA_EXCEEDED
        elif "overloaded" in error_message_lower:
            return APIErrorType.ENGINE_OVERLOADED
        elif "slow down" in error_message_lower:
            return APIErrorType.SLOW_DOWN
        elif "country" in error_message_lower or "region" in error_message_lower:
            return APIErrorType.COUNTRY_NOT_SUPPORTED
        elif "organization" in error_message_lower:
            return APIErrorType.NOT_ORGANIZATION_MEMBER
        
        # Default to server error
        return APIErrorType.SERVER_ERROR
    
    def parse_python_error(self, exception: Exception) -> Tuple[APIErrorType, Dict[str, Any]]:
        """Parse Python library exceptions."""
        error_class = exception.__class__.__name__
        api_error_type = self.python_error_mapping.get(error_class, APIErrorType.SERVER_ERROR)
        
        error_details = {
            "exception_type": error_class,
            "error_message": str(exception),
            "timestamp": datetime.now().isoformat()
        }
        
        return api_error_type, error_details
    
    async def handle_api_error(self, error_response: str, status_code: Optional[int] = None, 
                             context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Handle API error with automated recovery.
        
        Args:
            error_response: Error response from API
            status_code: HTTP status code
            context: Additional context information
            
        Returns:
            Dictionary with handling result
        """
        try:
            # Parse the error
            api_error_type, error_details = self.parse_api_error(error_response, status_code)
            
            # Update statistics
            self.stats["total_errors"] += 1
            self.stats["errors_by_type"][api_error_type.value] = self.stats["errors_by_type"].get(api_error_type.value, 0) + 1
            self.stats["last_error"] = datetime.now().isoformat()
            
            # Log error with EMM
            error_code = self._generate_api_error_code(api_error_type)
            self.error_manager.log_error_with_generation(
                "API_ERROR_HANDLER",
                "APIErrorHandler",
                "handle_api_error",
                f"API Error: {api_error_type.value} - {error_details.get('error_message', 'Unknown error')}",
                context=error_details
            )
            
            # Attempt recovery
            recovery_result = await self._attempt_recovery(api_error_type, error_details, context)
            
            # Prepare response
            result = {
                "success": recovery_result["success"],
                "api_error_type": api_error_type.value,
                "error_code": error_code,
                "error_details": error_details,
                "recovery_attempted": recovery_result["attempted"],
                "recovery_success": recovery_result["success"],
                "retry_recommended": recovery_result["retry_recommended"],
                "retry_delay": recovery_result["retry_delay"],
                "max_retries": recovery_result["max_retries"],
                "recommendations": recovery_result["recommendations"],
                "timestamp": datetime.now().isoformat()
            }
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error in handle_api_error: {e}")
            return {
                "success": False,
                "error": f"Error handling failed: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
    
    def _generate_api_error_code(self, api_error_type: APIErrorType) -> str:
        """Generate internal error code for API errors."""
        # Use a different prefix for API errors (API instead of 16-char hex)
        error_code_map = {
            APIErrorType.INVALID_AUTHENTICATION: "API_401_AUTH",
            APIErrorType.INCORRECT_API_KEY: "API_401_KEY",
            APIErrorType.NOT_ORGANIZATION_MEMBER: "API_401_ORG",
            APIErrorType.COUNTRY_NOT_SUPPORTED: "API_403_COUNTRY",
            APIErrorType.RATE_LIMIT_REACHED: "API_429_RATE",
            APIErrorType.QUOTA_EXCEEDED: "API_429_QUOTA",
            APIErrorType.SERVER_ERROR: "API_500_SERVER",
            APIErrorType.ENGINE_OVERLOADED: "API_503_OVERLOAD",
            APIErrorType.SLOW_DOWN: "API_503_SLOW",
            APIErrorType.API_CONNECTION_ERROR: "API_CONNECTION",
            APIErrorType.API_TIMEOUT_ERROR: "API_TIMEOUT",
            APIErrorType.AUTHENTICATION_ERROR: "API_AUTH",
            APIErrorType.BAD_REQUEST_ERROR: "API_BAD_REQUEST",
            APIErrorType.CONFLICT_ERROR: "API_CONFLICT",
            APIErrorType.INTERNAL_SERVER_ERROR: "API_INTERNAL",
            APIErrorType.NOT_FOUND_ERROR: "API_NOT_FOUND",
            APIErrorType.PERMISSION_DENIED_ERROR: "API_PERMISSION",
            APIErrorType.RATE_LIMIT_ERROR: "API_RATE_LIMIT",
            APIErrorType.UNPROCESSABLE_ENTITY_ERROR: "API_UNPROCESSABLE"
        }
        return error_code_map.get(api_error_type, "API_UNKNOWN")
    
    async def _attempt_recovery(self, api_error_type: APIErrorType, error_details: Dict[str, Any], 
                              context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Attempt to recover from the error."""
        
        # Get recovery strategy
        recovery_strategy = self.recovery_strategies.get(api_error_type)
        if not recovery_strategy:
            return {
                "success": False,
                "attempted": False,
                "retry_recommended": False,
                "retry_delay": 0,
                "max_retries": 0,
                "recommendations": ["No recovery strategy available"]
            }
        
        try:
            # Attempt recovery
            recovery_result = await recovery_strategy(error_details, context)
            
            # Get retry configuration
            retry_config = self.retry_config.get(api_error_type, {"max_retries": 0, "base_delay": 0, "max_delay": 0})
            
            # Update statistics
            if recovery_result["success"]:
                self.stats["successful_recoveries"] += 1
            else:
                self.stats["failed_recoveries"] += 1
            
            return {
                "success": recovery_result["success"],
                "attempted": True,
                "retry_recommended": recovery_result.get("retry_recommended", False),
                "retry_delay": recovery_result.get("retry_delay", retry_config["base_delay"]),
                "max_retries": retry_config["max_retries"],
                "recommendations": recovery_result.get("recommendations", [])
            }
            
        except Exception as e:
            self.logger.error(f"Recovery attempt failed: {e}")
            return {
                "success": False,
                "attempted": True,
                "retry_recommended": False,
                "retry_delay": 0,
                "max_retries": 0,
                "recommendations": [f"Recovery failed: {str(e)}"]
            }
    
    # Recovery Strategy Implementations
    async def _handle_invalid_auth(self, error_details: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Handle invalid authentication errors."""
        return {
            "success": False,
            "retry_recommended": False,
            "recommendations": [
                "Check API key configuration",
                "Verify organization settings",
                "Generate new API key if needed"
            ]
        }
    
    async def _handle_incorrect_api_key(self, error_details: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Handle incorrect API key errors."""
        return {
            "success": False,
            "retry_recommended": False,
            "recommendations": [
                "Verify API key is correct",
                "Check for typos or extra spaces",
                "Generate new API key",
                "Clear browser cache if applicable"
            ]
        }
    
    async def _handle_not_org_member(self, error_details: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Handle organization membership errors."""
        return {
            "success": False,
            "retry_recommended": False,
            "recommendations": [
                "Contact organization administrator",
                "Request organization invitation",
                "Create new organization if needed"
            ]
        }
    
    async def _handle_country_not_supported(self, error_details: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Handle country/region not supported errors."""
        return {
            "success": False,
            "retry_recommended": False,
            "recommendations": [
                "Check OpenAI's supported regions",
                "Use VPN if appropriate",
                "Contact OpenAI support for guidance"
            ]
        }
    
    async def _handle_rate_limit(self, error_details: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Handle rate limit errors."""
        await asyncio.sleep(5)  # Wait for rate limit reset
        return {
            "success": True,
            "retry_recommended": True,
            "retry_delay": 5,
            "recommendations": [
                "Implement exponential backoff",
                "Reduce request frequency",
                "Check rate limit headers",
                "Consider upgrading plan"
            ]
        }
    
    async def _handle_quota_exceeded(self, error_details: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Handle quota exceeded errors."""
        return {
            "success": False,
            "retry_recommended": False,
            "recommendations": [
                "Check billing and usage limits",
                "Upgrade plan or add credits",
                "Monitor usage patterns",
                "Contact billing support"
            ]
        }
    
    async def _handle_server_error(self, error_details: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Handle server errors."""
        await asyncio.sleep(2)  # Brief wait before retry
        return {
            "success": True,
            "retry_recommended": True,
            "retry_delay": 2,
            "recommendations": [
                "Retry with exponential backoff",
                "Check OpenAI status page",
                "Contact support if persistent"
            ]
        }
    
    async def _handle_engine_overloaded(self, error_details: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Handle engine overloaded errors."""
        await asyncio.sleep(10)  # Longer wait for overload
        return {
            "success": True,
            "retry_recommended": True,
            "retry_delay": 10,
            "recommendations": [
                "Wait longer between retries",
                "Check OpenAI status page",
                "Consider using different model",
                "Implement circuit breaker pattern"
            ]
        }
    
    async def _handle_slow_down(self, error_details: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Handle slow down errors."""
        await asyncio.sleep(15)  # Significant wait for slow down
        return {
            "success": True,
            "retry_recommended": True,
            "retry_delay": 15,
            "recommendations": [
                "Reduce request rate significantly",
                "Maintain consistent traffic pattern",
                "Consider Scale Tier upgrade",
                "Implement traffic shaping"
            ]
        }
    
    async def _handle_connection_error(self, error_details: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Handle connection errors."""
        await asyncio.sleep(1)  # Brief wait for connection
        return {
            "success": True,
            "retry_recommended": True,
            "retry_delay": 1,
            "recommendations": [
                "Check network connectivity",
                "Verify proxy settings",
                "Check firewall rules",
                "Retry with backoff"
            ]
        }
    
    async def _handle_timeout_error(self, error_details: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Handle timeout errors."""
        await asyncio.sleep(2)  # Wait before retry
        return {
            "success": True,
            "retry_recommended": True,
            "retry_delay": 2,
            "recommendations": [
                "Increase timeout settings",
                "Check network performance",
                "Simplify request if possible",
                "Retry with backoff"
            ]
        }
    
    async def _handle_auth_error(self, error_details: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Handle authentication errors."""
        return {
            "success": False,
            "retry_recommended": False,
            "recommendations": [
                "Check API key validity",
                "Verify authentication headers",
                "Generate new API key",
                "Check account status"
            ]
        }
    
    async def _handle_bad_request(self, error_details: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Handle bad request errors."""
        return {
            "success": False,
            "retry_recommended": False,
            "recommendations": [
                "Review request parameters",
                "Check API documentation",
                "Validate input data",
                "Fix request format"
            ]
        }
    
    async def _handle_conflict_error(self, error_details: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Handle conflict errors."""
        await asyncio.sleep(1)  # Brief wait
        return {
            "success": True,
            "retry_recommended": True,
            "retry_delay": 1,
            "recommendations": [
                "Check resource state",
                "Avoid concurrent updates",
                "Implement optimistic locking",
                "Retry with fresh data"
            ]
        }
    
    async def _handle_internal_server_error(self, error_details: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Handle internal server errors."""
        await asyncio.sleep(2)  # Wait before retry
        return {
            "success": True,
            "retry_recommended": True,
            "retry_delay": 2,
            "recommendations": [
                "Retry with exponential backoff",
                "Check OpenAI status page",
                "Contact support if persistent",
                "Consider alternative endpoints"
            ]
        }
    
    async def _handle_not_found(self, error_details: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Handle not found errors."""
        return {
            "success": False,
            "retry_recommended": False,
            "recommendations": [
                "Verify resource identifier",
                "Check resource existence",
                "Review API endpoint",
                "Update resource references"
            ]
        }
    
    async def _handle_permission_denied(self, error_details: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Handle permission denied errors."""
        return {
            "success": False,
            "retry_recommended": False,
            "recommendations": [
                "Check API key permissions",
                "Verify organization access",
                "Review resource ownership",
                "Contact administrator"
            ]
        }
    
    async def _handle_rate_limit_error(self, error_details: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Handle rate limit errors from Python library."""
        await asyncio.sleep(5)  # Wait for rate limit reset
        return {
            "success": True,
            "retry_recommended": True,
            "retry_delay": 5,
            "recommendations": [
                "Implement exponential backoff",
                "Reduce request frequency",
                "Check rate limit headers",
                "Consider upgrading plan"
            ]
        }
    
    async def _handle_unprocessable_entity(self, error_details: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Handle unprocessable entity errors."""
        await asyncio.sleep(1)  # Brief wait
        return {
            "success": True,
            "retry_recommended": True,
            "retry_delay": 1,
            "recommendations": [
                "Review request format",
                "Check data validation",
                "Verify content type",
                "Retry with corrected data"
            ]
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get error handling statistics."""
        return {
            "total_errors": self.stats["total_errors"],
            "errors_by_type": self.stats["errors_by_type"],
            "successful_recoveries": self.stats["successful_recoveries"],
            "failed_recoveries": self.stats["failed_recoveries"],
            "retry_attempts": self.stats["retry_attempts"],
            "last_error": self.stats["last_error"],
            "recovery_rate": (
                self.stats["successful_recoveries"] / max(self.stats["total_errors"], 1)
            ) * 100
        }
    
    async def send_error_report_to_ccu(self, error_result: Dict[str, Any]) -> bool:
        """Send error report to CCU via EMM."""
        try:
            # Create comprehensive error report
            report = {
                "error_report": {
                    "timestamp": datetime.now().isoformat(),
                    "api_error_type": error_result["api_error_type"],
                    "error_code": error_result["error_code"],
                    "error_details": error_result["error_details"],
                    "recovery_status": {
                        "attempted": error_result["recovery_attempted"],
                        "successful": error_result["recovery_success"],
                        "retry_recommended": error_result["retry_recommended"]
                    },
                    "recommendations": error_result["recommendations"],
                    "statistics": self.get_statistics()
                }
            }
            
            # Log to EMM for CCU transmission
            self.error_manager.log_error_with_generation(
                "API_ERROR_HANDLER",
                "APIErrorHandler",
                "send_error_report_to_ccu",
                f"API Error Report: {error_result['api_error_type']}",
                context=report
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send error report to CCU: {e}")
            return False


# Global instance
api_error_handler = APIErrorHandler() 