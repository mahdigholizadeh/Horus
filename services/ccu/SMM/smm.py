"""
Setting Modification Module (SMM)

This module handles centralized configuration management for the CCU and all 
microservices. It provides real-time configuration updates, validation, 
rollback capabilities, and secure configuration distribution.

Key Responsibilities:
- Centralized configuration management for all microservices
- Real-time configuration validation and deployment
- Configuration rollback and versioning
- Secure configuration distribution
- Configuration backup and recovery
- Dynamic configuration hot-reload
- Configuration change tracking and audit
"""

import asyncio
import logging
import json
import sqlite3
import hashlib
import shutil
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum
from dataclasses import dataclass, asdict
import threading
import os
import yaml


class ConfigurationStatus(Enum):
    """Configuration change status."""
    PENDING = "pending"
    VALIDATING = "validating"
    APPLYING = "applying"
    APPLIED = "applied"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class ConfigurationScope(Enum):
    """Configuration scope levels."""
    GLOBAL = "global"
    SERVICE = "service"
    MODULE = "module"
    INSTANCE = "instance"


@dataclass
class ConfigurationChange:
    """Configuration change record."""
    change_id: str
    scope: ConfigurationScope
    target: str
    changes: Dict[str, Any]
    previous_values: Dict[str, Any]
    status: ConfigurationStatus
    created_at: datetime
    applied_at: Optional[datetime] = None
    created_by: str = "system"
    validation_errors: List[str] = None
    
    def __post_init__(self):
        if self.validation_errors is None:
            self.validation_errors = []


@dataclass
class ConfigurationBackup:
    """Configuration backup record."""
    backup_id: str
    scope: ConfigurationScope
    target: str
    configuration: Dict[str, Any]
    created_at: datetime
    checksum: str
    size: int


class SettingModificationModule:
    """
    Setting Modification Module (SMM)
    
    Manages centralized configuration for all microservices with 
    validation, rollback, and hot-reload capabilities.
    """
    
    def __init__(self):
        """Initialize the SMM module."""
        self.logger = logging.getLogger(__name__)
        
        # Database setup
        self.db_path = Path("smm_configurations.db")
        self.init_database()
        
        # Configuration paths
        self.config_base_path = Path("ccu_setting")
        self.backup_path = Path("config_backups")
        self.backup_path.mkdir(exist_ok=True)
        
        # Configuration tracking
        self.active_configurations: Dict[str, Dict[str, Any]] = {}
        self.configuration_changes: Dict[str, ConfigurationChange] = {}
        self.configuration_backups: Dict[str, ConfigurationBackup] = {}
        
        # Validation rules
        self.validation_rules = {
            "ccu_setting": self._validate_ccu_config,
            "rla_setting": self._validate_rla_config,
            "tpp_setting": self._validate_tpp_config,
            "rcm_setting": self._validate_rcm_config,
            "jfa_setting": self._validate_jfa_config,
            "td_setting": self._validate_td_config,
            "ocm_setting": self._validate_ocm_config
        }
        
        # Service configurations
        self.service_configs = {
            "CCU": "ccu_setting.json",
            "RLA": "rla_setting.json", 
            "TPP": "tpp_setting.json",
            "RCM": "rcm_setting.json",
            "JFA": "jfa_setting.json",
            "TD": "td_setting.json",
            "OCM": "ocm_setting.json"
        }
        
        # Configuration state
        self.is_monitoring = False
        self.monitoring_task = None
        
        # Callbacks
        self.configuration_callbacks = []
        self.validation_callbacks = []
        
        # Statistics
        self.stats = {
            "total_changes": 0,
            "successful_changes": 0,
            "failed_changes": 0,
            "rollbacks": 0,
            "validations": 0,
            "backups_created": 0,
            "last_change": None
        }
        
        # Load current configurations
        self.load_all_configurations()
        
        self.logger.info("SMM module initialized successfully")
    
    def init_database(self):
        """Initialize the SQLite database for configuration tracking."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Configuration changes table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS configuration_changes (
                        change_id TEXT PRIMARY KEY,
                        scope TEXT NOT NULL,
                        target TEXT NOT NULL,
                        changes TEXT NOT NULL,
                        previous_values TEXT NOT NULL,
                        status TEXT NOT NULL,
                        created_at TIMESTAMP NOT NULL,
                        applied_at TIMESTAMP,
                        created_by TEXT NOT NULL,
                        validation_errors TEXT
                    )
                """)
                
                # Configuration backups table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS configuration_backups (
                        backup_id TEXT PRIMARY KEY,
                        scope TEXT NOT NULL,
                        target TEXT NOT NULL,
                        configuration TEXT NOT NULL,
                        created_at TIMESTAMP NOT NULL,
                        checksum TEXT NOT NULL,
                        size INTEGER NOT NULL
                    )
                """)
                
                # Configuration audit table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS configuration_audit (
                        audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        change_id TEXT NOT NULL,
                        action TEXT NOT NULL,
                        timestamp TIMESTAMP NOT NULL,
                        details TEXT,
                        FOREIGN KEY (change_id) REFERENCES configuration_changes (change_id)
                    )
                """)
                
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Failed to initialize database: {e}")
            raise
    
    def load_all_configurations(self):
        """Load all service configurations from files."""
        try:
            for service_name, config_file in self.service_configs.items():
                config_path = self.config_base_path / config_file
                
                if config_path.exists():
                    with open(config_path, 'r') as f:
                        config_data = json.load(f)
                        self.active_configurations[service_name] = config_data
                        self.logger.info(f"Loaded configuration for {service_name}")
                else:
                    self.logger.warning(f"Configuration file not found: {config_file}")
                    self.active_configurations[service_name] = {}
            
            self.logger.info("All configurations loaded successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to load configurations: {e}")
            raise
    
    async def apply_configuration(self, configuration: Dict[str, Any]) -> bool:
        """Apply new configuration to services."""
        try:
            self.logger.info("Applying new configuration...")
            
            # Validate configuration
            validation_result = await self._validate_configuration(configuration)
            if not validation_result['valid']:
                self.logger.error(f"Configuration validation failed: {validation_result['errors']}")
                return False
            
            # Apply configuration changes
            for service_name, service_config in configuration.items():
                if service_name in self.active_configurations:
                    # Create backup before applying
                    await self._create_backup(service_name)
                    
                    # Apply configuration
                    self.active_configurations[service_name].update(service_config)
                    
                    # Save to file
                    await self._save_configuration(service_name, self.active_configurations[service_name])
                    
                    self.logger.info(f"Applied configuration for {service_name}")
            
            self.stats['successful_changes'] += 1
            self.stats['last_change'] = datetime.now()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to apply configuration: {e}")
            self.stats['failed_changes'] += 1
            return False
    
    async def update_service_configuration(self, service_name: str, updates: Dict[str, Any]) -> str:
        """Update configuration for a specific service."""
        try:
            change_id = self._generate_change_id()
            
            # Get current configuration
            current_config = self.active_configurations.get(service_name, {})
            
            # Create change record
            change = ConfigurationChange(
                change_id=change_id,
                scope=ConfigurationScope.SERVICE,
                target=service_name,
                changes=updates,
                previous_values=self._extract_previous_values(current_config, updates),
                status=ConfigurationStatus.PENDING,
                created_at=datetime.now()
            )
            
            self.configuration_changes[change_id] = change
            
            # Validate changes
            change.status = ConfigurationStatus.VALIDATING
            validation_result = await self._validate_service_configuration(service_name, updates)
            
            if not validation_result['valid']:
                change.status = ConfigurationStatus.FAILED
                change.validation_errors = validation_result['errors']
                self.logger.error(f"Configuration validation failed for {service_name}: {validation_result['errors']}")
                return change_id
            
            # Create backup
            await self._create_backup(service_name)
            
            # Apply changes
            change.status = ConfigurationStatus.APPLYING
            self._apply_updates(current_config, updates)
            
            # Save configuration
            await self._save_configuration(service_name, current_config)
            
            # Update status
            change.status = ConfigurationStatus.APPLIED
            change.applied_at = datetime.now()
            
            # Persist change record
            await self._persist_change(change)
            
            # Notify callbacks
            for callback in self.configuration_callbacks:
                try:
                    await callback(service_name, current_config)
                except Exception as e:
                    self.logger.error(f"Configuration callback failed: {e}")
            
            self.stats['successful_changes'] += 1
            self.stats['last_change'] = datetime.now()
            
            self.logger.info(f"Successfully updated configuration for {service_name}")
            return change_id
            
        except Exception as e:
            self.logger.error(f"Failed to update configuration for {service_name}: {e}")
            if change_id in self.configuration_changes:
                self.configuration_changes[change_id].status = ConfigurationStatus.FAILED
            self.stats['failed_changes'] += 1
            return change_id
    
    async def rollback_configuration(self, change_id: str) -> bool:
        """Rollback a configuration change."""
        try:
            if change_id not in self.configuration_changes:
                self.logger.error(f"Configuration change not found: {change_id}")
                return False
            
            change = self.configuration_changes[change_id]
            
            if change.status != ConfigurationStatus.APPLIED:
                self.logger.error(f"Cannot rollback change {change_id} with status {change.status}")
                return False
            
            # Apply previous values
            current_config = self.active_configurations.get(change.target, {})
            self._apply_updates(current_config, change.previous_values)
            
            # Save configuration
            await self._save_configuration(change.target, current_config)
            
            # Update change status
            change.status = ConfigurationStatus.ROLLED_BACK
            await self._persist_change(change)
            
            self.stats['rollbacks'] += 1
            
            self.logger.info(f"Successfully rolled back configuration change {change_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to rollback configuration change {change_id}: {e}")
            return False
    
    async def get_configuration(self, service_name: str) -> Dict[str, Any]:
        """Get current configuration for a service."""
        return self.active_configurations.get(service_name, {})
    
    async def get_all_configurations(self) -> Dict[str, Dict[str, Any]]:
        """Get all current configurations."""
        return self.active_configurations.copy()
    
    async def validate_configuration(self, service_name: str, configuration: Dict[str, Any]) -> Dict[str, Any]:
        """Validate configuration for a service."""
        return await self._validate_service_configuration(service_name, configuration)
    
    async def backup_configuration(self, service_name: str) -> str:
        """Create a backup of current configuration."""
        return await self._create_backup(service_name)
    
    async def restore_configuration(self, backup_id: str) -> bool:
        """Restore configuration from a backup."""
        try:
            if backup_id not in self.configuration_backups:
                self.logger.error(f"Backup not found: {backup_id}")
                return False
            
            backup = self.configuration_backups[backup_id]
            
            # Apply backup configuration
            self.active_configurations[backup.target] = backup.configuration.copy()
            
            # Save to file
            await self._save_configuration(backup.target, backup.configuration)
            
            self.logger.info(f"Successfully restored configuration from backup {backup_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to restore configuration from backup {backup_id}: {e}")
            return False
    
    async def get_configuration_history(self, service_name: str) -> List[Dict[str, Any]]:
        """Get configuration change history for a service."""
        try:
            history = []
            
            for change in self.configuration_changes.values():
                if change.target == service_name:
                    history.append({
                        'change_id': change.change_id,
                        'status': change.status.value,
                        'changes': change.changes,
                        'created_at': change.created_at.isoformat(),
                        'applied_at': change.applied_at.isoformat() if change.applied_at else None,
                        'created_by': change.created_by,
                        'validation_errors': change.validation_errors
                    })
            
            # Sort by creation time
            history.sort(key=lambda x: x['created_at'], reverse=True)
            
            return history
            
        except Exception as e:
            self.logger.error(f"Failed to get configuration history for {service_name}: {e}")
            return []
    
    async def start_monitoring(self):
        """Start configuration monitoring."""
        if self.is_monitoring:
            return
        
        self.is_monitoring = True
        self.monitoring_task = asyncio.create_task(self._monitor_configurations())
        self.logger.info("Configuration monitoring started")
    
    async def stop_monitoring(self):
        """Stop configuration monitoring."""
        if not self.is_monitoring:
            return
        
        self.is_monitoring = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("Configuration monitoring stopped")
    
    async def _monitor_configurations(self):
        """Monitor configuration files for changes."""
        while self.is_monitoring:
            try:
                # Check for file changes
                for service_name, config_file in self.service_configs.items():
                    config_path = self.config_base_path / config_file
                    
                    if config_path.exists():
                        # Check if file was modified
                        file_mtime = config_path.stat().st_mtime
                        current_config = self.active_configurations.get(service_name, {})
                        
                        # If file is newer, reload configuration
                        if hasattr(current_config, '_file_mtime'):
                            if file_mtime > current_config._file_mtime:
                                await self._reload_configuration(service_name)
                        else:
                            # Set initial mtime
                            current_config['_file_mtime'] = file_mtime
                
                # Sleep for monitoring interval
                await asyncio.sleep(30)
                
            except Exception as e:
                self.logger.error(f"Error monitoring configurations: {e}")
                await asyncio.sleep(30)
    
    async def _reload_configuration(self, service_name: str):
        """Reload configuration from file."""
        try:
            config_file = self.service_configs[service_name]
            config_path = self.config_base_path / config_file
            
            with open(config_path, 'r') as f:
                new_config = json.load(f)
            
            # Update active configuration
            self.active_configurations[service_name] = new_config
            
            # Set file mtime
            new_config['_file_mtime'] = config_path.stat().st_mtime
            
            self.logger.info(f"Reloaded configuration for {service_name}")
            
        except Exception as e:
            self.logger.error(f"Failed to reload configuration for {service_name}: {e}")
    
    async def _validate_configuration(self, configuration: Dict[str, Any]) -> Dict[str, Any]:
        """Validate complete configuration."""
        errors = []
        
        for service_name, service_config in configuration.items():
            if service_name in self.validation_rules:
                try:
                    validation_result = self.validation_rules[service_name](service_config)
                    if not validation_result['valid']:
                        errors.extend([f"{service_name}: {error}" for error in validation_result['errors']])
                except Exception as e:
                    errors.append(f"{service_name}: Validation error - {str(e)}")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }
    
    async def _validate_service_configuration(self, service_name: str, configuration: Dict[str, Any]) -> Dict[str, Any]:
        """Validate configuration for a specific service."""
        try:
            # Get service-specific validation rule
            config_key = f"{service_name.lower()}_setting"
            if config_key in self.validation_rules:
                return self.validation_rules[config_key](configuration)
            else:
                # Generic validation
                return self._validate_generic_config(configuration)
                
        except Exception as e:
            return {
                'valid': False,
                'errors': [f"Validation error: {str(e)}"]
            }
    
    def _validate_ccu_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate CCU configuration."""
        errors = []
        
        # Check required fields
        required_fields = ['service_name', 'version', 'host', 'port']
        for field in required_fields:
            if field not in config:
                errors.append(f"Missing required field: {field}")
        
        # Validate port ranges
        if 'port' in config:
            port = config['port']
            if not isinstance(port, int) or port < 1 or port > 65535:
                errors.append(f"Invalid port: {port}")
        
        # Validate modules configuration
        if 'modules' in config:
            modules = config['modules']
            if not isinstance(modules, dict):
                errors.append("Modules configuration must be a dictionary")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }
    
    def _validate_rla_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate RLA configuration."""
        errors = []
        
        # Check required fields
        required_fields = ['service_name', 'validation', 'processing']
        for field in required_fields:
            if field not in config:
                errors.append(f"Missing required field: {field}")
        
        # Validate validation settings
        if 'validation' in config:
            validation = config['validation']
            if 'enabled' not in validation:
                errors.append("Validation must have 'enabled' field")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }
    
    def _validate_tpp_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate TPP configuration."""
        errors = []
        
        # Check required fields
        required_fields = ['service_name', 'text_processing', 'spam_filtering']
        for field in required_fields:
            if field not in config:
                errors.append(f"Missing required field: {field}")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }
    
    def _validate_rcm_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate RCM configuration."""
        errors = []
        
        # Check required fields
        required_fields = ['service_name', 'cache_management', 'processing']
        for field in required_fields:
            if field not in config:
                errors.append(f"Missing required field: {field}")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }
    
    def _validate_jfa_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate JFA configuration."""
        errors = []
        
        # Check required fields
        required_fields = ['service_name', 'json_processing', 'api_integration']
        for field in required_fields:
            if field not in config:
                errors.append(f"Missing required field: {field}")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }
    
    def _validate_td_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate TD configuration."""
        errors = []
        
        # Check required fields
        required_fields = ['service_name', 'calculation_processing', 'routing']
        for field in required_fields:
            if field not in config:
                errors.append(f"Missing required field: {field}")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }
    
    def _validate_ocm_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate OCM configuration."""
        errors = []
        
        # Check required fields
        required_fields = ['service_name', 'processing', 'cache_management']
        for field in required_fields:
            if field not in config:
                errors.append(f"Missing required field: {field}")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }
    
    def _validate_generic_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Generic configuration validation."""
        errors = []
        
        # Check if it's a valid JSON structure
        if not isinstance(config, dict):
            errors.append("Configuration must be a dictionary")
        
        # Check for common required fields
        if 'service_name' not in config:
            errors.append("Missing required field: service_name")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }
    
    async def _create_backup(self, service_name: str) -> str:
        """Create a backup of the current configuration."""
        try:
            backup_id = self._generate_backup_id()
            current_config = self.active_configurations.get(service_name, {})
            
            # Create backup record
            backup = ConfigurationBackup(
                backup_id=backup_id,
                scope=ConfigurationScope.SERVICE,
                target=service_name,
                configuration=current_config.copy(),
                created_at=datetime.now(),
                checksum=self._calculate_checksum(current_config),
                size=len(json.dumps(current_config))
            )
            
            self.configuration_backups[backup_id] = backup
            
            # Save backup to file
            backup_file = self.backup_path / f"{service_name}_{backup_id}.json"
            with open(backup_file, 'w') as f:
                json.dump(current_config, f, indent=2)
            
            # Persist to database
            await self._persist_backup(backup)
            
            self.stats['backups_created'] += 1
            
            self.logger.info(f"Created backup {backup_id} for {service_name}")
            return backup_id
            
        except Exception as e:
            self.logger.error(f"Failed to create backup for {service_name}: {e}")
            return ""
    
    async def _save_configuration(self, service_name: str, configuration: Dict[str, Any]):
        """Save configuration to file."""
        try:
            config_file = self.service_configs[service_name]
            config_path = self.config_base_path / config_file
            
            # Create backup of current file
            if config_path.exists():
                backup_path = config_path.with_suffix('.bak')
                shutil.copy2(config_path, backup_path)
            
            # Save new configuration
            with open(config_path, 'w') as f:
                json.dump(configuration, f, indent=2)
            
            self.logger.info(f"Saved configuration for {service_name}")
            
        except Exception as e:
            self.logger.error(f"Failed to save configuration for {service_name}: {e}")
            raise
    
    async def _persist_change(self, change: ConfigurationChange):
        """Persist configuration change to database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT OR REPLACE INTO configuration_changes 
                    (change_id, scope, target, changes, previous_values, status, 
                     created_at, applied_at, created_by, validation_errors)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    change.change_id,
                    change.scope.value,
                    change.target,
                    json.dumps(change.changes),
                    json.dumps(change.previous_values),
                    change.status.value,
                    change.created_at.isoformat(),
                    change.applied_at.isoformat() if change.applied_at else None,
                    change.created_by,
                    json.dumps(change.validation_errors)
                ))
                
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Failed to persist configuration change: {e}")
            raise
    
    async def _persist_backup(self, backup: ConfigurationBackup):
        """Persist configuration backup to database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO configuration_backups 
                    (backup_id, scope, target, configuration, created_at, checksum, size)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    backup.backup_id,
                    backup.scope.value,
                    backup.target,
                    json.dumps(backup.configuration),
                    backup.created_at.isoformat(),
                    backup.checksum,
                    backup.size
                ))
                
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Failed to persist configuration backup: {e}")
            raise
    
    def _apply_updates(self, config: Dict[str, Any], updates: Dict[str, Any]):
        """Apply updates to configuration."""
        for key, value in updates.items():
            if isinstance(value, dict) and key in config and isinstance(config[key], dict):
                # Recursively update nested dictionaries
                self._apply_updates(config[key], value)
            else:
                # Direct assignment
                config[key] = value
    
    def _extract_previous_values(self, config: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
        """Extract previous values for rollback."""
        previous_values = {}
        
        for key, value in updates.items():
            if key in config:
                if isinstance(value, dict) and isinstance(config[key], dict):
                    # Recursively extract nested values
                    previous_values[key] = self._extract_previous_values(config[key], value)
                else:
                    previous_values[key] = config[key]
            else:
                previous_values[key] = None
        
        return previous_values
    
    def _generate_change_id(self) -> str:
        """Generate a unique change ID."""
        import uuid
        return f"cfg_{uuid.uuid4().hex[:12]}"
    
    def _generate_backup_id(self) -> str:
        """Generate a unique backup ID."""
        import uuid
        return f"bkp_{uuid.uuid4().hex[:12]}"
    
    def _calculate_checksum(self, data: Dict[str, Any]) -> str:
        """Calculate checksum for data."""
        data_str = json.dumps(data, sort_keys=True)
        return hashlib.md5(data_str.encode()).hexdigest()
    
    def add_configuration_callback(self, callback: Callable[[str, Dict[str, Any]], None]):
        """Add configuration change callback."""
        self.configuration_callbacks.append(callback)
    
    def remove_configuration_callback(self, callback: Callable[[str, Dict[str, Any]], None]):
        """Remove configuration change callback."""
        if callback in self.configuration_callbacks:
            self.configuration_callbacks.remove(callback)
    
    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the SMM module."""
        return {
            'is_monitoring': self.is_monitoring,
            'active_configurations': len(self.active_configurations),
            'pending_changes': len([c for c in self.configuration_changes.values() if c.status == ConfigurationStatus.PENDING]),
            'total_backups': len(self.configuration_backups),
            'statistics': self.stats.copy()
        }
    
    async def start(self):
        """Start the SMM module."""
        await self.start_monitoring()
        self.logger.info("SMM module started")
    
    async def stop(self):
        """Stop the SMM module."""
        await self.stop_monitoring()
        self.logger.info("SMM module stopped") 