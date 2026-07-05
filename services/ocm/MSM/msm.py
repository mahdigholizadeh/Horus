"""
Monitoring System Module (MSM) for OCM

This module is responsible for collecting metrics, monitoring system health, logging,
and providing insights into OCM's operational status. It integrates with all other
modules to gather comprehensive performance and health data.
"""

import asyncio
import logging
import json
import psutil
import threading
import time
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict, deque
import statistics

class MetricType(Enum):
    """Types of metrics collected."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"

class AlertLevel(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class MetricPoint:
    """A single metric data point."""
    name: str
    value: float
    timestamp: datetime
    tags: Dict[str, str] = None
    metric_type: MetricType = MetricType.GAUGE
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = {}

@dataclass
class Alert:
    """System alert information."""
    alert_id: str
    level: AlertLevel
    title: str
    message: str
    source: str
    timestamp: datetime
    resolved: bool = False
    resolved_at: Optional[datetime] = None

@dataclass
class HealthCheckResult:
    """Health check result."""
    component: str
    healthy: bool
    message: str
    timestamp: datetime
    response_time: Optional[float] = None

class MonitoringSystemModule:
    """
    Monitoring System Module (MSM)
    
    Comprehensive monitoring for OCM:
    - Metrics collection and aggregation
    - System resource monitoring
    - Health checks for all components
    - Alert generation and management
    - Performance analytics
    - Log aggregation and analysis
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the MSM module."""
        self.logger = logging.getLogger(__name__)
        self.module_name = "MSM"
        self.is_active = False
        
        # Configuration
        self.config = config
        self.monitoring_config = config.get('monitoring', {})
        
        # Monitoring settings
        self.collection_interval = self.monitoring_config.get('collection_interval', 30)
        self.retention_period = self.monitoring_config.get('retention_period', 86400)  # 24 hours
        self.max_metrics_points = self.monitoring_config.get('max_metrics_points', 10000)
        self.health_check_interval = self.monitoring_config.get('health_check_interval', 60)
        
        # Metrics storage
        self.metrics = defaultdict(lambda: deque(maxlen=1000))  # metric_name -> deque of MetricPoints
        self.metric_summaries = {}  # metric_name -> summary stats
        
        # System resource tracking
        self.system_metrics = deque(maxlen=1000)
        
        # Health check results
        self.health_results = {}  # component_name -> HealthCheckResult
        
        # Alerts
        self.active_alerts = {}  # alert_id -> Alert
        self.alert_history = deque(maxlen=1000)
        
        # Performance tracking
        self.request_latencies = deque(maxlen=1000)
        self.error_counts = defaultdict(int)
        self.success_counts = defaultdict(int)
        
        # Module references for health checks
        self.modules = {}
        self.ocm_service = None
        
        # Registered health check functions
        self.health_checks = {}
        
        # Statistics
        self.stats = {
            'metrics_collected': 0,
            'alerts_generated': 0,
            'health_checks_performed': 0,
            'monitoring_start_time': None,
            'last_collection_time': None,
            'active_alerts_count': 0,
            'system_health_score': 100.0
        }
        
        # Performance thresholds
        self.thresholds = {
            'cpu_usage': self.monitoring_config.get('cpu_threshold', 80.0),
            'memory_usage': self.monitoring_config.get('memory_threshold', 85.0),
            'disk_usage': self.monitoring_config.get('disk_threshold', 90.0),
            'response_time': self.monitoring_config.get('response_time_threshold', 5.0),
            'error_rate': self.monitoring_config.get('error_rate_threshold', 5.0)
        }
        
        # Register built-in health checks
        self._register_builtin_health_checks()
        
        self.logger.info(f"{self.module_name} initialized - collection interval: {self.collection_interval}s")
    
    def set_references(self, ocm_service, modules: Dict[str, Any]):
        """Set references to OCM service and modules."""
        self.ocm_service = ocm_service
        self.modules = modules
    
    async def start(self):
        """Start the MSM module."""
        try:
            self.is_active = True
            self.stats['monitoring_start_time'] = datetime.now().isoformat()
            
            # Start monitoring tasks
            asyncio.create_task(self._metrics_collector())
            asyncio.create_task(self._system_monitor())
            asyncio.create_task(self._health_checker())
            asyncio.create_task(self._alert_manager())
            asyncio.create_task(self._cleanup_old_data())
            asyncio.create_task(self._performance_analyzer())
            
            self.logger.info("MSM started successfully - monitoring system active")
            
        except Exception as e:
            self.logger.error(f"Failed to start MSM: {e}")
            raise
    
    async def stop(self):
        """Stop the MSM module gracefully."""
        try:
            self.is_active = False
            self.logger.info("MSM stopped successfully")
            
        except Exception as e:
            self.logger.error(f"Error stopping MSM: {e}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        is_healthy = self.is_active
        
        return {
            'healthy': is_healthy,
            'is_active': self.is_active,
            'module': 'msm'
        }
    
    def _register_builtin_health_checks(self):
        """Register built-in health check functions."""
        self.health_checks = {
            'system_resources': self._health_check_system_resources,
            'disk_space': self._health_check_disk_space,
            'memory_usage': self._health_check_memory,
            'cpu_usage': self._health_check_cpu,
            'network_connectivity': self._health_check_network,
            'ssl_certificates': self._health_check_ssl,
            'database_connection': self._health_check_database,
            'cache_status': self._health_check_cache
        }
    
    def register_health_check(self, name: str, check_function: Callable):
        """Register a custom health check function."""
        self.health_checks[name] = check_function
        self.logger.info(f"Registered health check: {name}")
    
    def record_metric(self, name: str, value: float, metric_type: MetricType = MetricType.GAUGE, tags: Dict[str, str] = None):
        """Record a metric value."""
        try:
            metric_point = MetricPoint(
                name=name,
                value=value,
                timestamp=datetime.now(),
                tags=tags or {},
                metric_type=metric_type
            )
            
            self.metrics[name].append(metric_point)
            self.stats['metrics_collected'] += 1
            
            # Update summary statistics
            self._update_metric_summary(name, value)
            
        except Exception as e:
            self.logger.error(f"Failed to record metric {name}: {e}")
    
    def _update_metric_summary(self, metric_name: str, value: float):
        """Update summary statistics for a metric."""
        if metric_name not in self.metric_summaries:
            self.metric_summaries[metric_name] = {
                'count': 0,
                'sum': 0.0,
                'min': float('inf'),
                'max': float('-inf'),
                'avg': 0.0,
                'last_value': 0.0,
                'last_updated': None
            }
        
        summary = self.metric_summaries[metric_name]
        summary['count'] += 1
        summary['sum'] += value
        summary['min'] = min(summary['min'], value)
        summary['max'] = max(summary['max'], value)
        summary['avg'] = summary['sum'] / summary['count']
        summary['last_value'] = value
        summary['last_updated'] = datetime.now().isoformat()
    
    def increment_counter(self, name: str, value: float = 1.0, tags: Dict[str, str] = None):
        """Increment a counter metric."""
        self.record_metric(name, value, MetricType.COUNTER, tags)
    
    def set_gauge(self, name: str, value: float, tags: Dict[str, str] = None):
        """Set a gauge metric value."""
        self.record_metric(name, value, MetricType.GAUGE, tags)
    
    def record_timing(self, name: str, duration: float, tags: Dict[str, str] = None):
        """Record a timing/duration metric."""
        self.record_metric(name, duration, MetricType.HISTOGRAM, tags)
    
    async def _metrics_collector(self):
        """Main metrics collection loop."""
        while self.is_active:
            try:
                await self._collect_service_metrics()
                await self._collect_module_metrics()
                
                self.stats['last_collection_time'] = datetime.now().isoformat()
                await asyncio.sleep(self.collection_interval)
                
            except Exception as e:
                self.logger.error(f"Error in metrics collection: {e}")
                await asyncio.sleep(self.collection_interval)
    
    async def _collect_service_metrics(self):
        """Collect OCM service metrics."""
        try:
            if not self.ocm_service:
                return
            
            status = self.ocm_service.get_status()
            
            # Record service metrics
            self.set_gauge('ocm.uptime', status.uptime or 0)
            self.set_gauge('ocm.requests_processed', status.requests_processed)
            self.set_gauge('ocm.requests_sent', status.requests_sent)
            self.set_gauge('ocm.requests_failed', status.requests_failed)
            self.set_gauge('ocm.reports_generated', status.reports_generated)
            
            # Priority queue metrics
            if status.priority_queues:
                for priority, count in status.priority_queues.items():
                    self.set_gauge(f'ocm.queue_size.{priority.lower()}', count)
            
            # SSL status
            self.set_gauge('ocm.ssl_enabled', 1 if status.ssl_enabled else 0)
            
        except Exception as e:
            self.logger.error(f"Error collecting service metrics: {e}")
    
    async def _collect_module_metrics(self):
        """Collect metrics from all modules."""
        try:
            for name, module in self.modules.items():
                try:
                    if hasattr(module, 'get_status'):
                        module_status = module.get_status()
                        
                        # Record module health
                        is_active = module_status.get('active', False)
                        self.set_gauge(f'ocm.module.{name.lower()}.active', 1 if is_active else 0)
                        
                        # Record module-specific metrics
                        if name == 'RMM' and 'task_counts' in module_status:
                            for status_type, count in module_status['task_counts'].items():
                                self.set_gauge(f'ocm.rmm.{status_type}_requests', count)
                        
                        elif name == 'BTM' and 'stats' in module_status:
                            stats = module_status['stats']
                            self.set_gauge('ocm.btm.tasks_completed', stats.get('tasks_completed', 0))
                            self.set_gauge('ocm.btm.tasks_failed', stats.get('tasks_failed', 0))
                            self.set_gauge('ocm.btm.concurrent_tasks', stats.get('concurrent_tasks', 0))
                        
                        elif name == 'NMM' and 'connection_stats' in module_status:
                            conn_stats = module_status['connection_stats']
                            self.set_gauge('ocm.nmm.active_connections', conn_stats.get('active_connections', 0))
                            self.set_gauge('ocm.nmm.successful_deliveries', conn_stats.get('successful_deliveries', 0))
                        
                except Exception as e:
                    self.logger.error(f"Error collecting metrics from {name}: {e}")
                    # Record module error
                    self.set_gauge(f'ocm.module.{name.lower()}.error', 1)
        
        except Exception as e:
            self.logger.error(f"Error in module metrics collection: {e}")
    
    async def _system_monitor(self):
        """Monitor system resources."""
        while self.is_active:
            try:
                # CPU usage
                cpu_percent = psutil.cpu_percent(interval=1)
                self.set_gauge('system.cpu.usage_percent', cpu_percent)
                
                # Memory usage
                memory = psutil.virtual_memory()
                self.set_gauge('system.memory.usage_percent', memory.percent)
                self.set_gauge('system.memory.available_gb', memory.available / (1024**3))
                
                # Disk usage
                disk = psutil.disk_usage('/')
                disk_percent = (disk.used / disk.total) * 100
                self.set_gauge('system.disk.usage_percent', disk_percent)
                self.set_gauge('system.disk.free_gb', disk.free / (1024**3))
                
                # Network I/O
                net_io = psutil.net_io_counters()
                self.set_gauge('system.network.bytes_sent', net_io.bytes_sent)
                self.set_gauge('system.network.bytes_recv', net_io.bytes_recv)
                
                # Process info
                process = psutil.Process()
                self.set_gauge('process.memory_rss_mb', process.memory_info().rss / (1024**2))
                self.set_gauge('process.cpu_percent', process.cpu_percent())
                
                # Store system snapshot
                system_snapshot = {
                    'timestamp': datetime.now().isoformat(),
                    'cpu_percent': cpu_percent,
                    'memory_percent': memory.percent,
                    'disk_percent': disk_percent,
                    'process_memory_mb': process.memory_info().rss / (1024**2)
                }
                self.system_metrics.append(system_snapshot)
                
                # Check for threshold violations
                await self._check_system_thresholds(system_snapshot)
                
                await asyncio.sleep(30)  # System monitoring every 30 seconds
                
            except Exception as e:
                self.logger.error(f"Error in system monitoring: {e}")
                await asyncio.sleep(30)
    
    async def _check_system_thresholds(self, system_snapshot: Dict[str, Any]):
        """Check if system metrics exceed thresholds and generate alerts."""
        try:
            # CPU threshold
            if system_snapshot['cpu_percent'] > self.thresholds['cpu_usage']:
                await self._generate_alert(
                    AlertLevel.WARNING,
                    "High CPU Usage",
                    f"CPU usage is {system_snapshot['cpu_percent']:.1f}% (threshold: {self.thresholds['cpu_usage']}%)",
                    "system_monitor"
                )
            
            # Memory threshold
            if system_snapshot['memory_percent'] > self.thresholds['memory_usage']:
                await self._generate_alert(
                    AlertLevel.WARNING,
                    "High Memory Usage",
                    f"Memory usage is {system_snapshot['memory_percent']:.1f}% (threshold: {self.thresholds['memory_usage']}%)",
                    "system_monitor"
                )
            
            # Disk threshold
            if system_snapshot['disk_percent'] > self.thresholds['disk_usage']:
                await self._generate_alert(
                    AlertLevel.ERROR,
                    "High Disk Usage",
                    f"Disk usage is {system_snapshot['disk_percent']:.1f}% (threshold: {self.thresholds['disk_usage']}%)",
                    "system_monitor"
                )
        
        except Exception as e:
            self.logger.error(f"Error checking system thresholds: {e}")
    
    async def _health_checker(self):
        """Perform health checks on all components."""
        while self.is_active:
            try:
                self.stats['health_checks_performed'] += 1
                
                # Run all registered health checks
                for name, check_func in self.health_checks.items():
                    try:
                        start_time = time.time()
                        result = await check_func()
                        response_time = (time.time() - start_time) * 1000  # Convert to milliseconds
                        
                        health_result = HealthCheckResult(
                            component=name,
                            healthy=result.get('healthy', False),
                            message=result.get('message', ''),
                            timestamp=datetime.now(),
                            response_time=response_time
                        )
                        
                        self.health_results[name] = health_result
                        
                        # Record health metric
                        self.set_gauge(f'health.{name}', 1 if result.get('healthy') else 0)
                        self.record_timing(f'health.{name}.response_time', response_time)
                        
                        # Generate alert if unhealthy
                        if not result.get('healthy'):
                            await self._generate_alert(
                                AlertLevel.ERROR,
                                f"Health Check Failed: {name}",
                                result.get('message', 'Health check failed'),
                                f"health_check_{name}"
                            )
                    
                    except Exception as e:
                        self.logger.error(f"Health check failed for {name}: {e}")
                        
                        self.health_results[name] = HealthCheckResult(
                            component=name,
                            healthy=False,
                            message=f"Health check error: {e}",
                            timestamp=datetime.now()
                        )
                
                # Check module health
                await self._check_module_health()
                
                # Calculate overall health score
                self._calculate_health_score()
                
                await asyncio.sleep(self.health_check_interval)
                
            except Exception as e:
                self.logger.error(f"Error in health checking: {e}")
                await asyncio.sleep(self.health_check_interval)
    
    async def _check_module_health(self):
        """Check health of all OCM modules."""
        try:
            for name, module in self.modules.items():
                try:
                    if hasattr(module, 'health_check'):
                        is_healthy = await module.health_check()
                        
                        health_result = HealthCheckResult(
                            component=f"module_{name}",
                            healthy=is_healthy,
                            message="Module is healthy" if is_healthy else "Module is unhealthy",
                            timestamp=datetime.now()
                        )
                        
                        self.health_results[f"module_{name}"] = health_result
                        self.set_gauge(f'health.module.{name.lower()}', 1 if is_healthy else 0)
                        
                        if not is_healthy:
                            await self._generate_alert(
                                AlertLevel.ERROR,
                                f"Module Unhealthy: {name}",
                                f"Module {name} failed health check",
                                f"module_health_{name}"
                            )
                
                except Exception as e:
                    self.logger.error(f"Error checking health of module {name}: {e}")
        
        except Exception as e:
            self.logger.error(f"Error in module health checking: {e}")
    
    def _calculate_health_score(self):
        """Calculate overall system health score."""
        try:
            if not self.health_results:
                self.stats['system_health_score'] = 0.0
                return
            
            healthy_count = sum(1 for result in self.health_results.values() if result.healthy)
            total_count = len(self.health_results)
            
            health_score = (healthy_count / total_count) * 100.0
            self.stats['system_health_score'] = health_score
            self.set_gauge('system.health_score', health_score)
            
        except Exception as e:
            self.logger.error(f"Error calculating health score: {e}")
            self.stats['system_health_score'] = 0.0
    
    async def _generate_alert(self, level: AlertLevel, title: str, message: str, source: str):
        """Generate a system alert."""
        try:
            alert_id = f"{source}_{int(time.time())}"
            
            # Check if similar alert already exists (avoid spam)
            existing_alert = None
            for alert in self.active_alerts.values():
                if alert.title == title and alert.source == source and not alert.resolved:
                    existing_alert = alert
                    break
            
            if existing_alert:
                return  # Don't create duplicate alerts
            
            alert = Alert(
                alert_id=alert_id,
                level=level,
                title=title,
                message=message,
                source=source,
                timestamp=datetime.now()
            )
            
            self.active_alerts[alert_id] = alert
            self.alert_history.append(alert)
            
            self.stats['alerts_generated'] += 1
            self.stats['active_alerts_count'] = len([a for a in self.active_alerts.values() if not a.resolved])
            
            # Log the alert
            log_level = {
                AlertLevel.INFO: logging.INFO,
                AlertLevel.WARNING: logging.WARNING,
                AlertLevel.ERROR: logging.ERROR,
                AlertLevel.CRITICAL: logging.CRITICAL
            }.get(level, logging.INFO)
            
            self.logger.log(log_level, f"ALERT [{level.value.upper()}] {title}: {message}")
            
            # Record alert metric
            self.increment_counter(f'alerts.{level.value}')
            
        except Exception as e:
            self.logger.error(f"Error generating alert: {e}")
    
    async def _alert_manager(self):
        """Manage alert lifecycle and auto-resolution."""
        while self.is_active:
            try:
                current_time = datetime.now()
                
                # Auto-resolve old alerts (example: resolve after 1 hour if condition cleared)
                for alert_id, alert in list(self.active_alerts.items()):
                    if not alert.resolved:
                        # Check if alert should be auto-resolved
                        age = current_time - alert.timestamp
                        if age > timedelta(hours=1):
                            await self._resolve_alert(alert_id, "Auto-resolved: condition cleared or timeout")
                
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except Exception as e:
                self.logger.error(f"Error in alert management: {e}")
                await asyncio.sleep(300)
    
    async def _resolve_alert(self, alert_id: str, resolution_message: str = ""):
        """Resolve an active alert."""
        try:
            if alert_id in self.active_alerts:
                alert = self.active_alerts[alert_id]
                alert.resolved = True
                alert.resolved_at = datetime.now()
                
                self.logger.info(f"Alert resolved: {alert.title} - {resolution_message}")
                
                # Update active alerts count
                self.stats['active_alerts_count'] = len([a for a in self.active_alerts.values() if not a.resolved])
        
        except Exception as e:
            self.logger.error(f"Error resolving alert {alert_id}: {e}")
    
    async def _cleanup_old_data(self):
        """Clean up old metrics and alert data."""
        while self.is_active:
            try:
                current_time = datetime.now()
                cutoff_time = current_time - timedelta(seconds=self.retention_period)
                
                # Clean up old metrics
                for metric_name in list(self.metrics.keys()):
                    metric_points = self.metrics[metric_name]
                    # Remove old points
                    while metric_points and metric_points[0].timestamp < cutoff_time:
                        metric_points.popleft()
                    
                    # Remove empty metrics
                    if not metric_points:
                        del self.metrics[metric_name]
                
                # Clean up resolved alerts older than 7 days
                alert_cutoff = current_time - timedelta(days=7)
                self.active_alerts = {
                    alert_id: alert for alert_id, alert in self.active_alerts.items()
                    if not alert.resolved or alert.resolved_at > alert_cutoff
                }
                
                await asyncio.sleep(3600)  # Cleanup every hour
                
            except Exception as e:
                self.logger.error(f"Error in data cleanup: {e}")
                await asyncio.sleep(3600)
    
    async def _performance_analyzer(self):
        """Analyze performance trends and patterns."""
        while self.is_active:
            try:
                # Analyze request latencies
                if self.request_latencies:
                    latencies = list(self.request_latencies)
                    avg_latency = statistics.mean(latencies)
                    p95_latency = statistics.quantiles(latencies, n=20)[18] if len(latencies) >= 20 else max(latencies)
                    
                    self.set_gauge('performance.latency.avg', avg_latency)
                    self.set_gauge('performance.latency.p95', p95_latency)
                    
                    # Check if latency exceeds threshold
                    if avg_latency > self.thresholds['response_time']:
                        await self._generate_alert(
                            AlertLevel.WARNING,
                            "High Response Time",
                            f"Average response time is {avg_latency:.2f}s (threshold: {self.thresholds['response_time']}s)",
                            "performance_analyzer"
                        )
                
                # Calculate error rates
                total_requests = sum(self.success_counts.values()) + sum(self.error_counts.values())
                if total_requests > 0:
                    error_rate = (sum(self.error_counts.values()) / total_requests) * 100
                    self.set_gauge('performance.error_rate_percent', error_rate)
                    
                    if error_rate > self.thresholds['error_rate']:
                        await self._generate_alert(
                            AlertLevel.ERROR,
                            "High Error Rate",
                            f"Error rate is {error_rate:.1f}% (threshold: {self.thresholds['error_rate']}%)",
                            "performance_analyzer"
                        )
                
                await asyncio.sleep(300)  # Analyze every 5 minutes
                
            except Exception as e:
                self.logger.error(f"Error in performance analysis: {e}")
                await asyncio.sleep(300)
    
    # Built-in Health Check Functions
    
    async def _health_check_system_resources(self) -> Dict[str, Any]:
        """Check system resource availability."""
        try:
            cpu_usage = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            healthy = (
                cpu_usage < 95 and
                memory.percent < 95 and
                disk.percent < 95
            )
            
            return {
                'healthy': healthy,
                'message': f"CPU: {cpu_usage:.1f}%, Memory: {memory.percent:.1f}%, Disk: {disk.percent:.1f}%"
            }
        except Exception as e:
            return {'healthy': False, 'message': f"System resource check failed: {e}"}
    
    async def _health_check_disk_space(self) -> Dict[str, Any]:
        """Check available disk space."""
        try:
            disk = psutil.disk_usage('/')
            free_gb = disk.free / (1024**3)
            
            healthy = free_gb > 1.0  # At least 1GB free
            
            return {
                'healthy': healthy,
                'message': f"Free disk space: {free_gb:.1f}GB"
            }
        except Exception as e:
            return {'healthy': False, 'message': f"Disk space check failed: {e}"}
    
    async def _health_check_memory(self) -> Dict[str, Any]:
        """Check memory usage."""
        try:
            memory = psutil.virtual_memory()
            available_gb = memory.available / (1024**3)
            
            healthy = memory.percent < 90 and available_gb > 0.5
            
            return {
                'healthy': healthy,
                'message': f"Memory usage: {memory.percent:.1f}%, Available: {available_gb:.1f}GB"
            }
        except Exception as e:
            return {'healthy': False, 'message': f"Memory check failed: {e}"}
    
    async def _health_check_cpu(self) -> Dict[str, Any]:
        """Check CPU usage."""
        try:
            cpu_usage = psutil.cpu_percent(interval=1)
            
            healthy = cpu_usage < 90
            
            return {
                'healthy': healthy,
                'message': f"CPU usage: {cpu_usage:.1f}%"
            }
        except Exception as e:
            return {'healthy': False, 'message': f"CPU check failed: {e}"}
    
    async def _health_check_network(self) -> Dict[str, Any]:
        """Check network connectivity."""
        try:
            # Simple network check - could be enhanced with actual connectivity tests
            net_io = psutil.net_io_counters()
            
            healthy = True  # Basic check - network interface exists
            
            return {
                'healthy': healthy,
                'message': f"Network interfaces active, bytes sent: {net_io.bytes_sent}, received: {net_io.bytes_recv}"
            }
        except Exception as e:
            return {'healthy': False, 'message': f"Network check failed: {e}"}
    
    async def _health_check_ssl(self) -> Dict[str, Any]:
        """Check SSL certificate status."""
        try:
            if not self.ocm_service:
                return {'healthy': False, 'message': 'OCM service not available'}
            
            ssl_config = getattr(self.ocm_service, 'ssl_config', {})
            
            if not ssl_config.get('enabled'):
                return {'healthy': True, 'message': 'SSL not enabled'}
            
            # Basic SSL health check
            healthy = ssl_config.get('loaded_at') is not None
            
            return {
                'healthy': healthy,
                'message': f"SSL enabled, source: {ssl_config.get('source', 'unknown')}"
            }
        except Exception as e:
            return {'healthy': False, 'message': f"SSL check failed: {e}"}
    
    async def _health_check_database(self) -> Dict[str, Any]:
        """Check database connection."""
        try:
            # Check if DCM module is available and healthy
            if 'DCM' in self.modules:
                dcm = self.modules['DCM']
                if hasattr(dcm, 'health_check'):
                    is_healthy = await dcm.health_check()
                    return {
                        'healthy': is_healthy,
                        'message': 'Database connection healthy' if is_healthy else 'Database connection issues'
                    }
            
            return {'healthy': True, 'message': 'Database module not configured'}
        except Exception as e:
            return {'healthy': False, 'message': f"Database check failed: {e}"}
    
    async def _health_check_cache(self) -> Dict[str, Any]:
        """Check cache status."""
        try:
            # Basic cache health check - could be enhanced with actual cache tests
            return {
                'healthy': True,
                'message': 'Cache system operational'
            }
        except Exception as e:
            return {'healthy': False, 'message': f"Cache check failed: {e}"}
    
    # Public API Methods
    
    def get_metrics(self, metric_name: Optional[str] = None) -> Dict[str, Any]:
        """Get metrics data."""
        if metric_name:
            return {
                'metric': metric_name,
                'points': [asdict(point) for point in self.metrics.get(metric_name, [])],
                'summary': self.metric_summaries.get(metric_name, {})
            }
        else:
            return {
                'metrics': {
                    name: {
                        'points': [asdict(point) for point in points],
                        'summary': self.metric_summaries.get(name, {})
                    }
                    for name, points in self.metrics.items()
                }
            }
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get current health status of all components."""
        return {
            'overall_health_score': self.stats['system_health_score'],
            'components': {
                name: asdict(result) for name, result in self.health_results.items()
            },
            'timestamp': datetime.now().isoformat()
        }
    
    def get_alerts(self, active_only: bool = False) -> List[Dict[str, Any]]:
        """Get alerts."""
        if active_only:
            return [asdict(alert) for alert in self.active_alerts.values() if not alert.resolved]
        else:
            return [asdict(alert) for alert in self.alert_history]
    
    def get_system_metrics(self) -> List[Dict[str, Any]]:
        """Get system resource metrics."""
        return list(self.system_metrics)
    
    def record_request_latency(self, latency: float):
        """Record a request latency."""
        self.request_latencies.append(latency)
        self.record_timing('request.latency', latency)
    
    def record_request_success(self, endpoint: str):
        """Record a successful request."""
        self.success_counts[endpoint] += 1
        self.increment_counter(f'requests.success.{endpoint}')
    
    def record_request_error(self, endpoint: str, error_type: str):
        """Record a request error."""
        self.error_counts[f"{endpoint}_{error_type}"] += 1
        self.increment_counter(f'requests.error.{endpoint}.{error_type}')
    
    def get_status(self) -> Dict[str, Any]:
        """Get current MSM status."""
        return {
            'module': self.module_name,
            'active': self.is_active,
            'collection_interval': self.collection_interval,
            'metrics_count': len(self.metrics),
            'active_alerts': len([a for a in self.active_alerts.values() if not a.resolved]),
            'health_checks': len(self.health_checks),
            'system_health_score': self.stats['system_health_score'],
            'stats': self.stats.copy()
        } 