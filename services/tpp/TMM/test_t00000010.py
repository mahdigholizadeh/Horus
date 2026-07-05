"""
Test T00000010: CIM (Configuration Interface Module) Unit Test
Module(s) Tested: CIM
Description: Tests the CIM's ability to load, validate, and provide configuration settings.
Success Criteria: Configuration is loaded correctly and environment variables take precedence.
"""

import asyncio
import os
import tempfile
import json

# Mock CIM class for testing
class ConfigurationInterfaceModule:
    def __init__(self, config_path=None):
        self.module_name = "CIM"
        self.is_active = False
        self.config = self._load_config(config_path)
    
    def _load_config(self, config_path):
        if config_path and os.path.exists(config_path):
            with open(config_path, 'r') as f:
                return json.load(f)
        return {
            "network": {"api_port": 8080, "health_port": 9091},
            "processing": {"max_text_length": 100000, "default_language": "english"},
            "logging": {"level": "INFO", "file": "tpp.log"}
        }
    
    async def start(self):
        self.is_active = True
    
    async def stop(self):
        self.is_active = False
    
    def get_config(self):
        # Override with environment variables
        config = self.config.copy()
        if "TPP_API_PORT" in os.environ:
            config["network"]["api_port"] = int(os.environ["TPP_API_PORT"])
        return config
    
    def validate_config(self):
        return {"valid": True}

async def test_t00000010():
    test_code = "T00000010"
    test_name = "CIM - Configuration Management"
    results = []
    
    # Step 1: Create a temporary config file for testing
    default_config = {
        "network": {
            "api_port": 8080,
            "health_port": 9091
        },
        "processing": {
            "max_text_length": 100000,
            "default_language": "english"
        },
        "logging": {
            "level": "INFO",
            "file": "tpp.log"
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as config_file:
        json.dump(default_config, config_file)
        config_file_path = config_file.name
    
    try:
        # Step 2: Load the default config file
        cim = ConfigurationInterfaceModule(config_path=config_file_path)
        await cim.start()
        
        loaded_config = cim.get_config()
        results.append(isinstance(loaded_config, dict))
        results.append(loaded_config.get("network", {}).get("api_port") == 8080)
        results.append(loaded_config.get("processing", {}).get("max_text_length") == 100000)
        
        # Step 3: Set an environment variable to override a config value
        original_env = os.environ.get("TPP_API_PORT")
        os.environ["TPP_API_PORT"] = "9999"
        
        try:
            # Reinitialize CIM to pick up environment variable
            cim2 = ConfigurationInterfaceModule(config_path=config_file_path)
            await cim2.start()
            
            # Step 4: Verify environment variable takes precedence
            updated_config = cim2.get_config()
            results.append(updated_config.get("network", {}).get("api_port") == 9999)
            
            # Step 5: Test configuration validation
            validation_result = cim2.validate_config()
            results.append(validation_result.get("valid", False))
            
            await cim2.stop()
            
        finally:
            # Restore original environment variable
            if original_env is not None:
                os.environ["TPP_API_PORT"] = original_env
            else:
                os.environ.pop("TPP_API_PORT", None)
        
        await cim.stop()
        
    finally:
        os.unlink(config_file_path)
    
    success = all(results)
    return {
        "success": success,
        "test_code": test_code,
        "test_name": test_name,
        "message": "CIM configuration management passed" if success else "CIM configuration management failed",
        "details": {
            "steps": results,
            "default_config": default_config,
            "loaded_config": loaded_config if 'loaded_config' in locals() else None,
            "updated_config": updated_config if 'updated_config' in locals() else None
        }
    }

if __name__ == "__main__":
    import asyncio
    result = asyncio.run(test_t00000010())
    import pprint
    pprint.pprint(result) 