"""
Path Management Module (PMM) for CCU

This module provides centralized path management for the entire microservices architecture.
It handles:
- Cross-platform path resolution (Windows/Linux)
- Installation root detection and management
- Environment-specific path configurations (dev/staging/production)
- Service-specific directory structures
- Path distribution to dependent microservices
- Dynamic path reconfiguration

Core Responsibilities:
- Detect installation root directory
- Resolve all system-wide paths from central configuration
- Provide path resolution APIs to other microservices
- Handle cross-platform compatibility
- Support hot-reloading of path configurations
- Validate path accessibility and permissions
"""

import os
import sys
import json
import logging
from pathlib import Path, PurePath
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, asdict
from enum import Enum
import platform
import asyncio


class Environment(Enum):
    """Environment types for path configuration."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class PathType(Enum):
    """Types of paths managed by PMM."""
    ABSOLUTE = "absolute"
    RELATIVE_TO_ROOT = "relative_to_root"
    RELATIVE_TO_SERVICE = "relative_to_service"
    SYSTEM = "system"


@dataclass
class PathConfig:
    """Configuration for a managed path."""
    path: str
    path_type: PathType
    description: str
    create_if_missing: bool = True
    required_permissions: Optional[str] = None
    service_scope: Optional[str] = None  # Which service this path belongs to


@dataclass
class ServicePaths:
    """Standard directory structure for a microservice."""
    base: Path
    input: Path
    output: Path
    temp: Path
    logs: Path
    cache: Path
    config: Path
    error: Path
    archive: Path


class PathManagementModule:
    """
    Path Management Module (PMM)
    
    Provides centralized path management for the entire microservices ecosystem.
    """
    
    def __init__(self, installation_root: Optional[Path] = None, environment: Environment = Environment.DEVELOPMENT):
        """
        Initialize the Path Management Module.
        
        Args:
            installation_root: Root directory of the installation. If None, auto-detected.
            environment: Current environment (development, staging, production)
        """
        self.logger = logging.getLogger(__name__)
        self.environment = environment
        self.platform = platform.system().lower()
        
        # Auto-detect installation root if not provided
        self.installation_root = installation_root or self._detect_installation_root()
        
        # Path configurations
        self.path_configs: Dict[str, PathConfig] = {}
        self.service_paths: Dict[str, ServicePaths] = {}
        self.resolved_paths: Dict[str, Path] = {}
        
        # Load path configurations
        self._load_path_configurations()
        
        # Initialize service-specific paths
        self._initialize_service_paths()
        
        # Validate paths
        self._validate_paths()
        
        self.logger.info(f"PMM initialized - Root: {self.installation_root}, Platform: {self.platform}, Environment: {self.environment.value}")
    
    def _detect_installation_root(self) -> Path:
        """
        Auto-detect the installation root directory.
        
        Returns:
            Path to the installation root
        """
        try:
            # Method 1: Look for marker files that indicate root
            current_path = Path(__file__).resolve()
            
            # Traverse up the directory tree looking for installation markers
            markers = [
                "README.md",
                "LICENSE.txt",
                "services",
                ".git",
            ]
            
            for parent in current_path.parents:
                if any((parent / marker).exists() for marker in markers):
                    self.logger.info(f"Detected installation root via markers: {parent}")
                    return parent
            
            if "HORUS_ROOT" in os.environ:
                root = Path(os.environ["HORUS_ROOT"])
                if root.exists():
                    self.logger.info(f"Using installation root from environment: {root}")
                    return root
            
            default_root = current_path.parents[3]
            self.logger.warning(f"Using default installation root: {default_root}")
            return default_root
            
        except Exception as e:
            self.logger.error(f"Failed to detect installation root: {e}")
            # Fallback to current working directory
            return Path.cwd()
    
    def _load_path_configurations(self):
        """Load path configurations from JSON files."""
        try:
            # Load global path configuration
            global_config_path = self.installation_root / "config" / "paths" / "global_paths.json"
            if global_config_path.exists():
                with open(global_config_path, 'r') as f:
                    global_config = json.load(f)
                    self._parse_path_config(global_config, "global")
            else:
                # Create default configuration
                self._create_default_path_configuration()
            
            # Load environment-specific configurations
            env_config_path = self.installation_root / "config" / "paths" / f"{self.environment.value}_paths.json"
            if env_config_path.exists():
                with open(env_config_path, 'r') as f:
                    env_config = json.load(f)
                    self._parse_path_config(env_config, "environment")
            
            # Load platform-specific configurations
            platform_config_path = self.installation_root / "config" / "paths" / f"{self.platform}_paths.json"
            if platform_config_path.exists():
                with open(platform_config_path, 'r') as f:
                    platform_config = json.load(f)
                    self._parse_path_config(platform_config, "platform")
            
        except Exception as e:
            self.logger.error(f"Failed to load path configurations: {e}")
            self._create_default_path_configuration()
    
    def _create_default_path_configuration(self):
        """Create default path configuration if none exists."""
        try:
            # Create default global paths
            default_paths = {
                "global": {
                    "description": "Global system paths",
                    "paths": {
                        "root": {
                            "path": "",
                            "path_type": "absolute",
                            "description": "Installation root directory",
                            "create_if_missing": False
                        },
                        "data": {
                            "path": "data",
                            "path_type": "relative_to_root",
                            "description": "Global data directory",
                            "create_if_missing": True
                        },
                        "logs": {
                            "path": "logs",
                            "path_type": "relative_to_root", 
                            "description": "Global logs directory",
                            "create_if_missing": True
                        },
                        "temp": {
                            "path": "temp",
                            "path_type": "relative_to_root",
                            "description": "Global temporary directory",
                            "create_if_missing": True
                        },
                        "cache": {
                            "path": "cache",
                            "path_type": "relative_to_root",
                            "description": "Global cache directory",
                            "create_if_missing": True
                        },
                        "input": {
                            "path": "input",
                            "path_type": "relative_to_root",
                            "description": "Global input directory",
                            "create_if_missing": True
                        },
                        "output": {
                            "path": "output",
                            "path_type": "relative_to_root",
                            "description": "Global output directory",
                            "create_if_missing": True
                        },
                        "error": {
                            "path": "error",
                            "path_type": "relative_to_root",
                            "description": "Global error directory",
                            "create_if_missing": True
                        },
                        "database": {
                            "path": "database",
                            "path_type": "relative_to_root",
                            "description": "Database directory",
                            "create_if_missing": False
                        }
                    }
                },
                "services": {
                    "description": "Service-specific paths",
                    "CCU": {
                        "base": "services/ccu",
                        "config": "services/ccu/ccu_setting",
                        "certificates": "services/ccu/certificates",
                        "logs": "services/ccu/logs",
                        "temp": "services/ccu/temp"
                    },
                    "RCM": {
                        "base": "services/rcm",
                        "input": "services/rcm/input",
                        "output": "services/rcm/output",
                        "temp_input": "services/rcm/temp_input",
                        "temp_output": "services/rcm/temp_output",
                        "response_input": "services/rcm/RCM_RESPONSE_INPUT",
                        "response_output": "services/rcm/RCM_RESPONSE_OUTPUT"
                    },
                    "OCM": {
                        "base": "services/ocm",
                        "config": "services/ocm/deployment_config",
                        "data": "services/ocm/databases",
                        "reports": "services/ocm/reports",
                        "templates": "services/ocm/templates"
                    },
                    "JFA": {
                        "base": "services/jfa",
                        "datapool": "services/jfa/datapool"
                    },
                    "TPP": {
                        "base": "services/tpp"
                    },
                    "RLA": {
                        "base": "services/rla"
                    },
                    "TD": {
                        "base": "services/td",
                        "temp": "services/td/temp"
                    }
                }
            }
            
            # Save to default configuration
            self._parse_path_config(default_paths, "default")
            
            # Create the configuration directory structure
            config_dir = self.installation_root / "config" / "paths"
            config_dir.mkdir(parents=True, exist_ok=True)
            
            # Save default configuration to file
            with open(config_dir / "global_paths.json", 'w') as f:
                json.dump(default_paths, f, indent=2)
                
            self.logger.info("Created default path configuration")
            
        except Exception as e:
            self.logger.error(f"Failed to create default path configuration: {e}")
    
    def _parse_path_config(self, config: Dict[str, Any], config_type: str):
        """Parse and register path configurations."""
        try:
            # Parse global paths
            if "global" in config and "paths" in config["global"]:
                for path_name, path_info in config["global"]["paths"].items():
                    self.path_configs[f"global.{path_name}"] = PathConfig(
                        path=path_info["path"],
                        path_type=PathType(path_info["path_type"]),
                        description=path_info["description"],
                        create_if_missing=path_info.get("create_if_missing", True),
                        required_permissions=path_info.get("required_permissions"),
                        service_scope="global"
                    )
            
            # Parse service-specific paths
            if "services" in config:
                for service_name, service_paths in config["services"].items():
                    if service_name == "description":
                        continue
                    
                    for path_name, path_value in service_paths.items():
                        self.path_configs[f"service.{service_name}.{path_name}"] = PathConfig(
                            path=path_value,
                            path_type=PathType.RELATIVE_TO_ROOT,
                            description=f"{service_name} {path_name} directory",
                            create_if_missing=True,
                            service_scope=service_name
                        )
            
        except Exception as e:
            self.logger.error(f"Failed to parse path config ({config_type}): {e}")
    
    def _initialize_service_paths(self):
        """Initialize service-specific path structures."""
        services = ["CCU", "RCM", "OCM", "JFA", "TPP", "RLA", "TD"]
        
        for service in services:
            try:
                # Get base path for service
                base_path = self.get_service_path(service, "base")
                
                # Create standard directory structure
                service_paths = ServicePaths(
                    base=base_path,
                    input=self.get_service_path(service, "input", base_path / "input"),
                    output=self.get_service_path(service, "output", base_path / "output"),
                    temp=self.get_service_path(service, "temp", base_path / "temp"),
                    logs=self.get_service_path(service, "logs", base_path / "logs"),
                    cache=self.get_service_path(service, "cache", base_path / "cache"),
                    config=self.get_service_path(service, "config", base_path / "config"),
                    error=self.get_service_path(service, "error", base_path / "error"),
                    archive=self.get_service_path(service, "archive", base_path / "archive")
                )
                
                self.service_paths[service] = service_paths
                
            except Exception as e:
                self.logger.error(f"Failed to initialize paths for service {service}: {e}")
    
    def _validate_paths(self):
        """Validate all configured paths and create missing directories."""
        for path_key, path_config in self.path_configs.items():
            try:
                resolved_path = self._resolve_path(path_config)
                
                # Create directory if required
                if path_config.create_if_missing:
                    resolved_path.mkdir(parents=True, exist_ok=True)
                
                # Validate accessibility
                if not resolved_path.exists():
                    if path_config.create_if_missing:
                        self.logger.warning(f"Could not create path: {resolved_path}")
                    else:
                        self.logger.info(f"Path does not exist (not required): {resolved_path}")
                
                # Store resolved path
                self.resolved_paths[path_key] = resolved_path
                
            except Exception as e:
                self.logger.error(f"Failed to validate path {path_key}: {e}")
    
    def _resolve_path(self, path_config: PathConfig) -> Path:
        """Resolve a path configuration to an absolute Path."""
        try:
            if path_config.path_type == PathType.ABSOLUTE:
                return Path(path_config.path) if path_config.path else self.installation_root
            elif path_config.path_type == PathType.RELATIVE_TO_ROOT:
                return self.installation_root / path_config.path
            elif path_config.path_type == PathType.SYSTEM:
                return Path(path_config.path)
            else:
                # Default to relative to root
                return self.installation_root / path_config.path
                
        except Exception as e:
            self.logger.error(f"Failed to resolve path {path_config.path}: {e}")
            return self.installation_root / path_config.path
    
    def get_path(self, path_key: str) -> Optional[Path]:
        """
        Get a resolved path by key.
        
        Args:
            path_key: Path key (e.g., 'global.logs', 'service.RCM.input')
            
        Returns:
            Resolved Path object or None if not found
        """
        return self.resolved_paths.get(path_key)
    
    def get_global_path(self, path_name: str) -> Optional[Path]:
        """
        Get a global path by name.
        
        Args:
            path_name: Global path name (e.g., 'logs', 'temp', 'input')
            
        Returns:
            Resolved Path object or None if not found
        """
        return self.get_path(f"global.{path_name}")
    
    def get_service_path(self, service: str, path_name: str, default: Optional[Path] = None) -> Path:
        """
        Get a service-specific path by service and path name.
        
        Args:
            service: Service name (e.g., 'RCM', 'OCM')
            path_name: Path name (e.g., 'input', 'output', 'base')
            default: Default path if not found
            
        Returns:
            Resolved Path object
        """
        path_key = f"service.{service}.{path_name}"
        resolved_path = self.get_path(path_key)
        
        if resolved_path is None and default is not None:
            # Create and register the default path
            self.path_configs[path_key] = PathConfig(
                path=str(default.relative_to(self.installation_root)),
                path_type=PathType.RELATIVE_TO_ROOT,
                description=f"{service} {path_name} directory (default)",
                create_if_missing=True,
                service_scope=service
            )
            resolved_path = self._resolve_path(self.path_configs[path_key])
            self.resolved_paths[path_key] = resolved_path
            
            # Create directory if needed
            if resolved_path:
                resolved_path.mkdir(parents=True, exist_ok=True)
        
        return resolved_path or (default if default else self.installation_root)
    
    def get_service_paths(self, service: str) -> Optional[ServicePaths]:
        """
        Get all standard paths for a service.
        
        Args:
            service: Service name
            
        Returns:
            ServicePaths object or None if service not found
        """
        return self.service_paths.get(service)
    
    def get_installation_root(self) -> Path:
        """Get the installation root directory."""
        return self.installation_root
    
    def get_platform(self) -> str:
        """Get the current platform."""
        return self.platform
    
    def get_environment(self) -> Environment:
        """Get the current environment."""
        return self.environment
    
    def set_environment(self, environment: Environment):
        """
        Change the current environment and reload configurations.
        
        Args:
            environment: New environment
        """
        if environment != self.environment:
            self.environment = environment
            self.logger.info(f"Switching environment to: {environment.value}")
            
            # Reload configurations for new environment
            self._load_path_configurations()
            self._initialize_service_paths()
            self._validate_paths()
    
    def create_path_structure(self, service: str) -> bool:
        """
        Create the complete directory structure for a service.
        
        Args:
            service: Service name
            
        Returns:
            True if successful, False otherwise
        """
        try:
            service_paths = self.get_service_paths(service)
            if not service_paths:
                self.logger.error(f"No path configuration found for service: {service}")
                return False
            
            # Create all directories
            for path_name, path_obj in asdict(service_paths).items():
                path = Path(path_obj)
                path.mkdir(parents=True, exist_ok=True)
                self.logger.debug(f"Created {service} {path_name}: {path}")
            
            self.logger.info(f"Created complete directory structure for service: {service}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create path structure for {service}: {e}")
            return False
    
    def get_path_info(self) -> Dict[str, Any]:
        """
        Get comprehensive information about all managed paths.
        
        Returns:
            Dictionary containing path information
        """
        return {
            "installation_root": str(self.installation_root),
            "platform": self.platform,
            "environment": self.environment.value,
            "total_paths": len(self.resolved_paths),
            "global_paths": {k: str(v) for k, v in self.resolved_paths.items() if k.startswith("global.")},
            "service_paths": {
                service: {k: str(v) for k, v in asdict(paths).items()}
                for service, paths in self.service_paths.items()
            },
            "path_configs": {
                k: {
                    "path": config.path,
                    "type": config.path_type.value,
                    "description": config.description,
                    "resolved": str(self.resolved_paths.get(k, "Not resolved"))
                }
                for k, config in self.path_configs.items()
            }
        }
    
    def distribute_paths_to_service(self, service: str) -> Dict[str, str]:
        """
        Generate path configuration for distribution to a specific service.
        
        Args:
            service: Target service name
            
        Returns:
            Dictionary of paths for the service
        """
        try:
            service_paths = self.get_service_paths(service)
            if not service_paths:
                return {}
            
            # Create path dictionary for service
            paths = {
                "installation_root": str(self.installation_root),
                "service_root": str(service_paths.base),
                "input": str(service_paths.input),
                "output": str(service_paths.output),
                "temp": str(service_paths.temp),
                "logs": str(service_paths.logs),
                "cache": str(service_paths.cache),
                "config": str(service_paths.config),
                "error": str(service_paths.error),
                "archive": str(service_paths.archive),
                "global_input": str(self.get_global_path("input")),
                "global_output": str(self.get_global_path("output")),
                "global_temp": str(self.get_global_path("temp")),
                "global_logs": str(self.get_global_path("logs")),
                "global_cache": str(self.get_global_path("cache")),
                "database": str(self.get_global_path("database"))
            }
            
            # Add service-specific paths if available
            for path_key, resolved_path in self.resolved_paths.items():
                if path_key.startswith(f"service.{service}."):
                    path_name = path_key.replace(f"service.{service}.", "")
                    paths[f"service_{path_name}"] = str(resolved_path)
            
            return paths
            
        except Exception as e:
            self.logger.error(f"Failed to distribute paths to service {service}: {e}")
            return {}
    
    async def start(self):
        """Start the Path Management Module."""
        self.logger.info("PMM started successfully")
    
    async def stop(self):
        """Stop the Path Management Module."""
        self.logger.info("PMM stopped")
    
    def get_status(self) -> Dict[str, Any]:
        """Get the current status of PMM."""
        return {
            "active": True,
            "installation_root": str(self.installation_root),
            "platform": self.platform,
            "environment": self.environment.value,
            "total_paths_managed": len(self.resolved_paths),
            "services_configured": len(self.service_paths),
            "path_validation_status": "completed"
        } 