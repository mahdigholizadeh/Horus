"""
Monitoring System Module (MSM) for JFA Microservice

This module handles system monitoring:
- Performance monitoring and metrics
- Health tracking and reporting
- Resource utilization monitoring
- System alerts and notifications
"""

import logging
import asyncio
import psutil
from typing import Dict, Any
from datetime import datetime


class MonitoringSystemModule:
    """Monitoring System Module for JFA"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.module_name = "MSM"
        self.is_active = False
        
        self.metrics = {
            "cpu_usage": 0.0,
            "memory_usage": 0.0,
            "disk_usage": 0.0,
            "network_io": 0,
            "uptime": 0
        }
        
        self.stats = {
            "monitoring_cycles": 0,
            "alerts_triggered": 0,
            "last_monitoring": None
        }
        
        # Template processing metrics
        self.template_metrics = {
            "templates_processed": 0,
            "total_processing_time": 0.0,
            "average_processing_time": 0.0,
            "successful_processing": 0,
            "failed_processing": 0,
            "success_rate": 0.0,
            "processing_times": []
        }
    
    async def start(self):
        self.is_active = True
        self.logger.info(f"{self.module_name} started successfully")
    
    async def stop(self):
        self.is_active = False
        self.logger.info(f"{self.module_name} stopped successfully")
    
    async def start_monitoring(self):
        """Start system monitoring."""
        asyncio.create_task(self._monitoring_loop())
    
    async def _monitoring_loop(self):
        """Main monitoring loop."""
        while self.is_active:
            try:
                # Get system metrics
                self.metrics["cpu_usage"] = psutil.cpu_percent()
                self.metrics["memory_usage"] = psutil.virtual_memory().percent
                self.metrics["disk_usage"] = psutil.disk_usage('/').percent
                
                self.stats["monitoring_cycles"] += 1
                self.stats["last_monitoring"] = datetime.now()
                
                await asyncio.sleep(30)  # Monitor every 30 seconds
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(30)
    
    async def reset_metrics(self) -> Dict[str, Any]:
        """Reset all monitoring metrics."""
        try:
            self.metrics = {
                "cpu_usage": 0.0,
                "memory_usage": 0.0,
                "disk_usage": 0.0,
                "network_io": 0,
                "uptime": 0
            }
            
            self.stats = {
                "monitoring_cycles": 0,
                "alerts_triggered": 0,
                "last_monitoring": None
            }
            
            # Initialize template processing metrics
            self.template_metrics = {
                "templates_processed": 0,
                "total_processing_time": 0.0,
                "average_processing_time": 0.0,
                "successful_processing": 0,
                "failed_processing": 0,
                "success_rate": 0.0,
                "processing_times": []
            }
            
            return {
                "success": True,
                "message": "Metrics reset successfully",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def record_template_processed(self, template_id: str, processing_time: float, success: bool, size_bytes: int, error_message: str = None) -> Dict[str, Any]:
        """Record metrics for a processed template."""
        try:
            self.template_metrics["templates_processed"] += 1
            self.template_metrics["total_processing_time"] += processing_time
            self.template_metrics["processing_times"].append(processing_time)
            
            if success:
                self.template_metrics["successful_processing"] += 1
            else:
                self.template_metrics["failed_processing"] += 1
            
            # Calculate average processing time
            if self.template_metrics["templates_processed"] > 0:
                self.template_metrics["average_processing_time"] = (
                    self.template_metrics["total_processing_time"] / self.template_metrics["templates_processed"]
                )
            
            # Calculate success rate
            total_processed = self.template_metrics["successful_processing"] + self.template_metrics["failed_processing"]
            if total_processed > 0:
                self.template_metrics["success_rate"] = (
                    self.template_metrics["successful_processing"] / total_processed
                )
            
            return {
                "success": True,
                "template_id": template_id,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def get_monitoring_data(self) -> Dict[str, Any]:
        """Get current monitoring data."""
        try:
            # Update system metrics
            self.metrics["cpu_usage"] = psutil.cpu_percent()
            self.metrics["memory_usage"] = psutil.virtual_memory().percent
            self.metrics["disk_usage"] = psutil.disk_usage('/').percent
            
            return {
                **self.template_metrics,
                "system_metrics": self.metrics,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics."""
        try:
            # Calculate throughput (templates per second)
            throughput = 0.0
            if self.template_metrics["average_processing_time"] > 0:
                throughput = 1.0 / self.template_metrics["average_processing_time"]
            
            return {
                "throughput": throughput,
                "response_time": self.template_metrics["average_processing_time"],
                "error_rate": 1.0 - self.template_metrics["success_rate"],
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def export_metrics(self) -> Dict[str, Any]:
        """Export metrics to JSON format."""
        try:
            monitoring_data = await self.get_monitoring_data()
            performance_data = await self.get_performance_metrics()
            
            export_data = {
                "templates_processed": monitoring_data.get("templates_processed", 0),
                "monitoring_data": monitoring_data,
                "performance_data": performance_data,
                "export_timestamp": datetime.now().isoformat()
            }
            
            return {
                "success": True,
                "data": export_data,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def cleanup_old_metrics(self, days: int = 30) -> Dict[str, Any]:
        """Clean up old metrics data."""
        try:
            # In a real implementation, this would clean up old data
            # For now, just return success
            return {
                "success": True,
                "days_cleaned": days,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def get_status(self) -> Dict[str, Any]:
        return {
            "module": self.module_name,
            "is_active": self.is_active,
            "metrics": self.metrics,
            "statistics": self.stats,
            "timestamp": datetime.now().isoformat()
        }
    
    async def health_check(self) -> Dict[str, Any]:
        try:
            return {
                "healthy": self.is_active,
                "module": self.module_name,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "healthy": False,
                "module": self.module_name,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            } 