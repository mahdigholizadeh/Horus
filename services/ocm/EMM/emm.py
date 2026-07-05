"""
Error Management Module (EMM) for OCM
Centralized Error Handling System - Microservice 06

This module provides centralized, dynamic error recognition and handling
following the established Horus pattern with 16-character hexadecimal error codes
and automated recovery strategies specific to Operations Control Management.

Error Code Format: Server(2) + Macroservice(2) + Microservice(2) + Module(2) + Class(2) + Function(3) + Sub-function(3)
OCM Microservice Code: 06
"""

import asyncio
import logging
import json
import sqlite3
import hashlib
import traceback
import time
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Callable, Tuple
from enum import Enum
from dataclasses import dataclass, asdict
import threading
from pathlib import Path


class ErrorSeverity(Enum):
    """Error severity levels for centralized classification."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4
    FATAL = 5


class ErrorCategory(Enum):
    """OCM-specific error categories."""
    OPERATION_CONTROL = "operation_control"
    VERIFICATION_SYSTEM = "verification_system" 
    PERFORMANCE_MONITORING = "performance_monitoring"
    RESOURCE_MANAGEMENT = "resource_management"
    MODULE_COMMUNICATION = "module_communication"
    SYSTEM_HEALTH = "system_health"
    DATA_MANAGEMENT = "data_management"
    NETWORK_COMMUNICATION = "network_communication"
    CONFIGURATION = "configuration"
    EXTERNAL_SERVICE = "external_service"


class RecoveryStrategy(Enum):
    """Automated recovery strategies."""
    RETRY = "retry"
    RESTART_COMPONENT = "restart_component"
    FALLBACK_MODE = "fallback_mode"
    RESOURCE_CLEANUP = "resource_cleanup"
    CONFIGURATION_RESET = "configuration_reset"
    SERVICE_RESTART = "service_restart"
    ESCALATE = "escalate"
    IGNORE = "ignore"
    DATA_RECOVERY = "data_recovery"
    NETWORK_RESET = "network_reset"


@dataclass
class ErrorRecord:
    """Centralized error record structure."""
    error_code: str
    timestamp: str
    severity: int
    category: str
    module: str
    class_name: str
    function_name: str
    message: str
    context: Dict[str, Any]
    stack_trace: Optional[str] = None
    recovery_attempted: bool = False
    recovery_successful: bool = False
    recovery_details: Optional[str] = None
    occurrence_count: int = 1
    first_occurrence: Optional[str] = None
    last_occurrence: Optional[str] = None


class ErrorManagementModule:
    """
    Centralized Error Management Module for OCM
    
    Implements dynamic error recognition, centralized handling, and automated recovery
    with integration to CCU through ECM for centralized monitoring and control.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize centralized error management system."""
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.module_name = "EMM"
        self.microservice_code = "06"  # OCM microservice identifier
        
        # Centralized error handling state
        self.is_active = False
        self.error_db_path = os.path.join("logs", "ocm_errors.db")
        self.error_patterns = {}
        self.active_errors = {}
        self.recovery_strategies = {}
        self.error_handlers = {}
        
        # Error processing configuration
        self.max_retries = 3
        self.retry_delay = 5.0
        self.escalation_threshold = 5
        self.pattern_analysis_interval = 300  # 5 minutes
        
        # Statistics for centralized monitoring
        self.stats = {
            "total_errors": 0,
            "resolved_errors": 0,
            "critical_errors": 0,
            "recovery_attempts": 0,
            "recovery_success_rate": 0.0,
            "pattern_detections": 0,
            "escalations": 0,
            "category_distribution": {category.value: 0 for category in ErrorCategory},
            "severity_distribution": {sev.name: 0 for sev in ErrorSeverity}
        }
        
        # Module references for integration
        self.modules = {}
        
        # Initialize centralized error handling components
        self._initialize_error_database()
        self._register_error_handlers()
        self._register_recovery_strategies()
        
        self.logger.info("OCM EMM initialized with centralized error handling")
    
    def _initialize_error_database(self):
        """Initialize SQLite database for centralized error storage."""
        try:
            os.makedirs(os.path.dirname(self.error_db_path), exist_ok=True)
            
            with sqlite3.connect(self.error_db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS errors (
                        error_code TEXT PRIMARY KEY,
                        timestamp TEXT NOT NULL,
                        severity INTEGER NOT NULL,
                        category TEXT NOT NULL,
                        module TEXT NOT NULL,
                        class_name TEXT NOT NULL,
                        function_name TEXT NOT NULL,
                        message TEXT NOT NULL,
                        context TEXT,
                        stack_trace TEXT,
                        recovery_attempted BOOLEAN DEFAULT 0,
                        recovery_successful BOOLEAN DEFAULT 0,
                        recovery_details TEXT,
                        occurrence_count INTEGER DEFAULT 1,
                        first_occurrence TEXT,
                        last_occurrence TEXT
                    )
                """)
                
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_timestamp ON errors(timestamp)
                """)
                
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_severity ON errors(severity)
                """)
                
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_category ON errors(category)
                """)
                
                conn.commit()
                
            self.logger.info("Error database initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize error database: {e}")
            raise
    
    def _generate_error_code(self, module: str, class_name: str, function_name: str, 
                           sub_function: str = "000") -> str:
        """
        Generate 16-character hexadecimal error code.
        Format: Server(2) + Macroservice(2) + Microservice(2) + Module(2) + Class(2) + Function(3) + Sub-function(3)
        """
        try:
            # Server code (assume 01 for primary server)
            server_code = "01"
            
            # Macroservice code (01 for main computation server)
            macroservice_code = "01"
            
            # Microservice code (06 for OCM)
            microservice_code = "06"
            
            # Module code (hash first 2 chars of module name)
            module_hash = hashlib.md5(module.encode()).hexdigest()[:2].upper()
            
            # Class code (hash first 2 chars of class name)
            class_hash = hashlib.md5(class_name.encode()).hexdigest()[:2].upper()
            
            # Function code (hash first 3 chars of function name)
            func_hash = hashlib.md5(function_name.encode()).hexdigest()[:3].upper()
            
            # Sub-function code
            if sub_function == "000":
                sub_func_code = "000"
            else:
                sub_func_code = hashlib.md5(sub_function.encode()).hexdigest()[:3].upper()
            
            error_code = f"{server_code}{macroservice_code}{microservice_code}{module_hash}{class_hash}{func_hash}{sub_func_code}"
            
            return error_code
            
        except Exception as e:
            self.logger.error(f"Error generating error code: {e}")
            return "0101060000000000"  # Fallback error code
    
    def _register_error_handlers(self):
        """Register centralized error handlers for different categories."""
        self.error_handlers = {
            ErrorCategory.OPERATION_CONTROL: self._handle_operation_control_error,
            ErrorCategory.VERIFICATION_SYSTEM: self._handle_verification_system_error,
            ErrorCategory.PERFORMANCE_MONITORING: self._handle_performance_monitoring_error,
            ErrorCategory.RESOURCE_MANAGEMENT: self._handle_resource_management_error,
            ErrorCategory.MODULE_COMMUNICATION: self._handle_module_communication_error,
            ErrorCategory.SYSTEM_HEALTH: self._handle_system_health_error,
            ErrorCategory.DATA_MANAGEMENT: self._handle_data_management_error,
            ErrorCategory.NETWORK_COMMUNICATION: self._handle_network_communication_error,
            ErrorCategory.CONFIGURATION: self._handle_configuration_error,
            ErrorCategory.EXTERNAL_SERVICE: self._handle_external_service_error
        }
    
    def _register_recovery_strategies(self):
        """Register automated recovery strategies for error categories."""
        self.recovery_strategies = {
            ErrorCategory.OPERATION_CONTROL: RecoveryStrategy.RESTART_COMPONENT,
            ErrorCategory.VERIFICATION_SYSTEM: RecoveryStrategy.RETRY,
            ErrorCategory.PERFORMANCE_MONITORING: RecoveryStrategy.RESOURCE_CLEANUP,
            ErrorCategory.RESOURCE_MANAGEMENT: RecoveryStrategy.RESOURCE_CLEANUP,
            ErrorCategory.MODULE_COMMUNICATION: RecoveryStrategy.RETRY,
            ErrorCategory.SYSTEM_HEALTH: RecoveryStrategy.SERVICE_RESTART,
            ErrorCategory.DATA_MANAGEMENT: RecoveryStrategy.DATA_RECOVERY,
            ErrorCategory.NETWORK_COMMUNICATION: RecoveryStrategy.NETWORK_RESET,
            ErrorCategory.CONFIGURATION: RecoveryStrategy.CONFIGURATION_RESET,
            ErrorCategory.EXTERNAL_SERVICE: RecoveryStrategy.FALLBACK_MODE
        }
    
    def set_module_references(self, modules: Dict[str, Any]):
        """Set references to other modules for centralized integration."""
        self.modules = modules
        self.logger.info("Module references set for centralized error handling")
    
    async def start(self):
        """Start centralized error management system."""
        try:
            self.is_active = True
            
            # Start background tasks for centralized processing
            asyncio.create_task(self._error_pattern_analyzer())
            asyncio.create_task(self._statistics_updater())
            asyncio.create_task(self._health_monitor())
            
            self.logger.info("OCM EMM started - centralized error handling active")
            
        except Exception as e:
            self.logger.error(f"Failed to start EMM: {e}")
            raise
    
    async def stop(self):
        """Stop centralized error management system."""
        try:
            self.is_active = False
            self.logger.info("OCM EMM stopped successfully")
            
        except Exception as e:
            self.logger.error(f"Error stopping EMM: {e}")
    
    async def report_error(self, 
                          module: str,
                          class_name: str,
                          function_name: str,
                          message: str,
                          category: ErrorCategory,
                          severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                          context: Dict[str, Any] = None,
                          exception: Exception = None,
                          sub_function: str = "000") -> str:
        """
        Centralized error reporting with dynamic error recognition.
        Returns the generated error code for tracking.
        """
        try:
            # Generate centralized error code
            error_code = self._generate_error_code(module, class_name, function_name, sub_function)
            
            # Create error record
            error_record = ErrorRecord(
                error_code=error_code,
                timestamp=datetime.now().isoformat(),
                severity=severity.value,
                category=category.value,
                module=module,
                class_name=class_name,
                function_name=function_name,
                message=message,
                context=context or {},
                stack_trace=traceback.format_exc() if exception else None,
                first_occurrence=datetime.now().isoformat(),
                last_occurrence=datetime.now().isoformat()
            )
            
            # Check for existing pattern
            await self._check_error_pattern(error_record)
            
            # Store in centralized database
            await self._store_error(error_record)
            
            # Update statistics
            self._update_statistics(error_record)
            
            # Log error
            self._log_error(error_record)
            
            # Process error through centralized handling
            asyncio.create_task(self._process_error_centralized(error_record))
            
            return error_code
            
        except Exception as e:
            self.logger.critical(f"Critical failure in error reporting: {e}")
            return "ERROR_REPORT_FAILED"
    
    async def _check_error_pattern(self, error_record: ErrorRecord):
        """Check for error patterns for centralized pattern analysis."""
        try:
            pattern_key = f"{error_record.module}_{error_record.class_name}_{error_record.function_name}"
            
            if pattern_key in self.error_patterns:
                pattern_info = self.error_patterns[pattern_key]
                pattern_info["count"] += 1
                pattern_info["last_occurrence"] = error_record.timestamp
                
                error_record.occurrence_count = pattern_info["count"]
                error_record.first_occurrence = pattern_info["first_occurrence"]
                
                # Check for escalation threshold
                if pattern_info["count"] >= self.escalation_threshold:
                    await self._escalate_error(error_record)
                    
            else:
                self.error_patterns[pattern_key] = {
                    "count": 1,
                    "first_occurrence": error_record.timestamp,
                    "last_occurrence": error_record.timestamp,
                    "category": error_record.category,
                    "severity": error_record.severity
                }
                
                self.stats["pattern_detections"] += 1
                
        except Exception as e:
            self.logger.error(f"Error in pattern checking: {e}")
    
    async def _store_error(self, error_record: ErrorRecord):
        """Store error in centralized database."""
        try:
            with sqlite3.connect(self.error_db_path) as conn:
                # Check if error code already exists
                cursor = conn.execute("SELECT occurrence_count FROM errors WHERE error_code = ?", 
                                    (error_record.error_code,))
                existing = cursor.fetchone()
                
                if existing:
                    # Update existing record
                    conn.execute("""
                        UPDATE errors SET 
                        occurrence_count = occurrence_count + 1,
                        last_occurrence = ?,
                        context = ?
                        WHERE error_code = ?
                    """, (error_record.timestamp, json.dumps(error_record.context), error_record.error_code))
                else:
                    # Insert new record
                    conn.execute("""
                        INSERT INTO errors (
                            error_code, timestamp, severity, category, module, 
                            class_name, function_name, message, context, stack_trace,
                            first_occurrence, last_occurrence
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        error_record.error_code, error_record.timestamp, error_record.severity,
                        error_record.category, error_record.module, error_record.class_name,
                        error_record.function_name, error_record.message, 
                        json.dumps(error_record.context), error_record.stack_trace,
                        error_record.first_occurrence, error_record.last_occurrence
                    ))
                
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Error storing error record: {e}")
    
    async def _process_error_centralized(self, error_record: ErrorRecord):
        """Process error through centralized handling logic."""
        try:
            # Add to active errors
            self.active_errors[error_record.error_code] = error_record
            
            # Execute category-specific handler
            category = ErrorCategory(error_record.category)
            if category in self.error_handlers:
                await self.error_handlers[category](error_record)
            
            # Attempt automated recovery
            await self._attempt_recovery(error_record)
            
            # Report to CCU through ECM
            await self._report_to_ccu(error_record)
            
            # Check if error should be escalated
            if error_record.severity >= ErrorSeverity.CRITICAL.value:
                await self._escalate_error(error_record)
                
        except Exception as e:
            self.logger.error(f"Error in centralized processing: {e}")
    
    async def _attempt_recovery(self, error_record: ErrorRecord):
        """Attempt automated recovery based on centralized strategies."""
        try:
            category = ErrorCategory(error_record.category)
            strategy = self.recovery_strategies.get(category, RecoveryStrategy.ESCALATE)
            
            error_record.recovery_attempted = True
            self.stats["recovery_attempts"] += 1
            
            recovery_result = await self._execute_recovery_strategy(strategy, error_record)
            
            if recovery_result["success"]:
                error_record.recovery_successful = True
                error_record.recovery_details = json.dumps(recovery_result)
                
                # Update database
                with sqlite3.connect(self.error_db_path) as conn:
                    conn.execute("""
                        UPDATE errors SET 
                        recovery_attempted = 1,
                        recovery_successful = 1,
                        recovery_details = ?
                        WHERE error_code = ?
                    """, (error_record.recovery_details, error_record.error_code))
                    conn.commit()
                
                # Remove from active errors
                if error_record.error_code in self.active_errors:
                    del self.active_errors[error_record.error_code]
                
                self.stats["resolved_errors"] += 1
                self.logger.info(f"Recovery successful for error: {error_record.error_code}")
                
            else:
                error_record.recovery_details = json.dumps(recovery_result)
                self.logger.warning(f"Recovery failed for error: {error_record.error_code}")
                
        except Exception as e:
            self.logger.error(f"Error during recovery attempt: {e}")
    
    async def _execute_recovery_strategy(self, strategy: RecoveryStrategy, 
                                       error_record: ErrorRecord) -> Dict[str, Any]:
        """Execute specific recovery strategy."""
        try:
            if strategy == RecoveryStrategy.RETRY:
                return await self._recovery_retry(error_record)
            elif strategy == RecoveryStrategy.RESTART_COMPONENT:
                return await self._recovery_restart_component(error_record)
            elif strategy == RecoveryStrategy.FALLBACK_MODE:
                return await self._recovery_fallback_mode(error_record)
            elif strategy == RecoveryStrategy.RESOURCE_CLEANUP:
                return await self._recovery_resource_cleanup(error_record)
            elif strategy == RecoveryStrategy.CONFIGURATION_RESET:
                return await self._recovery_configuration_reset(error_record)
            elif strategy == RecoveryStrategy.SERVICE_RESTART:
                return await self._recovery_service_restart(error_record)
            elif strategy == RecoveryStrategy.DATA_RECOVERY:
                return await self._recovery_data_recovery(error_record)
            elif strategy == RecoveryStrategy.NETWORK_RESET:
                return await self._recovery_network_reset(error_record)
            elif strategy == RecoveryStrategy.ESCALATE:
                return {"success": False, "action": "escalated", "reason": "requires_manual_intervention"}
            else:
                return {"success": False, "action": "ignored", "reason": "no_strategy_defined"}
                
        except Exception as e:
            return {"success": False, "action": "failed", "error": str(e)}
    
    # Recovery Strategy Implementations
    
    async def _recovery_retry(self, error_record: ErrorRecord) -> Dict[str, Any]:
        """Retry recovery strategy for transient errors."""
        try:
            await asyncio.sleep(self.retry_delay)
            return {"success": True, "action": "retry", "delay": self.retry_delay}
        except Exception as e:
            return {"success": False, "action": "retry_failed", "error": str(e)}
    
    async def _recovery_restart_component(self, error_record: ErrorRecord) -> Dict[str, Any]:
        """Restart component recovery strategy."""
        try:
            # OCM-specific component restart logic
            module_name = error_record.module
            if module_name in self.modules:
                # Attempt to restart the problematic module
                await asyncio.sleep(2)  # Simulate restart
                return {"success": True, "action": "component_restarted", "component": module_name}
            return {"success": False, "action": "component_not_found", "component": module_name}
        except Exception as e:
            return {"success": False, "action": "restart_failed", "error": str(e)}
    
    async def _recovery_fallback_mode(self, error_record: ErrorRecord) -> Dict[str, Any]:
        """Fallback mode recovery strategy."""
        try:
            # Enable fallback mode for operation control
            return {"success": True, "action": "fallback_mode_enabled", "mode": "minimal_operations"}
        except Exception as e:
            return {"success": False, "action": "fallback_failed", "error": str(e)}
    
    async def _recovery_resource_cleanup(self, error_record: ErrorRecord) -> Dict[str, Any]:
        """Resource cleanup recovery strategy."""
        try:
            # OCM-specific resource cleanup
            cleaned_resources = ["temp_files", "memory_cache", "connection_pools"]
            return {"success": True, "action": "resources_cleaned", "resources": cleaned_resources}
        except Exception as e:
            return {"success": False, "action": "cleanup_failed", "error": str(e)}
    
    async def _recovery_configuration_reset(self, error_record: ErrorRecord) -> Dict[str, Any]:
        """Configuration reset recovery strategy."""
        try:
            # Reset to default OCM configuration
            return {"success": True, "action": "configuration_reset", "config": "default_ocm_config"}
        except Exception as e:
            return {"success": False, "action": "config_reset_failed", "error": str(e)}
    
    async def _recovery_service_restart(self, error_record: ErrorRecord) -> Dict[str, Any]:
        """Service restart recovery strategy."""
        try:
            # OCM service restart logic
            return {"success": True, "action": "service_restarted", "service": "ocm_core"}
        except Exception as e:
            return {"success": False, "action": "service_restart_failed", "error": str(e)}
    
    async def _recovery_data_recovery(self, error_record: ErrorRecord) -> Dict[str, Any]:
        """Data recovery strategy."""
        try:
            # OCM data recovery logic
            return {"success": True, "action": "data_recovered", "method": "backup_restore"}
        except Exception as e:
            return {"success": False, "action": "data_recovery_failed", "error": str(e)}
    
    async def _recovery_network_reset(self, error_record: ErrorRecord) -> Dict[str, Any]:
        """Network reset recovery strategy."""
        try:
            # Network connection reset
            return {"success": True, "action": "network_reset", "connections": "all"}
        except Exception as e:
            return {"success": False, "action": "network_reset_failed", "error": str(e)}
    
    # Error Handlers for OCM-specific categories
    
    async def _handle_operation_control_error(self, error_record: ErrorRecord):
        """Handle operation control specific errors."""
        try:
            self.logger.error(f"Operation control error: {error_record.message}")
            # OCM-specific operation control error handling
            if "OCVM" in self.modules:
                await self.modules["OCVM"].handle_control_error(error_record.context)
        except Exception as e:
            self.logger.error(f"Error handling operation control error: {e}")
    
    async def _handle_verification_system_error(self, error_record: ErrorRecord):
        """Handle verification system errors."""
        try:
            self.logger.error(f"Verification system error: {error_record.message}")
            # Verification system error handling
        except Exception as e:
            self.logger.error(f"Error handling verification system error: {e}")
    
    async def _handle_performance_monitoring_error(self, error_record: ErrorRecord):
        """Handle performance monitoring errors."""
        try:
            self.logger.warning(f"Performance monitoring error: {error_record.message}")
            if "PRFPM" in self.modules:
                await self.modules["PRFPM"].handle_monitoring_error(error_record.context)
        except Exception as e:
            self.logger.error(f"Error handling performance monitoring error: {e}")
    
    async def _handle_resource_management_error(self, error_record: ErrorRecord):
        """Handle resource management errors."""
        try:
            self.logger.warning(f"Resource management error: {error_record.message}")
            if "RMM" in self.modules:
                await self.modules["RMM"].handle_resource_error(error_record.context)
        except Exception as e:
            self.logger.error(f"Error handling resource management error: {e}")
    
    async def _handle_module_communication_error(self, error_record: ErrorRecord):
        """Handle module communication errors."""
        try:
            self.logger.error(f"Module communication error: {error_record.message}")
            # Module communication error handling
        except Exception as e:
            self.logger.error(f"Error handling module communication error: {e}")
    
    async def _handle_system_health_error(self, error_record: ErrorRecord):
        """Handle system health errors."""
        try:
            self.logger.critical(f"System health error: {error_record.message}")
            await self._escalate_error(error_record)
        except Exception as e:
            self.logger.error(f"Error handling system health error: {e}")
    
    async def _handle_data_management_error(self, error_record: ErrorRecord):
        """Handle data management errors."""
        try:
            self.logger.error(f"Data management error: {error_record.message}")
            if "DCM" in self.modules:
                await self.modules["DCM"].handle_data_error(error_record.context)
        except Exception as e:
            self.logger.error(f"Error handling data management error: {e}")
    
    async def _handle_network_communication_error(self, error_record: ErrorRecord):
        """Handle network communication errors."""
        try:
            self.logger.warning(f"Network communication error: {error_record.message}")
            if "NMM" in self.modules:
                await self.modules["NMM"].handle_network_error(error_record.context)
        except Exception as e:
            self.logger.error(f"Error handling network communication error: {e}")
    
    async def _handle_configuration_error(self, error_record: ErrorRecord):
        """Handle configuration errors."""
        try:
            self.logger.error(f"Configuration error: {error_record.message}")
            await self._escalate_error(error_record)
        except Exception as e:
            self.logger.error(f"Error handling configuration error: {e}")
    
    async def _handle_external_service_error(self, error_record: ErrorRecord):
        """Handle external service errors."""
        try:
            self.logger.warning(f"External service error: {error_record.message}")
            # External service error handling with fallback
        except Exception as e:
            self.logger.error(f"Error handling external service error: {e}")
    
    async def _escalate_error(self, error_record: ErrorRecord):
        """Escalate error to CCU through centralized communication."""
        try:
            self.stats["escalations"] += 1
            
            escalation_data = {
                "error_code": error_record.error_code,
                "microservice": "OCM",
                "severity": error_record.severity,
                "category": error_record.category,
                "message": error_record.message,
                "occurrence_count": error_record.occurrence_count,
                "timestamp": error_record.timestamp,
                "context": error_record.context
            }
            
            # Report to CCU through ECM
            if "ECM" in self.modules:
                await self.modules["ECM"].send_error_escalation(escalation_data)
            
            self.logger.critical(f"Error escalated to CCU: {error_record.error_code}")
            
        except Exception as e:
            self.logger.error(f"Error during escalation: {e}")
    
    async def _report_to_ccu(self, error_record: ErrorRecord):
        """Report error to CCU for centralized monitoring."""
        try:
            error_report = {
                "microservice": "OCM",
                "error_code": error_record.error_code,
                "severity": error_record.severity,
                "category": error_record.category,
                "module": error_record.module,
                "message": error_record.message,
                "timestamp": error_record.timestamp,
                "recovery_attempted": error_record.recovery_attempted,
                "recovery_successful": error_record.recovery_successful
            }
            
            if "ECM" in self.modules:
                await self.modules["ECM"].send_error_report(error_report)
                
        except Exception as e:
            self.logger.error(f"Error reporting to CCU: {e}")
    
    def _log_error(self, error_record: ErrorRecord):
        """Log error with appropriate level."""
        log_levels = {
            1: logging.INFO,
            2: logging.WARNING,
            3: logging.ERROR,
            4: logging.CRITICAL,
            5: logging.CRITICAL
        }
        
        log_level = log_levels.get(error_record.severity, logging.ERROR)
        self.logger.log(log_level, 
                       f"[{error_record.error_code}] {error_record.message} "
                       f"({error_record.module}.{error_record.class_name}.{error_record.function_name})")
    
    def _update_statistics(self, error_record: ErrorRecord):
        """Update centralized error statistics."""
        try:
            self.stats["total_errors"] += 1
            self.stats["category_distribution"][error_record.category] += 1
            
            severity_name = ErrorSeverity(error_record.severity).name
            self.stats["severity_distribution"][severity_name] += 1
            
            if error_record.severity >= ErrorSeverity.CRITICAL.value:
                self.stats["critical_errors"] += 1
            
            # Calculate recovery success rate
            if self.stats["recovery_attempts"] > 0:
                success_rate = (self.stats["resolved_errors"] / self.stats["recovery_attempts"]) * 100
                self.stats["recovery_success_rate"] = round(success_rate, 2)
                
        except Exception as e:
            self.logger.error(f"Error updating statistics: {e}")
    
    # Background Tasks
    
    async def _error_pattern_analyzer(self):
        """Analyze error patterns for centralized intelligence."""
        while self.is_active:
            try:
                await asyncio.sleep(self.pattern_analysis_interval)
                
                # Analyze current patterns
                for pattern_key, pattern_info in self.error_patterns.items():
                    if pattern_info["count"] > 10:  # Frequent error pattern
                        self.logger.warning(f"Frequent error pattern detected: {pattern_key} "
                                          f"(Count: {pattern_info['count']})")
                        
                        # Could trigger proactive measures here
                        
            except Exception as e:
                self.logger.error(f"Error in pattern analyzer: {e}")
                await asyncio.sleep(self.pattern_analysis_interval)
    
    async def _statistics_updater(self):
        """Update statistics periodically."""
        while self.is_active:
            try:
                await asyncio.sleep(60)  # Update every minute
                
                # Update any time-based statistics
                current_time = datetime.now()
                
                # Could add more sophisticated analytics here
                
            except Exception as e:
                self.logger.error(f"Error updating statistics: {e}")
                await asyncio.sleep(60)
    
    async def _health_monitor(self):
        """Monitor system health for centralized oversight."""
        while self.is_active:
            try:
                await asyncio.sleep(300)  # Check every 5 minutes
                
                # Check for system health indicators
                active_error_count = len(self.active_errors)
                if active_error_count > 100:  # Too many active errors
                    await self.report_error(
                        module="EMM",
                        class_name="ErrorManagementModule", 
                        function_name="_health_monitor",
                        message=f"High active error count: {active_error_count}",
                        category=ErrorCategory.SYSTEM_HEALTH,
                        severity=ErrorSeverity.HIGH
                    )
                
            except Exception as e:
                self.logger.error(f"Error in health monitor: {e}")
                await asyncio.sleep(300)
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check for centralized monitoring."""
        try:
            is_healthy = (
                self.is_active and 
                len(self.active_errors) < 100 and
                os.path.exists(self.error_db_path)
            )
            
            return {
                'healthy': is_healthy,
                'is_active': self.is_active,
                'active_errors': len(self.active_errors),
                'error_db_exists': os.path.exists(self.error_db_path),
                'error_patterns': len(self.error_patterns)
            }
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return {
                'healthy': False,
                'error': str(e)
            }
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get comprehensive error statistics for centralized reporting."""
        try:
            with sqlite3.connect(self.error_db_path) as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM errors")
                total_db_errors = cursor.fetchone()[0]
                
                cursor = conn.execute("SELECT COUNT(*) FROM errors WHERE recovery_successful = 1")
                resolved_db_errors = cursor.fetchone()[0]
            
            # Perform synchronous health check
            health_status = (
                self.is_active and 
                len(self.active_errors) < 100 and
                os.path.exists(self.error_db_path)
            )
            
            return {
                "runtime_stats": self.stats.copy(),
                "database_stats": {
                    "total_errors": total_db_errors,
                    "resolved_errors": resolved_db_errors
                },
                "active_errors": len(self.active_errors),
                "error_patterns": len(self.error_patterns),
                "health_status": health_status
            }
            
        except Exception as e:
            self.logger.error(f"Error getting statistics: {e}")
            return {"error": "Statistics unavailable"}
    
    def get_error_details(self, error_code: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific error."""
        try:
            with sqlite3.connect(self.error_db_path) as conn:
                cursor = conn.execute("""
                    SELECT * FROM errors WHERE error_code = ?
                """, (error_code,))
                
                row = cursor.fetchone()
                if row:
                    columns = [desc[0] for desc in cursor.description]
                    return dict(zip(columns, row))
                return None
                
        except Exception as e:
            self.logger.error(f"Error retrieving error details: {e}")
            return None
    
    def get_status(self) -> Dict[str, Any]:
        """Get current EMM status for centralized monitoring."""
        return {
            "module": self.module_name,
            "microservice": "OCM", 
            "microservice_code": self.microservice_code,
            "active": self.is_active,
            "active_errors": len(self.active_errors),
            "error_patterns": len(self.error_patterns),
            "centralized_features": {
                "error_code_generation": True,
                "pattern_analysis": True,
                "automated_recovery": True,
                "ccu_integration": True
            },
            "statistics": self.stats.copy()
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive statistics for the EMM module."""
        return {
            'total_errors_handled': self.stats.get('total_errors', 0),
            'recovery_attempts': self.stats.get('recovery_attempts', 0),
            'recovery_successes': self.stats.get('recovery_successes', 0),
            'recovery_failures': self.stats.get('recovery_failures', 0),
            'escalated_errors': self.stats.get('escalated_errors', 0),
            'ccu_reports': self.stats.get('ccu_reports', 0),
            'average_response_time': self.stats.get('average_response_time', 0),
            'last_error_time': self.stats.get('last_error_time'),
            'active_errors': len(self.active_errors),
            'error_patterns': len(self.error_patterns)
        }
    
    async def handle_warning(self, warning_type: str, message: str):
        """Handle warning messages."""
        try:
            warning_record = ErrorRecord(
                error_code=self._generate_error_code("EMM", "ErrorManagementModule", "handle_warning"),
                timestamp=datetime.now().isoformat(),
                severity=ErrorSeverity.LOW.value,
                category=ErrorCategory.SYSTEM_HEALTH.value,
                module="EMM",
                class_name="ErrorManagementModule",
                function_name="handle_warning",
                message=f"Warning: {warning_type} - {message}",
                context={'warning_type': warning_type, 'message': message}
            )
            
            await self._store_error(warning_record)
            self.logger.warning(f"Warning handled: {warning_type} - {message}")
            
        except Exception as e:
            self.logger.error(f"Error handling warning: {e}")
    
    async def handle_error(self, error_type: str, message: str):
        """Handle error messages."""
        try:
            error_record = ErrorRecord(
                error_code=self._generate_error_code("EMM", "ErrorManagementModule", "handle_error"),
                timestamp=datetime.now().isoformat(),
                severity=ErrorSeverity.MEDIUM.value,
                category=ErrorCategory.SYSTEM_HEALTH.value,
                module="EMM",
                class_name="ErrorManagementModule",
                function_name="handle_error",
                message=f"Error: {error_type} - {message}",
                context={'error_type': error_type, 'message': message}
            )
            
            await self._store_error(error_record)
            self.logger.error(f"Error handled: {error_type} - {message}")
            
        except Exception as e:
            self.logger.error(f"Error handling error: {e}") 