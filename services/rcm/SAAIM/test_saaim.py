"""
Test module for Special API Activation and Interaction Module (SAAIM)
"""

import asyncio
import pytest
import logging
from EMM.emm import ErrorManagementModule
from EMM.api_error_handler import api_error_handler
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from saaim import (
    SpecialAPIActivationModule, 
    SpecialAPIConfig, 
    SpecialAPIResponse,
    saaim
)

# Configure logging for tests
logging.basicConfig(level=logging.INFO)

class TestSpecialAPIConfig:
    def __init__(self):
        self.error_manager = ErrorManagementModule()

    """Test the SpecialAPIConfig dataclass."""
    
    def test_config_creation(self):
        """Test creating a SpecialAPIConfig instance."""
        config = SpecialAPIConfig(
            api_key="test_key",
            model_id="test_model",
            max_tokens=2000,
            temperature=0.5
        )
        
        assert config.api_key == "test_key"
        assert config.model_id == "test_model"
        assert config.max_tokens == 2000
        assert config.temperature == 0.5
        assert config.max_retries == 3  # default
        assert config.timeout == 30  # default
    
    def test_config_with_custom_parameters(self):
        """Test config with custom parameters."""
        custom_params = {"top_p": 0.9, "frequency_penalty": 0.1}
        config = SpecialAPIConfig(
            api_key="test_key",
            model_id="test_model",
            custom_parameters=custom_params
        )
        
        assert config.custom_parameters == custom_params


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

class TestSpecialAPIResponse:
    """Test the SpecialAPIResponse dataclass."""
    
    def test_successful_response(self):
        """Test creating a successful response."""
        response = SpecialAPIResponse(
            success=True,
            response="Test response",
            model_used="test_model",
            tokens_used=100,
            timestamp="2023-01-01T00:00:00"
        )
        
        assert response.success is True
        assert response.response == "Test response"
        assert response.model_used == "test_model"
        assert response.tokens_used == 100
        assert response.timestamp == "2023-01-01T00:00:00"
        assert response.error is None
    
    def test_error_response(self):
        """Test creating an error response."""
        response = SpecialAPIResponse(
            success=False,
            error="Test error",
            timestamp="2023-01-01T00:00:00"
        )
        
        assert response.success is False
        assert response.error == "Test error"
        assert response.response is None
        assert response.model_used is None


class TestSpecialAPIActivationModule:
    """Test the SpecialAPIActivationModule class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.saaim = SpecialAPIActivationModule()
    
    def test_initialization(self):
        """Test module initialization."""
        assert self.saaim.DEFAULT_SPECIAL_API_KEY is None
        assert self.saaim.DEFAULT_SPECIAL_API_MODEL_ID is None
        assert isinstance(self.saaim.current_config, SpecialAPIConfig)
        assert isinstance(self.saaim.active_requests, dict)
        assert isinstance(self.saaim.stats, dict)
        assert "total_requests" in self.saaim.stats
        assert "successful_requests" in self.saaim.stats
        assert "failed_requests" in self.saaim.stats
    
    def test_set_special_api_key(self):
        """Test setting the special API key."""
        self.saaim.set_special_api_key("new_api_key")
        
        assert self.saaim.current_config.api_key == "new_api_key"
        assert self.saaim.DEFAULT_SPECIAL_API_KEY == "new_api_key"
    
    def test_set_special_model_id(self):
        """Test setting the special model ID."""
        self.saaim.set_special_model_id("new_model_id")
        
        assert self.saaim.current_config.model_id == "new_model_id"
        assert self.saaim.DEFAULT_SPECIAL_API_MODEL_ID == "new_model_id"
    
    def test_set_config(self):
        """Test updating configuration parameters."""
        self.saaim.set_config(max_tokens=1500, temperature=0.8)
        
        assert self.saaim.current_config.max_tokens == 1500
        assert self.saaim.current_config.temperature == 0.8
    
    def test_is_configured(self):
        """Test configuration status check."""
        # Initially not configured
        assert self.saaim.is_configured() is False
        
        # Set API key only
        self.saaim.set_special_api_key("test_key")
        assert self.saaim.is_configured() is False
        
        # Set model ID only
        self.saaim.set_special_api_key("")
        self.saaim.set_special_model_id("test_model")
        assert self.saaim.is_configured() is False
        
        # Set both
        self.saaim.set_special_api_key("test_key")
        assert self.saaim.is_configured() is True
    
    def test_validate_model_id(self):
        """Test model ID validation."""
        # Valid model IDs
        assert self.saaim.validate_model_id("gpt-4") is True
        assert self.saaim.validate_model_id("custom-model-123") is True
        assert self.saaim.validate_model_id("model:version") is True
        assert self.saaim.validate_model_id("model_with_underscores") is True
        
        # Invalid model IDs
        assert self.saaim.validate_model_id("") is False
        assert self.saaim.validate_model_id("   ") is False
        assert self.saaim.validate_model_id("model with spaces") is False
        assert self.saaim.validate_model_id("model@special") is False
    
    def test_get_status(self):
        """Test getting module status."""
        status = self.saaim.get_status()
        
        assert status["module"] == "SAAIM"
        assert "configured" in status
        assert "api_key_set" in status
        assert "model_id_set" in status
        assert "active_requests" in status
        assert "stats" in status
        assert "error_codes" in status
    
    def test_get_config(self):
        """Test getting current configuration."""
        config = self.saaim.get_config()
        
        assert "api_key" in config
        assert "model_id" in config
        assert "max_tokens" in config
        assert "temperature" in config
        assert "max_retries" in config
        assert "timeout" in config
    
    def test_reset_stats(self):
        """Test resetting statistics."""
        # Set some stats
        self.saaim.stats["total_requests"] = 10
        self.saaim.stats["successful_requests"] = 8
        self.saaim.stats["failed_requests"] = 2
        
        self.saaim.reset_stats()
        
        assert self.saaim.stats["total_requests"] == 0
        assert self.saaim.stats["successful_requests"] == 0
        assert self.saaim.stats["failed_requests"] == 0
        assert self.saaim.stats["total_tokens_used"] == 0
        assert self.saaim.stats["average_response_time"] == 0
        assert self.saaim.stats["last_activity"] is None
    
    def test_cleanup(self):
        """Test cleanup method."""
        # Add some active requests
        self.saaim.active_requests["test_id"] = {"data": "test"}
        
        self.saaim.cleanup()
        
        assert len(self.saaim.active_requests) == 0
    
    @pytest.mark.asyncio
    async def test_process_request_not_configured(self):
        """Test processing request when not configured."""
        request_data = {
            "messages": [{"role": "user", "content": "Hello"}]
        }
        
        response = await self.saaim.process_request(request_data)
        
        assert response.success is False
        assert "not properly configured" in response.error
        assert self.saaim.stats["failed_requests"] == 1
    
    @pytest.mark.asyncio
    async def test_process_request_no_model_id(self):
        """Test processing request with no model ID."""
        self.saaim.set_special_api_key("test_key")
        # Don't set model ID
        
        request_data = {
            "messages": [{"role": "user", "content": "Hello"}]
        }
        
        response = await self.saaim.process_request(request_data)
        
        assert response.success is False
        assert "No model ID provided" in response.error
    
    @pytest.mark.asyncio
    async def test_process_request_with_configuration_overrides(self):
        """Test processing request with configuration overrides."""
        self.saaim.set_special_api_key("default_key")
        self.saaim.set_special_model_id("default_model")
        
        request_data = {
            "messages": [{"role": "user", "content": "Hello"}],
            "SPECIAL_API_KEY": "override_key",
            "SPECIAL_API_MODEL_ID": "override_model",
            "max_tokens": 500,
            "temperature": 0.3
        }
        
        with patch.object(self.saaim, '_make_special_completion') as mock_completion:
            mock_response = SpecialAPIResponse(
                success=True,
                response="Test response",
                model_used="override_model",
                tokens_used=50
            )
            mock_completion.return_value = mock_response
            
            response = await self.saaim.process_request(request_data)
            
            # Check that the mock was called with override values
            mock_completion.assert_called_once()
            call_args = mock_completion.call_args
            config = call_args[0][0]  # First argument is config
            messages = call_args[0][1]  # Second argument is messages
            
            assert config.api_key == "override_key"
            assert config.model_id == "override_model"
            assert config.max_tokens == 500
            assert config.temperature == 0.3
            assert messages == [{"role": "user", "content": "Hello"}]
            
            assert response.success is True
            assert response.response == "Test response"
            assert self.saaim.stats["successful_requests"] == 1
    
    @pytest.mark.asyncio
    async def test_make_special_completion_success(self):
        """Test successful API completion."""
        self.saaim.set_special_api_key("test_key")
        self.saaim.set_special_model_id("test_model")
        
        config = SpecialAPIConfig(
            api_key="test_key",
            model_id="test_model",
            max_tokens=100,
            temperature=0.7
        )
        messages = [{"role": "user", "content": "Hello"}]
        
        mock_response_data = {
            "choices": [{"message": {"content": "Hello! How can I help you?"}}],
            "usage": {"total_tokens": 25},
            "metadata": {"model": "test_model"}
        }
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value.status = 200
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value.json = AsyncMock(return_value=mock_response_data)
            
            response = await self.saaim._make_special_completion(config, messages)
            
            assert response.success is True
            assert response.response == "Hello! How can I help you?"
            assert response.model_used == "test_model"
            assert response.tokens_used == 25
            assert response.custom_metadata == {"model": "test_model"}
    
    @pytest.mark.asyncio
    async def test_make_special_completion_model_not_found(self):
        """Test API completion with model not found error."""
        config = SpecialAPIConfig(
            api_key="test_key",
            model_id="invalid_model",
            max_tokens=100,
            temperature=0.7
        )
        messages = [{"role": "user", "content": "Hello"}]
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value.status = 404
            
            response = await self.saaim._make_special_completion(config, messages)
            
            assert response.success is False
            assert "Model invalid_model not found" in response.error
    
    @pytest.mark.asyncio
    async def test_make_special_completion_rate_limit(self):
        """Test API completion with rate limit error."""
        config = SpecialAPIConfig(
            api_key="test_key",
            model_id="test_model",
            max_tokens=100,
            temperature=0.7,
            max_retries=2
        )
        messages = [{"role": "user", "content": "Hello"}]
        
        with patch('aiohttp.ClientSession') as mock_session:
            # First call returns 429, second call returns 200
            mock_response = mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value
            mock_response.status = 429
            mock_response.json = AsyncMock(return_value={"error": "Rate limit exceeded"})
            
            response = await self.saaim._make_special_completion(config, messages)
            
            assert response.success is False
            assert "Rate limit exceeded" in response.error
    
    @pytest.mark.asyncio
    async def test_make_special_completion_timeout(self):
        """Test API completion with timeout error."""
        config = SpecialAPIConfig(
            api_key="test_key",
            model_id="test_model",
            max_tokens=100,
            temperature=0.7,
            max_retries=2
        )
        messages = [{"role": "user", "content": "Hello"}]
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_session.return_value.__aenter__.return_value.post.side_effect = asyncio.TimeoutError()
            
            response = await self.saaim._make_special_completion(config, messages)
            
            assert response.success is False
            assert "Request timeout" in response.error
    
    @pytest.mark.asyncio
    async def test_test_connection_not_configured(self):
        """Test connection test when not configured."""
        result = await self.saaim.test_connection()
        assert result is False
    
    @pytest.mark.asyncio
    async def test_test_connection_configured(self):
        """Test connection test when configured."""
        self.saaim.set_special_api_key("test_key")
        self.saaim.set_special_model_id("test_model")
        
        with patch.object(self.saaim, 'process_request') as mock_process:
            mock_process.return_value = SpecialAPIResponse(success=True)
            
            result = await self.saaim.test_connection()
            assert result is True


class TestGlobalSAAIM:
    """Test the global SAAIM instance."""
    
    def test_global_instance(self):
        """Test that the global instance exists and is properly configured."""
        assert saaim is not None
        assert isinstance(saaim, SpecialAPIActivationModule)
        assert saaim.get_status()["module"] == "SAAIM"


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"]) 