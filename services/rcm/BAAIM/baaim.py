"""
Basic API Activation and Interaction Module (BAAIM)

Designed for standard, non-agentic interactions with the OpenAI API.
Handles chat completions, text generation, and response processing.
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
class BasicAPIConfig:
    """Configuration for basic API interactions."""
    api_key: str
    model: str = "gpt-4.1-nano"
    max_tokens: int = 1000
    temperature: float = 0.7
    max_retries: int = 3
    timeout: int = 30

@dataclass
class BasicAPIResponse:
    """Response from basic API interaction."""
    success: bool
    response: Optional[str] = None
    model_used: Optional[str] = None
    tokens_used: Optional[int] = None
    error: Optional[str] = None
    timestamp: Optional[str] = None

class BasicAPIActivationModule:
    """
    Basic API Activation and Interaction Module (BAAIM)
    
    Handles standard, non-agentic interactions with OpenAI API:
    - Default model: "gpt-4.1-nano"
    - Uses DEFAULT_API_KEY but accepts override API_KEY
    - Provides mechanism to override both API_KEY and model name
    - Implements async/await patterns for non-blocking operations
    - Comprehensive error handling and logging
    """
    
    def __init__(self):
        """Initialize the BAAIM module."""
        self.logger = logging.getLogger(__name__)
        self.error_manager = ErrorManagementModule()
        
        # Default configuration - API key should be set via CCU→ECM for security
        self.DEFAULT_API_KEY = None  # Will be set by CCU via ECM during startup
        self.DEFAULT_MODEL = "gpt-4.1-nano"
        
        # Current configuration
        self.current_config = BasicAPIConfig(
            api_key=self.DEFAULT_API_KEY or "",  # Empty string if None
            model=self.DEFAULT_MODEL
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
    
    def set_api_key(self, api_key: str):
        """Set the API key for basic API interactions."""
        self.current_config.api_key = api_key
        self.logger.info("BAAIM: API key updated")
    
    def set_model(self, model: str):
        """Set the model for API interactions."""
        self.current_config.model = model
        self.logger.info(f"BAAIM: Model updated to {model}")
    
    def set_config(self, **kwargs):
        """Update configuration parameters."""
        for key, value in kwargs.items():
            if hasattr(self.current_config, key):
                setattr(self.current_config, key, value)
                self.logger.info(f"BAAIM: {key} updated to {value}")
    
    async def process_request(self, request_data: Dict[str, Any]) -> BasicAPIResponse:
        """
        Process a request using the basic API.
        
        Args:
            request_data: Request data containing messages and optional configuration
            
        Returns:
            BasicAPIResponse with success status and response data
        """
        start_time = datetime.now()
        self.stats["total_requests"] += 1
        self.stats["last_activity"] = datetime.now()
        
        try:
            # Extract configuration overrides
            api_key = request_data.get("api_key", self.current_config.api_key)
            model = request_data.get("model", self.current_config.model)
            messages = request_data.get("messages", [])
            max_tokens = request_data.get("max_tokens", self.current_config.max_tokens)
            temperature = request_data.get("temperature", self.current_config.temperature)
            
            # Validate API key is available
            if not api_key:
                raise Exception("No API key available. API key should be set by CCU during startup or provided in request data.")
            
            print(f"DEBUG: BAAIM process_request - extracted messages: {messages}")
            print(f"DEBUG: BAAIM process_request - request_data keys: {list(request_data.keys())}")
            
            # Create temporary config for this request
            temp_config = BasicAPIConfig(
                api_key=api_key,
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                max_retries=self.current_config.max_retries,
                timeout=self.current_config.timeout
            )
            
            # Process the request
            response = await self._make_chat_completion(temp_config, messages)
            
            # Update statistics
            processing_time = (datetime.now() - start_time).total_seconds()
            self._update_stats(True, processing_time, response.tokens_used or 0)
            
            self.logger.info(f"BAAIM: Request processed successfully in {processing_time:.2f}s")
            return response
            
        except Exception as e:
            error_msg = f"Basic API request processing failed: {e}"
            self.logger.error(error_msg)
            self.error_manager.log_error_with_generation("BAAIM", "UnknownClass", "UnknownFunction", error_msg)
            self._update_stats(False, 0, 0)
            
            return BasicAPIResponse(
                success=False,
                error=error_msg,
                timestamp=datetime.now().isoformat()
            )
    
    async def _make_chat_completion(self, config: BasicAPIConfig, messages: List[Dict[str, str]]) -> BasicAPIResponse:
        """Make a chat completion request to OpenAI API."""
        try:
            headers = {
                "Authorization": f"Bearer {config.api_key}",
                "Content-Type": "application/json"
            }
            # Make a deep copy of messages to avoid mutation across retries
            import copy
            original_messages = copy.deepcopy(messages)
            
            for attempt in range(config.max_retries):
                try:
                    payload = {
                        "model": config.model,
                        "messages": original_messages,
                        "max_tokens": config.max_tokens,
                        "temperature": config.temperature
                    }
                    print(f"DEBUG: BAAIM sending payload to OpenAI: {json.dumps(payload, indent=2)}")
                    async with aiohttp.ClientSession() as session:
                        async with session.post(
                            self.chat_completions_url,
                            headers=headers,
                            json=payload,
                            timeout=aiohttp.ClientTimeout(total=config.timeout)
                        ) as response:
                            if response.status == 200:
                                data = await response.json()
                                return self._parse_response(data, config.model)
                            elif response.status in [401, 403, 429, 500, 503]:
                                error_text = await response.text()
                                error_result = await self.handle_api_error(error_text, response.status, {
                                    "attempt": attempt,
                                    "max_retries": config.max_retries,
                                    "model": config.model
                                })
                                if error_result.get("retry_recommended", False) and attempt < config.max_retries - 1:
                                    retry_delay = error_result.get("retry_delay", 2 ** attempt)
                                    self.logger.warning(f"API error, retrying in {retry_delay}s... (attempt {attempt + 1})")
                                    await asyncio.sleep(retry_delay)
                                    continue
                                else:
                                    raise Exception(f"API error: {error_result.get('error_details', {}).get('error_message', error_text)}")
                            else:
                                error_text = await response.text()
                                raise Exception(f"API call failed with status {response.status}: {error_text}")
                except asyncio.TimeoutError:
                    if attempt < config.max_retries - 1:
                        self.logger.warning(f"Request timeout, retrying... (attempt {attempt + 1})")
                        continue
                    else:
                        raise Exception("Request timed out after all retries")
            raise Exception("All retry attempts failed")
        except Exception as e:
            self.logger.error(f"Chat completion error: {e}")
            error_result = await self.handle_exception(e, "BasicAPIActivationModule", "_make_chat_completion", {
                "config": asdict(config),
                "messages_count": len(messages)
            })
            raise Exception(f"Chat completion failed: {error_result.get('error_message', str(e))}")
    
    def _parse_response(self, data: Dict[str, Any], model_used: str) -> BasicAPIResponse:
        """Parse the API response."""
        try:
            choices = data.get("choices", [])
            if not choices:
                raise Exception("No choices in response")
            
            message = choices[0].get("message", {})
            content = message.get("content", "")
            
            usage = data.get("usage", {})
            tokens_used = usage.get("total_tokens", 0)
            
            return BasicAPIResponse(
                success=True,
                response=content,
                model_used=model_used,
                tokens_used=tokens_used,
                timestamp=datetime.now().isoformat()
            )
            
        except Exception as e:
            self.logger.error(f"Response parsing error: {e}")
            # Log the error with EMM
            self.log_error(str(e), "BasicAPIActivationModule", "_parse_response")
            raise Exception(f"Response parsing failed: {str(e)}")
    
    def _update_stats(self, success: bool, processing_time: float, tokens_used: int):
        """Update statistics."""
        if success:
            self.stats["successful_requests"] += 1
            self.stats["total_tokens_used"] += tokens_used
            # Update average response time
            total_successful = self.stats["successful_requests"]
            current_avg = self.stats["average_response_time"]
            self.stats["average_response_time"] = (current_avg * (total_successful - 1) + processing_time) / total_successful
        else:
            self.stats["failed_requests"] += 1
    
    def get_request_status(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific request."""
        return self.active_requests.get(request_id)
    
    def get_module_status(self) -> Dict[str, Any]:
        """Get BAAIM module status."""
        return {
            "module": "BAAIM",
            "status": "active",
            "current_model": self.current_config.model,
            "active_requests": len(self.active_requests),
            "stats": self.stats.copy(),
            "last_activity": self.stats["last_activity"]
        }
    
    def get_config(self) -> Dict[str, Any]:
        """Get current configuration."""
        return asdict(self.current_config)
    
    def cleanup_request(self, request_id: str) -> bool:
        """Clean up a request."""
        if request_id in self.active_requests:
            del self.active_requests[request_id]
            self.logger.info(f"BAAIM: Cleaned up request {request_id}")
            return True
        return False
    
    async def test_connection(self) -> bool:
        """Test the API connection."""
        try:
            test_messages = [{"role": "user", "content": "Hello"}]
            response = await self.process_request({
                "messages": test_messages,
                "max_tokens": 10
            })
            return response.success
        except Exception as e:
            self.logger.error(f"Connection test failed: {e}")
            return False
    
    def get_available_models(self) -> List[str]:
        """Get list of available models (mocked for now)."""
        return [
            "gpt-4.1-nano",
            "gpt-4.1-micro",
            "gpt-4.1-mini",
            "gpt-4",
            "gpt-3.5-turbo"
        ]
    
    def validate_model(self, model: str) -> bool:
        """Validate if a model is available."""
        available_models = self.get_available_models()
        return model in available_models
    
    def log_error(self, error_message: str, class_name: str = "UnknownClass", function_name: str = "UnknownFunction", sub_function: str = "001"):
        """Log an error using EMM."""
        return self.error_manager.log_error_with_generation(
            "BAAIM", 
            class_name, 
            function_name, 
            error_message, 
            sub_function
        )
    
    def generate_error_code(self, class_name: str = "UnknownClass", function_name: str = "UnknownFunction", sub_function: str = "001") -> str:
        """Generate an error code using EMM."""
        return self.error_manager.generate_error_code("BAAIM", class_name, function_name, sub_function)
    
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
                "BAAIM",
                "BAAIM",
                "handle_api_error",
                f"API Error: {result.get('api_error_type', 'unknown')}",
                context=result
            )
            
            # Send report to CCU
            await api_error_handler.send_error_report_to_ccu(result)
            
            return result
            
        except Exception as e:
            self.error_manager.log_error_with_generation(
                "BAAIM",
                "BAAIM",
                "handle_api_error",
                f"Error handling API error: {str(e)}"
            )
            return {"success": False, "error": str(e)}


# Global instance and alias for compatibility
baaim = BasicAPIActivationModule()
BAAIM = BasicAPIActivationModule  # Class alias 