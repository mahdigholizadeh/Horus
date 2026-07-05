"""
MicroServices Monitoring Module (MSMM)

This module analyzes health data from other microservices and executes pre-defined
automated strategies to manage the service lifecycle autonomously. It implements
a Circuit Breaker pattern and provides fault tolerance capabilities.

Key Responsibilities:
- Monitor health of all dependent microservices (RLA, TPP, RCM, JFA, TD, OCM)
- Execute automated recovery strategies
- Implement Circuit Breaker pattern for failed services
- Provide health status reporting
- Manage service lifecycle (start, stop, restart, reset)
- Track service performance metrics
- Generate health alerts and notifications
"""

import asyncio
import logging
import json
import requests
import subprocess
import psutil
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum
from dataclasses import dataclass, asdict
import threading
import time
import socket
import websockets


class ServiceStatus(Enum):
    """Service status enumeration."""
    UNKNOWN = "unknown"
    STARTING = "starting"
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    MAINTENANCE = "maintenance"
    DEGRADED = "degraded"
    RECOVERING = "recovering"


class CircuitBreakerState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Service is failing, requests blocked
    HALF_OPEN = "half_open"  # Testing if service has recovered


@dataclass
class ServiceHealthMetrics:
    """Service health metrics."""
    service_name: str
    status: ServiceStatus
    last_check: datetime
    response_time: float
    error_count: int
    success_count: int
    uptime: float
    memory_usage: float
    cpu_usage: float
    active_connections: int
    last_error: Optional[str] = None
    circuit_breaker_state: CircuitBreakerState = CircuitBreakerState.CLOSED


@dataclass
class ServiceConfiguration:
    """Service configuration."""
    name: str
    host: str
    port: int
    health_endpoint: str
    protocol: str = "http"
    timeout: int = 30
    max_retries: int = 3
    retry_delay: int = 5
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: int = 60
    process_name: Optional[str] = None
    start_command: Optional[str] = None
    stop_command: Optional[str] = None
    restart_command: Optional[str] = None


class MicroServicesMonitoringModule:
    """
    MicroServices Monitoring Module (MSMM)
    
    Monitors and manages the health of all dependent microservices.
    """
    
    def __init__(self):
        """Initialize the MSMM module."""
        self.logger = logging.getLogger(__name__)
        
        # Service configurations
        self.services = {
            "RLA": ServiceConfiguration(
                name="RLA",
                host="localhost",
                port=3781,
                health_endpoint="/health",
                protocol="https",
                process_name="rla",
                start_command="python rla_main.py",
                stop_command="pkill -f rla_main.py",
                restart_command="python rla_main.py --restart"
            ),
            "TPP": ServiceConfiguration(
                name="TPP",
                host="localhost",
                port=8082,
                health_endpoint="/health",
                protocol="http",
                process_name="tpp",
                start_command="python tpp_main.py",
                stop_command="pkill -f tpp_main.py",
                restart_command="python tpp_main.py --restart"
            ),
            "RCM": ServiceConfiguration(
                name="RCM",
                host="localhost",
                port=8080,
                health_endpoint="/health",
                protocol="http",
                process_name="rcm",
                start_command="python RCM_main.py",
                stop_command="pkill -f RCM_main.py",
                restart_command="python RCM_main.py --restart"
            ),
            "JFA": ServiceConfiguration(
                name="JFA",
                host="localhost",
                port=8083,
                health_endpoint="/health",
                protocol="http",
                process_name="jfa",
                start_command="python jfa_main.py",
                stop_command="pkill -f jfa_main.py",
                restart_command="python jfa_main.py --restart"
            ),
            "TD": ServiceConfiguration(
                name="TD",
                host="localhost",
                port=8084,
                health_endpoint="/health",
                protocol="http",
                process_name="td",
                start_command="python td_main.py",
                stop_command="pkill -f td_main.py",
                restart_command="python td_main.py --restart"
            ),
            "OCM": ServiceConfiguration(
                name="OCM",
                host="localhost",
                port=8085,
                health_endpoint="/health",
                protocol="http",
                process_name="ocm",
                start_command="python ocm_main.py",
                stop_command="pkill -f ocm_main.py",
                restart_command="python ocm_main.py --restart"
            )
        }
        
        # Health metrics for each service
        self.health_metrics: Dict[str, ServiceHealthMetrics] = {}
        
        # Circuit breaker states
        self.circuit_breakers: Dict[str, Dict[str, Any]] = {}
        
        # Monitoring configuration
        self.health_check_interval = 30  # seconds
        self.recovery_timeout = 60  # seconds
        self.max_restart_attempts = 3
        
        # Monitoring state
        self.is_monitoring = False
        self.monitoring_task = None
        
        # Callbacks
        self.health_change_callbacks = []
        self.alert_callbacks = []
        
        # Statistics
        self.stats = {
            "total_health_checks": 0,
            "total_service_failures": 0,
            "total_recoveries": 0,
            "total_restarts": 0,
            "average_response_time": 0.0,
            "last_check": None
        }
        
        # Initialize health metrics and circuit breakers
        self.initialize_services()
        
        self.logger.info("MSMM module initialized")
    
    def initialize_services(self):
        """Initialize health metrics and circuit breakers for all services."""
        for service_name, config in self.services.items():
            self.health_metrics[service_name] = ServiceHealthMetrics(
                service_name=service_name,
                status=ServiceStatus.UNKNOWN,
                last_check=datetime.now(),
                response_time=0.0,
                error_count=0,
                success_count=0,
                uptime=0.0,
                memory_usage=0.0,
                cpu_usage=0.0,
                active_connections=0
            )
            
            self.circuit_breakers[service_name] = {
                "state": CircuitBreakerState.CLOSED,
                "failure_count": 0,
                "last_failure": None,
                "next_attempt": None
            }
    
    async def start(self):
        """Start the MSMM module."""
        try:
            self.logger.info("Starting MSMM module...")
            
            # Start monitoring
            self.is_monitoring = True
            self.monitoring_task = asyncio.create_task(self.monitor_services())
            
            # Start recovery tasks
            asyncio.create_task(self.recovery_manager())
            
            # Initial health check
            await self.check_all_services()
            
            self.logger.info("MSMM module started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start MSMM module: {e}")
            raise
    
    async def stop(self):
        """Stop the MSMM module."""
        try:
            self.logger.info("Stopping MSMM module...")
            
            # Stop monitoring
            self.is_monitoring = False
            if self.monitoring_task:
                self.monitoring_task.cancel()
                try:
                    await self.monitoring_task
                except asyncio.CancelledError:
                    pass
            
            self.logger.info("MSMM module stopped successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to stop MSMM module: {e}")
            raise
    
    async def monitor_services(self):
        """Main monitoring loop."""
        while self.is_monitoring:
            try:
                # Check all services
                await self.check_all_services()
                
                # Update statistics
                self.stats['last_check'] = datetime.now()
                
                # Sleep until next check
                await asyncio.sleep(self.health_check_interval)
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(self.health_check_interval)
    
    async def check_all_services(self) -> Dict[str, ServiceStatus]:
        """Check health of all services."""
        health_results = {}
        
        for service_name in self.services.keys():
            try:
                status = await self.check_service_health(service_name)
                health_results[service_name] = status
                
                # Notify callbacks if status changed
                old_status = self.health_metrics[service_name].status
                if status != old_status:
                    await self.notify_health_change_callbacks(service_name, old_status, status)
                
            except Exception as e:
                self.logger.error(f"Error checking {service_name} health: {e}")
                health_results[service_name] = ServiceStatus.ERROR
        
        return health_results
    
    async def check_service_health(self, service_name: str) -> ServiceStatus:
        """Check health of a specific service."""
        try:
            config = self.services[service_name]
            metrics = self.health_metrics[service_name]
            
            # Check circuit breaker state
            circuit_breaker = self.circuit_breakers[service_name]
            if circuit_breaker["state"] == CircuitBreakerState.OPEN:
                # Check if we should attempt recovery
                if (circuit_breaker["next_attempt"] and 
                    datetime.now() >= circuit_breaker["next_attempt"]):
                    circuit_breaker["state"] = CircuitBreakerState.HALF_OPEN
                    self.logger.info(f"Circuit breaker for {service_name} moved to HALF_OPEN")
                else:
                    # Service is still blocked
                    return ServiceStatus.ERROR
            
            # Perform health check
            start_time = time.time()
            
            # Check if process is running
            process_running = await self.is_process_running(service_name)
            if not process_running:
                metrics.status = ServiceStatus.INACTIVE
                await self.handle_service_failure(service_name, "Process not running")
                return ServiceStatus.INACTIVE
            
            # Check HTTP endpoint
            try:
                url = f"{config.protocol}://{config.host}:{config.port}{config.health_endpoint}"
                
                # Use aiohttp for async HTTP requests
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=config.timeout) as response:
                        response_time = time.time() - start_time
                        
                        if response.status == 200:
                            # Service is healthy
                            await self.handle_service_success(service_name, response_time)
                            
                            # Get additional metrics from response
                            try:
                                response_data = await response.json()
                                await self.update_service_metrics(service_name, response_data)
                            except:
                                pass  # Response may not be JSON
                            
                            return ServiceStatus.ACTIVE
                        else:
                            # Service returned error status
                            await self.handle_service_failure(service_name, f"HTTP {response.status}")
                            return ServiceStatus.ERROR
                            
            except asyncio.TimeoutError:
                await self.handle_service_failure(service_name, "Request timeout")
                return ServiceStatus.ERROR
            except Exception as e:
                await self.handle_service_failure(service_name, f"Connection error: {str(e)}")
                return ServiceStatus.ERROR
                
        except Exception as e:
            self.logger.error(f"Error checking {service_name} health: {e}")
            await self.handle_service_failure(service_name, f"Health check error: {str(e)}")
            return ServiceStatus.ERROR
    
    async def is_process_running(self, service_name: str) -> bool:
        """Check if service process is running."""
        try:
            config = self.services[service_name]
            if not config.process_name:
                return True  # Can't check process, assume running
            
            # Check if process is running
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    # Check process name or command line
                    if (config.process_name in proc.info['name'] or
                        any(config.process_name in arg for arg in proc.info['cmdline'])):
                        return True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking process for {service_name}: {e}")
            return False
    
    async def handle_service_success(self, service_name: str, response_time: float):
        """Handle successful service response."""
        metrics = self.health_metrics[service_name]
        circuit_breaker = self.circuit_breakers[service_name]
        
        # Update metrics
        metrics.status = ServiceStatus.ACTIVE
        metrics.last_check = datetime.now()
        metrics.response_time = response_time
        metrics.success_count += 1
        
        # Reset circuit breaker if it was open
        if circuit_breaker["state"] != CircuitBreakerState.CLOSED:
            circuit_breaker["state"] = CircuitBreakerState.CLOSED
            circuit_breaker["failure_count"] = 0
            circuit_breaker["last_failure"] = None
            circuit_breaker["next_attempt"] = None
            
            self.logger.info(f"Circuit breaker for {service_name} reset to CLOSED")
            
            # Notify recovery
            await self.notify_recovery(service_name)
    
    async def handle_service_failure(self, service_name: str, error: str):
        """Handle service failure."""
        metrics = self.health_metrics[service_name]
        circuit_breaker = self.circuit_breakers[service_name]
        
        # Update metrics
        metrics.status = ServiceStatus.ERROR
        metrics.last_check = datetime.now()
        metrics.error_count += 1
        metrics.last_error = error
        
        # Update circuit breaker
        circuit_breaker["failure_count"] += 1
        circuit_breaker["last_failure"] = datetime.now()
        
        # Check if we should open the circuit breaker
        config = self.services[service_name]
        if circuit_breaker["failure_count"] >= config.circuit_breaker_threshold:
            if circuit_breaker["state"] != CircuitBreakerState.OPEN:
                circuit_breaker["state"] = CircuitBreakerState.OPEN
                circuit_breaker["next_attempt"] = datetime.now() + timedelta(seconds=config.circuit_breaker_timeout)
                
                self.logger.warning(f"Circuit breaker for {service_name} opened due to {circuit_breaker['failure_count']} failures")
                
                # Notify failure
                await self.notify_service_failure(service_name, error)
        
        # Update statistics
        self.stats["total_service_failures"] += 1
        self.stats["total_health_checks"] += 1
    
    async def update_service_metrics(self, service_name: str, response_data: Dict[str, Any]):
        """Update service metrics from health check response."""
        try:
            metrics = self.health_metrics[service_name]
            
            # Update metrics if present in response
            if 'uptime' in response_data:
                metrics.uptime = response_data['uptime']
            
            if 'memory_usage' in response_data:
                metrics.memory_usage = response_data['memory_usage']
            
            if 'cpu_usage' in response_data:
                metrics.cpu_usage = response_data['cpu_usage']
            
            if 'active_connections' in response_data:
                metrics.active_connections = response_data['active_connections']
                
        except Exception as e:
            self.logger.error(f"Error updating metrics for {service_name}: {e}")
    
    async def recovery_manager(self):
        """Manage service recovery attempts."""
        while self.is_monitoring:
            try:
                for service_name, metrics in self.health_metrics.items():
                    if metrics.status == ServiceStatus.ERROR:
                        # Attempt recovery
                        await self.attempt_service_recovery(service_name)
                
                # Sleep before next recovery attempt
                await asyncio.sleep(self.recovery_timeout)
                
            except Exception as e:
                self.logger.error(f"Error in recovery manager: {e}")
                await asyncio.sleep(self.recovery_timeout)
    
    async def attempt_service_recovery(self, service_name: str):
        """Attempt to recover a failed service."""
        try:
            config = self.services[service_name]
            metrics = self.health_metrics[service_name]
            
            self.logger.info(f"Attempting recovery for {service_name}")
            
            # Try restart if we have restart attempts left
            if hasattr(metrics, 'restart_attempts'):
                restart_attempts = metrics.restart_attempts
            else:
                restart_attempts = 0
            
            if restart_attempts < self.max_restart_attempts:
                # Attempt service restart
                success = await self.restart_service(service_name)
                
                if success:
                    metrics.status = ServiceStatus.RECOVERING
                    self.stats["total_recoveries"] += 1
                    self.logger.info(f"Successfully initiated recovery for {service_name}")
                else:
                    metrics.restart_attempts = restart_attempts + 1
                    self.logger.warning(f"Failed to recover {service_name}, attempt {restart_attempts + 1}/{self.max_restart_attempts}")
            else:
                self.logger.error(f"Max restart attempts reached for {service_name}")
                metrics.status = ServiceStatus.INACTIVE
                
        except Exception as e:
            self.logger.error(f"Error attempting recovery for {service_name}: {e}")
    
    async def restart_service(self, service_name: str) -> bool:
        """Restart a service."""
        try:
            config = self.services[service_name]
            
            # Stop the service
            if config.stop_command:
                await self.execute_command(config.stop_command)
                await asyncio.sleep(5)  # Wait for graceful shutdown
            
            # Start the service
            if config.start_command:
                await self.execute_command(config.start_command)
                await asyncio.sleep(10)  # Wait for startup
                
                # Check if service is now running
                if await self.is_process_running(service_name):
                    self.stats["total_restarts"] += 1
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error restarting {service_name}: {e}")
            return False
    
    async def execute_command(self, command: str) -> bool:
        """Execute a system command."""
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                self.logger.info(f"Command executed successfully: {command}")
                return True
            else:
                self.logger.error(f"Command failed: {command}, stderr: {stderr.decode()}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error executing command {command}: {e}")
            return False
    
    # Callback methods
    async def notify_health_change_callbacks(self, service_name: str, old_status: ServiceStatus, new_status: ServiceStatus):
        """Notify health change callbacks."""
        for callback in self.health_change_callbacks:
            try:
                await callback(service_name, old_status, new_status)
            except Exception as e:
                self.logger.error(f"Error in health change callback: {e}")
    
    async def notify_service_failure(self, service_name: str, error: str):
        """Notify service failure."""
        alert = {
            'type': 'service_failure',
            'service': service_name,
            'error': error,
            'timestamp': datetime.now().isoformat(),
            'severity': 'high'
        }
        
        for callback in self.alert_callbacks:
            try:
                await callback(alert)
            except Exception as e:
                self.logger.error(f"Error in alert callback: {e}")
    
    async def notify_recovery(self, service_name: str):
        """Notify service recovery."""
        alert = {
            'type': 'service_recovery',
            'service': service_name,
            'timestamp': datetime.now().isoformat(),
            'severity': 'info'
        }
        
        for callback in self.alert_callbacks:
            try:
                await callback(alert)
            except Exception as e:
                self.logger.error(f"Error in alert callback: {e}")
    
    # Public API methods
    async def get_service_status(self, service_name: str) -> Optional[ServiceStatus]:
        """Get status of a specific service."""
        if service_name in self.health_metrics:
            return self.health_metrics[service_name].status
        return None
    
    async def get_all_service_status(self) -> Dict[str, ServiceStatus]:
        """Get status of all services."""
        return {name: metrics.status for name, metrics in self.health_metrics.items()}
    
    async def get_service_metrics(self, service_name: str) -> Optional[Dict[str, Any]]:
        """Get metrics for a specific service."""
        if service_name in self.health_metrics:
            metrics = self.health_metrics[service_name]
            return {
                'service_name': metrics.service_name,
                'status': metrics.status.value,
                'last_check': metrics.last_check.isoformat(),
                'response_time': metrics.response_time,
                'error_count': metrics.error_count,
                'success_count': metrics.success_count,
                'uptime': metrics.uptime,
                'memory_usage': metrics.memory_usage,
                'cpu_usage': metrics.cpu_usage,
                'active_connections': metrics.active_connections,
                'last_error': metrics.last_error,
                'circuit_breaker_state': metrics.circuit_breaker_state.value
            }
        return None
    
    async def get_all_service_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get metrics for all services."""
        result = {}
        for service_name in self.health_metrics.keys():
            metrics = await self.get_service_metrics(service_name)
            if metrics:
                result[service_name] = metrics
        return result
    
    async def force_restart_service(self, service_name: str) -> bool:
        """Force restart a service."""
        if service_name in self.services:
            return await self.restart_service(service_name)
        return False
    
    async def recover_service(self, service_name: str) -> bool:
        """Attempt to recover a specific service."""
        if service_name in self.services:
            await self.attempt_service_recovery(service_name)
            return True
        return False
    
    def register_health_change_callback(self, callback: Callable[[str, ServiceStatus, ServiceStatus], None]):
        """Register health change callback."""
        self.health_change_callbacks.append(callback)
    
    def register_alert_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """Register alert callback."""
        self.alert_callbacks.append(callback)
    
    def set_service_configuration(self, service_name: str, config: Dict[str, Any]):
        """Update service configuration."""
        if service_name in self.services:
            service_config = self.services[service_name]
            
            for key, value in config.items():
                if hasattr(service_config, key):
                    setattr(service_config, key, value)
            
            self.logger.info(f"Updated configuration for {service_name}: {config}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of the MSMM module."""
        return {
            'module': 'MSMM',
            'is_monitoring': self.is_monitoring,
            'services': {name: metrics.status.value for name, metrics in self.health_metrics.items()},
            'circuit_breakers': {name: breaker["state"].value for name, breaker in self.circuit_breakers.items()},
            'stats': self.stats
        } 