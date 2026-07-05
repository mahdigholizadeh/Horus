"""
Central Test Management Module (CTMM)

This module provides a comprehensive testing framework for the CCU and all
microservices. It manages test suites, executes automated tests, performs
regression testing, and generates detailed test reports.

Key Responsibilities:
- Manage test suites for all microservices
- Execute automated tests on startup and on-demand
- Perform regression testing for system changes
- Generate comprehensive test reports
- Monitor test coverage and quality metrics
- Coordinate integration testing across services
- Manage test data and fixtures
- Provide test result analytics and trends
"""

import asyncio
import logging
import json
import sqlite3
import subprocess
import sys
import os
import importlib
import traceback
from typing import Dict, Any, List, Optional, Callable, Tuple, Union
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import threading
import concurrent.futures
import unittest
import pytest

# Optional import for coverage - test environment may not have it installed
try:
    import coverage
    COVERAGE_AVAILABLE = True
except ImportError:
    coverage = None
    COVERAGE_AVAILABLE = False


class TestStatus(Enum):
    """Test execution status."""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"
    TIMEOUT = "timeout"


class TestType(Enum):
    """Test type enumeration."""
    UNIT = "unit"
    INTEGRATION = "integration"
    SYSTEM = "system"
    REGRESSION = "regression"
    PERFORMANCE = "performance"
    SECURITY = "security"
    STRESS = "stress"
    SMOKE = "smoke"


class TestPriority(Enum):
    """Test priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class TestCase:
    """Test case information."""
    test_id: str
    name: str
    description: str
    test_type: TestType
    priority: TestPriority
    module: str
    service: str
    file_path: str
    function_name: str
    tags: List[str]
    timeout: int = 300
    dependencies: List[str] = None
    setup_required: bool = False
    teardown_required: bool = False
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []


@dataclass
class TestResult:
    """Test result information."""
    test_id: str
    execution_id: str
    status: TestStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    duration: float = 0.0
    output: str = ""
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None
    coverage_data: Optional[Dict[str, Any]] = None
    details: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.details is None:
            self.details = {}


@dataclass
class TestSuite:
    """Test suite information."""
    suite_id: str
    name: str
    description: str
    test_cases: List[str]
    execution_order: List[str]
    setup_scripts: List[str]
    teardown_scripts: List[str]
    parallel_execution: bool = False
    max_workers: int = 4
    timeout: int = 1800
    
    def __post_init__(self):
        if not self.execution_order:
            self.execution_order = self.test_cases.copy()


@dataclass
class TestExecution:
    """Test execution session."""
    execution_id: str
    suite_id: str
    status: TestStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    skipped_tests: int = 0
    error_tests: int = 0
    coverage_percentage: float = 0.0
    results: List[TestResult] = None
    
    def __post_init__(self):
        if self.results is None:
            self.results = []


class CentralTestManagementModule:
    """
    Central Test Management Module (CTMM)
    
    Manages comprehensive testing framework for all microservices.
    """
    
    def __init__(self):
        """Initialize the CTMM module."""
        self.logger = logging.getLogger(__name__)
        
        # Database setup
        self.db_path = Path("ctmm_tests.db")
        self.init_database()
        
        # Test configuration
        self.test_suite_path = Path("tests")
        self.test_suite_path.mkdir(exist_ok=True)
        self.test_timeout = 300
        self.auto_test_on_startup = True
        self.coverage_threshold = 80.0
        
        # Test registry
        self.test_cases: Dict[str, TestCase] = {}
        self.test_suites: Dict[str, TestSuite] = {}
        self.test_executions: Dict[str, TestExecution] = {}
        
        # Test execution
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)
        self.running_tests: Dict[str, asyncio.Task] = {}
        
        # Coverage tracking (optional)
        self.coverage_instance = coverage.Coverage() if COVERAGE_AVAILABLE else None
        
        # Callbacks
        self.test_callbacks = []
        self.suite_callbacks = []
        
        # Statistics
        self.stats = {
            "total_test_cases": 0,
            "total_test_suites": 0,
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "overall_success_rate": 0.0,
            "average_execution_time": 0.0,
            "coverage_percentage": 0.0,
            "last_execution": None
        }
        
        # Default test suites
        self._create_default_test_suites()
        
        # Load existing test cases
        self._discover_test_cases()
        
        # Register additional test cases (34-40)
        self._register_additional_test_cases()
        
        self.logger.info("CTMM module initialized successfully")
    
    def init_database(self):
        """Initialize the SQLite database for test tracking."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Test cases table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS test_cases (
                        test_id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        description TEXT,
                        test_type TEXT NOT NULL,
                        priority TEXT NOT NULL,
                        module TEXT NOT NULL,
                        service TEXT NOT NULL,
                        file_path TEXT NOT NULL,
                        function_name TEXT NOT NULL,
                        tags TEXT,
                        timeout INTEGER DEFAULT 300,
                        dependencies TEXT,
                        setup_required INTEGER DEFAULT 0,
                        teardown_required INTEGER DEFAULT 0
                    )
                """)
                
                # Test suites table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS test_suites (
                        suite_id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        description TEXT,
                        test_cases TEXT NOT NULL,
                        execution_order TEXT NOT NULL,
                        setup_scripts TEXT,
                        teardown_scripts TEXT,
                        parallel_execution INTEGER DEFAULT 0,
                        max_workers INTEGER DEFAULT 4,
                        timeout INTEGER DEFAULT 1800
                    )
                """)
                
                # Test executions table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS test_executions (
                        execution_id TEXT PRIMARY KEY,
                        suite_id TEXT NOT NULL,
                        status TEXT NOT NULL,
                        start_time TIMESTAMP NOT NULL,
                        end_time TIMESTAMP,
                        total_tests INTEGER DEFAULT 0,
                        passed_tests INTEGER DEFAULT 0,
                        failed_tests INTEGER DEFAULT 0,
                        skipped_tests INTEGER DEFAULT 0,
                        error_tests INTEGER DEFAULT 0,
                        coverage_percentage REAL DEFAULT 0.0,
                        FOREIGN KEY (suite_id) REFERENCES test_suites (suite_id)
                    )
                """)
                
                # Test results table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS test_results (
                        result_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        test_id TEXT NOT NULL,
                        execution_id TEXT NOT NULL,
                        status TEXT NOT NULL,
                        start_time TIMESTAMP NOT NULL,
                        end_time TIMESTAMP,
                        duration REAL DEFAULT 0.0,
                        output TEXT,
                        error_message TEXT,
                        stack_trace TEXT,
                        coverage_data TEXT,
                        details TEXT,
                        FOREIGN KEY (test_id) REFERENCES test_cases (test_id),
                        FOREIGN KEY (execution_id) REFERENCES test_executions (execution_id)
                    )
                """)
                
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Failed to initialize database: {e}")
            raise
    
    def _create_default_test_suites(self):
        """Create default test suites."""
        # Smoke test suite
        smoke_suite = TestSuite(
            suite_id="smoke_tests",
            name="Smoke Tests",
            description="Basic smoke tests for all microservices",
            test_cases=[],
            execution_order=[],
            setup_scripts=[],
            teardown_scripts=[],
            parallel_execution=True,
            max_workers=2,
            timeout=600
        )
        self.test_suites["smoke_tests"] = smoke_suite
        
        # Integration test suite
        integration_suite = TestSuite(
            suite_id="integration_tests",
            name="Integration Tests",
            description="Integration tests for microservice interactions",
            test_cases=[],
            execution_order=[],
            setup_scripts=[],
            teardown_scripts=[],
            parallel_execution=False,
            max_workers=1,
            timeout=1800
        )
        self.test_suites["integration_tests"] = integration_suite
        
        # Regression test suite
        regression_suite = TestSuite(
            suite_id="regression_tests",
            name="Regression Tests",
            description="Regression tests for system stability",
            test_cases=[],
            execution_order=[],
            setup_scripts=[],
            teardown_scripts=[],
            parallel_execution=True,
            max_workers=4,
            timeout=3600
        )
        self.test_suites["regression_tests"] = regression_suite
        
        self.logger.info("Default test suites created")
    
    def _discover_test_cases(self):
        """Discover test cases from test files."""
        try:
            # Discover test files
            test_files = []
            for pattern in ["test_*.py", "*_test.py"]:
                test_files.extend(self.test_suite_path.rglob(pattern))
            
            # Process each test file
            for test_file in test_files:
                self._process_test_file(test_file)
            
            self.logger.info(f"Discovered {len(self.test_cases)} test cases")
            
        except Exception as e:
            self.logger.error(f"Failed to discover test cases: {e}")
    
    def _register_additional_test_cases(self):
        """Register additional test cases (21-40) for comprehensive testing."""
        additional_tests = [
            # Integration & Workflow Tests (21-33)
            {
                "test_id": "test_t00000021",
                "name": "CCU Complete WebSocket Startup Workflow",
                "description": "Test complete CCU startup workflow with three-phase WebSocket orchestration",
                "test_type": TestType.INTEGRATION,
                "priority": TestPriority.CRITICAL,
                "module": "SEM",
                "service": "CCU",
                "tags": ["websocket", "startup", "integration", "workflow"]
            },
            {
                "test_id": "test_t00000022",
                "name": "End-to-End WebSocket Request Processing Workflow",
                "description": "Test complete request processing through WebSocket communication from RLA to OCM",
                "test_type": TestType.INTEGRATION,
                "priority": TestPriority.CRITICAL,
                "module": "RTM",
                "service": "CCU", 
                "tags": ["websocket", "request", "workflow", "e2e"]
            },
            {
                "test_id": "test_t00000023",
                "name": "Multi-Service Health Monitoring Integration",
                "description": "Test integrated health monitoring across all dependent services",
                "test_type": TestType.INTEGRATION,
                "priority": TestPriority.HIGH,
                "module": "MSMM",
                "service": "CCU",
                "tags": ["health", "monitoring", "integration", "services"]
            },
            {
                "test_id": "test_t00000024",
                "name": "Configuration Management Integration",
                "description": "Test integrated configuration management across all services",
                "test_type": TestType.INTEGRATION,
                "priority": TestPriority.HIGH,
                "module": "SMM",
                "service": "CCU",
                "tags": ["configuration", "management", "integration", "services"]
            },
            {
                "test_id": "test_t00000025",
                "name": "Error Management Integration",
                "description": "Test integrated error management across all services",
                "test_type": TestType.INTEGRATION,
                "priority": TestPriority.HIGH,
                "module": "CEIM",
                "service": "CCU",
                "tags": ["error", "management", "integration", "recovery"]
            },
            {
                "test_id": "test_t00000026",
                "name": "SEM Restart Workflow with Request Blocking",
                "description": "Test SEM restart workflow with request gateway blocking",
                "test_type": TestType.INTEGRATION,
                "priority": TestPriority.HIGH,
                "module": "SEM",
                "service": "CCU",
                "tags": ["restart", "workflow", "blocking", "gateway"]
            },
            {
                "test_id": "test_t00000027",
                "name": "Resource Monitoring and Backpressure Workflow",
                "description": "Test integrated resource monitoring with backpressure management",
                "test_type": TestType.INTEGRATION,
                "priority": TestPriority.MEDIUM,
                "module": "SRMM",
                "service": "CCU",
                "tags": ["resources", "backpressure", "monitoring", "workflow"]
            },
            {
                "test_id": "test_t00000028",
                "name": "Certificate Management and Distribution Workflow",
                "description": "Test certificate management and distribution to all services",
                "test_type": TestType.INTEGRATION,
                "priority": TestPriority.MEDIUM,
                "module": "PMM",
                "service": "CCU",
                "tags": ["certificates", "distribution", "security", "management"]
            },
            {
                "test_id": "test_t00000029",
                "name": "API Key Security and Distribution Workflow",
                "description": "Test secure API key management and distribution",
                "test_type": TestType.INTEGRATION,
                "priority": TestPriority.MEDIUM,
                "module": "PMM",
                "service": "CCU",
                "tags": ["api_keys", "security", "distribution", "management"]
            },
            {
                "test_id": "test_t00000030",
                "name": "Database Backup and Recovery Workflow",
                "description": "Test automated database backup and recovery procedures",
                "test_type": TestType.INTEGRATION,
                "priority": TestPriority.MEDIUM,
                "module": "PMM",
                "service": "CCU",
                "tags": ["database", "backup", "recovery", "automation"]
            },
            {
                "test_id": "test_t00000031",
                "name": "Concurrent Request Processing Stress Test",
                "description": "Test CCU performance with maximum concurrent requests (10)",
                "test_type": TestType.STRESS,
                "priority": TestPriority.HIGH,
                "module": "RTM",
                "service": "CCU",
                "tags": ["stress", "concurrent", "performance", "requests"]
            },
            {
                "test_id": "test_t00000032",
                "name": "SEM Startup Performance Test",
                "description": "Test SEM pilot checklist performance under various conditions",
                "test_type": TestType.PERFORMANCE,
                "priority": TestPriority.MEDIUM,
                "module": "SEM",
                "service": "CCU",
                "tags": ["performance", "startup", "pilot", "checklist"]
            },
            {
                "test_id": "test_t00000033",
                "name": "Resource Monitoring Performance Test",
                "description": "Test resource monitoring performance under high load",
                "test_type": TestType.PERFORMANCE,
                "priority": TestPriority.MEDIUM,
                "module": "SRMM",
                "service": "CCU",
                "tags": ["performance", "monitoring", "resources", "load"]
            },
            
            # Advanced Integration & System Tests (34-40)
            {
                "test_id": "test_t00000034",
                "name": "Dashboard Performance and Scalability Test",
                "description": "Test web dashboard performance under high user load",
                "test_type": TestType.PERFORMANCE,
                "priority": TestPriority.HIGH,
                "module": "GMM",
                "service": "CCU",
                "tags": ["performance", "dashboard", "websocket", "scalability"]
            },
            {
                "test_id": "test_t00000035",
                "name": "WebSocket Communication Resilience and Recovery Test",
                "description": "Test WebSocket communication resilience and automatic recovery",
                "test_type": TestType.INTEGRATION,
                "priority": TestPriority.CRITICAL,
                "module": "Interaction_Modules",
                "service": "CCU",
                "tags": ["websocket", "resilience", "recovery", "network"]
            },
            {
                "test_id": "test_t00000036",
                "name": "Service Failure Recovery Integration Test",
                "description": "Test integrated recovery from service failures",
                "test_type": TestType.INTEGRATION,
                "priority": TestPriority.CRITICAL,
                "module": "MSMM",
                "service": "CCU",
                "tags": ["recovery", "failure", "integration", "monitoring"]
            },
            {
                "test_id": "test_t00000037",
                "name": "Configuration Change and Rollback Test",
                "description": "Test configuration change management with rollback capabilities",
                "test_type": TestType.INTEGRATION,
                "priority": TestPriority.HIGH,
                "module": "SMM",
                "service": "CCU",
                "tags": ["configuration", "rollback", "management", "validation"]
            },
            {
                "test_id": "test_t00000038",
                "name": "Network Communication Resilience Test",
                "description": "Test network communication resilience and recovery",
                "test_type": TestType.INTEGRATION,
                "priority": TestPriority.HIGH,
                "module": "Network_Layer",
                "service": "CCU",
                "tags": ["network", "resilience", "timeout", "recovery"]
            },
            {
                "test_id": "test_t00000039",
                "name": "Data Integrity and Consistency Test",
                "description": "Test data integrity and consistency across system operations",
                "test_type": TestType.INTEGRATION,
                "priority": TestPriority.CRITICAL,
                "module": "Data_Management",
                "service": "CCU",
                "tags": ["data", "integrity", "consistency", "persistence"]
            },
            {
                "test_id": "test_t00000040",
                "name": "End-to-End System Validation Test",
                "description": "Comprehensive end-to-end system validation",
                "test_type": TestType.SYSTEM,
                "priority": TestPriority.CRITICAL,
                "module": "System_Integration",
                "service": "CCU",
                "tags": ["e2e", "system", "validation", "comprehensive"]
            }
        ]
        
        try:
            for test_info in additional_tests:
                test_case = TestCase(
                    test_id=test_info["test_id"],
                    name=test_info["name"],
                    description=test_info["description"],
                    test_type=test_info["test_type"],
                    priority=test_info["priority"],
                    module=test_info["module"],
                    service=test_info["service"],
                    file_path=f"{test_info['test_id']}.py",
                    function_name=test_info["test_id"],
                    tags=test_info["tags"],
                    timeout=600  # 10 minutes for comprehensive tests
                )
                
                self.test_cases[test_info["test_id"]] = test_case
                self.stats["total_test_cases"] += 1
                
                # Add to appropriate test suites
                if test_info["test_type"] == TestType.INTEGRATION:
                    self.test_suites["integration_tests"].test_cases.append(test_info["test_id"])
                    self.test_suites["integration_tests"].execution_order.append(test_info["test_id"])
                elif test_info["test_type"] == TestType.SYSTEM:
                    self.test_suites["regression_tests"].test_cases.append(test_info["test_id"])
                    self.test_suites["regression_tests"].execution_order.append(test_info["test_id"])
                elif test_info["test_type"] == TestType.PERFORMANCE:
                    # Create performance test suite if it doesn't exist
                    if "performance_tests" not in self.test_suites:
                        performance_suite = TestSuite(
                            suite_id="performance_tests",
                            name="Performance Tests",
                            description="Performance and scalability tests",
                            test_cases=[],
                            execution_order=[],
                            setup_scripts=[],
                            teardown_scripts=[],
                            parallel_execution=False,
                            max_workers=1,
                            timeout=3600
                        )
                        self.test_suites["performance_tests"] = performance_suite
                    
                    self.test_suites["performance_tests"].test_cases.append(test_info["test_id"])
                    self.test_suites["performance_tests"].execution_order.append(test_info["test_id"])
                
                elif test_info["test_type"] == TestType.STRESS:
                    # Create stress test suite if it doesn't exist
                    if "stress_tests" not in self.test_suites:
                        stress_suite = TestSuite(
                            suite_id="stress_tests",
                            name="Stress Tests",
                            description="Stress and load testing",
                            test_cases=[],
                            execution_order=[],
                            setup_scripts=[],
                            teardown_scripts=[],
                            parallel_execution=False,
                            max_workers=1,
                            timeout=7200  # 2 hours for stress tests
                        )
                        self.test_suites["stress_tests"] = stress_suite
                    
                    self.test_suites["stress_tests"].test_cases.append(test_info["test_id"])
                    self.test_suites["stress_tests"].execution_order.append(test_info["test_id"])
            
            self.logger.info(f"Registered {len(additional_tests)} additional test cases (21-40)")
            
        except Exception as e:
            self.logger.error(f"Failed to register additional test cases: {e}")
    
    def _process_test_file(self, test_file: Path):
        """Process a test file to extract test cases."""
        try:
            # Read the test file
            with open(test_file, 'r') as f:
                content = f.read()
            
            # Simple parsing for test functions
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if line.strip().startswith('def test_') or line.strip().startswith('async def test_'):
                    function_name = line.strip().split('(')[0].replace('def ', '').replace('async def ', '')
                    
                    # Extract test information
                    test_id = f"{test_file.stem}_{function_name}"
                    name = function_name.replace('_', ' ').title()
                    
                    # Determine service and module
                    service = self._determine_service(test_file)
                    module = test_file.stem
                    
                    # Create test case
                    test_case = TestCase(
                        test_id=test_id,
                        name=name,
                        description=f"Test case: {name}",
                        test_type=TestType.UNIT,
                        priority=TestPriority.MEDIUM,
                        module=module,
                        service=service,
                        file_path=str(test_file),
                        function_name=function_name,
                        tags=[]
                    )
                    
                    self.test_cases[test_id] = test_case
                    self.stats["total_test_cases"] += 1
            
        except Exception as e:
            self.logger.error(f"Failed to process test file {test_file}: {e}")
    
    def _determine_service(self, test_file: Path) -> str:
        """Determine which service a test file belongs to."""
        path_parts = test_file.parts
        
        # Check for service indicators in path
        if "ccu" in path_parts:
            return "CCU"
        elif "rla" in path_parts:
            return "RLA"
        elif "tpp" in path_parts:
            return "TPP"
        elif "rcm" in path_parts:
            return "RCM"
        elif "jfa" in path_parts:
            return "JFA"
        elif "td" in path_parts:
            return "TD"
        elif "ocm" in path_parts:
            return "OCM"
        else:
            return "UNKNOWN"
    
    def register_test_case(self, test_case: TestCase):
        """Register a test case."""
        try:
            self.test_cases[test_case.test_id] = test_case
            
            # Persist to database
            self._persist_test_case(test_case)
            
            self.stats["total_test_cases"] += 1
            
            self.logger.info(f"Registered test case: {test_case.test_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to register test case {test_case.test_id}: {e}")
            raise
    
    def register_test_suite(self, test_suite: TestSuite):
        """Register a test suite."""
        try:
            self.test_suites[test_suite.suite_id] = test_suite
            
            # Persist to database
            self._persist_test_suite(test_suite)
            
            self.stats["total_test_suites"] += 1
            
            self.logger.info(f"Registered test suite: {test_suite.suite_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to register test suite {test_suite.suite_id}: {e}")
            raise
    
    async def execute_test_suite(self, suite_id: str) -> str:
        """Execute a test suite."""
        try:
            if suite_id not in self.test_suites:
                raise ValueError(f"Test suite not found: {suite_id}")
            
            suite = self.test_suites[suite_id]
            execution_id = self._generate_execution_id()
            
            # Create execution record
            execution = TestExecution(
                execution_id=execution_id,
                suite_id=suite_id,
                status=TestStatus.PENDING,
                start_time=datetime.now(),
                total_tests=len(suite.test_cases)
            )
            
            self.test_executions[execution_id] = execution
            
            # Start execution
            execution.status = TestStatus.RUNNING
            execution_task = asyncio.create_task(self._execute_suite(execution))
            self.running_tests[execution_id] = execution_task
            
            # Wait for completion
            await execution_task
            
            # Remove from running tests
            if execution_id in self.running_tests:
                del self.running_tests[execution_id]
            
            return execution_id
            
        except Exception as e:
            self.logger.error(f"Failed to execute test suite {suite_id}: {e}")
            raise
    
    async def _execute_suite(self, execution: TestExecution):
        """Execute a test suite."""
        try:
            suite = self.test_suites[execution.suite_id]
            
            # Start coverage tracking (if available)
            if self.coverage_instance:
                self.coverage_instance.start()
            
            # Execute setup scripts
            for setup_script in suite.setup_scripts:
                await self._execute_script(setup_script)
            
            # Execute tests
            if suite.parallel_execution:
                await self._execute_tests_parallel(execution, suite)
            else:
                await self._execute_tests_sequential(execution, suite)
            
            # Execute teardown scripts
            for teardown_script in suite.teardown_scripts:
                await self._execute_script(teardown_script)
            
            # Stop coverage tracking (if available)
            if self.coverage_instance:
                self.coverage_instance.stop()
                self.coverage_instance.save()
                
                # Calculate coverage
                coverage_data = self.coverage_instance.get_data()
                execution.coverage_percentage = self._calculate_coverage(coverage_data)
            else:
                # No coverage tracking available
                execution.coverage_percentage = 0.0
            
            # Update execution status
            execution.end_time = datetime.now()
            execution.status = TestStatus.PASSED if execution.failed_tests == 0 else TestStatus.FAILED
            
            # Update statistics
            self._update_execution_statistics(execution)
            
            # Persist execution
            await self._persist_execution(execution)
            
            # Notify callbacks
            for callback in self.suite_callbacks:
                try:
                    await callback(execution)
                except Exception as e:
                    self.logger.error(f"Suite callback failed: {e}")
            
            self.logger.info(f"Test suite execution completed: {execution.execution_id}")
            
        except Exception as e:
            self.logger.error(f"Test suite execution failed: {e}")
            execution.status = TestStatus.ERROR
            execution.end_time = datetime.now()
            await self._persist_execution(execution)
    
    async def _execute_tests_parallel(self, execution: TestExecution, suite: TestSuite):
        """Execute tests in parallel."""
        try:
            # Create semaphore for controlling concurrency
            semaphore = asyncio.Semaphore(suite.max_workers)
            
            # Create tasks for all tests
            tasks = []
            for test_id in suite.execution_order:
                if test_id in self.test_cases:
                    task = asyncio.create_task(
                        self._execute_test_with_semaphore(semaphore, test_id, execution)
                    )
                    tasks.append(task)
            
            # Wait for all tests to complete
            await asyncio.gather(*tasks, return_exceptions=True)
            
        except Exception as e:
            self.logger.error(f"Parallel test execution failed: {e}")
            raise
    
    async def _execute_tests_sequential(self, execution: TestExecution, suite: TestSuite):
        """Execute tests sequentially."""
        try:
            for test_id in suite.execution_order:
                if test_id in self.test_cases:
                    await self._execute_test(test_id, execution)
                    
        except Exception as e:
            self.logger.error(f"Sequential test execution failed: {e}")
            raise
    
    async def _execute_test_with_semaphore(self, semaphore: asyncio.Semaphore, test_id: str, execution: TestExecution):
        """Execute a test with semaphore control."""
        async with semaphore:
            await self._execute_test(test_id, execution)
    
    async def _execute_test(self, test_id: str, execution: TestExecution):
        """Execute a single test."""
        try:
            test_case = self.test_cases[test_id]
            
            # Create test result
            result = TestResult(
                test_id=test_id,
                execution_id=execution.execution_id,
                status=TestStatus.RUNNING,
                start_time=datetime.now()
            )
            
            execution.results.append(result)
            
            # Execute test in thread pool
            loop = asyncio.get_event_loop()
            
            try:
                # Run test with timeout
                await asyncio.wait_for(
                    loop.run_in_executor(
                        self.executor,
                        self._run_test_case,
                        test_case,
                        result
                    ),
                    timeout=test_case.timeout
                )
                
            except asyncio.TimeoutError:
                result.status = TestStatus.TIMEOUT
                result.error_message = f"Test timed out after {test_case.timeout} seconds"
            
            # Update result
            result.end_time = datetime.now()
            result.duration = (result.end_time - result.start_time).total_seconds()
            
            # Update execution counters
            if result.status == TestStatus.PASSED:
                execution.passed_tests += 1
            elif result.status == TestStatus.FAILED:
                execution.failed_tests += 1
            elif result.status == TestStatus.SKIPPED:
                execution.skipped_tests += 1
            else:
                execution.error_tests += 1
            
            # Persist result
            await self._persist_result(result)
            
            # Notify callbacks
            for callback in self.test_callbacks:
                try:
                    await callback(result)
                except Exception as e:
                    self.logger.error(f"Test callback failed: {e}")
            
        except Exception as e:
            self.logger.error(f"Test execution failed for {test_id}: {e}")
            result.status = TestStatus.ERROR
            result.error_message = str(e)
            result.end_time = datetime.now()
            execution.error_tests += 1
    
    def _run_test_case(self, test_case: TestCase, result: TestResult):
        """Run a test case (executed in thread pool)."""
        try:
            # Import test module
            spec = importlib.util.spec_from_file_location(test_case.module, test_case.file_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Get test function
            test_function = getattr(module, test_case.function_name)
            
            # Capture output
            import io
            import contextlib
            
            output_buffer = io.StringIO()
            
            with contextlib.redirect_stdout(output_buffer), contextlib.redirect_stderr(output_buffer):
                # Execute test function
                if asyncio.iscoroutinefunction(test_function):
                    # Run async test
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        loop.run_until_complete(test_function())
                    finally:
                        loop.close()
                else:
                    # Run sync test
                    test_function()
            
            # Test passed
            result.status = TestStatus.PASSED
            result.output = output_buffer.getvalue()
            
        except unittest.SkipTest:
            result.status = TestStatus.SKIPPED
            result.output = "Test skipped"
            
        except Exception as e:
            result.status = TestStatus.FAILED
            result.error_message = str(e)
            result.stack_trace = traceback.format_exc()
            result.output = f"Test failed: {str(e)}"
    
    async def _execute_script(self, script_path: str):
        """Execute a setup/teardown script."""
        try:
            # Execute script as subprocess
            process = await asyncio.create_subprocess_exec(
                sys.executable, script_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise RuntimeError(f"Script failed: {stderr.decode()}")
            
        except Exception as e:
            self.logger.error(f"Script execution failed: {e}")
            raise
    
    def _calculate_coverage(self, coverage_data) -> float:
        """Calculate code coverage percentage."""
        try:
            if not coverage_data:
                return 0.0
            
            total_lines = 0
            covered_lines = 0
            
            for filename in coverage_data.measured_files():
                lines = coverage_data.lines(filename)
                missing = coverage_data.missing_lines(filename)
                
                if lines:
                    total_lines += len(lines)
                    covered_lines += len(lines) - len(missing)
            
            if total_lines == 0:
                return 0.0
            
            return (covered_lines / total_lines) * 100
            
        except Exception as e:
            self.logger.error(f"Coverage calculation failed: {e}")
            return 0.0
    
    def _update_execution_statistics(self, execution: TestExecution):
        """Update execution statistics."""
        try:
            self.stats["total_executions"] += 1
            
            if execution.status == TestStatus.PASSED:
                self.stats["successful_executions"] += 1
            else:
                self.stats["failed_executions"] += 1
            
            # Update success rate
            if self.stats["total_executions"] > 0:
                self.stats["overall_success_rate"] = (
                    self.stats["successful_executions"] / self.stats["total_executions"]
                ) * 100
            
            # Update average execution time
            if execution.end_time:
                duration = (execution.end_time - execution.start_time).total_seconds()
                if self.stats["average_execution_time"] == 0:
                    self.stats["average_execution_time"] = duration
                else:
                    self.stats["average_execution_time"] = (
                        self.stats["average_execution_time"] + duration
                    ) / 2
            
            # Update coverage
            self.stats["coverage_percentage"] = execution.coverage_percentage
            self.stats["last_execution"] = execution.end_time
            
        except Exception as e:
            self.logger.error(f"Failed to update statistics: {e}")
    
    async def run_smoke_tests(self) -> str:
        """Run smoke tests on startup."""
        try:
            return await self.execute_test_suite("smoke_tests")
            
        except Exception as e:
            self.logger.error(f"Smoke tests failed: {e}")
            raise
    
    async def run_regression_tests(self) -> str:
        """Run regression tests."""
        try:
            return await self.execute_test_suite("regression_tests")
            
        except Exception as e:
            self.logger.error(f"Regression tests failed: {e}")
            raise
    
    async def get_test_results(self, execution_id: str) -> Dict[str, Any]:
        """Get test results for an execution."""
        try:
            if execution_id not in self.test_executions:
                return {}
            
            execution = self.test_executions[execution_id]
            return {
                "execution": asdict(execution),
                "results": [asdict(result) for result in execution.results]
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get test results: {e}")
            return {}
    
    async def get_test_history(self, test_id: Optional[str] = None, days: int = 30) -> List[Dict[str, Any]]:
        """Get test execution history."""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            history = []
            
            for execution in self.test_executions.values():
                if execution.start_time >= cutoff_date:
                    if test_id:
                        # Filter by specific test
                        test_results = [r for r in execution.results if r.test_id == test_id]
                        if test_results:
                            history.extend([asdict(r) for r in test_results])
                    else:
                        # All results
                        history.extend([asdict(r) for r in execution.results])
            
            # Sort by start time (newest first)
            history.sort(key=lambda x: x['start_time'], reverse=True)
            
            return history
            
        except Exception as e:
            self.logger.error(f"Failed to get test history: {e}")
            return []
    
    async def _persist_test_case(self, test_case: TestCase):
        """Persist test case to database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT OR REPLACE INTO test_cases 
                    (test_id, name, description, test_type, priority, module, service, 
                     file_path, function_name, tags, timeout, dependencies, 
                     setup_required, teardown_required)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    test_case.test_id,
                    test_case.name,
                    test_case.description,
                    test_case.test_type.value,
                    test_case.priority.value,
                    test_case.module,
                    test_case.service,
                    test_case.file_path,
                    test_case.function_name,
                    json.dumps(test_case.tags),
                    test_case.timeout,
                    json.dumps(test_case.dependencies),
                    1 if test_case.setup_required else 0,
                    1 if test_case.teardown_required else 0
                ))
                
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Failed to persist test case: {e}")
    
    async def _persist_test_suite(self, test_suite: TestSuite):
        """Persist test suite to database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT OR REPLACE INTO test_suites 
                    (suite_id, name, description, test_cases, execution_order, 
                     setup_scripts, teardown_scripts, parallel_execution, 
                     max_workers, timeout)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    test_suite.suite_id,
                    test_suite.name,
                    test_suite.description,
                    json.dumps(test_suite.test_cases),
                    json.dumps(test_suite.execution_order),
                    json.dumps(test_suite.setup_scripts),
                    json.dumps(test_suite.teardown_scripts),
                    1 if test_suite.parallel_execution else 0,
                    test_suite.max_workers,
                    test_suite.timeout
                ))
                
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Failed to persist test suite: {e}")
    
    async def _persist_execution(self, execution: TestExecution):
        """Persist execution to database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT OR REPLACE INTO test_executions 
                    (execution_id, suite_id, status, start_time, end_time, 
                     total_tests, passed_tests, failed_tests, skipped_tests, 
                     error_tests, coverage_percentage)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    execution.execution_id,
                    execution.suite_id,
                    execution.status.value,
                    execution.start_time.isoformat(),
                    execution.end_time.isoformat() if execution.end_time else None,
                    execution.total_tests,
                    execution.passed_tests,
                    execution.failed_tests,
                    execution.skipped_tests,
                    execution.error_tests,
                    execution.coverage_percentage
                ))
                
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Failed to persist execution: {e}")
    
    async def _persist_result(self, result: TestResult):
        """Persist test result to database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO test_results 
                    (test_id, execution_id, status, start_time, end_time, duration, 
                     output, error_message, stack_trace, coverage_data, details)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    result.test_id,
                    result.execution_id,
                    result.status.value,
                    result.start_time.isoformat(),
                    result.end_time.isoformat() if result.end_time else None,
                    result.duration,
                    result.output,
                    result.error_message,
                    result.stack_trace,
                    json.dumps(result.coverage_data) if result.coverage_data else None,
                    json.dumps(result.details)
                ))
                
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Failed to persist test result: {e}")
    
    def _generate_execution_id(self) -> str:
        """Generate a unique execution ID."""
        import uuid
        return f"exec_{uuid.uuid4().hex[:12]}"
    
    def add_test_callback(self, callback: Callable[[TestResult], None]):
        """Add test completion callback."""
        self.test_callbacks.append(callback)
    
    def add_suite_callback(self, callback: Callable[[TestExecution], None]):
        """Add suite completion callback."""
        self.suite_callbacks.append(callback)
    
    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the CTMM module."""
        return {
            'total_test_cases': len(self.test_cases),
            'total_test_suites': len(self.test_suites),
            'running_tests': len(self.running_tests),
            'auto_test_on_startup': self.auto_test_on_startup,
            'coverage_threshold': self.coverage_threshold,
            'statistics': self.stats.copy()
        }
    
    async def start(self):
        """Start the CTMM module."""
        if self.auto_test_on_startup:
            try:
                await self.run_smoke_tests()
            except Exception as e:
                self.logger.error(f"Startup smoke tests failed: {e}")
        
        self.logger.info("CTMM module started")
    
    async def stop(self):
        """Stop the CTMM module."""
        # Cancel running tests
        for execution_id, task in self.running_tests.items():
            task.cancel()
        
        # Wait for cancellation
        if self.running_tests:
            await asyncio.gather(*self.running_tests.values(), return_exceptions=True)
        
        # Shutdown executor
        self.executor.shutdown(wait=True)
        
        self.logger.info("CTMM module stopped") 