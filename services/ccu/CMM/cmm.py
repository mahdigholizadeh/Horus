"""
Central Monitoring Module (CMM)

This module is responsible for receiving and consolidating all monitoring logs
from every microservice into a real-time log stream. It provides centralized
logging aggregation, filtering, and distribution capabilities.

Key Responsibilities:
- Collect logs from all microservices
- Aggregate and correlate log data
- Provide real-time log streaming
- Implement log filtering and search
- Manage log retention and rotation
- Distribute logs to other modules (GMM, CEIM)
- Generate monitoring alerts based on log patterns
"""

import asyncio
import logging
import json
import sqlite3
from typing import Dict, Any, List, Optional, Callable, Set
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum
from dataclasses import dataclass, asdict
from collections import deque, defaultdict
import threading
import re
import gzip
import os


class LogLevel(Enum):
    """Log level enumeration."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class LogSource(Enum):
    """Log source enumeration."""
    CCU = "ccu"
    RLA = "rla"
    TPP = "tpp"
    RCM = "rcm"
    JFA = "jfa"
    TD = "td"
    OCM = "ocm"
    EXTERNAL = "external"


@dataclass
class LogEntry:
    """Log entry data structure."""
    id: str
    timestamp: datetime
    level: LogLevel
    source: LogSource
    module: str
    message: str
    request_id: Optional[str] = None
    user_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    correlation_id: Optional[str] = None


@dataclass
class LogFilter:
    """Log filter criteria."""
    level: Optional[LogLevel] = None
    source: Optional[LogSource] = None
    module: Optional[str] = None
    message_pattern: Optional[str] = None
    request_id: Optional[str] = None
    time_range: Optional[tuple] = None
    tags: Optional[List[str]] = None


class CentralMonitoringModule:
    """
    Central Monitoring Module (CMM)
    
    Centralizes log collection, aggregation, and streaming across all services.
    """
    
    def __init__(self):
        """Initialize the CMM module."""
        self.logger = logging.getLogger(__name__)
        
        # Database setup
        self.db_path = Path("cmm_logs.db")
        self.init_database()
        
        # Configuration
        self.log_aggregation_enabled = True
        self.real_time_streaming_enabled = True
        self.buffer_size = 1000
        self.log_retention_days = 30
        self.max_log_size = 100 * 1024 * 1024  # 100MB
        self.compression_enabled = True
        
        # Log storage
        self.log_buffer = deque(maxlen=self.buffer_size)
        self.log_streams: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        
        # Real-time subscribers
        self.subscribers: Set[Callable[[LogEntry], None]] = set()
        self.filtered_subscribers: Dict[str, tuple] = {}  # subscriber_id -> (callback, filter)
        
        # Log processing
        self.log_queue = asyncio.Queue()
        self.is_processing = False
        self.processing_tasks = []
        
        # Statistics
        self.stats = {
            "total_logs": 0,
            "logs_by_level": defaultdict(int),
            "logs_by_source": defaultdict(int),
            "logs_by_module": defaultdict(int),
            "buffer_size": 0,
            "active_subscribers": 0,
            "log_rate": deque(maxlen=60),  # Last 60 minutes
            "last_activity": None
        }
        
        # Log patterns for alerts
        self.alert_patterns = [
            {
                "name": "High Error Rate",
                "pattern": r"error|exception|failed|failure",
                "level": LogLevel.ERROR,
                "threshold": 10,  # 10 errors per minute
                "window": 60  # 1 minute
            },
            {
                "name": "Critical System Events",
                "pattern": r"critical|emergency|fatal|crash",
                "level": LogLevel.CRITICAL,
                "threshold": 1,
                "window": 60
            }
        ]
        
        # Log rotation
        self.log_file_path = Path("logs/cmm_consolidated.log")
        self.log_file_path.parent.mkdir(exist_ok=True)
        
        self.logger.info("CMM module initialized")
    
    def init_database(self):
        """Initialize the logs database."""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            # Create logs table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS log_entries (
                    id TEXT PRIMARY KEY,
                    timestamp TIMESTAMP NOT NULL,
                    level TEXT NOT NULL,
                    source TEXT NOT NULL,
                    module TEXT NOT NULL,
                    message TEXT NOT NULL,
                    request_id TEXT,
                    user_id TEXT,
                    context TEXT,
                    tags TEXT,
                    correlation_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create indexes for performance
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_timestamp ON log_entries(timestamp)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_level ON log_entries(level)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_source ON log_entries(source)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_request_id ON log_entries(request_id)
            ''')
            
            # Create log statistics table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS log_statistics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    source TEXT NOT NULL,
                    level TEXT NOT NULL,
                    count INTEGER DEFAULT 0,
                    timeframe TEXT NOT NULL
                )
            ''')
            
            conn.commit()
            conn.close()
            
            self.logger.info("CMM database initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize CMM database: {e}")
            raise
    
    async def start(self):
        """Start the CMM module."""
        try:
            self.logger.info("Starting CMM module...")
            
            # Start processing tasks
            self.is_processing = True
            self.processing_tasks = [
                asyncio.create_task(self.process_log_queue()),
                asyncio.create_task(self.monitor_log_patterns()),
                asyncio.create_task(self.cleanup_old_logs()),
                asyncio.create_task(self.update_statistics()),
                asyncio.create_task(self.rotate_logs())
            ]
            
            # Start monitoring if enabled
            if self.log_aggregation_enabled:
                self.logger.info("Log aggregation started")
            
            if self.real_time_streaming_enabled:
                self.logger.info("Real-time log streaming started")
            
            self.logger.info("CMM module started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start CMM module: {e}")
            raise
    
    async def stop(self):
        """Stop the CMM module."""
        try:
            self.logger.info("Stopping CMM module...")
            
            # Stop processing
            self.is_processing = False
            
            # Cancel all tasks
            for task in self.processing_tasks:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            
            # Flush remaining logs
            await self.flush_logs()
            
            self.logger.info("CMM module stopped successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to stop CMM module: {e}")
            raise
    
    async def ingest_log(self, source: LogSource, module: str, level: LogLevel, 
                        message: str, request_id: str = None, user_id: str = None,
                        context: Dict[str, Any] = None, tags: List[str] = None,
                        correlation_id: str = None) -> str:
        """
        Ingest a log entry into the CMM system.
        
        Args:
            source: Log source service
            module: Source module name
            level: Log level
            message: Log message
            request_id: Associated request ID
            user_id: Associated user ID
            context: Additional context
            tags: Log tags
            correlation_id: Correlation ID for tracking
            
        Returns:
            Log entry ID
        """
        try:
            # Generate unique log ID
            log_id = f"{source.value}_{module}_{int(datetime.now().timestamp() * 1000000)}"
            
            # Create log entry
            log_entry = LogEntry(
                id=log_id,
                timestamp=datetime.now(),
                level=level,
                source=source,
                module=module,
                message=message,
                request_id=request_id,
                user_id=user_id,
                context=context,
                tags=tags or [],
                correlation_id=correlation_id
            )
            
            # Add to processing queue
            await self.log_queue.put(log_entry)
            
            # Update statistics
            self.stats["total_logs"] += 1
            self.stats["logs_by_level"][level.value] += 1
            self.stats["logs_by_source"][source.value] += 1
            self.stats["logs_by_module"][module] += 1
            self.stats["last_activity"] = datetime.now()
            
            return log_id
            
        except Exception as e:
            self.logger.error(f"Error ingesting log: {e}")
            raise
    
    async def process_log_queue(self):
        """Process logs from the queue."""
        while self.is_processing:
            try:
                # Get log from queue
                log_entry = await asyncio.wait_for(self.log_queue.get(), timeout=1.0)
                
                # Process the log
                await self.process_log_entry(log_entry)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                self.logger.error(f"Error processing log queue: {e}")
                await asyncio.sleep(1)
    
    async def process_log_entry(self, log_entry: LogEntry):
        """Process a single log entry."""
        try:
            # Store in buffer
            self.log_buffer.append(log_entry)
            
            # Store in stream-specific buffer
            stream_key = f"{log_entry.source.value}_{log_entry.module}"
            self.log_streams[stream_key].append(log_entry)
            
            # Save to database
            await self.save_log_to_database(log_entry)
            
            # Write to log file
            await self.write_log_to_file(log_entry)
            
            # Notify subscribers
            await self.notify_subscribers(log_entry)
            
            # Check for alert patterns
            await self.check_alert_patterns(log_entry)
            
        except Exception as e:
            self.logger.error(f"Error processing log entry: {e}")
    
    async def save_log_to_database(self, log_entry: LogEntry):
        """Save log entry to database."""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO log_entries (
                    id, timestamp, level, source, module, message,
                    request_id, user_id, context, tags, correlation_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                log_entry.id,
                log_entry.timestamp.isoformat(),
                log_entry.level.value,
                log_entry.source.value,
                log_entry.module,
                log_entry.message,
                log_entry.request_id,
                log_entry.user_id,
                json.dumps(log_entry.context) if log_entry.context else None,
                json.dumps(log_entry.tags) if log_entry.tags else None,
                log_entry.correlation_id
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"Error saving log to database: {e}")
    
    async def write_log_to_file(self, log_entry: LogEntry):
        """Write log entry to file."""
        try:
            # Format log entry
            log_line = f"[{log_entry.timestamp.isoformat()}] {log_entry.level.value.upper()} " \
                      f"{log_entry.source.value}.{log_entry.module}: {log_entry.message}"
            
            if log_entry.request_id:
                log_line += f" [req:{log_entry.request_id}]"
            
            if log_entry.correlation_id:
                log_line += f" [corr:{log_entry.correlation_id}]"
            
            log_line += "\n"
            
            # Write to file
            with open(self.log_file_path, 'a', encoding='utf-8') as f:
                f.write(log_line)
                
        except Exception as e:
            self.logger.error(f"Error writing log to file: {e}")
    
    async def notify_subscribers(self, log_entry: LogEntry):
        """Notify all subscribers about new log entry."""
        try:
            # Notify general subscribers
            for subscriber in self.subscribers:
                try:
                    await subscriber(log_entry)
                except Exception as e:
                    self.logger.error(f"Error notifying subscriber: {e}")
            
            # Notify filtered subscribers
            for subscriber_id, (callback, filter_criteria) in self.filtered_subscribers.items():
                try:
                    if self.matches_filter(log_entry, filter_criteria):
                        await callback(log_entry)
                except Exception as e:
                    self.logger.error(f"Error notifying filtered subscriber {subscriber_id}: {e}")
                    
        except Exception as e:
            self.logger.error(f"Error notifying subscribers: {e}")
    
    def matches_filter(self, log_entry: LogEntry, filter_criteria: LogFilter) -> bool:
        """Check if log entry matches filter criteria."""
        try:
            # Check level
            if filter_criteria.level and log_entry.level != filter_criteria.level:
                return False
            
            # Check source
            if filter_criteria.source and log_entry.source != filter_criteria.source:
                return False
            
            # Check module
            if filter_criteria.module and log_entry.module != filter_criteria.module:
                return False
            
            # Check message pattern
            if filter_criteria.message_pattern:
                if not re.search(filter_criteria.message_pattern, log_entry.message, re.IGNORECASE):
                    return False
            
            # Check request ID
            if filter_criteria.request_id and log_entry.request_id != filter_criteria.request_id:
                return False
            
            # Check time range
            if filter_criteria.time_range:
                start_time, end_time = filter_criteria.time_range
                if not (start_time <= log_entry.timestamp <= end_time):
                    return False
            
            # Check tags
            if filter_criteria.tags:
                if not log_entry.tags or not any(tag in log_entry.tags for tag in filter_criteria.tags):
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error matching filter: {e}")
            return False
    
    async def check_alert_patterns(self, log_entry: LogEntry):
        """Check if log entry matches any alert patterns."""
        try:
            for pattern in self.alert_patterns:
                if self.matches_alert_pattern(log_entry, pattern):
                    await self.trigger_alert(log_entry, pattern)
                    
        except Exception as e:
            self.logger.error(f"Error checking alert patterns: {e}")
    
    def matches_alert_pattern(self, log_entry: LogEntry, pattern: Dict[str, Any]) -> bool:
        """Check if log entry matches an alert pattern."""
        try:
            # Check level
            if pattern.get("level") and log_entry.level != pattern["level"]:
                return False
            
            # Check message pattern
            if pattern.get("pattern"):
                if not re.search(pattern["pattern"], log_entry.message, re.IGNORECASE):
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error matching alert pattern: {e}")
            return False
    
    async def trigger_alert(self, log_entry: LogEntry, pattern: Dict[str, Any]):
        """Trigger an alert based on pattern match."""
        try:
            # Check if threshold is exceeded
            recent_matches = await self.count_recent_matches(pattern)
            
            if recent_matches >= pattern["threshold"]:
                alert = {
                    "type": "log_pattern_alert",
                    "pattern_name": pattern["name"],
                    "log_entry": asdict(log_entry),
                    "match_count": recent_matches,
                    "threshold": pattern["threshold"],
                    "timestamp": datetime.now().isoformat()
                }
                
                # Notify alert subscribers
                await self.notify_alert_subscribers(alert)
                
        except Exception as e:
            self.logger.error(f"Error triggering alert: {e}")
    
    async def count_recent_matches(self, pattern: Dict[str, Any]) -> int:
        """Count recent matches for a pattern."""
        try:
            window_start = datetime.now() - timedelta(seconds=pattern["window"])
            count = 0
            
            for log_entry in self.log_buffer:
                if (log_entry.timestamp >= window_start and 
                    self.matches_alert_pattern(log_entry, pattern)):
                    count += 1
            
            return count
            
        except Exception as e:
            self.logger.error(f"Error counting recent matches: {e}")
            return 0
    
    async def notify_alert_subscribers(self, alert: Dict[str, Any]):
        """Notify alert subscribers."""
        # This would be implemented to notify the CEIM and other interested modules
        pass
    
    # Background tasks
    async def monitor_log_patterns(self):
        """Monitor log patterns for anomalies."""
        while self.is_processing:
            try:
                # Run pattern analysis every 5 minutes
                await asyncio.sleep(300)
                
                # Analyze recent logs for patterns
                await self.analyze_log_patterns()
                
            except Exception as e:
                self.logger.error(f"Error monitoring log patterns: {e}")
                await asyncio.sleep(300)
    
    async def analyze_log_patterns(self):
        """Analyze recent logs for patterns."""
        try:
            # Analyze error patterns
            recent_errors = [log for log in self.log_buffer 
                           if log.level in [LogLevel.ERROR, LogLevel.CRITICAL]]
            
            if len(recent_errors) > 50:  # High error rate
                self.logger.warning(f"High error rate detected: {len(recent_errors)} errors in buffer")
                
        except Exception as e:
            self.logger.error(f"Error analyzing log patterns: {e}")
    
    async def cleanup_old_logs(self):
        """Clean up old logs."""
        while self.is_processing:
            try:
                # Clean up every hour
                await asyncio.sleep(3600)
                
                cutoff_date = datetime.now() - timedelta(days=self.log_retention_days)
                
                conn = sqlite3.connect(str(self.db_path))
                cursor = conn.cursor()
                
                cursor.execute('''
                    DELETE FROM log_entries 
                    WHERE timestamp < ?
                ''', (cutoff_date.isoformat(),))
                
                deleted_count = cursor.rowcount
                
                conn.commit()
                conn.close()
                
                if deleted_count > 0:
                    self.logger.info(f"Cleaned up {deleted_count} old log entries")
                    
            except Exception as e:
                self.logger.error(f"Error cleaning up old logs: {e}")
                await asyncio.sleep(3600)
    
    async def update_statistics(self):
        """Update log statistics."""
        while self.is_processing:
            try:
                # Update every minute
                await asyncio.sleep(60)
                
                # Update buffer size
                self.stats["buffer_size"] = len(self.log_buffer)
                self.stats["active_subscribers"] = len(self.subscribers) + len(self.filtered_subscribers)
                
                # Update log rate
                current_minute_logs = sum(1 for log in self.log_buffer 
                                        if (datetime.now() - log.timestamp).total_seconds() < 60)
                self.stats["log_rate"].append(current_minute_logs)
                
            except Exception as e:
                self.logger.error(f"Error updating statistics: {e}")
                await asyncio.sleep(60)
    
    async def rotate_logs(self):
        """Rotate log files."""
        while self.is_processing:
            try:
                # Check every hour
                await asyncio.sleep(3600)
                
                # Check file size
                if self.log_file_path.exists() and self.log_file_path.stat().st_size > self.max_log_size:
                    # Rotate log file
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    rotated_file = self.log_file_path.with_suffix(f".{timestamp}.log")
                    
                    # Move current log file
                    self.log_file_path.rename(rotated_file)
                    
                    # Compress if enabled
                    if self.compression_enabled:
                        await self.compress_log_file(rotated_file)
                    
                    self.logger.info(f"Rotated log file to {rotated_file}")
                    
            except Exception as e:
                self.logger.error(f"Error rotating logs: {e}")
                await asyncio.sleep(3600)
    
    async def compress_log_file(self, file_path: Path):
        """Compress log file."""
        try:
            compressed_path = file_path.with_suffix(file_path.suffix + '.gz')
            
            with open(file_path, 'rb') as f_in:
                with gzip.open(compressed_path, 'wb') as f_out:
                    f_out.writelines(f_in)
            
            # Remove original file
            file_path.unlink()
            
            self.logger.info(f"Compressed log file to {compressed_path}")
            
        except Exception as e:
            self.logger.error(f"Error compressing log file: {e}")
    
    async def flush_logs(self):
        """Flush remaining logs."""
        try:
            # Process remaining logs in queue
            while not self.log_queue.empty():
                log_entry = await self.log_queue.get()
                await self.process_log_entry(log_entry)
                
        except Exception as e:
            self.logger.error(f"Error flushing logs: {e}")
    
    # Public API methods
    def subscribe(self, callback: Callable[[LogEntry], None]) -> str:
        """Subscribe to all log entries."""
        subscriber_id = f"sub_{len(self.subscribers)}_{int(datetime.now().timestamp())}"
        self.subscribers.add(callback)
        return subscriber_id
    
    def subscribe_filtered(self, callback: Callable[[LogEntry], None], 
                          filter_criteria: LogFilter) -> str:
        """Subscribe to filtered log entries."""
        subscriber_id = f"filtered_sub_{len(self.filtered_subscribers)}_{int(datetime.now().timestamp())}"
        self.filtered_subscribers[subscriber_id] = (callback, filter_criteria)
        return subscriber_id
    
    def unsubscribe(self, subscriber_id: str):
        """Unsubscribe from log entries."""
        if subscriber_id in self.filtered_subscribers:
            del self.filtered_subscribers[subscriber_id]
    
    async def search_logs(self, filter_criteria: LogFilter, limit: int = 1000) -> List[LogEntry]:
        """Search logs with filter criteria."""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            # Build query
            query = "SELECT * FROM log_entries WHERE 1=1"
            params = []
            
            if filter_criteria.level:
                query += " AND level = ?"
                params.append(filter_criteria.level.value)
            
            if filter_criteria.source:
                query += " AND source = ?"
                params.append(filter_criteria.source.value)
            
            if filter_criteria.module:
                query += " AND module = ?"
                params.append(filter_criteria.module)
            
            if filter_criteria.message_pattern:
                query += " AND message LIKE ?"
                params.append(f"%{filter_criteria.message_pattern}%")
            
            if filter_criteria.request_id:
                query += " AND request_id = ?"
                params.append(filter_criteria.request_id)
            
            if filter_criteria.time_range:
                start_time, end_time = filter_criteria.time_range
                query += " AND timestamp BETWEEN ? AND ?"
                params.extend([start_time.isoformat(), end_time.isoformat()])
            
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            # Convert to LogEntry objects
            logs = []
            for row in rows:
                log_entry = LogEntry(
                    id=row[0],
                    timestamp=datetime.fromisoformat(row[1]),
                    level=LogLevel(row[2]),
                    source=LogSource(row[3]),
                    module=row[4],
                    message=row[5],
                    request_id=row[6],
                    user_id=row[7],
                    context=json.loads(row[8]) if row[8] else None,
                    tags=json.loads(row[9]) if row[9] else None,
                    correlation_id=row[10]
                )
                logs.append(log_entry)
            
            conn.close()
            
            return logs
            
        except Exception as e:
            self.logger.error(f"Error searching logs: {e}")
            return []
    
    async def get_recent_logs(self, limit: int = 100) -> List[LogEntry]:
        """Get recent logs."""
        return list(reversed(list(self.log_buffer)[-limit:]))
    
    async def get_log_statistics(self) -> Dict[str, Any]:
        """Get log statistics."""
        return {
            'total_logs': self.stats["total_logs"],
            'logs_by_level': dict(self.stats["logs_by_level"]),
            'logs_by_source': dict(self.stats["logs_by_source"]),
            'logs_by_module': dict(self.stats["logs_by_module"]),
            'buffer_size': self.stats["buffer_size"],
            'active_subscribers': self.stats["active_subscribers"],
            'log_rate': list(self.stats["log_rate"])[-10:],
            'last_activity': self.stats["last_activity"].isoformat() if self.stats["last_activity"] else None
        }
    
    async def start_monitoring(self):
        """Start monitoring (called by CCU)."""
        if not self.is_processing:
            await self.start()
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of the CMM module."""
        return {
            'module': 'CMM',
            'is_processing': self.is_processing,
            'log_aggregation_enabled': self.log_aggregation_enabled,
            'real_time_streaming_enabled': self.real_time_streaming_enabled,
            'buffer_size': len(self.log_buffer),
            'queue_size': self.log_queue.qsize(),
            'subscribers': len(self.subscribers),
            'filtered_subscribers': len(self.filtered_subscribers),
            'stats': self.stats
        } 