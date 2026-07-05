"""
TD Interaction Module (TDIM) for CCU

This module handles all communication and coordination with the TD (Task Divider) microservice.
The TD service has been refactored to a sophisticated routing and orchestration engine with
14-module architecture for multi-calculation coordination.

Key Features:
- Binary file processing coordination from JFA output
- Multi-calculation orchestration monitoring
- Real-time orchestration status tracking
- Concurrent calculation management
- Result aggregation coordination
- OCM integration preparation
- Health monitoring and performance tracking
- WebSocket communication for real-time updates

The TDIM serves as the bridge between CCU's orchestration logic and TD's 
routing engine for complex calculation workflows.
"""

import asyncio
import logging
import json
import sys
import websockets
import aiohttp
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import uuid
import os
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum

# Add utils path for WebSocketPortManager  
utils_path = Path(__file__).parent.parent / "utils"
sys.path.insert(0, str(utils_path))

try:
    from websocket_port_manager import WebSocketPortManager
except ImportError as e:
    print(f"Failed to import WebSocketPortManager: {e}")
    print(f"Utils path: {utils_path}")
    print(f"Utils path exists: {utils_path.exists()}")
    raise

class OrchestrationStatus(Enum):
    """Enumeration for orchestration status."""
    PENDING = "pending"
    PLANNING = "planning"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TDServiceStatus:
    """TD service status information."""
    service: str
    is_active: bool
    total_processed: int
    successful_processing: int
    failed_processing: int
    binary_files_processed: int
    calculations_orchestrated: int
    results_aggregated: int
    active_orchestrations: int
    orchestration_success_rate: float
    calculation_effectiveness: float
    average_processing_time: float
    modules: Dict[str, Any]
    last_update: datetime


@dataclass
class OrchestrationInfo:
    """Orchestration information tracking."""
    orchestration_id: str
    request_id: str
    status: OrchestrationStatus
    total_calculations: int
    active_calculations: List[str]
    completed_calculations: List[str]
    failed_calculations: List[str]
    start_time: datetime
    estimated_completion: Optional[datetime]
    processing_time: Optional[float]
    binary_file_path: str
    orchestration_plan: Dict[str, Any]


class TDInteractionModule:
    """
    TD Interaction Module for CCU
    
    Manages all interactions with the TD (Task Divider) microservice.
    Handles binary file processing, orchestration coordination, and result aggregation.
    """
    
    def __init__(self, ccu_config: Dict[str, Any] = None):
        """Initialize the TDIM module."""
        self.logger = logging.getLogger(__name__)
        self.module_name = "TDIM"
        self.is_active = False
        
        # Use WebSocket port manager from CCU config (shared instance)
        self.port_manager = ccu_config.get('websocket_port_manager') if ccu_config else None
        if not self.port_manager:
            # Fallback to creating new instance if not provided
            self.port_manager = WebSocketPortManager()
            self.logger.warning("No WebSocket port manager provided, creating new instance")
        
        # NEW ARCHITECTURE: WebSocket SERVER configuration
        self.websocket_server = None
        self.websocket_server_port = None
        self.connected_clients = {}  # Track TD ECM connections
        self.max_clients = 1  # Only one TD ECM should connect
        
        # Load TD configuration from CCU (includes PMM paths and network config)
        td_setting = ccu_config.get('td_setting', {}) if ccu_config else {}
        
        # TD service configuration (with PMM-provided defaults)
        self.td_config = {
            "service_name": "TD",
            "host": td_setting.get("network", {}).get("host", "localhost"),
            "api_port": td_setting.get("network", {}).get("api_port", 8003),
            "health_port": td_setting.get("network", {}).get("health_port", 9093),
            "websocket_port": td_setting.get("network", {}).get("websocket_port", 11492),
            "timeout": td_setting.get("routing", {}).get("calculation_timeout", 300),  # 5 minutes for orchestration
            "max_retries": td_setting.get("error_handling", {}).get("retry_attempts", 3),
            "retry_delay": td_setting.get("routing", {}).get("retry_delay", 10),
            "max_concurrent_orchestrations": td_setting.get("routing", {}).get("max_concurrent_calculations", 5)
        }
        
        # Connection management
        self.connections = {
            "http_session": None,
            "websocket": None,
            "health_check_interval": 30,
            "connection_timeout": 10
        }
        
        # Service status tracking
        self.service_status = {
            "is_healthy": False,
            "last_health_check": None,
            "last_successful_request": None,
            "consecutive_failures": 0,
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "orchestrations_completed": 0,
            "orchestrations_failed": 0,
            "last_orchestration_time": None
        }
        
        # Orchestration capabilities
        self.orchestration_capabilities = {
            "supported_routes": ["forward", "parallel", "sequential"],
            "max_concurrent_calculations": 12,
            "max_binary_file_size": 50 * 1024 * 1024,  # 50MB
            "binary_formats": ["jfa_v1", "jfa_v2", "legacy"],
            "orchestration_patterns": ["sequential", "parallel", "dependency_based", "resource_optimized"],
            "result_aggregation": True,
            "cross_calculation_analysis": True,
            "ocm_integration": True
        }
        
        # Active orchestrations tracking
        self.active_orchestrations = {}
        self.orchestration_history = []
        
        # Performance metrics
        self.performance_metrics = {
            "orchestration_response_times": [],
            "calculation_success_rates": {},
            "resource_utilization": {},
            "throughput_metrics": {
                "binary_files_per_hour": 0,
                "orchestrations_per_hour": 0,
                "calculations_per_hour": 0
            }
        }
        
        # Module health tracking
        self.module_health = {
            "BFPM": {"healthy": True, "last_check": None},
            "AFM": {"healthy": True, "last_check": None},
            "ROM": {"healthy": True, "last_check": None},
            "CAM": {"healthy": True, "last_check": None},
            "CIM": {"healthy": True, "last_check": None},
            "RMM": {"healthy": True, "last_check": None},
            "CCM": {"healthy": True, "last_check": None},
            "OCMIM": {"healthy": True, "last_check": None}
        }
        
        self.logger.info(f"{self.module_name} initialized for enhanced TD orchestration integration")
    
    async def start(self):
        """Start the TDIM module."""
        try:
            self.is_active = True
            
            
            # Start WebSocket server for ECM connections
            await self.start_websocket_server()
            # Initialize HTTP session
            self.connections["http_session"] = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.td_config["timeout"])
            )
            
            # Start health monitoring
            asyncio.create_task(self._monitor_td_health())
            
            # Start WebSocket connection
            asyncio.create_task(self._maintain_websocket_connection())
            
            # Start orchestration monitoring
            asyncio.create_task(self._monitor_orchestrations())
            
            # Start performance monitoring
            asyncio.create_task(self._monitor_performance())
            
            self.logger.info(f"{self.module_name} started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start {self.module_name}: {e}")
            raise
    async def start_websocket_server(self):
        """Start WebSocket server for TD ECM connections."""
        try:
            self.logger.info("Starting TDIM WebSocket server...")
            
            # Start WebSocket server using port manager
            self.websocket_server = await self.port_manager.start_ccu_websocket_server(
                "TDIM", 
                self.handle_td_connection
            )
            
            if not self.websocket_server:
                raise Exception("Failed to start WebSocket server - no available ports")
            
            # Get the allocated port
            self.websocket_server_port = self.port_manager.allocated_ports.get("TDIM")
            
            self.logger.info(f"✅ TDIM WebSocket server started on port {self.websocket_server_port}")
            self.logger.info(f"🔗 TD ECM should connect to: ws://localhost:{self.websocket_server_port}/ws")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to start TDIM WebSocket server: {e}")
            raise
    
    async def handle_td_connection(self, websocket, path):
        """Handle incoming TD ECM WebSocket connection."""
        client_id = None
        try:
            client_id = f"TD_ECM_{id(websocket)}"
            client_address = websocket.remote_address
            self.logger.info(f"🔗 TD ECM connected from {client_address} (ID: {client_id})")
            
            # Check if we already have max connections
            if len(self.connected_clients) >= self.max_clients:
                self.logger.warning(f"⚠️ Maximum TD connections ({self.max_clients}) reached, rejecting new connection")
                await websocket.close(code=1008, reason="Maximum connections reached")
                return
            
            # Add client to connected clients
            self.connected_clients[client_id] = {
                "websocket": websocket,
                "connected_at": datetime.now(),
                "last_heartbeat": datetime.now(),
                "client_address": client_address
            }
            
            self.logger.info(f"✅ TD ECM client registered (Total clients: {len(self.connected_clients)})")
            
            # Send welcome message
            welcome_msg = {
                "type": "welcome",
                "client_id": client_id,
                "server": "TDIM",
                "timestamp": datetime.now().isoformat(),
                "message": "Connected to CCU TDIM WebSocket server"
            }
            await websocket.send(json.dumps(welcome_msg))
            
            # Listen for messages from this TD ECM client
            await self.handle_client_messages(websocket, client_id)
            
        except Exception as e:
            self.logger.error(f"❌ Error handling TD connection: {e}")
        finally:
            # Clean up client connection
            if client_id and client_id in self.connected_clients:
                del self.connected_clients[client_id]
                self.logger.info(f"🔌 TD ECM client {client_id} disconnected")
    
    async def handle_client_messages(self, websocket, client_id: str):
        """Listen for messages from a specific TD ECM client."""
        try:
            async for message in websocket:
                self.logger.debug(f"Received message from TD ECM {client_id}: {message}")
                
                # Update heartbeat
                if client_id in self.connected_clients:
                    self.connected_clients[client_id]["last_heartbeat"] = datetime.now()
                
                try:
                    data = json.loads(message)
                    # Process message
                    await self.handle_td_message(data, client_id)
                except json.JSONDecodeError as e:
                    self.logger.error(f"Invalid JSON message from TD client {client_id}: {e}")
                    error_response = {
                        "type": "error",
                        "error": "invalid_json",
                        "message": str(e),
                        "timestamp": datetime.now().isoformat()
                    }
                    await websocket.send(json.dumps(error_response))
                
        except Exception as e:
            self.logger.error(f"Error handling messages from TD ECM {client_id}: {e}")
    
    async def handle_td_message(self, data: Dict[str, Any], client_id: str):
        """Handle a message from TD ECM."""
        try:
            message_type = data.get("type", "unknown")
            
            self.logger.debug(f"Processing {message_type} message from TD ECM {client_id}")
            
            # Handle different message types
            if message_type == "heartbeat":
                await self._handle_td_heartbeat(data, client_id)
            elif message_type == "status_update":
                await self._handle_td_status_update(data)
            elif message_type == "orchestration_result":
                await self._handle_orchestration_result(data)
            elif message_type == "binary_processing_result":
                await self._handle_binary_processing_result(data)
            elif message_type == "calculation_status":
                await self._handle_calculation_status(data)
            elif message_type == "health_report":
                await self._handle_td_health_report(data)
            elif message_type == "error_report":
                await self._handle_td_error_report(data)
            else:
                self.logger.warning(f"Unknown message type '{message_type}' from TD ECM {client_id}")
                
        except Exception as e:
            self.logger.error(f"Error processing message from TD ECM {client_id}: {e}")
    
    async def _handle_td_heartbeat(self, data: Dict[str, Any], client_id: str):
        """Handle heartbeat from TD ECM."""
        response = {
            "type": "heartbeat_response",
            "timestamp": datetime.now().isoformat(),
            "server": "TDIM",
            "client_id": client_id
        }
        
        if client_id in self.connected_clients:
            try:
                await self.connected_clients[client_id]["websocket"].send(json.dumps(response))
            except Exception as e:
                self.logger.error(f"Failed to send heartbeat response to {client_id}: {e}")
    
    async def _handle_td_status_update(self, data: Dict[str, Any]):
        """Handle status update from TD service."""
        try:
            status = data.get("status", {})
            self.service_status["is_healthy"] = status.get("is_active", False)
            self.service_status["last_health_check"] = datetime.now()
            self.logger.debug(f"Received TD status update: {status}")
        except Exception as e:
            self.logger.error(f"Error handling TD status update: {e}")
    
    async def _handle_orchestration_result(self, data: Dict[str, Any]):
        """Handle orchestration result from TD service."""
        try:
            orchestration_id = data.get("orchestration_id")
            if orchestration_id in self.active_orchestrations:
                self.active_orchestrations[orchestration_id].status = OrchestrationStatus.COMPLETED
                self.logger.info(f"TD orchestration {orchestration_id} completed")
        except Exception as e:
            self.logger.error(f"Error handling orchestration result: {e}")
    
    async def _handle_binary_processing_result(self, data: Dict[str, Any]):
        """Handle binary processing result from TD service."""
        try:
            result_info = data.get("result", {})
            self.logger.info(f"TD binary processing result: {result_info}")
        except Exception as e:
            self.logger.error(f"Error handling binary processing result: {e}")
    
    async def _handle_calculation_status(self, data: Dict[str, Any]):
        """Handle calculation status from TD service."""
        try:
            calc_status = data.get("calculation", {})
            self.logger.debug(f"TD calculation status: {calc_status}")
        except Exception as e:
            self.logger.error(f"Error handling calculation status: {e}")
    
    async def _handle_td_health_report(self, data: Dict[str, Any]):
        """Handle health report from TD service."""
        try:
            health_info = data.get("health", {})
            self.service_status["is_healthy"] = health_info.get("healthy", False)
            self.service_status["last_health_check"] = datetime.now()
            self.logger.debug(f"TD health report: {health_info}")
        except Exception as e:
            self.logger.error(f"Error handling TD health report: {e}")
    
    async def _handle_td_error_report(self, data: Dict[str, Any]):
        """Handle error report from TD service."""
        try:
            error_info = data.get("error", {})
            self.service_status["consecutive_failures"] += 1
            self.logger.error(f"TD error report: {error_info}")
        except Exception as e:
            self.logger.error(f"Error handling TD error report: {e}")
    
    async def send_command_to_td(self, command: Dict[str, Any]) -> bool:
        """Send command to connected TD ECM client."""
        if not self.connected_clients:
            self.logger.warning("No TD ECM clients connected - cannot send command")
            return False
        
        try:
            # Send to all connected clients (should be just one)
            for client_id, client_info in self.connected_clients.items():
                websocket = client_info["websocket"]
                await websocket.send(json.dumps(command))
                self.logger.debug(f"Sent command to TD ECM {client_id}: {command.get('type', 'unknown')}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error sending command to TD ECM: {e}")
            return False


    
    async def stop(self):
        """Stop the TDIM module."""
        try:
            self.is_active = False
            
            
            # Close all client connections
            for client_id, client_info in list(self.connected_clients.items()):
                try:
                    await client_info["websocket"].close()
                except:
                    pass
            self.connected_clients.clear()
            
            # Stop WebSocket server
            if self.websocket_server:
                self.websocket_server.close()
                await self.websocket_server.wait_closed()
                self.websocket_server = None
            # Close HTTP session
            if self.connections["http_session"]:
                await self.connections["http_session"].close()
            
            # Close WebSocket connection
            if self.connections["websocket"]:
                await self.connections["websocket"].close()
            
            # Cancel active orchestrations
            for orchestration_id in self.active_orchestrations.keys():
                await self._cancel_orchestration(orchestration_id)
            
            self.logger.info(f"{self.module_name} stopped successfully")
            
        except Exception as e:
            self.logger.error(f"Error stopping {self.module_name}: {e}")
            raise
    
    async def process_binary_file(self, binary_file_path: str, request_id: str,
                                 jfa_metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Process a binary file through TD orchestration engine.
        
        Args:
            binary_file_path: Path to binary file from JFA processing
            request_id: Request identifier for tracking
            jfa_metadata: Metadata from JFA processing
            
        Returns:
            Orchestration result with aggregated calculations
        """
        try:
            start_time = datetime.now()
            
            self.logger.info(f"Processing binary file for request {request_id} via TD orchestration")
            
            # Validate binary file
            if not os.path.exists(binary_file_path):
                raise FileNotFoundError(f"Binary file not found: {binary_file_path}")
            
            # Check file size
            file_size = os.path.getsize(binary_file_path)
            if file_size > self.orchestration_capabilities["max_binary_file_size"]:
                raise ValueError(f"Binary file size {file_size} exceeds maximum {self.orchestration_capabilities['max_binary_file_size']}")
            
            # Check orchestration capacity
            if len(self.active_orchestrations) >= self.td_config["max_concurrent_orchestrations"]:
                raise RuntimeError("Maximum concurrent orchestrations reached")
            
            # Create orchestration request
            orchestration_request = {
                "request_id": request_id,
                "binary_file_path": binary_file_path,
                "jfa_metadata": jfa_metadata or {},
                "orchestration_config": {
                    "enable_multi_calculation": True,
                    "enable_cross_analysis": True,
                    "enable_performance_optimization": True,
                    "ocm_integration": True
                },
                "timestamp": datetime.now().isoformat(),
                "source_service": "CCU"
            }
            
            # Send orchestration request to TD
            result = await self._send_orchestration_request(orchestration_request)
            
            if not result.get("success", False):
                self.service_status["failed_requests"] += 1
                self.service_status["orchestrations_failed"] += 1
                raise RuntimeError(f"TD orchestration failed: {result.get('errors', 'Unknown error')}")
            
            # Track orchestration
            orchestration_info = OrchestrationInfo(
                orchestration_id=result.get("orchestration_id", f"orch_{uuid.uuid4().hex[:8]}"),
                request_id=request_id,
                status=OrchestrationStatus.EXECUTING,
                total_calculations=len(result.get("active_calculations", [])),
                active_calculations=result.get("active_calculations", []),
                completed_calculations=[],
                failed_calculations=[],
                start_time=start_time,
                estimated_completion=None,
                processing_time=None,
                binary_file_path=binary_file_path,
                orchestration_plan=result.get("orchestration_plan", {})
            )
            
            self.active_orchestrations[orchestration_info.orchestration_id] = orchestration_info
            
            # Monitor orchestration progress
            orchestration_result = await self._monitor_orchestration_progress(orchestration_info)
            
            # Update statistics
            processing_time = (datetime.now() - start_time).total_seconds()
            self.service_status["total_requests"] += 1
            self.service_status["successful_requests"] += 1
            self.service_status["orchestrations_completed"] += 1
            self.service_status["last_successful_request"] = datetime.now()
            self.service_status["last_orchestration_time"] = processing_time
            
            # Update performance metrics
            self._update_performance_metrics(orchestration_result, processing_time)
            
            self.logger.info(f"Binary file processed successfully in {processing_time:.3f}s")
            
            return {
                "success": True,
                "request_id": request_id,
                "orchestration_id": orchestration_info.orchestration_id,
                "processing_time": processing_time,
                "orchestration_result": orchestration_result,
                "calculations_executed": orchestration_result.get("calculations_executed", []),
                "aggregated_results": orchestration_result.get("aggregated_results", {}),
                "ocm_ready": orchestration_result.get("ocm_ready", False),
                "metadata": {
                    "binary_file_path": binary_file_path,
                    "file_size": file_size,
                    "jfa_metadata": jfa_metadata,
                    "orchestration_summary": orchestration_result.get("orchestration_summary", {})
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error processing binary file: {e}")
            self.service_status["failed_requests"] += 1
            self.service_status["orchestrations_failed"] += 1
            self.service_status["consecutive_failures"] += 1
            
            return {
                "success": False,
                "error": str(e),
                "request_id": request_id,
                "timestamp": datetime.now().isoformat()
            }
    
    async def _send_orchestration_request(self, orchestration_request: Dict[str, Any]) -> Dict[str, Any]:
        """Send orchestration request to TD service."""
        try:
            url = f"http://{self.td_config['host']}:{self.td_config['api_port']}/process"
            
            async with self.connections["http_session"].post(url, json=orchestration_request) as response:
                if response.status == 200:
                    result = await response.json()
                    return result
                else:
                    error_text = await response.text()
                    return {
                        "success": False,
                        "errors": [f"HTTP {response.status}: {error_text}"]
                    }
                    
        except Exception as e:
            self.logger.error(f"Error sending orchestration request: {e}")
            return {
                "success": False,
                "errors": [str(e)]
            }
    
    async def _monitor_orchestration_progress(self, orchestration_info: OrchestrationInfo) -> Dict[str, Any]:
        """Monitor orchestration progress until completion."""
        try:
            max_wait_time = self.td_config["timeout"]
            check_interval = 5  # Check every 5 seconds
            elapsed_time = 0
            
            while elapsed_time < max_wait_time:
                # Check orchestration status
                status_result = await self._get_orchestration_status(orchestration_info.orchestration_id)
                
                if status_result.get("success", False):
                    status_data = status_result.get("status", {})
                    current_status = status_data.get("status", "unknown")
                    
                    # Update orchestration info
                    orchestration_info.status = OrchestrationStatus(current_status)
                    orchestration_info.completed_calculations = status_data.get("completed_calculations", [])
                    orchestration_info.failed_calculations = status_data.get("failed_calculations", [])
                    
                    # Check if completed
                    if current_status in ["completed", "failed", "cancelled"]:
                        orchestration_info.processing_time = elapsed_time
                        
                        # Get final results
                        if current_status == "completed":
                            final_result = await self._get_orchestration_results(orchestration_info.orchestration_id)
                            return final_result
                        else:
                            return {
                                "success": False,
                                "status": current_status,
                                "orchestration_id": orchestration_info.orchestration_id,
                                "error": f"Orchestration {current_status}"
                            }
                
                # Wait before next check
                await asyncio.sleep(check_interval)
                elapsed_time += check_interval
            
            # Timeout reached
            orchestration_info.status = OrchestrationStatus.FAILED
            return {
                "success": False,
                "status": "timeout",
                "orchestration_id": orchestration_info.orchestration_id,
                "error": f"Orchestration timed out after {max_wait_time} seconds"
            }
            
        except Exception as e:
            self.logger.error(f"Error monitoring orchestration progress: {e}")
            return {
                "success": False,
                "error": str(e),
                "orchestration_id": orchestration_info.orchestration_id
            }
    
    async def _get_orchestration_status(self, orchestration_id: str) -> Dict[str, Any]:
        """Get orchestration status from TD service."""
        try:
            url = f"http://{self.td_config['host']}:{self.td_config['api_port']}/orchestration/{orchestration_id}/status"
            
            async with self.connections["http_session"].get(url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {
                        "success": False,
                        "error": f"HTTP {response.status}"
                    }
                    
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _get_orchestration_results(self, orchestration_id: str) -> Dict[str, Any]:
        """Get final orchestration results from TD service."""
        try:
            url = f"http://{self.td_config['host']}:{self.td_config['api_port']}/orchestration/{orchestration_id}/results"
            
            async with self.connections["http_session"].get(url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {
                        "success": False,
                        "error": f"HTTP {response.status}"
                    }
                    
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _cancel_orchestration(self, orchestration_id: str) -> Dict[str, Any]:
        """Cancel an active orchestration."""
        try:
            url = f"http://{self.td_config['host']}:{self.td_config['api_port']}/orchestration/{orchestration_id}/cancel"
            
            async with self.connections["http_session"].post(url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {
                        "success": False,
                        "error": f"HTTP {response.status}"
                    }
                    
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_calculation_status(self) -> Dict[str, Any]:
        """Get current calculation block status from TD."""
        try:
            url = f"http://{self.td_config['host']}:{self.td_config['api_port']}/calculation/status"
            
            async with self.connections["http_session"].get(url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {
                        "success": False,
                        "error": f"HTTP {response.status}"
                    }
                    
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_td_health(self) -> Dict[str, Any]:
        """Get TD service health status."""
        try:
            url = f"http://{self.td_config['host']}:{self.td_config['health_port']}/health"
            
            async with self.connections["http_session"].get(url) as response:
                if response.status == 200:
                    health_data = await response.json()
                    self.service_status["is_healthy"] = health_data.get("healthy", False)
                    self.service_status["last_health_check"] = datetime.now()
                    self.service_status["consecutive_failures"] = 0
                    
                    # Update module health
                    modules = health_data.get("modules", {})
                    for module_name, module_health in modules.items():
                        if module_name in self.module_health:
                            self.module_health[module_name]["healthy"] = module_health.get("healthy", False)
                            self.module_health[module_name]["last_check"] = datetime.now()
                    
                    return health_data
                else:
                    self.service_status["is_healthy"] = False
                    self.service_status["consecutive_failures"] += 1
                    return {
                        "healthy": False,
                        "error": f"HTTP {response.status}"
                    }
                    
        except Exception as e:
            self.service_status["is_healthy"] = False
            self.service_status["consecutive_failures"] += 1
            return {
                "healthy": False,
                "error": str(e)
            }
    
    async def _monitor_td_health(self):
        """Monitor TD service health."""
        while self.is_active:
            try:
                await self.get_td_health()
                await asyncio.sleep(self.connections["health_check_interval"])
                
            except Exception as e:
                self.logger.error(f"Error monitoring TD health: {e}")
                await asyncio.sleep(self.connections["health_check_interval"])
    
    async def _maintain_websocket_connection(self):
        """Maintain WebSocket connection to TD service."""
        while self.is_active:
            try:
                uri = f"ws://{self.td_config['host']}:{self.td_config['websocket_port']}/ws"
                
                async with websockets.connect(uri) as websocket:
                    self.connections["websocket"] = websocket
                    self.logger.info("WebSocket connection to TD established")
                    
                    # Send identification
                    await websocket.send(json.dumps({
                        "type": "identify",
                        "client_id": "CCU_TDIM",
                        "timestamp": datetime.now().isoformat()
                    }))
                    
                    # Listen for messages
                    async for message in websocket:
                        await self._handle_websocket_message(message)
                        
            except Exception as e:
                self.logger.error(f"WebSocket connection error: {e}")
                self.connections["websocket"] = None
                await asyncio.sleep(10)  # Retry after 10 seconds
    
    async def _handle_websocket_message(self, message: str):
        """Handle incoming WebSocket messages from TD."""
        try:
            data = json.loads(message)
            message_type = data.get("type", "unknown")
            
            if message_type == "orchestration_update":
                await self._handle_orchestration_update(data)
            elif message_type == "calculation_update":
                await self._handle_calculation_update(data)
            elif message_type == "health_update":
                await self._handle_health_update(data)
            elif message_type == "error_report":
                await self._handle_error_report(data)
            else:
                self.logger.debug(f"Received unknown message type: {message_type}")
                
        except Exception as e:
            self.logger.error(f"Error handling WebSocket message: {e}")
    
    async def _handle_orchestration_update(self, data: Dict[str, Any]):
        """Handle orchestration update from TD."""
        try:
            orchestration_id = data.get("orchestration_id")
            if orchestration_id in self.active_orchestrations:
                orchestration_info = self.active_orchestrations[orchestration_id]
                
                # Update orchestration info
                orchestration_info.status = OrchestrationStatus(data.get("status", "unknown"))
                orchestration_info.completed_calculations = data.get("completed_calculations", [])
                orchestration_info.failed_calculations = data.get("failed_calculations", [])
                
                self.logger.info(f"Orchestration {orchestration_id} updated: {orchestration_info.status.value}")
                
        except Exception as e:
            self.logger.error(f"Error handling orchestration update: {e}")
    
    async def _handle_calculation_update(self, data: Dict[str, Any]):
        """Handle calculation update from TD."""
        try:
            calculation_name = data.get("calculation_name")
            status = data.get("status")
            
            self.logger.info(f"Calculation {calculation_name} status: {status}")
            
            # Update calculation success rates
            if calculation_name not in self.performance_metrics["calculation_success_rates"]:
                self.performance_metrics["calculation_success_rates"][calculation_name] = {
                    "total": 0,
                    "successful": 0,
                    "failed": 0
                }
            
            calc_metrics = self.performance_metrics["calculation_success_rates"][calculation_name]
            calc_metrics["total"] += 1
            
            if status == "completed":
                calc_metrics["successful"] += 1
            elif status == "failed":
                calc_metrics["failed"] += 1
                
        except Exception as e:
            self.logger.error(f"Error handling calculation update: {e}")
    
    async def _handle_health_update(self, data: Dict[str, Any]):
        """Handle health update from TD."""
        try:
            module_name = data.get("module")
            healthy = data.get("healthy", False)
            
            if module_name in self.module_health:
                self.module_health[module_name]["healthy"] = healthy
                self.module_health[module_name]["last_check"] = datetime.now()
                
                if not healthy:
                    self.logger.warning(f"TD module {module_name} is unhealthy")
                    
        except Exception as e:
            self.logger.error(f"Error handling health update: {e}")
    
    async def _handle_error_report(self, data: Dict[str, Any]):
        """Handle error report from TD."""
        try:
            error_type = data.get("error_type", "unknown")
            error_message = data.get("error_message", "")
            orchestration_id = data.get("orchestration_id")
            
            self.logger.error(f"TD error report: {error_type} - {error_message}")
            
            # Update orchestration if relevant
            if orchestration_id and orchestration_id in self.active_orchestrations:
                orchestration_info = self.active_orchestrations[orchestration_id]
                orchestration_info.status = OrchestrationStatus.FAILED
                
        except Exception as e:
            self.logger.error(f"Error handling error report: {e}")
    
    async def _monitor_orchestrations(self):
        """Monitor active orchestrations for timeouts and cleanup."""
        while self.is_active:
            try:
                current_time = datetime.now()
                timeout_threshold = timedelta(seconds=self.td_config["timeout"])
                
                # Check for timed out orchestrations
                for orchestration_id, orchestration_info in list(self.active_orchestrations.items()):
                    if current_time - orchestration_info.start_time > timeout_threshold:
                        self.logger.warning(f"Orchestration {orchestration_id} timed out")
                        orchestration_info.status = OrchestrationStatus.FAILED
                        
                        # Cancel orchestration
                        await self._cancel_orchestration(orchestration_id)
                
                # Clean up completed orchestrations
                completed_orchestrations = [
                    orchestration_id for orchestration_id, orchestration_info 
                    in self.active_orchestrations.items()
                    if orchestration_info.status in [OrchestrationStatus.COMPLETED, OrchestrationStatus.FAILED, OrchestrationStatus.CANCELLED]
                ]
                
                for orchestration_id in completed_orchestrations:
                    # Move to history
                    self.orchestration_history.append(self.active_orchestrations[orchestration_id])
                    del self.active_orchestrations[orchestration_id]
                    
                    # Keep only last 100 orchestrations in history
                    if len(self.orchestration_history) > 100:
                        self.orchestration_history = self.orchestration_history[-100:]
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                self.logger.error(f"Error monitoring orchestrations: {e}")
                await asyncio.sleep(60)
    
    async def _monitor_performance(self):
        """Monitor performance metrics."""
        while self.is_active:
            try:
                # Calculate throughput metrics
                current_time = datetime.now()
                
                # Update hourly metrics
                self.performance_metrics["throughput_metrics"]["orchestrations_per_hour"] = (
                    self.service_status["orchestrations_completed"] / 
                    max(1, (current_time - datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)).total_seconds() / 3600)
                )
                
                # Update resource utilization from TD
                try:
                    td_status = await self.get_td_status()
                    if td_status.get("success", False):
                        self.performance_metrics["resource_utilization"] = td_status.get("resource_utilization", {})
                except Exception:
                    pass
                
                await asyncio.sleep(300)  # Update every 5 minutes
                
            except Exception as e:
                self.logger.error(f"Error monitoring performance: {e}")
                await asyncio.sleep(300)
    
    async def get_td_status(self) -> Dict[str, Any]:
        """Get comprehensive TD service status."""
        try:
            url = f"http://{self.td_config['host']}:{self.td_config['api_port']}/status"
            
            async with self.connections["http_session"].get(url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {
                        "success": False,
                        "error": f"HTTP {response.status}"
                    }
                    
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _update_performance_metrics(self, orchestration_result: Dict[str, Any], processing_time: float):
        """Update performance metrics."""
        try:
            # Update response times
            self.performance_metrics["orchestration_response_times"].append(processing_time)
            
            # Keep only last 100 response times
            if len(self.performance_metrics["orchestration_response_times"]) > 100:
                self.performance_metrics["orchestration_response_times"] = (
                    self.performance_metrics["orchestration_response_times"][-100:]
                )
            
            # Update calculation success rates
            calculations_executed = orchestration_result.get("calculations_executed", [])
            for calc_name in calculations_executed:
                if calc_name not in self.performance_metrics["calculation_success_rates"]:
                    self.performance_metrics["calculation_success_rates"][calc_name] = {
                        "total": 0,
                        "successful": 0,
                        "failed": 0
                    }
                
                calc_metrics = self.performance_metrics["calculation_success_rates"][calc_name]
                calc_metrics["total"] += 1
                
                if orchestration_result.get("success", False):
                    calc_metrics["successful"] += 1
                else:
                    calc_metrics["failed"] += 1
                    
        except Exception as e:
            self.logger.error(f"Error updating performance metrics: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current TDIM status."""
        return {
            "module": self.module_name,
            "is_active": self.is_active,
            "service_status": self.service_status,
            "td_config": self.td_config,
            "orchestration_capabilities": self.orchestration_capabilities,
            "active_orchestrations": len(self.active_orchestrations),
            "orchestration_history": len(self.orchestration_history),
            "performance_metrics": self.performance_metrics,
            "module_health": self.module_health,
            "connections": {
                "http_session": self.connections["http_session"] is not None,
                "websocket": self.connections["websocket"] is not None,
                "last_health_check": self.service_status["last_health_check"]
            }
        }
    
    def get_orchestration_summary(self) -> Dict[str, Any]:
        """Get orchestration summary."""
        return {
            "active_orchestrations": {
                orchestration_id: {
                    "request_id": info.request_id,
                    "status": info.status.value,
                    "total_calculations": info.total_calculations,
                    "active_calculations": info.active_calculations,
                    "completed_calculations": info.completed_calculations,
                    "failed_calculations": info.failed_calculations,
                    "start_time": info.start_time.isoformat(),
                    "processing_time": info.processing_time
                }
                for orchestration_id, info in self.active_orchestrations.items()
            },
            "statistics": {
                "total_orchestrations": len(self.orchestration_history) + len(self.active_orchestrations),
                "completed_orchestrations": self.service_status["orchestrations_completed"],
                "failed_orchestrations": self.service_status["orchestrations_failed"],
                "success_rate": (
                    self.service_status["orchestrations_completed"] / 
                    max(1, self.service_status["orchestrations_completed"] + self.service_status["orchestrations_failed"])
                ),
                "average_processing_time": (
                    sum(self.performance_metrics["orchestration_response_times"]) / 
                    max(1, len(self.performance_metrics["orchestration_response_times"]))
                )
            }
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        try:
            # Check TD service health
            td_health = await self.get_td_health()
            
            # Check connection status
            http_connected = self.connections["http_session"] is not None
            websocket_connected = self.connections["websocket"] is not None
            
            # Check module health
            unhealthy_modules = [
                module_name for module_name, health in self.module_health.items()
                if not health["healthy"]
            ]
            
            is_healthy = (
                self.is_active and
                td_health.get("healthy", False) and
                http_connected and
                len(unhealthy_modules) == 0
            )
            
            return {
                "healthy": is_healthy,
                "module": self.module_name,
                "td_service_healthy": td_health.get("healthy", False),
                "connections": {
                    "http_connected": http_connected,
                    "websocket_connected": websocket_connected
                },
                "modules": self.module_health,
                "unhealthy_modules": unhealthy_modules,
                "active_orchestrations": len(self.active_orchestrations),
                "service_status": self.service_status,
                "last_health_check": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "healthy": False,
                "module": self.module_name,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            } 