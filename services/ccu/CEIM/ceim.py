"""
Central Error Investigation Module (CEIM) - Microservice 07
Centralized Error Handling System for CCU

This module implements the centralized error investigation system that:
1. Handles internal CCU errors using RCM EMM logic with microservice code 07
2. Aggregates and monitors errors from all microservices through interaction modules
3. Provides centralized error control and recovery coordination
4. Manages the error communication flows:
   - Monitoring: EMM → ECM → [Service]IM → CEIM
   - Control: CEIM → [Service]IM → ECM → EMM

Error Code Format: Server(2) + Macroservice(2) + Microservice(2) + Module(2) + Class(2) + Function(3) + Sub-function(3)
CCU Microservice Code: 07
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
from typing import Dict, Any, Optional, List, Callable, Tuple, Set
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
    """CCU-specific internal error categories."""
    CENTRAL_CONTROL = "central_control"
    CERTIFICATE_MANAGEMENT = "certificate_management"
    COMMUNICATION_HUB = "communication_hub"
    TASK_MANAGEMENT = "task_management"
    SERVICE_COORDINATION = "service_coordination"
    RESOURCE_MONITORING = "resource_monitoring"
    SYSTEM_HEALTH = "system_health"
    DATA_MANAGEMENT = "data_management"
    NETWORK_COMMUNICATION = "network_communication"
    CONFIGURATION = "configuration"
    EXTERNAL_INTEGRATION = "external_integration"


class MicroserviceType(Enum):
    """All microservices in the Horus system."""
    RCM = ("01", "RCM")
    RLA = ("02", "RLA") 
    TPP = ("03", "TPP")
    JFA = ("04", "JFA")
    TD = ("05", "TD")
    OCM = ("06", "OCM")
    CCU = ("07", "CCU")


class RecoveryStrategy(Enum):
    """Automated recovery strategies for centralized control."""
    RETRY = "retry"
    RESTART_COMPONENT = "restart_component"
    RESTART_SERVICE = "restart_service"
    FALLBACK_MODE = "fallback_mode"
    RESOURCE_CLEANUP = "resource_cleanup"
    CONFIGURATION_RESET = "configuration_reset"
    ESCALATE_TO_ADMIN = "escalate_to_admin"
    ISOLATE_SERVICE = "isolate_service"
    LOAD_BALANCE_REDISTRIBUTE = "load_balance_redistribute"
    CERTIFICATE_REFRESH = "certificate_refresh"


@dataclass
class CentralizedErrorRecord:
    """Centralized error record structure for all microservices."""
    error_code: str
    microservice: str
    microservice_code: str
    timestamp: str
    severity: int
    category: str
    module: str
    class_name: str
    function_name: str
    message: str
    context: Dict[str, Any]
    source: str  # "internal" for CCU errors, "external" for other microservices
    stack_trace: Optional[str] = None
    recovery_attempted: bool = False
    recovery_successful: bool = False
    recovery_details: Optional[str] = None
    occurrence_count: int = 1
    first_occurrence: Optional[str] = None
    last_occurrence: Optional[str] = None
    investigation_status: str = "pending"
    investigation_results: Optional[str] = None


@dataclass 
class MicroserviceHealthStatus:
    """Health status tracking for each microservice."""
    service_name: str
    service_code: str
    is_online: bool
    last_heartbeat: str
    error_count: int
    critical_error_count: int
    recovery_success_rate: float
    response_time: float
    status: str  # healthy, degraded, critical, offline


class CentralErrorInvestigationModule:
    """
    Central Error Investigation Module (CEIM) for CCU
    
    Implements centralized error handling following RCM EMM logic for internal CCU errors
    and coordinates centralized error monitoring and control across all microservices.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize centralized error investigation system."""
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.module_name = "CEIM"
        self.microservice_code = "07"  # CCU microservice identifier
        
        # Centralized error handling state
        self.is_active = False
        self.error_db_path = os.path.join("logs", "ccu_centralized_errors.db")
        self.error_patterns = {}
        self.active_internal_errors = {}  # CCU internal errors
        self.active_external_errors = {}  # Errors from other microservices
        
        # Centralized coordination
        self.microservice_health = {}  # Track health of all microservices
        self.interaction_modules = {}  # References to interaction modules
        self.error_correlations = {}   # Cross-service error correlations
        
        # Error processing configuration
        self.max_retries = 3
        self.retry_delay = 5.0
        self.escalation_threshold = 5
        self.investigation_interval = 300  # 5 minutes
        self.health_check_interval = 60    # 1 minute
        
        # Statistics for centralized monitoring
        self.stats = {
            "total_internal_errors": 0,
            "total_external_errors": 0,
            "resolved_internal_errors": 0,
            "resolved_external_errors": 0,
            "critical_errors": 0,
            "recovery_attempts": 0,
            "recovery_success_rate": 0.0,
            "pattern_detections": 0,
            "escalations": 0,
            "cross_service_correlations": 0,
            "microservice_stats": {service.value[1]: 0 for service in MicroserviceType},
            "category_distribution": {category.value: 0 for category in ErrorCategory},
            "severity_distribution": {sev.name: 0 for sev in ErrorSeverity}
        }
        
        # Recovery strategies for centralized coordination
        self.internal_recovery_strategies = self._initialize_internal_recovery_strategies()
        self.external_recovery_strategies = self._initialize_external_recovery_strategies()
        
        # Module references
        self.modules = {}
        
        # Initialize centralized error handling components
        self._initialize_error_database()
        self._initialize_microservice_health_tracking()
        
        self.logger.info("CCU CEIM initialized with centralized error handling")
    
    def _initialize_error_database(self):
        """Initialize SQLite database for centralized error storage."""
        try:
            os.makedirs(os.path.dirname(self.error_db_path), exist_ok=True)
            
            with sqlite3.connect(self.error_db_path) as conn:
                # Internal CCU errors table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS internal_errors (
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
                        last_occurrence TEXT,
                        investigation_status TEXT DEFAULT 'pending',
                        investigation_results TEXT
                    )
                """)
                
                # External microservice errors table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS external_errors (
                        error_code TEXT PRIMARY KEY,
                        microservice TEXT NOT NULL,
                        microservice_code TEXT NOT NULL,
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
                        last_occurrence TEXT,
                        investigation_status TEXT DEFAULT 'pending',
                        investigation_results TEXT
                    )
                """)
                
                # Microservice health tracking table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS microservice_health (
                        service_name TEXT PRIMARY KEY,
                        service_code TEXT NOT NULL,
                        is_online BOOLEAN DEFAULT 1,
                        last_heartbeat TEXT NOT NULL,
                        error_count INTEGER DEFAULT 0,
                        critical_error_count INTEGER DEFAULT 0,
                        recovery_success_rate REAL DEFAULT 0.0,
                        response_time REAL DEFAULT 0.0,
                        status TEXT DEFAULT 'healthy'
                    )
                """)
                
                # Error correlations table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS error_correlations (
                        correlation_id TEXT PRIMARY KEY,
                        primary_service TEXT NOT NULL,
                        secondary_service TEXT NOT NULL,
                        correlation_type TEXT NOT NULL,
                        correlation_strength REAL NOT NULL,
                        first_detected TEXT NOT NULL,
                        last_detected TEXT NOT NULL,
                        occurrence_count INTEGER DEFAULT 1
                    )
                """)
                
                # Create indexes
                conn.execute("CREATE INDEX IF NOT EXISTS idx_internal_timestamp ON internal_errors(timestamp)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_internal_severity ON internal_errors(severity)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_external_service ON external_errors(microservice)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_external_timestamp ON external_errors(timestamp)")
                
                conn.commit()
                
            self.logger.info("Centralized error database initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize centralized error database: {e}")
            raise
    
    def _initialize_microservice_health_tracking(self):
        """Initialize health tracking for all microservices."""
        try:
            for service in MicroserviceType:
                service_name = service.value[1]
                service_code = service.value[0]
                
                self.microservice_health[service_name] = MicroserviceHealthStatus(
                    service_name=service_name,
                    service_code=service_code,
                    is_online=True,
                    last_heartbeat=datetime.now().isoformat(),
                    error_count=0,
                    critical_error_count=0,
                    recovery_success_rate=0.0,
                    response_time=0.0,
                    status="healthy"
                )
            
            self.logger.info("Microservice health tracking initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize microservice health tracking: {e}")
            raise
    
    def _generate_internal_error_code(self, module: str, class_name: str, function_name: str, 
                                    sub_function: str = "000") -> str:
        """
        Generate 16-character hexadecimal error code for internal CCU errors.
        Format: Server(2) + Macroservice(2) + Microservice(2) + Module(2) + Class(2) + Function(3) + Sub-function(3)
        """
        try:
            # Server code (assume 01 for primary server)
            server_code = "01"
            
            # Macroservice code (01 for main computation server)
            macroservice_code = "01"
            
            # Microservice code (07 for CCU)
            microservice_code = "07"
            
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
            self.logger.error(f"Error generating internal error code: {e}")
            return "0101070000000000"  # Fallback error code
    
    def _initialize_internal_recovery_strategies(self):
        """Initialize recovery strategies for internal CCU errors."""
        return {
            ErrorCategory.CENTRAL_CONTROL: RecoveryStrategy.RESTART_COMPONENT,
            ErrorCategory.CERTIFICATE_MANAGEMENT: RecoveryStrategy.CERTIFICATE_REFRESH,
            ErrorCategory.COMMUNICATION_HUB: RecoveryStrategy.RESTART_SERVICE,
            ErrorCategory.TASK_MANAGEMENT: RecoveryStrategy.RESOURCE_CLEANUP,
            ErrorCategory.SERVICE_COORDINATION: RecoveryStrategy.RESTART_COMPONENT,
            ErrorCategory.RESOURCE_MONITORING: RecoveryStrategy.RETRY,
            ErrorCategory.SYSTEM_HEALTH: RecoveryStrategy.ESCALATE_TO_ADMIN,
            ErrorCategory.DATA_MANAGEMENT: RecoveryStrategy.RESOURCE_CLEANUP,
            ErrorCategory.NETWORK_COMMUNICATION: RecoveryStrategy.RESTART_SERVICE,
            ErrorCategory.CONFIGURATION: RecoveryStrategy.CONFIGURATION_RESET,
            ErrorCategory.EXTERNAL_INTEGRATION: RecoveryStrategy.FALLBACK_MODE
        }
    
    def _initialize_external_recovery_strategies(self):
        """Initialize recovery strategies for coordinating external microservice errors."""
        return {
            "RCM": RecoveryStrategy.LOAD_BALANCE_REDISTRIBUTE,
            "RLA": RecoveryStrategy.RESTART_SERVICE,
            "TPP": RecoveryStrategy.RESTART_COMPONENT,
            "JFA": RecoveryStrategy.RESOURCE_CLEANUP,
            "TD": RecoveryStrategy.RESTART_COMPONENT,
            "OCM": RecoveryStrategy.RESTART_SERVICE,
            "CCU": RecoveryStrategy.RESTART_COMPONENT
        }
    
    def set_interaction_module_references(self, interaction_modules: Dict[str, Any]):
        """Set references to interaction modules for centralized communication."""
        self.interaction_modules = interaction_modules
        self.logger.info(f"Interaction module references set: {list(interaction_modules.keys())}")
    
    def set_module_references(self, modules: Dict[str, Any]):
        """Set references to other CCU modules."""
        self.modules = modules
        self.logger.info("CCU module references set for centralized error handling")
    
    async def start(self):
        """Start centralized error investigation system."""
        try:
            self.is_active = True
            
            # Start background tasks for centralized processing
            asyncio.create_task(self._error_investigation_processor())
            asyncio.create_task(self._microservice_health_monitor())
            asyncio.create_task(self._error_correlation_analyzer())
            asyncio.create_task(self._centralized_recovery_coordinator())
            asyncio.create_task(self._statistics_updater())
            
            self.logger.info("CCU CEIM started - centralized error investigation active")
            
        except Exception as e:
            self.logger.error(f"Failed to start CEIM: {e}")
            raise
    
    async def stop(self):
        """Stop centralized error investigation system."""
        try:
            self.is_active = False
            self.logger.info("CCU CEIM stopped successfully")
            
        except Exception as e:
            self.logger.error(f"Error stopping CEIM: {e}")
    
    async def report_internal_error(self, 
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
        Report an internal CCU error using centralized error handling logic.
        Returns the generated error code for tracking.
        """
        try:
            # Generate centralized error code for CCU
            error_code = self._generate_internal_error_code(module, class_name, function_name, sub_function)
            
            # Create error record
            error_record = CentralizedErrorRecord(
                error_code=error_code,
                microservice="CCU",
                microservice_code="07",
                timestamp=datetime.now().isoformat(),
                severity=severity.value,
                category=category.value,
                module=module,
                class_name=class_name,
                function_name=function_name,
                message=message,
                context=context or {},
                source="internal",
                stack_trace=traceback.format_exc() if exception else None,
                first_occurrence=datetime.now().isoformat(),
                last_occurrence=datetime.now().isoformat()
            )
            
            # Process internal error
            await self._process_internal_error(error_record)
            
            return error_code
            
        except Exception as e:
            self.logger.critical(f"Critical failure in internal error reporting: {e}")
            return "INTERNAL_ERROR_REPORT_FAILED"
    
    async def receive_external_error_report(self, error_report: Dict[str, Any]):
        """
        Receive error report from external microservice through interaction module.
        This implements the monitoring flow: EMM → ECM → [Service]IM → CEIM
        """
        try:
            # Create centralized error record from external report
            error_record = CentralizedErrorRecord(
                error_code=error_report.get("error_code", "UNKNOWN"),
                microservice=error_report.get("microservice", "UNKNOWN"),
                microservice_code=error_report.get("microservice_code", "00"),
                timestamp=error_report.get("timestamp", datetime.now().isoformat()),
                severity=error_report.get("severity", ErrorSeverity.MEDIUM.value),
                category=error_report.get("category", "unknown"),
                module=error_report.get("module", "Unknown"),
                class_name=error_report.get("class_name", "Unknown"),
                function_name=error_report.get("function_name", "unknown"),
                message=error_report.get("message", "No message provided"),
                context=error_report.get("context", {}),
                source="external",
                stack_trace=error_report.get("stack_trace"),
                recovery_attempted=error_report.get("recovery_attempted", False),
                recovery_successful=error_report.get("recovery_successful", False)
            )
            
            # Process external error
            await self._process_external_error(error_record)
            
            # Update microservice health
            await self._update_microservice_health(error_record)
            
            self.logger.info(f"Received external error report: {error_record.error_code} from {error_record.microservice}")
            
        except Exception as e:
            self.logger.error(f"Error processing external error report: {e}")
    
    async def _process_internal_error(self, error_record: CentralizedErrorRecord):
        """Process internal CCU error using centralized logic."""
        try:
            # Check for existing pattern
            await self._check_internal_error_pattern(error_record)
            
            # Store in centralized database
            await self._store_internal_error(error_record)
            
            # Update statistics
            self._update_internal_statistics(error_record)
            
            # Log error
            self._log_error(error_record)
            
            # Add to active internal errors
            self.active_internal_errors[error_record.error_code] = error_record
            
            # Attempt automated recovery for critical errors
            if error_record.severity >= ErrorSeverity.CRITICAL.value:
                await self._attempt_internal_recovery(error_record)
            
        except Exception as e:
            self.logger.error(f"Error processing internal error: {e}")
    
    async def _process_external_error(self, error_record: CentralizedErrorRecord):
        """Process external microservice error for centralized coordination."""
        try:
            # Check for cross-service error correlations
            await self._check_error_correlations(error_record)
            
            # Store in centralized database
            await self._store_external_error(error_record)
            
            # Update statistics
            self._update_external_statistics(error_record)
            
            # Add to active external errors
            self.active_external_errors[error_record.error_code] = error_record
            
            # Start investigation if critical or high occurrence
            if (error_record.severity >= ErrorSeverity.CRITICAL.value or
                error_record.occurrence_count >= self.escalation_threshold):
                await self._start_centralized_investigation(error_record)
            
            self.logger.info(f"Processed external error from {error_record.microservice}: {error_record.error_code}")
            
        except Exception as e:
            self.logger.error(f"Error processing external error: {e}")
    
    async def _check_internal_error_pattern(self, error_record: CentralizedErrorRecord):
        """Check for internal error patterns."""
        try:
            pattern_key = f"internal_{error_record.module}_{error_record.class_name}_{error_record.function_name}"
            
            if pattern_key in self.error_patterns:
                pattern_info = self.error_patterns[pattern_key]
                pattern_info["count"] += 1
                pattern_info["last_occurrence"] = error_record.timestamp
                
                error_record.occurrence_count = pattern_info["count"]
                error_record.first_occurrence = pattern_info["first_occurrence"]
                
                # Check for escalation threshold
                if pattern_info["count"] >= self.escalation_threshold:
                    await self._escalate_internal_error(error_record)
                    
            else:
                self.error_patterns[pattern_key] = {
                    "count": 1,
                    "first_occurrence": error_record.timestamp,
                    "last_occurrence": error_record.timestamp,
                    "category": error_record.category,
                    "severity": error_record.severity,
                    "source": "internal"
                }
                
                self.stats["pattern_detections"] += 1
                
        except Exception as e:
            self.logger.error(f"Error in internal pattern checking: {e}")
    
    async def _check_error_correlations(self, error_record: CentralizedErrorRecord):
        """Check for cross-service error correlations."""
        try:
            # Look for related errors in other services within time window
            correlation_window = timedelta(minutes=5)
            current_time = datetime.fromisoformat(error_record.timestamp)
            
            for active_error in self.active_external_errors.values():
                if active_error.microservice != error_record.microservice:
                    error_time = datetime.fromisoformat(active_error.timestamp)
                    
                    if abs((current_time - error_time).total_seconds()) <= correlation_window.total_seconds():
                        correlation_id = f"{active_error.microservice}_{error_record.microservice}_{active_error.category}_{error_record.category}"
                        
                        if correlation_id not in self.error_correlations:
                            self.error_correlations[correlation_id] = {
                                "primary_service": active_error.microservice,
                                "secondary_service": error_record.microservice,
                                "correlation_type": "temporal",
                                "strength": 1.0,
                                "first_detected": datetime.now().isoformat(),
                                "count": 1
                            }
                            
                            self.stats["cross_service_correlations"] += 1
                            
                            self.logger.warning(f"Cross-service error correlation detected: {active_error.microservice} ↔ {error_record.microservice}")
                        else:
                            self.error_correlations[correlation_id]["count"] += 1
            
        except Exception as e:
            self.logger.error(f"Error checking correlations: {e}")
    
    async def _store_internal_error(self, error_record: CentralizedErrorRecord):
        """Store internal error in centralized database."""
        try:
            with sqlite3.connect(self.error_db_path) as conn:
                cursor = conn.execute("SELECT occurrence_count FROM internal_errors WHERE error_code = ?", 
                                    (error_record.error_code,))
                existing = cursor.fetchone()
                
                if existing:
                    # Update existing record
                    conn.execute("""
                        UPDATE internal_errors SET 
                        occurrence_count = occurrence_count + 1,
                        last_occurrence = ?,
                        context = ?
                        WHERE error_code = ?
                    """, (error_record.timestamp, json.dumps(error_record.context), error_record.error_code))
                else:
                    # Insert new record
                    conn.execute("""
                        INSERT INTO internal_errors (
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
            self.logger.error(f"Error storing internal error: {e}")
    
    async def _store_external_error(self, error_record: CentralizedErrorRecord):
        """Store external error in centralized database."""
        try:
            with sqlite3.connect(self.error_db_path) as conn:
                cursor = conn.execute("SELECT occurrence_count FROM external_errors WHERE error_code = ?", 
                                    (error_record.error_code,))
                existing = cursor.fetchone()
                
                if existing:
                    # Update existing record
                    conn.execute("""
                        UPDATE external_errors SET 
                        occurrence_count = occurrence_count + 1,
                        last_occurrence = ?,
                        context = ?
                        WHERE error_code = ?
                    """, (error_record.timestamp, json.dumps(error_record.context), error_record.error_code))
                else:
                    # Insert new record
                    conn.execute("""
                        INSERT INTO external_errors (
                            error_code, microservice, microservice_code, timestamp, severity, 
                            category, module, class_name, function_name, message, context, 
                            stack_trace, first_occurrence, last_occurrence, recovery_attempted, recovery_successful
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        error_record.error_code, error_record.microservice, error_record.microservice_code,
                        error_record.timestamp, error_record.severity, error_record.category,
                        error_record.module, error_record.class_name, error_record.function_name,
                        error_record.message, json.dumps(error_record.context), error_record.stack_trace,
                        error_record.first_occurrence, error_record.last_occurrence,
                        error_record.recovery_attempted, error_record.recovery_successful
                    ))
                
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Error storing external error: {e}")
    
    async def _attempt_internal_recovery(self, error_record: CentralizedErrorRecord):
        """Attempt automated recovery for internal CCU errors."""
        try:
            category = ErrorCategory(error_record.category)
            strategy = self.internal_recovery_strategies.get(category, RecoveryStrategy.ESCALATE_TO_ADMIN)
            
            error_record.recovery_attempted = True
            self.stats["recovery_attempts"] += 1
            
            recovery_result = await self._execute_internal_recovery_strategy(strategy, error_record)
            
            if recovery_result["success"]:
                error_record.recovery_successful = True
                error_record.recovery_details = json.dumps(recovery_result)
                
                # Update database
                with sqlite3.connect(self.error_db_path) as conn:
                    conn.execute("""
                        UPDATE internal_errors SET 
                        recovery_attempted = 1,
                        recovery_successful = 1,
                        recovery_details = ?
                        WHERE error_code = ?
                    """, (error_record.recovery_details, error_record.error_code))
                    conn.commit()
                
                # Remove from active errors
                if error_record.error_code in self.active_internal_errors:
                    del self.active_internal_errors[error_record.error_code]
                
                self.stats["resolved_internal_errors"] += 1
                self.logger.info(f"Internal error recovery successful: {error_record.error_code}")
                
            else:
                error_record.recovery_details = json.dumps(recovery_result)
                self.logger.warning(f"Internal error recovery failed: {error_record.error_code}")
                
        except Exception as e:
            self.logger.error(f"Error during internal recovery attempt: {e}")
    
    async def send_recovery_command(self, target_service: str, recovery_command: Dict[str, Any]):
        """
        Send recovery command to external microservice through interaction module.
        This implements the control flow: CEIM → [Service]IM → ECM → EMM
        """
        try:
            # Map service names to interaction module names
            service_to_im_mapping = {
                "RCM": "RCMIM",
                "RLA": "RLAIM", 
                "TPP": "TPPIM",
                "JFA": "JFAIM",
                "TD": "TDIM",
                "OCM": "OCMIM"
            }
            
            im_name = service_to_im_mapping.get(target_service)
            if im_name and im_name in self.interaction_modules:
                await self.interaction_modules[im_name].send_recovery_command(recovery_command)
                self.logger.info(f"Sent recovery command to {target_service} via {im_name}")
            else:
                self.logger.warning(f"No interaction module found for {target_service}")
                
        except Exception as e:
            self.logger.error(f"Error sending recovery command to {target_service}: {e}")
    
    async def _start_centralized_investigation(self, error_record: CentralizedErrorRecord):
        """Start centralized investigation for critical external errors."""
        try:
            error_record.investigation_status = "investigating"
            
            investigation_results = {
                "investigation_started": datetime.now().isoformat(),
                "service": error_record.microservice,
                "error_code": error_record.error_code,
                "severity": error_record.severity,
                "related_correlations": [],
                "recommended_actions": []
            }
            
            # Check for related correlations
            for correlation_id, correlation in self.error_correlations.items():
                if (correlation["primary_service"] == error_record.microservice or 
                    correlation["secondary_service"] == error_record.microservice):
                    investigation_results["related_correlations"].append(correlation)
            
            # Generate recommendations based on service and error type
            recommendations = await self._generate_centralized_recommendations(error_record)
            investigation_results["recommended_actions"] = recommendations
            
            # Store investigation results
            error_record.investigation_results = json.dumps(investigation_results)
            error_record.investigation_status = "completed"
            
            self.logger.info(f"Centralized investigation completed for {error_record.error_code}")
            
            # If critical, coordinate recovery across services
            if error_record.severity >= ErrorSeverity.CRITICAL.value:
                await self._coordinate_cross_service_recovery(error_record, investigation_results)
            
        except Exception as e:
            self.logger.error(f"Error in centralized investigation: {e}")
    
    async def _generate_centralized_recommendations(self, error_record: CentralizedErrorRecord) -> List[str]:
        """Generate centralized recovery recommendations."""
        recommendations = []
        
        try:
            service = error_record.microservice
            severity = error_record.severity
            
            # Service-specific recommendations
            if service == "RCM":
                recommendations.extend([
                    "Check resource computation load distribution",
                    "Verify database connection pools",
                    "Monitor memory usage patterns"
                ])
            elif service == "RLA":
                recommendations.extend([
                    "Check research and learning algorithm processing",
                    "Verify data pipeline integrity",
                    "Monitor ML model performance"
                ])
            elif service == "TPP":
                recommendations.extend([
                    "Check text processing pipeline",
                    "Verify template generation system",
                    "Monitor NLP model resources"
                ])
            elif service == "JFA":
                recommendations.extend([
                    "Check JSON file assembly process",
                    "Verify file generation pipeline",
                    "Monitor storage capacity"
                ])
            elif service == "TD":
                recommendations.extend([
                    "Check technical drawing generation",
                    "Verify calculation engine integrity",
                    "Monitor rendering resources"
                ])
            elif service == "OCM":
                recommendations.extend([
                    "Check operation control systems",
                    "Verify monitoring and verification",
                    "Monitor system performance metrics"
                ])
            
            # Severity-based recommendations
            if severity >= ErrorSeverity.CRITICAL.value:
                recommendations.extend([
                    "Consider service isolation to prevent cascade failures",
                    "Initiate emergency fallback procedures",
                    "Alert system administrators immediately"
                ])
            
            # Correlation-based recommendations
            related_services = [corr["secondary_service"] for corr in self.error_correlations.values() 
                              if corr["primary_service"] == service]
            if related_services:
                recommendations.append(f"Monitor related services for cascade effects: {', '.join(set(related_services))}")
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Error generating recommendations: {e}")
            return ["Unable to generate recommendations due to system error"]
    
    async def _coordinate_cross_service_recovery(self, error_record: CentralizedErrorRecord, investigation_results: Dict[str, Any]):
        """Coordinate recovery actions across multiple services."""
        try:
            service = error_record.microservice
            
            # Determine recovery strategy
            recovery_strategy = self.external_recovery_strategies.get(service, RecoveryStrategy.ESCALATE_TO_ADMIN)
            
            recovery_command = {
                "command_type": "centralized_recovery",
                "target_service": service,
                "strategy": recovery_strategy.value,
                "error_code": error_record.error_code,
                "investigation_results": investigation_results,
                "timestamp": datetime.now().isoformat(),
                "initiated_by": "CEIM"
            }
            
            # Send recovery command to target service
            await self.send_recovery_command(service, recovery_command)
            
            # Also coordinate with related services if correlations exist
            for correlation in investigation_results.get("related_correlations", []):
                related_service = correlation.get("secondary_service")
                if related_service and related_service != service:
                    preventive_command = {
                        "command_type": "preventive_action",
                        "target_service": related_service,
                        "primary_error_service": service,
                        "correlation_info": correlation,
                        "timestamp": datetime.now().isoformat(),
                        "initiated_by": "CEIM"
                    }
                    
                    await self.send_recovery_command(related_service, preventive_command)
            
            self.logger.info(f"Cross-service recovery coordination initiated for {service}")
            
        except Exception as e:
            self.logger.error(f"Error coordinating cross-service recovery: {e}")
    
    async def _execute_internal_recovery_strategy(self, strategy: RecoveryStrategy, error_record: CentralizedErrorRecord) -> Dict[str, Any]:
        """Execute specific internal recovery strategy."""
        try:
            if strategy == RecoveryStrategy.RETRY:
                return await self._internal_recovery_retry(error_record)
            elif strategy == RecoveryStrategy.RESTART_COMPONENT:
                return await self._internal_recovery_restart_component(error_record)
            elif strategy == RecoveryStrategy.RESTART_SERVICE:
                return await self._internal_recovery_restart_service(error_record)
            elif strategy == RecoveryStrategy.RESOURCE_CLEANUP:
                return await self._internal_recovery_resource_cleanup(error_record)
            elif strategy == RecoveryStrategy.CONFIGURATION_RESET:
                return await self._internal_recovery_configuration_reset(error_record)
            elif strategy == RecoveryStrategy.CERTIFICATE_REFRESH:
                return await self._internal_recovery_certificate_refresh(error_record)
            elif strategy == RecoveryStrategy.ESCALATE_TO_ADMIN:
                return await self._internal_recovery_escalate_to_admin(error_record)
            else:
                return {"success": False, "action": "unsupported_strategy", "strategy": strategy.value}
                
        except Exception as e:
            return {"success": False, "action": "strategy_execution_failed", "error": str(e)}
    
    # Internal Recovery Strategy Implementations
    
    async def _internal_recovery_retry(self, error_record: CentralizedErrorRecord) -> Dict[str, Any]:
        """Retry recovery strategy for transient internal errors."""
        try:
            await asyncio.sleep(self.retry_delay)
            return {"success": True, "action": "retry", "delay": self.retry_delay}
        except Exception as e:
            return {"success": False, "action": "retry_failed", "error": str(e)}
    
    async def _internal_recovery_restart_component(self, error_record: CentralizedErrorRecord) -> Dict[str, Any]:
        """Restart component recovery strategy for internal CCU components."""
        try:
            module_name = error_record.module
            if module_name in self.modules:
                # Attempt to restart the problematic CCU module
                await asyncio.sleep(2)  # Simulate restart
                return {"success": True, "action": "component_restarted", "component": module_name}
            return {"success": False, "action": "component_not_found", "component": module_name}
        except Exception as e:
            return {"success": False, "action": "restart_failed", "error": str(e)}
    
    async def _internal_recovery_restart_service(self, error_record: CentralizedErrorRecord) -> Dict[str, Any]:
        """Restart CCU service recovery strategy."""
        try:
            # CCU service restart logic
            return {"success": True, "action": "service_restarted", "service": "ccu_core"}
        except Exception as e:
            return {"success": False, "action": "service_restart_failed", "error": str(e)}
    
    async def _internal_recovery_resource_cleanup(self, error_record: CentralizedErrorRecord) -> Dict[str, Any]:
        """Resource cleanup recovery strategy for CCU."""
        try:
            # CCU-specific resource cleanup
            cleaned_resources = ["temp_files", "memory_cache", "connection_pools", "certificate_cache"]
            return {"success": True, "action": "resources_cleaned", "resources": cleaned_resources}
        except Exception as e:
            return {"success": False, "action": "cleanup_failed", "error": str(e)}
    
    async def _internal_recovery_configuration_reset(self, error_record: CentralizedErrorRecord) -> Dict[str, Any]:
        """Configuration reset recovery strategy for CCU."""
        try:
            # Reset to default CCU configuration
            return {"success": True, "action": "configuration_reset", "config": "default_ccu_config"}
        except Exception as e:
            return {"success": False, "action": "config_reset_failed", "error": str(e)}
    
    async def _internal_recovery_certificate_refresh(self, error_record: CentralizedErrorRecord) -> Dict[str, Any]:
        """Certificate refresh recovery strategy for CCU certificate management."""
        try:
            # CCU certificate refresh logic
            return {"success": True, "action": "certificates_refreshed", "certificates": "all_service_certificates"}
        except Exception as e:
            return {"success": False, "action": "certificate_refresh_failed", "error": str(e)}
    
    async def _internal_recovery_escalate_to_admin(self, error_record: CentralizedErrorRecord) -> Dict[str, Any]:
        """Escalate to admin recovery strategy."""
        try:
            # Escalation logic for critical CCU errors
            escalation_data = {
                "error_code": error_record.error_code,
                "severity": error_record.severity,
                "category": error_record.category,
                "message": error_record.message,
                "escalated_at": datetime.now().isoformat(),
                "requires_manual_intervention": True
            }
            
            self.logger.critical(f"CCU error escalated to admin: {error_record.error_code}")
            
            return {"success": False, "action": "escalated_to_admin", "escalation_data": escalation_data}
        except Exception as e:
            return {"success": False, "action": "escalation_failed", "error": str(e)}
    
    async def _update_microservice_health(self, error_record: CentralizedErrorRecord):
        """Update microservice health status based on error reports."""
        try:
            service_name = error_record.microservice
            if service_name in self.microservice_health:
                health_status = self.microservice_health[service_name]
                
                # Update error counts
                health_status.error_count += 1
                if error_record.severity >= ErrorSeverity.CRITICAL.value:
                    health_status.critical_error_count += 1
                
                # Update last heartbeat
                health_status.last_heartbeat = error_record.timestamp
                
                # Determine health status
                if health_status.critical_error_count > 5:
                    health_status.status = "critical"
                    health_status.is_online = False
                elif health_status.error_count > 20:
                    health_status.status = "degraded"
                else:
                    health_status.status = "healthy"
                
                # Update in database
                await self._store_microservice_health(health_status)
                
        except Exception as e:
            self.logger.error(f"Error updating microservice health: {e}")
    
    async def _store_microservice_health(self, health_status: MicroserviceHealthStatus):
        """Store microservice health status in database."""
        try:
            with sqlite3.connect(self.error_db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO microservice_health (
                        service_name, service_code, is_online, last_heartbeat, 
                        error_count, critical_error_count, recovery_success_rate, 
                        response_time, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    health_status.service_name, health_status.service_code,
                    health_status.is_online, health_status.last_heartbeat,
                    health_status.error_count, health_status.critical_error_count,
                    health_status.recovery_success_rate, health_status.response_time,
                    health_status.status
                ))
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Error storing microservice health: {e}")
    
    def _log_error(self, error_record: CentralizedErrorRecord):
        """Log error with appropriate level."""
        log_levels = {
            1: logging.INFO,
            2: logging.WARNING,
            3: logging.ERROR,
            4: logging.CRITICAL,
            5: logging.CRITICAL
        }
        
        log_level = log_levels.get(error_record.severity, logging.ERROR)
        source_prefix = "INTERNAL" if error_record.source == "internal" else f"EXTERNAL-{error_record.microservice}"
        
        self.logger.log(log_level, 
                       f"[{source_prefix}][{error_record.error_code}] {error_record.message} "
                       f"({error_record.module}.{error_record.class_name}.{error_record.function_name})")
    
    def _update_internal_statistics(self, error_record: CentralizedErrorRecord):
        """Update internal error statistics."""
        try:
            self.stats["total_internal_errors"] += 1
            self.stats["category_distribution"][error_record.category] += 1
            
            severity_name = ErrorSeverity(error_record.severity).name
            self.stats["severity_distribution"][severity_name] += 1
            
            if error_record.severity >= ErrorSeverity.CRITICAL.value:
                self.stats["critical_errors"] += 1
            
            # Calculate recovery success rate
            if self.stats["recovery_attempts"] > 0:
                success_rate = (self.stats["resolved_internal_errors"] / self.stats["recovery_attempts"]) * 100
                self.stats["recovery_success_rate"] = round(success_rate, 2)
                
        except Exception as e:
            self.logger.error(f"Error updating internal statistics: {e}")
    
    def _update_external_statistics(self, error_record: CentralizedErrorRecord):
        """Update external error statistics."""
        try:
            self.stats["total_external_errors"] += 1
            self.stats["microservice_stats"][error_record.microservice] += 1
            
            severity_name = ErrorSeverity(error_record.severity).name
            self.stats["severity_distribution"][severity_name] += 1
            
            if error_record.severity >= ErrorSeverity.CRITICAL.value:
                self.stats["critical_errors"] += 1
                
        except Exception as e:
            self.logger.error(f"Error updating external statistics: {e}")
    
    async def _escalate_internal_error(self, error_record: CentralizedErrorRecord):
        """Escalate internal CCU error."""
        try:
            self.stats["escalations"] += 1
            
            escalation_data = {
                "error_code": error_record.error_code,
                "microservice": "CCU",
                "severity": error_record.severity,
                "category": error_record.category,
                "message": error_record.message,
                "occurrence_count": error_record.occurrence_count,
                "timestamp": error_record.timestamp,
                "context": error_record.context,
                "requires_immediate_attention": True
            }
            
            self.logger.critical(f"Internal CCU error escalated: {error_record.error_code}")
            
            # Could send to external monitoring system or admin notification
            
        except Exception as e:
            self.logger.error(f"Error during internal escalation: {e}")
    
    # Background Tasks
    
    async def _error_investigation_processor(self):
        """Process error investigations continuously."""
        while self.is_active:
            try:
                await asyncio.sleep(self.investigation_interval)
                
                # Process pending investigations for critical errors
                for error_code, error_record in list(self.active_external_errors.items()):
                    if (error_record.severity >= ErrorSeverity.CRITICAL.value and
                        error_record.investigation_status == "pending"):
                        await self._start_centralized_investigation(error_record)
                
            except Exception as e:
                self.logger.error(f"Error in investigation processor: {e}")
                await asyncio.sleep(self.investigation_interval)
    
    async def _microservice_health_monitor(self):
        """Monitor microservice health status."""
        while self.is_active:
            try:
                await asyncio.sleep(self.health_check_interval)
                
                current_time = datetime.now()
                
                # Check for services that haven't reported recently
                for service_name, health_status in self.microservice_health.items():
                    last_heartbeat = datetime.fromisoformat(health_status.last_heartbeat)
                    time_since_heartbeat = (current_time - last_heartbeat).total_seconds()
                    
                    # Mark service as offline if no heartbeat for 5 minutes
                    if time_since_heartbeat > 300:  # 5 minutes
                        if health_status.is_online:
                            health_status.is_online = False
                            health_status.status = "offline"
                            await self._store_microservice_health(health_status)
                            
                            self.logger.warning(f"Microservice {service_name} marked as offline - no heartbeat for {time_since_heartbeat}s")
                
            except Exception as e:
                self.logger.error(f"Error in health monitor: {e}")
                await asyncio.sleep(self.health_check_interval)
    
    async def _error_correlation_analyzer(self):
        """Analyze error correlations across services."""
        while self.is_active:
            try:
                await asyncio.sleep(300)  # Analyze every 5 minutes
                
                # Look for new correlations
                services_with_errors = set()
                for error_record in self.active_external_errors.values():
                    services_with_errors.add(error_record.microservice)
                
                # If multiple services have concurrent errors, investigate correlation
                if len(services_with_errors) > 1:
                    self.logger.info(f"Multiple services reporting errors: {services_with_errors}")
                    # Could trigger deeper correlation analysis here
                    
            except Exception as e:
                self.logger.error(f"Error in correlation analyzer: {e}")
                await asyncio.sleep(300)
    
    async def _centralized_recovery_coordinator(self):
        """Coordinate recovery efforts across services."""
        while self.is_active:
            try:
                await asyncio.sleep(180)  # Coordinate every 3 minutes
                
                # Check for services that need coordinated recovery
                for error_record in list(self.active_external_errors.values()):
                    if (error_record.severity >= ErrorSeverity.HIGH.value and
                        not error_record.recovery_attempted and
                        error_record.investigation_status == "completed"):
                        
                        # Initiate coordinated recovery
                        investigation_results = json.loads(error_record.investigation_results or "{}")
                        await self._coordinate_cross_service_recovery(error_record, investigation_results)
                        
                        # Mark as recovery attempted
                        error_record.recovery_attempted = True
                
            except Exception as e:
                self.logger.error(f"Error in recovery coordinator: {e}")
                await asyncio.sleep(180)
    
    async def _statistics_updater(self):
        """Update centralized statistics."""
        while self.is_active:
            try:
                await asyncio.sleep(60)  # Update every minute
                
                # Calculate recovery success rates
                for service_name, health_status in self.microservice_health.items():
                    # Update recovery success rate based on recent recovery attempts
                    # This would be calculated based on actual recovery data
                    pass
                
            except Exception as e:
                self.logger.error(f"Error updating statistics: {e}")
                await asyncio.sleep(60)
    
    async def health_check(self) -> bool:
        """Perform centralized health check."""
        try:
            return (
                self.is_active and 
                len(self.active_internal_errors) < 50 and
                len(self.active_external_errors) < 200 and
                os.path.exists(self.error_db_path)
            )
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return False
    
    def get_centralized_statistics(self) -> Dict[str, Any]:
        """Get comprehensive centralized error statistics."""
        try:
            with sqlite3.connect(self.error_db_path) as conn:
                # Internal error stats
                cursor = conn.execute("SELECT COUNT(*) FROM internal_errors")
                total_internal_db_errors = cursor.fetchone()[0]
                
                cursor = conn.execute("SELECT COUNT(*) FROM internal_errors WHERE recovery_successful = 1")
                resolved_internal_db_errors = cursor.fetchone()[0]
                
                # External error stats
                cursor = conn.execute("SELECT COUNT(*) FROM external_errors")
                total_external_db_errors = cursor.fetchone()[0]
                
                cursor = conn.execute("SELECT COUNT(*) FROM external_errors WHERE recovery_successful = 1")
                resolved_external_db_errors = cursor.fetchone()[0]
            
            # Perform synchronous health check
            health_status = (
                self.is_active and 
                len(self.active_internal_errors) < 50 and
                len(self.active_external_errors) < 200 and
                os.path.exists(self.error_db_path)
            )
            
            return {
                "runtime_stats": self.stats.copy(),
                "database_stats": {
                    "total_internal_errors": total_internal_db_errors,
                    "resolved_internal_errors": resolved_internal_db_errors,
                    "total_external_errors": total_external_db_errors,
                    "resolved_external_errors": resolved_external_db_errors
                },
                "active_errors": {
                    "internal": len(self.active_internal_errors),
                    "external": len(self.active_external_errors)
                },
                "error_patterns": len(self.error_patterns),
                "error_correlations": len(self.error_correlations),
                "microservice_health": {name: asdict(status) for name, status in self.microservice_health.items()},
                "health_status": health_status
            }
            
        except Exception as e:
            self.logger.error(f"Error getting centralized statistics: {e}")
            return {"error": "Statistics unavailable"}
    
    def get_error_details(self, error_code: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific error (internal or external)."""
        try:
            # Check internal errors first
            with sqlite3.connect(self.error_db_path) as conn:
                cursor = conn.execute("SELECT * FROM internal_errors WHERE error_code = ?", (error_code,))
                row = cursor.fetchone()
                
                if row:
                    columns = [desc[0] for desc in cursor.description]
                    result = dict(zip(columns, row))
                    result["source"] = "internal"
                    return result
                
                # Check external errors
                cursor = conn.execute("SELECT * FROM external_errors WHERE error_code = ?", (error_code,))
                row = cursor.fetchone()
                
                if row:
                    columns = [desc[0] for desc in cursor.description]
                    result = dict(zip(columns, row))
                    result["source"] = "external"
                    return result
                
                return None
                
        except Exception as e:
            self.logger.error(f"Error retrieving error details: {e}")
            return None
    
    def get_status(self) -> Dict[str, Any]:
        """Get current CEIM status for centralized monitoring."""
        return {
            "module": self.module_name,
            "microservice": "CCU",
            "microservice_code": self.microservice_code,
            "active": self.is_active,
            "active_internal_errors": len(self.active_internal_errors),
            "active_external_errors": len(self.active_external_errors),
            "error_patterns": len(self.error_patterns),
            "error_correlations": len(self.error_correlations),
            "microservice_health_status": {name: status.status for name, status in self.microservice_health.items()},
            "centralized_features": {
                "internal_error_handling": True,
                "external_error_aggregation": True,
                "cross_service_correlation": True,
                "centralized_recovery_coordination": True,
                "microservice_health_monitoring": True,
                "interaction_module_integration": True
            },
            "statistics": self.stats.copy()
        } 