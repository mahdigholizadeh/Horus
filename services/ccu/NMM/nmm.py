"""
Network Monitoring Module (NMM)

This module provides comprehensive network connectivity monitoring for the CCU
and all dependent microservices. It monitors network health, latency, bandwidth,
and connection status across all services.

Key Responsibilities:
- Monitor network connectivity to all microservices
- Track network latency and performance metrics
- Perform bandwidth testing and monitoring
- Detect network outages and connection issues
- Provide network diagnostic capabilities
- Monitor DNS resolution and routing
- Track network security and firewall status
- Generate network health reports and alerts
"""

import asyncio
import logging
import json
import sqlite3
import socket
import requests

# Optional import for ping3 - test environment may not have it installed
try:
    import ping3
    PING3_AVAILABLE = True
except ImportError:
    ping3 = None
    PING3_AVAILABLE = False
import subprocess
import time
from typing import Dict, Any, List, Optional, Callable, Tuple
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import threading
import ipaddress
import psutil
import aiohttp

# Optional import for dns.resolver - test environment may not have it installed
try:
    import dns.resolver
    DNS_AVAILABLE = True
except ImportError:
    dns = None
    DNS_AVAILABLE = False


class NetworkStatus(Enum):
    """Network connection status."""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    DEGRADED = "degraded"
    TIMEOUT = "timeout"
    ERROR = "error"
    UNKNOWN = "unknown"


class ConnectionType(Enum):
    """Connection type enumeration."""
    HTTP = "http"
    HTTPS = "https"
    WEBSOCKET = "websocket"
    DATABASE = "database"
    PING = "ping"
    DNS = "dns"


@dataclass
class NetworkEndpoint:
    """Network endpoint information."""
    name: str
    host: str
    port: int
    protocol: str
    connection_type: ConnectionType
    service: str
    health_endpoint: Optional[str] = None
    timeout: int = 30
    expected_response_time: float = 1.0
    critical_threshold: float = 5.0
    enabled: bool = True


@dataclass
class NetworkMetrics:
    """Network metrics information."""
    endpoint_name: str
    timestamp: datetime
    status: NetworkStatus
    response_time: float
    latency: float
    bandwidth: float
    packet_loss: float
    dns_resolution_time: float
    connection_errors: int
    success_rate: float
    details: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.details is None:
            self.details = {}


@dataclass
class NetworkEvent:
    """Network event record."""
    event_id: str
    endpoint_name: str
    event_type: str
    severity: str
    message: str
    timestamp: datetime
    details: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.details is None:
            self.details = {}


class NetworkMonitoringModule:
    """
    Network Monitoring Module (NMM)
    
    Monitors network connectivity and performance across all microservices.
    """
    
    def __init__(self):
        """Initialize the NMM module."""
        self.logger = logging.getLogger(__name__)
        
        # Database setup
        self.db_path = Path("nmm_network.db")
        self.init_database()
        
        # Network endpoints
        self.endpoints: Dict[str, NetworkEndpoint] = {}
        self.network_metrics: Dict[str, deque] = {}
        self.network_events: Dict[str, deque] = {}
        
        # Monitoring configuration
        self.monitoring_interval = 30  # seconds
        self.metrics_retention_hours = 24
        self.events_retention_hours = 48
        
        # Monitoring state
        self.is_monitoring = False
        self.monitoring_task = None
        
        # Network tools
        self.ping_timeout = 5
        self.http_timeout = 30
        self.dns_timeout = 10
        
        # Performance thresholds
        self.thresholds = {
            "latency_warning": 100.0,    # ms
            "latency_critical": 500.0,   # ms
            "response_time_warning": 2.0, # seconds
            "response_time_critical": 10.0, # seconds
            "packet_loss_warning": 1.0,  # percentage
            "packet_loss_critical": 5.0, # percentage
            "bandwidth_warning": 1.0,    # Mbps
            "bandwidth_critical": 0.1    # Mbps
        }
        
        # External connectivity tests
        self.external_hosts = [
            "8.8.8.8",          # Google DNS
            "1.1.1.1",          # Cloudflare DNS
            "208.67.222.222",   # OpenDNS
            "google.com",       # Google
            "cloudflare.com"    # Cloudflare
        ]
        
        # Callbacks
        self.status_callbacks = []
        self.event_callbacks = []
        
        # Statistics
        self.stats = {
            "total_endpoints": 0,
            "active_endpoints": 0,
            "healthy_endpoints": 0,
            "degraded_endpoints": 0,
            "failed_endpoints": 0,
            "total_checks": 0,
            "successful_checks": 0,
            "failed_checks": 0,
            "average_latency": 0.0,
            "average_response_time": 0.0,
            "network_uptime": 0.0,
            "last_check": None
        }
        
        # Register default endpoints
        self._register_default_endpoints()
        
        self.logger.info("NMM module initialized successfully")
    
    def init_database(self):
        """Initialize the SQLite database for network tracking."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Network endpoints table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS network_endpoints (
                        name TEXT PRIMARY KEY,
                        host TEXT NOT NULL,
                        port INTEGER NOT NULL,
                        protocol TEXT NOT NULL,
                        connection_type TEXT NOT NULL,
                        service TEXT NOT NULL,
                        health_endpoint TEXT,
                        timeout INTEGER DEFAULT 30,
                        expected_response_time REAL DEFAULT 1.0,
                        critical_threshold REAL DEFAULT 5.0,
                        enabled INTEGER DEFAULT 1
                    )
                """)
                
                # Network metrics table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS network_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        endpoint_name TEXT NOT NULL,
                        timestamp TIMESTAMP NOT NULL,
                        status TEXT NOT NULL,
                        response_time REAL NOT NULL,
                        latency REAL NOT NULL,
                        bandwidth REAL NOT NULL,
                        packet_loss REAL NOT NULL,
                        dns_resolution_time REAL NOT NULL,
                        connection_errors INTEGER NOT NULL,
                        success_rate REAL NOT NULL,
                        details TEXT,
                        FOREIGN KEY (endpoint_name) REFERENCES network_endpoints (name)
                    )
                """)
                
                # Network events table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS network_events (
                        event_id TEXT PRIMARY KEY,
                        endpoint_name TEXT NOT NULL,
                        event_type TEXT NOT NULL,
                        severity TEXT NOT NULL,
                        message TEXT NOT NULL,
                        timestamp TIMESTAMP NOT NULL,
                        details TEXT,
                        FOREIGN KEY (endpoint_name) REFERENCES network_endpoints (name)
                    )
                """)
                
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Failed to initialize database: {e}")
            raise
    
    def _register_default_endpoints(self):
        """Register default endpoints for monitoring."""
        # RLA endpoints
        self.register_endpoint(NetworkEndpoint(
            name="RLA_HTTPS",
            host="localhost",
            port=3781,
            protocol="https",
            connection_type=ConnectionType.HTTPS,
            service="RLA",
            health_endpoint="/health",
            timeout=30
        ))
        
        # TPP endpoints
        self.register_endpoint(NetworkEndpoint(
            name="TPP_HTTP",
            host="localhost",
            port=8082,
            protocol="http",
            connection_type=ConnectionType.HTTP,
            service="TPP",
            health_endpoint="/health",
            timeout=30
        ))
        
        # RCM endpoints
        self.register_endpoint(NetworkEndpoint(
            name="RCM_HTTP",
            host="localhost",
            port=8080,
            protocol="http",
            connection_type=ConnectionType.HTTP,
            service="RCM",
            health_endpoint="/health",
            timeout=30
        ))
        
        self.register_endpoint(NetworkEndpoint(
            name="RCM_WEBSOCKET",
            host="localhost",
            port=8081,
            protocol="ws",
            connection_type=ConnectionType.WEBSOCKET,
            service="RCM",
            timeout=30
        ))
        
        # JFA endpoints
        self.register_endpoint(NetworkEndpoint(
            name="JFA_HTTP",
            host="localhost",
            port=8083,
            protocol="http",
            connection_type=ConnectionType.HTTP,
            service="JFA",
            health_endpoint="/health",
            timeout=30
        ))
        
        # TD endpoints
        self.register_endpoint(NetworkEndpoint(
            name="TD_HTTP",
            host="localhost",
            port=8003,
            protocol="http",
            connection_type=ConnectionType.HTTP,
            service="TD",
            health_endpoint="/health",
            timeout=30
        ))
        
        # OCM endpoints (when implemented)
        self.register_endpoint(NetworkEndpoint(
            name="OCM_HTTP",
            host="localhost",
            port=8085,
            protocol="http",
            connection_type=ConnectionType.HTTP,
            service="OCM",
            health_endpoint="/health",
            timeout=30,
            enabled=False  # Disabled until OCM is implemented
        ))
        
        # External connectivity tests
        for host in self.external_hosts:
            self.register_endpoint(NetworkEndpoint(
                name=f"EXTERNAL_{host.replace('.', '_').replace('-', '_').upper()}",
                host=host,
                port=80 if not host.replace('.', '').isdigit() else 53,
                protocol="ping",
                connection_type=ConnectionType.PING,
                service="EXTERNAL",
                timeout=5
            ))
        
        self.logger.info("Default endpoints registered")
    
    def register_endpoint(self, endpoint: NetworkEndpoint):
        """Register a network endpoint for monitoring."""
        try:
            self.endpoints[endpoint.name] = endpoint
            
            # Initialize metrics and events queues
            self.network_metrics[endpoint.name] = deque(maxlen=1000)
            self.network_events[endpoint.name] = deque(maxlen=500)
            
            # Persist to database
            self._persist_endpoint(endpoint)
            
            self.stats["total_endpoints"] += 1
            if endpoint.enabled:
                self.stats["active_endpoints"] += 1
            
            self.logger.info(f"Registered network endpoint: {endpoint.name}")
            
        except Exception as e:
            self.logger.error(f"Failed to register endpoint {endpoint.name}: {e}")
            raise
    
    def unregister_endpoint(self, endpoint_name: str):
        """Unregister a network endpoint."""
        try:
            if endpoint_name in self.endpoints:
                del self.endpoints[endpoint_name]
                del self.network_metrics[endpoint_name]
                del self.network_events[endpoint_name]
                
                self.stats["total_endpoints"] -= 1
                
                self.logger.info(f"Unregistered network endpoint: {endpoint_name}")
            
        except Exception as e:
            self.logger.error(f"Failed to unregister endpoint {endpoint_name}: {e}")
    
    async def start_monitoring(self):
        """Start network monitoring."""
        if self.is_monitoring:
            return
        
        self.is_monitoring = True
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        self.logger.info("Network monitoring started")
    
    async def stop_monitoring(self):
        """Stop network monitoring."""
        if not self.is_monitoring:
            return
        
        self.is_monitoring = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("Network monitoring stopped")
    
    async def _monitoring_loop(self):
        """Main monitoring loop."""
        while self.is_monitoring:
            try:
                # Perform network checks
                await self._perform_network_checks()
                
                # Update statistics
                self._update_statistics()
                
                # Clean up old data
                await self._cleanup_old_data()
                
                # Sleep for monitoring interval
                await asyncio.sleep(self.monitoring_interval)
                
            except Exception as e:
                self.logger.error(f"Network monitoring loop error: {e}")
                await asyncio.sleep(30)  # Short sleep on error
    
    async def _perform_network_checks(self):
        """Perform network checks on all endpoints."""
        try:
            # Create tasks for all enabled endpoints
            tasks = []
            for endpoint_name, endpoint in self.endpoints.items():
                if endpoint.enabled:
                    task = asyncio.create_task(self._check_endpoint(endpoint))
                    tasks.append(task)
            
            # Execute all checks concurrently
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
            
            self.stats["last_check"] = datetime.now()
            
        except Exception as e:
            self.logger.error(f"Network checks error: {e}")
    
    async def _check_endpoint(self, endpoint: NetworkEndpoint):
        """Check a specific network endpoint."""
        try:
            start_time = time.time()
            
            # Perform different checks based on connection type
            if endpoint.connection_type == ConnectionType.HTTP:
                metrics = await self._check_http_endpoint(endpoint)
            elif endpoint.connection_type == ConnectionType.HTTPS:
                metrics = await self._check_https_endpoint(endpoint)
            elif endpoint.connection_type == ConnectionType.WEBSOCKET:
                metrics = await self._check_websocket_endpoint(endpoint)
            elif endpoint.connection_type == ConnectionType.PING:
                metrics = await self._check_ping_endpoint(endpoint)
            elif endpoint.connection_type == ConnectionType.DNS:
                metrics = await self._check_dns_endpoint(endpoint)
            else:
                metrics = await self._check_generic_endpoint(endpoint)
            
            # Calculate total response time
            total_time = time.time() - start_time
            metrics.response_time = total_time
            
            # Store metrics
            self.network_metrics[endpoint.name].append(metrics)
            
            # Check thresholds and generate events
            await self._check_thresholds(endpoint, metrics)
            
            # Persist metrics
            await self._persist_metrics(metrics)
            
            # Update statistics
            self.stats["total_checks"] += 1
            if metrics.status == NetworkStatus.CONNECTED:
                self.stats["successful_checks"] += 1
            else:
                self.stats["failed_checks"] += 1
            
        except Exception as e:
            self.logger.error(f"Endpoint check failed for {endpoint.name}: {e}")
            
            # Create error metrics
            error_metrics = NetworkMetrics(
                endpoint_name=endpoint.name,
                timestamp=datetime.now(),
                status=NetworkStatus.ERROR,
                response_time=0.0,
                latency=0.0,
                bandwidth=0.0,
                packet_loss=100.0,
                dns_resolution_time=0.0,
                connection_errors=1,
                success_rate=0.0,
                details={"error": str(e)}
            )
            
            self.network_metrics[endpoint.name].append(error_metrics)
            self.stats["failed_checks"] += 1
    
    async def _check_http_endpoint(self, endpoint: NetworkEndpoint) -> NetworkMetrics:
        """Check HTTP endpoint."""
        try:
            # DNS resolution time
            dns_start = time.time()
            try:
                socket.gethostbyname(endpoint.host)
                dns_time = time.time() - dns_start
            except:
                dns_time = 0.0
            
            # HTTP request
            url = f"http://{endpoint.host}:{endpoint.port}"
            if endpoint.health_endpoint:
                url += endpoint.health_endpoint
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=endpoint.timeout)) as session:
                start_time = time.time()
                async with session.get(url) as response:
                    latency = (time.time() - start_time) * 1000  # Convert to ms
                    
                    # Determine status
                    if response.status == 200:
                        status = NetworkStatus.CONNECTED
                        success_rate = 100.0
                    else:
                        status = NetworkStatus.DEGRADED
                        success_rate = 50.0
                    
                    return NetworkMetrics(
                        endpoint_name=endpoint.name,
                        timestamp=datetime.now(),
                        status=status,
                        response_time=0.0,  # Will be set by caller
                        latency=latency,
                        bandwidth=0.0,  # Would need separate test
                        packet_loss=0.0,
                        dns_resolution_time=dns_time * 1000,
                        connection_errors=0,
                        success_rate=success_rate,
                        details={"status_code": response.status}
                    )
        
        except asyncio.TimeoutError:
            return NetworkMetrics(
                endpoint_name=endpoint.name,
                timestamp=datetime.now(),
                status=NetworkStatus.TIMEOUT,
                response_time=endpoint.timeout,
                latency=endpoint.timeout * 1000,
                bandwidth=0.0,
                packet_loss=0.0,
                dns_resolution_time=dns_time * 1000 if 'dns_time' in locals() else 0.0,
                connection_errors=1,
                success_rate=0.0,
                details={"error": "timeout"}
            )
        except Exception as e:
            return NetworkMetrics(
                endpoint_name=endpoint.name,
                timestamp=datetime.now(),
                status=NetworkStatus.ERROR,
                response_time=0.0,
                latency=0.0,
                bandwidth=0.0,
                packet_loss=100.0,
                dns_resolution_time=0.0,
                connection_errors=1,
                success_rate=0.0,
                details={"error": str(e)}
            )
    
    async def _check_https_endpoint(self, endpoint: NetworkEndpoint) -> NetworkMetrics:
        """Check HTTPS endpoint."""
        try:
            # DNS resolution time
            dns_start = time.time()
            try:
                socket.gethostbyname(endpoint.host)
                dns_time = time.time() - dns_start
            except:
                dns_time = 0.0
            
            # HTTPS request
            url = f"https://{endpoint.host}:{endpoint.port}"
            if endpoint.health_endpoint:
                url += endpoint.health_endpoint
            
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=endpoint.timeout),
                connector=aiohttp.TCPConnector(ssl=False)  # Skip SSL verification for testing
            ) as session:
                start_time = time.time()
                async with session.get(url) as response:
                    latency = (time.time() - start_time) * 1000  # Convert to ms
                    
                    # Determine status
                    if response.status == 200:
                        status = NetworkStatus.CONNECTED
                        success_rate = 100.0
                    else:
                        status = NetworkStatus.DEGRADED
                        success_rate = 50.0
                    
                    return NetworkMetrics(
                        endpoint_name=endpoint.name,
                        timestamp=datetime.now(),
                        status=status,
                        response_time=0.0,  # Will be set by caller
                        latency=latency,
                        bandwidth=0.0,  # Would need separate test
                        packet_loss=0.0,
                        dns_resolution_time=dns_time * 1000,
                        connection_errors=0,
                        success_rate=success_rate,
                        details={"status_code": response.status}
                    )
        
        except asyncio.TimeoutError:
            return NetworkMetrics(
                endpoint_name=endpoint.name,
                timestamp=datetime.now(),
                status=NetworkStatus.TIMEOUT,
                response_time=endpoint.timeout,
                latency=endpoint.timeout * 1000,
                bandwidth=0.0,
                packet_loss=0.0,
                dns_resolution_time=dns_time * 1000 if 'dns_time' in locals() else 0.0,
                connection_errors=1,
                success_rate=0.0,
                details={"error": "timeout"}
            )
        except Exception as e:
            return NetworkMetrics(
                endpoint_name=endpoint.name,
                timestamp=datetime.now(),
                status=NetworkStatus.ERROR,
                response_time=0.0,
                latency=0.0,
                bandwidth=0.0,
                packet_loss=100.0,
                dns_resolution_time=0.0,
                connection_errors=1,
                success_rate=0.0,
                details={"error": str(e)}
            )
    
    async def _check_websocket_endpoint(self, endpoint: NetworkEndpoint) -> NetworkMetrics:
        """Check WebSocket endpoint."""
        try:
            # Simple TCP connection test for WebSocket
            start_time = time.time()
            
            # Create socket connection
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(endpoint.timeout)
            
            try:
                result = sock.connect_ex((endpoint.host, endpoint.port))
                latency = (time.time() - start_time) * 1000
                
                if result == 0:
                    status = NetworkStatus.CONNECTED
                    success_rate = 100.0
                else:
                    status = NetworkStatus.DISCONNECTED
                    success_rate = 0.0
                
                return NetworkMetrics(
                    endpoint_name=endpoint.name,
                    timestamp=datetime.now(),
                    status=status,
                    response_time=0.0,
                    latency=latency,
                    bandwidth=0.0,
                    packet_loss=0.0,
                    dns_resolution_time=0.0,
                    connection_errors=0 if result == 0 else 1,
                    success_rate=success_rate,
                    details={"connection_result": result}
                )
            
            finally:
                sock.close()
        
        except Exception as e:
            return NetworkMetrics(
                endpoint_name=endpoint.name,
                timestamp=datetime.now(),
                status=NetworkStatus.ERROR,
                response_time=0.0,
                latency=0.0,
                bandwidth=0.0,
                packet_loss=100.0,
                dns_resolution_time=0.0,
                connection_errors=1,
                success_rate=0.0,
                details={"error": str(e)}
            )
    
    async def _check_ping_endpoint(self, endpoint: NetworkEndpoint) -> NetworkMetrics:
        """Check endpoint using ping."""
        try:
            if not PING3_AVAILABLE:
                # ping3 not available, return simulated result
                return NetworkMetrics(
                    endpoint_name=endpoint.name,
                    timestamp=datetime.now(),
                    status=NetworkStatus.UNKNOWN,
                    response_time=0.0,
                    latency=0.0,
                    bandwidth=0.0,
                    packet_loss=0.0,
                    dns_resolution_time=0.0,
                    connection_errors=0,
                    success_rate=50.0,  # Assume 50% for simulation
                    details={"ping_result": "ping3 not available", "simulated": True}
                )
            
            # Use ping3 for ping functionality
            result = ping3.ping(endpoint.host, timeout=self.ping_timeout)
            
            if result is not None:
                latency = result * 1000  # Convert to ms
                status = NetworkStatus.CONNECTED
                success_rate = 100.0
                packet_loss = 0.0
            else:
                latency = 0.0
                status = NetworkStatus.DISCONNECTED
                success_rate = 0.0
                packet_loss = 100.0
            
            return NetworkMetrics(
                endpoint_name=endpoint.name,
                timestamp=datetime.now(),
                status=status,
                response_time=0.0,
                latency=latency,
                bandwidth=0.0,
                packet_loss=packet_loss,
                dns_resolution_time=0.0,
                connection_errors=0 if result is not None else 1,
                success_rate=success_rate,
                details={"ping_result": result}
            )
        
        except Exception as e:
            return NetworkMetrics(
                endpoint_name=endpoint.name,
                timestamp=datetime.now(),
                status=NetworkStatus.ERROR,
                response_time=0.0,
                latency=0.0,
                bandwidth=0.0,
                packet_loss=100.0,
                dns_resolution_time=0.0,
                connection_errors=1,
                success_rate=0.0,
                details={"error": str(e)}
            )
    
    async def _check_dns_endpoint(self, endpoint: NetworkEndpoint) -> NetworkMetrics:
        """Check DNS endpoint."""
        try:
            if not DNS_AVAILABLE:
                # dns.resolver not available, return simulated result
                return NetworkMetrics(
                    endpoint_name=endpoint.name,
                    timestamp=datetime.now(),
                    status=NetworkStatus.UNKNOWN,
                    response_time=0.0,
                    latency=0.0,
                    bandwidth=0.0,
                    packet_loss=0.0,
                    dns_resolution_time=0.0,
                    connection_errors=0,
                    success_rate=50.0,  # Assume 50% for simulation
                    details={"dns_records": "dns.resolver not available", "simulated": True}
                )
            
            start_time = time.time()
            
            # DNS resolution test
            resolver = dns.resolver.Resolver()
            resolver.timeout = self.dns_timeout
            
            try:
                result = resolver.resolve(endpoint.host, 'A')
                dns_time = (time.time() - start_time) * 1000
                
                if result:
                    status = NetworkStatus.CONNECTED
                    success_rate = 100.0
                else:
                    status = NetworkStatus.DISCONNECTED
                    success_rate = 0.0
                
                return NetworkMetrics(
                    endpoint_name=endpoint.name,
                    timestamp=datetime.now(),
                    status=status,
                    response_time=0.0,
                    latency=dns_time,
                    bandwidth=0.0,
                    packet_loss=0.0,
                    dns_resolution_time=dns_time,
                    connection_errors=0,
                    success_rate=success_rate,
                    details={"dns_records": len(result)}
                )
            
            except Exception as e:
                return NetworkMetrics(
                    endpoint_name=endpoint.name,
                    timestamp=datetime.now(),
                    status=NetworkStatus.ERROR,
                    response_time=0.0,
                    latency=0.0,
                    bandwidth=0.0,
                    packet_loss=100.0,
                    dns_resolution_time=0.0,
                    connection_errors=1,
                    success_rate=0.0,
                    details={"error": str(e)}
                )
        
        except Exception as e:
            return NetworkMetrics(
                endpoint_name=endpoint.name,
                timestamp=datetime.now(),
                status=NetworkStatus.ERROR,
                response_time=0.0,
                latency=0.0,
                bandwidth=0.0,
                packet_loss=100.0,
                dns_resolution_time=0.0,
                connection_errors=1,
                success_rate=0.0,
                details={"error": str(e)}
            )
    
    async def _check_generic_endpoint(self, endpoint: NetworkEndpoint) -> NetworkMetrics:
        """Check generic endpoint using TCP connection."""
        try:
            start_time = time.time()
            
            # Create socket connection
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(endpoint.timeout)
            
            try:
                result = sock.connect_ex((endpoint.host, endpoint.port))
                latency = (time.time() - start_time) * 1000
                
                if result == 0:
                    status = NetworkStatus.CONNECTED
                    success_rate = 100.0
                else:
                    status = NetworkStatus.DISCONNECTED
                    success_rate = 0.0
                
                return NetworkMetrics(
                    endpoint_name=endpoint.name,
                    timestamp=datetime.now(),
                    status=status,
                    response_time=0.0,
                    latency=latency,
                    bandwidth=0.0,
                    packet_loss=0.0,
                    dns_resolution_time=0.0,
                    connection_errors=0 if result == 0 else 1,
                    success_rate=success_rate,
                    details={"connection_result": result}
                )
            
            finally:
                sock.close()
        
        except Exception as e:
            return NetworkMetrics(
                endpoint_name=endpoint.name,
                timestamp=datetime.now(),
                status=NetworkStatus.ERROR,
                response_time=0.0,
                latency=0.0,
                bandwidth=0.0,
                packet_loss=100.0,
                dns_resolution_time=0.0,
                connection_errors=1,
                success_rate=0.0,
                details={"error": str(e)}
            )
    
    async def _check_thresholds(self, endpoint: NetworkEndpoint, metrics: NetworkMetrics):
        """Check if metrics violate thresholds."""
        try:
            # Check latency threshold
            if metrics.latency > self.thresholds["latency_critical"]:
                self._generate_event(
                    endpoint_name=endpoint.name,
                    event_type="latency_critical",
                    severity="critical",
                    message=f"Latency critical: {metrics.latency:.1f}ms"
                )
            elif metrics.latency > self.thresholds["latency_warning"]:
                self._generate_event(
                    endpoint_name=endpoint.name,
                    event_type="latency_warning",
                    severity="warning",
                    message=f"Latency warning: {metrics.latency:.1f}ms"
                )
            
            # Check response time threshold
            if metrics.response_time > self.thresholds["response_time_critical"]:
                self._generate_event(
                    endpoint_name=endpoint.name,
                    event_type="response_time_critical",
                    severity="critical",
                    message=f"Response time critical: {metrics.response_time:.2f}s"
                )
            elif metrics.response_time > self.thresholds["response_time_warning"]:
                self._generate_event(
                    endpoint_name=endpoint.name,
                    event_type="response_time_warning",
                    severity="warning",
                    message=f"Response time warning: {metrics.response_time:.2f}s"
                )
            
            # Check connection status
            if metrics.status in [NetworkStatus.DISCONNECTED, NetworkStatus.ERROR]:
                self._generate_event(
                    endpoint_name=endpoint.name,
                    event_type="connection_failed",
                    severity="critical",
                    message=f"Connection failed: {metrics.status.value}"
                )
            elif metrics.status == NetworkStatus.TIMEOUT:
                self._generate_event(
                    endpoint_name=endpoint.name,
                    event_type="connection_timeout",
                    severity="warning",
                    message=f"Connection timeout: {metrics.response_time:.2f}s"
                )
            
        except Exception as e:
            self.logger.error(f"Threshold check failed for {endpoint.name}: {e}")
    
    def _generate_event(self, endpoint_name: str, event_type: str, severity: str, message: str, details: Optional[Dict[str, Any]] = None):
        """Generate a network event."""
        try:
            event_id = self._generate_event_id()
            
            event = NetworkEvent(
                event_id=event_id,
                endpoint_name=endpoint_name,
                event_type=event_type,
                severity=severity,
                message=message,
                timestamp=datetime.now(),
                details=details or {}
            )
            
            # Add to events queue
            self.network_events[endpoint_name].append(event)
            
            # Persist event
            asyncio.create_task(self._persist_event(event))
            
            # Notify callbacks
            for callback in self.event_callbacks:
                try:
                    callback(event)
                except Exception as e:
                    self.logger.error(f"Event callback failed: {e}")
            
        except Exception as e:
            self.logger.error(f"Failed to generate event: {e}")
    
    def _update_statistics(self):
        """Update network statistics."""
        try:
            # Count endpoints by status
            healthy_count = 0
            degraded_count = 0
            failed_count = 0
            
            total_latency = 0.0
            total_response_time = 0.0
            metric_count = 0
            
            for endpoint_name, metrics_queue in self.network_metrics.items():
                if metrics_queue:
                    latest_metrics = metrics_queue[-1]
                    
                    if latest_metrics.status == NetworkStatus.CONNECTED:
                        healthy_count += 1
                    elif latest_metrics.status == NetworkStatus.DEGRADED:
                        degraded_count += 1
                    else:
                        failed_count += 1
                    
                    total_latency += latest_metrics.latency
                    total_response_time += latest_metrics.response_time
                    metric_count += 1
            
            self.stats["healthy_endpoints"] = healthy_count
            self.stats["degraded_endpoints"] = degraded_count
            self.stats["failed_endpoints"] = failed_count
            
            if metric_count > 0:
                self.stats["average_latency"] = total_latency / metric_count
                self.stats["average_response_time"] = total_response_time / metric_count
                self.stats["network_uptime"] = (healthy_count / metric_count) * 100
            
        except Exception as e:
            self.logger.error(f"Failed to update statistics: {e}")
    
    async def _cleanup_old_data(self):
        """Clean up old metrics and events."""
        try:
            metrics_cutoff = datetime.now() - timedelta(hours=self.metrics_retention_hours)
            events_cutoff = datetime.now() - timedelta(hours=self.events_retention_hours)
            
            # Clean up old metrics
            for endpoint_name in self.network_metrics:
                metrics_queue = self.network_metrics[endpoint_name]
                while metrics_queue and metrics_queue[0].timestamp < metrics_cutoff:
                    metrics_queue.popleft()
            
            # Clean up old events
            for endpoint_name in self.network_events:
                events_queue = self.network_events[endpoint_name]
                while events_queue and events_queue[0].timestamp < events_cutoff:
                    events_queue.popleft()
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup old data: {e}")
    
    async def _persist_endpoint(self, endpoint: NetworkEndpoint):
        """Persist endpoint to database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT OR REPLACE INTO network_endpoints 
                    (name, host, port, protocol, connection_type, service, 
                     health_endpoint, timeout, expected_response_time, 
                     critical_threshold, enabled)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    endpoint.name,
                    endpoint.host,
                    endpoint.port,
                    endpoint.protocol,
                    endpoint.connection_type.value,
                    endpoint.service,
                    endpoint.health_endpoint,
                    endpoint.timeout,
                    endpoint.expected_response_time,
                    endpoint.critical_threshold,
                    1 if endpoint.enabled else 0
                ))
                
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Failed to persist endpoint: {e}")
    
    async def _persist_metrics(self, metrics: NetworkMetrics):
        """Persist metrics to database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO network_metrics 
                    (endpoint_name, timestamp, status, response_time, latency, 
                     bandwidth, packet_loss, dns_resolution_time, connection_errors, 
                     success_rate, details)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    metrics.endpoint_name,
                    metrics.timestamp.isoformat(),
                    metrics.status.value,
                    metrics.response_time,
                    metrics.latency,
                    metrics.bandwidth,
                    metrics.packet_loss,
                    metrics.dns_resolution_time,
                    metrics.connection_errors,
                    metrics.success_rate,
                    json.dumps(metrics.details)
                ))
                
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Failed to persist metrics: {e}")
    
    async def _persist_event(self, event: NetworkEvent):
        """Persist event to database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO network_events 
                    (event_id, endpoint_name, event_type, severity, message, timestamp, details)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    event.event_id,
                    event.endpoint_name,
                    event.event_type,
                    event.severity,
                    event.message,
                    event.timestamp.isoformat(),
                    json.dumps(event.details)
                ))
                
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Failed to persist event: {e}")
    
    def _generate_event_id(self) -> str:
        """Generate a unique event ID."""
        import uuid
        return f"net_{uuid.uuid4().hex[:12]}"
    
    async def get_network_status(self, endpoint_name: Optional[str] = None) -> Dict[str, Any]:
        """Get network status for endpoints."""
        try:
            if endpoint_name:
                if endpoint_name in self.network_metrics and self.network_metrics[endpoint_name]:
                    latest_metrics = self.network_metrics[endpoint_name][-1]
                    return asdict(latest_metrics)
                else:
                    return {}
            else:
                status = {}
                for name, metrics_queue in self.network_metrics.items():
                    if metrics_queue:
                        status[name] = asdict(metrics_queue[-1])
                return status
                
        except Exception as e:
            self.logger.error(f"Failed to get network status: {e}")
            return {}
    
    async def get_network_metrics(self, endpoint_name: str, hours: int = 1) -> List[Dict[str, Any]]:
        """Get network metrics for specified hours."""
        try:
            if endpoint_name not in self.network_metrics:
                return []
            
            cutoff_time = datetime.now() - timedelta(hours=hours)
            metrics = []
            
            for metric in self.network_metrics[endpoint_name]:
                if metric.timestamp >= cutoff_time:
                    metrics.append(asdict(metric))
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Failed to get network metrics: {e}")
            return []
    
    async def get_network_events(self, endpoint_name: Optional[str] = None, hours: int = 24) -> List[Dict[str, Any]]:
        """Get network events for specified hours."""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            events = []
            
            if endpoint_name:
                if endpoint_name in self.network_events:
                    for event in self.network_events[endpoint_name]:
                        if event.timestamp >= cutoff_time:
                            events.append(asdict(event))
            else:
                for endpoint_events in self.network_events.values():
                    for event in endpoint_events:
                        if event.timestamp >= cutoff_time:
                            events.append(asdict(event))
            
            # Sort by timestamp (newest first)
            events.sort(key=lambda x: x['timestamp'], reverse=True)
            
            return events
            
        except Exception as e:
            self.logger.error(f"Failed to get network events: {e}")
            return []
    
    def add_status_callback(self, callback: Callable[[str, NetworkMetrics], None]):
        """Add status change callback."""
        self.status_callbacks.append(callback)
    
    def add_event_callback(self, callback: Callable[[NetworkEvent], None]):
        """Add event callback."""
        self.event_callbacks.append(callback)
    
    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the NMM module."""
        return {
            'is_monitoring': self.is_monitoring,
            'registered_endpoints': len(self.endpoints),
            'active_endpoints': len([e for e in self.endpoints.values() if e.enabled]),
            'monitoring_interval': self.monitoring_interval,
            'statistics': self.stats.copy()
        }
    
    async def start(self):
        """Start the NMM module."""
        await self.start_monitoring()
        self.logger.info("NMM module started")
    
    async def stop(self):
        """Stop the NMM module."""
        await self.stop_monitoring()
        self.logger.info("NMM module stopped") 