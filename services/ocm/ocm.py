"""
OCM (Output Cache Management) Microservice - Main Entry Point

This is the central controller for the OCM microservice, responsible for:
- Initialization and orchestration of all modules
- SSL certificate management and distribution
- WebSocket-based integration with CCU
- Background task management
- Service lifecycle management
- Error handling and recovery
"""

import asyncio
import logging
import json
import sys
import signal
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

# Import all modules
from ECM.ecm import ExternalControlModule
from RMM.rmm import RequestManagementModule
from NMM.nmm import NetworkManagementModule
from DSM.dsm import DataSenderModule
from TDIM.tdim import TDInteractionModule
from RCMIM.rcmim import RCMInteractionModule
from EMM.emm import ErrorManagementModule
from BTM.btm import BackgroundTaskModule
from FAIM.faim import FastAPIIntegrationModule
from MSM.msm import MonitoringSystemModule
from DCM.dcm import DatabaseControlModule
from HRPM.hrpm import HTMLReportProducerModule
from PRFPM.prfpm import PDFReportFormatProducerModule
from OCVM.ocvm import OutputCheckValidityModule
from TMM.tmm import TestManagementModule


class OCMMicroservice:
    """
    OCM Microservice - Central Controller
    
    This class orchestrates all modules and provides the main interface for:
    - Output processing and validation
    - Report generation (HTML, PDF)
    - Secure delivery to web servers
    - SSL certificate management and hot-reload
    - CCU integration and control
    - Service lifecycle management
    """
    
    def __init__(self):
        """Initialize the OCM microservice with all modules."""
        self.logger = logging.getLogger(__name__)
        self.is_active = False
        self.modules = {}
        self.startup_time = None
        
        # Configuration
        self.config = self._load_configuration()
        
        # SSL certificate management
        self.ssl_certificates = {
            'cert_content': '',
            'key_content': '',
            'cert_hash': '',
            'key_hash': '',
            'expires_at': None,
            'updated_at': None
        }
        
        # Service metadata
        self.service_info = {
            'name': 'OCM',
            'version': self.config.get('service', {}).get('version', '1.0.0'),
            'description': 'Output Cache Management Microservice',
            'capabilities': [
                'output_processing',
                'report_generation',
                'secure_delivery',
                'ssl_management',
                'priority_queuing',
                'acknowledgment_protocol'
            ]
        }
        
        # Initialize all modules
        self._initialize_modules()
        
        # Set up signal handlers for graceful shutdown
        self._setup_signal_handlers()
        
        # Statistics
        self.stats = {
            'start_time': None,
            'uptime_seconds': 0,
            'requests_processed': 0,
            'reports_generated': 0,
            'deliveries_completed': 0,
            'ssl_certificate_updates': 0,
            'errors_handled': 0,
            'last_activity': None
        }
        
        self.logger.info(f"OCM microservice initialized - Version {self.service_info['version']}")
    
    def _load_configuration(self) -> Dict[str, Any]:
        """Load configuration from JSON files using PMM-aware paths."""
        try:
            # Try to get PMM paths from environment or CCU
            installation_root = Path.cwd()
            
            # Method 1: Try PMM environment variable
            if "PMM_PATHS" in os.environ:
                try:
                    pmm_paths = json.loads(os.environ["PMM_PATHS"])
                    installation_root = Path(pmm_paths.get("installation_root", Path.cwd()))
                    service_root = pmm_paths.get("service_root")
                    if service_root:
                        config_path = Path(service_root) / "config" / "ocm_config.json"
                    else:
                        config_path = installation_root / "MicroServices" / "OCM" / "OCM_MAIN" / "ocm" / "config" / "ocm_config.json"
                except (json.JSONDecodeError, KeyError):
                    config_path = None
            else:
                config_path = None
            
            # Method 2: Look for installation markers if PMM env not available
            if not config_path:
                current_path = Path(__file__).resolve()
                markers = ["JFA_CONFIGURATION_PLAN.md", "LICENSE.txt", "MicroServices", ".git"]
                
                for parent in current_path.parents:
                    if any((parent / marker).exists() for marker in markers):
                        # Found installation root, construct config path
                        config_path = parent / "MicroServices" / "OCM" / "OCM_MAIN" / "ocm" / "config" / "ocm_config.json"
                        break
                else:
                    # Method 3: Fallback to original method
                    config_path = Path("config/ocm_config.json")
            
            if config_path and config_path.exists():
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    self.logger.info(f"Configuration loaded from {config_path}")
                    return config
            else:
                self.logger.warning(f"Configuration file not found at {config_path}, using defaults")
                return self._get_default_config()
                
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            "service": {
                "name": "OCM",
                "version": "1.0.0",
                "description": "Output Cache Management Microservice"
            },
            "network": {
                "websocket_port": 47811,
                "api_port": 47812,
                "web_server_host": "localhost",
                "web_server_port": 443,
                "web_server_endpoint": "/api/data",
                "ssl_enabled": True,
                "max_connections": 50
            },
            "ssl_configuration": {
                "enabled": True,
                "certificate_source": "ccu_managed",
                "hot_reload": True
            },
            "priority_management": {
                "priorities": ["A", "B", "C", "D"],
                "default_priority": "C"
            },
            "acknowledgment_protocol": {
                "enabled": True,
                "timeout": 30,
                "retry_attempts": 3,
                "checksum_validation": True
            },
            "report_generation": {
                "html_templates_path": "templates/html",
                "pdf_engine": "weasyprint",
                "output_formats": ["html", "pdf"]
            },
            "output_validation": {
                "enabled_validations": ["content_integrity", "format_compliance", "completeness", "size_limits"],
                "max_file_size_mb": 50,
                "quality_threshold": 80,
                "html_max_size_mb": 10,
                "pdf_max_size_mb": 50,
                "json_max_size_mb": 5,
                "text_max_size_mb": 5
            },
            "database": {
                "type": "sqlite",
                "path": "data/ocm.db",
                "partition_by_priority": True
            },
            "logging": {
                "level": "INFO",
                "file": "logs/ocm.log",
                "max_size": "100MB",
                "backup_count": 5
            },
            "monitoring": {
                "enabled": True,
                "metrics_interval": 60,
                "health_check_interval": 30
            }
        }
    
    def _initialize_modules(self):
        """Initialize all modules in the correct order."""
        try:
            # Core modules first
            self.modules['EMM'] = ErrorManagementModule(self.config)
            self.modules['MSM'] = MonitoringSystemModule(self.config)
            self.modules['DCM'] = DatabaseControlModule(self.config)
            
            # Network and communication modules
            self.modules['NMM'] = NetworkManagementModule(self.config)
            self.modules['ECM'] = ExternalControlModule(self.config)
            
            # Processing modules
            self.modules['RMM'] = RequestManagementModule(self.config)
            self.modules['DSM'] = DataSenderModule(self.config)
            
            # Integration modules
            self.modules['TDIM'] = TDInteractionModule(self.config)
            self.modules['RCMIM'] = RCMInteractionModule(self.config)
            
            # Report generation modules
            self.modules['HRPM'] = HTMLReportProducerModule(self.config)
            self.modules['PRFPM'] = PDFReportFormatProducerModule(self.config)
            self.modules['OCVM'] = OutputCheckValidityModule(self.config)
            
            # Background and API modules
            self.modules['BTM'] = BackgroundTaskModule(self.config)
            self.modules['FAIM'] = FastAPIIntegrationModule(self.config)
            
            # Testing module
            self.modules['TMM'] = TestManagementModule(self.config)
            
            self.logger.info("All modules initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize modules: {e}")
            raise
    
    def _setup_signal_handlers(self):
        """Set up signal handlers for graceful shutdown."""
        try:
            if sys.platform != 'win32':
                signal.signal(signal.SIGTERM, self._signal_handler)
                signal.signal(signal.SIGINT, self._signal_handler)
            
        except Exception as e:
            self.logger.error(f"Failed to set up signal handlers: {e}")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        self.logger.info(f"Received signal {signum}, initiating graceful shutdown")
        asyncio.create_task(self.stop())
    
    async def start(self):
        """Start the OCM microservice."""
        try:
            self.logger.info("Starting OCM microservice...")
            self.startup_time = datetime.now()
            self.stats['start_time'] = self.startup_time.isoformat()
            
            # Start core modules first
            await self.modules['EMM'].start()
            await self.modules['DCM'].start()
            await self.modules['MSM'].start()
            
            # Start network modules
            await self.modules['NMM'].start()
            
            # Set up SSL certificate management callbacks
            self._setup_ssl_certificate_callbacks()
            
            # Start ECM for CCU communication
            await self.modules['ECM'].start()
            
            # Start processing modules
            await self.modules['RMM'].start()
            await self.modules['DSM'].start()
            
            # Start integration modules
            await self.modules['TDIM'].start()
            await self.modules['RCMIM'].start()
            
            # Start report generation modules
            await self.modules['HRPM'].start()
            await self.modules['PRFPM'].start()
            await self.modules['OCVM'].start()
            
            # Start background tasks
            await self.modules['BTM'].start()
            
            # Start API module
            await self.modules['FAIM'].start()
            
            # Start testing module
            await self.modules['TMM'].start()
            
            # Start main service loop
            asyncio.create_task(self._main_service_loop())
            
            self.is_active = True
            self.gateway_active = False  # Output gateway not active until CCU commands it
            self.logger.info("OCM microservice started successfully - ready for CCU activation")
            
            # Log startup summary
            await self._log_startup_summary()
            
        except Exception as e:
            self.logger.error(f"Failed to start OCM microservice: {e}")
            await self._handle_startup_error(e)
            raise
    
    async def stop(self):
        """Stop the OCM microservice gracefully."""
        try:
            self.logger.info("Stopping OCM microservice...")
            self.is_active = False
            
            # Stop modules in reverse order
            for module_name, module in reversed(list(self.modules.items())):
                try:
                    if hasattr(module, 'stop'):
                        await module.stop()
                        self.logger.info(f"Stopped {module_name}")
                except Exception as e:
                    self.logger.error(f"Error stopping {module_name}: {e}")
            
            # Calculate uptime
            if self.startup_time:
                self.stats['uptime_seconds'] = (datetime.now() - self.startup_time).total_seconds()
            
            self.logger.info("OCM microservice stopped successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to stop OCM microservice: {e}")
    
    def _setup_ssl_certificate_callbacks(self):
        """Set up SSL certificate update callbacks from CCU."""
        try:
            async def ssl_certificate_update_handler(cert_data):
                """Handle SSL certificate updates from CCU."""
                try:
                    self.logger.info("Received SSL certificate update from CCU")
                    
                    # Validate certificate data
                    if not cert_data.get('cert_content') or not cert_data.get('key_content'):
                        self.logger.error("Invalid certificate data received from CCU")
                        return False
                    
                    # Update internal certificate storage
                    self.ssl_certificates.update({
                        'cert_content': cert_data['cert_content'],
                        'key_content': cert_data['key_content'],
                        'cert_hash': cert_data.get('cert_hash', ''),
                        'key_hash': cert_data.get('key_hash', ''),
                        'expires_at': cert_data.get('expires_at'),
                        'updated_at': datetime.now().isoformat()
                    })
                    
                    # Update NMM with new certificates
                    if 'NMM' in self.modules:
                        success = await self.modules['NMM'].update_ssl_certificates(cert_data)
                        if success:
                            self.stats['ssl_certificate_updates'] += 1
                            self.logger.info("NMM SSL certificates updated successfully")
                            return True
                        else:
                            self.logger.error("Failed to update NMM SSL certificates")
                            return False
                    
                    self.logger.warning("NMM module not available for certificate update")
                    return False
                    
                except Exception as e:
                    self.logger.error(f"Error handling SSL certificate update: {e}")
                    # Report error to EMM
                    if 'EMM' in self.modules:
                        await self.modules['EMM'].handle_error('ssl_certificate_update', str(e))
                    return False
            
            # Register the callback with ECM
            if 'ECM' in self.modules:
                self.modules['ECM'].register_command_handler('certificate_update', ssl_certificate_update_handler)
                self.logger.info("SSL certificate update callbacks registered with ECM")
            
        except Exception as e:
            self.logger.error(f"Failed to set up SSL certificate callbacks: {e}")
    
    async def _main_service_loop(self):
        """Main service loop for handling background operations."""
        while self.is_active:
            try:
                # Update uptime
                if self.startup_time:
                    self.stats['uptime_seconds'] = (datetime.now() - self.startup_time).total_seconds()
                
                # Perform periodic maintenance
                await self._perform_periodic_maintenance()
                
                # Sleep for a short interval
                await asyncio.sleep(1)
                
            except Exception as e:
                self.logger.error(f"Error in main service loop: {e}")
                if 'EMM' in self.modules:
                    await self.modules['EMM'].handle_error('main_service_loop', str(e))
                await asyncio.sleep(5)
    
    async def _perform_periodic_maintenance(self):
        """Perform periodic maintenance tasks."""
        try:
            # Update statistics from modules
            await self._update_statistics()
            
            # Check SSL certificate expiry
            await self._check_ssl_certificate_expiry()
            
            # Perform health checks
            await self._perform_health_checks()
            
        except Exception as e:
            self.logger.error(f"Error in periodic maintenance: {e}")
    
    async def _update_statistics(self):
        """Update service statistics from modules."""
        try:
            # Collect statistics from all modules
            if 'RMM' in self.modules:
                rmm_stats = self.modules['RMM'].get_statistics()
                self.stats['requests_processed'] = rmm_stats.get('total_requests_processed', 0)
                self.stats['reports_generated'] = rmm_stats.get('reports_generated', 0)
            
            if 'DSM' in self.modules:
                dsm_stats = self.modules['DSM'].get_statistics()
                self.stats['deliveries_completed'] = dsm_stats.get('successful_deliveries', 0)
            
            if 'EMM' in self.modules:
                emm_stats = self.modules['EMM'].get_statistics()
                self.stats['errors_handled'] = emm_stats.get('total_errors_handled', 0)
            
            self.stats['last_activity'] = datetime.now().isoformat()
            
        except Exception as e:
            self.logger.error(f"Error updating statistics: {e}")
    
    async def _check_ssl_certificate_expiry(self):
        """Check SSL certificate expiry and log warnings."""
        try:
            if not self.ssl_certificates.get('expires_at'):
                return
            
            expires_at = datetime.fromisoformat(self.ssl_certificates['expires_at'])
            time_to_expiry = expires_at - datetime.now()
            
            if time_to_expiry.days <= 7:
                self.logger.warning(f"SSL certificate expires in {time_to_expiry.days} days")
                if 'EMM' in self.modules:
                    await self.modules['EMM'].handle_warning(
                        'ssl_certificate_expiry',
                        f'Certificate expires in {time_to_expiry.days} days'
                    )
            elif time_to_expiry.days <= 30:
                self.logger.info(f"SSL certificate expires in {time_to_expiry.days} days")
                
        except Exception as e:
            self.logger.error(f"Error checking SSL certificate expiry: {e}")
    
    async def _perform_health_checks(self):
        """Perform periodic health checks on modules."""
        try:
            unhealthy_modules = []
            
            for module_name, module in self.modules.items():
                if hasattr(module, 'health_check'):
                    try:
                        is_healthy = await module.health_check()
                        if not is_healthy.get('healthy', False):
                            unhealthy_modules.append(module_name)
                    except Exception as e:
                        self.logger.error(f"Health check failed for {module_name}: {e}")
                        unhealthy_modules.append(module_name)
            
            if unhealthy_modules:
                self.logger.warning(f"Unhealthy modules detected: {', '.join(unhealthy_modules)}")
                if 'EMM' in self.modules:
                    await self.modules['EMM'].handle_warning(
                        'unhealthy_modules',
                        f'Modules in unhealthy state: {", ".join(unhealthy_modules)}'
                    )
            
        except Exception as e:
            self.logger.error(f"Error performing health checks: {e}")
    
    async def _log_startup_summary(self):
        """Log startup summary information."""
        try:
            module_count = len(self.modules)
            ssl_enabled = self.ssl_certificates.get('cert_content', '') != ''
            
            summary = {
                'service': self.service_info['name'],
                'version': self.service_info['version'],
                'startup_time': self.startup_time.isoformat(),
                'modules_loaded': module_count,
                'ssl_enabled': ssl_enabled,
                'network_ports': {
                    'websocket': self.config.get('network', {}).get('websocket_port', 47811),
                    'api': self.config.get('network', {}).get('api_port', 47812)
                },
                'capabilities': self.service_info['capabilities']
            }
            
            self.logger.info(f"OCM Startup Summary: {json.dumps(summary, indent=2)}")
            
        except Exception as e:
            self.logger.error(f"Error logging startup summary: {e}")
    
    async def _handle_startup_error(self, error: Exception):
        """Handle startup errors."""
        try:
            error_info = {
                'error_type': type(error).__name__,
                'error_message': str(error),
                'timestamp': datetime.now().isoformat(),
                'service': 'OCM',
                'phase': 'startup'
            }
            
            self.logger.critical(f"OCM Startup Failed: {json.dumps(error_info, indent=2)}")
            
            # Try to notify EMM if it's available
            if 'EMM' in self.modules:
                await self.modules['EMM'].handle_critical_error('startup_failure', error_info)
            
        except Exception as e:
            self.logger.error(f"Error handling startup error: {e}")
    
    # Public API methods for external control
    
    async def process_output_request(self, request_data: Dict[str, Any], 
                                   priority: str = 'C',
                                   delivery_options: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Process an output request through the OCM pipeline.
        
        Args:
            request_data: The data to process and deliver
            priority: Priority level (A, B, C, D)
            delivery_options: Custom delivery options
            
        Returns:
            Processing result with delivery confirmation
        """
        try:
            if not self.is_active:
                raise RuntimeError("OCM service is not active")
            
            self.logger.info(f"Processing output request with priority {priority}")
            
            # Submit to RMM for processing
            if 'RMM' in self.modules:
                result = await self.modules['RMM'].submit_request(
                    request_data=request_data,
                    priority=priority,
                    delivery_options=delivery_options or {}
                )
                
                self.stats['requests_processed'] += 1
                return result
            else:
                raise RuntimeError("RMM module not available")
                
        except Exception as e:
            self.logger.error(f"Failed to process output request: {e}")
            if 'EMM' in self.modules:
                await self.modules['EMM'].handle_error('output_request_processing', str(e))
            raise
    
    async def update_configuration(self, config_updates: Dict[str, Any]) -> bool:
        """
        Update service configuration dynamically.
        
        Args:
            config_updates: Configuration updates to apply
            
        Returns:
            bool: True if configuration was updated successfully
        """
        try:
            self.logger.info(f"Updating configuration: {list(config_updates.keys())}")
            
            # Update internal configuration
            self._update_config_dict(self.config, config_updates)
            
            # Propagate configuration updates to modules
            for module_name, module in self.modules.items():
                if hasattr(module, 'update_configuration'):
                    try:
                        await module.update_configuration(config_updates)
                        self.logger.debug(f"Configuration updated for {module_name}")
                    except Exception as e:
                        self.logger.error(f"Failed to update configuration for {module_name}: {e}")
            
            self.logger.info("Configuration updated successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update configuration: {e}")
            return False
    
    def _update_config_dict(self, target: Dict[str, Any], updates: Dict[str, Any]):
        """Recursively update configuration dictionary."""
        for key, value in updates.items():
            if isinstance(value, dict) and key in target and isinstance(target[key], dict):
                self._update_config_dict(target[key], value)
            else:
                target[key] = value
    
    async def run_tests(self, test_types: List[str] = None) -> Dict[str, Any]:
        """
        Run tests on the OCM service.
        
        Args:
            test_types: List of test types to run
            
        Returns:
            Test results
        """
        try:
            if 'TMM' in self.modules:
                return await self.modules['TMM'].run_tests(test_types or ['health', 'integration'])
            else:
                raise RuntimeError("TMM module not available")
                
        except Exception as e:
            self.logger.error(f"Failed to run tests: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def get_service_status(self) -> Dict[str, Any]:
        """Get comprehensive service status."""
        try:
            module_status = {}
            for module_name, module in self.modules.items():
                try:
                    if hasattr(module, 'get_status'):
                        module_status[module_name] = module.get_status()
                    else:
                        module_status[module_name] = {'status': 'unknown'}
                except Exception as e:
                    module_status[module_name] = {'status': 'error', 'error': str(e)}
            
            return {
                'service': self.service_info,
                'active': self.is_active,
                'statistics': self.stats.copy(),
                'ssl_certificates': {
                    'enabled': bool(self.ssl_certificates.get('cert_content')),
                    'expires_at': self.ssl_certificates.get('expires_at'),
                    'last_updated': self.ssl_certificates.get('updated_at')
                },
                'configuration': {
                    'network_ports': {
                        'websocket': self.config.get('network', {}).get('websocket_port', 47811),
                        'api': self.config.get('network', {}).get('api_port', 47812)
                    },
                    'ssl_enabled': self.config.get('ssl_configuration', {}).get('enabled', True),
                    'priority_levels': self.config.get('priority_management', {}).get('priorities', ['A', 'B', 'C', 'D'])
                },
                'modules': module_status,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting service status: {e}")
            return {
                'service': self.service_info,
                'active': self.is_active,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check."""
        try:
            overall_healthy = self.is_active
            module_health = {}
            
            # Check health of all modules
            for module_name, module in self.modules.items():
                try:
                    if hasattr(module, 'health_check'):
                        health_result = await module.health_check()
                        module_health[module_name] = health_result
                        # NMM can fail due to SSL certificate issues but service should still be healthy
                        if not health_result.get('healthy', False) and module_name != 'NMM':
                            overall_healthy = False
                    else:
                        module_health[module_name] = {'healthy': True, 'note': 'No health check available'}
                except Exception as e:
                    module_health[module_name] = {'healthy': False, 'error': str(e)}
                    # NMM can fail due to SSL certificate issues but service should still be healthy
                    if module_name != 'NMM':
                        overall_healthy = False
            
            return {
                'healthy': overall_healthy,
                'service': self.service_info['name'],
                'version': self.service_info['version'],
                'uptime_seconds': self.stats['uptime_seconds'],
                'ssl_certificates_valid': bool(self.ssl_certificates.get('cert_content')),
                'modules_health': module_health,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return {
                'healthy': False,
                'service': self.service_info['name'],
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    async def activate_gateway(self):
        """Activate OCM output gateway to start sending results to external destinations."""
        try:
            if self.gateway_active:
                self.logger.info("OCM Output Gateway is already active")
                return {"status": "already_active"}
            
            self.logger.info("OCM: Activating output gateway services...")
            
            # Activate output validation and conversion modules
            output_modules = ['OCVM', 'HRPM', 'PRFPM']
            for module_name in output_modules:
                if module_name in self.modules:
                    module = self.modules[module_name]
                    if hasattr(module, 'activate_output_processing'):
                        await module.activate_output_processing()
                        self.logger.info(f"OCM: {module_name} output processing activated")
            
            # Update gateway state
            self.gateway_active = True
            
            self.logger.info("OCM: Output Gateway activated - ready to send results to website")
            return {"status": "gateway_activated", "outputs": ["website", "reports", "performance"]}
            
        except Exception as e:
            self.logger.error(f"OCM: Failed to activate output gateway: {e}")
            return {"status": "error", "message": str(e)}
    
    async def deactivate_gateway(self):
        """Deactivate OCM output gateway to stop sending results."""
        try:
            if not self.gateway_active:
                self.logger.info("OCM Output Gateway is already inactive")
                return {"status": "already_inactive"}
            
            self.logger.info("OCM: Deactivating output gateway services...")
            
            # Deactivate output modules
            output_modules = ['OCVM', 'HRPM', 'PRFPM']
            for module_name in output_modules:
                if module_name in self.modules:
                    module = self.modules[module_name]
                    if hasattr(module, 'deactivate_output_processing'):
                        await module.deactivate_output_processing()
                        self.logger.info(f"OCM: {module_name} output processing deactivated")
            
            # Update gateway state
            self.gateway_active = False
            
            self.logger.info("OCM: Output Gateway deactivated")
            return {"status": "gateway_deactivated"}
            
        except Exception as e:
            self.logger.error(f"OCM: Failed to deactivate output gateway: {e}")
            return {"status": "error", "message": str(e)}


async def main():
    """Main entry point for the OCM microservice."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('logs/ocm.log', mode='a')
        ]
    )
    
    # Create logs directory if it doesn't exist
    Path('logs').mkdir(exist_ok=True)
    
    # Create and start OCM microservice
    ocm = OCMMicroservice()
    
    try:
        await ocm.start()
        
        # Keep the service running
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        print("\nShutting down OCM microservice...")
        await ocm.stop()
    except Exception as e:
        print(f"Error running OCM microservice: {e}")
        await ocm.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nOCM microservice terminated by user")
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)
