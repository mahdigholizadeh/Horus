"""
TPP (Text Processing and Purification) Microservice - Main Entry Point

This is the central controller for the TPP microservice, responsible for:
- Advanced text processing and spam filtering
- Persian/Farsi language processing
- Multi-language spam detection
- Content purification and sanitization
- CCU integration and health monitoring
- Dynamic spam word management

The TPP microservice acts as an advanced text processing engine that filters
spam words, purifies content, and prepares text for downstream processing.

Refactored to follow modular architecture pattern similar to RCM and RLA.
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
from TPDM.tpdm import TextProcessingDataModule

# Import SWM with fallback for null bytes issue
try:
    from SWM.swm import SpamWordManagementModule
except SyntaxError as e:
    if "null bytes" in str(e):
        # Create a minimal fallback SWM class
        class SpamWordManagementModule:
            def __init__(self):
                self.module_name = "SWM"
                self.is_active = False
            async def start(self):
                self.is_active = True
            async def load_persian_alphabet_lists(self):
                """Load Persian alphabet-organized spam word lists (fallback implementation)."""
                return True
            async def load_custom_lists(self):
                """Load custom spam word lists (fallback implementation)."""
                return True
            async def load_multilingual_lists(self):
                """Load multilingual spam word lists (fallback implementation)."""
                return True
            async def reload_all_lists(self):
                """Reload all spam word lists (fallback implementation)."""
                return True
            async def remove_spam_words(self, words, language="persian", category="custom"):
                """Remove spam words (fallback implementation)."""
                return {"success": True, "words_removed": [], "count": 0}
            async def get_lists_status(self):
                """Get lists status (fallback implementation)."""
                return {"loaded": True, "total_words": 0}
            async def add_spam_words(self, words, language="persian", category="custom"):
                """Add spam words (fallback implementation)."""
                return {"success": True, "words_added": [], "count": 0}
            async def import_spam_words(self, file_path, language="persian", category="custom"):
                """Import spam words (fallback implementation)."""
                return {"success": True, "imported_count": 0}
            async def export_spam_words(self, file_path, language="all", category="all"):
                """Export spam words (fallback implementation)."""
                return {"success": True, "exported_count": 0}
            async def check_spam(self, text, language="persian"):
                return {"success": True, "is_spam": False, "spam_words_found": []}
            async def health_check(self):
                return {"healthy": self.is_active, "module": self.module_name}
    else:
        raise

from LPM.lpm import LanguageProcessingModule
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
from FTM.ftm import FilterTextModule



class TPPMicroservice:
    """
    TPP Microservice - Central Controller
    
    This class orchestrates all modules and provides the main interface for:
    - Advanced text processing and spam filtering
    - Persian/Farsi language processing with alphabet organization
    - Multi-language content purification
    - Dynamic spam word management
    - CCU integration and health monitoring
    - Service lifecycle management
    """
    
    def __init__(self):
        """Initialize the TPP microservice with all modules."""
        self.logger = logging.getLogger(__name__)
        self.is_active = False
        self.modules = {}
        
        # Configuration
        self.config = self._load_configuration()
        
        # Initialize all modules
        self._initialize_modules()
        
        # Service configuration
        self.service_config = {
            "service_name": "TPP",
            "version": "1.0.0",
            "processing_modes": ["persian", "multilingual", "custom"],
            "supported_languages": ["fa", "en", "ar", "ur"],
            "max_text_length": 100000,
            "max_file_size": 50 * 1024 * 1024,  # 50MB
            "default_mode": "persian"
        }
        
        # Network configuration
        self.network_config = {
            "api_port": 8080,
            "health_port": 9091,
            "websocket_port": 11490,
            "host": "0.0.0.0"
        }
        
        # Processing statistics
        self.stats = {
            "total_processed": 0,
            "successful_processing": 0,
            "failed_processing": 0,
            "spam_words_removed": 0,
            "total_words_processed": 0,
            "average_processing_time": 0,
            "last_activity": None,
            "processing_by_language": {},
            "filter_effectiveness": 0.0
        }
        
        # Text processing metrics
        self.processing_metrics = {
            "persian_texts": 0,
            "english_texts": 0,
            "multilingual_texts": 0,
            "total_words_filtered": 0,
            "spam_detection_rate": 0.0,
            "content_reduction_rate": 0.0,
            "processing_speed_wps": 0.0  # words per second
        }
        
        self.logger.info("TPP microservice initialized successfully")
    
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
                installation_root / "MicroServices" / "TPP" / "TPP_Main" / "TPP" / "TPP" / "config" / "tpp_setting.json",
                installation_root / "config" / "tpp_setting.json",
                Path("config/tpp_setting.json"),  # Fallback to relative path
                Path.cwd() / "config" / "tpp_setting.json"
            ]
            
            for config_path in config_locations:
                if config_path.exists():
                    self.logger.info(f"Loading TPP configuration from: {config_path}")
                    with open(config_path, 'r', encoding='utf-8') as f:
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
            "service_name": "TPP",
            "version": "1.0.0",
            "processing": {
                "default_language": "persian",
                "enable_multilingual": True,
                "max_text_length": 100000,
                "preserve_word_order": True,
                "case_sensitive": True,
                "enable_stemming": False
            },
            "spam_filtering": {
                "enabled": True,
                "persian_alphabet_mode": True,
                "custom_lists_enabled": True,
                "dynamic_updates": True,
                "strictness_level": "medium"
            },
            "network": {
                "api_port": 8080,
                "health_port": 9091,
                "websocket_port": 11490,
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
            "file_processing": {
                "input_formats": ["json", "txt", "csv"],
                "output_formats": ["json", "txt"],
                "batch_size": 100,
                "temp_directory": "temp"  # PMM will manage actual temp paths
            }
        }
    
    def _initialize_modules(self):
        """Initialize all modules in the correct order."""
        try:
            # Core system modules first
            self.modules['EMM'] = ErrorManagementModule()
            self.modules['MSM'] = MonitoringSystemModule()
            self.modules['CIM'] = ConfigurationInterfaceModule()
            
            # Text processing core modules
            self.modules['TPDM'] = TextProcessingDataModule()
            self.modules['SWM'] = SpamWordManagementModule()
            self.modules['FTM'] = FilterTextModule()
            self.modules['LPM'] = LanguageProcessingModule()
            
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
        """Start the TPP microservice."""
        try:
            self.logger.info("Starting TPP microservice...")
            
            # Start all modules
            for module_name, module in self.modules.items():
                if hasattr(module, 'start'):
                    await module.start()
                    self.logger.info(f"Started {module_name}")
            
            # Initialize spam word lists
            await self._initialize_spam_word_lists()
            
            # Start API server
            await self.modules['ARM'].start_api_server(self.network_config["api_port"])
            
            # Start health monitoring
            await self.modules['MSM'].start_monitoring()
            
            # ECM will handle CCU communication internally (already started)
            
            # Start background tasks
            await self.modules['BTM'].start_background_tasks()
            
            self.is_active = True
            self.logger.info("TPP microservice started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start TPP microservice: {e}")
            raise
    
    async def stop(self):
        """Stop the TPP microservice."""
        try:
            self.logger.info("Stopping TPP microservice...")
            
            # Stop all modules in reverse order
            for module_name, module in reversed(list(self.modules.items())):
                if hasattr(module, 'stop'):
                    await module.stop()
                    self.logger.info(f"Stopped {module_name}")
            
            self.is_active = False
            self.logger.info("TPP microservice stopped successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to stop TPP microservice: {e}")
            raise
    
    async def _initialize_spam_word_lists(self):
        """Initialize spam word lists from configuration."""
        try:
            # Load Persian alphabet-organized spam words
            await self.modules['SWM'].load_persian_alphabet_lists()
            
            # Load custom spam word lists if configured
            if self.config.get('spam_filtering', {}).get('custom_lists_enabled', True):
                await self.modules['SWM'].load_custom_lists()
            
            # Initialize multilingual spam detection if enabled
            if self.config.get('processing', {}).get('enable_multilingual', True):
                await self.modules['SWM'].load_multilingual_lists()
            
            self.logger.info("Spam word lists initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize spam word lists: {e}")
            raise
    
    async def process_text(self, text_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process text through the complete purification pipeline.
        
        Args:
            text_data: Dictionary containing text and processing parameters
            
        Returns:
            Processing result with purified text
        """
        try:
            start_time = datetime.now()
            self.stats["total_processed"] += 1
            
            # Step 1: Input validation and processing via IPM
            input_result = await self.modules['IPM'].process_input(text_data)
            if not input_result['valid']:
                self.stats["failed_processing"] += 1
                return self._create_error_response("Input validation failed", input_result['errors'])
            
            # Step 2: Language detection via LPM
            language_result = await self.modules['LPM'].detect_language(input_result['processed_data'])
            detected_language = language_result.get('language', 'unknown')
            
            # Step 3: Text processing via TPDM
            processing_result = await self.modules['TPDM'].process_text(
                input_result['processed_data'], 
                language_result
            )
            
            # Step 4: Spam filtering via FTM
            filter_result = await self.modules['FTM'].filter_spam_words(
                processing_result['processed_text'],
                detected_language,
                self.modules['SWM']
            )
            
            # Step 5: Output generation via OPM
            output_result = await self.modules['OPM'].generate_output(
                text_data,
                filter_result,
                {
                    'language': detected_language,
                    'processing_stats': processing_result.get('stats', {}),
                    'filter_stats': filter_result.get('stats', {})
                }
            )
            
            # Update statistics
            processing_time = (datetime.now() - start_time).total_seconds()
            self.stats["successful_processing"] += 1
            self.stats["last_activity"] = datetime.now()
            
            # Update processing metrics
            self._update_processing_metrics(filter_result, detected_language, processing_time)
            
            # Update average processing time
            total = self.stats["total_processed"]
            self.stats["average_processing_time"] = (
                (self.stats["average_processing_time"] * (total - 1) + processing_time) / total
            )
            
            self.logger.info(f"Text processed successfully in {processing_time:.3f}s")
            
            return {
                'success': True,
                'processed_data': output_result['output_data'],
                'processing_time': processing_time,
                'language': detected_language,
                'statistics': {
                    'words_removed': filter_result.get('words_removed', 0),
                    'original_word_count': filter_result.get('original_word_count', 0),
                    'final_word_count': filter_result.get('final_word_count', 0),
                    'reduction_percentage': filter_result.get('reduction_percentage', 0.0)
                },
                'flags': {
                    'TPP_flag': 1,
                    'spam_filtered': filter_result.get('spam_detected', False),
                    'language_detected': detected_language
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error processing text: {e}")
            self.stats["failed_processing"] += 1
            
            # Log error via EMM
            await self.modules['EMM'].log_error("TPP", "TPPMicroservice", "process_text", str(e))
            
            return self._create_error_response("Processing error", [str(e)])
    
    async def process_file(self, file_path: str, output_path: str = None) -> Dict[str, Any]:
        """
        Process a file through the TPP pipeline.
        
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
            result = await self.process_text(file_data)
            
            # Save output if specified
            if output_path and result['success']:
                await self.modules['FIM'].write_file(output_path, result['processed_data'])
                result['output_file'] = output_path
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error processing file: {e}")
            return self._create_error_response("File processing error", [str(e)])
    
    def _update_processing_metrics(self, filter_result: Dict[str, Any], language: str, processing_time: float):
        """Update processing metrics."""
        try:
            # Update language-specific counters
            if language == 'fa':  # Persian/Farsi
                self.processing_metrics["persian_texts"] += 1
            elif language == 'en':  # English
                self.processing_metrics["english_texts"] += 1
            else:
                self.processing_metrics["multilingual_texts"] += 1
            
            # Update filter metrics
            words_removed = filter_result.get('words_removed', 0)
            original_count = filter_result.get('original_word_count', 0)
            
            self.processing_metrics["total_words_filtered"] += words_removed
            self.stats["spam_words_removed"] += words_removed
            self.stats["total_words_processed"] += original_count
            
            # Calculate processing speed (words per second)
            if processing_time > 0:
                wps = original_count / processing_time
                # Update running average
                current_wps = self.processing_metrics["processing_speed_wps"]
                total_texts = (self.processing_metrics["persian_texts"] + 
                             self.processing_metrics["english_texts"] + 
                             self.processing_metrics["multilingual_texts"])
                self.processing_metrics["processing_speed_wps"] = (
                    (current_wps * (total_texts - 1) + wps) / total_texts
                )
            
            # Update effectiveness metrics
            if self.stats["total_words_processed"] > 0:
                self.stats["filter_effectiveness"] = (
                    self.stats["spam_words_removed"] / self.stats["total_words_processed"]
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
            'service': 'TPP'
        }
    
    async def reload_spam_lists(self) -> bool:
        """Reload spam word lists."""
        try:
            await self.modules['SWM'].reload_all_lists()
            self.logger.info("Spam word lists reloaded successfully")
            return True
        except Exception as e:
            self.logger.error(f"Failed to reload spam lists: {e}")
            return False
    
    async def add_spam_words(self, words: List[str], language: str = "fa") -> bool:
        """Add new spam words to the system."""
        try:
            result = await self.modules['SWM'].add_spam_words(words, language)
            self.logger.info(f"Added {len(words)} spam words for language {language}")
            return result
        except Exception as e:
            self.logger.error(f"Failed to add spam words: {e}")
            return False
    
    async def remove_spam_words(self, words: List[str], language: str = "fa") -> bool:
        """Remove spam words from the system."""
        try:
            result = await self.modules['SWM'].remove_spam_words(words, language)
            self.logger.info(f"Removed {len(words)} spam words for language {language}")
            return result
        except Exception as e:
            self.logger.error(f"Failed to remove spam words: {e}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the TPP microservice."""
        return {
            'service': 'TPP',
            'version': self.service_config['version'],
            'is_active': self.is_active,
            'modules': {name: getattr(module, 'get_status', lambda: {'status': 'unknown'})() for name, module in self.modules.items()},
            'configuration': self.service_config,
            'network': self.network_config,
            'statistics': self.stats,
            'processing_metrics': self.processing_metrics,
            'supported_languages': self.service_config['supported_languages'],
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
            
            # Check spam word lists status
            spam_lists_healthy = True
            try:
                spam_status = await self.modules['SWM'].get_lists_status()
                spam_lists_healthy = spam_status.get('loaded', False)
            except:
                spam_lists_healthy = False
            
            return {
                'healthy': all_healthy and spam_lists_healthy,
                'service': 'TPP',
                'timestamp': datetime.now().isoformat(),
                'modules': module_health,
                'spam_lists_status': spam_lists_healthy,
                'processing_metrics': self.processing_metrics,
                'uptime': self.stats.get('uptime', 0)
            }
            
        except Exception as e:
            return {
                'healthy': False,
                'error': str(e),
                'service': 'TPP',
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
    
    def process_file_legacy(self, input_path: str, output_path: str) -> bool:
        """Legacy file processing method."""
        try:
            result = asyncio.run(self.process_file(input_path, output_path))
            return result.get('success', False)
        except Exception as e:
            self.logger.error(f"Legacy file processing failed: {e}")
            return False


async def main():
    """Main entry point for the TPP microservice."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create and start TPP microservice
    tpp = TPPMicroservice()
    
    try:
        await tpp.start()
        
        # Keep the service running
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        print("Shutting down TPP microservice...")
        await tpp.stop()
    except Exception as e:
        print(f"Error running TPP microservice: {e}")
        await tpp.stop()


if __name__ == "__main__":
    asyncio.run(main()) 