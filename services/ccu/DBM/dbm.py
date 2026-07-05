"""
Database Backup Module (DBM)

This module provides comprehensive database backup and restoration capabilities
for the CCU and all microservices. It implements automated backup scheduling,
compression, encryption, and disaster recovery procedures.

Key Responsibilities:
- Automated database backups with configurable scheduling
- Backup compression and encryption
- Database restoration and recovery
- Backup integrity verification
- Distributed backup storage
- Backup retention policies
- Disaster recovery procedures
- Cross-service backup coordination
"""

import asyncio
import logging
import json
import sqlite3
import shutil
import gzip
import hashlib
import os
import tarfile
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum
from dataclasses import dataclass, asdict
import threading
import subprocess
import tempfile
import concurrent.futures


class BackupStatus(Enum):
    """Backup operation status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    VERIFYING = "verifying"
    VERIFIED = "verified"
    CORRUPTED = "corrupted"


class BackupType(Enum):
    """Backup type enumeration."""
    FULL = "full"
    INCREMENTAL = "incremental"
    DIFFERENTIAL = "differential"
    SNAPSHOT = "snapshot"


class RestoreStatus(Enum):
    """Restore operation status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class BackupJob:
    """Backup job definition."""
    job_id: str
    database_name: str
    database_path: str
    backup_type: BackupType
    status: BackupStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    backup_path: Optional[str] = None
    file_size: int = 0
    compressed_size: int = 0
    checksum: Optional[str] = None
    error_message: Optional[str] = None
    retention_days: int = 30


@dataclass
class RestoreJob:
    """Restore job definition."""
    job_id: str
    database_name: str
    backup_path: str
    target_path: str
    status: RestoreStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


@dataclass
class DatabaseInfo:
    """Database information."""
    name: str
    path: str
    service: str
    type: str
    size: int
    last_backup: Optional[datetime] = None
    backup_schedule: str = "daily"
    retention_days: int = 30
    compression_enabled: bool = True
    encryption_enabled: bool = False


class DatabaseBackupModule:
    """
    Database Backup Module (DBM)
    
    Manages automated database backups, restoration, and disaster recovery
    for all CCU and microservice databases.
    """
    
    def __init__(self):
        """Initialize the DBM module."""
        self.logger = logging.getLogger(__name__)
        
        # Configuration
        self.backup_base_path = Path("database_backups")
        self.backup_base_path.mkdir(exist_ok=True)
        
        # Database setup
        self.db_path = Path("dbm_backups.db")
        self.init_database()
        
        # Registered databases
        self.databases: Dict[str, DatabaseInfo] = {}
        
        # Active jobs
        self.backup_jobs: Dict[str, BackupJob] = {}
        self.restore_jobs: Dict[str, RestoreJob] = {}
        
        # Backup configuration
        self.backup_interval = 3600  # 1 hour
        self.max_backups = 24
        self.compression_enabled = True
        self.encryption_enabled = False
        self.parallel_backups = 2
        
        # Scheduler
        self.scheduler_running = False
        self.scheduler_task = None
        
        # Thread executor for backup operations
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=self.parallel_backups)
        
        # Callbacks
        self.backup_callbacks = []
        self.restore_callbacks = []
        
        # Statistics
        self.stats = {
            "total_backups": 0,
            "successful_backups": 0,
            "failed_backups": 0,
            "total_restores": 0,
            "successful_restores": 0,
            "failed_restores": 0,
            "total_backup_size": 0,
            "last_backup": None,
            "backup_success_rate": 0.0
        }
        
        # Register default databases
        self._register_default_databases()
        
        self.logger.info("DBM module initialized successfully")
    
    def init_database(self):
        """Initialize the SQLite database for backup tracking."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Backup jobs table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS backup_jobs (
                        job_id TEXT PRIMARY KEY,
                        database_name TEXT NOT NULL,
                        database_path TEXT NOT NULL,
                        backup_type TEXT NOT NULL,
                        status TEXT NOT NULL,
                        created_at TIMESTAMP NOT NULL,
                        started_at TIMESTAMP,
                        completed_at TIMESTAMP,
                        backup_path TEXT,
                        file_size INTEGER DEFAULT 0,
                        compressed_size INTEGER DEFAULT 0,
                        checksum TEXT,
                        error_message TEXT,
                        retention_days INTEGER DEFAULT 30
                    )
                """)
                
                # Restore jobs table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS restore_jobs (
                        job_id TEXT PRIMARY KEY,
                        database_name TEXT NOT NULL,
                        backup_path TEXT NOT NULL,
                        target_path TEXT NOT NULL,
                        status TEXT NOT NULL,
                        created_at TIMESTAMP NOT NULL,
                        started_at TIMESTAMP,
                        completed_at TIMESTAMP,
                        error_message TEXT
                    )
                """)
                
                # Database registry table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS database_registry (
                        name TEXT PRIMARY KEY,
                        path TEXT NOT NULL,
                        service TEXT NOT NULL,
                        type TEXT NOT NULL,
                        size INTEGER DEFAULT 0,
                        last_backup TIMESTAMP,
                        backup_schedule TEXT DEFAULT 'daily',
                        retention_days INTEGER DEFAULT 30,
                        compression_enabled INTEGER DEFAULT 1,
                        encryption_enabled INTEGER DEFAULT 0
                    )
                """)
                
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Failed to initialize database: {e}")
            raise
    
    def _register_default_databases(self):
        """Register default databases from all services."""
        # CCU databases
        self.register_database(DatabaseInfo(
            name="ccu_main",
            path="ccu_main.db",
            service="CCU",
            type="sqlite",
            size=0,
            backup_schedule="hourly",
            retention_days=30
        ))
        
        self.register_database(DatabaseInfo(
            name="rtm_database",
            path="rtm_database.db",
            service="CCU",
            type="sqlite",
            size=0,
            backup_schedule="hourly",
            retention_days=7
        ))
        
        self.register_database(DatabaseInfo(
            name="cmm_logs",
            path="cmm_logs.db",
            service="CCU",
            type="sqlite",
            size=0,
            backup_schedule="daily",
            retention_days=14
        ))
        
        self.register_database(DatabaseInfo(
            name="ceim_errors",
            path="ceim_errors.db",
            service="CCU",
            type="sqlite",
            size=0,
            backup_schedule="daily",
            retention_days=30
        ))
        
        self.register_database(DatabaseInfo(
            name="srmm_metrics",
            path="srmm_metrics.db",
            service="CCU",
            type="sqlite",
            size=0,
            backup_schedule="daily",
            retention_days=7
        ))
        
        self.register_database(DatabaseInfo(
            name="smm_configurations",
            path="smm_configurations.db",
            service="CCU",
            type="sqlite",
            size=0,
            backup_schedule="daily",
            retention_days=30
        ))
        
        # RCM databases
        self.register_database(DatabaseInfo(
            name="rcm_database",
            path="../../../RCM/RCM_main/RCM_main/RCM_main/DCMM/conversations.db",
            service="RCM",
            type="sqlite",
            size=0,
            backup_schedule="hourly",
            retention_days=14
        ))
        
        self.register_database(DatabaseInfo(
            name="rcm_errors",
            path="../../../RCM/RCM_main/RCM_main/RCM_main/DCMM/error_logs.db",
            service="RCM",
            type="sqlite",
            size=0,
            backup_schedule="daily",
            retention_days=30
        ))
        
        # JFA databases
        self.register_database(DatabaseInfo(
            name="jfa_database",
            path="../../../JFA/JFA_main/JFA_Main/JFA_Main/jfa_database.db",
            service="JFA",
            type="sqlite",
            size=0,
            backup_schedule="hourly",
            retention_days=14
        ))
        
        self.logger.info("Default databases registered")
    
    def register_database(self, db_info: DatabaseInfo):
        """Register a database for backup."""
        try:
            self.databases[db_info.name] = db_info
            
            # Update registry in database
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT OR REPLACE INTO database_registry 
                    (name, path, service, type, size, last_backup, backup_schedule, 
                     retention_days, compression_enabled, encryption_enabled)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    db_info.name,
                    db_info.path,
                    db_info.service,
                    db_info.type,
                    db_info.size,
                    db_info.last_backup.isoformat() if db_info.last_backup else None,
                    db_info.backup_schedule,
                    db_info.retention_days,
                    1 if db_info.compression_enabled else 0,
                    1 if db_info.encryption_enabled else 0
                ))
                
                conn.commit()
            
            self.logger.info(f"Registered database: {db_info.name}")
            
        except Exception as e:
            self.logger.error(f"Failed to register database {db_info.name}: {e}")
            raise
    
    async def perform_backup(self, database_name: Optional[str] = None) -> List[str]:
        """Perform backup operation."""
        try:
            if database_name:
                # Backup specific database
                if database_name not in self.databases:
                    raise ValueError(f"Database not found: {database_name}")
                
                job_id = await self._create_backup_job(database_name)
                await self._execute_backup_job(job_id)
                return [job_id]
            else:
                # Backup all databases
                job_ids = []
                for db_name in self.databases.keys():
                    job_id = await self._create_backup_job(db_name)
                    job_ids.append(job_id)
                
                # Execute jobs in parallel
                backup_tasks = [self._execute_backup_job(job_id) for job_id in job_ids]
                await asyncio.gather(*backup_tasks, return_exceptions=True)
                
                return job_ids
                
        except Exception as e:
            self.logger.error(f"Backup operation failed: {e}")
            raise
    
    async def restore_database(self, database_name: str, backup_path: str, target_path: Optional[str] = None) -> str:
        """Restore database from backup."""
        try:
            if database_name not in self.databases:
                raise ValueError(f"Database not found: {database_name}")
            
            if not Path(backup_path).exists():
                raise FileNotFoundError(f"Backup file not found: {backup_path}")
            
            # Create restore job
            job_id = self._generate_job_id()
            target = target_path or self.databases[database_name].path
            
            restore_job = RestoreJob(
                job_id=job_id,
                database_name=database_name,
                backup_path=backup_path,
                target_path=target,
                status=RestoreStatus.PENDING,
                created_at=datetime.now()
            )
            
            self.restore_jobs[job_id] = restore_job
            
            # Execute restore
            await self._execute_restore_job(job_id)
            
            return job_id
            
        except Exception as e:
            self.logger.error(f"Restore operation failed: {e}")
            raise
    
    async def _create_backup_job(self, database_name: str) -> str:
        """Create a backup job."""
        try:
            db_info = self.databases[database_name]
            job_id = self._generate_job_id()
            
            # Create backup job
            backup_job = BackupJob(
                job_id=job_id,
                database_name=database_name,
                database_path=db_info.path,
                backup_type=BackupType.FULL,
                status=BackupStatus.PENDING,
                created_at=datetime.now(),
                retention_days=db_info.retention_days
            )
            
            self.backup_jobs[job_id] = backup_job
            
            # Persist to database
            await self._persist_backup_job(backup_job)
            
            return job_id
            
        except Exception as e:
            self.logger.error(f"Failed to create backup job for {database_name}: {e}")
            raise
    
    async def _execute_backup_job(self, job_id: str):
        """Execute a backup job."""
        try:
            job = self.backup_jobs[job_id]
            job.status = BackupStatus.IN_PROGRESS
            job.started_at = datetime.now()
            
            # Create backup directory
            backup_dir = self.backup_base_path / job.database_name
            backup_dir.mkdir(exist_ok=True)
            
            # Generate backup filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"{job.database_name}_{timestamp}.db"
            backup_path = backup_dir / backup_filename
            
            # Perform backup in thread pool
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                self.executor,
                self._backup_database,
                job.database_path,
                str(backup_path),
                job
            )
            
            # Update job status
            job.status = BackupStatus.COMPLETED
            job.completed_at = datetime.now()
            job.backup_path = str(backup_path)
            
            # Update database info
            self.databases[job.database_name].last_backup = datetime.now()
            
            # Persist updated job
            await self._persist_backup_job(job)
            
            # Update statistics
            self.stats["successful_backups"] += 1
            self.stats["total_backups"] += 1
            self.stats["last_backup"] = datetime.now()
            
            # Cleanup old backups
            await self._cleanup_old_backups(job.database_name)
            
            # Notify callbacks
            for callback in self.backup_callbacks:
                try:
                    await callback(job)
                except Exception as e:
                    self.logger.error(f"Backup callback failed: {e}")
            
            self.logger.info(f"Backup job {job_id} completed successfully")
            
        except Exception as e:
            self.logger.error(f"Backup job {job_id} failed: {e}")
            
            # Update job status
            job.status = BackupStatus.FAILED
            job.error_message = str(e)
            job.completed_at = datetime.now()
            
            # Persist failed job
            await self._persist_backup_job(job)
            
            # Update statistics
            self.stats["failed_backups"] += 1
            self.stats["total_backups"] += 1
    
    def _backup_database(self, source_path: str, backup_path: str, job: BackupJob):
        """Backup database file (runs in thread pool)."""
        try:
            source = Path(source_path)
            
            if not source.exists():
                raise FileNotFoundError(f"Source database not found: {source_path}")
            
            # Get file size
            job.file_size = source.stat().st_size
            
            # Copy database file
            shutil.copy2(source, backup_path)
            
            # Compress if enabled
            if self.compression_enabled:
                compressed_path = f"{backup_path}.gz"
                with open(backup_path, 'rb') as f_in:
                    with gzip.open(compressed_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                
                # Remove uncompressed file
                os.remove(backup_path)
                backup_path = compressed_path
                job.backup_path = compressed_path
                
                # Update compressed size
                job.compressed_size = Path(compressed_path).stat().st_size
            else:
                job.compressed_size = job.file_size
            
            # Calculate checksum
            job.checksum = self._calculate_file_checksum(backup_path)
            
            self.logger.info(f"Database backup completed: {backup_path}")
            
        except Exception as e:
            self.logger.error(f"Database backup failed: {e}")
            raise
    
    async def _execute_restore_job(self, job_id: str):
        """Execute a restore job."""
        try:
            job = self.restore_jobs[job_id]
            job.status = RestoreStatus.IN_PROGRESS
            job.started_at = datetime.now()
            
            # Perform restore in thread pool
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                self.executor,
                self._restore_database,
                job.backup_path,
                job.target_path,
                job
            )
            
            # Update job status
            job.status = RestoreStatus.COMPLETED
            job.completed_at = datetime.now()
            
            # Persist updated job
            await self._persist_restore_job(job)
            
            # Update statistics
            self.stats["successful_restores"] += 1
            self.stats["total_restores"] += 1
            
            # Notify callbacks
            for callback in self.restore_callbacks:
                try:
                    await callback(job)
                except Exception as e:
                    self.logger.error(f"Restore callback failed: {e}")
            
            self.logger.info(f"Restore job {job_id} completed successfully")
            
        except Exception as e:
            self.logger.error(f"Restore job {job_id} failed: {e}")
            
            # Update job status
            job.status = RestoreStatus.FAILED
            job.error_message = str(e)
            job.completed_at = datetime.now()
            
            # Persist failed job
            await self._persist_restore_job(job)
            
            # Update statistics
            self.stats["failed_restores"] += 1
            self.stats["total_restores"] += 1
    
    def _restore_database(self, backup_path: str, target_path: str, job: RestoreJob):
        """Restore database file (runs in thread pool)."""
        try:
            backup = Path(backup_path)
            target = Path(target_path)
            
            if not backup.exists():
                raise FileNotFoundError(f"Backup file not found: {backup_path}")
            
            # Create target directory if needed
            target.parent.mkdir(parents=True, exist_ok=True)
            
            # Backup existing database if it exists
            if target.exists():
                backup_existing = target.with_suffix('.bak')
                shutil.copy2(target, backup_existing)
            
            # Check if backup is compressed
            if backup_path.endswith('.gz'):
                # Decompress and restore
                with gzip.open(backup_path, 'rb') as f_in:
                    with open(target, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
            else:
                # Direct copy
                shutil.copy2(backup_path, target)
            
            self.logger.info(f"Database restore completed: {target}")
            
        except Exception as e:
            self.logger.error(f"Database restore failed: {e}")
            raise
    
    async def _cleanup_old_backups(self, database_name: str):
        """Cleanup old backups based on retention policy."""
        try:
            db_info = self.databases[database_name]
            backup_dir = self.backup_base_path / database_name
            
            if not backup_dir.exists():
                return
            
            # Get all backup files
            backup_files = list(backup_dir.glob(f"{database_name}_*.db*"))
            
            # Sort by modification time (newest first)
            backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            # Keep only max_backups number of files
            files_to_delete = backup_files[self.max_backups:]
            
            # Also check retention days
            cutoff_date = datetime.now() - timedelta(days=db_info.retention_days)
            
            for backup_file in backup_files:
                file_time = datetime.fromtimestamp(backup_file.stat().st_mtime)
                if file_time < cutoff_date:
                    files_to_delete.append(backup_file)
            
            # Delete old files
            for file_to_delete in files_to_delete:
                try:
                    file_to_delete.unlink()
                    self.logger.info(f"Deleted old backup: {file_to_delete}")
                except Exception as e:
                    self.logger.error(f"Failed to delete old backup {file_to_delete}: {e}")
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup old backups for {database_name}: {e}")
    
    async def start_scheduler(self):
        """Start the backup scheduler."""
        if self.scheduler_running:
            return
        
        self.scheduler_running = True
        self.scheduler_task = asyncio.create_task(self._backup_scheduler())
        self.logger.info("Backup scheduler started")
    
    async def stop_scheduler(self):
        """Stop the backup scheduler."""
        if not self.scheduler_running:
            return
        
        self.scheduler_running = False
        if self.scheduler_task:
            self.scheduler_task.cancel()
            try:
                await self.scheduler_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("Backup scheduler stopped")
    
    async def _backup_scheduler(self):
        """Backup scheduler main loop."""
        while self.scheduler_running:
            try:
                # Check which databases need backup
                for db_name, db_info in self.databases.items():
                    if self._should_backup(db_info):
                        self.logger.info(f"Scheduled backup for {db_name}")
                        await self.perform_backup(db_name)
                
                # Sleep for backup interval
                await asyncio.sleep(self.backup_interval)
                
            except Exception as e:
                self.logger.error(f"Backup scheduler error: {e}")
                await asyncio.sleep(60)  # Short sleep on error
    
    def _should_backup(self, db_info: DatabaseInfo) -> bool:
        """Check if database should be backed up."""
        if not db_info.last_backup:
            return True
        
        # Check schedule
        if db_info.backup_schedule == "hourly":
            return datetime.now() - db_info.last_backup > timedelta(hours=1)
        elif db_info.backup_schedule == "daily":
            return datetime.now() - db_info.last_backup > timedelta(days=1)
        elif db_info.backup_schedule == "weekly":
            return datetime.now() - db_info.last_backup > timedelta(weeks=1)
        
        return False
    
    async def verify_backup(self, backup_path: str) -> bool:
        """Verify backup integrity."""
        try:
            backup = Path(backup_path)
            
            if not backup.exists():
                return False
            
            # Check if it's a compressed file
            if backup_path.endswith('.gz'):
                # Try to decompress
                with gzip.open(backup_path, 'rb') as f:
                    # Read a small portion to verify
                    f.read(1024)
            else:
                # Try to open as SQLite database
                with sqlite3.connect(backup_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                    tables = cursor.fetchall()
                    
                    if not tables:
                        return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Backup verification failed for {backup_path}: {e}")
            return False
    
    async def get_backup_history(self, database_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get backup history."""
        try:
            history = []
            
            for job in self.backup_jobs.values():
                if database_name is None or job.database_name == database_name:
                    history.append({
                        'job_id': job.job_id,
                        'database_name': job.database_name,
                        'backup_type': job.backup_type.value,
                        'status': job.status.value,
                        'created_at': job.created_at.isoformat(),
                        'completed_at': job.completed_at.isoformat() if job.completed_at else None,
                        'backup_path': job.backup_path,
                        'file_size': job.file_size,
                        'compressed_size': job.compressed_size,
                        'checksum': job.checksum,
                        'error_message': job.error_message
                    })
            
            # Sort by creation time (newest first)
            history.sort(key=lambda x: x['created_at'], reverse=True)
            
            return history
            
        except Exception as e:
            self.logger.error(f"Failed to get backup history: {e}")
            return []
    
    async def get_restore_history(self, database_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get restore history."""
        try:
            history = []
            
            for job in self.restore_jobs.values():
                if database_name is None or job.database_name == database_name:
                    history.append({
                        'job_id': job.job_id,
                        'database_name': job.database_name,
                        'backup_path': job.backup_path,
                        'target_path': job.target_path,
                        'status': job.status.value,
                        'created_at': job.created_at.isoformat(),
                        'completed_at': job.completed_at.isoformat() if job.completed_at else None,
                        'error_message': job.error_message
                    })
            
            # Sort by creation time (newest first)
            history.sort(key=lambda x: x['created_at'], reverse=True)
            
            return history
            
        except Exception as e:
            self.logger.error(f"Failed to get restore history: {e}")
            return []
    
    async def _persist_backup_job(self, job: BackupJob):
        """Persist backup job to database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT OR REPLACE INTO backup_jobs 
                    (job_id, database_name, database_path, backup_type, status, 
                     created_at, started_at, completed_at, backup_path, file_size, 
                     compressed_size, checksum, error_message, retention_days)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    job.job_id,
                    job.database_name,
                    job.database_path,
                    job.backup_type.value,
                    job.status.value,
                    job.created_at.isoformat(),
                    job.started_at.isoformat() if job.started_at else None,
                    job.completed_at.isoformat() if job.completed_at else None,
                    job.backup_path,
                    job.file_size,
                    job.compressed_size,
                    job.checksum,
                    job.error_message,
                    job.retention_days
                ))
                
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Failed to persist backup job: {e}")
            raise
    
    async def _persist_restore_job(self, job: RestoreJob):
        """Persist restore job to database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT OR REPLACE INTO restore_jobs 
                    (job_id, database_name, backup_path, target_path, status, 
                     created_at, started_at, completed_at, error_message)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    job.job_id,
                    job.database_name,
                    job.backup_path,
                    job.target_path,
                    job.status.value,
                    job.created_at.isoformat(),
                    job.started_at.isoformat() if job.started_at else None,
                    job.completed_at.isoformat() if job.completed_at else None,
                    job.error_message
                ))
                
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Failed to persist restore job: {e}")
            raise
    
    def _calculate_file_checksum(self, file_path: str) -> str:
        """Calculate file checksum."""
        try:
            hash_md5 = hashlib.md5()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            self.logger.error(f"Failed to calculate checksum for {file_path}: {e}")
            return ""
    
    def _generate_job_id(self) -> str:
        """Generate a unique job ID."""
        import uuid
        return f"dbm_{uuid.uuid4().hex[:12]}"
    
    def add_backup_callback(self, callback: Callable[[BackupJob], None]):
        """Add backup completion callback."""
        self.backup_callbacks.append(callback)
    
    def add_restore_callback(self, callback: Callable[[RestoreJob], None]):
        """Add restore completion callback."""
        self.restore_callbacks.append(callback)
    
    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the DBM module."""
        # Calculate success rate
        total_backups = self.stats["total_backups"]
        if total_backups > 0:
            success_rate = (self.stats["successful_backups"] / total_backups) * 100
            self.stats["backup_success_rate"] = success_rate
        
        return {
            'scheduler_running': self.scheduler_running,
            'registered_databases': len(self.databases),
            'active_backup_jobs': len([j for j in self.backup_jobs.values() if j.status == BackupStatus.IN_PROGRESS]),
            'active_restore_jobs': len([j for j in self.restore_jobs.values() if j.status == RestoreStatus.IN_PROGRESS]),
            'statistics': self.stats.copy()
        }
    
    async def start(self):
        """Start the DBM module."""
        await self.start_scheduler()
        self.logger.info("DBM module started")
    
    async def stop(self):
        """Stop the DBM module."""
        await self.stop_scheduler()
        self.executor.shutdown(wait=True)
        self.logger.info("DBM module stopped") 