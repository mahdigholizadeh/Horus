"""
Test T00000010: CIM (Configuration Interface Module) Unit Test
Module(s) Tested: CIM
Description: To test the CIM's ability to load configuration from files and environment variables.
Success Criteria: CIM loads all settings from default config file, environment variable override is successful.
"""

import asyncio
import json
import sys
import os
import tempfile
from pathlib import Path
from typing import Dict, Any

# Add parent directory to path for module imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from CIM.cim import ConfigurationInterfaceModule

async def test_t00000010():
    test_code = "T00000010"
    test_name = "CIM - Configuration Interface Module Unit Test"
    results = []
    
    # Step 1: Set an environment variable to override a config value
    original_log_level = os.environ.get("JFA_LOG_LEVEL", "")
    os.environ["JFA_LOG_LEVEL"] = "DEBUG"
    
    # Create a temporary config file for testing
    test_config = {
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
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_config:
        json.dump(test_config, temp_config)
        config_file_path = temp_config.name
    
    try:
        # Step 2: Initialize the CIM
        cim = ConfigurationInterfaceModule()
        await cim.start()
        
        # Test if CIM loaded configuration successfully
        config = cim.get_configuration()
        results.append(isinstance(config, dict))
        
        # Check if all required sections are present
        required_sections = ["logging", "processing", "api", "database"]
        sections_present = all(section in config for section in required_sections)
        results.append(sections_present)
        
        # Check if logging level setting should be DEBUG (environment variable override)
        logging_config = config.get("logging", {})
        log_level = logging_config.get("level", "")
        results.append(log_level == "DEBUG")
        
        # Test configuration validation
        validation_result = await cim.validate_configuration()
        results.append(validation_result.get("valid", False))
        
        # Test configuration reload
        reload_result = await cim.reload_configuration()
        results.append(reload_result.get("success", False))
        
        # Test getting specific configuration values
        max_template_size = cim.get_config_value("processing.max_template_size")
        results.append(max_template_size == 10485760)
        
        api_port = cim.get_config_value("api.port")
        results.append(api_port == 8001)
        
        # Test setting configuration values
        set_result = await cim.set_config_value("api.debug", True)
        results.append(set_result.get("success", False))
        
        if set_result.get("success", False):
            new_debug_value = cim.get_config_value("api.debug")
            results.append(new_debug_value == True)
        else:
            results.append(False)
        
        # Test configuration export
        export_result = await cim.export_configuration()
        results.append(export_result.get("success", False))
        
        if export_result.get("success", False):
            exported_config = export_result.get("configuration", {})
            results.append(isinstance(exported_config, dict))
            results.append("logging" in exported_config)
        else:
            results.extend([False, False])
        
        success = all(results)
        
        return {
            "success": success,
            "test_code": test_code,
            "test_name": test_name,
            "message": "CIM unit test passed" if success else "CIM unit test failed",
            "details": {
                "configuration_loaded": results[0],
                "required_sections_present": results[1],
                "environment_override_working": results[2],
                "configuration_valid": results[3],
                "reload_successful": results[4],
                "max_template_size_correct": results[5],
                "api_port_correct": results[6],
                "set_config_value_works": results[7],
                "set_value_persisted": results[8] if len(results) > 8 else False,
                "export_successful": results[9] if len(results) > 9 else False,
                "exported_config_valid": results[10] if len(results) > 10 else False,
                "exported_config_has_logging": results[11] if len(results) > 11 else False,
                "current_config": config,
                "results": results
            }
        }
        
    finally:
        # Clean up
        await cim.stop()
        os.remove(config_file_path)
        # Restore original environment variable
        if original_log_level:
            os.environ["JFA_LOG_LEVEL"] = original_log_level
        else:
            os.environ.pop("JFA_LOG_LEVEL", None)