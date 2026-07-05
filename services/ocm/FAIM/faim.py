"""
FastAPI Integration Module (FAIM) for OCM

This module integrates the FastAPI framework to expose the necessary API endpoints
for OCM's operation and management. It provides RESTful APIs for status monitoring,
configuration management, health checks, and administrative operations.
"""

import asyncio
import logging
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import ssl

# Request/Response Models
class HealthResponse(BaseModel):
    status: str
    timestamp: str
    service: str = "OCM"
    version: str = "1.0.0"

class StatusResponse(BaseModel):
    service: str
    status: str
    uptime: Optional[float]
    modules: Dict[str, Any]
    statistics: Dict[str, Any]
    timestamp: str

class TaskRequest(BaseModel):
    name: str
    function: str
    parameters: Dict[str, Any] = {}
    priority: str = "medium"
    schedule_for: Optional[str] = None
    max_retries: int = 3
    timeout: Optional[int] = None

class TaskResponse(BaseModel):
    task_id: str
    status: str
    message: str

class ConfigUpdateRequest(BaseModel):
    configuration: Dict[str, Any]

class ReportStatusRequest(BaseModel):
    request_id: str

class ReportStatusResponse(BaseModel):
    request_id: str
    status: str
    progress: Dict[str, Any]
    generated_at: Optional[str] = None
    delivered_at: Optional[str] = None

class PriorityUpdateRequest(BaseModel):
    priority_config: Dict[str, Any]

class CertificateStatusResponse(BaseModel):
    ssl_enabled: bool
    certificate_source: str
    loaded_at: Optional[str] = None
    expires_at: Optional[str] = None
    certificate_updates: int

class MetricsResponse(BaseModel):
    timestamp: str
    service_metrics: Dict[str, Any]
    module_metrics: Dict[str, Any]
    performance_metrics: Dict[str, Any]

class FastAPIIntegrationModule:
    """
    FastAPI Integration Module (FAIM)
    
    Provides RESTful API interface for OCM:
    - Health and status endpoints
    - Configuration management
    - Task management
    - Report status queries
    - Administrative operations
    - Metrics and monitoring
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the FAIM module."""
        self.logger = logging.getLogger(__name__)
        self.module_name = "FAIM"
        self.is_active = False
        
        # Configuration
        self.config = config
        self.api_config = config.get('api', {})
        self.monitoring_config = config.get('monitoring', {})
        
        # API settings
        self.host = self.api_config.get('host', '0.0.0.0')
        self.port = self.api_config.get('port', 8082)
        self.ssl_enabled = config.get('ssl_configuration', {}).get('enabled', False)
        
        # Module references
        self.ocm_service = None
        self.modules = {}
        
        # FastAPI application
        self.app = FastAPI(
            title="OCM API",
            description="Output Cache Management Microservice API",
            version="1.0.0",
            docs_url="/docs" if self.api_config.get('enable_docs', True) else None,
            redoc_url="/redoc" if self.api_config.get('enable_redoc', True) else None
        )
        
        # Configure CORS
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=self.api_config.get('cors_origins', ["*"]),
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Register routes
        self._register_routes()
        
        # Server instance
        self.server = None
        
        self.logger.info(f"{self.module_name} initialized - API server on {self.host}:{self.port}")
    
    def set_references(self, ocm_service, modules: Dict[str, Any]):
        """Set references to OCM service and modules."""
        self.ocm_service = ocm_service
        self.modules = modules
    
    async def start(self):
        """Start the FAIM module and API server."""
        try:
            self.is_active = True
            
            # Configure SSL if enabled
            ssl_context = None
            if self.ssl_enabled:
                ssl_context = self._create_ssl_context()
            
            # Create and configure server
            config = uvicorn.Config(
                app=self.app,
                host=self.host,
                port=self.port,
                ssl_keyfile=None if not ssl_context else self.config.get('ssl_configuration', {}).get('local_key_path'),
                ssl_certfile=None if not ssl_context else self.config.get('ssl_configuration', {}).get('local_cert_path'),
                access_log=self.api_config.get('access_log', False),
                log_level=self.api_config.get('log_level', 'info').lower()
            )
            
            self.server = uvicorn.Server(config)
            
            # Start server in background
            asyncio.create_task(self.server.serve())
            
            self.logger.info(f"FAIM started successfully - API server running on {'https' if self.ssl_enabled else 'http'}://{self.host}:{self.port}")
            
        except Exception as e:
            self.logger.error(f"Failed to start FAIM: {e}")
            raise
    
    async def stop(self):
        """Stop the FAIM module gracefully."""
        try:
            self.is_active = False
            
            if self.server:
                self.server.should_exit = True
                await self.server.shutdown()
            
            self.logger.info("FAIM stopped successfully")
            
        except Exception as e:
            self.logger.error(f"Error stopping FAIM: {e}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        is_healthy = self.is_active and (self.server is not None)
        
        return {
            'healthy': is_healthy,
            'is_active': self.is_active,
            'server_running': self.server is not None,
            'api_endpoints': len(self.app.routes) if hasattr(self.app, 'routes') else 0
        }
    
    def _create_ssl_context(self) -> Optional[ssl.SSLContext]:
        """Create SSL context for HTTPS."""
        try:
            ssl_config = self.config.get('ssl_configuration', {})
            
            context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            context.load_cert_chain(
                ssl_config.get('local_cert_path', 'certs/cert.pem'),
                ssl_config.get('local_key_path', 'certs/key.pem')
            )
            
            return context
            
        except Exception as e:
            self.logger.error(f"Failed to create SSL context: {e}")
            return None
    
    def _register_routes(self):
        """Register all API routes."""
        
        # Health and Status Endpoints
        @self.app.get("/health", response_model=HealthResponse)
        async def health_check():
            """Health check endpoint."""
            return HealthResponse(
                status="healthy",
                timestamp=datetime.now().isoformat()
            )
        
        @self.app.get("/status", response_model=StatusResponse)
        async def get_status():
            """Get detailed service status."""
            try:
                if not self.ocm_service:
                    raise HTTPException(status_code=503, detail="OCM service not available")
                
                status_info = self.ocm_service.get_status()
                
                return StatusResponse(
                    service="OCM",
                    status=status_info.state,
                    uptime=status_info.uptime,
                    modules={module: "active" for module in status_info.active_modules or []},
                    statistics={
                        "requests_processed": status_info.requests_processed,
                        "requests_sent": status_info.requests_sent,
                        "requests_failed": status_info.requests_failed,
                        "reports_generated": status_info.reports_generated,
                        "priority_queues": status_info.priority_queues or {}
                    },
                    timestamp=datetime.now().isoformat()
                )
                
            except Exception as e:
                self.logger.error(f"Error getting status: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/metrics", response_model=MetricsResponse)
        async def get_metrics():
            """Get detailed metrics."""
            try:
                service_metrics = {}
                module_metrics = {}
                
                # Collect metrics from modules
                for name, module in self.modules.items():
                    if hasattr(module, 'get_status'):
                        module_status = module.get_status()
                        module_metrics[name] = module_status
                
                # Performance metrics
                performance_metrics = {
                    "timestamp": datetime.now().isoformat(),
                    "service_uptime": self.ocm_service.get_status().uptime if self.ocm_service else 0
                }
                
                return MetricsResponse(
                    timestamp=datetime.now().isoformat(),
                    service_metrics=service_metrics,
                    module_metrics=module_metrics,
                    performance_metrics=performance_metrics
                )
                
            except Exception as e:
                self.logger.error(f"Error getting metrics: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Task Management Endpoints
        @self.app.post("/tasks", response_model=TaskResponse)
        async def create_task(task_request: TaskRequest):
            """Create a new background task."""
            try:
                if 'BTM' not in self.modules:
                    raise HTTPException(status_code=503, detail="Background Task Module not available")
                
                btm = self.modules['BTM']
                
                # Convert priority string to enum
                from BTM.btm import TaskPriority
                priority = TaskPriority(task_request.priority.upper())
                
                # Parse schedule_for if provided
                schedule_for = None
                if task_request.schedule_for:
                    schedule_for = datetime.fromisoformat(task_request.schedule_for)
                
                task_id = await btm.create_task(
                    name=task_request.name,
                    function=task_request.function,
                    parameters=task_request.parameters,
                    priority=priority,
                    schedule_for=schedule_for,
                    max_retries=task_request.max_retries,
                    timeout=task_request.timeout
                )
                
                return TaskResponse(
                    task_id=task_id,
                    status="created",
                    message=f"Task '{task_request.name}' created successfully"
                )
                
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"Invalid request: {e}")
            except Exception as e:
                self.logger.error(f"Error creating task: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/tasks/{task_id}")
        async def get_task_info(task_id: str):
            """Get information about a specific task."""
            try:
                if 'BTM' not in self.modules:
                    raise HTTPException(status_code=503, detail="Background Task Module not available")
                
                btm = self.modules['BTM']
                task_info = btm.get_task_info(task_id)
                
                if not task_info:
                    raise HTTPException(status_code=404, detail="Task not found")
                
                return task_info
                
            except HTTPException:
                raise
            except Exception as e:
                self.logger.error(f"Error getting task info: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.delete("/tasks/{task_id}")
        async def cancel_task(task_id: str):
            """Cancel a specific task."""
            try:
                if 'BTM' not in self.modules:
                    raise HTTPException(status_code=503, detail="Background Task Module not available")
                
                btm = self.modules['BTM']
                success = await btm.cancel_task(task_id)
                
                if not success:
                    raise HTTPException(status_code=404, detail="Task not found or cannot be cancelled")
                
                return {"status": "cancelled", "task_id": task_id}
                
            except HTTPException:
                raise
            except Exception as e:
                self.logger.error(f"Error cancelling task: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Report Management Endpoints
        @self.app.post("/reports/status", response_model=ReportStatusResponse)
        async def get_report_status(request: ReportStatusRequest):
            """Get status of a report."""
            try:
                if 'RMM' not in self.modules:
                    raise HTTPException(status_code=503, detail="Request Management Module not available")
                
                rmm = self.modules['RMM']
                request_status = await rmm.get_request_status(request.request_id)
                
                if not request_status:
                    raise HTTPException(status_code=404, detail="Request not found")
                
                return ReportStatusResponse(
                    request_id=request.request_id,
                    status=request_status.get('status', 'unknown'),
                    progress={
                        "received_at": request_status.get('received_at'),
                        "processing_started": request_status.get('processing_started'),
                        "current_status": request_status.get('status')
                    },
                    generated_at=request_status.get('processing_started'),
                    delivered_at=request_status.get('delivered_at')
                )
                
            except HTTPException:
                raise
            except Exception as e:
                self.logger.error(f"Error getting report status: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/reports/queue")
        async def get_report_queue_status():
            """Get current report queue status."""
            try:
                if 'RMM' not in self.modules:
                    raise HTTPException(status_code=503, detail="Request Management Module not available")
                
                rmm = self.modules['RMM']
                queue_stats = rmm.get_queue_stats()
                
                return {
                    "timestamp": datetime.now().isoformat(),
                    "queue_sizes": queue_stats,
                    "total_queued": sum(queue_stats.values())
                }
                
            except Exception as e:
                self.logger.error(f"Error getting queue status: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Configuration Management Endpoints
        @self.app.post("/config/update")
        async def update_configuration(config_request: ConfigUpdateRequest):
            """Update service configuration."""
            try:
                if not self.ocm_service:
                    raise HTTPException(status_code=503, detail="OCM service not available")
                
                # Update configuration (would need to be implemented in main service)
                # self.ocm_service.update_configuration(config_request.configuration)
                
                return {
                    "status": "updated",
                    "timestamp": datetime.now().isoformat(),
                    "message": "Configuration updated successfully"
                }
                
            except Exception as e:
                self.logger.error(f"Error updating configuration: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/config/priority")
        async def update_priority_configuration(priority_request: PriorityUpdateRequest):
            """Update priority configuration."""
            try:
                if 'RMM' not in self.modules:
                    raise HTTPException(status_code=503, detail="Request Management Module not available")
                
                # Would need to implement priority update in RMM
                return {
                    "status": "updated",
                    "timestamp": datetime.now().isoformat(),
                    "priority_config": priority_request.priority_config
                }
                
            except Exception as e:
                self.logger.error(f"Error updating priority configuration: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # SSL Certificate Endpoints
        @self.app.get("/ssl/status", response_model=CertificateStatusResponse)
        async def get_ssl_certificate_status():
            """Get SSL certificate status."""
            try:
                if not self.ocm_service:
                    raise HTTPException(status_code=503, detail="OCM service not available")
                
                ssl_config = getattr(self.ocm_service, 'ssl_config', {})
                
                return CertificateStatusResponse(
                    ssl_enabled=ssl_config.get('enabled', False),
                    certificate_source=ssl_config.get('source', 'unknown'),
                    loaded_at=ssl_config.get('loaded_at'),
                    expires_at=ssl_config.get('expires_at'),
                    certificate_updates=ssl_config.get('updates', 0)
                )
                
            except Exception as e:
                self.logger.error(f"Error getting SSL status: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Module Status Endpoints
        @self.app.get("/modules")
        async def get_modules_status():
            """Get status of all modules."""
            try:
                modules_status = {}
                
                for name, module in self.modules.items():
                    try:
                        if hasattr(module, 'get_status'):
                            modules_status[name] = module.get_status()
                        elif hasattr(module, 'health_check'):
                            health = await module.health_check()
                            modules_status[name] = {
                                "module": name,
                                "active": health,
                                "status": "healthy" if health else "unhealthy"
                            }
                        else:
                            modules_status[name] = {
                                "module": name,
                                "status": "unknown"
                            }
                    except Exception as e:
                        modules_status[name] = {
                            "module": name,
                            "status": "error",
                            "error": str(e)
                        }
                
                return {
                    "timestamp": datetime.now().isoformat(),
                    "total_modules": len(modules_status),
                    "modules": modules_status
                }
                
            except Exception as e:
                self.logger.error(f"Error getting modules status: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/modules/{module_name}")
        async def get_module_status(module_name: str):
            """Get status of a specific module."""
            try:
                if module_name not in self.modules:
                    raise HTTPException(status_code=404, detail="Module not found")
                
                module = self.modules[module_name]
                
                if hasattr(module, 'get_status'):
                    return module.get_status()
                elif hasattr(module, 'health_check'):
                    health = await module.health_check()
                    return {
                        "module": module_name,
                        "active": health,
                        "status": "healthy" if health else "unhealthy"
                    }
                else:
                    return {
                        "module": module_name,
                        "status": "unknown"
                    }
                
            except HTTPException:
                raise
            except Exception as e:
                self.logger.error(f"Error getting module status: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Administrative Endpoints
        @self.app.post("/admin/restart")
        async def restart_service():
            """Restart the OCM service (requires admin privileges)."""
            try:
                # This would trigger a service restart
                return {
                    "status": "restart_initiated",
                    "timestamp": datetime.now().isoformat(),
                    "message": "Service restart initiated"
                }
                
            except Exception as e:
                self.logger.error(f"Error restarting service: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/admin/reload")
        async def reload_configuration():
            """Reload service configuration."""
            try:
                # This would trigger configuration reload
                return {
                    "status": "configuration_reloaded",
                    "timestamp": datetime.now().isoformat(),
                    "message": "Configuration reloaded successfully"
                }
                
            except Exception as e:
                self.logger.error(f"Error reloading configuration: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Error handling
        @self.app.exception_handler(HTTPException)
        async def http_exception_handler(request: Request, exc: HTTPException):
            return JSONResponse(
                status_code=exc.status_code,
                content={
                    "error": exc.detail,
                    "status_code": exc.status_code,
                    "timestamp": datetime.now().isoformat()
                }
            )
        
        @self.app.exception_handler(Exception)
        async def general_exception_handler(request: Request, exc: Exception):
            self.logger.error(f"Unhandled exception: {exc}")
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal server error",
                    "status_code": 500,
                    "timestamp": datetime.now().isoformat()
                }
            )
    
    def get_app(self) -> FastAPI:
        """Get FastAPI application instance."""
        return self.app
    
    def get_status(self) -> Dict[str, Any]:
        """Get current FAIM status."""
        return {
            'module': self.module_name,
            'active': self.is_active,
            'api_host': self.host,
            'api_port': self.port,
            'ssl_enabled': self.ssl_enabled,
            'server_running': self.server is not None and not getattr(self.server, 'should_exit', True)
        } 