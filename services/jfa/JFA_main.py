"""
JFA (JSON File Analyzer) Microservice - Main Entry Point

This is the central controller for the JFA microservice, responsible for:
- Advanced JSON template analysis and validation
- Binary data generation and processing
- Template structure validation
- Complex data analysis workflows
- CCU integration and health monitoring
- Dynamic template management

The JFA microservice acts as an advanced JSON analysis engine that validates
template structures, generates binary data, and performs comprehensive analysis
for downstream processing in the Horus ecosystem.

Refactored to follow modular architecture pattern similar to RCM, RLA, and TPP.
"""

import asyncio
import logging
import sys
import uvicorn
import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

# Import all modules
from JDPM.jdpm import JSONDataProcessingModule
from TVM.tvm import TemplateValidationModule
from BDM.bdm import BinaryDataModule
from DAM.dam import DataAnalysisModule
from IPM.ipm import InputProcessingModule
from OPM.opm import OutputProcessingModule
from FIM.fim import FileInterfaceModule
from ECM.ecm import ExternalControlModule
from ARM.arm import APIRequestModule
from CIM.cim import ConfigurationInterfaceModule
from EMM.emm import ErrorManagementModule
from MSM.msm import MonitoringSystemModule
from BTM.btm import BackgroundTasksModule
from TMM.tmm import TestManagementModule


class JFAMicroservice:
    """
    JFA Microservice - Central Controller
    
    This class orchestrates all modules and provides the main interface for:
    - Advanced JSON template analysis and validation
    - Binary data generation and processing
    - Template structure validation with complex rules
    - Multi-stage data analysis workflows
    - CCU integration and health monitoring
    - Service lifecycle management
    """
    
    def __init__(self):
        """Initialize the JFA microservice with all modules."""
        self.logger = logging.getLogger(__name__)
        self.is_active = False
        self.modules = {}
        
        # Configuration
        self.config = self._load_configuration()
        
        # Initialize all modules
        self._initialize_modules()
        
        # Service configuration
        self.service_config = {
            "service_name": "JFA",
            "version": "1.0.0",
            "analysis_modes": ["template", "binary", "comprehensive"],
            "supported_formats": ["json", "binary", "structured"],
            "max_template_size": 10 * 1024 * 1024,  # 10MB
            "max_batch_size": 100,
            "default_mode": "comprehensive"
        }
        
        # Network configuration
        self.network_config = {
            "api_port": 8001,
            "health_port": 9092,
            "websocket_port": 11491,
            "host": "0.0.0.0"
        }
        
        # Processing statistics
        self.stats = {
            "total_processed": 0,
            "successful_processing": 0,
            "failed_processing": 0,
            "templates_validated": 0,
            "binary_files_generated": 0,
            "analyses_completed": 0,
            "average_processing_time": 0,
            "last_activity": None,
            "validation_success_rate": 0.0,
            "analysis_effectiveness": 0.0
        }
        
        # Template processing metrics
        self.processing_metrics = {
            "template_validations": 0,
            "binary_generations": 0,
            "data_analyses": 0,
            "complex_validations": 0,
            "processing_speed_tps": 0.0,  # templates per second
            "validation_accuracy": 0.0,
            "binary_generation_rate": 0.0
        }
        
        self.logger.info("JFA microservice initialized successfully")
    
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
                        config_path = Path(service_root) / "config" / "jfa_setting.json"
                    else:
                        config_path = installation_root / "services" / "jfa" / "config" / "jfa_setting.json"
                except (json.JSONDecodeError, KeyError):
                    config_path = None
            else:
                config_path = None
            
            # Method 2: Look for installation markers if PMM env not available
            if not config_path:
                current_path = Path(__file__).resolve()
                markers = ["README.md", "LICENSE.txt", "services", ".git"]
                
                for parent in current_path.parents:
                    if any((parent / marker).exists() for marker in markers):
                        config_path = parent / "services" / "jfa" / "config" / "jfa_setting.json"
                        break
                else:
                    config_path = Path(__file__).resolve().parent / "config" / "jfa_setting.json"
            
            if config_path and config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                self.logger.warning(f"Configuration file not found at {config_path}, using defaults")
                return self._get_default_config()
                
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            "service_name": "JFA",
            "version": "1.0.0",
            "processing": {
                "default_mode": "comprehensive",
                "enable_binary_generation": True,
                "max_template_size": 10 * 1024 * 1024,
                "enable_batch_processing": True,
                "validation_strictness": "high",
                "enable_data_analysis": True
            },
            "template_validation": {
                "validate_structure": True,
                "validate_data_types": True,
                "validate_required_fields": True,
                "validate_business_rules": True,
                "custom_validators": True
            },
            "binary_processing": {
                "enabled": True,
                "compression": "gzip",
                "encoding": "utf-8",
                "checksum_validation": True,
                "version_control": True
            },
            "network": {
                "api_port": 8001,
                "health_port": 9092,
                "websocket_port": 11491,
                "host": "0.0.0.0",
                "max_connections": 1000
            },
            "ccu_integration": {
                "enabled": True,
                "ccu_host": "localhost",
                "ccu_port": 11489,
                "heartbeat_interval": 30,
                "status_report_interval": 60
            },
            "analysis": {
                "enable_deep_analysis": True,
                "enable_pattern_detection": True,
                "enable_anomaly_detection": True,
                "analysis_timeout": 300,
                "concurrent_analyses": 10
            }
        }
    
    def _initialize_modules(self):
        """Initialize all modules in the correct order."""
        try:
            # Core system modules first
            self.modules['EMM'] = ErrorManagementModule()
            self.modules['MSM'] = MonitoringSystemModule()
            self.modules['CIM'] = ConfigurationInterfaceModule()
            
            # JSON analysis core modules
            self.modules['JDPM'] = JSONDataProcessingModule()
            self.modules['TVM'] = TemplateValidationModule()
            self.modules['BDM'] = BinaryDataModule()
            self.modules['DAM'] = DataAnalysisModule()
            
            # Input/Output modules
            self.modules['IPM'] = InputProcessingModule()
            self.modules['OPM'] = OutputProcessingModule()
            self.modules['FIM'] = FileInterfaceModule()
            
            # Integration modules
            self.modules['ECM'] = ExternalControlModule()
            self.modules['ARM'] = APIRequestModule()
            
            # Support modules
            self.modules['BTM'] = BackgroundTasksModule()
            self.modules['TMM'] = TestManagementModule()
            
            self.logger.info("All modules initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize modules: {e}")
            raise
    
    async def start(self):
        """Start the JFA microservice."""
        try:
            self.logger.info("Starting JFA microservice...")
            
            # Start all modules
            for module_name, module in self.modules.items():
                if hasattr(module, 'start'):
                    await module.start()
                    self.logger.info(f"Started {module_name}")
            
            # Start API server
            await self.modules['ARM'].start_api_server(self.network_config["api_port"])
            
            # Start health monitoring
            await self.modules['MSM'].start_monitoring()
            
            # ECM will handle CCU communication internally (already started)
            
            # Start background tasks
            await self.modules['BTM'].start_background_tasks()
            
            self.is_active = True
            self.logger.info("JFA microservice started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start JFA microservice: {e}")
            raise
    
    async def stop(self):
        """Stop the JFA microservice."""
        try:
            self.logger.info("Stopping JFA microservice...")
            
            # Stop all modules in reverse order
            for module_name, module in reversed(list(self.modules.items())):
                if hasattr(module, 'stop'):
                    await module.stop()
                    self.logger.info(f"Stopped {module_name}")
            
            self.is_active = False
            self.logger.info("JFA microservice stopped successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to stop JFA microservice: {e}")
            raise
    
    async def process_template(self, template_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a JSON template through the complete analysis pipeline.
        
        Args:
            template_data: Dictionary containing template and processing parameters
            
        Returns:
            Processing result with analysis data and binary file for TD consumption
        """
        try:
            start_time = datetime.now()
            self.stats["total_processed"] += 1
            
            # Step 1: Input validation and processing via IPM
            input_result = await self.modules['IPM'].process_input(template_data)
            if not input_result['valid']:
                self.stats["failed_processing"] += 1
                return self._create_error_response("Input validation failed", input_result['errors'])
            
            # Step 2: JSON data processing via JDPM
            json_result = await self.modules['JDPM'].process_json_data(input_result['processed_data'])
            if not json_result['success']:
                self.stats["failed_processing"] += 1
                return self._create_error_response("JSON processing failed", json_result.get('errors', []))
            
            # Step 3: Template validation via TVM
            validation_result = await self.modules['TVM'].validate_template(
                json_result['processed_json'],
                template_data.get('validation_rules', {})
            )
            
            # Handle validation failures with detailed recognition
            if not validation_result.get('valid', False):
                self.stats["failed_processing"] += 1
                
                # Get request_id for tracking
                request_id = template_data.get('request_id', f"jfa_req_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}")
                
                # Perform detailed validation failure analysis
                validation_errors = validation_result.get('errors', [])
                
                # Use ECM to analyze validation failures
                if 'ECM' in self.modules:
                    try:
                        # Analyze invalid data
                        invalid_analysis = await self.modules['ECM'].invalid_data_recognition(
                            template_data, validation_errors, request_id
                        )
                        
                        # Analyze insufficient data
                        insufficient_analysis = await self.modules['ECM'].insufficient_data_recognition(
                            template_data, validation_errors, request_id
                        )
                        
                        # Create enhanced error response with recognition data
                        enhanced_error_response = self._create_error_response("Template validation failed", validation_errors)
                        enhanced_error_response.update({
                            'validation_analysis': {
                                'invalid_data_recognition': invalid_analysis,
                                'insufficient_data_recognition': insufficient_analysis,
                                'request_id': request_id
                            },
                            'recognition_available': True
                        })
                        
                        return enhanced_error_response
                        
                    except Exception as e:
                        self.logger.error(f"Error in validation failure analysis: {e}")
                        # Fall back to standard error response
                        return self._create_error_response("Template validation failed", validation_errors)
                else:
                    # Fall back to standard error response if ECM not available
                    return self._create_error_response("Template validation failed", validation_errors)
            
            # Step 4: Binary data generation via BDM (enhanced for TD compatibility)
            binary_result = {}
            td_compatible_binary = None
            
            binary_result = await self.modules['BDM'].generate_binary_data(
                validation_result['validated_data']
            )
            
            # Generate TD-compatible binary format
            if binary_result.get('success', False):
                td_compatible_binary = await self._generate_td_binary_format(
                    validation_result['validated_data'],
                    template_data
                )
            
            # Step 5: Data analysis via DAM
            analysis_result = await self.modules['DAM'].analyze_data(
                validation_result,
                binary_result,
                template_data.get('analysis_config', {})
            )
            
            # Step 6: Output generation via OPM (enhanced for CCU integration)
            output_result = await self.modules['OPM'].generate_output(
                template_data,
                {
                    'json_processing': json_result,
                    'validation': validation_result,
                    'binary_generation': binary_result,
                    'analysis': analysis_result,
                    'td_binary': td_compatible_binary
                }
            )
            
            # Step 7: Prepare data for CCU/TD transmission
            ccu_ready_data = await self._prepare_for_ccu_transmission(
                output_result,
                td_compatible_binary,
                template_data
            )
            
            # Update statistics
            processing_time = (datetime.now() - start_time).total_seconds()
            self.stats["successful_processing"] += 1
            self.stats["last_activity"] = datetime.now()
            
            if validation_result.get('valid', False):
                self.stats["templates_validated"] += 1
            
            if binary_result.get('success', False):
                self.stats["binary_files_generated"] += 1
            
            if analysis_result.get('success', False):
                self.stats["analyses_completed"] += 1
            
            # Update processing metrics
            self._update_processing_metrics(validation_result, binary_result, analysis_result, processing_time)
            
            # Update average processing time
            total = self.stats["total_processed"]
            self.stats["average_processing_time"] = (
                (self.stats["average_processing_time"] * (total - 1) + processing_time) / total
            )
            
            self.logger.info(f"Template processed successfully in {processing_time:.3f}s")
            
            return {
                'success': True,
                'processed_data': output_result['output_data'],
                'processing_time': processing_time,
                'validation_result': validation_result,
                'binary_result': binary_result,
                'analysis_result': analysis_result,
                'td_binary_data': td_compatible_binary,
                'ccu_ready_data': ccu_ready_data,
                'statistics': {
                    'templates_validated': self.stats["templates_validated"],
                    'binary_files_generated': self.stats["binary_files_generated"],
                    'analyses_completed': self.stats["analyses_completed"],
                    'processing_speed': 1.0 / processing_time if processing_time > 0 else 0
                },
                'flags': {
                    'JFA_flag': 1,
                    'validation_passed': validation_result.get('valid', False),
                    'binary_generated': binary_result.get('success', False),
                    'analysis_completed': analysis_result.get('success', False),
                    'td_compatible': td_compatible_binary is not None,
                    'ccu_ready': ccu_ready_data is not None
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error processing template: {e}")
            self.stats["failed_processing"] += 1
            
            # Log error via EMM
            await self.modules['EMM'].log_error("JFA", "JFAMicroservice", "process_template", str(e))
            
            return self._create_error_response("Processing error", [str(e)])
    
    async def process_file(self, file_path: str, output_path: str = None) -> Dict[str, Any]:
        """
        Process a JSON file through the JFA pipeline.
        
        Args:
            file_path: Path to input file
            output_path: Path for output file (optional)
            
        Returns:
            Processing result
        """
        try:
            # Use FIM for file operations
            file_data = await self.modules['FIM'].read_file(file_path)
            
            # Process the file content
            result = await self.process_template(file_data)
            
            # Save output if specified
            if output_path and result['success']:
                await self.modules['FIM'].write_file(output_path, result['processed_data'])
                result['output_file'] = output_path
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error processing file: {e}")
            return self._create_error_response("File processing error", [str(e)])
    
    def _update_processing_metrics(self, validation_result: Dict[str, Any], 
                                 binary_result: Dict[str, Any], 
                                 analysis_result: Dict[str, Any], 
                                 processing_time: float):
        """Update processing metrics."""
        try:
            # Update validation metrics
            if validation_result.get('valid', False):
                self.processing_metrics["template_validations"] += 1
            
            # Update binary generation metrics
            if binary_result.get('success', False):
                self.processing_metrics["binary_generations"] += 1
            
            # Update analysis metrics
            if analysis_result.get('success', False):
                self.processing_metrics["data_analyses"] += 1
            
            # Update complex validation metrics
            if validation_result.get('complex_validation', False):
                self.processing_metrics["complex_validations"] += 1
            
            # Calculate processing speed (templates per second)
            if processing_time > 0:
                tps = 1.0 / processing_time
                current_tps = self.processing_metrics["processing_speed_tps"]
                total_processed = self.stats["total_processed"]
                self.processing_metrics["processing_speed_tps"] = (
                    (current_tps * (total_processed - 1) + tps) / total_processed
                )
            
            # Update validation accuracy
            if self.stats["total_processed"] > 0:
                self.processing_metrics["validation_accuracy"] = (
                    self.stats["templates_validated"] / self.stats["total_processed"]
                )
            
            # Update binary generation rate
            if self.stats["templates_validated"] > 0:
                self.processing_metrics["binary_generation_rate"] = (
                    self.stats["binary_files_generated"] / self.stats["templates_validated"]
                )
            
            # Update overall effectiveness
            if self.stats["total_processed"] > 0:
                self.stats["validation_success_rate"] = (
                    self.stats["templates_validated"] / self.stats["total_processed"]
                )
                self.stats["analysis_effectiveness"] = (
                    self.stats["analyses_completed"] / self.stats["total_processed"]
                )
            
        except Exception as e:
            self.logger.error(f"Error updating processing metrics: {e}")
    
    def _create_error_response(self, reason: str, details: list) -> Dict[str, Any]:
        """Create a standardized error response."""
        return {
            'success': False,
            'error': True,
            'reason': reason,
            'details': details,
            'timestamp': datetime.now().isoformat(),
            'service': 'JFA'
        }
    
    async def batch_process(self, templates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process multiple templates in batch."""
        try:
            results = []
            
            for template in templates:
                result = await self.process_template(template)
                results.append(result)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error in batch processing: {e}")
            raise
    
    async def get_validation_rules(self) -> Dict[str, Any]:
        """Get current validation rules."""
        try:
            return await self.modules['TVM'].get_validation_rules()
        except Exception as e:
            self.logger.error(f"Error getting validation rules: {e}")
            return {}
    
    async def update_validation_rules(self, rules: Dict[str, Any]) -> bool:
        """Update validation rules."""
        try:
            return await self.modules['TVM'].update_validation_rules(rules)
        except Exception as e:
            self.logger.error(f"Error updating validation rules: {e}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the JFA microservice."""
        return {
            'service': 'JFA',
            'version': self.service_config['version'],
            'is_active': self.is_active,
            'modules': {name: getattr(module, 'get_status', lambda: {'status': 'unknown'})() for name, module in self.modules.items()},
            'configuration': self.service_config,
            'network': self.network_config,
            'statistics': self.stats,
            'processing_metrics': self.processing_metrics,
            'supported_formats': self.service_config['supported_formats'],
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
                'healthy': all_healthy and self.is_active,
                'service': 'JFA',
                'timestamp': datetime.now().isoformat(),
                'modules': module_health,
                'processing_metrics': self.processing_metrics,
                'uptime': self.stats.get('uptime', 0),
                'analysis_capabilities': {
                    'template_validation': True,
                    'binary_generation': True,
                    'data_analysis': True,
                    'batch_processing': True
                }
            }
            
        except Exception as e:
            return {
                'healthy': False,
                'error': str(e),
                'service': 'JFA',
                'timestamp': datetime.now().isoformat()
            }
    
    # Legacy compatibility methods
    def activate(self) -> bool:
        """Legacy activation method."""
        self.is_active = True
        return True
    
    def deactivate(self) -> bool:
        """Legacy deactivation method."""
        self.is_active = False
        return True
    
    async def _generate_td_binary_format(self, validated_data: Dict[str, Any], 
                                       template_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Generate TD-compatible binary format for calculation processing.
        
        Args:
            validated_data: Validated template data
            template_data: Original template data with metadata
            
        Returns:
            Dictionary containing TD-compatible binary data structure
        """
        try:
            route = template_data.get("route") or validated_data.get("route") or "forward"
            payload = validated_data.get("payload", validated_data)

            td_binary_data = {
                "request_id": template_data.get(
                    "request_id", f'jfa_req_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
                ),
                "route": route,
                "payload": payload,
                "metadata": {
                    "template_version": template_data.get("version", "1.0"),
                    "jfa_processed_timestamp": datetime.now().isoformat(),
                    "proxy_mode": True,
                },
            }

            td_binary_data["activation_flags"] = self._generate_activation_flags(
                validated_data, route
            )
            return td_binary_data

        except Exception as e:
            self.logger.error(f"Error generating TD routing payload: {e}")
            return None

    def _generate_activation_flags(self, validated_data: Dict[str, Any], route: str) -> Dict[str, int]:
        """Generate routing flags for TD proxy (forward / parallel / sequential)."""
        try:
            flags = {"forward": 0, "parallel": 0, "sequential": 0}
            if route in flags:
                flags[route] = 1
            else:
                flags["forward"] = 1

            if validated_data.get("parallel_routing"):
                flags["parallel"] = 1
            if validated_data.get("sequential_routing"):
                flags["sequential"] = 1

            return flags

        except Exception as e:
            self.logger.error(f"Error generating activation flags: {e}")
            return {"forward": 1, "parallel": 0, "sequential": 0}
    
    async def _prepare_for_ccu_transmission(self, output_result: Dict[str, Any], 
                                          td_binary: Optional[Dict[str, Any]], 
                                          template_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Prepare processed data for CCU transmission to TD.
        
        Args:
            output_result: JFA processing output
            td_binary: TD-compatible binary data
            template_data: Original template data
            
        Returns:
            Dictionary ready for CCU transmission
        """
        try:
            if not td_binary:
                return None
            
            ccu_data = {
                'transmission_metadata': {
                    'source_service': 'JFA',
                    'target_service': 'TD',
                    'via_service': 'CCU',
                    'transmission_id': f'jfa_to_td_{datetime.now().strftime("%Y%m%d_%H%M%S_%f")}',
                    'timestamp': datetime.now().isoformat(),
                    'priority': template_data.get('priority', 'normal'),
                    'expected_processing_time_seconds': 60
                },
                
                'binary_data': td_binary,
                
                'calculation_request': {
                    'route': td_binary.get('route', 'forward'),
                    'activation_flags': td_binary.get('activation_flags', [1] + [0]*11),
                    'orchestration_mode': 'concurrent',
                    'result_format': 'ocm_compatible',
                    'enable_cross_analysis': True
                },
                
                'jfa_metadata': {
                    'template_validated': output_result.get('validation_passed', False),
                    'binary_generated': td_binary is not None,
                    'analysis_completed': output_result.get('analysis_completed', False),
                    'processing_time_seconds': output_result.get('processing_time', 0),
                    'jfa_version': self.service_config['version']
                },
                
                'ccu_instructions': {
                    'forward_to_td': True,
                    'wait_for_td_response': True,
                    'forward_td_results_to_ocm': True,
                    'include_jfa_metadata': True,
                    'timeout_seconds': 300
                }
            }
            
            return ccu_data
            
        except Exception as e:
            self.logger.error(f"Error preparing CCU transmission data: {e}")
            return None
    
    async def send_to_ccu(self, ccu_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send processed data to CCU for forwarding to TD.
        
        Args:
            ccu_data: Data prepared for CCU transmission
            
        Returns:
            CCU response dictionary
        """
        try:
            # Use ECM (External Control Module) for CCU communication
            if 'ECM' in self.modules:
                ccu_response = await self.modules['ECM'].send_to_ccu(ccu_data)
                return ccu_response
            else:
                self.logger.warning("ECM module not available for CCU communication")
                return {
                    'success': False,
                    'error': 'CCU communication module not available',
                    'timestamp': datetime.now().isoformat()
                }
                
        except Exception as e:
            self.logger.error(f"Error sending data to CCU: {e}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    async def process_and_send_to_td(self, template_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Complete workflow: Process template and send to TD via CCU.
        
        Args:
            template_data: Template data for processing
            
        Returns:
            Complete workflow result including TD response
        """
        try:
            # Step 1: Process template
            jfa_result = await self.process_template(template_data)
            
            if not jfa_result['success']:
                return jfa_result
            
            # Step 2: Send to CCU if TD-compatible data generated
            ccu_response = None
            if jfa_result.get('ccu_ready_data'):
                ccu_response = await self.send_to_ccu(jfa_result['ccu_ready_data'])
            
            # Step 3: Return complete workflow result
            return {
                'success': True,
                'workflow': 'JFA_to_TD_via_CCU',
                'jfa_processing': jfa_result,
                'ccu_transmission': ccu_response,
                'td_ready': jfa_result.get('flags', {}).get('td_compatible', False),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error in complete JFA to TD workflow: {e}")
            return self._create_error_response("Workflow error", [str(e)])
    
    def process_template_legacy(self, template_data: Dict[str, Any]) -> bool:
        """Legacy template processing method."""
        try:
            result = asyncio.run(self.process_template(template_data))
            return result.get('success', False)
        except Exception as e:
            self.logger.error(f"Legacy template processing failed: {e}")
            return False


async def main():
    """Main entry point for the JFA microservice."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create and start JFA microservice
    jfa = JFAMicroservice()
    
    try:
        await jfa.start()
        
        # Keep the service running
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        print("Shutting down JFA microservice...")
        await jfa.stop()
    except Exception as e:
        print(f"Error running JFA microservice: {e}")
        await jfa.stop()


if __name__ == "__main__":
    asyncio.run(main()) 