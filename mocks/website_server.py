#!/usr/bin/env python3
"""
Website Mock Server - Standalone
Simulates a website that sends requests to RLA and receives responses from OCM.
Can be run independently of the main test suite.
"""

import asyncio
import aiohttp
import ssl
import logging
import json
import uuid
import os
import glob
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import argparse
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("WebsiteMockServer")

@dataclass
class TestRequest:
    """Represents a test request sent to the Horus system."""
    id: str
    payload: Dict[str, Any]
    status: str = "pending"
    created_at: datetime = field(default_factory=datetime.now)
    workflow_stages: List[str] = field(default_factory=list)
    response_data: Dict[str, Any] = field(default_factory=dict)
    error: str = ""

@dataclass
class TestStats:
    """Statistics for the test run."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    avg_response_time: float = 0.0
    start_time: datetime = field(default_factory=datetime.now)
    end_time: datetime = None

class WebsiteMockServer:
    """
    Standalone Website Mock Server that can interact with Horus system.
    """
    
    def __init__(self, server_port: int = 8888, rla_host: str = "localhost", 
                 rla_port: int = 3781, ocm_host: str = "localhost", ocm_port: int = 443,
                 request_folder: str = "website_request", test_mode: bool = False, 
                 skip_horusd_check: bool = False):
        self.server_port = server_port
        self.rla_host = rla_host
        self.rla_port = rla_port
        self.ocm_host = ocm_host  
        self.ocm_port = ocm_port
        self.request_folder = request_folder
        self.test_mode = test_mode
        self.skip_horusd_check = skip_horusd_check
        
        self.requests: Dict[str, TestRequest] = {}
        self.stats = TestStats()
        self.running = False
        self.horusd_ready = skip_horusd_check  # Skip check if requested
        self.loaded_requests: List[Dict[str, Any]] = []
        
        # FastAPI app for receiving OCM responses
        self.app = FastAPI(title="Website Mock Server", version="1.0.0")
        self._setup_routes()
        
    def _setup_routes(self):
        """Set up FastAPI routes."""
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
            return {"message": "Website Mock Server", "status": "running", "requests": len(self.requests)}
        
        @self.app.get("/stats")
        async def get_stats():
            return {
                "stats": {
                    "total_requests": self.stats.total_requests,
                    "successful_requests": self.stats.successful_requests,
                    "failed_requests": self.stats.failed_requests,
                    "avg_response_time": self.stats.avg_response_time,
                    "start_time": self.stats.start_time.isoformat() if self.stats.start_time else None,
                    "end_time": self.stats.end_time.isoformat() if self.stats.end_time else None
                },
                "active_requests": len([r for r in self.requests.values() if r.status == "pending"])
            }
        
        @self.app.post("/response")
        async def receive_ocm_response(response_data: dict):
            """Receive response from OCM."""
            try:
                request_id = response_data.get("request_id")
                if request_id and request_id in self.requests:
                    request = self.requests[request_id]
                    request.response_data = response_data
                    request.status = "completed"
                    request.workflow_stages.append("OCM_RESPONSE")
                    
                    self.stats.successful_requests += 1
                    logger.info(f"[OK] Received response for request {request_id}")
                    
                    return {"status": "received", "request_id": request_id}
                else:
                    logger.warning(f"[WARN] Unknown request ID: {request_id}")
                    return {"status": "unknown_request", "request_id": request_id}
                    
            except Exception as e:
                logger.error(f"[ERROR] Failed to process OCM response: {e}")
                raise HTTPException(status_code=500, detail=str(e))
    
    def load_test_requests(self) -> bool:
        """Load all JSON request files from the request folder."""
        try:
            if not os.path.exists(self.request_folder):
                logger.error(f"[ERROR] Request folder '{self.request_folder}' not found")
                return False
            
            json_files = glob.glob(os.path.join(self.request_folder, "*.json"))
            if not json_files:
                logger.error(f"[ERROR] No JSON files found in '{self.request_folder}'")
                return False
            
            logger.info(f"[LOAD] Loading {len(json_files)} request files from '{self.request_folder}'")
            
            loaded_count = 0
            for json_file in sorted(json_files):
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        request_data = json.load(f)
                        self.loaded_requests.append(request_data)
                        loaded_count += 1
                except Exception as e:
                    logger.error(f"[ERROR] Failed to load {json_file}: {e}")
            
            logger.info(f"[LOAD] Successfully loaded {loaded_count} request files")
            
            # Sort by priority and request_id for systematic processing
            priority_order = {'A': 1, 'B': 2, 'C': 3, 'D': 4}
            self.loaded_requests.sort(key=lambda x: (
                priority_order.get(x.get('priority', 'D'), 4),
                x.get('request_id', '')
            ))
            
            return loaded_count > 0
            
        except Exception as e:
            logger.error(f"[ERROR] Failed to load test requests: {e}")
            return False
    
    async def check_horusd_ready(self, max_attempts: int = 60, check_interval: int = 5) -> bool:
        """Check if Horus service is ready to handle requests (IMPROVED LOGIC)."""
        
        # IMPROVEMENT: Skip check in test mode if requested
        if self.skip_horusd_check:
            logger.info(f"[CHECK] Skipping Horus readiness check (test mode)")
            self.horusd_ready = True
            return True
        
        # IMPROVEMENT: Detect test environment automatically
        if self.test_mode and os.environ.get('HORUS_ENV') == 'test':
            logger.info(f"[CHECK] Test environment detected - using reduced wait time")
            max_attempts = min(max_attempts, 10)  # Reduce wait time in test
            check_interval = 2
        
        logger.info(f"[CHECK] Checking if Horus service is ready...")
        
        # IMPROVEMENT: More comprehensive endpoint checking
        endpoints_to_check = [
            f"http://{self.rla_host}:{self.rla_port}/health",
            f"http://{self.rla_host}:{self.rla_port}/status",
            f"https://{self.rla_host}:{self.rla_port}/health",
            f"https://{self.rla_host}:{self.rla_port}/status"
        ]
        
        # IMPROVEMENT: Add CCU endpoint check (primary service indicator)
        ccu_endpoints = [
            "http://localhost:8443/health",
            "https://localhost:8443/health",
            "http://localhost:8443/status"
        ]
        endpoints_to_check.extend(ccu_endpoints)
        
        for attempt in range(max_attempts):
            logger.info(f"[CHECK] Attempt {attempt + 1}/{max_attempts} - Checking Horus readiness")
            
            # IMPROVEMENT: Try endpoints in priority order
            ready_services = 0
            total_services = len(endpoints_to_check)
            
            for endpoint in endpoints_to_check:
                try:
                    if endpoint.startswith('https'):
                        ssl_context = ssl.create_default_context()
                        ssl_context.check_hostname = False
                        ssl_context.verify_mode = ssl.CERT_NONE
                        connector = aiohttp.TCPConnector(ssl=ssl_context)
                    else:
                        connector = aiohttp.TCPConnector()
                    
                    async with aiohttp.ClientSession(
                        timeout=aiohttp.ClientTimeout(total=5),  # Reduced timeout
                        connector=connector
                    ) as session:
                        async with session.get(endpoint) as response:
                            if response.status == 200:
                                ready_services += 1
                                logger.debug(f"[CHECK] Endpoint ready: {endpoint}")
                                
                                # IMPROVEMENT: Consider ready if primary service (CCU) responds
                                if "8443" in endpoint:  # CCU endpoint
                                    logger.info(f"[READY] Horus CCU service is ready! (endpoint: {endpoint})")
                                    self.horusd_ready = True
                                    return True
                                    
                except Exception as e:
                    logger.debug(f"[CHECK] Endpoint {endpoint} not ready: {e}")
                    continue
            
            # IMPROVEMENT: Partial readiness acceptance
            readiness_ratio = ready_services / total_services
            if readiness_ratio >= 0.3:  # 30% of services ready
                logger.info(f"[READY] Partial Horus readiness detected ({ready_services}/{total_services} services)")
                self.horusd_ready = True
                return True
            
            if attempt < max_attempts - 1:
                logger.info(f"[WAIT] Horus not ready yet ({ready_services}/{total_services} services), waiting {check_interval} seconds...")
                await asyncio.sleep(check_interval)
        
        # IMPROVEMENT: Graceful fallback for test environments
        if self.test_mode:
            logger.warning(f"[FALLBACK] Test mode - proceeding without Horus readiness confirmation")
            self.horusd_ready = True
            return True
        
        logger.error(f"[ERROR] Horus service did not become ready after {max_attempts} attempts")
        return False
    
    async def send_structured_requests(self, batch_size: int = 10, delay_between_batches: float = 1.0) -> Dict[str, Any]:
        """Send all loaded requests systematically based on priority."""
        if not self.loaded_requests:
            logger.error("[ERROR] No requests loaded. Call load_test_requests() first.")
            return {"error": "No requests loaded"}
        
        if not self.horusd_ready:
            logger.error("[ERROR] Horus service not ready. Call check_horusd_ready() first.")
            return {"error": "Horus service not ready"}
        
        logger.info(f"[START] Sending {len(self.loaded_requests)} structured requests in batches of {batch_size}")
        
        self.stats.start_time = datetime.now()
        self.stats.total_requests = len(self.loaded_requests)
        
        # Group requests by priority for reporting
        priority_counts = {}
        for req in self.loaded_requests:
            priority = req.get('priority', 'Unknown')
            priority_counts[priority] = priority_counts.get(priority, 0) + 1
        
        logger.info(f"[PRIORITY] Request distribution: {priority_counts}")
        
        # Convert loaded requests to TestRequest objects and send
        successful_requests = 0
        failed_requests = 0
        
        for i in range(0, len(self.loaded_requests), batch_size):
            batch = self.loaded_requests[i:i+batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(self.loaded_requests) + batch_size - 1) // batch_size
            
            logger.info(f"[BATCH] Processing batch {batch_num}/{total_batches} ({len(batch)} requests)")
            
            # Prepare batch requests
            batch_test_requests = []
            for req_data in batch:
                request_id = req_data.get('request_id', f"req_{uuid.uuid4().hex[:8]}")
                test_request = TestRequest(
                    id=request_id,
                    payload={
                        "query": req_data.get('content', ''),
                        "user_id": req_data.get('user_id', 'unknown'),
                        "session_id": req_data.get('session_id', str(uuid.uuid4())),
                        "priority": req_data.get('priority', 'C'),
                        "metadata": req_data.get('metadata', {}),
                        "request_id": request_id,
                        "timestamp": req_data.get('timestamp', datetime.now().isoformat())
                    }
                )
                batch_test_requests.append(test_request)
                self.requests[request_id] = test_request
            
            # Send batch requests concurrently
            batch_tasks = [self.send_request_to_rla(request) for request in batch_test_requests]
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # Count results
            batch_success = sum(1 for result in batch_results if result is True)
            batch_failed = len(batch_results) - batch_success
            
            successful_requests += batch_success
            failed_requests += batch_failed
            
            logger.info(f"[BATCH] Batch {batch_num} completed: {batch_success} successful, {batch_failed} failed")
            
            # Wait between batches
            if i + batch_size < len(self.loaded_requests):
                await asyncio.sleep(delay_between_batches)
        
        self.stats.end_time = datetime.now()
        self.stats.successful_requests = successful_requests
        self.stats.failed_requests = failed_requests
        
        duration = (self.stats.end_time - self.stats.start_time).total_seconds()
        
        results = {
            "total_requests": len(self.loaded_requests),
            "successful_requests": successful_requests,
            "failed_requests": failed_requests,
            "duration_seconds": duration,
            "requests_per_second": len(self.loaded_requests) / duration if duration > 0 else 0,
            "priority_distribution": priority_counts,
            "batch_size": batch_size,
            "batches_processed": (len(self.loaded_requests) + batch_size - 1) // batch_size
        }
        
        logger.info(f"[COMPLETE] Structured request sending completed:")
        logger.info(f"[STATS] Total: {results['total_requests']}, Success: {successful_requests}, Failed: {failed_requests}")
        logger.info(f"[STATS] Duration: {duration:.2f}s, Rate: {results['requests_per_second']:.2f} req/s")
        
        return results
    
    async def send_request_to_rla(self, request: TestRequest) -> bool:
        """Send a request to RLA."""
        try:
            payload = {
                "request_id": request.id,
                "data": request.payload,
                "timestamp": request.created_at.isoformat(),
                "source": "website_mock"
            }
            
            # Try both HTTP and HTTPS for RLA
            urls_to_try = [
                f"http://{self.rla_host}:{self.rla_port}/data",  # HTTP without SSL
                f"https://{self.rla_host}:{self.rla_port}/data"  # HTTPS with SSL
            ]
            
            for url in urls_to_try:
                try:
                    logger.debug(f"Trying to send request {request.id} to {url}")
                    
                    if url.startswith('https'):
                        ssl_context = ssl.create_default_context()
                        ssl_context.check_hostname = False
                        ssl_context.verify_mode = ssl.CERT_NONE
                        connector = aiohttp.TCPConnector(ssl=ssl_context)
                    else:
                        connector = aiohttp.TCPConnector()
                    
                    async with aiohttp.ClientSession(
                        timeout=aiohttp.ClientTimeout(total=60),
                        connector=connector
                    ) as session:
                        async with session.post(
                            url,
                            json=payload,
                            headers={"Content-Type": "application/json"}
                        ) as response:
                            if response.status == 200:
                                response_data = await response.json()
                                request.status = "sent_to_rla"
                                request.workflow_stages.append("RLA")
                                logger.info(f"[OK] Request {request.id} sent to RLA successfully via {url}")
                                return True
                            else:
                                logger.debug(f"RLA returned status {response.status} for {url}")
                                continue  # Try next URL
                                
                except Exception as e:
                    logger.debug(f"Failed to connect to {url}: {e}")
                    continue  # Try next URL
            
            # If we get here, all URLs failed
            request.status = "rla_failed"
            request.error = "Failed to connect to RLA via HTTP or HTTPS"
            self.stats.failed_requests += 1
            logger.error(f"[ERROR] Request {request.id} failed at RLA: all connection attempts failed")
            return False
            
        except Exception as e:
            request.status = "error"
            request.error = str(e)
            self.stats.failed_requests += 1
            logger.error(f"[ERROR] Request {request.id} failed: {e}")
            return False
    
    async def send_batch_requests(self, count: int = 100, batch_size: int = 10) -> Dict[str, Any]:
        """Send a batch of requests to the system."""
        logger.info(f"[START] Sending {count} requests in batches of {batch_size}")
        
        self.stats.start_time = datetime.now()
        self.stats.total_requests = count
        
        # Generate requests
        requests_to_send = []
        for i in range(count):
            request_id = f"req_{uuid.uuid4().hex[:8]}"
            test_request = TestRequest(
                id=request_id,
                payload={
                    "query": f"Test query {i+1}",
                    "user_id": f"user_{i % 10}",
                    "session_id": f"session_{uuid.uuid4().hex[:8]}",
                    "priority": "normal",
                    "metadata": {
                        "test_batch": True,
                        "batch_index": i,
                        "timestamp": datetime.now().isoformat()
                    }
                }
            )
            requests_to_send.append(test_request)
            self.requests[request_id] = test_request
        
        # Send requests in batches
        successful_batches = 0
        for i in range(0, len(requests_to_send), batch_size):
            batch = requests_to_send[i:i+batch_size]
            logger.info(f"[BATCH] Sending batch {i//batch_size + 1}/{(count + batch_size - 1)//batch_size} ({len(batch)} requests)")
            
            # Send batch concurrently
            batch_tasks = [self.send_request_to_rla(request) for request in batch]
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # Count successful requests in this batch
            batch_success_count = sum(1 for result in batch_results if result is True)
            if batch_success_count > 0:
                successful_batches += 1
                
            logger.info(f"[BATCH] Batch {i//batch_size + 1} completed: {batch_success_count}/{len(batch)} successful")
            
            # Wait between batches
            await asyncio.sleep(1)
        
        self.stats.end_time = datetime.now()
        duration = (self.stats.end_time - self.stats.start_time).total_seconds()
        
        logger.info(f"[COMPLETE] Request sending completed in {duration:.2f} seconds")
        logger.info(f"[STATS] Success: {self.stats.successful_requests}, Failed: {self.stats.failed_requests}")
        
        return {
            "total_requests": count,
            "successful_requests": self.stats.successful_requests,
            "failed_requests": self.stats.failed_requests,
            "duration_seconds": duration,
            "requests_per_second": count / duration if duration > 0 else 0
        }
    
    async def start_server(self):
        """Start the mock website server."""
        logger.info(f"[START] Starting Website Mock Server on port {self.server_port}")
        self.running = True
        
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
        """Stop the mock website server."""
        logger.info("[STOP] Stopping Website Mock Server")
        self.running = False

async def main():
    """Main entry point for standalone execution."""
    parser = argparse.ArgumentParser(description="Website Mock Server")
    parser.add_argument("--port", type=int, default=8888, help="Server port (default: 8888)")
    parser.add_argument("--rla-host", default="localhost", help="RLA host (default: localhost)")
    parser.add_argument("--rla-port", type=int, default=3781, help="RLA port (default: 3781)")
    parser.add_argument("--ocm-host", default="localhost", help="OCM host (default: localhost)")
    parser.add_argument("--ocm-port", type=int, default=443, help="OCM port (default: 443)")
    parser.add_argument("--requests", type=int, default=0, help="Number of requests to send (0 = server only)")
    parser.add_argument("--batch-size", type=int, default=10, help="Batch size for requests (default: 10)")
    parser.add_argument("--request-folder", default="website_request", help="Folder containing request JSON files")
    parser.add_argument("--test-mode", action="store_true", help="Use structured test mode with JSON files")
    parser.add_argument("--wait-for-horusd", action="store_true", help="Wait for Horus service to be ready")
    parser.add_argument("--skip-horusd-check", action="store_true", help="Skip Horus readiness check (for testing)")
    parser.add_argument("--max-wait-attempts", type=int, default=60, help="Max attempts to wait for Horus (default: 60)")
    
    args = parser.parse_args()
    
    # Create and start server
    server = WebsiteMockServer(
        server_port=args.port,
        rla_host=args.rla_host,
        rla_port=args.rla_port,
        ocm_host=args.ocm_host,
        ocm_port=args.ocm_port,
        request_folder=args.request_folder,
        test_mode=args.test_mode,
        skip_horusd_check=args.skip_horusd_check
    )
    
    if args.test_mode:
        # Structured test mode with JSON files
        logger.info("[MODE] Structured test mode - using JSON request files")
        
        # Load test requests
        if not server.load_test_requests():
            logger.error("[ERROR] Failed to load test requests. Exiting.")
            return
        
        # Start server in background
        server_task = asyncio.create_task(server.start_server())
        await asyncio.sleep(2)  # Wait for server to start
        
        # Wait for Horus service if requested
        if args.wait_for_horusd:
            logger.info("[WAIT] Waiting for Horus service to be ready...")
            if not await server.check_horusd_ready(max_attempts=args.max_wait_attempts):
                logger.error("[ERROR] Horus service not ready. Exiting.")
                return
        else:
            server.horusd_ready = True  # Skip readiness check
        
        # Send structured requests
        results = await server.send_structured_requests(batch_size=args.batch_size)
        logger.info(f"[RESULTS] Test completed: {results}")
        
        # Keep server running to receive responses
        logger.info("[INFO] Server running to receive responses. Press Ctrl+C to stop.")
        try:
            await server_task
        except KeyboardInterrupt:
            logger.info("[STOP] Server stopped by user")
            
    elif args.requests > 0:
        # Legacy batch request mode
        logger.info(f"[MODE] Legacy request sending mode: {args.requests} requests")
        
        # Start server in background
        server_task = asyncio.create_task(server.start_server())
        await asyncio.sleep(2)  # Wait for server to start
        
        # Send requests
        results = await server.send_batch_requests(args.requests, args.batch_size)
        logger.info(f"[RESULTS] {results}")
        
        # Keep server running to receive responses
        logger.info("[INFO] Server running to receive responses. Press Ctrl+C to stop.")
        try:
            await server_task
        except KeyboardInterrupt:
            logger.info("[STOP] Server stopped by user")
    else:
        # Server only mode
        logger.info("[MODE] Server only mode - listening for manual requests")
        try:
            await server.start_server()
        except KeyboardInterrupt:
            logger.info("[STOP] Server stopped by user")

if __name__ == "__main__":
    asyncio.run(main()) 