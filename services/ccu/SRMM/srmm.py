"""
Server Resources Monitor Module (SRMM)

This module continuously monitors critical system resources including RAM usage, 
CPU load, disk space, and network connectivity. It provides real-time data to 
other modules and implements backpressure mechanisms when resource utilization 
exceeds predefined thresholds.

Key Responsibilities:
- Monitor RAM, CPU, disk, and network resources
- Detect resource threshold breaches
- Implement backpressure mechanisms
- Provide real-time resource metrics
- Generate alerts and notifications
- Historical resource usage tracking
"""

import asyncio
import logging
import psutil
import json
import sqlite3
import socket
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum
from dataclasses import dataclass, asdict
import threading
import time
import requests


class ResourceStatus(Enum):
    """Resource status levels."""
    NORMAL = "normal"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class BackpressureLevel(Enum):
    """Backpressure levels."""
    NONE = "none"
    LIGHT = "light"
    MODERATE = "moderate"
    HEAVY = "heavy"
    MAXIMUM = "maximum"


@dataclass
class ResourceMetrics:
    """Resource metrics data structure."""
    timestamp: datetime
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    network_connectivity: bool
    network_latency: float
    active_connections: int
    load_average: List[float]
    available_memory: int
    total_memory: int
    disk_io_read: int
    disk_io_write: int
    network_bytes_sent: int
    network_bytes_recv: int


@dataclass
class ResourceThresholds:
    """Resource threshold configuration."""
    cpu_warning: float = 70.0
    cpu_critical: float = 90.0
    memory_warning: float = 70.0
    memory_critical: float = 90.0
    disk_warning: float = 80.0
    disk_critical: float = 95.0
    network_timeout: float = 5.0
    max_connections: int = 1000


class ServerResourcesMonitorModule:
    """
    Server Resources Monitor Module (SRMM)
    
    Monitors system resources and implements backpressure mechanisms.
    """
    
    def __init__(self):
        """Initialize the SRMM module."""
        self.logger = logging.getLogger(__name__)
        
        # Configuration
        self.thresholds = ResourceThresholds()
        self.monitoring_interval = 10  # seconds
        self.history_retention_days = 7
        
        # Current metrics
        self.current_metrics: Optional[ResourceMetrics] = None
        self.resource_status = ResourceStatus.NORMAL
        self.backpressure_level = BackpressureLevel.NONE
        
        # Database for historical data
        self.db_path = Path("srmm_metrics.db")
        self.init_database()
        
        # Monitoring state
        self.is_monitoring = False
        self.monitoring_task = None
        
        # Callbacks
        self.threshold_callbacks = []
        self.metrics_callbacks = []
        
        # Statistics
        self.stats = {
            "total_measurements": 0,
            "warning_count": 0,
            "critical_count": 0,
            "backpressure_activations": 0,
            "average_cpu_usage": 0.0,
            "average_memory_usage": 0.0,
            "peak_cpu_usage": 0.0,
            "peak_memory_usage": 0.0,
            "uptime": 0
        }
        
        # Network monitoring
        self.network_test_hosts = [
            "8.8.8.8",  # Google DNS
            "1.1.1.1",  # Cloudflare DNS
            "208.67.222.222"  # OpenDNS
        ]
        
        # Baseline metrics for comparison
        self.baseline_metrics = None
        
        self.logger.info("SRMM module initialized")
    
    def init_database(self):
        """Initialize the metrics database."""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            # Create metrics table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS resource_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    cpu_usage REAL NOT NULL,
                    memory_usage REAL NOT NULL,
                    disk_usage REAL NOT NULL,
                    network_connectivity BOOLEAN NOT NULL,
                    network_latency REAL,
                    active_connections INTEGER,
                    load_average_1m REAL,
                    load_average_5m REAL,
                    load_average_15m REAL,
                    available_memory INTEGER,
                    total_memory INTEGER,
                    disk_io_read INTEGER,
                    disk_io_write INTEGER,
                    network_bytes_sent INTEGER,
                    network_bytes_recv INTEGER
                )
            ''')
            
            # Create alerts table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS resource_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    resource_type TEXT NOT NULL,
                    alert_level TEXT NOT NULL,
                    current_value REAL NOT NULL,
                    threshold_value REAL NOT NULL,
                    message TEXT,
                    resolved BOOLEAN DEFAULT FALSE,
                    resolved_at TIMESTAMP
                )
            ''')
            
            conn.commit()
            conn.close()
            
            self.logger.info("SRMM database initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize SRMM database: {e}")
            raise
    
    async def start(self):
        """Start the SRMM module."""
        try:
            self.logger.info("Starting SRMM module...")
            
            # Establish baseline metrics
            await self.establish_baseline()
            
            # Start monitoring
            self.is_monitoring = True
            self.monitoring_task = asyncio.create_task(self.monitor_resources())
            
            # Start cleanup task
            asyncio.create_task(self.cleanup_old_metrics())
            
            self.logger.info("SRMM module started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start SRMM module: {e}")
            raise
    
    async def stop(self):
        """Stop the SRMM module."""
        try:
            self.logger.info("Stopping SRMM module...")
            
            # Stop monitoring
            self.is_monitoring = False
            if self.monitoring_task:
                self.monitoring_task.cancel()
                try:
                    await self.monitoring_task
                except asyncio.CancelledError:
                    pass
            
            self.logger.info("SRMM module stopped successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to stop SRMM module: {e}")
            raise
    
    async def establish_baseline(self):
        """Establish baseline metrics for comparison."""
        try:
            # Take several measurements to establish baseline
            measurements = []
            for _ in range(5):
                metrics = await self.collect_metrics()
                measurements.append(metrics)
                await asyncio.sleep(2)
            
            # Calculate averages
            if measurements:
                self.baseline_metrics = ResourceMetrics(
                    timestamp=datetime.now(),
                    cpu_usage=sum(m.cpu_usage for m in measurements) / len(measurements),
                    memory_usage=sum(m.memory_usage for m in measurements) / len(measurements),
                    disk_usage=measurements[0].disk_usage,  # Disk usage doesn't change rapidly
                    network_connectivity=all(m.network_connectivity for m in measurements),
                    network_latency=sum(m.network_latency for m in measurements) / len(measurements),
                    active_connections=int(sum(m.active_connections for m in measurements) / len(measurements)),
                    load_average=measurements[0].load_average,  # Use latest load average
                    available_memory=measurements[0].available_memory,
                    total_memory=measurements[0].total_memory,
                    disk_io_read=measurements[0].disk_io_read,
                    disk_io_write=measurements[0].disk_io_write,
                    network_bytes_sent=measurements[0].network_bytes_sent,
                    network_bytes_recv=measurements[0].network_bytes_recv
                )
            
            self.logger.info("Baseline metrics established")
            
        except Exception as e:
            self.logger.error(f"Error establishing baseline metrics: {e}")
    
    async def monitor_resources(self):
        """Main monitoring loop."""
        while self.is_monitoring:
            try:
                # Collect current metrics
                metrics = await self.collect_metrics()
                self.current_metrics = metrics
                
                # Store metrics in database
                await self.store_metrics(metrics)
                
                # Check thresholds
                await self.check_thresholds(metrics)
                
                # Update statistics
                self.update_statistics(metrics)
                
                # Notify callbacks
                await self.notify_metrics_callbacks(metrics)
                
                # Sleep until next monitoring cycle
                await asyncio.sleep(self.monitoring_interval)
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(self.monitoring_interval)
    
    async def collect_metrics(self) -> ResourceMetrics:
        """Collect current resource metrics."""
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            load_avg = psutil.getloadavg() if hasattr(psutil, 'getloadavg') else [0, 0, 0]
            
            # Memory metrics
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            available_memory = memory.available
            total_memory = memory.total
            
            # Disk metrics
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            
            # Disk I/O metrics
            disk_io = psutil.disk_io_counters()
            disk_io_read = disk_io.read_bytes if disk_io else 0
            disk_io_write = disk_io.write_bytes if disk_io else 0
            
            # Network metrics
            network_io = psutil.net_io_counters()
            network_bytes_sent = network_io.bytes_sent if network_io else 0
            network_bytes_recv = network_io.bytes_recv if network_io else 0
            
            # Network connectivity and latency
            network_connectivity, network_latency = await self.test_network_connectivity()
            
            # Active connections
            active_connections = len(psutil.net_connections())
            
            return ResourceMetrics(
                timestamp=datetime.now(),
                cpu_usage=cpu_percent,
                memory_usage=memory_percent,
                disk_usage=disk_percent,
                network_connectivity=network_connectivity,
                network_latency=network_latency,
                active_connections=active_connections,
                load_average=list(load_avg),
                available_memory=available_memory,
                total_memory=total_memory,
                disk_io_read=disk_io_read,
                disk_io_write=disk_io_write,
                network_bytes_sent=network_bytes_sent,
                network_bytes_recv=network_bytes_recv
            )
            
        except Exception as e:
            self.logger.error(f"Error collecting metrics: {e}")
            # Return default metrics to prevent failures
            return ResourceMetrics(
                timestamp=datetime.now(),
                cpu_usage=0.0,
                memory_usage=0.0,
                disk_usage=0.0,
                network_connectivity=False,
                network_latency=0.0,
                active_connections=0,
                load_average=[0.0, 0.0, 0.0],
                available_memory=0,
                total_memory=0,
                disk_io_read=0,
                disk_io_write=0,
                network_bytes_sent=0,
                network_bytes_recv=0
            )
    
    async def test_network_connectivity(self) -> tuple[bool, float]:
        """Test network connectivity and measure latency."""
        try:
            total_latency = 0.0
            successful_tests = 0
            
            for host in self.network_test_hosts:
                try:
                    start_time = time.time()
                    
                    # Test connectivity
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(self.thresholds.network_timeout)
                    result = sock.connect_ex((host, 53))  # DNS port
                    sock.close()
                    
                    if result == 0:
                        latency = (time.time() - start_time) * 1000  # Convert to ms
                        total_latency += latency
                        successful_tests += 1
                        
                except Exception:
                    continue
            
            if successful_tests > 0:
                average_latency = total_latency / successful_tests
                return True, average_latency
            else:
                return False, 0.0
                
        except Exception as e:
            self.logger.error(f"Error testing network connectivity: {e}")
            return False, 0.0
    
    async def store_metrics(self, metrics: ResourceMetrics):
        """Store metrics in database."""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO resource_metrics (
                    timestamp, cpu_usage, memory_usage, disk_usage,
                    network_connectivity, network_latency, active_connections,
                    load_average_1m, load_average_5m, load_average_15m,
                    available_memory, total_memory, disk_io_read, disk_io_write,
                    network_bytes_sent, network_bytes_recv
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                metrics.timestamp.isoformat(),
                metrics.cpu_usage,
                metrics.memory_usage,
                metrics.disk_usage,
                metrics.network_connectivity,
                metrics.network_latency,
                metrics.active_connections,
                metrics.load_average[0] if len(metrics.load_average) > 0 else 0.0,
                metrics.load_average[1] if len(metrics.load_average) > 1 else 0.0,
                metrics.load_average[2] if len(metrics.load_average) > 2 else 0.0,
                metrics.available_memory,
                metrics.total_memory,
                metrics.disk_io_read,
                metrics.disk_io_write,
                metrics.network_bytes_sent,
                metrics.network_bytes_recv
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"Error storing metrics: {e}")
    
    async def check_thresholds(self, metrics: ResourceMetrics):
        """Check if metrics exceed thresholds."""
        try:
            alerts = []
            
            # Check CPU thresholds
            if metrics.cpu_usage >= self.thresholds.cpu_critical:
                alerts.append({
                    'resource': 'cpu',
                    'level': ResourceStatus.CRITICAL,
                    'value': metrics.cpu_usage,
                    'threshold': self.thresholds.cpu_critical,
                    'message': f'CPU usage critical: {metrics.cpu_usage:.1f}%'
                })
            elif metrics.cpu_usage >= self.thresholds.cpu_warning:
                alerts.append({
                    'resource': 'cpu',
                    'level': ResourceStatus.WARNING,
                    'value': metrics.cpu_usage,
                    'threshold': self.thresholds.cpu_warning,
                    'message': f'CPU usage warning: {metrics.cpu_usage:.1f}%'
                })
            
            # Check memory thresholds
            if metrics.memory_usage >= self.thresholds.memory_critical:
                alerts.append({
                    'resource': 'memory',
                    'level': ResourceStatus.CRITICAL,
                    'value': metrics.memory_usage,
                    'threshold': self.thresholds.memory_critical,
                    'message': f'Memory usage critical: {metrics.memory_usage:.1f}%'
                })
            elif metrics.memory_usage >= self.thresholds.memory_warning:
                alerts.append({
                    'resource': 'memory',
                    'level': ResourceStatus.WARNING,
                    'value': metrics.memory_usage,
                    'threshold': self.thresholds.memory_warning,
                    'message': f'Memory usage warning: {metrics.memory_usage:.1f}%'
                })
            
            # Check disk thresholds
            if metrics.disk_usage >= self.thresholds.disk_critical:
                alerts.append({
                    'resource': 'disk',
                    'level': ResourceStatus.CRITICAL,
                    'value': metrics.disk_usage,
                    'threshold': self.thresholds.disk_critical,
                    'message': f'Disk usage critical: {metrics.disk_usage:.1f}%'
                })
            elif metrics.disk_usage >= self.thresholds.disk_warning:
                alerts.append({
                    'resource': 'disk',
                    'level': ResourceStatus.WARNING,
                    'value': metrics.disk_usage,
                    'threshold': self.thresholds.disk_warning,
                    'message': f'Disk usage warning: {metrics.disk_usage:.1f}%'
                })
            
            # Check network connectivity
            if not metrics.network_connectivity:
                alerts.append({
                    'resource': 'network',
                    'level': ResourceStatus.CRITICAL,
                    'value': 0,
                    'threshold': 1,
                    'message': 'Network connectivity lost'
                })
            
            # Process alerts
            if alerts:
                await self.process_alerts(alerts)
            
            # Update overall resource status
            await self.update_resource_status(alerts)
            
        except Exception as e:
            self.logger.error(f"Error checking thresholds: {e}")
    
    async def process_alerts(self, alerts: List[Dict[str, Any]]):
        """Process resource alerts."""
        try:
            for alert in alerts:
                # Store alert in database
                await self.store_alert(alert)
                
                # Log alert
                level = alert['level']
                if level == ResourceStatus.CRITICAL:
                    self.logger.error(alert['message'])
                elif level == ResourceStatus.WARNING:
                    self.logger.warning(alert['message'])
                
                # Notify threshold callbacks
                await self.notify_threshold_callbacks(alert)
                
                # Update statistics
                if level == ResourceStatus.CRITICAL:
                    self.stats['critical_count'] += 1
                elif level == ResourceStatus.WARNING:
                    self.stats['warning_count'] += 1
                    
        except Exception as e:
            self.logger.error(f"Error processing alerts: {e}")
    
    async def store_alert(self, alert: Dict[str, Any]):
        """Store alert in database."""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO resource_alerts (
                    timestamp, resource_type, alert_level, current_value,
                    threshold_value, message
                ) VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                datetime.now().isoformat(),
                alert['resource'],
                alert['level'].value,
                alert['value'],
                alert['threshold'],
                alert['message']
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"Error storing alert: {e}")
    
    async def update_resource_status(self, alerts: List[Dict[str, Any]]):
        """Update overall resource status and backpressure level."""
        try:
            # Determine overall status
            if any(alert['level'] == ResourceStatus.CRITICAL for alert in alerts):
                self.resource_status = ResourceStatus.CRITICAL
                self.backpressure_level = BackpressureLevel.HEAVY
            elif any(alert['level'] == ResourceStatus.WARNING for alert in alerts):
                self.resource_status = ResourceStatus.WARNING
                self.backpressure_level = BackpressureLevel.MODERATE
            else:
                self.resource_status = ResourceStatus.NORMAL
                self.backpressure_level = BackpressureLevel.NONE
                
        except Exception as e:
            self.logger.error(f"Error updating resource status: {e}")
    
    async def notify_threshold_callbacks(self, alert: Dict[str, Any]):
        """Notify threshold callbacks."""
        for callback in self.threshold_callbacks:
            try:
                await callback(alert)
            except Exception as e:
                self.logger.error(f"Error in threshold callback: {e}")
    
    async def notify_metrics_callbacks(self, metrics: ResourceMetrics):
        """Notify metrics callbacks."""
        for callback in self.metrics_callbacks:
            try:
                await callback(metrics)
            except Exception as e:
                self.logger.error(f"Error in metrics callback: {e}")
    
    def update_statistics(self, metrics: ResourceMetrics):
        """Update statistics."""
        try:
            self.stats['total_measurements'] += 1
            
            # Update averages
            total = self.stats['total_measurements']
            self.stats['average_cpu_usage'] = (
                (self.stats['average_cpu_usage'] * (total - 1) + metrics.cpu_usage) / total
            )
            self.stats['average_memory_usage'] = (
                (self.stats['average_memory_usage'] * (total - 1) + metrics.memory_usage) / total
            )
            
            # Update peaks
            self.stats['peak_cpu_usage'] = max(self.stats['peak_cpu_usage'], metrics.cpu_usage)
            self.stats['peak_memory_usage'] = max(self.stats['peak_memory_usage'], metrics.memory_usage)
            
        except Exception as e:
            self.logger.error(f"Error updating statistics: {e}")
    
    async def cleanup_old_metrics(self):
        """Clean up old metrics and alerts."""
        while True:
            try:
                # Clean up metrics older than retention period
                cutoff_date = datetime.now() - timedelta(days=self.history_retention_days)
                
                conn = sqlite3.connect(str(self.db_path))
                cursor = conn.cursor()
                
                cursor.execute('''
                    DELETE FROM resource_metrics 
                    WHERE timestamp < ?
                ''', (cutoff_date.isoformat(),))
                
                cursor.execute('''
                    DELETE FROM resource_alerts 
                    WHERE timestamp < ?
                ''', (cutoff_date.isoformat(),))
                
                conn.commit()
                conn.close()
                
                # Sleep for 1 hour
                await asyncio.sleep(3600)
                
            except Exception as e:
                self.logger.error(f"Error cleaning up old metrics: {e}")
                await asyncio.sleep(3600)
    
    # Public API methods
    async def get_resource_metrics(self) -> Dict[str, Any]:
        """Get current resource metrics."""
        if self.current_metrics:
            return {
                'timestamp': self.current_metrics.timestamp.isoformat(),
                'cpu_usage': self.current_metrics.cpu_usage,
                'memory_usage': self.current_metrics.memory_usage,
                'disk_usage': self.current_metrics.disk_usage,
                'network_connectivity': self.current_metrics.network_connectivity,
                'network_latency': self.current_metrics.network_latency,
                'active_connections': self.current_metrics.active_connections,
                'load_average': self.current_metrics.load_average,
                'available_memory': self.current_metrics.available_memory,
                'total_memory': self.current_metrics.total_memory
            }
        return {}
    
    def get_resource_status(self) -> ResourceStatus:
        """Get current resource status."""
        return self.resource_status
    
    def get_backpressure_level(self) -> BackpressureLevel:
        """Get current backpressure level."""
        return self.backpressure_level
    
    def should_apply_backpressure(self) -> bool:
        """Check if backpressure should be applied."""
        return self.backpressure_level != BackpressureLevel.NONE
    
    def register_threshold_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """Register threshold callback."""
        self.threshold_callbacks.append(callback)
    
    def register_metrics_callback(self, callback: Callable[[ResourceMetrics], None]):
        """Register metrics callback."""
        self.metrics_callbacks.append(callback)
    
    def set_thresholds(self, thresholds: Dict[str, float]):
        """Update resource thresholds."""
        try:
            for key, value in thresholds.items():
                if hasattr(self.thresholds, key):
                    setattr(self.thresholds, key, value)
            
            self.logger.info(f"Updated thresholds: {thresholds}")
            
        except Exception as e:
            self.logger.error(f"Error setting thresholds: {e}")
    
    async def get_historical_metrics(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get historical metrics."""
        try:
            cutoff_date = datetime.now() - timedelta(hours=hours)
            
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT timestamp, cpu_usage, memory_usage, disk_usage,
                       network_connectivity, network_latency, active_connections
                FROM resource_metrics
                WHERE timestamp > ?
                ORDER BY timestamp ASC
            ''', (cutoff_date.isoformat(),))
            
            rows = cursor.fetchall()
            conn.close()
            
            metrics = []
            for row in rows:
                metrics.append({
                    'timestamp': row[0],
                    'cpu_usage': row[1],
                    'memory_usage': row[2],
                    'disk_usage': row[3],
                    'network_connectivity': row[4],
                    'network_latency': row[5],
                    'active_connections': row[6]
                })
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error getting historical metrics: {e}")
            return []
    
    async def get_recent_alerts(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get recent alerts."""
        try:
            cutoff_date = datetime.now() - timedelta(hours=hours)
            
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT timestamp, resource_type, alert_level, current_value,
                       threshold_value, message
                FROM resource_alerts
                WHERE timestamp > ?
                ORDER BY timestamp DESC
            ''', (cutoff_date.isoformat(),))
            
            rows = cursor.fetchall()
            conn.close()
            
            alerts = []
            for row in rows:
                alerts.append({
                    'timestamp': row[0],
                    'resource_type': row[1],
                    'alert_level': row[2],
                    'current_value': row[3],
                    'threshold_value': row[4],
                    'message': row[5]
                })
            
            return alerts
            
        except Exception as e:
            self.logger.error(f"Error getting recent alerts: {e}")
            return []
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of the SRMM module."""
        return {
            'module': 'SRMM',
            'is_monitoring': self.is_monitoring,
            'resource_status': self.resource_status.value,
            'backpressure_level': self.backpressure_level.value,
            'thresholds': asdict(self.thresholds),
            'stats': self.stats,
            'current_metrics': self.current_metrics.__dict__ if self.current_metrics else None
        } 