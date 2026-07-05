"""
Systemd Integration Module - SEM Component

Handles systemd service management integration for Horus.
Provides support for standard systemctl commands (start, stop, restart, enable, disable).
"""

import asyncio
import logging
import os
import subprocess
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


def _resolve_horus_root() -> Path:
    """Resolve project root from HORUS_ROOT env or file location."""
    env_root = os.environ.get("HORUS_ROOT")
    if env_root:
        return Path(env_root).resolve()
    return Path(__file__).resolve().parents[3]


class SystemdServiceState(Enum):
    """Enumeration for systemd service states."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ACTIVATING = "activating"
    DEACTIVATING = "deactivating"
    FAILED = "failed"
    UNKNOWN = "unknown"


@dataclass
class SystemdServiceInfo:
    """Information about a systemd service."""
    service_name: str
    state: SystemdServiceState
    enabled: bool
    pid: Optional[int] = None
    memory_usage: Optional[str] = None
    cpu_usage: Optional[str] = None
    uptime: Optional[str] = None
    last_started: Optional[datetime] = None


class SystemdIntegrator:
    """Handles systemd service management for Horus."""
    
    def __init__(self):
        """Initialize the systemd integrator."""
        self.logger = logging.getLogger(f'{__name__}.SystemdIntegrator')
        self.service_name = "horusd"
        self.service_file_path = "/etc/systemd/system/horusd.service"
        self.horus_root = _resolve_horus_root()
        root = self.horus_root

        self.service_file_template = f"""[Unit]
Description=Horus - Distributed AI Orchestration Platform
After=network.target
Wants=network.target

[Service]
Type=simple
User=root
Group=root
WorkingDirectory={root}
ExecStart=/usr/bin/python3 {root / 'horus_startup.py'} --start
ExecStop=/usr/bin/python3 {root / 'horus_startup.py'} --stop
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=horusd

Environment=PYTHONPATH={root}
Environment=HORUS_ROOT={root}
Environment=HORUS_ENV=production

NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths={root / 'logs'}
ReadWritePaths={root / 'temp'}
ReadWritePaths={root / 'cache'}
ReadWritePaths={root / 'output'}

LimitNOFILE=65536
MemoryMax=8G
CPUQuota=400%

[Install]
WantedBy=multi-user.target
"""
        
        self.logger.info("SystemdIntegrator initialized")
    
    async def install_service(self) -> bool:
        """
        Install the Horus systemd service file.
        
        Returns:
            True if installation successful, False otherwise
        """
        try:
            self.logger.info("Installing Horus systemd service...")
            
            # Write service file
            with open(self.service_file_path, 'w') as f:
                f.write(self.service_file_template)
            
            # Reload systemd daemon
            result = await self._run_systemctl_command("daemon-reload")
            if not result:
                return False
            
            self.logger.info("✅ Horus systemd service installed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to install systemd service: {e}")
            return False
    
    async def enable_service(self) -> bool:
        """
        Enable the Horus service for auto-start.
        
        Returns:
            True if enable successful, False otherwise
        """
        try:
            self.logger.info("Enabling Horus service...")
            
            result = await self._run_systemctl_command("enable", self.service_name)
            
            if result:
                self.logger.info("✅ Horus service enabled for auto-start")
            else:
                self.logger.error("❌ Failed to enable Horus service")
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Error enabling service: {e}")
            return False
    
    async def disable_service(self) -> bool:
        """
        Disable the Horus service auto-start.
        
        Returns:
            True if disable successful, False otherwise
        """
        try:
            self.logger.info("Disabling Horus service...")
            
            result = await self._run_systemctl_command("disable", self.service_name)
            
            if result:
                self.logger.info("✅ Horus service disabled")
            else:
                self.logger.error("❌ Failed to disable Horus service")
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Error disabling service: {e}")
            return False
    
    async def start_service(self) -> bool:
        """
        Start the Horus service.
        
        Returns:
            True if start successful, False otherwise
        """
        try:
            self.logger.info("Starting Horus service...")
            
            result = await self._run_systemctl_command("start", self.service_name)
            
            if result:
                self.logger.info("✅ Horus service started")
                # Wait a moment for service to initialize
                await asyncio.sleep(2)
            else:
                self.logger.error("❌ Failed to start Horus service")
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Error starting service: {e}")
            return False
    
    async def stop_service(self) -> bool:
        """
        Stop the Horus service.
        
        Returns:
            True if stop successful, False otherwise
        """
        try:
            self.logger.info("Stopping Horus service...")
            
            result = await self._run_systemctl_command("stop", self.service_name)
            
            if result:
                self.logger.info("✅ Horus service stopped")
            else:
                self.logger.error("❌ Failed to stop Horus service")
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Error stopping service: {e}")
            return False
    
    async def restart_service(self) -> bool:
        """
        Restart the Horus service.
        
        Returns:
            True if restart successful, False otherwise
        """
        try:
            self.logger.info("Restarting Horus service...")
            
            result = await self._run_systemctl_command("restart", self.service_name)
            
            if result:
                self.logger.info("✅ Horus service restarted")
                # Wait a moment for service to initialize
                await asyncio.sleep(3)
            else:
                self.logger.error("❌ Failed to restart Horus service")
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Error restarting service: {e}")
            return False
    
    async def get_service_status(self) -> SystemdServiceInfo:
        """
        Get detailed status information about the Horus service.
        
        Returns:
            SystemdServiceInfo with current service status
        """
        try:
            # Get basic status
            process = await asyncio.create_subprocess_exec(
                'systemctl', 'status', self.service_name, '--no-pager',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            # Parse systemctl status output
            status_output = stdout.decode()
            
            # Determine state
            if "Active: active (running)" in status_output:
                state = SystemdServiceState.ACTIVE
            elif "Active: inactive" in status_output:
                state = SystemdServiceState.INACTIVE
            elif "Active: activating" in status_output:
                state = SystemdServiceState.ACTIVATING
            elif "Active: deactivating" in status_output:
                state = SystemdServiceState.DEACTIVATING
            elif "Active: failed" in status_output:
                state = SystemdServiceState.FAILED
            else:
                state = SystemdServiceState.UNKNOWN
            
            # Check if enabled
            enabled = await self._is_service_enabled()
            
            # Extract PID if running
            pid = None
            if state == SystemdServiceState.ACTIVE:
                pid = await self._extract_pid_from_status(status_output)
            
            # Get resource usage if running
            memory_usage = None
            cpu_usage = None
            if pid:
                memory_usage, cpu_usage = await self._get_resource_usage(pid)
            
            return SystemdServiceInfo(
                service_name=self.service_name,
                state=state,
                enabled=enabled,
                pid=pid,
                memory_usage=memory_usage,
                cpu_usage=cpu_usage,
                uptime=await self._get_service_uptime(status_output) if state == SystemdServiceState.ACTIVE else None
            )
            
        except Exception as e:
            self.logger.error(f"❌ Error getting service status: {e}")
            return SystemdServiceInfo(
                service_name=self.service_name,
                state=SystemdServiceState.UNKNOWN,
                enabled=False
            )
    
    async def update_service_status(self, status: str) -> bool:
        """
        Update the service status (used by SEM).
        
        Args:
            status: Status to set (active, failed, etc.)
            
        Returns:
            True if update successful, False otherwise
        """
        try:
            # This is called by SEM to update service status
            # In a real implementation, this might update service metadata
            self.logger.info(f"Service status updated to: {status}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error updating service status: {e}")
            return False
    
    async def get_service_logs(self, lines: int = 50) -> List[str]:
        """
        Get recent service logs.
        
        Args:
            lines: Number of log lines to retrieve
            
        Returns:
            List of log lines
        """
        try:
            process = await asyncio.create_subprocess_exec(
                'journalctl', '-u', self.service_name, '-n', str(lines), '--no-pager',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                log_lines = stdout.decode().strip().split('\n')
                return log_lines
            else:
                self.logger.warning(f"Failed to get service logs: {stderr.decode()}")
                return []
                
        except Exception as e:
            self.logger.error(f"❌ Error getting service logs: {e}")
            return []
    
    async def _run_systemctl_command(self, command: str, service: str = None) -> bool:
        """
        Run a systemctl command.
        
        Args:
            command: Systemctl command (start, stop, enable, etc.)
            service: Service name (optional)
            
        Returns:
            True if command successful, False otherwise
        """
        try:
            cmd_args = ['systemctl', command]
            if service:
                cmd_args.append(service)
            
            process = await asyncio.create_subprocess_exec(
                *cmd_args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                return True
            else:
                error_msg = stderr.decode().strip()
                self.logger.error(f"systemctl {command} failed: {error_msg}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Error running systemctl {command}: {e}")
            return False
    
    async def _is_service_enabled(self) -> bool:
        """Check if service is enabled for auto-start."""
        try:
            process = await asyncio.create_subprocess_exec(
                'systemctl', 'is-enabled', self.service_name,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            return process.returncode == 0 and "enabled" in stdout.decode()
            
        except Exception:
            return False
    
    async def _extract_pid_from_status(self, status_output: str) -> Optional[int]:
        """Extract PID from systemctl status output."""
        try:
            lines = status_output.split('\n')
            for line in lines:
                if "Main PID:" in line:
                    pid_part = line.split("Main PID:")[1].strip()
                    pid_str = pid_part.split()[0]
                    return int(pid_str)
            return None
        except Exception:
            return None
    
    async def _get_resource_usage(self, pid: int) -> tuple[Optional[str], Optional[str]]:
        """Get memory and CPU usage for a process."""
        try:
            # Get memory usage
            process = await asyncio.create_subprocess_exec(
                'ps', '-p', str(pid), '-o', 'rss=',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await process.communicate()
            
            if process.returncode == 0:
                memory_kb = int(stdout.decode().strip())
                memory_mb = memory_kb / 1024
                memory_usage = f"{memory_mb:.1f}MB"
            else:
                memory_usage = None
            
            # Get CPU usage (simplified)
            process = await asyncio.create_subprocess_exec(
                'ps', '-p', str(pid), '-o', 'pcpu=',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await process.communicate()
            
            if process.returncode == 0:
                cpu_percent = float(stdout.decode().strip())
                cpu_usage = f"{cpu_percent:.1f}%"
            else:
                cpu_usage = None
            
            return memory_usage, cpu_usage
            
        except Exception:
            return None, None
    
    async def _get_service_uptime(self, status_output: str) -> Optional[str]:
        """Extract service uptime from status output."""
        try:
            lines = status_output.split('\n')
            for line in lines:
                if "Active:" in line and "since" in line:
                    # Extract timestamp and calculate uptime
                    since_part = line.split("since")[1].strip()
                    # Simplified uptime extraction
                    return since_part.split(';')[0].strip()
            return None
        except Exception:
            return None
    
    def generate_service_file(self, config: Dict[str, Any]) -> str:
        """
        Generate customized systemd service file based on configuration.
        
        Args:
            config: Horus configuration
            
        Returns:
            Service file content as string
        """
        # Customize service file based on config
        service_content = self.service_file_template
        
        # Customize working directory if specified in config
        working_dir = config.get('ccu_setting', {}).get('system', {}).get('working_directory')
        if working_dir:
            service_content = service_content.replace(
                f'WorkingDirectory={self.horus_root}',
                f'WorkingDirectory={working_dir}'
            )
        
        # Customize memory limit if specified
        memory_limit = config.get('ccu_setting', {}).get('system', {}).get('memory_limit')
        if memory_limit:
            service_content = service_content.replace(
                'MemoryMax=8G',
                f'MemoryMax={memory_limit}'
            )
        
        # Customize CPU limit if specified
        cpu_limit = config.get('ccu_setting', {}).get('system', {}).get('cpu_limit')
        if cpu_limit:
            service_content = service_content.replace(
                'CPUQuota=400%',
                f'CPUQuota={cpu_limit}'
            )
        
        return service_content
    
    def get_systemd_summary(self) -> Dict[str, Any]:
        """
        Get summary of systemd integration capabilities.
        
        Returns:
            Summary dictionary
        """
        return {
            "service_name": self.service_name,
            "service_file_path": self.service_file_path,
            "supported_commands": [
                "start", "stop", "restart", "enable", "disable", "status"
            ],
            "features": [
                "Auto-restart on failure",
                "Resource limits",
                "Security hardening",
                "Journal logging",
                "Dependency management"
            ],
            "status": "ready"
        } 