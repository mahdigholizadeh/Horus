"""
Internal Micro Service Manager Module (IMSMM)

This module provides self-monitoring and health management capabilities for
the CCU's internal modules. It monitors the health of all internal modules,
manages their lifecycle, and provides automatic recovery mechanisms.

Key Responsibilities:
- Monitor health of all internal CCU modules
- Manage internal module lifecycle (start, stop, restart)
- Provide self-healing capabilities
- Track module performance and resource usage
- Generate health reports and alerts
- Coordinate module dependencies
- Implement circuit breaker patterns for internal modules
- Provide module status dashboard
"""

import asyncio
import logging
import json
import sqlite3
import psutil
import threading
from typing import Dict, Any, List, Optional, Callable, Set
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import traceback
import inspect
import gc


class ModuleStatus(Enum):
    """Module status enumeration."""
    UNKNOWN = "unknown"
    STARTING = "starting"
    ACTIVE = "active"
    IDLE = "idle"
    BUSY = "busy"
    WARNING = "warning"
    ERROR = "error"
    STOPPED = "stopped"
    RESTARTING = "restarting"
    MAINTENANCE = "maintenance"


class HealthLevel(Enum):
    """Health level enumeration."""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    CRITICAL = "critical"


@dataclass
class ModuleHealth:
    """Module health information."""
    module_name: str
    status: ModuleStatus
    health_level: HealthLevel
    cpu_usage: float
    memory_usage: float
    error_count: int
    last_activity: datetime
    uptime: float
    response_time: float
    success_rate: float
    details: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.details is None:
            self.details = {}


@dataclass
class ModuleMetrics:
    """Module performance metrics."""
    module_name: str
    timestamp: datetime
    cpu_usage: float
    memory_usage: float
    thread_count: int
    active_tasks: int
    completed_tasks: int
    failed_tasks: int
    average_response_time: float
    error_rate: float
    custom_metrics: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.custom_metrics is None:
            self.custom_metrics = {}


@dataclass
class ModuleEvent:
    """Module event record."""
    event_id: str
    module_name: str
    event_type: str
    severity: str
    message: str
    timestamp: datetime
    details: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.details is None:
            self.details = {}


class InternalMicroServiceManagerModule:
    """
    Internal Micro Service Manager Module (IMSMM)
    
    Manages the health and lifecycle of all internal CCU modules.
    """
    
    def __init__(self):
        """Initialize the IMSMM module."""
        self.logger = logging.getLogger(__name__)
        
        # Database setup
        self.db_path = Path("imsmm_health.db")
        self.init_database()
        
        # Module registry
        self.modules: Dict[str, Any] = {}
        self.module_health: Dict[str, ModuleHealth] = {}
        self.module_metrics: Dict[str, deque] = {}
        self.module_events: Dict[str, deque] = {}
        
        # Health monitoring configuration
        self.health_check_interval = 60  # seconds
        self.metrics_retention_hours = 24
        self.events_retention_hours = 48
        self.self_healing_enabled = True
        
        # Monitoring state
        self.is_monitoring = False
        self.monitoring_task = None
        
        # Internal modules to monitor
        self.internal_module_names = [
            "RTM", "MSMM", "SRMM", "CEIM", "CMM", "GMM", 
            "SMM", "DBM", "CTMM", "NMM"
        ]
        
        # Health thresholds
        self.health_thresholds = {
            "cpu_warning": 70.0,
            "cpu_critical": 90.0,
            "memory_warning": 70.0,
            "memory_critical": 90.0,
            "error_rate_warning": 5.0,
            "error_rate_critical": 10.0,
            "response_time_warning": 5.0,
            "response_time_critical": 10.0
        }
        
        # Circuit breaker states
        self.circuit_breakers: Dict[str, Dict[str, Any]] = {}
        
        # Recovery strategies
        self.recovery_strategies = {
            "restart_module": self._restart_module,
            "clear_cache": self._clear_module_cache,
            "reduce_load": self._reduce_module_load,
            "emergency_stop": self._emergency_stop_module
        }
        
        # Callbacks
        self.health_callbacks = []
        self.event_callbacks = []
        
        # Statistics
        self.stats = {
            "total_modules": 0,
            "active_modules": 0,
            "healthy_modules": 0,
            "warning_modules": 0,
            "error_modules": 0,
            "total_events": 0,
            "recovery_actions": 0,
            "last_health_check": None,
            "system_uptime": 0
        }
        
        # System startup time
        self.startup_time = datetime.now()
        
        self.logger.info("IMSMM module initialized successfully")
    
    def init_database(self):
        """Initialize the SQLite database for health tracking."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Module health table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS module_health (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        module_name TEXT NOT NULL,
                        status TEXT NOT NULL,
                        health_level TEXT NOT NULL,
                        cpu_usage REAL NOT NULL,
                        memory_usage REAL NOT NULL,
                        error_count INTEGER NOT NULL,
                        last_activity TIMESTAMP NOT NULL,
                        uptime REAL NOT NULL,
                        response_time REAL NOT NULL,
                        success_rate REAL NOT NULL,
                        details TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Module metrics table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS module_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        module_name TEXT NOT NULL,
                        timestamp TIMESTAMP NOT NULL,
                        cpu_usage REAL NOT NULL,
                        memory_usage REAL NOT NULL,
                        thread_count INTEGER NOT NULL,
                        active_tasks INTEGER NOT NULL,
                        completed_tasks INTEGER NOT NULL,
                        failed_tasks INTEGER NOT NULL,
                        average_response_time REAL NOT NULL,
                        error_rate REAL NOT NULL,
                        custom_metrics TEXT
                    )
                """)
                
                # Module events table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS module_events (
                        event_id TEXT PRIMARY KEY,
                        module_name TEXT NOT NULL,
                        event_type TEXT NOT NULL,
                        severity TEXT NOT NULL,
                        message TEXT NOT NULL,
                        timestamp TIMESTAMP NOT NULL,
                        details TEXT
                    )
                """)
                
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Failed to initialize database: {e}")
            raise
    
    def register_module(self, module_name: str, module_instance: Any):
        """Register a module for monitoring."""
        try:
            self.modules[module_name] = module_instance
            
            # Initialize health tracking
            self.module_health[module_name] = ModuleHealth(
                module_name=module_name,
                status=ModuleStatus.UNKNOWN,
                health_level=HealthLevel.GOOD,
                cpu_usage=0.0,
                memory_usage=0.0,
                error_count=0,
                last_activity=datetime.now(),
                uptime=0.0,
                response_time=0.0,
                success_rate=100.0
            )
            
            # Initialize metrics and events queues
            self.module_metrics[module_name] = deque(maxlen=1000)
            self.module_events[module_name] = deque(maxlen=500)
            
            # Initialize circuit breaker
            self.circuit_breakers[module_name] = {
                "state": "closed",
                "failure_count": 0,
                "last_failure": None,
                "recovery_timeout": 60
            }
            
            # Generate registration event
            self._generate_event(
                module_name=module_name,
                event_type="module_registered",
                severity="info",
                message=f"Module {module_name} registered for monitoring"
            )
            
            self.stats["total_modules"] += 1
            
            self.logger.info(f"Registered module for monitoring: {module_name}")
            
        except Exception as e:
            self.logger.error(f"Failed to register module {module_name}: {e}")
            raise
    
    def unregister_module(self, module_name: str):
        """Unregister a module from monitoring."""
        try:
            if module_name in self.modules:
                del self.modules[module_name]
                del self.module_health[module_name]
                del self.module_metrics[module_name]
                del self.module_events[module_name]
                del self.circuit_breakers[module_name]
                
                self.stats["total_modules"] -= 1
                
                self.logger.info(f"Unregistered module: {module_name}")
            
        except Exception as e:
            self.logger.error(f"Failed to unregister module {module_name}: {e}")
    
    async def start_monitoring(self):
        """Start health monitoring."""
        if self.is_monitoring:
            return
        
        self.is_monitoring = True
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        self.logger.info("Health monitoring started")
    
    async def stop_monitoring(self):
        """Stop health monitoring."""
        if not self.is_monitoring:
            return
        
        self.is_monitoring = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("Health monitoring stopped")
    
    async def _monitoring_loop(self):
        """Main monitoring loop."""
        while self.is_monitoring:
            try:
                # Perform health checks
                await self._perform_health_checks()
                
                # Update system statistics
                self._update_system_stats()
                
                # Clean up old data
                await self._cleanup_old_data()
                
                # Sleep for health check interval
                await asyncio.sleep(self.health_check_interval)
                
            except Exception as e:
                self.logger.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(30)  # Short sleep on error
    
    async def _perform_health_checks(self):
        """Perform health checks on all registered modules."""
        try:
            for module_name, module_instance in self.modules.items():
                await self._check_module_health(module_name, module_instance)
            
            self.stats["last_health_check"] = datetime.now()
            
        except Exception as e:
            self.logger.error(f"Health check error: {e}")
    
    async def _check_module_health(self, module_name: str, module_instance: Any):
        """Check health of a specific module."""
        try:
            start_time = datetime.now()
            
            # Get current health
            current_health = self.module_health[module_name]
            
            # Check if module has get_status method
            if hasattr(module_instance, 'get_status'):
                try:
                    status_result = module_instance.get_status()
                    if asyncio.iscoroutine(status_result):
                        status = await status_result
                    else:
                        status = status_result
                        
                    current_health.status = ModuleStatus.ACTIVE
                    current_health.last_activity = datetime.now()
                    
                    # Extract metrics from status
                    if isinstance(status, dict):
                        current_health.details = status
                        
                        # Update success rate if available
                        if 'success_rate' in status:
                            current_health.success_rate = status['success_rate']
                        
                        # Update error count if available
                        if 'error_count' in status:
                            current_health.error_count = status['error_count']
                    
                except Exception as e:
                    current_health.status = ModuleStatus.ERROR
                    current_health.error_count += 1
                    self.logger.error(f"Module {module_name} status check failed: {e}")
                    
                    # Generate error event
                    self._generate_event(
                        module_name=module_name,
                        event_type="health_check_failed",
                        severity="error",
                        message=f"Health check failed: {str(e)}"
                    )
            else:
                # Module doesn't have get_status method
                current_health.status = ModuleStatus.UNKNOWN
            
            # Calculate response time
            response_time = (datetime.now() - start_time).total_seconds()
            current_health.response_time = response_time
            
            # Get resource usage
            await self._update_module_resources(module_name, current_health)
            
            # Calculate uptime
            current_health.uptime = (datetime.now() - self.startup_time).total_seconds()
            
            # Determine health level
            current_health.health_level = self._calculate_health_level(current_health)
            
            # Create metrics record
            metrics = ModuleMetrics(
                module_name=module_name,
                timestamp=datetime.now(),
                cpu_usage=current_health.cpu_usage,
                memory_usage=current_health.memory_usage,
                thread_count=threading.active_count(),
                active_tasks=len([t for t in asyncio.all_tasks() if not t.done()]),
                completed_tasks=0,  # Would need to be tracked separately
                failed_tasks=current_health.error_count,
                average_response_time=current_health.response_time,
                error_rate=self._calculate_error_rate(module_name)
            )
            
            # Store metrics
            self.module_metrics[module_name].append(metrics)
            
            # Check for threshold violations
            await self._check_thresholds(module_name, current_health)
            
            # Apply self-healing if needed
            if self.self_healing_enabled:
                await self._apply_self_healing(module_name, current_health)
            
            # Persist health data
            await self._persist_health_data(current_health)
            
        except Exception as e:
            self.logger.error(f"Module health check failed for {module_name}: {e}")
    
    async def _update_module_resources(self, module_name: str, health: ModuleHealth):
        """Update module resource usage."""
        try:
            # Get current process
            process = psutil.Process()
            
            # Get CPU usage
            health.cpu_usage = process.cpu_percent()
            
            # Get memory usage
            memory_info = process.memory_info()
            health.memory_usage = (memory_info.rss / (1024 * 1024 * 1024)) * 100  # Convert to GB percentage
            
        except Exception as e:
            self.logger.error(f"Failed to update resource usage for {module_name}: {e}")
    
    def _calculate_health_level(self, health: ModuleHealth) -> HealthLevel:
        """Calculate overall health level for a module."""
        try:
            if health.status in [ModuleStatus.ERROR, ModuleStatus.STOPPED]:
                return HealthLevel.CRITICAL
            
            # Check thresholds
            critical_count = 0
            warning_count = 0
            
            if health.cpu_usage > self.health_thresholds["cpu_critical"]:
                critical_count += 1
            elif health.cpu_usage > self.health_thresholds["cpu_warning"]:
                warning_count += 1
            
            if health.memory_usage > self.health_thresholds["memory_critical"]:
                critical_count += 1
            elif health.memory_usage > self.health_thresholds["memory_warning"]:
                warning_count += 1
            
            if health.response_time > self.health_thresholds["response_time_critical"]:
                critical_count += 1
            elif health.response_time > self.health_thresholds["response_time_warning"]:
                warning_count += 1
            
            error_rate = self._calculate_error_rate(health.module_name)
            if error_rate > self.health_thresholds["error_rate_critical"]:
                critical_count += 1
            elif error_rate > self.health_thresholds["error_rate_warning"]:
                warning_count += 1
            
            # Determine health level
            if critical_count > 0:
                return HealthLevel.CRITICAL
            elif warning_count > 2:
                return HealthLevel.POOR
            elif warning_count > 0:
                return HealthLevel.FAIR
            elif health.success_rate > 95:
                return HealthLevel.EXCELLENT
            else:
                return HealthLevel.GOOD
            
        except Exception as e:
            self.logger.error(f"Failed to calculate health level: {e}")
            return HealthLevel.FAIR
    
    def _calculate_error_rate(self, module_name: str) -> float:
        """Calculate error rate for a module."""
        try:
            if module_name not in self.module_metrics:
                return 0.0
            
            metrics = list(self.module_metrics[module_name])
            if not metrics:
                return 0.0
            
            # Calculate error rate from recent metrics
            recent_metrics = metrics[-10:]  # Last 10 measurements
            total_tasks = sum(m.completed_tasks + m.failed_tasks for m in recent_metrics)
            total_errors = sum(m.failed_tasks for m in recent_metrics)
            
            if total_tasks == 0:
                return 0.0
            
            return (total_errors / total_tasks) * 100
            
        except Exception as e:
            self.logger.error(f"Failed to calculate error rate for {module_name}: {e}")
            return 0.0
    
    async def _check_thresholds(self, module_name: str, health: ModuleHealth):
        """Check if module health violates thresholds."""
        try:
            # Check CPU threshold
            if health.cpu_usage > self.health_thresholds["cpu_critical"]:
                self._generate_event(
                    module_name=module_name,
                    event_type="cpu_critical",
                    severity="critical",
                    message=f"CPU usage critical: {health.cpu_usage:.1f}%"
                )
            elif health.cpu_usage > self.health_thresholds["cpu_warning"]:
                self._generate_event(
                    module_name=module_name,
                    event_type="cpu_warning",
                    severity="warning",
                    message=f"CPU usage warning: {health.cpu_usage:.1f}%"
                )
            
            # Check memory threshold
            if health.memory_usage > self.health_thresholds["memory_critical"]:
                self._generate_event(
                    module_name=module_name,
                    event_type="memory_critical",
                    severity="critical",
                    message=f"Memory usage critical: {health.memory_usage:.1f}%"
                )
            elif health.memory_usage > self.health_thresholds["memory_warning"]:
                self._generate_event(
                    module_name=module_name,
                    event_type="memory_warning",
                    severity="warning",
                    message=f"Memory usage warning: {health.memory_usage:.1f}%"
                )
            
            # Check response time threshold
            if health.response_time > self.health_thresholds["response_time_critical"]:
                self._generate_event(
                    module_name=module_name,
                    event_type="response_time_critical",
                    severity="critical",
                    message=f"Response time critical: {health.response_time:.2f}s"
                )
            elif health.response_time > self.health_thresholds["response_time_warning"]:
                self._generate_event(
                    module_name=module_name,
                    event_type="response_time_warning",
                    severity="warning",
                    message=f"Response time warning: {health.response_time:.2f}s"
                )
            
        except Exception as e:
            self.logger.error(f"Threshold check failed for {module_name}: {e}")
    
    async def _apply_self_healing(self, module_name: str, health: ModuleHealth):
        """Apply self-healing strategies if needed."""
        try:
            if health.health_level == HealthLevel.CRITICAL:
                # Apply emergency strategies
                if health.cpu_usage > 95:
                    await self._reduce_module_load(module_name)
                elif health.memory_usage > 95:
                    await self._clear_module_cache(module_name)
                elif health.status == ModuleStatus.ERROR:
                    await self._restart_module(module_name)
                    
            elif health.health_level == HealthLevel.POOR:
                # Apply preventive strategies
                if health.error_count > 10:
                    await self._clear_module_cache(module_name)
                    
        except Exception as e:
            self.logger.error(f"Self-healing failed for {module_name}: {e}")
    
    async def _restart_module(self, module_name: str):
        """Restart a module."""
        try:
            if module_name not in self.modules:
                return
            
            module_instance = self.modules[module_name]
            
            # Stop module if it has stop method
            if hasattr(module_instance, 'stop'):
                if asyncio.iscoroutinefunction(module_instance.stop):
                    await module_instance.stop()
                else:
                    module_instance.stop()
            
            # Start module if it has start method
            if hasattr(module_instance, 'start'):
                if asyncio.iscoroutinefunction(module_instance.start):
                    await module_instance.start()
                else:
                    module_instance.start()
            
            # Update status
            self.module_health[module_name].status = ModuleStatus.RESTARTING
            
            # Generate event
            self._generate_event(
                module_name=module_name,
                event_type="module_restarted",
                severity="info",
                message=f"Module {module_name} restarted"
            )
            
            self.stats["recovery_actions"] += 1
            
        except Exception as e:
            self.logger.error(f"Failed to restart module {module_name}: {e}")
    
    async def _clear_module_cache(self, module_name: str):
        """Clear module cache."""
        try:
            if module_name not in self.modules:
                return
            
            module_instance = self.modules[module_name]
            
            # Clear cache if module has clear_cache method
            if hasattr(module_instance, 'clear_cache'):
                if asyncio.iscoroutinefunction(module_instance.clear_cache):
                    await module_instance.clear_cache()
                else:
                    module_instance.clear_cache()
            
            # Force garbage collection
            gc.collect()
            
            # Generate event
            self._generate_event(
                module_name=module_name,
                event_type="cache_cleared",
                severity="info",
                message=f"Cache cleared for module {module_name}"
            )
            
            self.stats["recovery_actions"] += 1
            
        except Exception as e:
            self.logger.error(f"Failed to clear cache for module {module_name}: {e}")
    
    async def _reduce_module_load(self, module_name: str):
        """Reduce module load."""
        try:
            if module_name not in self.modules:
                return
            
            module_instance = self.modules[module_name]
            
            # Reduce load if module has reduce_load method
            if hasattr(module_instance, 'reduce_load'):
                if asyncio.iscoroutinefunction(module_instance.reduce_load):
                    await module_instance.reduce_load()
                else:
                    module_instance.reduce_load()
            
            # Generate event
            self._generate_event(
                module_name=module_name,
                event_type="load_reduced",
                severity="info",
                message=f"Load reduced for module {module_name}"
            )
            
            self.stats["recovery_actions"] += 1
            
        except Exception as e:
            self.logger.error(f"Failed to reduce load for module {module_name}: {e}")
    
    async def _emergency_stop_module(self, module_name: str):
        """Emergency stop module."""
        try:
            if module_name not in self.modules:
                return
            
            module_instance = self.modules[module_name]
            
            # Emergency stop if module has emergency_stop method
            if hasattr(module_instance, 'emergency_stop'):
                if asyncio.iscoroutinefunction(module_instance.emergency_stop):
                    await module_instance.emergency_stop()
                else:
                    module_instance.emergency_stop()
            elif hasattr(module_instance, 'stop'):
                if asyncio.iscoroutinefunction(module_instance.stop):
                    await module_instance.stop()
                else:
                    module_instance.stop()
            
            # Update status
            self.module_health[module_name].status = ModuleStatus.STOPPED
            
            # Generate event
            self._generate_event(
                module_name=module_name,
                event_type="emergency_stop",
                severity="critical",
                message=f"Emergency stop executed for module {module_name}"
            )
            
            self.stats["recovery_actions"] += 1
            
        except Exception as e:
            self.logger.error(f"Failed to emergency stop module {module_name}: {e}")
    
    def _generate_event(self, module_name: str, event_type: str, severity: str, message: str, details: Optional[Dict[str, Any]] = None):
        """Generate a module event."""
        try:
            event_id = self._generate_event_id()
            
            event = ModuleEvent(
                event_id=event_id,
                module_name=module_name,
                event_type=event_type,
                severity=severity,
                message=message,
                timestamp=datetime.now(),
                details=details or {}
            )
            
            # Add to events queue
            self.module_events[module_name].append(event)
            
            # Persist event
            asyncio.create_task(self._persist_event(event))
            
            # Update statistics
            self.stats["total_events"] += 1
            
            # Notify callbacks
            for callback in self.event_callbacks:
                try:
                    callback(event)
                except Exception as e:
                    self.logger.error(f"Event callback failed: {e}")
            
        except Exception as e:
            self.logger.error(f"Failed to generate event: {e}")
    
    def _update_system_stats(self):
        """Update system statistics."""
        try:
            # Count modules by status
            active_count = 0
            healthy_count = 0
            warning_count = 0
            error_count = 0
            
            for health in self.module_health.values():
                if health.status == ModuleStatus.ACTIVE:
                    active_count += 1
                
                if health.health_level in [HealthLevel.EXCELLENT, HealthLevel.GOOD]:
                    healthy_count += 1
                elif health.health_level in [HealthLevel.FAIR, HealthLevel.POOR]:
                    warning_count += 1
                else:
                    error_count += 1
            
            self.stats["active_modules"] = active_count
            self.stats["healthy_modules"] = healthy_count
            self.stats["warning_modules"] = warning_count
            self.stats["error_modules"] = error_count
            self.stats["system_uptime"] = (datetime.now() - self.startup_time).total_seconds()
            
        except Exception as e:
            self.logger.error(f"Failed to update system stats: {e}")
    
    async def _cleanup_old_data(self):
        """Clean up old metrics and events."""
        try:
            cutoff_time = datetime.now() - timedelta(hours=self.metrics_retention_hours)
            
            # Clean up old metrics
            for module_name in self.module_metrics:
                metrics_queue = self.module_metrics[module_name]
                while metrics_queue and metrics_queue[0].timestamp < cutoff_time:
                    metrics_queue.popleft()
            
            # Clean up old events
            event_cutoff = datetime.now() - timedelta(hours=self.events_retention_hours)
            for module_name in self.module_events:
                events_queue = self.module_events[module_name]
                while events_queue and events_queue[0].timestamp < event_cutoff:
                    events_queue.popleft()
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup old data: {e}")
    
    async def _persist_health_data(self, health: ModuleHealth):
        """Persist health data to database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO module_health 
                    (module_name, status, health_level, cpu_usage, memory_usage, 
                     error_count, last_activity, uptime, response_time, success_rate, details)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    health.module_name,
                    health.status.value,
                    health.health_level.value,
                    health.cpu_usage,
                    health.memory_usage,
                    health.error_count,
                    health.last_activity.isoformat(),
                    health.uptime,
                    health.response_time,
                    health.success_rate,
                    json.dumps(health.details)
                ))
                
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Failed to persist health data: {e}")
    
    async def _persist_event(self, event: ModuleEvent):
        """Persist event to database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO module_events 
                    (event_id, module_name, event_type, severity, message, timestamp, details)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    event.event_id,
                    event.module_name,
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
        return f"evt_{uuid.uuid4().hex[:12]}"
    
    async def get_module_health(self, module_name: Optional[str] = None) -> Dict[str, Any]:
        """Get module health information."""
        try:
            if module_name:
                if module_name in self.module_health:
                    health = self.module_health[module_name]
                    return asdict(health)
                else:
                    return {}
            else:
                return {name: asdict(health) for name, health in self.module_health.items()}
                
        except Exception as e:
            self.logger.error(f"Failed to get module health: {e}")
            return {}
    
    async def get_module_metrics(self, module_name: str, hours: int = 1) -> List[Dict[str, Any]]:
        """Get module metrics for specified hours."""
        try:
            if module_name not in self.module_metrics:
                return []
            
            cutoff_time = datetime.now() - timedelta(hours=hours)
            metrics = []
            
            for metric in self.module_metrics[module_name]:
                if metric.timestamp >= cutoff_time:
                    metrics.append(asdict(metric))
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Failed to get module metrics: {e}")
            return []
    
    async def get_module_events(self, module_name: Optional[str] = None, hours: int = 24) -> List[Dict[str, Any]]:
        """Get module events for specified hours."""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            events = []
            
            if module_name:
                if module_name in self.module_events:
                    for event in self.module_events[module_name]:
                        if event.timestamp >= cutoff_time:
                            events.append(asdict(event))
            else:
                for module_events in self.module_events.values():
                    for event in module_events:
                        if event.timestamp >= cutoff_time:
                            events.append(asdict(event))
            
            # Sort by timestamp (newest first)
            events.sort(key=lambda x: x['timestamp'], reverse=True)
            
            return events
            
        except Exception as e:
            self.logger.error(f"Failed to get module events: {e}")
            return []
    
    def add_health_callback(self, callback: Callable[[str, ModuleHealth], None]):
        """Add health change callback."""
        self.health_callbacks.append(callback)
    
    def add_event_callback(self, callback: Callable[[ModuleEvent], None]):
        """Add event callback."""
        self.event_callbacks.append(callback)
    
    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the IMSMM module."""
        return {
            'is_monitoring': self.is_monitoring,
            'registered_modules': len(self.modules),
            'self_healing_enabled': self.self_healing_enabled,
            'health_check_interval': self.health_check_interval,
            'statistics': self.stats.copy()
        }
    
    async def start(self):
        """Start the IMSMM module."""
        await self.start_monitoring()
        self.logger.info("IMSMM module started")
    
    async def stop(self):
        """Stop the IMSMM module."""
        await self.stop_monitoring()
        self.logger.info("IMSMM module stopped") 