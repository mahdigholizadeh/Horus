"""
FastAPI Integration Module (FAIM)

Provides RESTful API endpoints for managing and monitoring the RCM service.
Includes endpoints for health checks, status monitoring, metrics, commands, and logs.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import json
from pathlib import Path
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn

from EMM.emm import ErrorManagementModule
from EMM.api_error_handler import api_error_handler

# Import other modules for status checking
try:
    from GIDVM.gidvm import gidvm
    from PBRPM.pbrpm import pbrpm
    from AACM.aacm import aacm
    from FBWM.fbwm import fbwm
    from FDM.fdm import fdm
    from PRM.prm import prm
    from RTRMM.rtrmm import rtrmm
    from RLM.rlm import rlm
    from MMM.mmm import mmm
    from DRM.drm import drm
    from BTM.btm import btm
    from IFCM.ifcm import ifcm
    from ECM.ecm import ecm
    from AAAIM.aaaim import aaaim
    from BAAIM.baaim import baaim
    from SAAIM.saaim import saaim
    from SODVM.sodvm import sodvm
    from DCMM.dcmm import dcmm
    from TMM.tmm import tmm
    from EMM.emm import emm
    from MSM.msm import msm
    from SMSM.smsm import smsm
    from SMCM.smcm import smcm
    from JFAIM.jfaim import jfaim
    from OCMIM.ocmim import ocmim
except ImportError:
    # Handle case where modules are not yet implemented
    pass

class CommandRequest(BaseModel):
    """Model for command requests."""
    command: str
    parameters: Optional[Dict[str, Any]] = None

class ModuleStatus(BaseModel):
    """Model for module status responses."""
    module_name: str
    status: str
    details: Optional[Dict[str, Any]] = None

class FastAPIIntegrationModule:
    """
    FastAPI Integration Module (FAIM)
    
    Provides RESTful API endpoints for:
    - Health checks and status monitoring
    - Metrics and performance data
    - Command execution
    - Module status queries
    - Log retrieval and management
    """
    
    def __init__(self):
        """Initialize the FAIM module."""
        self.logger = logging.getLogger(__name__)
        self.error_manager = ErrorManagementModule()
        self.app = FastAPI(
            title="RCM FastAPI Integration Module",
            description="RESTful API endpoints for RCM service management",
            version="1.0.0"
        )
        
        # Error codes for this module (Module code: 0C for FAIM)
        # Error codes now generated dynamically by EMM
        
        # Register endpoints
        self._register_endpoints()
        
        # Statistics
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "last_activity": None
        }
    
    def _register_endpoints(self):
        """Register all FastAPI endpoints."""
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint."""
            try:
                self.stats["total_requests"] += 1
                self.stats["successful_requests"] += 1
                self.stats["last_activity"] = datetime.now().isoformat()
                
                return {
                    "status": "healthy",
                    "timestamp": datetime.now().isoformat(),
                    "service": "RCM FastAPI Integration Module"
                }
            except Exception as e:
                self.stats["failed_requests"] += 1
                error_msg = f"Health check failed: {e}"
                self.error_manager.log_error_with_generation("FAIM", "UnknownClass", "UnknownFunction", error_msg)
                raise HTTPException(status_code=500, detail=error_msg)
        
        @self.app.get("/status")
        async def get_status():
            """Get overall service status."""
            try:
                self.stats["total_requests"] += 1
                self.stats["successful_requests"] += 1
                self.stats["last_activity"] = datetime.now().isoformat()
                
                # Get status from all available modules
                module_statuses = {}
                
                # Try to get status from each module
                modules = {
                    "gidvm": "GIDVM",
                    "pbrpm": "PBRPM", 
                    "aacm": "AACM",
                    "fbwm": "FBWM",
                    "fdm": "FDM",
                    "prm": "PRM",
                    "rtrmm": "RTRMM",
                    "rlm": "RLM",
                    "mmm": "MMM",
                    "drm": "DRM",
                    "btm": "BTM",
                    "ifcm": "IFCM",
                    "ecm": "ECM",
                    "aaaim": "AAAIM",
                    "baaim": "BAAIM",
                    "saaim": "SAAIM",
                    "sodvm": "SODVM",
                    "dcmm": "DCMM",
                    "tmm": "TMM",
                    "emm": "EMM",
                    "msm": "MSM",
                    "smsm": "SMSM",
                    "smcm": "SMCM",
                    "jfaim": "JFAIM",
                    "ocmim": "OCMIM"
                }
                
                for module_var, module_name in modules.items():
                    try:
                        if module_var in globals():
                            module_instance = globals()[module_var]
                            if hasattr(module_instance, 'get_module_status'):
                                module_statuses[module_name] = module_instance.get_module_status()
                            elif hasattr(module_instance, 'get_status'):
                                module_statuses[module_name] = module_instance.get_status()
                            else:
                                module_statuses[module_name] = {"status": "unknown"}
                        else:
                            module_statuses[module_name] = {"status": "not_implemented"}
                    except Exception as e:
                        module_statuses[module_name] = {"status": "error", "error": str(e)}
                
                return {
                    "service": "RCM Microservice",
                    "timestamp": datetime.now().isoformat(),
                    "overall_status": "active",
                    "module_statuses": module_statuses,
                    "api_stats": self.stats.copy()
                }
                
            except Exception as e:
                self.stats["failed_requests"] += 1
                error_msg = f"Status check failed: {e}"
                self.error_manager.log_error_with_generation("FAIM", "UnknownClass", "UnknownFunction", error_msg)
                raise HTTPException(status_code=500, detail=error_msg)
        
        @self.app.get("/metrics")
        async def get_metrics():
            """Get performance metrics."""
            try:
                self.stats["total_requests"] += 1
                self.stats["successful_requests"] += 1
                self.stats["last_activity"] = datetime.now().isoformat()
                
                # Get metrics from MSM if available
                metrics = {
                    "timestamp": datetime.now().isoformat(),
                    "api_requests": self.stats.copy(),
                    "system_metrics": {}
                }
                
                try:
                    if 'msm' in globals() and hasattr(globals()['msm'], 'get_metrics'):
                        metrics["system_metrics"] = globals()['msm'].get_metrics()
                except Exception as e:
                    metrics["system_metrics"] = {"error": str(e)}
                
                return metrics
                
            except Exception as e:
                self.stats["failed_requests"] += 1
                error_msg = f"Metrics retrieval failed: {e}"
                self.error_manager.log_error_with_generation("FAIM", "UnknownClass", "UnknownFunction", error_msg)
                raise HTTPException(status_code=500, detail=error_msg)
        
        @self.app.post("/command")
        async def execute_command(command_request: CommandRequest):
            """Execute a command."""
            try:
                self.stats["total_requests"] += 1
                self.stats["successful_requests"] += 1
                self.stats["last_activity"] = datetime.now().isoformat()
                
                command = command_request.command
                parameters = command_request.parameters or {}
                
                # Route command to appropriate module
                result = await self._execute_command(command, parameters)
                
                return {
                    "command": command,
                    "parameters": parameters,
                    "result": result,
                    "timestamp": datetime.now().isoformat()
                }
                
            except Exception as e:
                self.stats["failed_requests"] += 1
                error_msg = f"Command execution failed: {e}"
                self.error_manager.log_error_with_generation("FAIM", "UnknownClass", "UnknownFunction", error_msg)
                raise HTTPException(status_code=500, detail=error_msg)
        
        @self.app.get("/module/{module_name}")
        async def get_module_status(module_name: str):
            """Get status of a specific module."""
            try:
                self.stats["total_requests"] += 1
                self.stats["successful_requests"] += 1
                self.stats["last_activity"] = datetime.now().isoformat()
                
                module_status = await self._get_module_status(module_name)
                
                return {
                    "module_name": module_name,
                    "status": module_status,
                    "timestamp": datetime.now().isoformat()
                }
                
            except Exception as e:
                self.stats["failed_requests"] += 1
                error_msg = f"Module status check failed: {e}"
                self.error_manager.log_error_with_generation("FAIM", "UnknownClass", "UnknownFunction", error_msg)
                raise HTTPException(status_code=404, detail=error_msg)
        
        @self.app.get("/logs")
        async def get_logs(level: str = "INFO", limit: int = 100):
            """Get recent logs."""
            try:
                self.stats["total_requests"] += 1
                self.stats["successful_requests"] += 1
                self.stats["last_activity"] = datetime.now().isoformat()
                
                # This would integrate with the logging system
                # For now, return a placeholder
                logs = [
                    {
                        "timestamp": datetime.now().isoformat(),
                        "level": "INFO",
                        "message": "FAIM endpoint accessed",
                        "module": "FAIM"
                    }
                ]
                
                return {
                    "logs": logs[:limit],
                    "total_logs": len(logs),
                    "level": level
                }
                
            except Exception as e:
                self.stats["failed_requests"] += 1
                error_msg = f"Log retrieval failed: {e}"
                self.error_manager.log_error_with_generation("FAIM", "UnknownClass", "UnknownFunction", error_msg)
                raise HTTPException(status_code=500, detail=error_msg)
    
    async def _execute_command(self, command: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a command by routing to appropriate module."""
        try:
            # Route commands to appropriate modules
            if command.startswith("module_"):
                # Module-specific commands
                module_name = command.split("_")[1]
                return await self._execute_module_command(module_name, parameters)
            elif command.startswith("system_"):
                # System-level commands
                return await self._execute_system_command(command, parameters)
            else:
                # General commands
                return await self._execute_general_command(command, parameters)
                
        except Exception as e:
            error_msg = f"Command execution failed: {e}"
            self.error_manager.log_error_with_generation("FAIM", "UnknownClass", "UnknownFunction", error_msg)
            raise
    
    async def _execute_module_command(self, module_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a module-specific command."""
        try:
            # Try to find the module instance
            module_instance = None
            for var_name, var_value in globals().items():
                if var_name.lower() == module_name.lower():
                    module_instance = var_value
                    break
            
            if module_instance is None:
                raise ValueError(f"Module {module_name} not found")
            
            # Execute command based on parameters
            if "action" in parameters:
                action = parameters["action"]
                if hasattr(module_instance, action):
                    method = getattr(module_instance, action)
                    if callable(method):
                        result = method(**parameters.get("args", {}))
                        return {"success": True, "result": result}
                    else:
                        raise ValueError(f"{action} is not callable")
                else:
                    raise ValueError(f"Action {action} not found in module {module_name}")
            else:
                # Default to getting status
                if hasattr(module_instance, 'get_module_status'):
                    return {"success": True, "result": module_instance.get_module_status()}
                elif hasattr(module_instance, 'get_status'):
                    return {"success": True, "result": module_instance.get_status()}
                else:
                    return {"success": True, "result": {"status": "unknown"}}
                    
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _execute_system_command(self, command: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a system-level command."""
        try:
            if command == "system_restart":
                # This would trigger a system restart
                return {"success": True, "message": "System restart initiated"}
            elif command == "system_status":
                # Get overall system status
                return {"success": True, "status": "active"}
            else:
                return {"success": False, "error": f"Unknown system command: {command}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _execute_general_command(self, command: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a general command."""
        try:
            if command == "ping":
                return {"success": True, "message": "pong"}
            elif command == "version":
                return {"success": True, "version": "1.0.0"}
            else:
                return {"success": False, "error": f"Unknown command: {command}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _get_module_status(self, module_name: str) -> Dict[str, Any]:
        """Get status of a specific module."""
        try:
            # Try to find the module instance
            module_instance = None
            for var_name, var_value in globals().items():
                if var_name.lower() == module_name.lower():
                    module_instance = var_value
                    break
            
            if module_instance is None:
                raise ValueError(f"Module {module_name} not found")
            
            # Get status from module
            if hasattr(module_instance, 'get_module_status'):
                return module_instance.get_module_status()
            elif hasattr(module_instance, 'get_status'):
                return module_instance.get_status()
            else:
                return {"status": "unknown", "message": "Module does not provide status"}
                
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def get_module_status(self) -> Dict[str, Any]:
        """Get FAIM module status."""
        return {
            "module": "FAIM",
            "status": "active",
            "endpoints": [
                "/health",
                "/status", 
                "/metrics",
                "/command",
                "/module/{module_name}",
                "/logs"
            ],
            "stats": self.stats.copy(),
            "last_activity": self.stats["last_activity"]
        }
    
    def run_server(self, host: str = "0.0.0.0", port: int = 8000):
        """Run the FastAPI server."""
        try:
            uvicorn.run(self.app, host=host, port=port)
        except Exception as e:
            error_msg = f"Failed to start FAIM server: {e}"
            self.error_manager.log_error_with_generation("FAIM", "UnknownClass", "UnknownFunction", error_msg)
            raise

    async def handle_api_error(self, error: Exception, context: str = "unknown") -> dict:
        return api_error_handler.handle_error(error, context, "FAIM")

# Global instances
faim = FastAPIIntegrationModule()
FAIM = FastAPIIntegrationModule()
