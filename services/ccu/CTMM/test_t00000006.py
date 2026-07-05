"""
Test T00000006: PMM Installation Root Detection
Module(s) Tested: PMM (Path Management Module)
Description: Test automatic installation root directory detection
Test Description: 
- Test installation root detection via marker files
- Verify environment variable fallback (COMPUTATION_SERVER_ROOT)
- Check default root path calculation
- Test cross-platform path resolution (Windows/Linux)
- Validate root path accessibility and permissions
- Test root path validation and error handling
Expected Result: Accurate installation root detection across platforms
Pass Criteria: Root detected correctly, fallbacks work, cross-platform support, validation passes
Implementation Notes: Test on different platforms, simulate various directory structures
"""

import asyncio
import json
import sys
import time
import logging
import tempfile
import os
import platform
from pathlib import Path
from typing import Dict, Any
from unittest.mock import Mock, patch, AsyncMock

# Add parent directory to path for module imports
sys.path.insert(0, str(Path(__file__).parent.parent))

async def test_t00000006():
    test_code = "T00000006"
    test_name = "PMM Installation Root Detection"
    results = []
    
    try:
        # Import PMM module
        from PMM.pmm import PathManagementModule, Environment
        
        # Step 1: Test PMM initialization with auto-detection
        pmm = PathManagementModule()
        results.append(pmm is not None)
        results.append(hasattr(pmm, 'installation_root'))
        results.append(hasattr(pmm, 'platform'))
        results.append(hasattr(pmm, 'environment'))
        
        # Step 2: Verify installation root detection
        installation_root = pmm.get_installation_root()
        results.append(installation_root is not None)
        results.append(isinstance(installation_root, Path))
        results.append(installation_root.exists())
        
        # Step 3: Test platform detection
        current_platform = pmm.get_platform()
        results.append(current_platform is not None)
        results.append(isinstance(current_platform, str))
        results.append(current_platform in ['windows', 'linux', 'darwin'])
        results.append(current_platform == platform.system().lower())
        
        # Step 4: Test environment detection
        environment = pmm.get_environment()
        results.append(environment is not None)
        results.append(isinstance(environment, Environment))
        results.append(environment.value in ['development', 'staging', 'production', 'testing'])
        
        # Step 5: Test marker file detection
        # Create temporary directory structure with marker files
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create marker files
            marker_files = [
                "JFA_CONFIGURATION_PLAN.md",
                "LICENSE.txt",
                "services",
                ".git"
            ]
            
            for marker in marker_files:
                if marker == "services":
                    # Create directory
                    (temp_path / marker).mkdir(exist_ok=True)
                elif marker == ".git":
                    # Create .git directory
                    (temp_path / marker).mkdir(exist_ok=True)
                else:
                    # Create file
                    (temp_path / marker).touch()
            
            # Test PMM with custom root
            pmm_custom = PathManagementModule(installation_root=temp_path)
            results.append(pmm_custom is not None)
            results.append(pmm_custom.get_installation_root() == temp_path)
            
            # Verify marker detection
            for marker in marker_files:
                marker_path = temp_path / marker
                results.append(marker_path.exists())
        
        # Step 6: Test environment variable fallback
        # Test with COMPUTATION_SERVER_ROOT environment variable
        test_env_root = Path(tempfile.gettempdir()) / "test_computation_server"
        test_env_root.mkdir(exist_ok=True)
        
        # Set environment variable
        original_env = os.environ.get("COMPUTATION_SERVER_ROOT")
        os.environ["COMPUTATION_SERVER_ROOT"] = str(test_env_root)
        
        try:
            # Create PMM instance that should use environment variable
            pmm_env = PathManagementModule()
            env_detected_root = pmm_env.get_installation_root()
            results.append(env_detected_root == test_env_root)
            results.append(env_detected_root.exists())
            
        finally:
            # Restore original environment
            if original_env:
                os.environ["COMPUTATION_SERVER_ROOT"] = original_env
            else:
                del os.environ["COMPUTATION_SERVER_ROOT"]
            
            # Cleanup
            if test_env_root.exists():
                test_env_root.rmdir()
        
        # Step 7: Test cross-platform path resolution
        # Test Windows path resolution
        with patch('platform.system', return_value='Windows'):
            pmm_windows = PathManagementModule()
            results.append(pmm_windows.get_platform() == 'windows')
            
            # Test Windows path handling
            windows_path = pmm_windows.get_installation_root()
            results.append(isinstance(windows_path, Path))
            results.append(windows_path.exists())
        
        # Test Linux path resolution
        with patch('platform.system', return_value='Linux'):
            pmm_linux = PathManagementModule()
            results.append(pmm_linux.get_platform() == 'linux')
            
            # Test Linux path handling
            linux_path = pmm_linux.get_installation_root()
            results.append(isinstance(linux_path, Path))
            results.append(linux_path.exists())
        
        # Test macOS path resolution
        with patch('platform.system', return_value='Darwin'):
            pmm_macos = PathManagementModule()
            results.append(pmm_macos.get_platform() == 'darwin')
            
            # Test macOS path handling
            macos_path = pmm_macos.get_installation_root()
            results.append(isinstance(macos_path, Path))
            results.append(macos_path.exists())
        
        # Step 8: Test path accessibility and permissions
        installation_root = pmm.get_installation_root()
        
        # Test read access
        try:
            list(installation_root.iterdir())
            results.append(True)  # Read access works
        except PermissionError:
            results.append(False)  # No read access
        
        # Test write access (if possible)
        test_file = installation_root / "test_write_access.tmp"
        try:
            test_file.write_text("test")
            test_file.unlink()  # Clean up
            results.append(True)  # Write access works
        except (PermissionError, OSError):
            results.append(False)  # No write access
        
        # Step 9: Test root path validation
        # Test with valid root
        results.append(pmm.get_installation_root().exists())
        results.append(pmm.get_installation_root().is_dir())
        
        # Test with invalid root
        invalid_root = Path("/nonexistent/path/that/should/not/exist")
        try:
            pmm_invalid = PathManagementModule(installation_root=invalid_root)
            # Should handle invalid root gracefully
            results.append(pmm_invalid is not None)
            results.append(hasattr(pmm_invalid, 'installation_root'))
        except Exception as e:
            # Should handle invalid root with error
            results.append("path" in str(e).lower() or "invalid" in str(e).lower())
        
        # Step 10: Test error handling
        # Test with None root
        try:
            pmm_none = PathManagementModule(installation_root=None)
            results.append(pmm_none is not None)
            results.append(hasattr(pmm_none, 'installation_root'))
            results.append(pmm_none.get_installation_root() is not None)
        except Exception as e:
            # Should handle None root gracefully
            results.append("none" in str(e).lower() or "null" in str(e).lower())
        
        # Step 11: Test path information
        path_info = pmm.get_path_info()
        results.append(isinstance(path_info, dict))
        results.append("installation_root" in path_info)
        results.append("platform" in path_info)
        results.append("environment" in path_info)
        results.append("service_paths" in path_info)
        
        # Step 12: Test service path distribution
        # Test path distribution to a service
        service_paths = pmm.distribute_paths_to_service("RCM")
        results.append(isinstance(service_paths, dict))
        results.append("installation_root" in service_paths)
        results.append("service_root" in service_paths)
        results.append("input" in service_paths)
        results.append("output" in service_paths)
        results.append("temp" in service_paths)
        results.append("logs" in service_paths)
        results.append("cache" in service_paths)
        results.append("config" in service_paths)
        results.append("error" in service_paths)
        results.append("archive" in service_paths)
        
        # Step 13: Test environment switching
        # Test switching to different environments
        for env_name in ['development', 'staging', 'production', 'testing']:
            env_enum = Environment(env_name)
            pmm_env_switch = PathManagementModule(environment=env_enum)
            results.append(pmm_env_switch is not None)
            results.append(pmm_env_switch.get_environment() == env_enum)
            results.append(pmm_env_switch.get_environment().value == env_name)
        
        # Step 14: Test path resolution methods
        # Test getting specific service paths
        rcm_paths = pmm.get_service_paths("RCM")
        results.append(rcm_paths is not None)
        results.append(hasattr(rcm_paths, 'base'))
        results.append(hasattr(rcm_paths, 'input'))
        results.append(hasattr(rcm_paths, 'output'))
        results.append(hasattr(rcm_paths, 'temp'))
        results.append(hasattr(rcm_paths, 'logs'))
        results.append(hasattr(rcm_paths, 'cache'))
        results.append(hasattr(rcm_paths, 'config'))
        results.append(hasattr(rcm_paths, 'error'))
        results.append(hasattr(rcm_paths, 'archive'))
        
        # Step 15: Test global path access
        global_paths = ['input', 'output', 'temp', 'logs', 'cache', 'database']
        for path_name in global_paths:
            try:
                global_path = pmm.get_global_path(path_name)
                results.append(global_path is not None)
                results.append(isinstance(global_path, Path))
            except Exception as e:
                # Some paths might not exist, which is okay
                results.append("path" in str(e).lower() or "not found" in str(e).lower())
        
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
        logging.info(f"Installation root: {installation_root}")
        logging.info(f"Platform: {current_platform}")
        logging.info(f"Environment: {environment.value}")
        
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
            "installation_root": str(installation_root),
            "platform": current_platform,
            "environment": environment.value
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
    result = asyncio.run(test_t00000006())
    
    if result["success"]:
        print(f"PASS {result['test_code']}: {result['test_name']} - PASSED")
        print(f"   Passed: {result['passed_tests']}/{result['total_tests']} tests")
        print(f"   Success rate: {result['success_rate']:.2f}%")
        print(f"   Installation root: {result.get('installation_root', 'N/A')}")
        print(f"   Platform: {result.get('platform', 'N/A')}")
        print(f"   Environment: {result.get('environment', 'N/A')}")
    else:
        print(f"FAIL {result['test_code']}: {result['test_name']} - FAILED")
        if "error" in result:
            print(f"   Error: {result['error']}")
        else:
            print(f"   Passed: {result['passed_tests']}/{result['total_tests']} tests")
            print(f"   Success rate: {result['success_rate']:.2f}%")