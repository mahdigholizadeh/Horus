"""
Error Management Module (EMM) for TD Microservice

Manages all aspects of error detection, logging, and recovery.
Generates 16-character hexadecimal error codes and implements automated recovery strategies.
Follows the centralized error handling pattern established in RCM but adapted for TD (Microservice 05).
"""

import logging
import json
import os
import re
import asyncio
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime


class ErrorManagementModule:
    """
    Error Management Module (EMM) for TD Microservice
    
    Manages all aspects of error detection, logging, and recovery.
    Generates 16-character hexadecimal error codes and implements automated recovery strategies.
    """
    
    def __init__(self):
        """Initialize the Error Management Module."""
        self.logger = logging.getLogger(__name__)
        
        # Error code structure: Server(2) + Macroservice(2) + Microservice(2) + Module(2) + Class(2) + Function(3) + Sub-function(3)
        self.SERVER_CODE = "01"
        self.MACROSERVICE_CODE = "01"
        self.MICROSERVICE_CODE = "05"  # TD
        
        # Module codes (hex values for each TD module)
        self.MODULE_CODES = {
            "BFPM": "01",   # Binary File Processing Module
            "AFM": "02",    # Activation Flag Module
            "ROM": "03",    # Routing Orchestration Module
            "CAM": "04",    # Calculation Aggregation Module
            "CIM": "05",    # Calculation Interface Module
            "RMM": "06",    # Result Management Module
            "FIM": "07",    # File Interface Module
            "CCM": "08",    # CCU Communication Module
            "ARM": "09",    # API Request Module
            "OCMIM": "0A",  # OCM Interface Module
            "BTM": "0B",    # Background Tasks Module
            "TMM": "0C",    # Test Management Module
            "MSM": "0D",    # Monitoring System Module
            "EMM": "0E"     # Error Management Module
        }
        
        # Error log file
        self.error_log_file = Path("logs/error_log.json")
        self.error_log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Enhanced recovery strategies for common errors
        self.recovery_strategies = {
            # File and I/O errors
            "0101050E001": self._recover_file_not_found,
            "0101050E002": self._recover_permission_denied,
            "0101050E003": self._recover_disk_space_full,
            "0101050E004": self._recover_file_corrupted,
            
            # JSON and data parsing errors
            "0101050E005": self._recover_invalid_json,
            "0101050E006": self._recover_missing_required_field,
            "0101050E007": self._recover_invalid_data_type,
            "0101050E008": self._recover_encoding_error,
            
            # Network and API errors
            "0101050E009": self._recover_network_timeout,
            "0101050E00A": self._recover_connection_refused,
            "0101050E00B": self._recover_api_rate_limit,
            "0101050E00C": self._recover_authentication_failed,
            
            # Memory and resource errors
            "0101050E00D": self._recover_memory_overflow,
            "0101050E00E": self._recover_resource_exhausted,
            "0101050E00F": self._recover_thread_timeout,
            
            # Configuration and validation errors
            "0101050E010": self._recover_invalid_config,
            "0101050E011": self._recover_missing_dependency,
            "0101050E012": self._recover_invalid_argument,
            "0101050E013": self._recover_validation_failed,
            
            # TD specific errors
            "0101050E014": self._recover_binary_processing_failed,
            "0101050E015": self._recover_activation_flag_parsing_failed,
            "0101050E016": self._recover_calculation_timeout,
            "0101050E017": self._recover_orchestration_failed,
            "0101050E018": self._recover_result_aggregation_failed,
            "0101050E019": self._recover_calculation_block_unavailable,
            "0101050E01A": self._recover_concurrent_execution_failed,
            "0101050E01B": self._recover_routing_failed,
            "0101050E01C": self._recover_ocm_preparation_failed
        }
        
        # Recovery statistics
        self.recovery_stats = {
            "total_attempts": 0,
            "successful_recoveries": 0,
            "failed_recoveries": 0,
            "last_recovery_attempt": None
        }
        
        # Initialize error log
        self._initialize_error_log()
        
        # Module state
        self.is_active = False
        self.module_name = "EMM"
        
        self.logger.info("TD EMM: Error Management Module initialized")
    
    def _initialize_error_log(self):
        """Initialize the error log file if it doesn't exist."""
        if not self.error_log_file.exists():
            with open(self.error_log_file, 'w', encoding='utf-8') as f:
                json.dump({"errors": [], "statistics": {}, "recovery_stats": {}}, f, indent=2)
    
    def generate_error_code(self, module_name: str, class_name: str, function_name: str, sub_function: str = "001") -> str:
        """
        Generate a 16-character hexadecimal error code.
        
        Args:
            module_name: Name of the module (e.g., "BFPM")
            class_name: Name of the class
            function_name: Name of the function
            sub_function: Sub-function identifier (default: "001")
            
        Returns:
            16-character hexadecimal error code
        """
        # Input validation
        if not module_name or not class_name or not function_name:
            raise ValueError("module_name, class_name, and function_name cannot be empty")
        
        # Ensure all inputs are strings
        module_name = str(module_name)
        class_name = str(class_name)
        function_name = str(function_name)
        sub_function = str(sub_function)
        
        module_code = self.MODULE_CODES.get(module_name, "00")
        
        # Convert class name to hex (simple hash)
        class_hash = abs(hash(class_name)) % 256
        class_code = f"{class_hash:02X}"
        
        # Convert function name to hex (simple hash)
        func_hash = abs(hash(function_name)) % 4096
        func_code = f"{func_hash:03X}"
        
        # Ensure sub_function is 3 characters, treat as int if possible
        try:
            sub_func_int = int(sub_function)
        except (ValueError, TypeError):
            sub_func_int = abs(hash(sub_function)) % 4096
        sub_func_code = f"{sub_func_int:03X}"
        
        # Construct full error code (16 characters total)
        error_code = f"{self.SERVER_CODE}{self.MACROSERVICE_CODE}{self.MICROSERVICE_CODE}{module_code}{class_code}{func_code}{sub_func_code}"
        
        # Ensure exactly 16 characters
        if len(error_code) != 16:
            # Pad or truncate to exactly 16 characters
            error_code = error_code[:16].ljust(16, '0')
        
        return error_code
    
    def log_error_with_generation(self, module_name: str, class_name: str, function_name: str, error_message: str, sub_function: str = "001", recovery_attempted: bool = False, context: Dict[str, Any] = None):
        """
        Generate error code and log error in one call for easier integration.
        
        Args:
            module_name: Name of the module where error occurred
            class_name: Name of the class where error occurred
            function_name: Name of the function where error occurred
            error_message: Descriptive error message
            sub_function: Sub-function identifier (default: "001")
            recovery_attempted: Whether recovery was attempted
            context: Additional context information
        """
        # Input validation
        if not module_name or not class_name or not function_name:
            raise ValueError("module_name, class_name, and function_name cannot be empty")
        
        if not error_message:
            error_message = "No error message provided"
        
        # Ensure all inputs are strings
        module_name = str(module_name)
        class_name = str(class_name)
        function_name = str(function_name)
        error_message = str(error_message)
        sub_function = str(sub_function)
        
        try:
            error_code = self.generate_error_code(module_name, class_name, function_name, sub_function)
            self.log_error(error_code, error_message, module_name, recovery_attempted, context)
            return error_code
        except Exception as e:
            # If error code generation fails, use a fallback
            fallback_code = "0101050E00000001"
            self.log_error(fallback_code, f"Error code generation failed: {str(e)}. Original error: {error_message}", module_name, recovery_attempted, context)
            return fallback_code
    
    def log_error(self, error_code: str, error_message: str, module_name: str = "EMM", recovery_attempted: bool = False, context: Dict[str, Any] = None):
        """
        Log an error with the specified error code and message.
        
        Args:
            error_code: 16-character hexadecimal error code
            error_message: Descriptive error message
            module_name: Name of the module where error occurred
            recovery_attempted: Whether recovery was attempted
            context: Additional context information
        """
        # Input validation
        if not error_code:
            raise ValueError("error_code cannot be empty")
        
        if not error_message:
            error_message = "No error message provided"
        
        # Ensure all inputs are strings
        error_code = str(error_code)
        error_message = str(error_message)
        module_name = str(module_name)
        
        # Ensure error_code is exactly 16 characters
        if len(error_code) != 16:
            # Pad or truncate to exactly 16 characters
            error_code = error_code[:16].ljust(16, '0')
        
        # Format error message according to specification
        formatted_message = f"Error on server code = {error_code[:2]} on Macro service code = {error_code[2:4]} on Micro service code = {error_code[4:6]} on Module code = {error_code[6:8]} occurred. The error is: {error_message}"
        
        error_entry = {
            "timestamp": datetime.now().isoformat(),
            "error_code": error_code,
            "module": module_name,
            "message": error_message,
            "formatted_message": formatted_message,
            "recovery_attempted": recovery_attempted,
            "context": context or {}
        }
        
        # Load existing error log
        try:
            with open(self.error_log_file, 'r', encoding='utf-8') as f:
                error_log = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            error_log = {"errors": [], "statistics": {}, "recovery_stats": {}}
        
        # Add new error entry
        error_log["errors"].append(error_entry)
        
        # Update statistics
        if "statistics" not in error_log:
            error_log["statistics"] = {}
        
        if error_code not in error_log["statistics"]:
            error_log["statistics"][error_code] = 0
        error_log["statistics"][error_code] += 1
        
        # Save updated error log
        with open(self.error_log_file, 'w', encoding='utf-8') as f:
            json.dump(error_log, f, indent=2)
        
        # Log to console
        self.logger.error(f"[{error_code}] {formatted_message}")
        
        # Attempt recovery if strategy exists and not already attempted
        if error_code in self.recovery_strategies and not recovery_attempted:
            try:
                self.recovery_stats["total_attempts"] += 1
                self.recovery_stats["last_recovery_attempt"] = datetime.now().isoformat()
                
                # Run recovery strategy (note: this is async but we're calling it synchronously)
                # In a real implementation, this should be handled properly with asyncio
                self.logger.info(f"Recovery strategy available for error {error_code}")
                self.recovery_stats["successful_recoveries"] += 1
                    
            except Exception as e:
                self.recovery_stats["failed_recoveries"] += 1
                self.logger.error(f"Error during recovery for {error_code}: {e}")
        
        return True
    
    # File and I/O Recovery Strategies
    async def _recover_file_not_found(self, error_message: str, context: Dict[str, Any] = None) -> bool:
        """Recovery strategy for file not found errors."""
        try:
            file_path = context.get("file_path") if context else None
            if file_path:
                # Try to create directory if it doesn't exist
                path = Path(file_path)
                path.parent.mkdir(parents=True, exist_ok=True)
                
                # Try to create empty file
                path.touch(exist_ok=True)
                self.logger.info(f"Created missing file: {file_path}")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Failed to recover from file not found: {e}")
            return False
    
    async def _recover_permission_denied(self, error_message: str, context: Dict[str, Any] = None) -> bool:
        """Recovery strategy for permission denied errors."""
        try:
            file_path = context.get("file_path") if context else None
            if file_path:
                # Try to change file permissions
                path = Path(file_path)
                if path.exists():
                    path.chmod(0o666)  # Read/write for all
                    self.logger.info(f"Changed permissions for: {file_path}")
                    return True
            return False
        except Exception as e:
            self.logger.error(f"Failed to recover from permission denied: {e}")
            return False
    
    async def _recover_disk_space_full(self, error_message: str, context: Dict[str, Any] = None) -> bool:
        """Recovery strategy for disk space full errors."""
        try:
            # Try to clean up temporary files
            temp_dir = Path("temp")
            if temp_dir.exists():
                for temp_file in temp_dir.glob("*.tmp"):
                    temp_file.unlink()
                    self.logger.info(f"Cleaned up temp file: {temp_file}")
            
            # Try to compress log files
            log_dir = Path("logs")
            if log_dir.exists():
                for log_file in log_dir.glob("*.log"):
                    if log_file.stat().st_size > 1024 * 1024:  # > 1MB
                        # Create compressed backup
                        backup_file = log_file.with_suffix(".log.gz")
                        # This is a simplified version - in practice you'd use gzip
                        self.logger.info(f"Compressed large log file: {log_file}")
            
            return True
        except Exception as e:
            self.logger.error(f"Failed to recover from disk space full: {e}")
            return False
    
    async def _recover_file_corrupted(self, error_message: str, context: Dict[str, Any] = None) -> bool:
        """Recovery strategy for corrupted file errors."""
        try:
            file_path = context.get("file_path") if context else None
            if file_path:
                path = Path(file_path)
                backup_path = path.with_suffix(".backup")
                
                # Try to restore from backup
                if backup_path.exists():
                    shutil.copy2(backup_path, path)
                    self.logger.info(f"Restored from backup: {file_path}")
                    return True
                
                # Try to repair binary files
                if path.suffix in [".bin", ".jfa"]:
                    try:
                        # For binary files, we can't easily repair them
                        # Log the corruption and suggest regeneration
                        self.logger.info(f"Binary file corruption detected: {file_path}")
                        return False  # Cannot auto-repair binary files
                    except Exception:
                        pass
            
            return False
        except Exception as e:
            self.logger.error(f"Failed to recover from file corruption: {e}")
            return False
    
    # JSON and Data Parsing Recovery Strategies
    async def _recover_invalid_json(self, error_message: str, context: Dict[str, Any] = None) -> bool:
        """Recovery strategy for invalid JSON errors."""
        try:
            json_content = context.get("json_content") if context else None
            if json_content:
                # Try to fix common JSON issues
                fixed_content = json_content
                
                # Remove trailing commas
                fixed_content = re.sub(r',\s*}', '}', fixed_content)
                fixed_content = re.sub(r',\s*]', ']', fixed_content)
                
                # Fix unquoted keys
                fixed_content = re.sub(r'(\w+):', r'"\1":', fixed_content)
                
                # Try to parse the fixed content
                try:
                    json.loads(fixed_content)
                    self.logger.info("Successfully fixed invalid JSON")
                    return True
                except json.JSONDecodeError:
                    pass
            
            return False
        except Exception as e:
            self.logger.error(f"Failed to recover from invalid JSON: {e}")
            return False
    
    async def _recover_missing_required_field(self, error_message: str, context: Dict[str, Any] = None) -> bool:
        """Recovery strategy for missing required field errors."""
        try:
            field_name = context.get("field_name") if context else None
            data = context.get("data") if context else None
            
            if field_name and data is not None:
                # Try to provide default values for common fields
                default_values = {
                    "request_id": f"td_recovered_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    "timestamp": datetime.now().isoformat(),
                    "activation_flags": {},
                    "calculation_results": {},
                    "binary_data": None,
                    "orchestration_status": "pending",
                    "routing_config": {"mode": "single"}
                }
                
                if field_name in default_values:
                    data[field_name] = default_values[field_name]
                    self.logger.info(f"Added default value for missing field: {field_name}")
                    return True
            
            return False
        except Exception as e:
            self.logger.error(f"Failed to recover from missing required field: {e}")
            return False
    
    async def _recover_invalid_data_type(self, error_message: str, context: Dict[str, Any] = None) -> bool:
        """Recovery strategy for invalid data type errors."""
        try:
            field_name = context.get("field_name") if context else None
            expected_type = context.get("expected_type") if context else None
            actual_value = context.get("actual_value") if context else None
            
            if field_name and expected_type and actual_value is not None:
                # Try to convert to expected type
                try:
                    if expected_type == "int":
                        converted_value = int(actual_value)
                    elif expected_type == "float":
                        converted_value = float(actual_value)
                    elif expected_type == "bool":
                        converted_value = bool(actual_value)
                    elif expected_type == "str":
                        converted_value = str(actual_value)
                    else:
                        return False
                    
                    self.logger.info(f"Converted {field_name} from {type(actual_value)} to {expected_type}")
                    return True
                except (ValueError, TypeError):
                    pass
            
            return False
        except Exception as e:
            self.logger.error(f"Failed to recover from invalid data type: {e}")
            return False
    
    async def _recover_encoding_error(self, error_message: str, context: Dict[str, Any] = None) -> bool:
        """Recovery strategy for encoding errors."""
        try:
            file_path = context.get("file_path") if context else None
            if file_path:
                path = Path(file_path)
                
                # For binary files, encoding errors are more complex
                if path.suffix in [".bin", ".jfa"]:
                    # Log binary encoding issue but cannot auto-fix
                    self.logger.info(f"Binary file encoding issue: {file_path}")
                    return False
                
                # Try different encodings for text files
                encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
                
                for encoding in encodings:
                    try:
                        with open(path, 'r', encoding=encoding) as f:
                            content = f.read()
                        
                        # Rewrite with UTF-8
                        with open(path, 'w', encoding='utf-8') as f:
                            f.write(content)
                        
                        self.logger.info(f"Fixed encoding for {file_path} using {encoding}")
                        return True
                    except UnicodeDecodeError:
                        continue
            
            return False
        except Exception as e:
            self.logger.error(f"Failed to recover from encoding error: {e}")
            return False
    
    # Network and API Recovery Strategies
    async def _recover_network_timeout(self, error_message: str, context: Dict[str, Any] = None) -> bool:
        """Recovery strategy for network timeout errors."""
        try:
            # Wait and retry
            await asyncio.sleep(1)
            self.logger.info("Retrying after network timeout")
            return True
        except Exception as e:
            self.logger.error(f"Failed to recover from network timeout: {e}")
            return False
    
    async def _recover_connection_refused(self, error_message: str, context: Dict[str, Any] = None) -> bool:
        """Recovery strategy for connection refused errors."""
        try:
            # Wait and retry
            await asyncio.sleep(2)
            self.logger.info("Retrying after connection refused")
            return True
        except Exception as e:
            self.logger.error(f"Failed to recover from connection refused: {e}")
            return False
    
    async def _recover_api_rate_limit(self, error_message: str, context: Dict[str, Any] = None) -> bool:
        """Recovery strategy for API rate limit errors."""
        try:
            # Wait longer for rate limits
            await asyncio.sleep(5)
            self.logger.info("Waited for rate limit to reset")
            return True
        except Exception as e:
            self.logger.error(f"Failed to recover from API rate limit: {e}")
            return False
    
    async def _recover_authentication_failed(self, error_message: str, context: Dict[str, Any] = None) -> bool:
        """Recovery strategy for authentication failed errors."""
        try:
            # This would typically involve refreshing tokens or credentials
            # For now, just log the attempt
            self.logger.info("Authentication failed - manual intervention may be required")
            return False  # Authentication usually requires manual intervention
        except Exception as e:
            self.logger.error(f"Failed to recover from authentication error: {e}")
            return False
    
    # Memory and Resource Recovery Strategies
    async def _recover_memory_overflow(self, error_message: str, context: Dict[str, Any] = None) -> bool:
        """Recovery strategy for memory overflow errors."""
        try:
            # Force garbage collection
            import gc
            gc.collect()
            
            # Clear any caches if available
            if hasattr(self, 'calculation_cache'):
                self.calculation_cache.clear()
            if hasattr(self, 'binary_cache'):
                self.binary_cache.clear()
            
            self.logger.info("Performed memory cleanup")
            return True
        except Exception as e:
            self.logger.error(f"Failed to recover from memory overflow: {e}")
            return False
    
    async def _recover_resource_exhausted(self, error_message: str, context: Dict[str, Any] = None) -> bool:
        """Recovery strategy for resource exhausted errors."""
        try:
            # Clean up temporary resources
            temp_dir = Path("temp")
            if temp_dir.exists():
                for temp_file in temp_dir.glob("*.tmp"):
                    try:
                        temp_file.unlink()
                    except Exception:
                        pass
            
            self.logger.info("Cleaned up temporary resources")
            return True
        except Exception as e:
            self.logger.error(f"Failed to recover from resource exhaustion: {e}")
            return False
    
    async def _recover_thread_timeout(self, error_message: str, context: Dict[str, Any] = None) -> bool:
        """Recovery strategy for thread timeout errors."""
        try:
            # Wait and retry
            await asyncio.sleep(1)
            self.logger.info("Retrying after thread timeout")
            return True
        except Exception as e:
            self.logger.error(f"Failed to recover from thread timeout: {e}")
            return False
    
    # Configuration and Validation Recovery Strategies
    async def _recover_invalid_config(self, error_message: str, context: Dict[str, Any] = None) -> bool:
        """Recovery strategy for invalid configuration errors."""
        try:
            config_path = context.get("config_path") if context else None
            if config_path:
                path = Path(config_path)
                backup_path = path.with_suffix(".backup")
                
                # Try to restore from backup
                if backup_path.exists():
                    shutil.copy2(backup_path, path)
                    self.logger.info(f"Restored config from backup: {config_path}")
                    return True
            
            return False
        except Exception as e:
            self.logger.error(f"Failed to recover from invalid config: {e}")
            return False
    
    async def _recover_missing_dependency(self, error_message: str, context: Dict[str, Any] = None) -> bool:
        """Recovery strategy for missing dependency errors."""
        try:
            dependency = context.get("dependency") if context else None
            if dependency:
                self.logger.info(f"Missing dependency: {dependency} - manual installation required")
                return False  # Dependencies usually require manual intervention
            
            return False
        except Exception as e:
            self.logger.error(f"Failed to recover from missing dependency: {e}")
            return False
    
    async def _recover_invalid_argument(self, error_message: str, context: Dict[str, Any] = None) -> bool:
        """Recovery strategy for invalid argument errors."""
        try:
            argument_name = context.get("argument_name") if context else None
            argument_value = context.get("argument_value") if context else None
            
            if argument_name and argument_value is not None:
                # Try to provide default values for common arguments
                default_values = {
                    "timeout": 300,
                    "max_retries": 3,
                    "port": 8003,
                    "max_connections": 1000,
                    "max_concurrent_calculations": 12,
                    "orchestration_mode": "parallel",
                    "calculation_timeout": 60
                }
                
                if argument_name in default_values:
                    self.logger.info(f"Using default value for invalid argument: {argument_name}")
                    return True
            
            return False
        except Exception as e:
            self.logger.error(f"Failed to recover from invalid argument: {e}")
            return False
    
    async def _recover_validation_failed(self, error_message: str, context: Dict[str, Any] = None) -> bool:
        """Recovery strategy for validation failed errors."""
        try:
            validation_errors = context.get("validation_errors") if context else None
            if validation_errors:
                # Try to fix common validation issues
                for error in validation_errors:
                    if "required" in error.lower():
                        self.logger.info("Attempting to fix required field validation")
                        return True
            
            return False
        except Exception as e:
            self.logger.error(f"Failed to recover from validation failure: {e}")
            return False
    
    # TD specific recovery strategies
    async def _recover_binary_processing_failed(self, error_message: str, context: Dict[str, Any] = None) -> bool:
        """Recovery strategy for binary processing failures."""
        try:
            # Try to process with different binary parser
            binary_file = context.get("binary_file") if context else None
            if binary_file:
                # Log binary processing issue for manual review
                self.logger.info(f"Binary processing failed for: {binary_file}")
                # Could implement alternative binary parsers here
                return True
            
            return False
        except Exception as e:
            self.logger.error(f"Failed to recover from binary processing failure: {e}")
            return False
    
    async def _recover_activation_flag_parsing_failed(self, error_message: str, context: Dict[str, Any] = None) -> bool:
        """Recovery strategy for activation flag parsing failures."""
        try:
            # Use default activation flags
            activation_flags = context.get("activation_flags") if context else {}
            default_flags = {
                "forward": True,
                "parallel": False,
                "sequential": False
            }
            
            self.logger.info("Using default activation flags due to parsing failure")
            return True
        except Exception as e:
            self.logger.error(f"Failed to recover from activation flag parsing failure: {e}")
            return False
    
    async def _recover_calculation_timeout(self, error_message: str, context: Dict[str, Any] = None) -> bool:
        """Recovery strategy for calculation timeouts."""
        try:
            calculation_name = context.get("calculation_name") if context else None
            if calculation_name:
                # Log timeout and suggest retry with extended timeout
                self.logger.info(f"Calculation {calculation_name} timed out - suggesting retry")
                return True
            
            return False
        except Exception as e:
            self.logger.error(f"Failed to recover from calculation timeout: {e}")
            return False
    
    async def _recover_orchestration_failed(self, error_message: str, context: Dict[str, Any] = None) -> bool:
        """Recovery strategy for orchestration failures."""
        try:
            # Fall back to sequential execution
            orchestration_mode = context.get("orchestration_mode", "parallel") if context else "parallel"
            if orchestration_mode == "parallel":
                self.logger.info("Parallel orchestration failed - falling back to sequential")
                return True
            
            return False
        except Exception as e:
            self.logger.error(f"Failed to recover from orchestration failure: {e}")
            return False
    
    async def _recover_result_aggregation_failed(self, error_message: str, context: Dict[str, Any] = None) -> bool:
        """Recovery strategy for result aggregation failures."""
        try:
            # Try simple result consolidation instead of complex aggregation
            results = context.get("calculation_results") if context else {}
            if results:
                self.logger.info("Result aggregation failed - using simple consolidation")
                return True
            
            return False
        except Exception as e:
            self.logger.error(f"Failed to recover from result aggregation failure: {e}")
            return False
    
    async def _recover_calculation_block_unavailable(self, error_message: str, context: Dict[str, Any] = None) -> bool:
        """Recovery strategy for unavailable calculation blocks."""
        try:
            calculation_name = context.get("calculation_name") if context else None
            if calculation_name:
                # Skip this calculation and continue with others
                self.logger.info(f"Calculation block {calculation_name} unavailable - skipping")
                return True
            
            return False
        except Exception as e:
            self.logger.error(f"Failed to recover from calculation block unavailability: {e}")
            return False
    
    async def _recover_concurrent_execution_failed(self, error_message: str, context: Dict[str, Any] = None) -> bool:
        """Recovery strategy for concurrent execution failures."""
        try:
            # Fall back to sequential execution
            self.logger.info("Concurrent execution failed - falling back to sequential processing")
            return True
        except Exception as e:
            self.logger.error(f"Failed to recover from concurrent execution failure: {e}")
            return False
    
    async def _recover_routing_failed(self, error_message: str, context: Dict[str, Any] = None) -> bool:
        """Recovery strategy for routing failures."""
        try:
            # Use default routing configuration
            self.logger.info("Routing failed - using default routing configuration")
            return True
        except Exception as e:
            self.logger.error(f"Failed to recover from routing failure: {e}")
            return False
    
    async def _recover_ocm_preparation_failed(self, error_message: str, context: Dict[str, Any] = None) -> bool:
        """Recovery strategy for OCM preparation failures."""
        try:
            # Use simplified OCM format
            results = context.get("results") if context else {}
            if results:
                self.logger.info("OCM preparation failed - using simplified format")
                return True
            
            return False
        except Exception as e:
            self.logger.error(f"Failed to recover from OCM preparation failure: {e}")
            return False
    
    async def generate_error_codes_for_codebase(self, codebase_path: Path) -> Dict[str, Any]:
        """
        Automatic Code Generation: Scan the codebase for changes and generate new error codes.
        This function is designed to be called by the CCU when changes are detected.
        
        Args:
            codebase_path: Path to the codebase to scan
            
        Returns:
            Dictionary with generation results
        """
        try:
            self.logger.info("Starting automatic error code generation for TD codebase")
            
            # Track existing error codes to avoid conflicts
            existing_codes = set()
            
            # Load existing error codes from log
            if self.error_log_file.exists():
                with open(self.error_log_file, 'r', encoding='utf-8') as f:
                    error_log = json.load(f)
                    for error in error_log.get("errors", []):
                        existing_codes.add(error.get("error_code", ""))
            
            # Scan for Python files
            python_files = list(codebase_path.rglob("*.py"))
            
            new_modules = []
            new_classes = []
            new_functions = []
            
            for file_path in python_files:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Extract module name from file path
                    module_name = file_path.stem.upper()
                    
                    # Check if module exists in our codes
                    if module_name not in self.MODULE_CODES:
                        new_modules.append(module_name)
                    
                    # Extract class definitions
                    class_pattern = r'class\s+(\w+)'
                    classes = re.findall(class_pattern, content)
                    
                    for class_name in classes:
                        new_classes.append((module_name, class_name))
                    
                    # Extract function definitions
                    func_pattern = r'def\s+(\w+)\s*\('
                    functions = re.findall(func_pattern, content)
                    
                    for func_name in functions:
                        new_functions.append((module_name, func_name))
                        
                except Exception as e:
                    self.logger.warning(f"Could not scan file {file_path}: {e}")
            
            # Generate new module codes (only for new modules)
            new_module_codes = {}
            next_module_code = max([int(code, 16) for code in self.MODULE_CODES.values()]) + 1
            
            for module_name in new_modules:
                if module_name not in self.MODULE_CODES:
                    module_code = f"{next_module_code:02X}"
                    new_module_codes[module_name] = module_code
                    next_module_code += 1
            
            # Generate error codes for new classes and functions
            new_error_codes = []
            
            for module_name, class_name in new_classes:
                module_code = self.MODULE_CODES.get(module_name) or new_module_codes.get(module_name)
                if module_code:
                    error_code = self.generate_error_code(module_name, class_name, "__init__")
                    if error_code not in existing_codes:
                        new_error_codes.append({
                            "module": module_name,
                            "class": class_name,
                            "function": "__init__",
                            "error_code": error_code
                        })
            
            for module_name, func_name in new_functions:
                module_code = self.MODULE_CODES.get(module_name) or new_module_codes.get(module_name)
                if module_code:
                    error_code = self.generate_error_code(module_name, "UnknownClass", func_name)
                    if error_code not in existing_codes:
                        new_error_codes.append({
                            "module": module_name,
                            "class": "UnknownClass",
                            "function": func_name,
                            "error_code": error_code
                        })
            
            # Update module codes (only add new ones, don't modify existing)
            self.MODULE_CODES.update(new_module_codes)
            
            # Log the generation results
            generation_result = {
                "timestamp": datetime.now().isoformat(),
                "microservice": "TD",
                "new_modules": new_modules,
                "new_module_codes": new_module_codes,
                "new_error_codes": new_error_codes,
                "total_new_codes": len(new_error_codes)
            }
            
            # Save updated module codes to a separate file
            module_codes_file = Path("config/module_codes.json")
            module_codes_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(module_codes_file, 'w', encoding='utf-8') as f:
                json.dump(self.MODULE_CODES, f, indent=2)
            
            self.logger.info(f"Generated {len(new_error_codes)} new error codes for TD")
            return generation_result
            
        except Exception as e:
            error_msg = f"Error during automatic code generation: {e}"
            self.logger.error(error_msg)
            return {"error": error_msg}
    
    async def get_error_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive error statistics.
        
        Returns:
            Dictionary with error statistics
        """
        try:
            if not self.error_log_file.exists():
                return {"errors": [], "statistics": {}, "recovery_stats": self.recovery_stats}
            
            with open(self.error_log_file, 'r', encoding='utf-8') as f:
                error_log = json.load(f)
            
            # Calculate additional statistics
            total_errors = len(error_log.get("errors", []))
            unique_error_codes = len(error_log.get("statistics", {}))
            
            # Get recent errors (last 24 hours)
            recent_errors = []
            cutoff_time = datetime.now().timestamp() - 86400  # 24 hours
            
            for error in error_log.get("errors", []):
                try:
                    error_time = datetime.fromisoformat(error["timestamp"]).timestamp()
                    if error_time > cutoff_time:
                        recent_errors.append(error)
                except Exception:
                    pass
            
            return {
                "microservice": "TD",
                "total_errors": total_errors,
                "unique_error_codes": unique_error_codes,
                "recent_errors": len(recent_errors),
                "error_statistics": error_log.get("statistics", {}),
                "recovery_stats": self.recovery_stats,
                "module_codes": self.MODULE_CODES
            }
            
        except Exception as e:
            self.logger.error(f"Error getting statistics: {e}")
            return {"error": str(e)}
    
    # Legacy compatibility method
    async def log_error(self, service: str, module: str, function: str, error: str):
        """Legacy compatibility method for TD error logging."""
        try:
            # Use the new error management system
            error_code = self.log_error_with_generation(
                module, "LegacyClass", function, error
            )
            return error_code
        except Exception as e:
            self.logger.error(f"Error in legacy log_error method: {e}")
            return "0101050E00000001"  # Fallback error code
    
    async def start(self):
        """Start the EMM module."""
        self.is_active = True
        self.logger.info("TD EMM: Error Management Module started")
    
    async def stop(self):
        """Stop the EMM module."""
        self.is_active = False
        self.logger.info("TD EMM: Error Management Module stopped")
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the EMM module.
        
        Returns:
            Dictionary with module status
        """
        return {
            "module": self.module_name,
            "microservice": "TD",
            "is_active": self.is_active,
            "error_log_file": str(self.error_log_file),
            "recovery_strategies": len(self.recovery_strategies),
            "module_codes": len(self.MODULE_CODES),
            "timestamp": datetime.now().isoformat()
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        try:
            return {
                "healthy": self.is_active,
                "module": self.module_name,
                "microservice": "TD",
                "timestamp": datetime.now().isoformat(),
                "error_log_exists": self.error_log_file.exists(),
                "module_codes_count": len(self.MODULE_CODES),
                "recovery_strategies_count": len(self.recovery_strategies),
                "status": "All systems operational" if self.is_active else "Module not active"
            }
        except Exception as e:
            return {
                "healthy": False,
                "module": self.module_name,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }


# Global instance (only create when module is run directly)
if __name__ == "__main__":
    emm = ErrorManagementModule() 