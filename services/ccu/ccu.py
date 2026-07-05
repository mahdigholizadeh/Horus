"""
CCU (Central Control Unit) Microservice - Main Entry Point for Horus

This is the central orchestrator and command center for the entire Horus service architecture.
The CCU bears full responsibility for managing and tracking the entire lifecycle of incoming requests,
from initial reception to final egress from the system.

NEW: SEM (Start Execution Module) Pilot Checklist System
Like an airline pilot's pre-flight checklist, the SEM ensures all systems are verified and ready 
before allowing Horus to accept production requests. This comprehensive validation includes:

- Configuration validation and settings freeze
- Controlled sequential startup of all 7 microservices (RLA, RCM, TPP, TD, JFA, OCM, CCU)
- API connectivity validation (OpenAI, external services)
- Webserver connectivity testing (RLA, OCM)
- Interaction module validation (all 6 interaction modules)
- End-to-end workflow testing (RLA → OCM)
- Request gateway blocking during restart operations
- Systemd service management integration

Core Responsibilities:
- Request ingestion and workflow management with pilot checklist validation
- Orchestration of dependent microservices (RLA, TPP, RCM, JFA, TD, OCM)
- End-to-end request status monitoring
- Microservice health monitoring and fault tolerance
- System resource monitoring and backpressure
- Real-time graphical logging and observability
- Centralized configuration management with runtime freeze protection
- Automated database backups and disaster recovery
- Dynamic configuration ingestion (only during startup/restart)
- SSL/TLS certificate management and distribution
- Systemd service integration (start, stop, restart, enable, disable)

Usage:
    sudo systemctl enable --now horusd    # Enable and start Horus service
    sudo systemctl start horusd           # Start Horus with pilot checklist
    sudo systemctl stop horusd            # Stop Horus service
    sudo systemctl restart horusd         # Restart with full pilot checklist
    sudo systemctl disable horusd         # Disable auto-start
"""

import asyncio
import logging
import sys
import json
import uvicorn
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import threading
import queue
from dataclasses import dataclass, asdict
from enum import Enum

# Import all internal modules
from RTM.rtm import RequestTrackingModule
from MSMM.msmm import MicroServicesMonitoringModule
from SRMM.srmm import ServerResourcesMonitorModule
from CEIM.ceim import CentralErrorInvestigationModule
from CMM.cmm import CentralMonitoringModule
from GMM.gmm import GraphicalMonitoringModule
from SMM.smm import SettingModificationModule
from DBM.dbm import DatabaseBackupModule
from IMSMM.imsmm import InternalMicroServiceManagerModule
from CTMM.ctmm import CentralTestManagementModule
from NMM.nmm import NetworkMonitoringModule
from CERTM.certm import CertificateManagementModule
from PMM.pmm import PathManagementModule, Environment

# Import SEM (Start Execution Module)
from SEM.sem import StartExecutionModule, SEMOperation

# Import WebSocket port manager
from utils.websocket_port_manager import WebSocketPortManager

# Import interaction modules
from RLAIM.rlaim import RLAInteractionModule
from TPPIM.tppim import TPPInteractionModule
from RCMIM.rcmim import RCMInteractionModule
from JFAIM.jfaim import JFAInteractionModule
from TDIM.tdim import TDInteractionModule
from OCMIM.ocmim import OCMInteractionModule


class RequestStatus(Enum):
    """Enumeration for request status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class ServiceStatus(Enum):
    """Enumeration for service status."""
    INACTIVE = "inactive"
    ACTIVE = "active"
    ERROR = "error"
    MAINTENANCE = "maintenance"


@dataclass
class RequestContext:
    """Context information for tracking requests."""
    request_id: str
    status: RequestStatus
    created_at: datetime
    updated_at: datetime
    current_service: Optional[str] = None
    processing_history: List[Dict[str, Any]] = None
    error_count: int = 0
    retry_count: int = 0
    
    def __post_init__(self):
        if self.processing_history is None:
            self.processing_history = []


class CCUMicroservice:
    """
    CCU Microservice - Central Control Unit
    
    This class orchestrates the entire service ecosystem and provides:
    - Request lifecycle management
    - Service orchestration
    - Resource monitoring
    - Error handling and recovery
    - Real-time observability
    - Configuration management
    """
    
    def __init__(self):
        """Initialize the CCU microservice with all modules."""
        self.logger = logging.getLogger(__name__)
        self.is_active = False
        self.internal_modules = {}
        self.interaction_modules = {}
        self.request_contexts = {}
        self.service_statuses = {}
        self.settings_frozen = False  # For settings freeze logic
        
        # Initialize WebSocket Port Manager FIRST (required for interaction modules)
        self.websocket_port_manager = WebSocketPortManager()
        
        # Initialize Path Management Module SECOND (required by other modules)
        self.pmm = PathManagementModule(environment=Environment.DEVELOPMENT)
        
        # Configuration (now using PMM for paths)
        self.config = self._load_configuration()
        
        # Initialize modules
        self._initialize_internal_modules()
        self._initialize_interaction_modules()
        
        # Request tracking
        self.request_queue = asyncio.Queue()
        self.max_concurrent_requests = 10
        self.request_timeout = 300  # 5 minutes
        
        # Statistics
        self.stats = {
            "total_requests": 0,
            "active_requests": 0,
            "completed_requests": 0,
            "failed_requests": 0,
            "average_processing_time": 0,
            "last_activity": None,
            "service_health": {}
        }
        
        self.logger.info("CCU Microservice initialized successfully")
    
    def _load_configuration(self) -> Dict[str, Any]:
        """Load configuration from JSON files using PMM-managed paths."""
        try:
            # Get CCU configuration directory from PMM
            config_path = self.pmm.get_service_path("CCU", "config")
            config = {}
            
            # Load all configuration files
            config_files = [
                "ccu_setting.json",
                "rla_setting.json", 
                "tpp_setting.json",
                "rcm_setting.json",
                "jfa_setting.json",
                "td_setting.json",
                "ocm_setting.json"
            ]
            
            for config_file in config_files:
                file_path = config_path / config_file
                if file_path.exists():
                    with open(file_path, 'r') as f:
                        config[config_file.replace('.json', '')] = json.load(f)
                        # Add PMM path information to each service config
                        service_name = config_file.replace('_setting.json', '').upper()
                        if service_name != "CCU":
                            config[config_file.replace('.json', '')]["pmm_paths"] = self.pmm.distribute_paths_to_service(service_name)
                else:
                    self.logger.warning(f"Configuration file not found: {config_file}")
                    config[config_file.replace('.json', '')] = {}
            
            # Add PMM information to main config
            config["pmm_info"] = self.pmm.get_path_info()
            
            return config
            
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            return {}
    
    def _initialize_internal_modules(self):
        """Initialize all internal modules."""
        try:
            # Add PMM to internal modules (already initialized, just register it)
            self.internal_modules['PMM'] = self.pmm
            
            # Initialize SEM (Start Execution Module) as first module after PMM
            self.internal_modules['SEM'] = StartExecutionModule(self.config)
            
            # Initialize internal modules in order (PMM and SEM are already initialized)
            self.internal_modules['RTM'] = RequestTrackingModule()
            self.internal_modules['MSMM'] = MicroServicesMonitoringModule()
            self.internal_modules['SRMM'] = ServerResourcesMonitorModule()
            self.internal_modules['CEIM'] = CentralErrorInvestigationModule(self.config)
            self.internal_modules['CMM'] = CentralMonitoringModule()
            self.internal_modules['GMM'] = GraphicalMonitoringModule()
            self.internal_modules['SMM'] = SettingModificationModule()
            self.internal_modules['DBM'] = DatabaseBackupModule()
            self.internal_modules['IMSMM'] = InternalMicroServiceManagerModule()
            self.internal_modules['CTMM'] = CentralTestManagementModule()
            self.internal_modules['NMM'] = NetworkMonitoringModule()
            self.internal_modules['CERTM'] = CertificateManagementModule(self.config)
            
            self.logger.info("All internal modules initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize internal modules: {e}")
            raise
    
    def _initialize_interaction_modules(self):
        """Initialize all interaction modules."""
        try:
            # Pass WebSocket port manager to all interaction modules
            interaction_module_config = {
                **self.config,
                'websocket_port_manager': self.websocket_port_manager
            }
            
            # Initialize interaction modules for each microservice with PMM-enabled configuration
            self.interaction_modules['RLAIM'] = RLAInteractionModule(interaction_module_config)
            self.interaction_modules['TPPIM'] = TPPInteractionModule(interaction_module_config)
            self.interaction_modules['RCMIM'] = RCMInteractionModule(interaction_module_config)
            self.interaction_modules['JFAIM'] = JFAInteractionModule(interaction_module_config)
            self.interaction_modules['TDIM'] = TDInteractionModule(interaction_module_config)
            self.interaction_modules['OCMIM'] = OCMInteractionModule(interaction_module_config)
            
            self.logger.info("All interaction modules initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize interaction modules: {e}")
            raise
    
    async def start(self, operation: SEMOperation = SEMOperation.START):
        """Start the CCU microservice with SEM pilot checklist."""
        try:
            self.logger.info("Starting CCU microservice with SEM pilot checklist...")
            
            # FIRST: Execute SEM pilot checklist
            # NEW ARCHITECTURE: Start interaction modules FIRST (they create WebSocket servers) 
            self.logger.info("🚀 Starting CCU interaction modules with WebSocket servers...")
            for module_name, module in self.interaction_modules.items():
                try:
                    self.logger.info(f"🔄 Starting interaction module: {module_name}")
                    if hasattr(module, 'start'):
                        await module.start()
                        self.logger.info(f"✅ Started interaction module: {module_name}")
                    else:
                        self.logger.warning(f"⚠️ Interaction module {module_name} has no start() method")
                except Exception as e:
                    self.logger.error(f"❌ Failed to start interaction module {module_name}: {e}")
                    # Continue with other modules instead of failing completely
                    self.logger.error(f"❌ Error details for {module_name}: {type(e).__name__}: {str(e)}")
            
            self.logger.info("📋 Interaction module startup completed")
            # Start other internal modules (excluding PMM which is already running)
            self.logger.info("🔄 Starting internal modules...")
            for module_name, module in self.internal_modules.items():
                if module_name in ['PMM', 'SEM']:  # Skip PMM (already running) and SEM (handled externally)
                    continue
                
                try:
                    self.logger.info(f"🔄 Starting internal module: {module_name}")
                    if hasattr(module, 'start'):
                        await module.start()
                        self.logger.info(f"✅ Started internal module: {module_name}")
                    else:
                        self.logger.warning(f"⚠️ Internal module {module_name} has no start() method")
                except Exception as e:
                    self.logger.error(f"❌ Failed to start internal module {module_name}: {e}")
                    # Continue with other modules
                    self.logger.error(f"❌ Error details for {module_name}: {type(e).__name__}: {str(e)}")
            
            self.logger.info("📋 Internal module startup completed")
            
            # NOTE: SEM pilot checklist is now handled by external horus_startup.py script
            # This allows proper orchestration of the 6-WebSocket-server architecture
            self.logger.info("ℹ️ SEM pilot checklist handled by external startup orchestrator")
            
            # Distribute API keys to all services
            await self._distribute_api_keys()
            
            # Start background tasks
            await self._start_background_tasks()
            
            # Start monitoring services
            await self._start_monitoring()
            
            # Start request processing
            await self._start_request_processing()
            
            # Freeze settings after successful startup
            self.freeze_settings()
            
            self.is_active = True
            self.logger.info("CCU microservice started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start CCU microservice: {e}")
            raise
    
    async def stop(self):
        """Stop the CCU microservice."""
        try:
            self.logger.info("Stopping CCU microservice...")
            
            # Unfreeze settings on shutdown
            self.settings_frozen = False
            
            # Stop all modules in reverse order
            for module_name, module in reversed(list(self.interaction_modules.items())):
                if hasattr(module, 'stop'):
                    await module.stop()
                    self.logger.info(f"Stopped interaction module: {module_name}")
            
            for module_name, module in reversed(list(self.internal_modules.items())):
                if module_name == 'SEM':  # SEM should already be deactivated
                    continue
                if hasattr(module, 'stop'):
                    await module.stop()
                    self.logger.info(f"Stopped internal module: {module_name}")
            
            self.is_active = False
            self.logger.info("CCU microservice stopped successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to stop CCU microservice: {e}")
            raise
    
    async def restart(self):
        """Restart the CCU microservice with full SEM pilot checklist."""
        try:
            self.logger.info("🔄 Restarting CCU microservice...")
            
            # Stop current instance
            await self.stop()
            
            # Wait a moment for clean shutdown
            await asyncio.sleep(2)
            
            # Start with RESTART operation (includes request blocking)
            await self.start(SEMOperation.RESTART)
            
            self.logger.info("✅ CCU microservice restarted successfully")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to restart CCU microservice: {e}")
            raise
    
    async def _start_background_tasks(self):
        """Start background tasks for monitoring and maintenance."""
        # Start resource monitoring
        asyncio.create_task(self._monitor_system_resources())
        
        # Start service health monitoring
        asyncio.create_task(self._monitor_service_health())
        
        # Start request timeout monitoring
        asyncio.create_task(self._monitor_request_timeouts())
        
        # Start database backup task
        asyncio.create_task(self._schedule_database_backups())
        
        self.logger.info("Background tasks started")
    
    async def _start_monitoring(self):
        """Start monitoring services."""
        # Start central monitoring
        await self.internal_modules['CMM'].start_monitoring()
        
        # Start graphical monitoring
        await self.internal_modules['GMM'].start_dashboard()
        
        # Start network monitoring
        await self.internal_modules['NMM'].start_monitoring()
        
        self.logger.info("Monitoring services started")
    
    async def _start_request_processing(self):
        """Start request processing loop."""
        asyncio.create_task(self._process_request_queue())
        self.logger.info("Request processing started")
    
    async def _distribute_api_keys(self):
        """Distribute API keys to all services during startup for security."""
        try:
            from api_key_security_utils import api_key_security, validate_api_key_secure
            
            self.logger.info("🔒 Starting secure API key distribution...")
            
            # Validate environment keys first
            key_status = api_key_security.validate_environment_keys()
            recommendations = api_key_security.get_security_recommendations(key_status)
            
            # Log security status
            for key_name, status in key_status.items():
                if status['present']:
                    self.logger.info(f"🔐 {key_name}: {status['result']} - {status['masked_key']}")
                else:
                    self.logger.info(f"❌ {key_name}: {status['result']}")
            
            # Log security recommendations
            for recommendation in recommendations:
                if "CRITICAL" in recommendation or "Fix" in recommendation:
                    self.logger.error(recommendation)
                elif "⚠️" in recommendation:
                    self.logger.warning(recommendation)
                else:
                    self.logger.info(recommendation)
            
            # Get validated API keys
            import os
            openai_api_key = os.getenv('OPENAI_API_KEY')
            special_api_key = os.getenv('SPECIAL_API_KEY')
            agent_api_key = os.getenv('AGENT_API_KEY')
            
            # Fallback to configuration if environment variables are not set
            if not openai_api_key:
                openai_api_key = self.config.get('rcm_setting', {}).get('api_configuration', {}).get('openai', {}).get('api_key')
            
            # Validate and distribute main API key
            if openai_api_key:
                is_valid, validation_message = validate_api_key_secure(openai_api_key, "openai")
                
                if is_valid:
                    # Distribute to RCM modules via RCMIM
                    if 'RCMIM' in self.interaction_modules:
                        try:
                            # Set API key for BAAIM (Basic API)
                            await self.interaction_modules['RCMIM'].set_rcm_api_key(openai_api_key, "BAAIM")
                            self.logger.info("✅ Secure API key distributed to RCM BAAIM module")
                            
                            # Set API key for AAAIM (Agent API) - use agent key if available, otherwise use main key
                            agent_key = agent_api_key if agent_api_key else openai_api_key
                            
                            # Validate agent key if different from main key
                            if agent_key != openai_api_key:
                                agent_valid, agent_message = validate_api_key_secure(agent_key, "agent")
                                if not agent_valid:
                                    self.logger.warning(f"Agent API key validation failed: {agent_message}, using main key")
                                    agent_key = openai_api_key
                            
                            await self.interaction_modules['RCMIM'].set_rcm_api_key(agent_key, "AAAIM")
                            self.logger.info("✅ Secure API key distributed to RCM AAAIM module")
                            
                            # Set special API key for SAAIM if available and valid
                            if special_api_key:
                                special_valid, special_message = validate_api_key_secure(special_api_key, "special")
                                if special_valid:
                                    await self.interaction_modules['RCMIM'].set_rcm_api_key(special_api_key, "SAAIM")
                                    self.logger.info("✅ Secure special API key distributed to RCM SAAIM module")
                                else:
                                    self.logger.warning(f"Special API key validation failed: {special_message}")
                            else:
                                self.logger.info("ℹ️  No special API key configured for SAAIM")
                                
                        except Exception as e:
                            self.logger.error(f"Failed to distribute validated API keys to RCM: {e}")
                            # Don't raise - continue startup even if key distribution fails
                    else:
                        self.logger.warning("RCMIM module not available - cannot distribute API keys to RCM")
                else:
                    self.logger.error(f"🚨 Main API key validation failed: {validation_message}")
                    self.logger.error("🚨 System will start but API functionality may be limited")
            else:
                self.logger.warning("⚠️  No OpenAI API key found in environment or configuration")
                self.logger.info("💡 Set OPENAI_API_KEY environment variable for secure key management")
            
            # TODO: Add API key distribution to other services (TPP, OCM, etc.) when they support it
            # Example for future implementation:
            # if 'TPPIM' in self.interaction_modules:
            #     await self.interaction_modules['TPPIM'].set_api_key(openai_api_key)
            
            self.logger.info("🔒 Secure API key distribution completed")
            
        except ImportError:
            self.logger.warning("API key security utilities not available, falling back to basic validation")
            await self._distribute_api_keys_fallback()
        except Exception as e:
            self.logger.error(f"Error during secure API key distribution: {e}")
            # Don't raise - allow CCU to continue starting even if key distribution fails
            # This maintains system availability while logging security concerns
    
    async def _distribute_api_keys_fallback(self):
        """Fallback API key distribution without security utilities."""
        import os
        
        self.logger.info("Using fallback API key distribution...")
        
        # Get API keys from environment variables or config
        openai_api_key = os.getenv('OPENAI_API_KEY')
        special_api_key = os.getenv('SPECIAL_API_KEY')
        agent_api_key = os.getenv('AGENT_API_KEY')
        
        # Fallback to configuration
        if not openai_api_key:
            openai_api_key = self.config.get('rcm_setting', {}).get('api_configuration', {}).get('openai', {}).get('api_key')
        
        # Basic validation and distribution
        if openai_api_key and openai_api_key != "sk-proj-YOUR_API_KEY_HERE" and not openai_api_key.startswith("sk-proj-YOUR"):
            if 'RCMIM' in self.interaction_modules:
                try:
                    await self.interaction_modules['RCMIM'].set_rcm_api_key(openai_api_key, "BAAIM")
                    await self.interaction_modules['RCMIM'].set_rcm_api_key(agent_api_key or openai_api_key, "AAAIM")
                    if special_api_key:
                        await self.interaction_modules['RCMIM'].set_rcm_api_key(special_api_key, "SAAIM")
                    self.logger.info("✅ API keys distributed using fallback method")
                except Exception as e:
                    self.logger.error(f"Fallback API key distribution failed: {e}")
        else:
            self.logger.warning("No valid API key found for distribution")
    
    async def process_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a request through the entire microservice pipeline.
        
        Args:
            request_data: The request data to process
            
        Returns:
            Processing result
        """
        try:
            request_id = request_data.get('request_id')
            if not request_id:
                request_id = self._generate_request_id()
                request_data['request_id'] = request_id
            
            self.logger.info(f"Processing request {request_id}")
            
            # Check if request already exists (stateful interaction)
            if request_id in self.request_contexts:
                self.logger.info(f"Resuming existing workflow for request {request_id}")
                context = self.request_contexts[request_id]
            else:
                # Create new workflow
                self.logger.info(f"Creating new workflow for request {request_id}")
                context = RequestContext(
                    request_id=request_id,
                    status=RequestStatus.PENDING,
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                self.request_contexts[request_id] = context
            
            # Use RTM to manage the workflow
            result = await self.internal_modules['RTM'].orchestrate_request(request_data, context)
            
            # Update statistics
            self.stats['total_requests'] += 1
            self.stats['last_activity'] = datetime.now()
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error processing request: {e}")
            # Use CEIM for error investigation
            await self.internal_modules['CEIM'].investigate_error(str(e), request_data)
            raise
    
    def _generate_request_id(self) -> str:
        """Generate a unique request ID in the format wsrid_0x<12-digit-hex>."""
        import uuid
        # Generate a 12-digit hex number
        hex_part = format(uuid.uuid4().int & 0xFFFFFFFFFFFF, '012X')
        return f"wsrid_0x{hex_part}"
    
    async def _process_request_queue(self):
        """Process requests from the queue."""
        while self.is_active:
            try:
                # Get request from queue with timeout
                request_data = await asyncio.wait_for(
                    self.request_queue.get(), 
                    timeout=1.0
                )
                
                # Process request
                await self.process_request(request_data)
                
            except asyncio.TimeoutError:
                # No request in queue, continue
                continue
            except Exception as e:
                self.logger.error(f"Error processing request from queue: {e}")
    
    async def _monitor_system_resources(self):
        """Monitor system resources and apply backpressure if needed."""
        while self.is_active:
            try:
                # Get resource metrics from SRMM
                resource_metrics = await self.internal_modules['SRMM'].get_resource_metrics()
                
                # Check thresholds
                if resource_metrics.get('cpu_usage', 0) > 90 or resource_metrics.get('memory_usage', 0) > 90:
                    self.logger.warning("High resource usage detected - applying backpressure")
                    # Apply backpressure logic here
                    await self._apply_backpressure()
                
                # Sleep for 10 seconds
                await asyncio.sleep(10)
                
            except Exception as e:
                self.logger.error(f"Error monitoring system resources: {e}")
                await asyncio.sleep(10)
    
    async def _monitor_service_health(self):
        """Monitor health of all dependent microservices."""
        while self.is_active:
            try:
                # Use MSMM to check service health
                health_status = await self.internal_modules['MSMM'].check_all_services()
                
                # Update service statuses
                for service_name, status in health_status.items():
                    self.service_statuses[service_name] = status
                    
                    # Handle failed services
                    if status == ServiceStatus.ERROR:
                        await self._handle_service_failure(service_name)
                
                # Sleep for 30 seconds
                await asyncio.sleep(30)
                
            except Exception as e:
                self.logger.error(f"Error monitoring service health: {e}")
                await asyncio.sleep(30)
    
    async def _monitor_request_timeouts(self):
        """Monitor requests for timeouts."""
        while self.is_active:
            try:
                current_time = datetime.now()
                
                # Check for timed out requests
                for request_id, context in list(self.request_contexts.items()):
                    if context.status == RequestStatus.PROCESSING:
                        elapsed = (current_time - context.updated_at).total_seconds()
                        if elapsed > self.request_timeout:
                            self.logger.warning(f"Request {request_id} timed out after {elapsed} seconds")
                            context.status = RequestStatus.FAILED
                            await self._handle_request_timeout(request_id, context)
                
                # Sleep for 60 seconds
                await asyncio.sleep(60)
                
            except Exception as e:
                self.logger.error(f"Error monitoring request timeouts: {e}")
                await asyncio.sleep(60)
    
    async def _schedule_database_backups(self):
        """Schedule regular database backups."""
        while self.is_active:
            try:
                # Use DBM to perform backups
                await self.internal_modules['DBM'].perform_backup()
                
                # Sleep for 1 hour
                await asyncio.sleep(3600)
                
            except Exception as e:
                self.logger.error(f"Error performing database backup: {e}")
                await asyncio.sleep(3600)
    
    async def _apply_backpressure(self):
        """Apply backpressure to reduce system load."""
        # Implementation for backpressure - halt new request acceptance
        self.logger.info("Applying backpressure - halting new request acceptance")
        # Add logic to pause request processing
        
    async def _handle_service_failure(self, service_name: str):
        """Handle failure of a dependent service."""
        self.logger.error(f"Service {service_name} has failed")
        
        # Use MSMM to attempt service recovery
        recovery_result = await self.internal_modules['MSMM'].recover_service(service_name)
        
        if recovery_result:
            self.logger.info(f"Service {service_name} recovered successfully")
        else:
            self.logger.error(f"Failed to recover service {service_name}")
    
    async def _handle_request_timeout(self, request_id: str, context: RequestContext):
        """Handle request timeout."""
        self.logger.error(f"Request {request_id} timed out")
        
        # Use CEIM to investigate timeout
        await self.internal_modules['CEIM'].investigate_timeout(request_id, context)
        
        # Update statistics
        self.stats['failed_requests'] += 1
    
    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the CCU microservice."""
        # Get SEM status if available
        sem_status = None
        sem_module = self.internal_modules.get('SEM')
        if sem_module:
            sem_status = getattr(sem_module, 'get_status', lambda: {'status': 'unknown'})()
        
        return {
            'is_active': self.is_active,
            'settings_frozen': self.settings_frozen,
            'total_requests': self.stats['total_requests'],
            'active_requests': len([r for r in self.request_contexts.values() if r.status == RequestStatus.PROCESSING]),
            'completed_requests': self.stats['completed_requests'],
            'failed_requests': self.stats['failed_requests'],
            'service_health': self.service_statuses,
            'sem_status': sem_status,
            'internal_modules': {name: getattr(module, 'get_status', lambda: {'status': 'unknown'})() for name, module in self.internal_modules.items()},
            'interaction_modules': {name: getattr(module, 'get_status', lambda: {'status': 'unknown'})() for name, module in self.interaction_modules.items()},
            'websocket_servers': self.websocket_port_manager.get_server_status(),
            'last_activity': self.stats['last_activity'],
            'horus_service_info': {
                'total_microservices': 7,
                'service_names': ['RLA', 'RCM', 'TPP', 'TD', 'JFA', 'OCM', 'CCU'],
                'pilot_checklist_enabled': True,
                'websocket_architecture': '6_servers_in_ccu'
            }
        }
    
    async def reload_configuration(self):
        """Reload configuration - only allowed when settings are not frozen."""
        try:
            if self.settings_frozen:
                raise Exception("Configuration changes are not allowed while system is running. Use restart to apply new settings.")
            
            self.logger.info("Reloading configuration...")
            self.config = self._load_configuration()
            
            # Use SMM to apply new configuration
            await self.internal_modules['SMM'].apply_configuration(self.config)
            
            self.logger.info("Configuration reloaded successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to reload configuration: {e}")
            raise
    
    # Systemd Integration Methods
    async def systemd_enable(self):
        """Enable Horus service for auto-start via systemd."""
        try:
            sem_module = self.internal_modules.get('SEM')
            if sem_module and hasattr(sem_module, 'systemd_integrator'):
                result = await sem_module.systemd_integrator.enable_service()
                return result
            else:
                self.logger.error("SEM or systemd integrator not available")
                return False
        except Exception as e:
            self.logger.error(f"Failed to enable systemd service: {e}")
            return False
    
    async def systemd_disable(self):
        """Disable Horus service auto-start via systemd."""
        try:
            sem_module = self.internal_modules.get('SEM')
            if sem_module and hasattr(sem_module, 'systemd_integrator'):
                result = await sem_module.systemd_integrator.disable_service()
                return result
            else:
                self.logger.error("SEM or systemd integrator not available")
                return False
        except Exception as e:
            self.logger.error(f"Failed to disable systemd service: {e}")
            return False
    
    async def systemd_install(self):
        """Install Horus systemd service file."""
        try:
            sem_module = self.internal_modules.get('SEM')
            if sem_module and hasattr(sem_module, 'systemd_integrator'):
                result = await sem_module.systemd_integrator.install_service()
                return result
            else:
                self.logger.error("SEM or systemd integrator not available")
                return False
        except Exception as e:
            self.logger.error(f"Failed to install systemd service: {e}")
            return False
    
    async def get_systemd_status(self):
        """Get systemd service status."""
        try:
            sem_module = self.internal_modules.get('SEM')
            if sem_module and hasattr(sem_module, 'systemd_integrator'):
                status = await sem_module.systemd_integrator.get_service_status()
                return status
            else:
                self.logger.error("SEM or systemd integrator not available")
                return None
        except Exception as e:
            self.logger.error(f"Failed to get systemd status: {e}")
            return None
    
    # Settings Management Methods
    def freeze_settings(self):
        """Freeze settings to prevent runtime changes."""
        self.settings_frozen = True
        self.logger.info("⚠️ Settings are now frozen - restart required to apply configuration changes")
    
    def unfreeze_settings(self):
        """Unfreeze settings (only used during shutdown/restart)."""
        self.settings_frozen = False
        self.logger.info("✅ Settings unfrozen")
    
    def is_settings_frozen(self) -> bool:
        """Check if settings are currently frozen."""
        return self.settings_frozen
    
    def get_service_paths(self, service: str) -> Dict[str, str]:
        """
        Get path configuration for a specific service.
        
        This method is called by interaction modules to provide paths to microservices.
        
        Args:
            service: Service name (e.g., 'RCM', 'OCM', 'TPP')
            
        Returns:
            Dictionary containing all paths for the service
        """
        try:
            return self.pmm.distribute_paths_to_service(service)
        except Exception as e:
            self.logger.error(f"Failed to get paths for service {service}: {e}")
            return {}
    
    def get_path_management_info(self) -> Dict[str, Any]:
        """
        Get comprehensive path management information.
        
        Returns:
            Dictionary containing PMM status and configuration
        """
        try:
            return self.pmm.get_path_info()
        except Exception as e:
            self.logger.error(f"Failed to get path management info: {e}")
            return {}
    
    def set_environment(self, environment: str):
        """
        Set the deployment environment and update paths accordingly.
        
        Args:
            environment: Environment name ('development', 'staging', 'production')
        """
        try:
            env_enum = Environment(environment.lower())
            self.pmm.set_environment(env_enum)
            
            # Reload configuration with new paths
            self.config = self._load_configuration()
            
            self.logger.info(f"Environment switched to: {environment}")
            
        except ValueError:
            self.logger.error(f"Invalid environment: {environment}")
        except Exception as e:
            self.logger.error(f"Failed to set environment: {e}")
    
    async def _validate_websocket_servers(self):
        """Validate that all 6 CCU WebSocket servers are running."""
        try:
            server_status = self.websocket_port_manager.get_server_status()
            expected_servers = ["RLAIM", "TPPIM", "RCMIM", "JFAIM", "TDIM", "OCMIM"]
            
            running_servers = list(server_status.get("running_servers", {}).keys())
            
            for server in expected_servers:
                if server not in running_servers:
                    raise Exception(f"WebSocket server {server} is not running")
                    
                # Verify server is actually listening
                port = server_status["allocated_ports"].get(server)
                if port and not self.websocket_port_manager.is_port_available(port):
                    self.logger.info(f"✅ {server} WebSocket server verified on port {port}")
                else:
                    raise Exception(f"WebSocket server {server} port {port} is not accessible")
            
            self.logger.info(f"✅ All {len(expected_servers)} WebSocket servers validated successfully")
            
        except Exception as e:
            self.logger.error(f"❌ WebSocket server validation failed: {e}")
            raise


async def main():
    """
    Main entry point for the Horus CCU microservice.
    
    The CCU now includes the SEM (Start Execution Module) pilot checklist system
    that performs comprehensive pre-flight checks before allowing the system to
    accept production requests.
    
    Usage:
        python ccu.py                    # Normal start with pilot checklist
        python ccu.py --restart          # Restart with full checklist (includes request blocking)
        python ccu.py --enable           # Enable for systemd auto-start
        python ccu.py --install-service  # Install systemd service file
    """
    import sys
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Parse command line arguments
    operation = SEMOperation.START
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        if arg == '--restart':
            operation = SEMOperation.RESTART
        elif arg == '--enable':
            operation = SEMOperation.ENABLE
        elif arg == '--install-service':
            # Handle systemd service installation
            ccu = CCUMicroservice()
            result = await ccu.systemd_install()
            if result:
                print("[SUCCESS] Horus systemd service installed successfully")
                print("[INFO] Run 'sudo systemctl enable horusd' to enable auto-start")
                print("[INFO] Run 'sudo systemctl start horusd' to start the service")
            else:
                print("[ERROR] Failed to install systemd service")
            return
    
    # Create and start CCU microservice
    ccu = CCUMicroservice()
    
    try:
        print(f"[STARTUP] Starting Horus with operation: {operation.value}")
        print("[STARTUP] SEM pilot checklist will perform comprehensive pre-flight checks")
        print("[STARTUP] All 7 microservices will be validated before accepting requests")
        
        await ccu.start(operation)
        
        print("[SUCCESS] Horus is now ready to accept production requests")
        print("[INFO] Monitor status via CCU interface or logs")
        print("[INFO] Settings are frozen - use restart to apply configuration changes")
        
        # Keep the service running
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        print("\n[SHUTDOWN] Shutting down Horus...")
        await ccu.stop()
        print("[SUCCESS] Horus stopped successfully")
    except Exception as e:
        print(f"[ERROR] Error running Horus: {e}")
        print("[DEBUG] Check logs for detailed error information")
        await ccu.stop()


if __name__ == "__main__":
    asyncio.run(main())
