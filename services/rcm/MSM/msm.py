"""
Monitoring System Module (MSM)

Gathers and reports monitoring data including module status, performance statistics, 
network traffic, and token usage. Polls all modules every 10 seconds or when CCU 
requests monitoring data through ECM.
"""

import asyncio
import json
import psutil
import time
import threading
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
from EMM.emm import ErrorManagementModule
from EMM.api_error_handler import api_error_handler
import math

class MonitoringSystemModule:
    """
    Monitoring System Module (MSM)
    
    Gathers and reports monitoring data including module status, performance statistics, 
    network traffic, and token usage. Polls all modules every 10 seconds or when CCU 
    requests monitoring data through ECM.
    """
    
    def __init__(self):
        """Initialize the Monitoring System Module."""
        self.error_manager = ErrorManagementModule()
        self.monitoring_interval = 10  # seconds
        self.is_monitoring = False
        self.monitoring_thread = None
        self.start_time = time.time()
        
        # Token tracking
        self.token_stats = {
            "input_tokens": 0,
            "output_tokens": 0,
            "system_tokens": 0,
            "total_tokens": 0,
            "last_reset": datetime.now().isoformat()
        }
        
        # Initialize monitoring data structure
        self.monitoring_data = {
            "timestamp": None,
            "system_info": {},
            "module_status": {},
            "resource_usage": {},
            "performance_metrics": {},
            "network_traffic": {},
            "token_usage": {}
        }
    
    def calculate_tokens(self, text: str) -> int:
        """
        Calculate tokens based on 4-character = 1 token approximation, using ceiling.
        
        Args:
            text: Text to calculate tokens for
            
        Returns:
            Number of tokens
        """
        if not text:
            return 0
        # 4 characters = 1 token, always round up
        return math.ceil(len(text) / 4)
    
    def extract_conversation_data(self) -> Dict[str, Any]:
        """
        Extract conversation data from databases.
        
        Returns:
            Dictionary containing conversation data and token counts
        """
        try:
            # Simulate database extraction
            conversation_data = {
                "total_conversations": 0,
                "active_conversations": 0,
                "total_messages": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "system_tokens": 0
            }
            
            # In a real implementation, this would query the database
            # For now, we'll simulate some data
            sample_conversations = [
                {"input": "Hello, how are you?", "output": "I'm doing well, thank you!", "system": "You are a helpful assistant."},
                {"input": "What's the weather like?", "output": "I don't have access to real-time weather data.", "system": "You are a helpful assistant."}
            ]
            
            for conv in sample_conversations:
                conversation_data["total_conversations"] += 1
                conversation_data["input_tokens"] += self.calculate_tokens(conv["input"])
                conversation_data["output_tokens"] += self.calculate_tokens(conv["output"])
                conversation_data["system_tokens"] += self.calculate_tokens(conv["system"])
                conversation_data["total_messages"] += 2  # input + output
            
            conversation_data["total_tokens"] = (
                conversation_data["input_tokens"] + 
                conversation_data["output_tokens"] + 
                conversation_data["system_tokens"]
            )
            
            return conversation_data
            
        except Exception as e:
            self.error_manager.log_error_with_generation(
                "MSM", "MonitoringSystemModule", "extract_conversation_data",
                f"Failed to extract conversation data: {str(e)}"
            )
            return {"error": str(e)}
    
    def gather_monitoring_data(self) -> Dict[str, Any]:
        """
        Gather comprehensive monitoring data from the system.
        
        Returns:
            Dictionary containing monitoring data
        """
        try:
            current_time = datetime.now()
            
            # System information
            system_info = {
                "platform": psutil.sys.platform,
                "python_version": psutil.sys.version,
                "cpu_count": psutil.cpu_count(),
                "memory_total": psutil.virtual_memory().total,
                "disk_total": psutil.disk_usage('/').total
            }
            
            # Resource usage
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            resource_usage = {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_used": memory.used,
                "memory_available": memory.available,
                "disk_percent": disk.percent,
                "disk_used": disk.used,
                "disk_free": disk.free
            }
            
            # Module status (simulated)
            module_status = {
                "EMM": {"status": "active", "last_activity": current_time.isoformat()},
                "MSM": {"status": "active", "last_activity": current_time.isoformat()},
                "RCM": {"status": "active", "last_activity": current_time.isoformat()},
                "TMM": {"status": "active", "last_activity": current_time.isoformat()},
                "DCMM": {"status": "active", "last_activity": current_time.isoformat()},
                "RLM": {"status": "active", "last_activity": current_time.isoformat()},
                "ECM": {"status": "active", "last_activity": current_time.isoformat()}
            }
            
            # Performance metrics
            performance_metrics = {
                "uptime": time.time() - self.start_time,
                "active_threads": threading.active_count(),
                "process_count": len(psutil.pids())
            }
            
            # Network traffic (simulated)
            network_traffic = {
                "bytes_sent": 0,
                "bytes_recv": 0,
                "packets_sent": 0,
                "packets_recv": 0,
                "connections": len(psutil.net_connections())
            }
            
            # Extract conversation data and calculate tokens
            conversation_data = self.extract_conversation_data()
            
            # Token usage
            token_usage = {
                "input_tokens": conversation_data.get("input_tokens", 0),
                "output_tokens": conversation_data.get("output_tokens", 0),
                "system_tokens": conversation_data.get("system_tokens", 0),
                "total_tokens": conversation_data.get("total_tokens", 0),
                "total_conversations": conversation_data.get("total_conversations", 0),
                "total_messages": conversation_data.get("total_messages", 0),
                "last_token_reset": current_time.isoformat()
            }
            
            # Update monitoring data
            self.monitoring_data = {
                "timestamp": current_time.isoformat(),
                "system_info": system_info,
                "module_status": module_status,
                "resource_usage": resource_usage,
                "performance_metrics": performance_metrics,
                "network_traffic": network_traffic,
                "token_usage": token_usage
            }
            
            return self.monitoring_data
            
        except Exception as e:
            error_code = self.error_manager.log_error_with_generation(
                "MSM", "MonitoringSystemModule", "gather_monitoring_data", 
                f"Failed to gather monitoring data: {str(e)}"
            )
            return {"error": str(e), "error_code": error_code}
    
    def get_monitoring(self) -> Dict[str, Any]:
        """
        Get current monitoring data for ECM.
        
        Returns:
            Dictionary containing current monitoring data
        """
        try:
            monitoring_data = self.gather_monitoring_data()
            return monitoring_data
        except Exception as e:
            self.error_manager.log_error_with_generation(
                "MSM", "MonitoringSystemModule", "get_monitoring",
                f"Failed to get monitoring data: {str(e)}"
            )
            return {"error": str(e)}
    
    def start_monitoring(self):
        """Start the monitoring loop."""
        self.is_monitoring = True
        self.start_time = time.time()
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop)
        self.monitoring_thread.daemon = True
        self.monitoring_thread.start()
        
        self.error_manager.log_error_with_generation(
            "MSM", "MonitoringSystemModule", "start_monitoring",
            "MSM monitoring started"
        )
    
    def stop_monitoring(self):
        """Stop the monitoring loop."""
        self.is_monitoring = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        
        self.error_manager.log_error_with_generation(
            "MSM", "MonitoringSystemModule", "stop_monitoring",
            "MSM monitoring stopped"
        )
    
    def _monitoring_loop(self):
        """Internal monitoring loop that runs every 10 seconds."""
        while self.is_monitoring:
            try:
                # Gather monitoring data
                monitoring_data = self.gather_monitoring_data()
                
                # Log monitoring activity (ECM will handle CCU communication)
                self.error_manager.log_error_with_generation(
                    "MSM", "MonitoringSystemModule", "_monitoring_loop",
                    f"Monitoring data gathered: {len(monitoring_data)} items"
                )
                
                # Wait for next interval
                time.sleep(self.monitoring_interval)
                
            except Exception as e:
                self.error_manager.log_error_with_generation(
                    "MSM", "MonitoringSystemModule", "_monitoring_loop",
                    f"Error in monitoring loop: {str(e)}"
                )
                time.sleep(self.monitoring_interval)
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the MSM module.
        
        Returns:
            Dictionary with module status
        """
        return {
            "module": "MSM",
            "status": "active" if self.is_monitoring else "inactive",
            "monitoring_interval": self.monitoring_interval,
            "start_time": self.start_time,
            "uptime": time.time() - self.start_time if self.start_time else 0,
            "last_activity": datetime.now().isoformat()
        }

    def log_error(self, error_message: str, class_name: str = "UnknownClass", function_name: str = "UnknownFunction", sub_function: str = "001"):
        """Log an error using EMM."""
        return self.error_manager.log_error_with_generation(
            "MSM", 
            class_name, 
            function_name, 
            error_message, 
            sub_function
        )
    
    def generate_error_code(self, class_name: str = "UnknownClass", function_name: str = "UnknownFunction", sub_function: str = "001") -> str:
        """Generate an error code using EMM."""
        return self.error_manager.generate_error_code("MSM", class_name, function_name, sub_function)
    
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
            result = await api_error_handler.handle_api_error(error_response, status_code, context)
            self.error_manager.log_error_with_generation(
                "MSM",
                "MSM",
                "handle_api_error",
                f"API Error: {result.get('api_error_type', 'unknown')}",
                context=result
            )
            await api_error_handler.send_error_report_to_ccu(result)
            return result
        except Exception as e:
            self.error_manager.log_error_with_generation(
                "MSM",
                "MSM",
                "handle_api_error",
                f"Error handling API error: {str(e)}"
            )
            return {"success": False, "error": str(e)}


# Global instance for ECM to access
msm = MonitoringSystemModule()
MSM = MonitoringSystemModule  # Class alias
