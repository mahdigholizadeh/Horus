"""
API Key Security Utilities

This module provides secure utilities for API key validation, rotation, and management
across the microservice architecture.

Security Features:
- API key format validation
- Key strength verification
- Secure key rotation
- Key expiration monitoring
- Security event logging
"""

import re
import os
import logging
import hashlib
import secrets
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from enum import Enum


class APIKeyValidationResult(Enum):
    """API key validation results."""
    VALID = "valid"
    INVALID_FORMAT = "invalid_format"
    WEAK_KEY = "weak_key"
    EXPIRED = "expired"
    PLACEHOLDER = "placeholder"
    EMPTY = "empty"


class APIKeySecurityUtils:
    """Utility class for secure API key management."""
    
    def __init__(self):
        """Initialize the security utilities."""
        self.logger = logging.getLogger(__name__)
        
        # API key format patterns
        self.openai_pattern = re.compile(r'^sk-[a-zA-Z0-9\-_]{20,}$')
        self.placeholder_patterns = [
            r'YOUR.*KEY.*HERE',
            r'sk-proj-YOUR',
            r'INSERT.*KEY',
            r'REPLACE.*KEY'
        ]
        
        # Security thresholds
        self.min_key_length = 32
        self.key_rotation_days = 90
        
        # Key validation history (for monitoring)
        self.validation_history: List[Dict[str, Any]] = []
    
    def validate_api_key(self, api_key: str, key_type: str = "openai") -> Tuple[APIKeyValidationResult, str]:
        """
        Validate API key format and security.
        
        Args:
            api_key: The API key to validate
            key_type: Type of API key (openai, special, agent)
            
        Returns:
            Tuple of (validation_result, error_message)
        """
        try:
            # Check for empty or None keys
            if not api_key or api_key.strip() == "":
                return APIKeyValidationResult.EMPTY, "API key is empty"
            
            # Check for placeholder values
            if self._is_placeholder_key(api_key):
                return APIKeyValidationResult.PLACEHOLDER, "API key appears to be a placeholder value"
            
            # Validate format based on key type
            if key_type == "openai":
                if not self.openai_pattern.match(api_key):
                    return APIKeyValidationResult.INVALID_FORMAT, "Invalid OpenAI API key format"
            
            # Check key strength
            if len(api_key) < self.min_key_length:
                return APIKeyValidationResult.WEAK_KEY, f"API key too short (minimum {self.min_key_length} characters)"
            
            # Log successful validation
            self._log_validation_event(api_key, APIKeyValidationResult.VALID, key_type)
            
            return APIKeyValidationResult.VALID, "API key is valid"
            
        except Exception as e:
            self.logger.error(f"Error validating API key: {e}")
            return APIKeyValidationResult.INVALID_FORMAT, f"Validation error: {str(e)}"
    
    def _is_placeholder_key(self, api_key: str) -> bool:
        """Check if the API key is a placeholder value."""
        for pattern in self.placeholder_patterns:
            if re.search(pattern, api_key, re.IGNORECASE):
                return True
        return False
    
    def _log_validation_event(self, api_key: str, result: APIKeyValidationResult, key_type: str):
        """Log API key validation event securely."""
        # Create a hash of the key for logging (never log actual key)
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()[:16]
        
        event = {
            "timestamp": datetime.now().isoformat(),
            "key_hash": key_hash,
            "key_type": key_type,
            "validation_result": result.value,
            "key_length": len(api_key)
        }
        
        self.validation_history.append(event)
        
        # Keep only last 100 events
        if len(self.validation_history) > 100:
            self.validation_history = self.validation_history[-100:]
        
        self.logger.info(f"API key validation: {key_type} key (hash: {key_hash}) - {result.value}")
    
    def mask_api_key(self, api_key: str) -> str:
        """
        Safely mask API key for logging.
        
        Args:
            api_key: The API key to mask
            
        Returns:
            Masked API key string
        """
        if not api_key or len(api_key) < 8:
            return "***INVALID***"
        
        return f"{api_key[:4]}...{api_key[-4:]}"
    
    def generate_secure_test_key(self, key_type: str = "openai") -> str:
        """
        Generate a secure test API key for development/testing.
        
        Args:
            key_type: Type of key to generate
            
        Returns:
            Secure test API key
        """
        if key_type == "openai":
            # Generate OpenAI-style test key
            random_part = secrets.token_urlsafe(48)
            return f"sk-test-{random_part}"
        else:
            # Generate generic secure test key
            return f"sk-test-{key_type}-{secrets.token_urlsafe(32)}"
    
    def check_key_rotation_needed(self, key_set_date: datetime) -> bool:
        """
        Check if API key rotation is needed based on age.
        
        Args:
            key_set_date: When the key was first set
            
        Returns:
            True if rotation is needed
        """
        age_days = (datetime.now() - key_set_date).days
        return age_days >= self.key_rotation_days
    
    def validate_environment_keys(self) -> Dict[str, Dict[str, Any]]:
        """
        Validate all API keys from environment variables.
        
        Returns:
            Dictionary with validation results for each key
        """
        results = {}
        
        # Check main OpenAI key
        openai_key = os.getenv('OPENAI_API_KEY')
        if openai_key:
            result, message = self.validate_api_key(openai_key, "openai")
            results['OPENAI_API_KEY'] = {
                "present": True,
                "valid": result == APIKeyValidationResult.VALID,
                "result": result.value,
                "message": message,
                "masked_key": self.mask_api_key(openai_key)
            }
        else:
            results['OPENAI_API_KEY'] = {
                "present": False,
                "valid": False,
                "result": "missing",
                "message": "Environment variable not set"
            }
        
        # Check special API key
        special_key = os.getenv('SPECIAL_API_KEY')
        if special_key:
            result, message = self.validate_api_key(special_key, "special")
            results['SPECIAL_API_KEY'] = {
                "present": True,
                "valid": result == APIKeyValidationResult.VALID,
                "result": result.value,
                "message": message,
                "masked_key": self.mask_api_key(special_key)
            }
        else:
            results['SPECIAL_API_KEY'] = {
                "present": False,
                "valid": False,
                "result": "missing",
                "message": "Optional key not set"
            }
        
        # Check agent API key
        agent_key = os.getenv('AGENT_API_KEY')
        if agent_key:
            result, message = self.validate_api_key(agent_key, "agent")
            results['AGENT_API_KEY'] = {
                "present": True,
                "valid": result == APIKeyValidationResult.VALID,
                "result": result.value,
                "message": message,
                "masked_key": self.mask_api_key(agent_key)
            }
        else:
            results['AGENT_API_KEY'] = {
                "present": False,
                "valid": False,
                "result": "missing",
                "message": "Optional key not set, will fallback to main key"
            }
        
        return results
    
    def get_security_recommendations(self, validation_results: Dict[str, Dict[str, Any]]) -> List[str]:
        """
        Get security recommendations based on validation results.
        
        Args:
            validation_results: Results from validate_environment_keys()
            
        Returns:
            List of security recommendations
        """
        recommendations = []
        
        # Check main API key
        openai_result = validation_results.get('OPENAI_API_KEY', {})
        if not openai_result.get('present'):
            recommendations.append("🚨 CRITICAL: Set OPENAI_API_KEY environment variable")
        elif not openai_result.get('valid'):
            recommendations.append(f"❌ Fix OPENAI_API_KEY: {openai_result.get('message')}")
        
        # Check for placeholder keys
        for key_name, result in validation_results.items():
            if result.get('result') == 'placeholder':
                recommendations.append(f"⚠️  Replace placeholder {key_name} with real API key")
        
        # Security best practices
        if not recommendations:  # Only if no critical issues
            recommendations.extend([
                "✅ Consider rotating API keys every 90 days",
                "🔒 Store API keys in secure key management system",
                "📝 Monitor API key usage and set up alerts",
                "🔄 Implement automated key rotation"
            ])
        
        return recommendations
    
    def get_validation_summary(self) -> Dict[str, Any]:
        """
        Get summary of recent API key validation events.
        
        Returns:
            Summary statistics and events
        """
        if not self.validation_history:
            return {"total_validations": 0, "events": []}
        
        # Count validation results
        result_counts = {}
        for event in self.validation_history:
            result = event["validation_result"]
            result_counts[result] = result_counts.get(result, 0) + 1
        
        # Get recent events (last 10)
        recent_events = self.validation_history[-10:]
        
        return {
            "total_validations": len(self.validation_history),
            "result_counts": result_counts,
            "recent_events": recent_events,
            "security_health": "good" if result_counts.get("valid", 0) > 0 else "poor"
        }


# Global instance for use across the application
api_key_security = APIKeySecurityUtils()


def validate_api_key_secure(api_key: str, key_type: str = "openai") -> Tuple[bool, str]:
    """
    Convenience function for secure API key validation.
    
    Args:
        api_key: The API key to validate
        key_type: Type of API key
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    result, message = api_key_security.validate_api_key(api_key, key_type)
    return result == APIKeyValidationResult.VALID, message


def get_environment_key_status() -> Dict[str, Any]:
    """
    Get the status of all environment API keys.
    
    Returns:
        Dictionary with key validation status and recommendations
    """
    validation_results = api_key_security.validate_environment_keys()
    recommendations = api_key_security.get_security_recommendations(validation_results)
    
    return {
        "validation_results": validation_results,
        "recommendations": recommendations,
        "summary": api_key_security.get_validation_summary()
    } 