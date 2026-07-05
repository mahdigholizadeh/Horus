"""
Asynchronous API Communication Module (AACM)

Manages all interactions with the OpenAI API using async/await patterns for non-blocking, efficient I/O operations.
"""

import asyncio
import aiohttp
import logging
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
import time

from EMM.emm import ErrorManagementModule
from EMM.api_error_handler import api_error_handler


class AsyncAPIClient:
    """Async HTTP client for API communications."""
    
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.session = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def post(self, url: str, data: Dict[str, Any], headers: Dict[str, str] = None) -> Dict[str, Any]:
        """Make async POST request."""
        if not self.session:
            raise RuntimeError("Session not initialized")
        
        async with self.session.post(url, json=data, headers=headers) as response:
            response.raise_for_status()
            return await response.json()




class AsynchronousAPICommunicationModule:
    """
    Asynchronous API Communication Module (AACM)
    
    Manages all interactions with the OpenAI API using async/await patterns.
    """
    
    def __init__(self):
        """Initialize the AACM module."""
        self.logger = logging.getLogger(__name__)
        self.error_manager = ErrorManagementModule()
        
        # API configuration
        self.base_url = "https://api.openai.com/v1"
        self.default_headers = {
            "Content-Type": "application/json"
        }
        
        # Connection pool settings
        self.max_connections = 100
        self.max_connections_per_host = 10
        self.connection_timeout = 30
        self.request_timeout = 60
        
        # Error codes for this module (Module code: 03 for AACM)
        # Error codes now generated dynamically by EMM
        
        # Request tracking
        self.active_requests = {}
        self.completed_requests = {}
        self.failed_requests = {}
        
        # Statistics
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_response_time": 0,
            "average_response_time": 0
        }
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session with proper configuration."""
        connector = aiohttp.TCPConnector(
            limit=self.max_connections,
            limit_per_host=self.max_connections_per_host,
            ttl_dns_cache=300
        )
        
        timeout = aiohttp.ClientTimeout(
            total=self.request_timeout,
            connect=self.connection_timeout
        )
        
        return aiohttp.ClientSession(
            connector=connector,
            timeout=timeout
        )
    
    async def make_api_request(
        self,
        endpoint: str,
        data: Dict[str, Any],
        api_key: str,
        request_id: str,
        model: str = "gpt-4.1-nano"
    ) -> Dict[str, Any]:
        """
        Make an async API request to OpenAI.
        
        Args:
            endpoint: API endpoint (e.g., "/chat/completions")
            data: Request payload
            api_key: OpenAI API key
            request_id: Unique request identifier
            model: Model to use for the request
            
        Returns:
            API response as dictionary
        """
        start_time = time.time()
        
        try:
            # Track active request
            self.active_requests[request_id] = {
                "start_time": start_time,
                "endpoint": endpoint,
                "model": model,
                "status": "active"
            }
            
            self.logger.info(f"Making API request {request_id} to {endpoint}")
            
            # Prepare headers
            headers = {
                **self.default_headers,
                "Authorization": f"Bearer {api_key}"
            }
            
            # Prepare request data
            request_data = {
                "model": model,
                **data
            }
            
            # Make async request
            session = await self._get_session()
            async with session:
                url = f"{self.base_url}{endpoint}"
                
                async with session.post(url, json=request_data, headers=headers) as response:
                    response.raise_for_status()
                    result = await response.json()
                    
                    # Calculate response time
                    response_time = time.time() - start_time
                    
                    # Update statistics
                    self.stats["total_requests"] += 1
                    self.stats["successful_requests"] += 1
                    self.stats["total_response_time"] += response_time
                    self.stats["average_response_time"] = (
                        self.stats["total_response_time"] / self.stats["successful_requests"]
                    )
                    
                    # Track completed request
                    self.completed_requests[request_id] = {
                        "response_time": response_time,
                        "status": "success",
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    # Remove from active requests
                    if request_id in self.active_requests:
                        del self.active_requests[request_id]
                    
                    self.logger.info(f"API request {request_id} completed in {response_time:.2f}s")
                    return result
                    
        except aiohttp.ClientError as e:
            error_msg = f"Connection error for request {request_id}: {e}"
            self.log_error(error_msg, "AsynchronousAPICommunicationModule", "make_api_request")
            await self._handle_failed_request(request_id, "connection_error", str(e))
            raise
            
        except asyncio.TimeoutError as e:
            error_msg = f"Timeout error for request {request_id}: {e}"
            self.log_error(error_msg, "AsynchronousAPICommunicationModule", "make_api_request")
            await self._handle_failed_request(request_id, "timeout_error", str(e))
            raise
            
        except aiohttp.ClientResponseError as e:
            if e.status == 429:
                error_msg = f"Rate limit exceeded for request {request_id}"
                self.log_error(error_msg, "AsynchronousAPICommunicationModule", "make_api_request")
                await self._handle_failed_request(request_id, "rate_limit_error", str(e))
            else:
                error_msg = f"API error for request {request_id}: {e}"
                self.log_error(error_msg, "AsynchronousAPICommunicationModule", "make_api_request")
                await self._handle_failed_request(request_id, "api_error", str(e))
            raise
            
        except Exception as e:
            error_msg = f"Unexpected error for request {request_id}: {e}"
            self.log_error(error_msg, "AsynchronousAPICommunicationModule", "make_api_request")
            await self._handle_failed_request(request_id, "unexpected_error", str(e))
            raise
    
    async def _handle_failed_request(self, request_id: str, error_type: str, error_message: str):
        """Handle failed request tracking."""
        response_time = time.time() - self.active_requests.get(request_id, {}).get("start_time", time.time())
        
        self.stats["total_requests"] += 1
        self.stats["failed_requests"] += 1
        
        self.failed_requests[request_id] = {
            "error_type": error_type,
            "error_message": error_message,
            "response_time": response_time,
            "timestamp": datetime.now().isoformat()
        }
        
        if request_id in self.active_requests:
            del self.active_requests[request_id]
    
    async def make_chat_completion(
        self,
        messages: List[Dict[str, str]],
        api_key: str,
        request_id: str,
        model: str = "gpt-4.1-nano",
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> Dict[str, Any]:
        """
        Make a chat completion request.
        
        Args:
            messages: List of message dictionaries
            api_key: OpenAI API key
            request_id: Unique request identifier
            model: Model to use
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            
        Returns:
            Chat completion response
        """
        data = {
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        return await self.make_api_request("/chat/completions", data, api_key, request_id, model)
    
    async def make_agent_request(
        self,
        thread_id: str,
        message: str,
        api_key: str,
        request_id: str,
        assistant_id: str = "asst_lQCwiQAJcycDj7YqHBafyWtT"
    ) -> Dict[str, Any]:
        """
        Make an agent request using OpenAI's Assistant API.
        
        Args:
            thread_id: Thread ID for the conversation
            message: User message
            api_key: OpenAI API key
            request_id: Unique request identifier
            assistant_id: Assistant ID to use
            
        Returns:
            Agent response
        """
        # First, add message to thread
        message_data = {
            "role": "user",
            "content": message
        }
        
        # Add message to thread
        session = await self._get_session()
        async with session:
            url = f"{self.base_url}/threads/{thread_id}/messages"
            headers = {
                **self.default_headers,
                "Authorization": f"Bearer {api_key}"
            }
            
            async with session.post(url, json=message_data, headers=headers) as response:
                response.raise_for_status()
        
        # Run the assistant
        run_data = {
            "assistant_id": assistant_id
        }
        
        session = await self._get_session()
        async with session:
            url = f"{self.base_url}/threads/{thread_id}/runs"
            headers = {
                **self.default_headers,
                "Authorization": f"Bearer {api_key}"
            }
            
            async with session.post(url, json=run_data, headers=headers) as response:
                response.raise_for_status()
                run_result = await response.json()
                run_id = run_result["id"]
        
        # Wait for completion
        while True:
            session = await self._get_session()
            async with session:
                url = f"{self.base_url}/threads/{thread_id}/runs/{run_id}"
                headers = {
                    **self.default_headers,
                    "Authorization": f"Bearer {api_key}"
                }
                
                async with session.get(url, headers=headers) as response:
                    response.raise_for_status()
                    run_status = await response.json()
                    
                    if run_status["status"] == "completed":
                        break
                    elif run_status["status"] == "failed":
                        raise Exception(f"Run failed: {run_status.get('last_error', {})}")
                    
                    await asyncio.sleep(1)
        
        # Get the response
        session = await self._get_session()
        async with session:
            url = f"{self.base_url}/threads/{thread_id}/messages"
            headers = {
                **self.default_headers,
                "Authorization": f"Bearer {api_key}"
            }
            
            async with session.get(url, headers=headers) as response:
                response.raise_for_status()
                messages = await response.json()
                
                # Return the latest assistant message
                for message in messages["data"]:
                    if message["role"] == "assistant":
                        return {
                            "assistant_message": message["content"][0]["text"]["value"],
                            "run_id": run_id,
                            "thread_id": thread_id
                        }
                
                return {"error": "No assistant response found"}
    
    async def get_status(self) -> Dict[str, Any]:
        """
        Get the status of the AACM module.
        
        Returns:
            Dictionary containing module status information
        """
        return {
            "status": "active",
            "active_requests": len(self.active_requests),
            "completed_requests": len(self.completed_requests),
            "failed_requests": len(self.failed_requests),
            "statistics": self.stats,
            "last_activity": datetime.now().isoformat()
        }
    
    async def get_request_status(self, request_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the status of a specific request.
        
        Args:
            request_id: Request identifier
            
        Returns:
            Request status or None if not found
        """
        if request_id in self.active_requests:
            return {
                "status": "active",
                **self.active_requests[request_id]
            }
        elif request_id in self.completed_requests:
            return {
                "status": "completed",
                **self.completed_requests[request_id]
            }
        elif request_id in self.failed_requests:
            return {
                "status": "failed",
                **self.failed_requests[request_id]
            }
        
        return None
    
    async def start(self):
        """Start the AACM module."""
        self.logger.info("AACM module started")
    
    async def stop(self):
        """Stop the AACM module."""
        self.logger.info("AACM module stopped")
    
    def log_error(self, error_message: str, class_name: str = "UnknownClass", function_name: str = "UnknownFunction", sub_function: str = "001"):
        """Log an error using EMM."""
        return self.error_manager.log_error_with_generation(
            "AACM", 
            class_name, 
            function_name, 
            error_message, 
            sub_function
        )
    
    def generate_error_code(self, class_name: str = "UnknownClass", function_name: str = "UnknownFunction", sub_function: str = "001") -> str:
        """Generate an error code using EMM."""
        return self.error_manager.generate_error_code("AACM", class_name, function_name, sub_function)
    
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
                "AACM",
                "AACM",
                "handle_api_error",
                f"API Error: {result.get('api_error_type', 'unknown')}",
                context=result
            )
            
            # Send report to CCU
            await api_error_handler.send_error_report_to_ccu(result)
            
            return result
            
        except Exception as e:
            self.error_manager.log_error_with_generation(
                "AACM",
                "AACM",
                "handle_api_error",
                f"Error handling API error: {str(e)}"
            )
            return {"success": False, "error": str(e)} 

# Global instance and alias for compatibility
aacm = AsynchronousAPICommunicationModule()
AACM = AsynchronousAPICommunicationModule  # Class alias
