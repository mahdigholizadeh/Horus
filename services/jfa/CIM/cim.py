"""
Configuration Interface Module (CIM) for JFA Microservice

This module handles configuration management:
- Configuration loading and validation
- Dynamic configuration updates
- Settings persistence
- Environment variable handling
"""

import logging
import asyncio
import json
import os
from typing import Dict, Any
from datetime import datetime


class ConfigurationInterfaceModule:
    """Configuration Interface Module for JFA"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.module_name = "CIM"
        self.is_active = False
        
        # Default configuration
        self.config = {
            "service_name": "JFA",
            "version": "1.0.0",
            "debug": False,
            "max_requests": 1000,
            "timeout": 300,
            "logging": {
                "level": "INFO",
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "file": "jfa.log"
            },
            "processing": {
                "max_template_size": 10485760,
                "max_depth": 10,
                "timeout": 30
            },
            "api": {
                "port": 8001,
                "host": "0.0.0.0",
                "debug": False
            },
            "database": {
                "url": "sqlite:///jfa.db",
                "pool_size": 10
            }
        }
        
        self.stats = {
            "config_loads": 0,
            "config_updates": 0,
            "last_activity": None
        }
    
    async def start(self):
        self.is_active = True
        # Load environment variables
        await self._load_environment_variables()
        self.logger.info(f"{self.module_name} started successfully")
    
    async def stop(self):
        self.is_active = False
        self.logger.info(f"{self.module_name} stopped successfully")
    
    async def _load_environment_variables(self):
        """Load configuration from environment variables."""
        try:
            # Check for JFA_LOG_LEVEL environment variable
            if "JFA_LOG_LEVEL" in os.environ:
                self.config["logging"]["level"] = os.environ["JFA_LOG_LEVEL"]
            
            # Check for other environment variables
            if "JFA_API_PORT" in os.environ:
                try:
                    self.config["api"]["port"] = int(os.environ["JFA_API_PORT"])
                except ValueError:
                    pass
            
            if "JFA_DEBUG" in os.environ:
                self.config["debug"] = os.environ["JFA_DEBUG"].lower() in ["true", "1", "yes"]
                self.config["api"]["debug"] = self.config["debug"]
            
            if "JFA_MAX_REQUESTS" in os.environ:
                try:
                    self.config["max_requests"] = int(os.environ["JFA_MAX_REQUESTS"])
                except ValueError:
                    pass
            
            if "JFA_TIMEOUT" in os.environ:
                try:
                    self.config["timeout"] = int(os.environ["JFA_TIMEOUT"])
                except ValueError:
                    pass
                    
        except Exception as e:
            self.logger.error(f"Error loading environment variables: {e}")
    
    async def load_configuration(self, config_path: str = None) -> Dict[str, Any]:
        """Load configuration from file or environment."""
        try:
            self.stats["config_loads"] += 1
            self.stats["last_activity"] = datetime.now()
            
            # Load environment variables
            await self._load_environment_variables()
            
            # If config_path is provided, try to load from file
            if config_path and os.path.exists(config_path):
                try:
                    with open(config_path, 'r') as f:
                        file_config = json.load(f)
                    self.config.update(file_config)
                except Exception as e:
                    self.logger.error(f"Error loading config file {config_path}: {e}")
            
            return self.config
            
        except Exception as e:
            self.logger.error(f"Error loading configuration: {e}")
            return {}
    
    def get_configuration(self) -> Dict[str, Any]:
        """Get current configuration."""
        return self.config
    
    def get_config_value(self, key: str, default: Any = None) -> Any:
        """Get a specific configuration value using dot notation."""
        try:
            keys = key.split('.')
            value = self.config
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    async def set_config_value(self, key: str, value: Any) -> Dict[str, Any]:
        """Set a specific configuration value using dot notation."""
        try:
            keys = key.split('.')
            config = self.config
            
            # Navigate to the parent of the target key
            for k in keys[:-1]:
                if k not in config:
                    config[k] = {}
                config = config[k]
            
            # Set the value
            config[keys[-1]] = value
            
            self.stats["config_updates"] += 1
            self.stats["last_activity"] = datetime.now()
            
            return {
                "success": True,
                "key": key,
                "value": value,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            self.logger.error(f"Error setting config value {key}: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def export_configuration(self) -> Dict[str, Any]:
        """Export current configuration."""
        try:
            return {
                "success": True,
                "configuration": self.config.copy(),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def update_configuration(self, updates: Dict[str, Any]) -> bool:
        """Update configuration with new values."""
        try:
            self.config.update(updates)
            self.stats["config_updates"] += 1
            self.stats["last_activity"] = datetime.now()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating configuration: {e}")
            return False
    
    async def validate_configuration(self, config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Validate configuration values."""
        try:
            config_to_validate = config or self.config
            validation_results = {
                "valid": True,
                "errors": [],
                "warnings": [],
                "validated_config": config_to_validate
            }
            
            # Validate required fields
            required_fields = ["service_name", "version"]
            for field in required_fields:
                if field not in config_to_validate:
                    validation_results["valid"] = False
                    validation_results["errors"].append(f"Missing required field: {field}")
            
            # Validate logging section
            if "logging" in config_to_validate:
                logging_config = config_to_validate["logging"]
                if "level" in logging_config:
                    valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
                    if logging_config["level"] not in valid_levels:
                        validation_results["warnings"].append(f"Invalid log level: {logging_config['level']}")
            
            # Validate processing section
            if "processing" in config_to_validate:
                processing_config = config_to_validate["processing"]
                if "max_template_size" in processing_config:
                    if not isinstance(processing_config["max_template_size"], int):
                        validation_results["valid"] = False
                        validation_results["errors"].append("max_template_size must be an integer")
                    elif processing_config["max_template_size"] <= 0:
                        validation_results["warnings"].append("max_template_size should be positive")
            
            # Validate API section
            if "api" in config_to_validate:
                api_config = config_to_validate["api"]
                if "port" in api_config:
                    if not isinstance(api_config["port"], int):
                        validation_results["valid"] = False
                        validation_results["errors"].append("api.port must be an integer")
                    elif api_config["port"] <= 0 or api_config["port"] > 65535:
                        validation_results["warnings"].append("api.port should be between 1 and 65535")
            
            # Validate data types
            if "max_requests" in config_to_validate:
                if not isinstance(config_to_validate["max_requests"], int):
                    validation_results["valid"] = False
                    validation_results["errors"].append("max_requests must be an integer")
                elif config_to_validate["max_requests"] <= 0:
                    validation_results["warnings"].append("max_requests should be positive")
            
            if "timeout" in config_to_validate:
                if not isinstance(config_to_validate["timeout"], int):
                    validation_results["valid"] = False
                    validation_results["errors"].append("timeout must be an integer")
                elif config_to_validate["timeout"] <= 0:
                    validation_results["warnings"].append("timeout should be positive")
            
            if "debug" in config_to_validate:
                if not isinstance(config_to_validate["debug"], bool):
                    validation_results["valid"] = False
                    validation_results["errors"].append("debug must be a boolean")
            
            # Validate version format
            if "version" in config_to_validate:
                version = config_to_validate["version"]
                if not isinstance(version, str) or "." not in version:
                    validation_results["warnings"].append("version should be in format X.Y.Z")
            
            return validation_results
            
        except Exception as e:
            return {
                "valid": False,
                "errors": [f"Validation error: {str(e)}"],
                "warnings": [],
                "validated_config": config_to_validate if 'config_to_validate' in locals() else {}
            }
    
    async def reload_configuration(self) -> Dict[str, Any]:
        """Reload configuration from source."""
        try:
            # Load environment variables
            await self._load_environment_variables()
            
            self.stats["config_loads"] += 1
            self.stats["last_activity"] = datetime.now()
            
            # Validate the reloaded configuration
            validation_result = await self.validate_configuration()
            
            return {
                "success": validation_result.get("valid", False),
                "config": self.config,
                "validation": validation_result,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def get_status(self) -> Dict[str, Any]:
        return {
            "module": self.module_name,
            "is_active": self.is_active,
            "statistics": self.stats,
            "config": self.config,
            "timestamp": datetime.now().isoformat()
        }
    
    async def health_check(self) -> Dict[str, Any]:
        try:
            return {
                "healthy": self.is_active,
                "module": self.module_name,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "healthy": False,
                "module": self.module_name,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            } 