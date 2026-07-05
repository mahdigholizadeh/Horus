"""
Special API Activation and Interaction Module (SAAIM)

Designed to interact with custom-trained OpenAI models.
Handles special model interactions, custom configurations, and response processing.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import json
import aiohttp
from dataclasses import dataclass, asdict

from EMM.emm import ErrorManagementModule
from EMM.api_error_handler import api_error_handler

@dataclass
class SpecialAPIConfig:
    """Configuration for special API interactions."""
    api_key: str
    model_id: str
    max_tokens: int = 1000
    temperature: float = 0.7
    max_retries: int = 3
    timeout: int = 30
    custom_parameters: Optional[Dict[str, Any]] = None

@dataclass
class SpecialAPIResponse:
    """Response from special API interaction."""
    success: bool
    response: Optional[str] = None
    model_used: Optional[str] = None
    tokens_used: Optional[int] = None
    custom_metadata: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: Optional[str] = None

class SpecialAPIActivationModule:
    """
    Special API Activation and Interaction Module (SAAIM)
    
    Handles interactions with custom-trained OpenAI models:
    - Stores default values for DEFAULT_SPECIAL_API_KEY and DEFAULT_SPECIAL_API_MODEL_ID
    - Accepts SPECIAL_API_KEY and SPECIAL_API_MODEL_ID as input to override defaults
    - Implements async/await patterns for non-blocking operations
    - Comprehensive error handling and logging
    - Supports custom parameters for specialized models
    """
    
    def __init__(self):
        """Initialize the SAAIM module."""
        self.logger = logging.getLogger(__name__)
        self.error_manager = ErrorManagementModule()
        
        # Default configuration (can be null/empty initially)
        self.DEFAULT_SPECIAL_API_KEY = None  # Should be set from environment or configuration
        self.DEFAULT_SPECIAL_API_MODEL_ID = None  # Should be set from environment or configuration
        
        # Current configuration
        self.current_config = SpecialAPIConfig(
            api_key=self.DEFAULT_SPECIAL_API_KEY or "",
            model_id=self.DEFAULT_SPECIAL_API_MODEL_ID or ""
        )
        
        # Active requests tracking
        self.active_requests: Dict[str, Dict[str, Any]] = {}
        
        # Statistics
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_tokens_used": 0,
            "average_response_time": 0,
            "last_activity": None
        }
        
        # Error codes now generated dynamically by EMM
        
        # OpenAI API endpoints
        self.base_url = "https://api.openai.com/v1"
        self.chat_completions_url = f"{self.base_url}/chat/completions"
    
    def set_special_api_key(self, api_key: str):
        """Set the special API key for custom model interactions."""
        self.current_config.api_key = api_key
        self.DEFAULT_SPECIAL_API_KEY = api_key
        self.logger.info("SAAIM: Special API key updated")
    
    def set_special_model_id(self, model_id: str):
        """Set the special model ID for custom model interactions."""
        self.current_config.model_id = model_id
        self.DEFAULT_SPECIAL_API_MODEL_ID = model_id
        self.logger.info(f"SAAIM: Special model ID updated to {model_id}")
    
    def set_config(self, **kwargs):
        """Update configuration parameters."""
        for key, value in kwargs.items():
            if hasattr(self.current_config, key):
                setattr(self.current_config, key, value)
                self.logger.info(f"SAAIM: {key} updated to {value}")
    
    def is_configured(self) -> bool:
        """Check if the module is properly configured."""
        return bool(self.current_config.api_key and self.current_config.model_id)
    
    async def process_request(self, request_data: Dict[str, Any]) -> SpecialAPIResponse:
        """
        Process a request using the special API.
        
        Args:
            request_data: Request data containing messages and optional configuration
            
        Returns:
            SpecialAPIResponse with success status and response data
        """
        start_time = datetime.now()
        self.stats["total_requests"] += 1
        self.stats["last_activity"] = datetime.now()
        
        try:
            # Extract configuration overrides first
            api_key = request_data.get("SPECIAL_API_KEY", self.current_config.api_key)
            model_id = request_data.get("SPECIAL_API_MODEL_ID", self.current_config.model_id)
            messages = request_data.get("messages", [])
            max_tokens = request_data.get("max_tokens", self.current_config.max_tokens)
            temperature = request_data.get("temperature", self.current_config.temperature)
            custom_parameters = request_data.get("custom_parameters", self.current_config.custom_parameters)
            
            # Validate API key is available
            if not api_key:
                raise Exception("No special API key available. API key should be set by CCU during startup or provided in request data.")
            
            # Validate model ID
            if not model_id:
                raise Exception("No special model ID provided. Please configure SPECIAL_API_MODEL_ID.")
            
            # Create temporary config for this request
            temp_config = SpecialAPIConfig(
                api_key=api_key,
                model_id=model_id,
                max_tokens=max_tokens,
                temperature=temperature,
                max_retries=self.current_config.max_retries,
                timeout=self.current_config.timeout,
                custom_parameters=custom_parameters
            )
            
            # Process the request
            response = await self._make_special_completion(temp_config, messages)
            
            # Update statistics
            end_time = datetime.now()
            response_time = (end_time - start_time).total_seconds()
            
            if response.success:
                self.stats["successful_requests"] += 1
                if response.tokens_used:
                    self.stats["total_tokens_used"] += response.tokens_used
            else:
                self.stats["failed_requests"] += 1
            
            # Update average response time
            if self.stats["total_requests"] > 1:
                self.stats["average_response_time"] = (
                    (self.stats["average_response_time"] * (self.stats["total_requests"] - 1) + response_time) 
                    / self.stats["total_requests"]
                )
            else:
                self.stats["average_response_time"] = response_time
            
            return response
            
        except Exception as e:
            error_msg = f"SAAIM process_request error: {str(e)}"
            self.logger.error(error_msg)
            self.error_manager.log_error_with_generation("SAAIM", "UnknownClass", "UnknownFunction", error_msg)
            self.stats["failed_requests"] += 1
            
            return SpecialAPIResponse(
                success=False,
                error=error_msg,
                timestamp=datetime.now().isoformat()
            )
    
    async def _make_special_completion(self, config: SpecialAPIConfig, messages: List[Dict[str, str]]) -> SpecialAPIResponse:
        """
        Make a completion request to the special API.
        
        Args:
            config: Configuration for the API call
            messages: List of message dictionaries
            
        Returns:
            SpecialAPIResponse with the completion result
        """
        headers = {
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": config.model_id,
            "messages": messages,
            "max_tokens": config.max_tokens,
            "temperature": config.temperature
        }
        
        # Add custom parameters if provided
        if config.custom_parameters:
            payload.update(config.custom_parameters)
        
        for attempt in range(config.max_retries):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        self.chat_completions_url,
                        headers=headers,
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=config.timeout)
                    ) as response:
                        
                        if response.status == 200:
                            data = await response.json()
                            
                            # Extract response content
                            if "choices" in data and len(data["choices"]) > 0:
                                choice = data["choices"][0]
                                response_text = choice.get("message", {}).get("content", "")
                                
                                # Extract usage information
                                usage = data.get("usage", {})
                                tokens_used = usage.get("total_tokens", 0)
                                
                                return SpecialAPIResponse(
                                    success=True,
                                    response=response_text,
                                    model_used=config.model_id,
                                    tokens_used=tokens_used,
                                    custom_metadata=data.get("metadata"),
                                    timestamp=datetime.now().isoformat()
                                )
                            else:
                                raise Exception("No choices in response")
                        
                        elif response.status in [401, 403, 404, 429, 500, 503]:
                            # Use centralized API error handling
                            error_text = await response.text()
                            error_result = await self.handle_api_error(error_text, response.status, {
                                "attempt": attempt,
                                "max_retries": config.max_retries,
                                "model_id": config.model_id
                            })
                            
                            # Check if we should retry based on error handler recommendation
                            if error_result.get("retry_recommended", False) and attempt < config.max_retries - 1:
                                retry_delay = error_result.get("retry_delay", 2 ** attempt)
                                self.logger.warning(f"API error, retrying in {retry_delay}s... (attempt {attempt + 1})")
                                await asyncio.sleep(retry_delay)
                                continue
                            else:
                                # Don't retry or max retries reached
                                error_msg = error_result.get('error_details', {}).get('error_message', error_text)
                                return SpecialAPIResponse(
                                    success=False,
                                    error=error_msg,
                                    timestamp=datetime.now().isoformat()
                                )
                        else:
                            error_text = await response.text()
                            error_msg = f"API call failed with status {response.status}: {error_text}"
                            self.log_error(error_msg, "SpecialAPIActivationModule", "_make_special_completion")
                            return SpecialAPIResponse(
                                success=False,
                                error=error_msg,
                                timestamp=datetime.now().isoformat()
                            )
                            
            except asyncio.TimeoutError:
                error_msg = f"Request timeout after {config.timeout} seconds"
                self.log_error(error_msg, "SpecialAPIActivationModule", "_make_special_completion")
                if attempt < config.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                return SpecialAPIResponse(
                    success=False,
                    error=error_msg,
                    timestamp=datetime.now().isoformat()
                )
                
            except Exception as e:
                error_msg = f"Request failed: {str(e)}"
                self.log_error(error_msg, "SpecialAPIActivationModule", "_make_special_completion")
                if attempt < config.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                return SpecialAPIResponse(
                    success=False,
                    error=error_msg,
                    timestamp=datetime.now().isoformat()
                )
        
        # If all retries failed
        error_msg = f"All {config.max_retries} retry attempts failed"
        self.log_error(error_msg, "SpecialAPIActivationModule", "_make_special_completion")
        return SpecialAPIResponse(
            success=False,
            error=error_msg,
            timestamp=datetime.now().isoformat()
        )
    
    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the SAAIM module."""
        return {
            "module": "SAAIM",
            "configured": self.is_configured(),
            "api_key_set": bool(self.current_config.api_key),
            "model_id_set": bool(self.current_config.model_id),
            "active_requests": len(self.active_requests),
            "stats": self.stats.copy(),
            "error_handling": "EMM Integrated"
        }
    
    def get_config(self) -> Dict[str, Any]:
        """Get the current configuration."""
        return asdict(self.current_config)
    
    def reset_stats(self):
        """Reset statistics."""
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_tokens_used": 0,
            "average_response_time": 0,
            "last_activity": None
        }
        self.logger.info("SAAIM: Statistics reset")
    
    def validate_model_id(self, model_id: str) -> bool:
        """
        Validate if a model ID is properly formatted.
        
        Args:
            model_id: The model ID to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not model_id:
            return False
        
        # Basic validation - model IDs should not be empty and should contain valid characters
        if len(model_id.strip()) == 0:
            return False
        
        # Check for basic format (alphanumeric, hyphens, underscores, colons, periods)
        # This allows for models like gpt-3.5-turbo, ft:gpt-3.5-turbo:org:model:1234567890
        import re
        pattern = r'^[a-zA-Z0-9\-_:.]+$'
        return bool(re.match(pattern, model_id))
    
    async def test_connection(self) -> bool:
        """
        Test the connection to the special API.
        
        Returns:
            True if connection is successful, False otherwise
        """
        if not self.is_configured():
            return False
        
        test_messages = [{"role": "user", "content": "Hello"}]
        
        try:
            response = await self.process_request({
                "messages": test_messages,
                "max_tokens": 10
            })
            return response.success
        except Exception as e:
            self.logger.error(f"SAAIM connection test failed: {e}")
            return False
    
    def cleanup(self):
        """Clean up resources."""
        self.active_requests.clear()
        self.logger.info("SAAIM: Cleanup completed")
    
    def log_error(self, error_message: str, class_name: str = "UnknownClass", function_name: str = "UnknownFunction", sub_function: str = "001"):
        """Log an error using EMM."""
        return self.error_manager.log_error_with_generation(
            "SAAIM", 
            class_name, 
            function_name, 
            error_message, 
            sub_function
        )
    
    def generate_error_code(self, class_name: str = "UnknownClass", function_name: str = "UnknownFunction", sub_function: str = "001") -> str:
        """Generate an error code using EMM."""
        return self.error_manager.generate_error_code("SAAIM", class_name, function_name, sub_function)
    
    async def handle_exception(self, exception: Exception, class_name: str = "UnknownClass", function_name: str = "UnknownFunction", context: dict = None):
        """Handle exceptions with comprehensive logging and recovery."""
        error_message = str(exception)
        
        # Log the error
        error_code = self.log_error(error_message, class_name, function_name)
        
        # Check if it's an API error
        if hasattr(exception, 'status_code') or 'api' in error_message.lower():
            return await self.handle_api_error(error_message, getattr(exception, 'status_code', None), context)
        
        # Return standard error response
        return {
            "success": False,
            "error_code": error_code,
            "error_message": error_message,
            "timestamp": datetime.now().isoformat()
        }
    
    async def handle_api_error(self, error_response: str, status_code: int = None, context: dict = None) -> dict:
        """Handle API errors using the centralized API error handler."""
        try:
            # Use the centralized API error handler
            result = await api_error_handler.handle_api_error(error_response, status_code, context)
            
            # Log the error with EMM
            self.error_manager.log_error_with_generation(
                "SAAIM",
                "SAAIM",
                "handle_api_error",
                f"API Error: {result.get('api_error_type', 'unknown')}",
                context=result
            )
            
            # Send report to CCU
            await api_error_handler.send_error_report_to_ccu(result)
            
            return result
            
        except Exception as e:
            self.error_manager.log_error_with_generation(
                "SAAIM",
                "SAAIM",
                "handle_api_error",
                f"Error handling API error: {str(e)}"
            )
            return {"success": False, "error": str(e)}


# Global instance and alias for compatibility
saaim = SpecialAPIActivationModule()
SAAIM = SpecialAPIActivationModule  # Class alias
    