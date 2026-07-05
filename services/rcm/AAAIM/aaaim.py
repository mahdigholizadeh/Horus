"""
Agentic API Activation and Interaction Module (AAAIM)

Dedicated module for interacting with OpenAI's "Agent" models.
Handles agent-based conversations, thread management, and response processing.
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
class AgentConfig:
    """Configuration for agent interactions."""
    agent_id: str
    api_key: str
    model: str = "gpt-4"
    max_retries: int = 3
    timeout: int = 30

@dataclass
class AgentResponse:
    """Response from agent interaction."""
    success: bool
    response: Optional[str] = None
    thread_id: Optional[str] = None
    run_id: Optional[str] = None
    error: Optional[str] = None
    timestamp: Optional[str] = None

class AgenticAPIActivationModule:
    """
    Agentic API Activation and Interaction Module (AAAIM)
    
    Handles interactions with OpenAI's Agent models:
    - Default Agent ID: "asst_lQCwiQAJcycDj7YqHBafyWtT"
    - Uses DEFAULT_API_KEY but accepts override API_KEY
    - Manages agent conversations and thread lifecycle
    - Implements async/await patterns for non-blocking operations
    - Comprehensive error handling and logging
    """
    
    def __init__(self):
        """Initialize the AAAIM module."""
        self.logger = logging.getLogger(__name__)
        self.error_manager = ErrorManagementModule()
        
        # Default configuration - should be set via CCU→ECM for security
        self.DEFAULT_API_AGENT_KEY = "asst_lQCwiQAJcycDj7YqHBafyWtT"  # Agent ID can remain as default
        self.DEFAULT_API_KEY = None  # Will be set by CCU via ECM during startup
        
        # Current configuration
        self.current_config = AgentConfig(
            agent_id=self.DEFAULT_API_AGENT_KEY,
            api_key=self.DEFAULT_API_KEY or ""  # Empty string if None
        )
        
        # Active conversations
        self.active_conversations: Dict[str, Dict[str, Any]] = {}
        
        # Statistics
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "active_conversations": 0,
            "average_response_time": 0,
            "last_activity": None
        }
        
        # Error codes now generated dynamically by EMM
        
        # OpenAI API endpoints
        self.base_url = "https://api.openai.com/v1"
        self.assistants_url = f"{self.base_url}/assistants"
        self.threads_url = f"{self.base_url}/threads"
        self.messages_url = f"{self.base_url}/threads"
        self.runs_url = f"{self.base_url}/threads"
    
    def set_api_key(self, api_key: str):
        """Set the API key for agent interactions."""
        self.current_config.api_key = api_key
        self.logger.info("AAAIM: API key updated")
    
    def set_agent_id(self, agent_id: str):
        """Set the agent ID for interactions."""
        self.current_config.agent_id = agent_id
        self.logger.info(f"AAAIM: Agent ID updated to {agent_id}")
    
    def set_config(self, **kwargs):
        """Update configuration parameters."""
        for key, value in kwargs.items():
            if hasattr(self.current_config, key):
                setattr(self.current_config, key, value)
                self.logger.info(f"AAAIM: {key} updated to {value}")
    
    async def process_request(self, request_data: Dict[str, Any]) -> AgentResponse:
        """
        Process a request using the agent.
        
        Args:
            request_data: Request data containing message and optional configuration
            
        Returns:
            AgentResponse with success status and response data
        """
        start_time = datetime.now()
        self.stats["total_requests"] += 1
        self.stats["last_activity"] = datetime.now()
        
        try:
            # Extract configuration overrides
            api_key = request_data.get("api_key", self.current_config.api_key)
            agent_id = request_data.get("agent_id", self.current_config.agent_id)
            message = request_data.get("message", "")
            thread_id = request_data.get("thread_id")
            
            # Validate API key is available
            if not api_key:
                raise Exception("No API key available. API key should be set by CCU during startup or provided in request data.")
            
            # Create temporary config for this request
            temp_config = AgentConfig(
                agent_id=agent_id,
                api_key=api_key,
                model=self.current_config.model,
                max_retries=self.current_config.max_retries,
                timeout=self.current_config.timeout
            )
            
            # Process the request
            if thread_id:
                # Continue existing conversation
                response = await self._continue_conversation(temp_config, thread_id, message)
            else:
                # Start new conversation
                response = await self._start_new_conversation(temp_config, message)
            
            # Update statistics
            processing_time = (datetime.now() - start_time).total_seconds()
            self._update_stats(True, processing_time)
            
            self.logger.info(f"AAAIM: Request processed successfully in {processing_time:.2f}s")
            return response
            
        except Exception as e:
            error_msg = f"Agent request processing failed: {e}"
            self.logger.error(error_msg)
            self.error_manager.log_error_with_generation("AAAIM", "UnknownClass", "UnknownFunction", error_msg)
            self._update_stats(False, 0)
            
            return AgentResponse(
                success=False,
                error=error_msg,
                timestamp=datetime.now().isoformat()
            )
    
    async def _start_new_conversation(self, config: AgentConfig, message: str) -> AgentResponse:
        """Start a new conversation with the agent."""
        try:
            # Create a new thread
            thread_id = await self._create_thread(config)
            if not thread_id:
                raise Exception("Failed to create thread")
            
            # Send the initial message
            message_id = await self._send_message(config, thread_id, message)
            if not message_id:
                raise Exception("Failed to send message (no message_id returned)")
            
            # Run the agent
            run_id = await self._run_agent(config, thread_id)
            if not run_id:
                raise Exception("Failed to run agent")
            
            # Wait for completion and get response
            response = await self._get_response(config, thread_id, run_id)
            
            # Track conversation
            self.active_conversations[thread_id] = {
                "agent_id": config.agent_id,
                "created_at": datetime.now().isoformat(),
                "message_count": 1
            }
            self.stats["active_conversations"] += 1
            
            return AgentResponse(
                success=True,
                response=response,
                thread_id=thread_id,
                run_id=run_id,
                timestamp=datetime.now().isoformat()
            )
            
        except Exception as e:
            raise Exception(f"Failed to start new conversation: {e}")
    
    async def _continue_conversation(self, config: AgentConfig, thread_id: str, message: str) -> AgentResponse:
        """Continue an existing conversation."""
        try:
            # Send the message
            message_id = await self._send_message(config, thread_id, message)
            if not message_id:
                raise Exception("Failed to send message")
            
            # Run the agent
            run_id = await self._run_agent(config, thread_id)
            if not run_id:
                raise Exception("Failed to run agent")
            
            # Wait for completion and get response
            response = await self._get_response(config, thread_id, run_id)
            
            # Update conversation tracking
            if thread_id in self.active_conversations:
                self.active_conversations[thread_id]["message_count"] += 1
            
            return AgentResponse(
                success=True,
                response=response,
                thread_id=thread_id,
                run_id=run_id,
                timestamp=datetime.now().isoformat()
            )
            
        except Exception as e:
            raise Exception(f"Failed to continue conversation: {e}")
    
    async def _create_thread(self, config: AgentConfig) -> Optional[str]:
        """Create a new thread."""
        try:
            headers = {
                "Authorization": f"Bearer {config.api_key}",
                "Content-Type": "application/json",
                "OpenAI-Beta": "assistants=v2"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.threads_url,
                    headers=headers,
                    json={}
                ) as response:
                    if response.status in [200, 201]:  # v2 API returns 200, v1 returned 201
                        data = await response.json()
                        thread_id = data.get("id")
                        self.logger.info(f"Thread created successfully: {thread_id}")
                        return thread_id
                    else:
                        error_text = await response.text()
                        self.logger.error(f"Thread creation failed with status {response.status}: {error_text}")
                        raise Exception(f"Thread creation failed: {error_text}")
                        
        except Exception as e:
            self.logger.error(f"Thread creation error: {e}")
            self.log_error(str(e), "AgenticAPIActivationModule", "_create_thread")
            return None
    
    async def _send_message(self, config: AgentConfig, thread_id: str, message: str) -> Optional[str]:
        try:
            print("DEBUG: Entered _send_message")
            url = f"{self.messages_url}/{thread_id}/messages"
            headers = {
                "Authorization": f"Bearer {config.api_key}",
                "Content-Type": "application/json",
                "OpenAI-Beta": "assistants=v2"
            }
            payload = {
                "role": "user",
                "content": message
            }
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=config.timeout)) as response:
                    if response.status in (200, 201):
                        data = await response.json()
                        print(f"DEBUG: AAAIM _send_message response type: {type(data)}")
                        print(f"DEBUG: AAAIM _send_message response keys: {list(data.keys())}")
                        print(f"DEBUG: AAAIM _send_message response data: {json.dumps(data, indent=2)}")
                        message_id = data.get("id")
                        print(f"DEBUG: AAAIM _send_message extracted message_id: {message_id}")
                        if message_id:
                            self.logger.info(f"Successfully sent message with ID: {message_id}")
                            return message_id
                        else:
                            raise Exception("API response missing message ID")
                    else:
                        error_text = await response.text()
                        raise Exception(f"Failed to send message: {error_text}")
        except Exception as e:
            self.logger.error(f"Send message error: {e}")
            await self.handle_exception(e, "AgenticAPIActivationModule", "_send_message", {"thread_id": thread_id})
            return None
    
    async def _run_agent(self, config: AgentConfig, thread_id: str) -> Optional[str]:
        """Run the agent on the thread."""
        try:
            url = f"{self.runs_url}/{thread_id}/runs"
            headers = {
                "Authorization": f"Bearer {config.api_key}",
                "Content-Type": "application/json",
                "OpenAI-Beta": "assistants=v2"
            }
            payload = {
                "assistant_id": config.agent_id
            }
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=config.timeout)) as response:
                    if response.status in (200, 201):
                        data = await response.json()
                        run_id = data.get("id")
                        status = data.get("status", "")
                        if run_id:
                            self.logger.info(f"Successfully created agent run with ID: {run_id}, status: {status}")
                            return run_id
                        else:
                            raise Exception("API response missing run ID")
                    else:
                        error_text = await response.text()
                        raise Exception(f"Failed to run agent: {error_text}")
        except Exception as e:
            self.logger.error(f"Run agent error: {e}")
            await self.handle_exception(e, "AgenticAPIActivationModule", "_run_agent", {"thread_id": thread_id})
            return None
    
    async def _get_response(self, config: AgentConfig, thread_id: str, run_id: str) -> Optional[str]:
        """Get the response from the agent."""
        try:
            headers = {
                "Authorization": f"Bearer {config.api_key}",
                "Content-Type": "application/json",
                "OpenAI-Beta": "assistants=v2"
            }
            
            # Wait for run to complete
            for _ in range(config.max_retries):
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"{self.runs_url}/{thread_id}/runs/{run_id}",
                        headers=headers
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            status = data.get("status")
                            
                            if status == "completed":
                                # Get the messages
                                async with session.get(
                                    f"{self.messages_url}/{thread_id}/messages",
                                    headers=headers
                                ) as msg_response:
                                    if msg_response.status == 200:
                                        messages_data = await msg_response.json()
                                        messages = messages_data.get("data", [])
                                        
                                        # Find the assistant's response
                                        for message in messages:
                                            if message.get("role") == "assistant":
                                                content = message.get("content", [])
                                                if content and len(content) > 0:
                                                    return content[0].get("text", {}).get("value", "")
                                
                                break
                            elif status in ["failed", "cancelled", "expired"]:
                                raise Exception(f"Run failed with status: {status}")
                            else:
                                # Still running, wait and retry
                                await asyncio.sleep(1)
                        else:
                            error_text = await response.text()
                            raise Exception(f"Run status check failed: {error_text}")
            
            raise Exception("Run did not complete within expected time")
            
        except Exception as e:
            self.logger.error(f"Response retrieval error: {e}")
            self.log_error(str(e), "AgenticAPIActivationModule", "_get_response")
            return None
    
    def _update_stats(self, success: bool, processing_time: float):
        """Update statistics."""
        if success:
            self.stats["successful_requests"] += 1
            # Update average response time
            total_successful = self.stats["successful_requests"]
            current_avg = self.stats["average_response_time"]
            self.stats["average_response_time"] = (current_avg * (total_successful - 1) + processing_time) / total_successful
        else:
            self.stats["failed_requests"] += 1
    
    def get_conversation_status(self, thread_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific conversation."""
        if thread_id in self.active_conversations:
            return self.active_conversations[thread_id]
        return None
    
    def get_module_status(self) -> Dict[str, Any]:
        """Get AAAIM module status."""
        return {
            "module": "AAAIM",
            "status": "active",
            "current_agent_id": self.current_config.agent_id,
            "active_conversations": len(self.active_conversations),
            "stats": self.stats.copy(),
            "last_activity": self.stats["last_activity"]
        }
    
    def cleanup_conversation(self, thread_id: str) -> bool:
        """Clean up a conversation."""
        if thread_id in self.active_conversations:
            del self.active_conversations[thread_id]
            self.stats["active_conversations"] -= 1
            self.logger.info(f"AAAIM: Cleaned up conversation {thread_id}")
            return True
        return False
    
    def get_config(self) -> Dict[str, Any]:
        """Get current configuration."""
        return asdict(self.current_config)
    
    def log_error(self, error_message: str, class_name: str = "UnknownClass", function_name: str = "UnknownFunction", sub_function: str = "001"):
        """Log an error using EMM."""
        return self.error_manager.log_error_with_generation(
            "AAAIM", 
            class_name, 
            function_name, 
            error_message, 
            sub_function
        )
    
    def generate_error_code(self, class_name: str = "UnknownClass", function_name: str = "UnknownFunction", sub_function: str = "001") -> str:
        """Generate an error code using EMM."""
        return self.error_manager.generate_error_code("AAAIM", class_name, function_name, sub_function)
    
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
                "AAAIM",
                "AAAIM",
                "handle_api_error",
                f"API Error: {result.get('api_error_type', 'unknown')}",
                context=result
            )
            
            # Send report to CCU
            await api_error_handler.send_error_report_to_ccu(result)
            
            return result
            
        except Exception as e:
            self.error_manager.log_error_with_generation(
                "AAAIM",
                "AAAIM",
                "handle_api_error",
                f"Error handling API error: {str(e)}"
            )
            return {"success": False, "error": str(e)}


# Global instance and alias for compatibility
aaaim = AgenticAPIActivationModule()
AAAIM = AgenticAPIActivationModule  # Class alias 