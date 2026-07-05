"""
Database Control Module (DCM) for OCM

This module is responsible for database operations with priority partitioning,
data management, backup operations, and ensuring data integrity. It provides
abstracted database access for all OCM components.
"""

import asyncio
import logging
import sqlite3
import json
import os
import shutil
from typing import Dict, Any, Optional, List, Union, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import threading
import queue
import hashlib
import time

class Priority(Enum):
    """Request priority levels."""
    A = "A"  # Highest priority
    B = "B"  # High priority
    C = "C"  # Medium priority
    D = "D"  # Low priority

class RequestStatus(Enum):
    """Request processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DELIVERED = "delivered"

@dataclass
class DatabaseEntry:
    """Database entry structure."""
    entry_id: str
    priority: str
    status: str
    data: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

@dataclass
class BackupInfo:
    """Backup information."""
    backup_id: str
    backup_path: str
    created_at: datetime
    size_bytes: int
    checksum: str
    description: str

class DatabaseControlModule:
    """
    Database Control Module (DCM)
    
    Manages OCM databases with:
    - Priority-based database partitioning (A, B, C, D)
    - Request tracking and history
    - Data integrity and validation
    - Automated backup and recovery
    - Transaction management
    - Performance optimization
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the DCM module."""
        self.logger = logging.getLogger(__name__)
        self.module_name = "DCM"
        self.is_active = False
        
        # Configuration
        self.config = config
        self.db_config = config.get('database', {})
        
        # Database settings
        self.db_type = self.db_config.get('type', 'sqlite')
        self.db_path = self.db_config.get('path', 'databases/ocm.db')
        self.enable_partitioning = self.db_config.get('priority_partitions', True)
        self.backup_enabled = self.db_config.get('backup_enabled', True)
        self.backup_interval = self.db_config.get('backup_interval', 3600)  # 1 hour
        self.max_backups = self.db_config.get('max_backups', 24)
        
        # Database connections (one per priority if partitioning enabled)
        self.connections = {}
        self.connection_lock = threading.Lock()
        
        # Database paths
        self.db_dir = os.path.dirname(self.db_path)
        if self.enable_partitioning:
            self.db_paths = {
                Priority.A.value: os.path.join(self.db_dir, 'ocm_priority_a.db'),
                Priority.B.value: os.path.join(self.db_dir, 'ocm_priority_b.db'),
                Priority.C.value: os.path.join(self.db_dir, 'ocm_priority_c.db'),
                Priority.D.value: os.path.join(self.db_dir, 'ocm_priority_d.db')
            }
        else:
            self.db_paths = {'main': self.db_path}
        
        # Backup information
        self.backup_dir = os.path.join(self.db_dir, 'backups')
        self.backup_history = []
        
        # Operation queue for database operations
        self.operation_queue = queue.Queue()
        self.worker_thread = None
        self.shutdown_event = threading.Event()
        
        # Statistics
        self.stats = {
            'operations_performed': 0,
            'records_inserted': 0,
            'records_updated': 0,
            'records_deleted': 0,
            'queries_executed': 0,
            'backups_created': 0,
            'start_time': None,
            'last_backup_time': None,
            'database_size_bytes': 0
        }
        
        # Create directories
        os.makedirs(self.db_dir, exist_ok=True)
        os.makedirs(self.backup_dir, exist_ok=True)
        
        self.logger.info(f"{self.module_name} initialized - DB type: {self.db_type}, Partitioning: {self.enable_partitioning}")
    
    async def start(self):
        """Start the DCM module."""
        try:
            self.is_active = True
            self.stats['start_time'] = datetime.now().isoformat()
            
            # Initialize databases
            await self._initialize_databases()
            
            # Start background worker thread
            self.worker_thread = threading.Thread(target=self._database_worker, daemon=True)
            self.worker_thread.start()
            
            # Start backup scheduler if enabled
            if self.backup_enabled:
                asyncio.create_task(self._backup_scheduler())
            
            # Start database maintenance
            asyncio.create_task(self._database_maintenance())
            
            # Load backup history
            await self._load_backup_history()
            
            self.logger.info("DCM started successfully - database system ready")
            
        except Exception as e:
            self.logger.error(f"Failed to start DCM: {e}")
            raise
    
    async def stop(self):
        """Stop the DCM module gracefully."""
        try:
            self.is_active = False
            self.shutdown_event.set()
            
            # Close all database connections
            with self.connection_lock:
                for conn in self.connections.values():
                    if conn:
                        conn.close()
                self.connections.clear()
            
            # Wait for worker thread to finish
            if self.worker_thread and self.worker_thread.is_alive():
                self.worker_thread.join(timeout=5)
            
            self.logger.info("DCM stopped successfully")
            
        except Exception as e:
            self.logger.error(f"Error stopping DCM: {e}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        try:
            # Test database connectivity
            db_healthy = True
            db_status = {}
            
            for priority, path in self.db_paths.items():
                conn = await self._get_connection(priority)
                if not conn:
                    db_healthy = False
                    db_status[priority] = {'connected': False, 'error': 'No connection'}
                    continue
                
                # Test simple query
                try:
                    cursor = conn.cursor()
                    cursor.execute("SELECT 1")
                    result = cursor.fetchone()
                    if not result:
                        db_healthy = False
                        db_status[priority] = {'connected': False, 'error': 'Query failed'}
                    else:
                        db_status[priority] = {'connected': True, 'error': None}
                except Exception as e:
                    db_healthy = False
                    db_status[priority] = {'connected': False, 'error': str(e)}
            
            is_healthy = self.is_active and db_healthy
            
            return {
                'healthy': is_healthy,
                'is_active': self.is_active,
                'database_healthy': db_healthy,
                'database_status': db_status,
                'module': 'dcm'
            }
            
        except Exception as e:
            self.logger.error(f"Database health check failed: {e}")
            return {
                'healthy': False,
                'error': str(e),
                'module': 'dcm'
            }
    
    async def _initialize_databases(self):
        """Initialize all databases and create necessary tables."""
        try:
            for priority, path in self.db_paths.items():
                self.logger.info(f"Initializing database for priority {priority}: {path}")
                
                # Create connection
                conn = sqlite3.connect(path, check_same_thread=False)
                conn.row_factory = sqlite3.Row  # Enable dict-like access
                
                # Store connection
                with self.connection_lock:
                    self.connections[priority] = conn
                
                # Create tables
                await self._create_tables(conn, priority)
                
                # Optimize database settings
                cursor = conn.cursor()
                cursor.execute("PRAGMA journal_mode = WAL")
                cursor.execute("PRAGMA synchronous = NORMAL")
                cursor.execute("PRAGMA cache_size = 10000")
                cursor.execute("PRAGMA temp_store = MEMORY")
                conn.commit()
            
            self.logger.info("All databases initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize databases: {e}")
            raise
    
    async def _create_tables(self, conn: sqlite3.Connection, priority: str):
        """Create database tables for a specific priority."""
        try:
            cursor = conn.cursor()
            
            # Request tracking table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS requests (
                    request_id TEXT PRIMARY KEY,
                    priority TEXT NOT NULL,
                    status TEXT NOT NULL,
                    request_type TEXT NOT NULL,
                    source_module TEXT NOT NULL,
                    data TEXT NOT NULL,
                    metadata TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    completed_at TEXT,
                    delivered_at TEXT,
                    retry_count INTEGER DEFAULT 0,
                    error_message TEXT,
                    checksum TEXT
                )
            """)
            
            # Reports table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS reports (
                    report_id TEXT PRIMARY KEY,
                    request_id TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    report_type TEXT NOT NULL,
                    format TEXT NOT NULL,
                    content TEXT,
                    file_path TEXT,
                    size_bytes INTEGER,
                    checksum TEXT,
                    generated_at TEXT NOT NULL,
                    delivered_at TEXT,
                    status TEXT NOT NULL,
                    metadata TEXT,
                    FOREIGN KEY (request_id) REFERENCES requests(request_id)
                )
            """)
            
            # Delivery log table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS delivery_log (
                    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    request_id TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    destination TEXT NOT NULL,
                    delivery_method TEXT NOT NULL,
                    status TEXT NOT NULL,
                    attempt_count INTEGER DEFAULT 1,
                    response_code INTEGER,
                    response_message TEXT,
                    delivery_time_ms INTEGER,
                    delivered_at TEXT NOT NULL,
                    metadata TEXT,
                    FOREIGN KEY (request_id) REFERENCES requests(request_id)
                )
            """)
            
            # Configuration table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS configuration (
                    config_key TEXT PRIMARY KEY,
                    config_value TEXT NOT NULL,
                    config_type TEXT NOT NULL,
                    description TEXT,
                    updated_at TEXT NOT NULL,
                    updated_by TEXT
                )
            """)
            
            # Statistics table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS statistics (
                    stat_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    priority TEXT NOT NULL,
                    stat_name TEXT NOT NULL,
                    stat_value REAL NOT NULL,
                    stat_type TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    metadata TEXT
                )
            """)
            
            # Create indexes for better performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_requests_priority ON requests(priority)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_requests_status ON requests(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_requests_created_at ON requests(created_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_reports_request_id ON reports(request_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_delivery_log_request_id ON delivery_log(request_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_statistics_priority ON statistics(priority)")
            
            conn.commit()
            self.logger.info(f"Tables created successfully for priority {priority}")
            
        except Exception as e:
            self.logger.error(f"Failed to create tables for priority {priority}: {e}")
            raise
    
    async def _get_connection(self, priority: str = 'main') -> Optional[sqlite3.Connection]:
        """Get database connection for specified priority."""
        try:
            with self.connection_lock:
                if priority in self.connections:
                    return self.connections[priority]
                else:
                    # If priority-specific connection doesn't exist, use main
                    return self.connections.get('main')
        except Exception as e:
            self.logger.error(f"Failed to get database connection for priority {priority}: {e}")
            return None
    
    def _database_worker(self):
        """Background worker thread for database operations."""
        while not self.shutdown_event.is_set():
            try:
                # Get operation from queue with timeout
                try:
                    operation = self.operation_queue.get(timeout=1)
                    self._execute_operation(operation)
                    self.operation_queue.task_done()
                except queue.Empty:
                    continue
                    
            except Exception as e:
                self.logger.error(f"Error in database worker: {e}")
    
    def _execute_operation(self, operation: Dict[str, Any]):
        """Execute a database operation."""
        try:
            op_type = operation.get('type')
            priority = operation.get('priority', 'main')
            
            # Get connection
            with self.connection_lock:
                conn = self.connections.get(priority)
                if not conn:
                    raise Exception(f"No connection available for priority {priority}")
            
            cursor = conn.cursor()
            
            if op_type == 'insert':
                cursor.execute(operation['query'], operation['params'])
                self.stats['records_inserted'] += 1
                
            elif op_type == 'update':
                cursor.execute(operation['query'], operation['params'])
                self.stats['records_updated'] += cursor.rowcount
                
            elif op_type == 'delete':
                cursor.execute(operation['query'], operation['params'])
                self.stats['records_deleted'] += cursor.rowcount
                
            elif op_type == 'select':
                cursor.execute(operation['query'], operation['params'])
                result = cursor.fetchall()
                if 'callback' in operation:
                    operation['callback'](result)
            
            conn.commit()
            self.stats['operations_performed'] += 1
            self.stats['queries_executed'] += 1
            
        except Exception as e:
            self.logger.error(f"Failed to execute database operation: {e}")
            # Rollback if needed
            if 'conn' in locals():
                conn.rollback()
    
    async def insert_request(self, request_id: str, priority: Priority, status: RequestStatus, 
                           request_type: str, source_module: str, data: Dict[str, Any], 
                           metadata: Dict[str, Any] = None) -> bool:
        """Insert a new request record."""
        try:
            priority_str = priority.value if self.enable_partitioning else 'main'
            
            # Calculate checksum
            data_str = json.dumps(data, sort_keys=True)
            checksum = hashlib.md5(data_str.encode()).hexdigest()
            
            operation = {
                'type': 'insert',
                'priority': priority_str,
                'query': """
                    INSERT INTO requests (
                        request_id, priority, status, request_type, source_module, 
                        data, metadata, created_at, updated_at, checksum
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                'params': (
                    request_id,
                    priority.value,
                    status.value,
                    request_type,
                    source_module,
                    json.dumps(data),
                    json.dumps(metadata or {}),
                    datetime.now().isoformat(),
                    datetime.now().isoformat(),
                    checksum
                )
            }
            
            self.operation_queue.put(operation)
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to insert request {request_id}: {e}")
            return False
    
    async def update_request_status(self, request_id: str, status: RequestStatus, 
                                  error_message: str = None, delivered_at: str = None) -> bool:
        """Update request status."""
        try:
            # Find which database contains this request
            priority_db = await self._find_request_database(request_id)
            if not priority_db:
                self.logger.error(f"Request {request_id} not found in any database")
                return False
            
            update_fields = ['status = ?', 'updated_at = ?']
            params = [status.value, datetime.now().isoformat()]
            
            if status == RequestStatus.COMPLETED:
                update_fields.append('completed_at = ?')
                params.append(datetime.now().isoformat())
            
            if error_message:
                update_fields.append('error_message = ?')
                params.append(error_message)
            
            if delivered_at:
                update_fields.append('delivered_at = ?')
                params.append(delivered_at)
            
            params.append(request_id)
            
            operation = {
                'type': 'update',
                'priority': priority_db,
                'query': f"UPDATE requests SET {', '.join(update_fields)} WHERE request_id = ?",
                'params': params
            }
            
            self.operation_queue.put(operation)
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update request status for {request_id}: {e}")
            return False
    
    async def get_request(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Get request by ID."""
        try:
            # Search all databases for the request
            for priority, path in self.db_paths.items():
                conn = await self._get_connection(priority)
                if not conn:
                    continue
                
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM requests WHERE request_id = ?", (request_id,))
                result = cursor.fetchone()
                
                if result:
                    row_dict = dict(result)
                    # Parse JSON fields
                    row_dict['data'] = json.loads(row_dict['data'])
                    row_dict['metadata'] = json.loads(row_dict['metadata'] or '{}')
                    return row_dict
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get request {request_id}: {e}")
            return None
    
    async def get_requests_by_priority(self, priority: Priority, status: RequestStatus = None, 
                                     limit: int = None) -> List[Dict[str, Any]]:
        """Get requests by priority and optionally by status."""
        try:
            priority_str = priority.value if self.enable_partitioning else 'main'
            conn = await self._get_connection(priority_str)
            if not conn:
                return []
            
            query = "SELECT * FROM requests WHERE priority = ?"
            params = [priority.value]
            
            if status:
                query += " AND status = ?"
                params.append(status.value)
            
            query += " ORDER BY created_at DESC"
            
            if limit:
                query += " LIMIT ?"
                params.append(limit)
            
            cursor = conn.cursor()
            cursor.execute(query, params)
            results = cursor.fetchall()
            
            requests = []
            for result in results:
                row_dict = dict(result)
                row_dict['data'] = json.loads(row_dict['data'])
                row_dict['metadata'] = json.loads(row_dict['metadata'] or '{}')
                requests.append(row_dict)
            
            return requests
            
        except Exception as e:
            self.logger.error(f"Failed to get requests by priority {priority.value}: {e}")
            return []
    
    async def insert_report(self, report_id: str, request_id: str, priority: Priority, 
                          report_type: str, format: str, content: str = None, 
                          file_path: str = None, size_bytes: int = None, 
                          metadata: Dict[str, Any] = None) -> bool:
        """Insert a report record."""
        try:
            priority_str = priority.value if self.enable_partitioning else 'main'
            
            # Calculate checksum if content provided
            checksum = None
            if content:
                checksum = hashlib.md5(content.encode()).hexdigest()
            elif file_path and os.path.exists(file_path):
                with open(file_path, 'rb') as f:
                    checksum = hashlib.md5(f.read()).hexdigest()
                if not size_bytes:
                    size_bytes = os.path.getsize(file_path)
            
            operation = {
                'type': 'insert',
                'priority': priority_str,
                'query': """
                    INSERT INTO reports (
                        report_id, request_id, priority, report_type, format, 
                        content, file_path, size_bytes, checksum, generated_at, 
                        status, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                'params': (
                    report_id,
                    request_id,
                    priority.value,
                    report_type,
                    format,
                    content,
                    file_path,
                    size_bytes,
                    checksum,
                    datetime.now().isoformat(),
                    'generated',
                    json.dumps(metadata or {})
                )
            }
            
            self.operation_queue.put(operation)
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to insert report {report_id}: {e}")
            return False
    
    async def log_delivery(self, request_id: str, priority: Priority, destination: str, 
                         delivery_method: str, status: str, response_code: int = None, 
                         response_message: str = None, delivery_time_ms: int = None, 
                         metadata: Dict[str, Any] = None) -> bool:
        """Log a delivery attempt."""
        try:
            priority_str = priority.value if self.enable_partitioning else 'main'
            
            operation = {
                'type': 'insert',
                'priority': priority_str,
                'query': """
                    INSERT INTO delivery_log (
                        request_id, priority, destination, delivery_method, status,
                        response_code, response_message, delivery_time_ms, 
                        delivered_at, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                'params': (
                    request_id,
                    priority.value,
                    destination,
                    delivery_method,
                    status,
                    response_code,
                    response_message,
                    delivery_time_ms,
                    datetime.now().isoformat(),
                    json.dumps(metadata or {})
                )
            }
            
            self.operation_queue.put(operation)
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to log delivery for request {request_id}: {e}")
            return False
    
    async def get_statistics(self, priority: Priority = None, 
                           start_date: datetime = None, end_date: datetime = None) -> Dict[str, Any]:
        """Get database statistics."""
        try:
            stats = {
                'total_requests': 0,
                'requests_by_status': {},
                'requests_by_priority': {},
                'total_reports': 0,
                'total_deliveries': 0,
                'successful_deliveries': 0,
                'failed_deliveries': 0,
                'average_processing_time': 0,
                'timestamp': datetime.now().isoformat()
            }
            
            # Query all databases or specific priority
            databases_to_query = {}
            if priority and self.enable_partitioning:
                databases_to_query[priority.value] = self.db_paths[priority.value]
            else:
                databases_to_query = self.db_paths
            
            for priority_key in databases_to_query:
                conn = await self._get_connection(priority_key)
                if not conn:
                    continue
                
                cursor = conn.cursor()
                
                # Count total requests
                cursor.execute("SELECT COUNT(*) FROM requests")
                count = cursor.fetchone()[0]
                stats['total_requests'] += count
                
                # Requests by status
                cursor.execute("SELECT status, COUNT(*) FROM requests GROUP BY status")
                for status, count in cursor.fetchall():
                    stats['requests_by_status'][status] = stats['requests_by_status'].get(status, 0) + count
                
                # Requests by priority
                cursor.execute("SELECT priority, COUNT(*) FROM requests GROUP BY priority")
                for priority_val, count in cursor.fetchall():
                    stats['requests_by_priority'][priority_val] = stats['requests_by_priority'].get(priority_val, 0) + count
                
                # Count reports
                cursor.execute("SELECT COUNT(*) FROM reports")
                count = cursor.fetchone()[0]
                stats['total_reports'] += count
                
                # Count deliveries
                cursor.execute("SELECT COUNT(*) FROM delivery_log")
                count = cursor.fetchone()[0]
                stats['total_deliveries'] += count
                
                # Successful deliveries
                cursor.execute("SELECT COUNT(*) FROM delivery_log WHERE status = 'success'")
                count = cursor.fetchone()[0]
                stats['successful_deliveries'] += count
                
                # Failed deliveries
                cursor.execute("SELECT COUNT(*) FROM delivery_log WHERE status = 'failed'")
                count = cursor.fetchone()[0]
                stats['failed_deliveries'] += count
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to get statistics: {e}")
            return {}
    
    async def _find_request_database(self, request_id: str) -> Optional[str]:
        """Find which database contains a specific request."""
        try:
            for priority in self.db_paths:
                conn = await self._get_connection(priority)
                if not conn:
                    continue
                
                cursor = conn.cursor()
                cursor.execute("SELECT 1 FROM requests WHERE request_id = ? LIMIT 1", (request_id,))
                if cursor.fetchone():
                    return priority
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to find database for request {request_id}: {e}")
            return None
    
    async def _backup_scheduler(self):
        """Schedule regular database backups."""
        while self.is_active:
            try:
                await self._create_backup()
                self.stats['last_backup_time'] = datetime.now().isoformat()
                
                await asyncio.sleep(self.backup_interval)
                
            except Exception as e:
                self.logger.error(f"Error in backup scheduler: {e}")
                await asyncio.sleep(self.backup_interval)
    
    async def _create_backup(self) -> bool:
        """Create database backup."""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_id = f"ocm_backup_{timestamp}"
            
            # Create backup for each database
            backup_paths = []
            total_size = 0
            
            for priority, db_path in self.db_paths.items():
                if not os.path.exists(db_path):
                    continue
                
                backup_filename = f"{backup_id}_{priority}.db"
                backup_path = os.path.join(self.backup_dir, backup_filename)
                
                # Copy database file
                shutil.copy2(db_path, backup_path)
                
                backup_paths.append(backup_path)
                total_size += os.path.getsize(backup_path)
            
            if not backup_paths:
                self.logger.warning("No databases found to backup")
                return False
            
            # Calculate checksum for backup verification
            combined_checksum = hashlib.md5()
            for backup_path in backup_paths:
                with open(backup_path, 'rb') as f:
                    combined_checksum.update(f.read())
            
            # Store backup information
            backup_info = BackupInfo(
                backup_id=backup_id,
                backup_path=self.backup_dir,
                created_at=datetime.now(),
                size_bytes=total_size,
                checksum=combined_checksum.hexdigest(),
                description=f"Automated backup of {len(backup_paths)} databases"
            )
            
            self.backup_history.append(backup_info)
            self.stats['backups_created'] += 1
            
            # Clean up old backups
            await self._cleanup_old_backups()
            
            self.logger.info(f"Database backup created: {backup_id} ({total_size} bytes)")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create database backup: {e}")
            return False
    
    async def _cleanup_old_backups(self):
        """Clean up old backup files."""
        try:
            if len(self.backup_history) <= self.max_backups:
                return
            
            # Sort backups by creation time
            self.backup_history.sort(key=lambda x: x.created_at)
            
            # Remove oldest backups
            backups_to_remove = self.backup_history[:-self.max_backups]
            
            for backup_info in backups_to_remove:
                # Remove backup files
                backup_pattern = f"{backup_info.backup_id}_*.db"
                import glob
                
                for backup_file in glob.glob(os.path.join(backup_info.backup_path, backup_pattern)):
                    try:
                        os.remove(backup_file)
                        self.logger.info(f"Removed old backup file: {backup_file}")
                    except Exception as e:
                        self.logger.error(f"Failed to remove backup file {backup_file}: {e}")
                
                # Remove from history
                self.backup_history.remove(backup_info)
            
        except Exception as e:
            self.logger.error(f"Error cleaning up old backups: {e}")
    
    async def _load_backup_history(self):
        """Load backup history from backup directory."""
        try:
            if not os.path.exists(self.backup_dir):
                return
            
            # Scan backup directory for existing backups
            import glob
            
            backup_files = glob.glob(os.path.join(self.backup_dir, "ocm_backup_*.db"))
            backup_groups = {}
            
            for backup_file in backup_files:
                filename = os.path.basename(backup_file)
                # Extract backup_id (remove priority suffix)
                backup_id = '_'.join(filename.split('_')[:-1]) if '_' in filename else filename.replace('.db', '')
                
                if backup_id not in backup_groups:
                    backup_groups[backup_id] = []
                
                backup_groups[backup_id].append(backup_file)
            
            # Create backup info for each group
            for backup_id, files in backup_groups.items():
                try:
                    # Get creation time from first file
                    creation_time = datetime.fromtimestamp(os.path.getctime(files[0]))
                    
                    # Calculate total size
                    total_size = sum(os.path.getsize(f) for f in files)
                    
                    backup_info = BackupInfo(
                        backup_id=backup_id,
                        backup_path=self.backup_dir,
                        created_at=creation_time,
                        size_bytes=total_size,
                        checksum="",  # Would need to calculate if needed
                        description=f"Existing backup with {len(files)} databases"
                    )
                    
                    self.backup_history.append(backup_info)
                    
                except Exception as e:
                    self.logger.error(f"Failed to process backup {backup_id}: {e}")
            
            # Sort by creation time
            self.backup_history.sort(key=lambda x: x.created_at, reverse=True)
            
            self.logger.info(f"Loaded {len(self.backup_history)} existing backups")
            
        except Exception as e:
            self.logger.error(f"Error loading backup history: {e}")
    
    async def _database_maintenance(self):
        """Perform database maintenance tasks."""
        while self.is_active:
            try:
                # Update database size statistics
                total_size = 0
                for priority, path in self.db_paths.items():
                    if os.path.exists(path):
                        total_size += os.path.getsize(path)
                
                self.stats['database_size_bytes'] = total_size
                
                # Vacuum databases periodically (weekly)
                current_time = datetime.now()
                if current_time.weekday() == 6 and current_time.hour == 2:  # Sunday 2 AM
                    await self._vacuum_databases()
                
                await asyncio.sleep(3600)  # Run every hour
                
            except Exception as e:
                self.logger.error(f"Error in database maintenance: {e}")
                await asyncio.sleep(3600)
    
    async def _vacuum_databases(self):
        """Vacuum all databases to optimize performance."""
        try:
            for priority, path in self.db_paths.items():
                if not os.path.exists(path):
                    continue
                
                conn = await self._get_connection(priority)
                if not conn:
                    continue
                
                cursor = conn.cursor()
                cursor.execute("VACUUM")
                conn.commit()
                
                self.logger.info(f"Vacuumed database for priority {priority}")
            
        except Exception as e:
            self.logger.error(f"Error vacuuming databases: {e}")
    
    def get_backup_history(self) -> List[Dict[str, Any]]:
        """Get backup history."""
        return [asdict(backup) for backup in self.backup_history]
    
    def get_status(self) -> Dict[str, Any]:
        """Get current DCM status."""
        return {
            'module': self.module_name,
            'active': self.is_active,
            'database_type': self.db_type,
            'partitioning_enabled': self.enable_partitioning,
            'active_databases': len(self.connections),
            'backup_enabled': self.backup_enabled,
            'total_backups': len(self.backup_history),
            'database_size_mb': round(self.stats['database_size_bytes'] / (1024 * 1024), 2),
            'stats': self.stats.copy()
        } 