"""
RLA (Request Limit Analyzer) Microservice - Main Entry Point

This is the central controller for the RLA microservice, responsible for:
- Initialization of all modules
- Gateway validation and limit enforcement
- CCU integration and health monitoring
- Request validation and sanitization

The RLA microservice acts as the primary Gateway/Ingress Controller, receiving text payloads
in JSON format via HTTPS/TCP on port 3781 and enforcing critical limits to protect downstream services.

Refactored to follow modular architecture pattern similar to RCM.
"""

import asyncio
import logging
import sys
import uvicorn
import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

# Import all modules
from GVDM.gvdm import GatewayValidationDataModule
from ARM.arm import ActivationReceiverModule
from DRM.drm import DataReceiverModule
from LEM.lem import LimitEnforcementModule
from SVM.svm import SpamValidationModule
from IVM.ivm import InputValidationModule
from OPM.opm import OutputProcessingModule
from ECM.ecm import ExternalControlModule
from EMM.emm import ErrorManagementModule
from MSM.msm import MonitoringSystemModule
from TMM.tmm import TestManagementModule
from FAIM.faim import FastAPIIntegrationModule
from BTM.btm import BackgroundTasksModule


class RLAMicroservice:
    """
    RLA Microservice - Central Controller
    
    This class orchestrates all modules and provides the main interface for:
    - Gateway validation and ingress control
    - Request limit enforcement
    - Input sanitization and validation
    - CCU integration and health monitoring
    - Service lifecycle management
    """
    
    def __init__(self):
        """Initialize the RLA microservice with all modules."""
        self.logger = logging.getLogger(__name__)
        self.is_active = False
        self.modules = {}
        
        # Configuration
        self.config = self._load_configuration()
        
        # Initialize all modules
        self._initialize_modules()
        
        # Protocol constants
        self.activation_key = 0b1001110100110111  # 0x9D37
        self.handshake_start = 0xBB7F73DF  # R1
        self.handshake_end = 0xBB7578DF    # R2
        self.success_ack = 0b1011111111111111  # 0xBFFF
        
        # Network configuration
        self.activation_port = 3812
        self.data_port = 3781
        self.health_port = 9090
        
        # Limits configuration
        self.max_words = 3000
        self.max_tokens = 5000
        self.max_request_size = 10 * 1024 * 1024  # 10MB
        
        # Statistics
        self.stats = {
            "total_requests": 0,
            "validated_requests": 0,
            "rejected_requests": 0,
            "activation_attempts": 0,
            "successful_activations": 0,
            "average_processing_time": 0,
            "last_activity": None
        }
        
        self.logger.info("RLA microservice initialized successfully")
    
    def _load_configuration(self) -> Dict[str, Any]:
        """Load configuration from JSON files using PMM-aware paths."""
        try:
            # Try to get PMM paths from environment or CCU
            installation_root = Path.cwd()
            
            # Check for PMM-provided path information
            if "PMM_PATHS" in os.environ:
                import json
                pmm_paths = json.loads(os.environ["PMM_PATHS"])
                installation_root = Path(pmm_paths.get("installation_root", Path.cwd()))
            
            # Try multiple configuration locations (PMM-aware)
            config_locations = [
                installation_root / "MicroServices" / "RLA" / "RLA_Main" / "RLA" / "RLA" / "RLA" / "config" / "rla_setting.json",
                installation_root / "config" / "rla_setting.json",
                Path("config/rla_setting.json"),  # Fallback to relative path
                Path.cwd() / "config" / "rla_setting.json"
            ]
            
            for config_path in config_locations:
                if config_path.exists():
                    self.logger.info(f"Loading RLA configuration from: {config_path}")
                    with open(config_path, 'r') as f:
                        config = json.load(f)
                        
                    # Add PMM path information if available
                    if "PMM_PATHS" in os.environ:
                        config["pmm_paths"] = pmm_paths
                        
                    return config
            
            self.logger.warning("Configuration file not found in any location, using defaults")
            return self._get_default_config()
                
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            "service_name": "RLA",
            "version": "1.0.0",
            "network": {
                "activation_port": 3812,
                "data_port": 3781,
                "health_port": 9090,
                "host": "0.0.0.0",
                "max_connections": 1000,
                "connection_timeout": 30
            },
            "limits": {
                "max_words": 3000,
                "max_tokens": 5000,
                "max_request_size": "10MB"
            },
            "validation": {
                "enabled": True,
                "json_schema_validation": True,
                "content_filtering": True,
                "spam_detection": True
            },
            "security": {
                "enable_ssl": True,
                "cert_file": "certificates/cert.pem",  # PMM-managed certificate path
                "key_file": "certificates/key.pem"    # PMM-managed certificate path
            }
        }
    
    def _initialize_modules(self):
        """Initialize all modules in the correct order."""
        try:
            # Core modules first
            self.modules['EMM'] = ErrorManagementModule()
            self.modules['MSM'] = MonitoringSystemModule()
            
            # Gateway and validation modules
            self.modules['GVDM'] = GatewayValidationDataModule()
            self.modules['ARM'] = ActivationReceiverModule()
            self.modules['DRM'] = DataReceiverModule()
            self.modules['LEM'] = LimitEnforcementModule()
            self.modules['SVM'] = SpamValidationModule()
            self.modules['IVM'] = InputValidationModule()
            self.modules['OPM'] = OutputProcessingModule()
            
            # Control and integration modules
            self.modules['ECM'] = ExternalControlModule()
            self.modules['FAIM'] = FastAPIIntegrationModule()
            self.modules['BTM'] = BackgroundTasksModule()
            
            # Testing module
            self.modules['TMM'] = TestManagementModule()
            
            self.logger.info("All modules initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize modules: {e}")
            raise
    
    async def start(self):
        """Start the RLA microservice."""
        try:
            self.logger.info("Starting RLA microservice...")
            
            # Start all modules
            for module_name, module in self.modules.items():
                if hasattr(module, 'start'):
                    await module.start()
                    self.logger.info(f"Started {module_name}")
            
            # Set up certificate update callback
            self._setup_certificate_callbacks()
            
            # Start background tasks
            await self.modules['BTM'].start_background_tasks()
            
            # Start monitoring
            await self.modules['MSM'].start_monitoring()
            
            # Start health API
            await self.modules['FAIM'].start_health_api()
            
            # ECM will handle CCU communication and activation commands
            # Set up ECM callback for activation
            self._setup_ecm_activation_callback()
            
            self.is_active = True
            self.gateway_active = False  # Gateway not active until CCU commands it
            self.logger.info("RLA microservice started successfully - ready for CCU activation")
            
        except Exception as e:
            self.logger.error(f"Failed to start RLA microservice: {e}")
            raise
    
    async def stop(self):
        """Stop the RLA microservice."""
        try:
            self.logger.info("Stopping RLA microservice...")
            
            # Stop all modules in reverse order
            for module_name, module in reversed(list(self.modules.items())):
                if hasattr(module, 'stop'):
                    await module.stop()
                    self.logger.info(f"Stopped {module_name}")
            
            self.is_active = False
            self.logger.info("RLA microservice stopped successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to stop RLA microservice: {e}")
            raise
    
    def _setup_certificate_callbacks(self):
        """Set up certificate update callbacks from CCU via ECM."""
        try:
            # ECM now handles certificate updates internally through its comprehensive
            # command routing system. SSL certificates are managed via the 
            # update_ssl_certificate command that ECM processes.
            
            self.logger.info("Certificate management delegated to ECM - no additional callbacks needed")
            
        except Exception as e:
            self.logger.error(f"Failed to set up certificate callbacks: {e}")
    
    def _setup_ecm_activation_callback(self):
        """Set up ECM activation callback for CCU control."""
        try:
            # Set callback in ECM for activation commands
            ecm_module = self.modules.get('ECM')
            if ecm_module:
                # Override ECM's _activate_service method to call our activation
                ecm_module._original_activate_service = ecm_module._activate_service
                ecm_module._activate_service = self._handle_ccu_activation
                ecm_module._original_deactivate_service = ecm_module._deactivate_service  
                ecm_module._deactivate_service = self._handle_ccu_deactivation
                
                self.logger.info("ECM activation callbacks configured")
            else:
                self.logger.error("ECM module not found for activation callback setup")
                
        except Exception as e:
            self.logger.error(f"Failed to set up ECM activation callback: {e}")
    
    def _handle_ccu_activation(self):
        """Handle activation command from CCU via ECM."""
        try:
            self.logger.info("RLA: Received activation command from CCU")
            
            # RLA microservice is already running, just acknowledge activation
            # Gateway activation will be handled separately
            
            # Update ECM gateway state
            ecm_module = self.modules.get('ECM')
            if ecm_module:
                ecm_module.gateway_state["activation_enabled"] = True
                ecm_module.gateway_state["data_reception_enabled"] = False  # Gateway not active yet
            
            self.logger.info("RLA: Microservice activation acknowledged by CCU")
            return {"status": "activated", "message": "RLA microservice ready, gateway awaiting separate activation"}
            
        except Exception as e:
            self.logger.error(f"RLA: Failed to handle CCU activation: {e}")
            return {"status": "error", "message": str(e)}
    
    async def activate_gateway(self):
        """Activate RLA gateway to start accepting requests."""
        try:
            if self.gateway_active:
                self.logger.info("RLA Gateway is already active")
                return {"status": "already_active"}
            
            self.logger.info("RLA: Activating gateway services...")
            
            # Start gateway services now
            await self._start_gateway_services()
            
            # Update gateway state
            self.gateway_active = True
            
            # Update ECM gateway state
            ecm_module = self.modules.get('ECM')
            if ecm_module:
                ecm_module.gateway_state["data_reception_enabled"] = True
            
            self.logger.info("RLA: Gateway activated - ready to accept requests")
            return {"status": "gateway_activated", "endpoints": ["data:3781", "health:3781"]}
            
        except Exception as e:
            self.logger.error(f"RLA: Failed to activate gateway: {e}")
            return {"status": "error", "message": str(e)}
    
    async def deactivate_gateway(self):
        """Deactivate RLA gateway to stop accepting requests."""
        try:
            if not self.gateway_active:
                self.logger.info("RLA Gateway is already inactive")
                return {"status": "already_inactive"}
            
            self.logger.info("RLA: Deactivating gateway services...")
            
            # Stop gateway services
            if hasattr(self.modules['DRM'], 'stop_data_listener'):
                await self.modules['DRM'].stop_data_listener()
            
            # Update gateway state
            self.gateway_active = False
            
            # Update ECM gateway state
            ecm_module = self.modules.get('ECM')
            if ecm_module:
                ecm_module.gateway_state["data_reception_enabled"] = False
            
            self.logger.info("RLA: Gateway deactivated")
            return {"status": "gateway_deactivated"}
            
        except Exception as e:
            self.logger.error(f"RLA: Failed to deactivate gateway: {e}")
            return {"status": "error", "message": str(e)}
    
    def _handle_ccu_deactivation(self):
        """Handle deactivation command from CCU via ECM."""
        try:
            self.logger.info("Received deactivation command from CCU")
            
            # Stop gateway services
            if hasattr(self.modules['DRM'], 'stop_data_listener'):
                asyncio.create_task(self.modules['DRM'].stop_data_listener())
            if hasattr(self.modules['ARM'], 'stop_activation_listener'):
                asyncio.create_task(self.modules['ARM'].stop_activation_listener())
            
            # Update ECM gateway state
            ecm_module = self.modules.get('ECM')
            if ecm_module:
                ecm_module.gateway_state["activation_enabled"] = False
                ecm_module.gateway_state["data_reception_enabled"] = False
            
            self.logger.info("RLA Gateway service deactivated by CCU")
            return {"status": "deactivated"}
            
        except Exception as e:
            self.logger.error(f"Failed to handle CCU deactivation: {e}")
            return {"status": "error", "message": str(e)}
    
    async def _start_gateway_services(self):
        """Start the gateway services for request processing."""
        # Only start data receiver for processing requests
        # ARM activation listener is no longer needed since we use ECM activation
        
        # Start data receiver with SSL configuration from config
        ssl_config = self.config.get('ssl_configuration', {})
        await self.modules['DRM'].start_data_listener(
            port=self.data_port,
            ssl_config=ssl_config
        )
        
        self.logger.info(f"RLA gateway services started - ready to receive requests on port {self.data_port}")
    
    async def process_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process an incoming request through the validation pipeline.
        
        Args:
            request_data: The request data to validate
            
        Returns:
            Validation result
        """
        try:
            start_time = datetime.now()
            
            self.logger.info(f"Processing request with {len(str(request_data))} bytes")
            
            # Step 1: Input validation via IVM
            validation_result = await self.modules['IVM'].validate_input(request_data)
            if not validation_result['valid']:
                self.stats['rejected_requests'] += 1
                return self._create_rejection_response("Input validation failed", validation_result['errors'])
            
            # Step 2: Limit enforcement via LEM
            limit_result = await self.modules['LEM'].check_limits(request_data)
            if not limit_result['within_limits']:
                self.stats['rejected_requests'] += 1
                return self._create_rejection_response("Limits exceeded", limit_result['violations'])
            
            # Step 3: Spam validation via SVM
            spam_result = await self.modules['SVM'].check_spam(request_data)
            if spam_result['is_spam']:
                self.stats['rejected_requests'] += 1
                return self._create_rejection_response("Spam detected", spam_result['reasons'])
            
            # Step 4: Output processing via OPM
            processed_data = await self.modules['OPM'].process_output(
                request_data, 
                validation_result, 
                limit_result
            )
            
            # Update statistics
            processing_time = (datetime.now() - start_time).total_seconds()
            self.stats['total_requests'] += 1
            self.stats['validated_requests'] += 1
            self.stats['last_activity'] = datetime.now()
            
            # Update average processing time
            total = self.stats['total_requests']
            self.stats['average_processing_time'] = (
                (self.stats['average_processing_time'] * (total - 1) + processing_time) / total
            )
            
            self.logger.info(f"Request processed successfully in {processing_time:.3f}s")
            
            return {
                'success': True,
                'data': processed_data,
                'processing_time': processing_time,
                'validation_flags': {
                    'input_valid': True,
                    'limits_ok': True,
                    'spam_free': True
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error processing request: {e}")
            self.stats['rejected_requests'] += 1
            
            # Log error via EMM
            await self.modules['EMM'].log_error("RLA", "RLAMicroservice", "process_request", str(e))
            
            return self._create_rejection_response("Processing error", [str(e)])
    
    def _create_rejection_response(self, reason: str, details: list) -> Dict[str, Any]:
        """Create a standardized rejection response."""
        return {
            'success': False,
            'rejected': True,
            'reason': reason,
            'details': details,
            'timestamp': datetime.now().isoformat(),
            'service': 'RLA'
        }
    
    async def activate_service(self) -> bool:
        """Activate the RLA service (legacy compatibility)."""
        self.is_active = True
        self.stats['activation_attempts'] += 1
        self.stats['successful_activations'] += 1
        return True
    
    async def deactivate_service(self) -> bool:
        """Deactivate the RLA service."""
        self.is_active = False
        return True
    
    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the RLA microservice."""
        return {
            'service': 'RLA',
            'version': '1.0.0',
            'is_active': self.is_active,
            'modules': {name: getattr(module, 'get_status', lambda: {'status': 'unknown'})() for name, module in self.modules.items()},
            'network': {
                'activation_port': self.activation_port,
                'data_port': self.data_port,
                'health_port': self.health_port
            },
            'limits': {
                'max_words': self.max_words,
                'max_tokens': self.max_tokens,
                'max_request_size': self.max_request_size
            },
            'statistics': self.stats,
            'timestamp': datetime.now().isoformat()
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        try:
            # Check all modules
            module_health = {}
            all_healthy = True
            
            for name, module in self.modules.items():
                if hasattr(module, 'health_check'):
                    health = await module.health_check()
                    module_health[name] = health
                    if not health.get('healthy', True):
                        all_healthy = False
                else:
                    module_health[name] = {'healthy': True, 'status': 'no_check'}
            
            return {
                'healthy': all_healthy,
                'service': 'RLA',
                'timestamp': datetime.now().isoformat(),
                'modules': module_health,
                'uptime': self.stats.get('uptime', 0)
            }
            
        except Exception as e:
            return {
                'healthy': False,
                'error': str(e),
                'service': 'RLA',
                'timestamp': datetime.now().isoformat()
            }
    
    async def run_service(self):
        """Legacy compatibility method for original RLA interface."""
        try:
            await self.start()
            
            # Keep service running
            while self.is_active:
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            self.logger.info("RLA service stopped by user")
        except Exception as e:
            self.logger.error(f"Service error: {e}")
        finally:
            await self.stop()
    
    # Legacy compatibility methods
    def activate(self) -> bool:
        """Legacy activation method."""
        return asyncio.run(self.activate_service())
    
    def getdata(self):
        """Legacy getdata method - now redirects to modular processing."""
        self.logger.warning("getdata() is deprecated - use process_request() instead")
        return {"error": "Use new API", "success": False}


async def main():
    """Main entry point for the RLA microservice."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create and start RLA microservice
    rla = RLAMicroservice()
    
    try:
        await rla.start()
        
        # Keep the service running
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        print("Shutting down RLA microservice...")
        await rla.stop()
    except Exception as e:
        print(f"Error running RLA microservice: {e}")
        await rla.stop()


if __name__ == "__main__":
    asyncio.run(main())


