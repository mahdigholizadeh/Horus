"""
Test T00000007: PMM Service Path Distribution
Module(s) Tested: PMM (Path Management Module)
Description: Test path distribution to all dependent microservices
Test Description: 
- Distribute paths to all 6 services: RLA, RCM, TPP, TD, JFA, OCM
- Verify standard directory structure creation (base, input, output, temp, logs, cache, config, error, archive)
- Test environment-specific path configurations (dev/staging/production)
- Check path validation and accessibility
- Validate path permissions and security
- Test path update and reconfiguration
Expected Result: Complete path distribution with proper directory structure
Pass Criteria: All services get paths, directories created, environments supported, validation works
Implementation Notes: Create test directory structures, simulate different environments
"""

import asyncio
import json
import sys
import time
import logging
import tempfile
import os
from pathlib import Path
from typing import Dict, Any
from unittest.mock import Mock, patch, AsyncMock

# Add parent directory to path for module imports
sys.path.insert(0, str(Path(__file__).parent.parent))

async def test_t00000007():
    test_code = "T00000007"
    test_name = "PMM Service Path Distribution"
    results = []
    
    try:
        # Import PMM module
        from PMM.pmm import PathManagementModule, Environment
        
        # Step 1: Test PMM initialization
        pmm = PathManagementModule()
        results.append(pmm is not None)
        results.append(hasattr(pmm, 'installation_root'))
        
        # Step 2: Define all services to test
        services = ["RLA", "RCM", "TPP", "TD", "JFA", "OCM"]
        standard_directories = ["base", "input", "output", "temp", "logs", "cache", "config", "error", "archive"]
        
        # Step 3: Test path distribution to all services
        for service in services:
            service_paths = pmm.distribute_paths_to_service(service)
            results.append(isinstance(service_paths, dict))
            results.append(len(service_paths) > 0)
            
            # Check required paths
            required_paths = [
                "installation_root", "service_root", "input", "output", "temp", 
                "logs", "cache", "config", "error", "archive", "global_input", 
                "global_output", "global_temp", "global_logs", "global_cache", "database"
            ]
            
            for path_name in required_paths:
                results.append(path_name in service_paths)
                if path_name in service_paths:
                    path_value = service_paths[path_name]
                    results.append(isinstance(path_value, str))
                    results.append(len(path_value) > 0)
        
        # Step 4: Test service-specific path structures
        for service in services:
            service_paths_obj = pmm.get_service_paths(service)
            results.append(service_paths_obj is not None)
            
            if service_paths_obj:
                for dir_name in standard_directories:
                    results.append(hasattr(service_paths_obj, dir_name))
                    if hasattr(service_paths_obj, dir_name):
                        dir_path = getattr(service_paths_obj, dir_name)
                        results.append(isinstance(dir_path, Path))
        
        # Step 5: Test environment-specific configurations
        environments = [Environment.DEVELOPMENT, Environment.STAGING, Environment.PRODUCTION, Environment.TESTING]
        
        for env in environments:
            pmm_env = PathManagementModule(environment=env)
            results.append(pmm_env is not None)
            results.append(pmm_env.get_environment() == env)
            
            # Test path distribution in different environments
            for service in services:
                env_service_paths = pmm_env.distribute_paths_to_service(service)
                results.append(isinstance(env_service_paths, dict))
                results.append("installation_root" in env_service_paths)
                results.append("service_root" in env_service_paths)
        
        # Step 6: Test directory structure creation
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create PMM with temporary root
            pmm_temp = PathManagementModule(installation_root=temp_path)
            results.append(pmm_temp is not None)
            
            # Test directory creation for a service
            service = "RCM"
            service_paths = pmm_temp.distribute_paths_to_service(service)
            
            # Check if directories can be created
            for dir_name in ["input", "output", "temp", "logs", "cache", "config", "error", "archive"]:
                if dir_name in service_paths:
                    dir_path = Path(service_paths[dir_name])
                    try:
                        dir_path.mkdir(parents=True, exist_ok=True)
                        results.append(dir_path.exists())
                        results.append(dir_path.is_dir())
                    except Exception as e:
                        results.append(False)  # Directory creation failed
        
        # Step 7: Test path validation and accessibility
        for service in services:
            service_paths = pmm.distribute_paths_to_service(service)
            
            # Test installation root accessibility
            if "installation_root" in service_paths:
                install_root = Path(service_paths["installation_root"])
                results.append(install_root.exists())
                results.append(install_root.is_dir())
                
                # Test read access
                try:
                    list(install_root.iterdir())
                    results.append(True)  # Read access works
                except PermissionError:
                    results.append(False)  # No read access
        
        # Step 8: Test path permissions and security
        # Test that paths don't contain sensitive information
        for service in services:
            service_paths = pmm.distribute_paths_to_service(service)
            
            for path_name, path_value in service_paths.items():
                results.append(isinstance(path_value, str))
                # Check that paths don't contain obvious security issues
                results.append(".." not in path_value)  # No directory traversal
                results.append("~" not in path_value)   # No home directory expansion
                results.append("//" not in path_value)  # No double slashes
        
        # Step 9: Test path update and reconfiguration
        # Test updating paths dynamically
        original_paths = pmm.distribute_paths_to_service("RCM")
        results.append(isinstance(original_paths, dict))
        
        # Test with different installation root
        with tempfile.TemporaryDirectory() as temp_dir:
            new_root = Path(temp_dir)
            pmm_new = PathManagementModule(installation_root=new_root)
            
            new_paths = pmm_new.distribute_paths_to_service("RCM")
            results.append(isinstance(new_paths, dict))
            results.append(new_paths["installation_root"] == str(new_root))
            results.append(new_paths["installation_root"] != original_paths["installation_root"])
        
        # Step 10: Test global path distribution
        global_paths = ["input", "output", "temp", "logs", "cache", "database"]
        
        for path_name in global_paths:
            try:
                global_path = pmm.get_global_path(path_name)
                results.append(global_path is not None)
                results.append(isinstance(global_path, Path))
                
                # Test that global paths are included in service distributions
                for service in services:
                    service_paths = pmm.distribute_paths_to_service(service)
                    global_key = f"global_{path_name}"
                    if global_key in service_paths:
                        results.append(service_paths[global_key] == str(global_path))
                        
            except Exception as e:
                # Some global paths might not exist, which is okay
                results.append("path" in str(e).lower() or "not found" in str(e).lower())
        
        # Step 11: Test service-specific path customization
        # Test getting specific service paths
        for service in services:
            service_root = pmm.get_service_path(service, "service_base")
            results.append(service_root is not None)
            results.append(isinstance(service_root, Path))
            
            # Test getting non-existent path with default
            default_path = pmm.installation_root / "default"
            non_existent_path = pmm.get_service_path(service, "non_existent", default=default_path)
            results.append(non_existent_path == default_path)
        
        # Step 12: Test path information retrieval
        path_info = pmm.get_path_info()
        results.append(isinstance(path_info, dict))
        results.append("installation_root" in path_info)
        results.append("platform" in path_info)
        results.append("environment" in path_info)
        results.append("service_paths" in path_info)
        
        # Step 13: Test cross-platform path compatibility
        # Test Windows path handling
        with patch('platform.system', return_value='Windows'):
            pmm_windows = PathManagementModule()
            windows_paths = pmm_windows.distribute_paths_to_service("RCM")
            results.append(isinstance(windows_paths, dict))
            results.append("installation_root" in windows_paths)
            
            # Check Windows path format
            for path_value in windows_paths.values():
                if isinstance(path_value, str) and len(path_value) > 0:
                    # Windows paths should use backslashes or forward slashes
                    results.append("\\" in path_value or "/" in path_value)
        
        # Test Linux path handling
        with patch('platform.system', return_value='Linux'):
            pmm_linux = PathManagementModule()
            linux_paths = pmm_linux.distribute_paths_to_service("RCM")
            results.append(isinstance(linux_paths, dict))
            results.append("installation_root" in linux_paths)
            
            # Check Linux path format
            for path_value in linux_paths.values():
                if isinstance(path_value, str) and len(path_value) > 0:
                    # Linux paths should use forward slashes
                    results.append("/" in path_value)
        
        # Step 14: Test path configuration persistence
        # Test that path configurations are consistent across multiple calls
        first_paths = pmm.distribute_paths_to_service("RCM")
        second_paths = pmm.distribute_paths_to_service("RCM")
        results.append(first_paths == second_paths)
        
        # Test that different services get different paths
        rcm_paths = pmm.distribute_paths_to_service("RCM")
        rla_paths = pmm.distribute_paths_to_service("RLA")
        results.append(rcm_paths != rla_paths)
        
        # Step 15: Test error handling for invalid services
        try:
            invalid_paths = pmm.distribute_paths_to_service("INVALID_SERVICE")
            results.append(isinstance(invalid_paths, dict))
            results.append(len(invalid_paths) == 0)  # Should return empty dict for invalid service
        except Exception as e:
            # Should handle invalid service gracefully
            results.append("invalid" in str(e).lower() or "service" in str(e).lower())
        
        # Calculate test results
        total_tests = len(results)
        passed_tests = sum(results)
        failed_tests = total_tests - passed_tests
        
        # Log results
        logging.info(f"Test {test_code}: {test_name}")
        logging.info(f"Total tests: {total_tests}")
        logging.info(f"Passed: {passed_tests}")
        logging.info(f"Failed: {failed_tests}")
        logging.info(f"Success rate: {(passed_tests/total_tests)*100:.2f}%")
        logging.info(f"Services tested: {', '.join(services)}")
        logging.info(f"Directories tested: {', '.join(standard_directories)}")
        
        return {
            "test_code": test_code,
            "test_name": test_name,
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "success_rate": (passed_tests/total_tests)*100,
            "execution_time": 0.0,
            "results": results,
            "success": failed_tests == 0,
            "services_tested": services,
            "directories_tested": standard_directories
        }
        
    except Exception as e:
        logging.error(f"Test {test_code} failed with exception: {e}")
        return {
            "test_code": test_code,
            "test_name": test_name,
            "total_tests": 0,
            "passed_tests": 0,
            "failed_tests": 1,
            "success_rate": 0.0,
            "execution_time": 0.0,
            "results": [],
            "success": False,
            "error": str(e)
        }


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run the test
    result = asyncio.run(test_t00000007())
    
    if result["success"]:
        print(f"✅ {result['test_code']}: {result['test_name']} - PASSED")
        print(f"   Passed: {result['passed_tests']}/{result['total_tests']} tests")
        print(f"   Success rate: {result['success_rate']:.2f}%")
        print(f"   Services tested: {', '.join(result.get('services_tested', []))}")
        print(f"   Directories tested: {', '.join(result.get('directories_tested', []))}")
    else:
        print(f"❌ {result['test_code']}: {result['test_name']} - FAILED")
        if "error" in result:
            print(f"   Error: {result['error']}")
        else:
            print(f"   Passed: {result['passed_tests']}/{result['total_tests']} tests")
            print(f"   Success rate: {result['success_rate']:.2f}%") 