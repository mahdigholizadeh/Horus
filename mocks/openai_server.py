#!/usr/bin/env python3
"""
OpenAI Mock Server - Standalone
Simulates OpenAI API endpoints that RCM can connect to.
Can be run independently of the main test suite.
"""

import asyncio
import logging
import json
import uuid
import time
import os
import glob
import random
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import uvicorn
import argparse

logger = logging.getLogger("OpenAIMockServer")
# Try to import OpenAI client for real API integration
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI package not available - real API integration disabled")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


@dataclass
class MockAPIRequest:
    """Represents an API request to the mock OpenAI server."""
    id: str
    endpoint: str
    method: str
    payload: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    response_sent: bool = False
    processing_time: float = 0.0

@dataclass
class APIStats:
    """Statistics for the mock API server."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    avg_response_time: float = 0.0
    start_time: datetime = field(default_factory=datetime.now)

class OpenAIMockServer:
    """
    Standalone OpenAI API Mock Server that RCM can connect to.
    """
    
    def __init__(self, server_port: int = 8080, response_delay: float = 0.5, 
                 response_folder: str = "API_respond", validate_api_keys: bool = False,
                 use_real_openai: bool = False):
        self.server_port = server_port
        self.response_delay = response_delay  # Simulate API response time
        self.response_folder = response_folder
        self.validate_api_keys = validate_api_keys
        self.use_real_openai = use_real_openai
        
        # API Key Configuration
        self.valid_api_keys = self._load_valid_api_keys()
        self.real_openai_client = None
        
        self.requests: Dict[str, MockAPIRequest] = {}
        self.stats = APIStats()
        self.running = False
        self.loaded_responses: List[Dict[str, Any]] = []
        self.ofgssc_responses: List[Dict[str, Any]] = []
        self.standard_responses: List[Dict[str, Any]] = []
        
        # Initialize real OpenAI client if requested
        if self.use_real_openai:
            self._init_real_openai_client()
        
        # FastAPI app
        self.app = FastAPI(title="OpenAI Mock Server", version="1.0.0")
        
        # Security scheme for API key validation
        if self.validate_api_keys:
            self.security = HTTPBearer()
        
        self._setup_routes()
    
    def _load_valid_api_keys(self) -> Dict[str, str]:
        """Load valid API keys from environment variables"""
        api_keys = {}
        
        # Load OpenAI API key
        openai_key = os.environ.get('OPENAI_API_KEY')
        if openai_key:
            api_keys['openai'] = openai_key
            logger.info("[API_KEYS] Loaded OpenAI API key from environment")
        
        # Load Agentic API key  
        agentic_key = os.environ.get('AGENTIC_API_KEY')
        if agentic_key:
            api_keys['agentic'] = agentic_key
            logger.info("[API_KEYS] Loaded Agentic API key from environment")
        
        # For testing, also check test-specific environment variables
        test_openai_key = os.environ.get('OPENAI_API_KEY_TEST')
        if test_openai_key:
            api_keys['openai_test'] = test_openai_key
            logger.info("[API_KEYS] Loaded test OpenAI API key from environment")
        
        test_agentic_key = os.environ.get('AGENTIC_API_KEY_TEST')
        if test_agentic_key:
            api_keys['agentic_test'] = test_agentic_key
            logger.info("[API_KEYS] Loaded test Agentic API key from environment")
        
        if not api_keys:
            logger.warning("[API_KEYS] No API keys found in environment variables")
        
        return api_keys
    
    def _init_real_openai_client(self):
        """Initialize real OpenAI client"""
        if not OPENAI_AVAILABLE:
            logger.error("[REAL_API] OpenAI package not available - cannot use real API")
            return
        
        api_key = self.valid_api_keys.get('openai') or self.valid_api_keys.get('openai_test')
        if not api_key:
            logger.error("[REAL_API] No OpenAI API key available")
            return
        
        try:
            self.real_openai_client = openai.OpenAI(api_key=api_key)
            logger.info("[REAL_API] Real OpenAI client initialized successfully")
        except Exception as e:
            logger.error(f"[REAL_API] Failed to initialize OpenAI client: {e}")
    
    def validate_api_key(self, credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())) -> str:
        """Validate API key from Authorization header"""
        if not self.validate_api_keys:
            return "valid"  # Skip validation if disabled
        
        api_key = credentials.credentials
        
        # Check if the API key matches any of our valid keys
        for key_type, valid_key in self.valid_api_keys.items():
            if api_key == valid_key:
                logger.info(f"[AUTH] Valid API key authenticated: {key_type}")
                return key_type
        
        # Check for test API keys (simplified validation)
        test_keys = [
            "sk-test-api-key-for-testing",
            "test-api-key-123",
            "mock-api-key"
        ]
        
        if api_key in test_keys:
            logger.info(f"[AUTH] Test API key authenticated: {api_key[:20]}...")
            return "test"
        
        logger.warning(f"[AUTH] Invalid API key attempted: {api_key[:20]}...")
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )
    
    async def _forward_to_real_openai(self, request_data: dict, endpoint: str) -> dict:
        """Forward request to real OpenAI API"""
        if not self.real_openai_client:
            raise HTTPException(status_code=503, detail="Real OpenAI client not available")
        
        try:
            logger.info(f"[REAL_API] Forwarding request to OpenAI {endpoint}")
            
            if endpoint == "chat/completions":
                # Extract required parameters
                messages = request_data.get("messages", [])
                model = request_data.get("model", "gpt-3.5-turbo")
                max_tokens = request_data.get("max_tokens", 150)
                temperature = request_data.get("temperature", 0.7)
                
                # Call real OpenAI API
                response = await asyncio.to_thread(
                    self.real_openai_client.chat.completions.create,
                    model=model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature
                )
                
                # Convert to dict format expected by mock
                return {
                    "id": f"chatcmpl-{uuid.uuid4().hex[:29]}",
                    "object": "chat.completion",
                    "created": int(time.time()),
                    "model": model,
                    "choices": [
                        {
                            "index": 0,
                            "message": {
                                "role": "assistant",
                                "content": response.choices[0].message.content
                            },
                            "finish_reason": response.choices[0].finish_reason
                        }
                    ],
                    "usage": {
                        "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                        "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                        "total_tokens": response.usage.total_tokens if response.usage else 0
                    }
                }
            
        except Exception as e:
            logger.error(f"[REAL_API] Error forwarding to OpenAI: {e}")
            # Fall back to mock response
            return await self._generate_mock_response(request_data)
        
    def _setup_routes(self):
        """Set up FastAPI routes to simulate OpenAI API."""
        # Add CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        @self.app.get("/")
        async def root():
            return {
                "message": "OpenAI Mock Server", 
                "status": "running", 
                "requests_handled": len(self.requests),
                "api_version": "v1"
            }
        
        @self.app.get("/stats")
        async def get_stats():
            return {
                "stats": {
                    "total_requests": self.stats.total_requests,
                    "successful_requests": self.stats.successful_requests,
                    "failed_requests": self.stats.failed_requests,
                    "avg_response_time": self.stats.avg_response_time,
                    "start_time": self.stats.start_time.isoformat()
                },
                "recent_requests": len([r for r in self.requests.values() 
                                      if (datetime.now() - r.timestamp).seconds < 300])
            }
        
        # OpenAI Chat Completions endpoint
        @self.app.post("/v1/chat/completions")
        async def chat_completions(request_data: dict, authorization: Optional[str] = Header(None),
                                 auth_result: str = Depends(self.validate_api_key) if self.validate_api_keys else None):
            """Mock OpenAI Chat Completions API with real API key validation."""
            
            # If using real OpenAI API, forward the request
            if self.use_real_openai and self.real_openai_client:
                return await self._forward_to_real_openai(request_data, "chat/completions")
            
            # Otherwise use mock response
            return await self._handle_api_request("chat_completions", "POST", request_data, authorization, auth_result)
        
        # OpenAI Completions endpoint (legacy)
        @self.app.post("/v1/completions")
        async def completions(request_data: dict, authorization: Optional[str] = Header(None)):
            """Mock OpenAI Completions API."""
            return await self._handle_api_request("completions", "POST", request_data, authorization)
        
        # OpenAI Models endpoint
        @self.app.get("/v1/models")
        async def list_models(authorization: Optional[str] = Header(None)):
            """Mock OpenAI Models API."""
            return await self._handle_api_request("models", "GET", {}, authorization)
        
        # Generic API endpoint for other requests
        @self.app.post("/v1/{path:path}")
        async def generic_api(path: str, request_data: dict, authorization: Optional[str] = Header(None)):
            """Handle any other OpenAI API requests."""
            return await self._handle_api_request(path, "POST", request_data, authorization)
    
    async def _handle_api_request(self, endpoint: str, method: str, payload: Dict[str, Any], 
                                 authorization: Optional[str] = None) -> Dict[str, Any]:
        """Handle API requests with mock responses."""
        start_time = time.time()
        request_id = f"req_{uuid.uuid4().hex[:8]}"
        
        # Log the request
        logger.info(f"[API] {method} /{endpoint} - Request ID: {request_id}")
        
        # Store request
        api_request = MockAPIRequest(
            id=request_id,
            endpoint=endpoint,
            method=method,
            payload=payload
        )
        self.requests[request_id] = api_request
        self.stats.total_requests += 1
        
        try:
            # Validate API key (simple check)
            if not authorization or not authorization.startswith("Bearer "):
                raise HTTPException(status_code=401, detail="Invalid API key")
            
            # Simulate processing delay
            await asyncio.sleep(self.response_delay)
            
            # Generate mock response based on endpoint
            response = await self._generate_mock_response(endpoint, payload)
            
            # Mark as successful
            processing_time = time.time() - start_time
            api_request.response_sent = True
            api_request.processing_time = processing_time
            self.stats.successful_requests += 1
            
            # Update average response time
            if self.stats.successful_requests > 0:
                self.stats.avg_response_time = (
                    (self.stats.avg_response_time * (self.stats.successful_requests - 1) + processing_time) / 
                    self.stats.successful_requests
                )
            
            logger.info(f"[API] Request {request_id} completed in {processing_time:.3f}s")
            return response
            
        except HTTPException:
            raise
        except Exception as e:
            self.stats.failed_requests += 1
            logger.error(f"[API] Request {request_id} failed: {e}")
            raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    
    async def _generate_mock_response(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Generate appropriate mock responses for different endpoints."""
        
        # Try to get structured response if response files are loaded
        if self.loaded_responses:
            structured_response = self._get_structured_response(payload, endpoint)
            if structured_response:
                return structured_response
        
        # Fallback to original mock responses
        if endpoint == "chat_completions":
            # Mock chat completion response
            messages = payload.get("messages", [])
            last_message = messages[-1] if messages else {"role": "user", "content": "Hello"}
            
            return {
                "id": f"chatcmpl-{uuid.uuid4().hex}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": payload.get("model", "gpt-3.5-turbo"),
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": f"Mock response to: {last_message.get('content', 'No content')[:100]}... [This is a mock OpenAI API response for testing Horus system]"
                    },
                    "finish_reason": "stop"
                }],
                "usage": {
                    "prompt_tokens": len(str(payload).split()) * 2,
                    "completion_tokens": 50,
                    "total_tokens": len(str(payload).split()) * 2 + 50
                }
            }
            
        elif endpoint == "completions":
            # Mock completion response
            prompt = payload.get("prompt", "")
            
            return {
                "id": f"cmpl-{uuid.uuid4().hex}",
                "object": "text_completion",
                "created": int(time.time()),
                "model": payload.get("model", "text-davinci-003"),
                "choices": [{
                    "text": f"Mock completion for prompt: {prompt[:50]}... [Mock response]",
                    "index": 0,
                    "logprobs": None,
                    "finish_reason": "stop"
                }],
                "usage": {
                    "prompt_tokens": len(prompt.split()) if prompt else 10,
                    "completion_tokens": 25,
                    "total_tokens": len(prompt.split()) + 25 if prompt else 35
                }
            }
            
        elif endpoint == "models":
            # Mock models list
            return {
                "object": "list",
                "data": [
                    {
                        "id": "gpt-4",
                        "object": "model",
                        "created": 1687882411,
                        "owned_by": "openai"
                    },
                    {
                        "id": "gpt-3.5-turbo",
                        "object": "model", 
                        "created": 1677610602,
                        "owned_by": "openai"
                    },
                    {
                        "id": "text-davinci-003",
                        "object": "model",
                        "created": 1669599635,
                        "owned_by": "openai"
                    }
                ]
            }
            
        else:
            # Generic mock response
            return {
                "id": f"mock-{uuid.uuid4().hex}",
                "object": endpoint,
                "created": int(time.time()),
                "data": {
                    "message": f"Mock response for {endpoint}",
                    "original_payload": payload,
                    "mock_server": True
                }
            }
    
    def load_response_files(self) -> bool:
        """Load all JSON response files from the response folder."""
        try:
            if not os.path.exists(self.response_folder):
                logger.error(f"[ERROR] Response folder '{self.response_folder}' not found")
                return False
            
            json_files = glob.glob(os.path.join(self.response_folder, "*.json"))
            if not json_files:
                logger.error(f"[ERROR] No JSON files found in '{self.response_folder}'")
                return False
            
            logger.info(f"[LOAD] Loading {len(json_files)} response files from '{self.response_folder}'")
            
            loaded_count = 0
            ofgssc_count = 0
            standard_count = 0
            
            for json_file in sorted(json_files):
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        response_data = json.load(f)
                        self.loaded_responses.append(response_data)
                        
                        # Categorize responses
                        if response_data.get('type') == 'OFGSSC_computation':
                            self.ofgssc_responses.append(response_data)
                            ofgssc_count += 1
                        else:
                            self.standard_responses.append(response_data)
                            standard_count += 1
                            
                        loaded_count += 1
                except Exception as e:
                    logger.error(f"[ERROR] Failed to load {json_file}: {e}")
            
            logger.info(f"[LOAD] Successfully loaded {loaded_count} response files:")
            logger.info(f"[LOAD] - OFGSSC responses: {ofgssc_count}")
            logger.info(f"[LOAD] - Standard responses: {standard_count}")
            
            return loaded_count > 0
            
        except Exception as e:
            logger.error(f"[ERROR] Failed to load response files: {e}")
            return False
    
    def _get_structured_response(self, payload: Dict[str, Any], endpoint: str) -> Dict[str, Any]:
        """Get a structured response based on request content and available response files."""
        request_content = ""
        
        # Extract content from different API formats
        if endpoint == "chat_completions":
            messages = payload.get("messages", [])
            if messages:
                request_content = messages[-1].get("content", "")
        elif endpoint == "completions":
            request_content = payload.get("prompt", "")
        
        # Determine if this should be an OFGSSC response
        # Look for computational keywords or high priority indicators
        computational_keywords = [
            "carbon", "footprint", "emission", "energy", "efficiency", 
            "sustainability", "analysis", "calculation", "assessment",
            "impact", "optimization", "lifecycle", "environmental"
        ]
        
        requires_computation = any(keyword in request_content.lower() 
                                 for keyword in computational_keywords)
        
        # Select appropriate response pool
        if requires_computation and self.ofgssc_responses:
            response_pool = self.ofgssc_responses
            response_type = "OFGSSC"
        elif self.standard_responses:
            response_pool = self.standard_responses
            response_type = "standard"
        else:
            # Fallback to original mock response
            return None
        
        # Select a random response from the appropriate pool
        selected_response = random.choice(response_pool)
        
        logger.info(f"[RESPONSE] Using {response_type} response (ID: {selected_response.get('response_id', 'unknown')})")
        
        # Adapt the response to OpenAI API format
        if endpoint == "chat_completions":
            # Format as chat completion response
            content = self._format_response_content(selected_response, request_content)
            
            return {
                "id": f"chatcmpl-{uuid.uuid4().hex}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": payload.get("model", "gpt-3.5-turbo"),
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": content
                    },
                    "finish_reason": "stop"
                }],
                "usage": {
                    "prompt_tokens": len(request_content.split()) * 1.3,
                    "completion_tokens": len(content.split()) * 1.3,
                    "total_tokens": len(request_content.split()) * 1.3 + len(content.split()) * 1.3
                },
                "horus_metadata": {
                    "response_type": response_type,
                    "response_id": selected_response.get("response_id"),
                    "computation_module": selected_response.get("computation_module"),
                    "processing_time": selected_response.get("processing_time", 0)
                }
            }
            
        elif endpoint == "completions":
            # Format as completion response
            content = self._format_response_content(selected_response, request_content)
            
            return {
                "id": f"cmpl-{uuid.uuid4().hex}",
                "object": "text_completion",
                "created": int(time.time()),
                "model": payload.get("model", "text-davinci-003"),
                "choices": [{
                    "text": content,
                    "index": 0,
                    "logprobs": None,
                    "finish_reason": "stop"
                }],
                "usage": {
                    "prompt_tokens": len(request_content.split()) if request_content else 10,
                    "completion_tokens": len(content.split()),
                    "total_tokens": len(request_content.split()) + len(content.split()) if request_content else 10 + len(content.split())
                },
                "horus_metadata": {
                    "response_type": response_type,
                    "response_id": selected_response.get("response_id"),
                    "computation_module": selected_response.get("computation_module"),
                    "processing_time": selected_response.get("processing_time", 0)
                }
            }
        
        return None
    
    def _format_response_content(self, response_data: Dict[str, Any], request_content: str) -> str:
        """Format response data into readable content for the API response."""
        if response_data.get('type') == 'OFGSSC_computation':
            # Format OFGSSC computation response
            template = response_data.get('template', {})
            analysis_type = template.get('analysis_type', 'environmental_analysis')
            
            content = f"Based on your inquiry about {request_content[:100]}...\n\n"
            content += f"**Environmental Analysis Report**\n"
            content += f"Analysis Type: {analysis_type.replace('_', ' ').title()}\n"
            content += f"Methodology: {template.get('methodology', 'OFGSSC Standard')}\n\n"
            
            if 'results' in template:
                results = template['results']
                content += "**Key Findings:**\n"
                for key, value in results.items():
                    if isinstance(value, dict):
                        content += f"- {key.replace('_', ' ').title()}:\n"
                        for sub_key, sub_value in value.items():
                            content += f"  • {sub_key.replace('_', ' ').title()}: {sub_value}\n"
                    else:
                        content += f"- {key.replace('_', ' ').title()}: {value}\n"
            
            content += f"\n*This analysis was generated using OFGSSC computational methods.*"
            
        else:
            # Format standard response
            response_content = response_data.get('content', {})
            content_text = response_content.get('content', 'No content available')
            
            content = f"Regarding your question: {request_content[:100]}...\n\n"
            content += content_text
            
            if 'details' in response_content:
                details = response_content['details']
                if isinstance(details, dict):
                    content += "\n\n**Additional Information:**\n"
                    for key, value in details.items():
                        if isinstance(value, list):
                            content += f"- {key.replace('_', ' ').title()}:\n"
                            for item in value:
                                content += f"  • {item}\n"
                        else:
                            content += f"- {key.replace('_', ' ').title()}: {value}\n"
        
        return content
    
    async def start_server(self):
        """Start the mock OpenAI API server."""
        logger.info(f"[START] Starting OpenAI Mock Server on port {self.server_port}")
        self.running = True
        self.stats.start_time = datetime.now()
        
        config = uvicorn.Config(
            self.app,
            host="0.0.0.0",
            port=self.server_port,
            log_level="info"
        )
        server = uvicorn.Server(config)
        
        try:
            await server.serve()
        except Exception as e:
            logger.error(f"[ERROR] Server failed: {e}")
            self.running = False
    
    def stop_server(self):
        """Stop the mock OpenAI API server."""
        logger.info("[STOP] Stopping OpenAI Mock Server")
        self.running = False
    
    async def simulate_load(self, requests_per_minute: int = 60, duration_minutes: int = 5):
        """Simulate API load for testing."""
        logger.info(f"[LOAD] Simulating {requests_per_minute} requests/minute for {duration_minutes} minutes")
        
        total_requests = requests_per_minute * duration_minutes
        interval = 60.0 / requests_per_minute  # seconds between requests
        
        for i in range(total_requests):
            # This would be called by external clients in real scenario
            await asyncio.sleep(interval)
            if not self.running:
                break
                
        logger.info(f"[LOAD] Load simulation completed")

async def main():
    """Main entry point for standalone execution."""
    parser = argparse.ArgumentParser(description="OpenAI Mock Server")
    parser.add_argument("--port", type=int, default=8080, help="Server port (default: 8080)")
    parser.add_argument("--delay", type=float, default=0.5, help="Response delay in seconds (default: 0.5)")
    parser.add_argument("--response-folder", default="API_respond", help="Folder containing response JSON files")
    parser.add_argument("--load-responses", action="store_true", help="Load structured responses from JSON files")
    parser.add_argument("--validate-api-keys", action="store_true", help="Enable API key validation")
    parser.add_argument("--use-real-openai", action="store_true", help="Forward requests to real OpenAI API")
    parser.add_argument("--load-test", action="store_true", help="Run load test simulation")
    parser.add_argument("--requests-per-minute", type=int, default=60, help="Requests per minute for load test")
    parser.add_argument("--duration", type=int, default=5, help="Load test duration in minutes")
    
    args = parser.parse_args()
    
    # Create and start server
    server = OpenAIMockServer(
        server_port=args.port,
        response_delay=args.delay,
        response_folder=args.response_folder,
        validate_api_keys=args.validate_api_keys,
        use_real_openai=args.use_real_openai
    )
    
    # Load response files if requested
    if args.load_responses:
        logger.info("[INIT] Loading structured response files...")
        if not server.load_response_files():
            logger.error("[ERROR] Failed to load response files. Using fallback responses.")
        else:
            logger.info("[INIT] Structured responses loaded successfully")
    
    if args.load_test:
        # Run load test
        logger.info(f"[MODE] Load test mode: {args.requests_per_minute} req/min for {args.duration} min")
        
        # Start server in background
        server_task = asyncio.create_task(server.start_server())
        await asyncio.sleep(2)  # Wait for server to start
        
        # Run load simulation
        load_task = asyncio.create_task(
            server.simulate_load(args.requests_per_minute, args.duration)
        )
        
        try:
            await asyncio.gather(server_task, load_task)
        except KeyboardInterrupt:
            logger.info("[STOP] Load test stopped by user")
    else:
        # Normal server mode
        logger.info("[MODE] Server mode - listening for OpenAI API requests")
        try:
            await server.start_server()
        except KeyboardInterrupt:
            logger.info("[STOP] Server stopped by user")

if __name__ == "__main__":
    asyncio.run(main()) 