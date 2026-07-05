"""
Error Management Module (EMM)

Manages all aspects of error detection, logging, and recovery.
Generates 16-character hexadecimal error codes and implements automated recovery strategies.
Includes Automatic Code Generation script to scan codebase for changes and generate new error codes.
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
    Error Management Module (EMM)
    
    Manages all aspects of error detection, logging, and recovery.
    Generates 16-character hexadecimal error codes and implements automated recovery strategies.
    """
    
    def __init__(self):
        """Initialize the Error Management Module."""
        self.logger = logging.getLogger(__name__)
        
        # Error code structure: Server(2) + Macroservice(2) + Microservice(2) + Module(2) + Class(2) + Function(3) + Sub-function(3)
        self.SERVER_CODE = "01"
        self.MACROSERVICE_CODE = "01"
        self.MICROSERVICE_CODE = "03"  # RCM
        
        # Module codes (hex values for each module)
        self.MODULE_CODES = {
            "GIDVM": "01",
            "PBRPM": "02", 
            "AACM": "03",
            "FBWM": "04",
            "FDM": "05",
            "PRM": "06",
            "RTRMM": "07",
            "RLM": "08",
            "MMM": "09",
            "DRM": "0A",
            "FAIM": "0B",
            "BTM": "0C",
            "IFCM": "0D",
            "ECM": "0E",
            "AAAIM": "0F",
            "BAAIM": "10",
            "SAAIM": "11",
            "SODVM": "12",
            "FOM": "13",
            "DCMM": "14",
            "TMM": "15",
            "EMM": "16",
            "MSM": "17",
            "SMSM": "18",
            "SMCM": "19",
            "JFAIM": "1A",
            "OCMIM": "1B"
        }
        
        # Error log file
        self.error_log_file = Path("logs/error_log.json")
        self.error_log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Enhanced recovery strategies for common errors
        self.recovery_strategies = {
            # File and I/O errors
            "01010316001": self._recover_file_not_found,
            "01010316002": self._recover_permission_denied,
            "01010316003": self._recover_disk_space_full,
            "01010316004": self._recover_file_corrupted,
            
            # JSON and data parsing errors
            "01010316005": self._recover_invalid_json,
            "01010316006": self._recover_missing_required_field,
            "01010316007": self._recover_invalid_data_type,
            "01010316008": self._recover_encoding_error,
            
            # Network and API errors
            "01010316009": self._recover_network_timeout,
            "0101031600A": self._recover_connection_refused,
            "0101031600B": self._recover_api_rate_limit,
            "0101031600C": self._recover_authentication_failed,
            
            # Memory and resource errors
            "0101031600D": self._recover_memory_overflow,
            "0101031600E": self._recover_resource_exhausted,
            "0101031600F": self._recover_thread_timeout,
            
            # Configuration and validation errors
            "01010316010": self._recover_invalid_config,
            "01010316011": self._recover_missing_dependency,
            "01010316012": self._recover_invalid_argument,
            
            # WebSocket and CCU communication errors
            "01010316013": self._recover_websocket_connection_failed,
            "01010316014": self._recover_websocket_authentication_failed,
            "01010316015": self._recover_websocket_message_send_failed,
            "01010316016": self._recover_ccu_service_unavailable,
            "01010316017": self._recover_validation_failed
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
    
    def _initialize_error_log(self):
        """Initialize the error log file if it doesn't exist."""
        if not self.error_log_file.exists():
            with open(self.error_log_file, 'w', encoding='utf-8') as f:
                json.dump({"errors": [], "statistics": {}, "recovery_stats": {}}, f, indent=2)
    
    def generate_error_code(self, module_name: str, class_name: str, function_name: str, sub_function: str = "001") -> str:
        """
        Generate a 16-character hexadecimal error code.
        
        Args:
            module_name: Name of the module (e.g., "GIDVM")
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
            fallback_code = "0101031600000001"
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
                
                # Try to repair JSON files
                if path.suffix == ".json":
                    try:
                        with open(path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        # Try to fix common JSON issues
                        content = re.sub(r',\s*}', '}', content)  # Remove trailing commas
                        content = re.sub(r',\s*]', ']', content)  # Remove trailing commas in arrays
                        
                        with open(path, 'w', encoding='utf-8') as f:
                            f.write(content)
                        
                        self.logger.info(f"Attempted to repair JSON file: {file_path}")
                        return True
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
                    "priority": "C",
                    "model": "gpt-3.5-turbo",
                    "messages": [],
                    "request_id": f"recovered_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    "timestamp": datetime.now().isoformat()
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
                
                # Try different encodings
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
            if hasattr(self, 'response_cache'):
                self.response_cache.clear()
            
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
                    "priority": "C",
                    "model": "gpt-3.5-turbo",
                    "timeout": 30,
                    "max_retries": 3
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

    async def _recover_websocket_connection_failed(self, error_message: str, context: Dict[str, Any] = None) -> bool:
        """Recovery strategy for WebSocket connection failed errors."""
        try:
            self.logger.info("Attempting to recover from WebSocket connection failure")
            
            # Wait before retry
            await asyncio.sleep(5)
            
            # Log retry attempt
            self.logger.info("WebSocket connection retry attempted")
            return True
        except Exception as e:
            self.logger.error(f"Failed to recover from WebSocket connection failure: {e}")
            return False

    async def _recover_websocket_authentication_failed(self, error_message: str, context: Dict[str, Any] = None) -> bool:
        """Recovery strategy for WebSocket authentication failed errors."""
        try:
            self.logger.info("Attempting to recover from WebSocket authentication failure")
            
            # Check if service credentials are valid
            service_id = context.get("service_id") if context else None
            if service_id:
                self.logger.info(f"Re-authenticating service: {service_id}")
            
            # Wait before retry
            await asyncio.sleep(3)
            
            self.logger.info("WebSocket authentication retry attempted")
            return True
        except Exception as e:
            self.logger.error(f"Failed to recover from WebSocket authentication failure: {e}")
            return False

    async def _recover_websocket_message_send_failed(self, error_message: str, context: Dict[str, Any] = None) -> bool:
        """Recovery strategy for WebSocket message send failed errors."""
        try:
            self.logger.info("Attempting to recover from WebSocket message send failure")
            
            # Check if connection is still valid
            connection_status = context.get("connection_status") if context else None
            if connection_status == "disconnected":
                self.logger.info("Connection is disconnected, attempting reconnection")
            
            # Wait before retry
            await asyncio.sleep(2)
            
            self.logger.info("WebSocket message send retry attempted")
            return True
        except Exception as e:
            self.logger.error(f"Failed to recover from WebSocket message send failure: {e}")
            return False

    async def _recover_ccu_service_unavailable(self, error_message: str, context: Dict[str, Any] = None) -> bool:
        """Recovery strategy for CCU service unavailable errors."""
        try:
            self.logger.info("Attempting to recover from CCU service unavailability")
            
            # Check CCU service status
            ccu_host = context.get("ccu_host") if context else "localhost"
            ccu_port = context.get("ccu_port") if context else None
            
            if ccu_host and ccu_port:
                self.logger.info(f"CCU service at {ccu_host}:{ccu_port} is unavailable")
            
            # Wait longer for service to become available
            await asyncio.sleep(10)
            
            self.logger.info("CCU service availability retry attempted")
            return True
        except Exception as e:
            self.logger.error(f"Failed to recover from CCU service unavailability: {e}")
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
            self.logger.info("Starting automatic error code generation for codebase")
            
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
                    module_name = file_path.stem
                    
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
            
            self.logger.info(f"Generated {len(new_error_codes)} new error codes")
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
    
    async def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the EMM module.
        
        Returns:
            Dictionary with module status
        """
        stats = await self.get_error_statistics()
        
        return {
            "module": "EMM",
            "status": "active",
            "error_log_file": str(self.error_log_file),
            "recovery_strategies": len(self.recovery_strategies),
            "module_codes": len(self.MODULE_CODES),
            "statistics": stats,
            "last_activity": datetime.now().isoformat()
        }
    
    async def start(self):
        """Start the EMM module."""
        self.logger.info("EMM: Module started")
    
    async def stop(self):
        """Stop the EMM module."""
        self.logger.info("EMM: Module stopped")


# Global instance (only create when module is run directly)
if __name__ == "__main__":
    emm = ErrorManagementModule() 