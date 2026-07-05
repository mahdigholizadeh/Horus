"""
JFA Interaction Module (JFAIM) for CCU

This module handles all interactions with the JFA (JSON File Analyzer) microservice,
providing comprehensive template analysis, binary generation, and analytical processing
capabilities for the CCU system.

Enhanced to work with the new modular JFA architecture featuring:
- 14-module architecture integration
- Advanced template validation
- Binary data processing
- Statistical analysis and decision-making
- Real-time monitoring and health checks
"""

import asyncio
import aiohttp
import websockets
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import time
import uuid
import sys
from pathlib import Path

# Add utils path for WebSocketPortManager
sys.path.insert(0, str(Path(__file__).parent.parent / "utils"))
from websocket_port_manager import WebSocketPortManager


class JFAInteractionModule:
    """
    Enhanced JFA Interaction Module for CCU
    
    Provides comprehensive integration with the refactored JFA microservice,
    supporting advanced template analysis, binary generation, and analytical processing.
    """
    
    def __init__(self, ccu_config: Dict[str, Any] = None):
        """Initialize the JFAIM with enhanced configuration."""
        self.logger = logging.getLogger(__name__)
        self.module_name = "JFAIM"
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
        self.connected_clients = {}  # Track JFA ECM connections
        self.max_clients = 1  # Only one JFA ECM should connect
        
        # Load JFA configuration from CCU (includes PMM paths and network config)
        jfa_setting = ccu_config.get('jfa_setting', {}) if ccu_config else {}
        
        # Enhanced JFA API configuration (with PMM-provided defaults)
        self.jfa_config = {
            "base_url": jfa_setting.get("network", {}).get("base_url", "http://localhost:8001"),
            "websocket_url": jfa_setting.get("network", {}).get("websocket_url", "ws://localhost:11491"),
            "health_url": jfa_setting.get("network", {}).get("health_url", "http://localhost:9092"),
            "timeout": jfa_setting.get("network", {}).get("timeout", 30),
            "retry_attempts": jfa_setting.get("network", {}).get("retry_attempts", 3),
            "retry_delay": jfa_setting.get("network", {}).get("retry_delay", 2),
            "max_retries": jfa_setting.get("processing", {}).get("max_retries", 5),
            "batch_size": jfa_setting.get("processing", {}).get("batch_size", 50),
            "concurrent_requests": jfa_setting.get("processing", {}).get("concurrent_requests", 10)
        }
        
        # Advanced processing configuration
        self.processing_config = {
            "enable_template_validation": True,
            "enable_binary_generation": True,
            "enable_data_analysis": True,
            "enable_pattern_detection": True,
            "enable_anomaly_detection": True,
            "enable_quality_assessment": True,
            "validation_strictness": "high",
            "analysis_mode": "comprehensive",
            "binary_format": "standard",
            "compression_enabled": True
        }
        
        # Enhanced monitoring and statistics
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "templates_processed": 0,
            "binary_files_generated": 0,
            "analyses_completed": 0,
            "validation_success_rate": 0.0,
            "average_processing_time": 0.0,
            "last_activity": None,
            "connection_status": "disconnected",
            "health_status": "unknown",
            "performance_metrics": {
                "requests_per_second": 0.0,
                "avg_response_time": 0.0,
                "error_rate": 0.0,
                "throughput": 0.0
            }
        }
        
        # Connection management
        self.http_session = None
        self.websocket_connection = None
        self.connection_retry_count = 0
        
        # Request tracking
        self.active_requests = {}
        self.request_queue = asyncio.Queue()
        
        # JFA service status
        self.jfa_status = {
            "service_available": False,
            "last_health_check": None,
            "service_version": "unknown",
            "modules_status": {},
            "performance_data": {}
        }
        
        # Template validation rules
        self.validation_rules = {
            "required_fields": ["id", "object", "created", "model", "choices"],
            "jfa_specific_fields": ["flag", "loca", "cust", "sinf"],
            "validation_modes": ["basic", "comprehensive", "strict"],
            "business_rules": ["payload_validation", "schema_validation", "route_consistency"]
        }
        
        self.logger.info(f"Enhanced {self.module_name} initialized successfully")
    
    async def start(self):
        """Start the enhanced JFAIM module."""
        try:
            self.logger.info("Starting enhanced JFA Interaction Module...")
            
            # Initialize HTTP session
            self.http_session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.jfa_config["timeout"])
            )
            
            # Start background tasks
            asyncio.create_task(self._health_monitoring_loop())
            asyncio.create_task(self._websocket_connection_loop())
            asyncio.create_task(self._request_processing_loop())
            asyncio.create_task(self._statistics_update_loop())
            
            # Perform initial health check
            await self._initial_health_check()
            
            self.is_active = True
            
            # Start WebSocket server for ECM connections
            await self.start_websocket_server()
            self.logger.info("Enhanced JFAIM started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start enhanced JFAIM: {e}")
            raise
    async def start_websocket_server(self):
        """Start WebSocket server for JFA ECM connections."""
        try:
            self.logger.info("Starting JFAIM WebSocket server...")
            
            # Start WebSocket server using port manager
            self.websocket_server = await self.port_manager.start_ccu_websocket_server(
                "JFAIM", 
                self.handle_jfa_connection
            )
            
            if not self.websocket_server:
                raise Exception("Failed to start WebSocket server - no available ports")
            
            # Get the allocated port
            self.websocket_server_port = self.port_manager.allocated_ports.get("JFAIM")
            
            self.logger.info(f"✅ JFAIM WebSocket server started on port {self.websocket_server_port}")
            self.logger.info(f"🔗 JFA ECM should connect to: ws://localhost:{self.websocket_server_port}/ws")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to start JFAIM WebSocket server: {e}")
            raise
    
    async def handle_jfa_connection(self, websocket, path):
        """Handle incoming JFA ECM WebSocket connection."""
        client_id = None
        try:
            client_id = f"JFA_ECM_{id(websocket)}"
            client_address = websocket.remote_address
            self.logger.info(f"🔗 JFA ECM connected from {client_address} (ID: {client_id})")
            
            # Check if we already have max connections
            if len(self.connected_clients) >= self.max_clients:
                self.logger.warning(f"⚠️ Maximum JFA connections ({self.max_clients}) reached, rejecting new connection")
                await websocket.close(code=1008, reason="Maximum connections reached")
                return
            
            # Add client to connected clients
            self.connected_clients[client_id] = {
                "websocket": websocket,
                "connected_at": datetime.now(),
                "last_heartbeat": datetime.now(),
                "client_address": client_address
            }
            
            self.logger.info(f"✅ JFA ECM client registered (Total clients: {len(self.connected_clients)})")
            
            # Send welcome message
            welcome_msg = {
                "type": "welcome",
                "client_id": client_id,
                "server": "JFAIM",
                "timestamp": datetime.now().isoformat(),
                "message": "Connected to CCU JFAIM WebSocket server"
            }
            await websocket.send(json.dumps(welcome_msg))
            
            # Listen for messages from this JFA ECM client
            await self.handle_client_messages(websocket, client_id)
            
        except Exception as e:
            self.logger.error(f"❌ Error handling JFA connection: {e}")
        finally:
            # Clean up client connection
            if client_id and client_id in self.connected_clients:
                del self.connected_clients[client_id]
                self.logger.info(f"🔌 JFA ECM client {client_id} disconnected")
    
    async def handle_client_messages(self, websocket, client_id: str):
        """Listen for messages from a specific JFA ECM client."""
        try:
            async for message in websocket:
                self.logger.debug(f"Received message from JFA ECM {client_id}: {message}")
                
                # Update heartbeat
                if client_id in self.connected_clients:
                    self.connected_clients[client_id]["last_heartbeat"] = datetime.now()
                
                try:
                    data = json.loads(message)
                    # Process message
                    await self.handle_jfa_message(data, client_id)
                except json.JSONDecodeError as e:
                    self.logger.error(f"Invalid JSON message from JFA client {client_id}: {e}")
                    error_response = {
                        "type": "error",
                        "error": "invalid_json",
                        "message": str(e),
                        "timestamp": datetime.now().isoformat()
                    }
                    await websocket.send(json.dumps(error_response))
                
        except Exception as e:
            self.logger.error(f"Error handling messages from JFA ECM {client_id}: {e}")
    
    async def handle_jfa_message(self, data: Dict[str, Any], client_id: str):
        """Handle a message from JFA ECM."""
        try:
            message_type = data.get("type", "unknown")
            
            self.logger.debug(f"Processing {message_type} message from JFA ECM {client_id}")
            
            # Handle different message types
            if message_type == "heartbeat":
                await self._handle_jfa_heartbeat(data, client_id)
            elif message_type == "status_update":
                await self._handle_jfa_status_update(data)
            elif message_type == "processing_result":
                await self._handle_jfa_processing_result(data)
            elif message_type == "template_validation_result":
                await self._handle_template_validation_result(data)
            elif message_type == "binary_generation_result":
                await self._handle_binary_generation_result(data)
            elif message_type == "health_report":
                await self._handle_jfa_health_report(data)
            elif message_type == "error_report":
                await self._handle_jfa_error_report(data)
            else:
                self.logger.warning(f"Unknown message type '{message_type}' from JFA ECM {client_id}")
                
        except Exception as e:
            self.logger.error(f"Error processing message from JFA ECM {client_id}: {e}")
    
    async def _handle_jfa_heartbeat(self, data: Dict[str, Any], client_id: str):
        """Handle heartbeat from JFA ECM."""
        response = {
            "type": "heartbeat_response",
            "timestamp": datetime.now().isoformat(),
            "server": "JFAIM",
            "client_id": client_id
        }
        
        if client_id in self.connected_clients:
            try:
                await self.connected_clients[client_id]["websocket"].send(json.dumps(response))
            except Exception as e:
                self.logger.error(f"Failed to send heartbeat response to {client_id}: {e}")
    
    async def _handle_jfa_status_update(self, data: Dict[str, Any]):
        """Handle status update from JFA service."""
        try:
            status = data.get("status", {})
            self.jfa_status["service_available"] = status.get("is_active", False)
            self.jfa_status["last_health_check"] = datetime.now()
            self.logger.debug(f"Received JFA status update: {status}")
        except Exception as e:
            self.logger.error(f"Error handling JFA status update: {e}")
    
    async def _handle_jfa_processing_result(self, data: Dict[str, Any]):
        """Handle processing result from JFA service."""
        try:
            request_id = data.get("request_id")
            if request_id in self.active_requests:
                self.active_requests[request_id]["status"] = "completed"
                self.active_requests[request_id]["result"] = data.get("result")
                self.logger.debug(f"JFA processing result received for {request_id}")
        except Exception as e:
            self.logger.error(f"Error handling processing result: {e}")
    
    async def _handle_template_validation_result(self, data: Dict[str, Any]):
        """Handle template validation result from JFA."""
        try:
            validation_info = data.get("validation", {})
            self.logger.info(f"JFA template validation result: {validation_info}")
        except Exception as e:
            self.logger.error(f"Error handling template validation result: {e}")
    
    async def _handle_binary_generation_result(self, data: Dict[str, Any]):
        """Handle binary generation result from JFA."""
        try:
            binary_info = data.get("binary", {})
            self.logger.info(f"JFA binary generation result: {binary_info}")
        except Exception as e:
            self.logger.error(f"Error handling binary generation result: {e}")
    
    async def _handle_jfa_health_report(self, data: Dict[str, Any]):
        """Handle health report from JFA service."""
        try:
            health_info = data.get("health", {})
            self.jfa_status["service_available"] = health_info.get("healthy", False)
            self.jfa_status["last_health_check"] = datetime.now()
            self.logger.debug(f"JFA health report: {health_info}")
        except Exception as e:
            self.logger.error(f"Error handling JFA health report: {e}")
    
    async def _handle_jfa_error_report(self, data: Dict[str, Any]):
        """Handle error report from JFA service."""
        try:
            error_info = data.get("error", {})
            self.logger.error(f"JFA error report: {error_info}")
        except Exception as e:
            self.logger.error(f"Error handling JFA error report: {e}")
    
    async def send_command_to_jfa(self, command: Dict[str, Any]) -> bool:
        """Send command to connected JFA ECM client."""
        if not self.connected_clients:
            self.logger.warning("No JFA ECM clients connected - cannot send command")
            return False
        
        try:
            # Send to all connected clients (should be just one)
            for client_id, client_info in self.connected_clients.items():
                websocket = client_info["websocket"]
                await websocket.send(json.dumps(command))
                self.logger.debug(f"Sent command to JFA ECM {client_id}: {command.get('type', 'unknown')}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error sending command to JFA ECM: {e}")
            return False


    
    async def stop(self):
        """Stop the enhanced JFAIM module."""
        try:
            self.logger.info("Stopping enhanced JFA Interaction Module...")
            
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
            # Close connections
            if self.websocket_connection:
                await self.websocket_connection.close()
            
            if self.http_session:
                await self.http_session.close()
            
            # Cancel active requests
            for request_id, request_info in self.active_requests.items():
                if "task" in request_info:
                    request_info["task"].cancel()
            
            self.logger.info("Enhanced JFAIM stopped successfully")
            
        except Exception as e:
            self.logger.error(f"Error stopping enhanced JFAIM: {e}")
    
    async def process_template_comprehensive(self, template_data: Dict[str, Any], 
                                           request_id: str = None,
                                           processing_options: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Process a template through the comprehensive JFA pipeline.
        
        Args:
            template_data: Template data to process
            request_id: Optional request ID for tracking
            processing_options: Optional processing configuration
            
        Returns:
            Comprehensive processing results
        """
        try:
            if not request_id:
                request_id = f"jfa_req_{uuid.uuid4().hex[:8]}"
            
            start_time = time.time()
            self.stats["total_requests"] += 1
            
            # Merge processing options
            options = {**self.processing_config, **(processing_options or {})}
            
            # Prepare request payload
            request_payload = {
                "template_data": template_data,
                "request_id": request_id,
                "processing_options": options,
                "validation_rules": self.validation_rules,
                "analysis_config": {
                    "enable_statistical_analysis": options.get("enable_data_analysis", True),
                    "enable_pattern_detection": options.get("enable_pattern_detection", True),
                    "enable_anomaly_detection": options.get("enable_anomaly_detection", True),
                    "enable_decision_making": True,
                    "decision_threshold": 0.7
                }
            }
            
            # Track request
            self.active_requests[request_id] = {
                "start_time": start_time,
                "status": "processing",
                "template_data": template_data,
                "options": options
            }
            
            # Send request to JFA service
            result = await self._send_comprehensive_request(request_payload)
            
            # Process response
            processing_time = time.time() - start_time
            
            if result.get("success", False):
                self.stats["successful_requests"] += 1
                self.stats["templates_processed"] += 1
                
                # Update specific metrics
                if result.get("flags", {}).get("binary_generated", False):
                    self.stats["binary_files_generated"] += 1
                
                if result.get("flags", {}).get("analysis_completed", False):
                    self.stats["analyses_completed"] += 1
                
                # Enhanced response processing
                enhanced_result = await self._process_jfa_response(result, processing_time)
                
                # Update success rate
                self._update_success_rate()
                
                # Update performance metrics
                self._update_performance_metrics(processing_time)
                
                self.logger.info(f"Successfully processed template {request_id} in {processing_time:.3f}s")
                
                return enhanced_result
                
            else:
                self.stats["failed_requests"] += 1
                error_msg = result.get("error", "Unknown JFA processing error")
                self.logger.error(f"JFA processing failed for {request_id}: {error_msg}")
                
                return {
                    "success": False,
                    "error": error_msg,
                    "request_id": request_id,
                    "processing_time": processing_time,
                    "service": "JFA",
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            processing_time = time.time() - start_time
            self.stats["failed_requests"] += 1
            error_msg = f"Enhanced JFA processing error: {str(e)}"
            self.logger.error(error_msg)
            
            return {
                "success": False,
                "error": error_msg,
                "request_id": request_id,
                "processing_time": processing_time,
                "service": "JFA",
                "timestamp": datetime.now().isoformat()
            }
            
        finally:
            # Clean up request tracking
            if request_id in self.active_requests:
                del self.active_requests[request_id]
            
            self.stats["last_activity"] = datetime.now()
    
    async def _send_comprehensive_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Send comprehensive request to JFA service."""
        try:
            # Determine endpoint based on processing mode
            endpoint = "/process"
            
            # Add headers
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "CCU-JFAIM/1.0",
                "X-Request-Source": "CCU",
                "X-Processing-Mode": "comprehensive"
            }
            
            # Send request with retries
            for attempt in range(self.jfa_config["retry_attempts"]):
                try:
                    async with self.http_session.post(
                        f"{self.jfa_config['base_url']}{endpoint}",
                        json=payload,
                        headers=headers
                    ) as response:
                        
                        if response.status == 200:
                            result = await response.json()
                            return result
                        else:
                            error_text = await response.text()
                            self.logger.error(f"JFA API error {response.status}: {error_text}")
                            
                            if attempt < self.jfa_config["retry_attempts"] - 1:
                                await asyncio.sleep(self.jfa_config["retry_delay"])
                                continue
                            
                            return {
                                "success": False,
                                "error": f"JFA API error {response.status}: {error_text}",
                                "status_code": response.status
                            }
                            
                except aiohttp.ClientError as e:
                    self.logger.error(f"JFA connection error (attempt {attempt + 1}): {e}")
                    
                    if attempt < self.jfa_config["retry_attempts"] - 1:
                        await asyncio.sleep(self.jfa_config["retry_delay"])
                        continue
                    
                    return {
                        "success": False,
                        "error": f"JFA connection failed: {str(e)}",
                        "connection_error": True
                    }
            
            return {
                "success": False,
                "error": "JFA service unavailable after retries",
                "retries_exhausted": True
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Request processing error: {str(e)}",
                "exception": True
            }
    
    async def _process_jfa_response(self, response: Dict[str, Any], processing_time: float) -> Dict[str, Any]:
        """Process and enhance JFA response."""
        try:
            # Extract core information
            enhanced_response = {
                "success": response.get("success", False),
                "JFA_flag": response.get("flags", {}).get("JFA_flag", 1),
                "request_id": response.get("request_id", "unknown"),
                "processing_time": processing_time,
                "service": "JFA",
                "timestamp": datetime.now().isoformat()
            }
            
            # Handle validation analysis data if available
            if not response.get("success", False) and response.get("recognition_available", False):
                validation_analysis = response.get("validation_analysis", {})
                enhanced_response["validation_analysis"] = validation_analysis
                
                # Extract recognition data for CCU processing
                if "invalid_data_recognition" in validation_analysis:
                    enhanced_response["invalid_data_recognition"] = validation_analysis["invalid_data_recognition"]
                
                if "insufficient_data_recognition" in validation_analysis:
                    enhanced_response["insufficient_data_recognition"] = validation_analysis["insufficient_data_recognition"]
            
            # Add processing results
            if "processed_data" in response:
                enhanced_response["processed_data"] = response["processed_data"]
            
            # Add validation results
            if "validation_result" in response:
                validation = response["validation_result"]
                enhanced_response["validation"] = {
                    "passed": validation.get("valid", False),
                    "score": validation.get("validation_score", 0),
                    "errors": validation.get("errors", []),
                    "warnings": validation.get("warnings", []),
                    "business_rules": validation.get("business_rule_results", {})
                }
            
            # Add binary generation results
            if "binary_result" in response:
                binary = response["binary_result"]
                enhanced_response["binary"] = {
                    "generated": binary.get("success", False),
                    "size": binary.get("size", 0),
                    "format": binary.get("format_type", "unknown"),
                    "compression_ratio": binary.get("generation_stats", {}).get("compression_ratio", 0),
                    "checksum": binary.get("checksum", "")
                }
            
            # Add analysis results
            if "analysis_result" in response:
                analysis = response["analysis_result"]
                enhanced_response["analysis"] = {
                    "completed": analysis.get("success", False),
                    "algorithms_used": analysis.get("algorithms_used", []),
                    "statistical_analysis": analysis.get("results", {}).get("statistical", {}),
                    "pattern_detection": analysis.get("results", {}).get("pattern", {}),
                    "anomaly_detection": analysis.get("results", {}).get("anomaly", {}),
                    "quality_assessment": analysis.get("results", {}).get("quality", {}),
                    "decisions": analysis.get("decisions", {}),
                    "insights": analysis.get("insights", {}),
                    "recommendations": analysis.get("recommendations", [])
                }
            
            # Add statistics
            if "statistics" in response:
                enhanced_response["statistics"] = response["statistics"]
            
            # Add flags
            enhanced_response["flags"] = {
                "validation_passed": response.get("flags", {}).get("validation_passed", False),
                "binary_generated": response.get("flags", {}).get("binary_generated", False),
                "analysis_completed": response.get("flags", {}).get("analysis_completed", False),
                "quality_grade": response.get("analysis", {}).get("quality", {}).get("quality_grade", "F")
            }
            
            # Add JFA-specific metadata
            enhanced_response["jfa_metadata"] = {
                "processing_pipeline": ["IPM", "JDPM", "TVM", "BDM", "DAM", "OPM"],
                "modules_involved": response.get("metadata", {}).get("modules_used", []),
                "service_version": "1.0.0",
                "architecture": "14-module",
                "processing_mode": "comprehensive"
            }
            
            return enhanced_response
            
        except Exception as e:
            self.logger.error(f"Error processing JFA response: {e}")
            return {
                "success": False,
                "error": f"Response processing error: {str(e)}",
                "original_response": response,
                "processing_time": processing_time,
                "service": "JFA",
                "timestamp": datetime.now().isoformat()
            }
    
    async def batch_process_templates(self, templates: List[Dict[str, Any]], 
                                    batch_options: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Process multiple templates in batch."""
        try:
            batch_id = f"jfa_batch_{uuid.uuid4().hex[:8]}"
            self.logger.info(f"Starting batch processing {batch_id} with {len(templates)} templates")
            
            # Configure batch processing
            batch_size = min(len(templates), self.jfa_config["batch_size"])
            concurrent_limit = min(batch_size, self.jfa_config["concurrent_requests"])
            
            # Process templates in batches
            results = []
            semaphore = asyncio.Semaphore(concurrent_limit)
            
            async def process_single_template(template_data: Dict[str, Any], index: int):
                async with semaphore:
                    request_id = f"{batch_id}_item_{index}"
                    return await self.process_template_comprehensive(
                        template_data, request_id, batch_options
                    )
            
            # Create tasks for all templates
            tasks = [
                process_single_template(template, i) 
                for i, template in enumerate(templates)
            ]
            
            # Execute batch processing
            start_time = time.time()
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            batch_time = time.time() - start_time
            
            # Process results
            successful_count = 0
            failed_count = 0
            
            for i, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    results.append({
                        "success": False,
                        "error": str(result),
                        "index": i,
                        "request_id": f"{batch_id}_item_{i}",
                        "service": "JFA"
                    })
                    failed_count += 1
                else:
                    results.append(result)
                    if result.get("success", False):
                        successful_count += 1
                    else:
                        failed_count += 1
            
            # Create batch summary
            batch_summary = {
                "batch_id": batch_id,
                "total_templates": len(templates),
                "successful_count": successful_count,
                "failed_count": failed_count,
                "batch_processing_time": batch_time,
                "average_processing_time": batch_time / len(templates),
                "results": results,
                "timestamp": datetime.now().isoformat()
            }
            
            self.logger.info(f"Batch {batch_id} completed: {successful_count} successful, {failed_count} failed")
            
            return batch_summary
            
        except Exception as e:
            self.logger.error(f"Error in batch processing: {e}")
            return {
                "success": False,
                "error": f"Batch processing error: {str(e)}",
                "batch_id": batch_id,
                "timestamp": datetime.now().isoformat()
            }
    
    async def get_jfa_service_status(self) -> Dict[str, Any]:
        """Get comprehensive JFA service status."""
        try:
            # Get service status
            async with self.http_session.get(
                f"{self.jfa_config['base_url']}/status"
            ) as response:
                if response.status == 200:
                    status_data = await response.json()
                    
                    # Update cached status
                    self.jfa_status.update({
                        "service_available": True,
                        "last_health_check": datetime.now(),
                        "service_version": status_data.get("version", "unknown"),
                        "modules_status": status_data.get("modules", {}),
                        "performance_data": status_data.get("processing_metrics", {})
                    })
                    
                    return {
                        "success": True,
                        "jfa_status": status_data,
                        "connection_status": self.stats["connection_status"],
                        "jfaim_stats": self.stats,
                        "timestamp": datetime.now().isoformat()
                    }
                else:
                    return {
                        "success": False,
                        "error": f"JFA status check failed: {response.status}",
                        "timestamp": datetime.now().isoformat()
                    }
                    
        except Exception as e:
            return {
                "success": False,
                "error": f"JFA status check error: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
    
    async def _health_monitoring_loop(self):
        """Continuous health monitoring loop."""
        while self.is_active:
            try:
                # Check JFA service health
                health_result = await self._check_jfa_health()
                
                if health_result["healthy"]:
                    self.stats["connection_status"] = "connected"
                    self.stats["health_status"] = "healthy"
                else:
                    self.stats["connection_status"] = "disconnected"
                    self.stats["health_status"] = "unhealthy"
                    self.logger.warning(f"JFA service unhealthy: {health_result.get('error', 'Unknown error')}")
                
                # Update connection retry count
                if health_result["healthy"]:
                    self.connection_retry_count = 0
                else:
                    self.connection_retry_count += 1
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                self.logger.error(f"Error in health monitoring: {e}")
                await asyncio.sleep(30)
    
    async def _check_jfa_health(self) -> Dict[str, Any]:
        """Check JFA service health."""
        try:
            async with self.http_session.get(
                f"{self.jfa_config['base_url']}/health",
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    health_data = await response.json()
                    return {
                        "healthy": True,
                        "data": health_data,
                        "timestamp": datetime.now().isoformat()
                    }
                else:
                    return {
                        "healthy": False,
                        "error": f"Health check failed: {response.status}",
                        "timestamp": datetime.now().isoformat()
                    }
                    
        except Exception as e:
            return {
                "healthy": False,
                "error": f"Health check error: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
    
    async def _websocket_connection_loop(self):
        """Maintain WebSocket connection to JFA service."""
        while self.is_active:
            try:
                if not self.websocket_connection or self.websocket_connection.closed:
                    await self._connect_websocket()
                
                # Handle incoming messages
                if self.websocket_connection and not self.websocket_connection.closed:
                    try:
                        message = await asyncio.wait_for(
                            self.websocket_connection.recv(), 
                            timeout=1.0
                        )
                        await self._handle_websocket_message(message)
                    except asyncio.TimeoutError:
                        continue
                    except websockets.exceptions.ConnectionClosed:
                        self.logger.info("WebSocket connection closed")
                        self.websocket_connection = None
                
                await asyncio.sleep(1)
                
            except Exception as e:
                self.logger.error(f"Error in WebSocket loop: {e}")
                await asyncio.sleep(5)
    
    async def _connect_websocket(self):
        """Connect to JFA WebSocket."""
        try:
            self.websocket_connection = await websockets.connect(
                f"{self.jfa_config['websocket_url']}/jfaim",
                timeout=10
            )
            
            # Send registration message
            registration = {
                "type": "client_registration",
                "client": "CCU_JFAIM",
                "version": "1.0.0",
                "capabilities": ["template_processing", "batch_processing", "monitoring"],
                "timestamp": datetime.now().isoformat()
            }
            
            await self.websocket_connection.send(json.dumps(registration))
            self.logger.info("WebSocket connection established with JFA")
            
        except Exception as e:
            self.logger.error(f"WebSocket connection failed: {e}")
            self.websocket_connection = None
    
    async def _handle_websocket_message(self, message: str):
        """Handle incoming WebSocket messages."""
        try:
            data = json.loads(message)
            message_type = data.get("type", "unknown")
            
            if message_type == "status_update":
                await self._handle_status_update(data)
            elif message_type == "processing_complete":
                await self._handle_processing_complete(data)
            elif message_type == "error_notification":
                await self._handle_error_notification(data)
            
        except Exception as e:
            self.logger.error(f"Error handling WebSocket message: {e}")
    
    async def _handle_status_update(self, data: Dict[str, Any]):
        """Handle status update from JFA."""
        try:
            # Update JFA status
            self.jfa_status.update(data.get("status", {}))
            
        except Exception as e:
            self.logger.error(f"Error handling status update: {e}")
    
    async def _handle_processing_complete(self, data: Dict[str, Any]):
        """Handle processing completion notification."""
        try:
            request_id = data.get("request_id")
            if request_id in self.active_requests:
                self.active_requests[request_id]["status"] = "completed"
            
        except Exception as e:
            self.logger.error(f"Error handling processing complete: {e}")
    
    async def _handle_error_notification(self, data: Dict[str, Any]):
        """Handle error notification from JFA."""
        try:
            error_info = data.get("error", {})
            self.logger.error(f"JFA error notification: {error_info}")
            
        except Exception as e:
            self.logger.error(f"Error handling error notification: {e}")
    
    async def _request_processing_loop(self):
        """Process queued requests."""
        while self.is_active:
            try:
                # Process queued requests
                if not self.request_queue.empty():
                    request = await self.request_queue.get()
                    await self._process_queued_request(request)
                
                await asyncio.sleep(0.1)
                
            except Exception as e:
                self.logger.error(f"Error in request processing loop: {e}")
                await asyncio.sleep(1)
    
    async def _process_queued_request(self, request: Dict[str, Any]):
        """Process a queued request."""
        try:
            # Implementation for queued request processing
            pass
            
        except Exception as e:
            self.logger.error(f"Error processing queued request: {e}")
    
    async def _statistics_update_loop(self):
        """Update statistics periodically."""
        while self.is_active:
            try:
                # Update performance metrics
                await self._update_statistics()
                
                await asyncio.sleep(60)  # Update every minute
                
            except Exception as e:
                self.logger.error(f"Error updating statistics: {e}")
                await asyncio.sleep(60)
    
    async def _update_statistics(self):
        """Update internal statistics."""
        try:
            # Calculate rates and averages
            if self.stats["total_requests"] > 0:
                self.stats["validation_success_rate"] = (
                    self.stats["successful_requests"] / self.stats["total_requests"]
                )
            
            # Update performance metrics
            self.stats["performance_metrics"].update({
                "active_requests": len(self.active_requests),
                "queue_size": self.request_queue.qsize(),
                "connection_retries": self.connection_retry_count,
                "last_updated": datetime.now().isoformat()
            })
            
        except Exception as e:
            self.logger.error(f"Error updating statistics: {e}")
    
    async def _initial_health_check(self):
        """Perform initial health check."""
        try:
            health_result = await self._check_jfa_health()
            
            if health_result["healthy"]:
                self.logger.info("JFA service is healthy and ready")
                self.stats["connection_status"] = "connected"
                self.stats["health_status"] = "healthy"
            else:
                self.logger.warning("JFA service is not healthy")
                self.stats["connection_status"] = "disconnected"
                self.stats["health_status"] = "unhealthy"
                
        except Exception as e:
            self.logger.error(f"Initial health check failed: {e}")
    
    def _update_success_rate(self):
        """Update success rate calculation."""
        try:
            if self.stats["total_requests"] > 0:
                self.stats["validation_success_rate"] = (
                    self.stats["successful_requests"] / self.stats["total_requests"]
                )
                
        except Exception as e:
            self.logger.error(f"Error updating success rate: {e}")
    
    def _update_performance_metrics(self, processing_time: float):
        """Update performance metrics."""
        try:
            # Update average processing time
            total_requests = self.stats["total_requests"]
            current_avg = self.stats["average_processing_time"]
            
            self.stats["average_processing_time"] = (
                (current_avg * (total_requests - 1) + processing_time) / total_requests
            )
            
            # Update performance metrics
            self.stats["performance_metrics"]["avg_response_time"] = self.stats["average_processing_time"]
            self.stats["performance_metrics"]["error_rate"] = (
                self.stats["failed_requests"] / self.stats["total_requests"]
            )
            
        except Exception as e:
            self.logger.error(f"Error updating performance metrics: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of the enhanced JFAIM."""
        return {
            "module": self.module_name,
            "is_active": self.is_active,
            "jfa_config": self.jfa_config,
            "processing_config": self.processing_config,
            "statistics": self.stats,
            "jfa_service_status": self.jfa_status,
            "active_requests": len(self.active_requests),
            "connection_retry_count": self.connection_retry_count,
            "timestamp": datetime.now().isoformat()
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check of the enhanced JFAIM."""
        try:
            # Check JFA service availability
            jfa_health = await self._check_jfa_health()
            
            # Check WebSocket connection
            websocket_healthy = (
                self.websocket_connection is not None and 
                not self.websocket_connection.closed
            )
            
            return {
                "healthy": self.is_active and jfa_health["healthy"],
                "module": self.module_name,
                "jfa_service_healthy": jfa_health["healthy"],
                "websocket_connected": websocket_healthy,
                "statistics": self.stats,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "healthy": False,
                "module": self.module_name,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    # Legacy compatibility methods
    async def process_jfa_template(self, template_data: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """Legacy template processing method."""
        return await self.process_template_comprehensive(template_data, request_id)
    
    async def send_to_jfa_microservice(self, template_data: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """Legacy microservice communication method."""
        return await self.process_template_comprehensive(template_data, request_id)
    
    async def process_complete_jfa_workflow(self, template_data: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """Legacy complete workflow method."""
        return await self.process_template_comprehensive(template_data, request_id)
    
    async def get_invalid_data_recognition(self, jfa_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract invalid data recognition information from JFA response.
        
        Args:
            jfa_response: Response from JFA service containing validation analysis
            
        Returns:
            Invalid data recognition data or empty dict if not available
        """
        try:
            if not jfa_response.get("success", False) and jfa_response.get("recognition_available", False):
                validation_analysis = jfa_response.get("validation_analysis", {})
                invalid_recognition = validation_analysis.get("invalid_data_recognition", {})
                
                if invalid_recognition:
                    self.logger.info(f"JFAIM: Extracted invalid data recognition for request {invalid_recognition.get('request_id', 'unknown')}")
                    return invalid_recognition
            
            return {}
            
        except Exception as e:
            self.logger.error(f"Error extracting invalid data recognition: {e}")
            return {}
    
    async def get_insufficient_data_recognition(self, jfa_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract insufficient data recognition information from JFA response.
        
        Args:
            jfa_response: Response from JFA service containing validation analysis
            
        Returns:
            Insufficient data recognition data or empty dict if not available
        """
        try:
            if not jfa_response.get("success", False) and jfa_response.get("recognition_available", False):
                validation_analysis = jfa_response.get("validation_analysis", {})
                insufficient_recognition = validation_analysis.get("insufficient_data_recognition", {})
                
                if insufficient_recognition:
                    self.logger.info(f"JFAIM: Extracted insufficient data recognition for request {insufficient_recognition.get('request_id', 'unknown')}")
                    return insufficient_recognition
            
            return {}
            
        except Exception as e:
            self.logger.error(f"Error extracting insufficient data recognition: {e}")
            return {} 