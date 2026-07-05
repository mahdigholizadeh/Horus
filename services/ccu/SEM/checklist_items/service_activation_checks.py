"""
Service Activation Checker - SEM Checklist Item

Handles controlled sequential activation of all Horus microservices.
Ensures proper startup order and validates each service comes online correctly.
"""

import asyncio
import logging
import subprocess
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ServiceActivationResult:
    """Result of service activation attempt."""
    service_name: str
    success: bool
    message: str
    duration_seconds: float
    process_id: Optional[int] = None
    port_status: Optional[Dict[str, bool]] = None


class ServiceActivationChecker:
    """Handles controlled activation of all Horus microservices."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the service activation checker."""
        self.logger = logging.getLogger(f'{__name__}.ServiceActivationChecker')
        self.config = config
        
        # Service configuration mapping
        self.service_configs = {
            "RLA": {
                "path": self._get_service_path("RLA"),
                "main_file": "rla_main.py",
                "ports": [8080, 8081],  # HTTP and admin ports
                "dependencies": [],
                "startup_timeout": 30
            },
            "RCM": {
                "path": self._get_service_path("RCM"),
                "main_file": "RCM_main.py",
                "ports": [8082],
                "dependencies": [],
                "startup_timeout": 45
            },
            "TPP": {
                "path": self._get_service_path("TPP"),
                "main_file": "tpp_main.py",
                "ports": [8083],
                "dependencies": ["RLA"],
                "startup_timeout": 30
            },
            "TD": {
                "path": self._get_service_path("TD"),
                "main_file": "td_main.py",
                "ports": [8084],
                "dependencies": ["RCM"],
                "startup_timeout": 30
            },
            "JFA": {
                "path": self._get_service_path("JFA"),
                "main_file": "JFA_main.py",
                "ports": [8085],
                "dependencies": ["TD"],
                "startup_timeout": 30
            },
            "OCM": {
                "path": self._get_service_path("OCM"),
                "main_file": "ocm.py",
                "ports": [8086, 8087],  # HTTP and admin ports
                "dependencies": ["JFA"],
                "startup_timeout": 30
            },
            "CCU": {
                "path": self._get_service_path("CCU"),
                "main_file": "ccu.py",
                "ports": [8088, 8089],  # HTTP and admin ports
                "dependencies": ["RLA", "RCM", "TPP", "TD", "JFA", "OCM"],
                "startup_timeout": 60
            }
        }
        
        self.logger.info("ServiceActivationChecker initialized")
    
    def _get_service_path(self, service_name: str) -> str:
        """Get the path for a specific service."""
        # This would use PMM path management in real implementation
        base_path = "/path/to/horus/services"
        service_paths = {
            "RLA": f"{base_path}/RLA/RLA_Main/RLA/RLA",
            "RCM": f"{base_path}/RCM/RCM_main/RCM_main/RCM_main",
            "TPP": f"{base_path}/TPP/TPP_Main/TPP/TPP",
            "TD": f"{base_path}/TD/TD_main/TDblock/TDblock",
            "JFA": f"{base_path}/JFA/JFA_main/JFA_Main/JFA_Main",
            "OCM": f"{base_path}/OCM/OCM_MAIN/ocm/ocm",
            "CCU": f"{base_path}/CCU/ccu_main/ccu/ccu"
        }
        return service_paths.get(service_name, "")
    
    async def activate_service(self, service_name: str) -> ServiceActivationResult:
        """
        Activate a specific service with proper validation.
        
        Args:
            service_name: Name of the service to activate
            
        Returns:
            ServiceActivationResult with activation details
        """
        start_time = time.time()
        self.logger.info(f"🔄 Activating service: {service_name}")
        
        try:
            service_config = self.service_configs.get(service_name)
            if not service_config:
                raise Exception(f"Unknown service: {service_name}")
            
            # Check dependencies first
            deps_ready = await self._check_service_dependencies(service_name)
            if not deps_ready:
                raise Exception(f"Dependencies not ready for {service_name}")
            
            # Check if service is already running
            if await self._is_service_running(service_name):
                self.logger.info(f"Service {service_name} is already running")
                return ServiceActivationResult(
                    service_name=service_name,
                    success=True,
                    message=f"{service_name} already running",
                    duration_seconds=time.time() - start_time
                )
            
            # Start the service
            process_id = await self._start_service_process(service_name, service_config)
            
            # Wait for service to be ready
            await self._wait_for_service_ready(service_name, service_config)
            
            # Validate ports are listening
            port_status = await self._check_service_ports(service_name, service_config['ports'])
            
            duration = time.time() - start_time
            
            result = ServiceActivationResult(
                service_name=service_name,
                success=True,
                message=f"{service_name} activated successfully",
                duration_seconds=duration,
                process_id=process_id,
                port_status=port_status
            )
            
            self.logger.info(f"✅ Service {service_name} activated in {duration:.2f}s")
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"Failed to activate {service_name}: {e}"
            self.logger.error(f"❌ {error_msg}")
            
            return ServiceActivationResult(
                service_name=service_name,
                success=False,
                message=error_msg,
                duration_seconds=duration
            )
    
    async def stop_service(self, service_name: str) -> ServiceActivationResult:
        """
        Stop a specific service gracefully.
        
        Args:
            service_name: Name of the service to stop
            
        Returns:
            ServiceActivationResult with stop details
        """
        start_time = time.time()
        self.logger.info(f"⏹️ Stopping service: {service_name}")
        
        try:
            # Find process
            process_id = await self._find_service_process(service_name)
            if not process_id:
                return ServiceActivationResult(
                    service_name=service_name,
                    success=True,
                    message=f"{service_name} was not running",
                    duration_seconds=time.time() - start_time
                )
            
            # Send graceful shutdown signal
            await self._graceful_shutdown(service_name, process_id)
            
            # Wait for process to stop
            await self._wait_for_service_stop(service_name, process_id)
            
            duration = time.time() - start_time
            
            result = ServiceActivationResult(
                service_name=service_name,
                success=True,
                message=f"{service_name} stopped successfully",
                duration_seconds=duration,
                process_id=process_id
            )
            
            self.logger.info(f"✅ Service {service_name} stopped in {duration:.2f}s")
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"Failed to stop {service_name}: {e}"
            self.logger.error(f"❌ {error_msg}")
            
            return ServiceActivationResult(
                service_name=service_name,
                success=False,
                message=error_msg,
                duration_seconds=duration
            )
    
    async def _check_service_dependencies(self, service_name: str) -> bool:
        """Check if service dependencies are ready."""
        service_config = self.service_configs[service_name]
        dependencies = service_config.get('dependencies', [])
        
        for dep_service in dependencies:
            if not await self._is_service_ready(dep_service):
                self.logger.warning(f"Dependency {dep_service} not ready for {service_name}")
                return False
        
        return True
    
    async def _is_service_running(self, service_name: str) -> bool:
        """Check if a service is currently running."""
        try:
            # Check process by name pattern
            result = await asyncio.create_subprocess_exec(
                'pgrep', '-f', f'{service_name.lower()}_main',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await result.communicate()
            return len(stdout.decode().strip()) > 0
        except Exception:
            return False
    
    async def _is_service_ready(self, service_name: str) -> bool:
        """Check if a service is ready to accept requests."""
        if not await self._is_service_running(service_name):
            return False
        
        # Check if ports are responding
        service_config = self.service_configs.get(service_name, {})
        ports = service_config.get('ports', [])
        
        for port in ports:
            if not await self._is_port_listening(port):
                return False
        
        return True
    
    async def _start_service_process(self, service_name: str, service_config: Dict[str, Any]) -> int:
        """Start the service process."""
        service_path = service_config['path']
        main_file = service_config['main_file']
        
        # Change to service directory and start
        full_command = f"cd {service_path} && python {main_file}"
        
        # Start process in background
        process = await asyncio.create_subprocess_shell(
            full_command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            start_new_session=True
        )
        
        self.logger.info(f"Started {service_name} process with PID: {process.pid}")
        return process.pid
    
    async def _wait_for_service_ready(self, service_name: str, service_config: Dict[str, Any]):
        """Wait for service to be ready."""
        timeout = service_config.get('startup_timeout', 30)
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if await self._is_service_ready(service_name):
                return True
            await asyncio.sleep(1)
        
        raise Exception(f"Service {service_name} did not become ready within {timeout}s")
    
    async def _check_service_ports(self, service_name: str, ports: List[int]) -> Dict[str, bool]:
        """Check if service ports are listening."""
        port_status = {}
        
        for port in ports:
            is_listening = await self._is_port_listening(port)
            port_status[str(port)] = is_listening
            if is_listening:
                self.logger.info(f"✅ {service_name} port {port} is listening")
            else:
                self.logger.warning(f"⚠️ {service_name} port {port} is not listening")
        
        return port_status
    
    async def _is_port_listening(self, port: int) -> bool:
        """Check if a port is listening."""
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection('localhost', port),
                timeout=5.0
            )
            writer.close()
            await writer.wait_closed()
            return True
        except Exception:
            return False
    
    async def _find_service_process(self, service_name: str) -> Optional[int]:
        """Find the process ID of a running service."""
        try:
            result = await asyncio.create_subprocess_exec(
                'pgrep', '-f', f'{service_name.lower()}_main',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await result.communicate()
            pids = stdout.decode().strip().split('\n')
            return int(pids[0]) if pids and pids[0] else None
        except Exception:
            return None
    
    async def _graceful_shutdown(self, service_name: str, process_id: int):
        """Send graceful shutdown signal to service."""
        try:
            # Send SIGTERM for graceful shutdown
            import signal
            import os
            os.kill(process_id, signal.SIGTERM)
            self.logger.info(f"Sent SIGTERM to {service_name} (PID: {process_id})")
        except Exception as e:
            self.logger.warning(f"Failed to send graceful shutdown to {service_name}: {e}")
    
    async def _wait_for_service_stop(self, service_name: str, process_id: int, timeout: int = 30):
        """Wait for service process to stop."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                import os
                os.kill(process_id, 0)  # Check if process exists
                await asyncio.sleep(1)
            except OSError:
                # Process doesn't exist anymore
                self.logger.info(f"Process {process_id} ({service_name}) has stopped")
                return
        
        # Force kill if still running
        try:
            import signal
            import os
            os.kill(process_id, signal.SIGKILL)
            self.logger.warning(f"Force killed {service_name} (PID: {process_id})")
        except OSError:
            pass  # Process already stopped
    
    def get_service_status(self, service_name: str) -> Dict[str, Any]:
        """Get current status of a service."""
        return {
            "service_name": service_name,
            "configured": service_name in self.service_configs,
            "config": self.service_configs.get(service_name, {}),
        }