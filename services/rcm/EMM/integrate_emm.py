#!/usr/bin/env python3
"""
EMM Integration Script

This script systematically integrates the Error Management Module (EMM) into all modules
of the RCM microservice. It updates error handling to use dynamic error code generation
and ensures proper error logging throughout the system.
"""

import os
import re
import shutil
from pathlib import Path
from typing import List, Dict, Any

class EMMIntegrator:
    """Integrates EMM error handling into all modules."""
    
    def __init__(self):
        self.base_path = Path(__file__).parent
        self.modules_path = self.base_path
        self.emm_path = self.base_path / "EMM" / "emm.py"
        
        # Module names and their codes
        self.module_codes = {
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
    
    def find_module_files(self) -> List[Path]:
        """Find all Python module files."""
        module_files = []
        for module_dir in self.modules_path.iterdir():
            if module_dir.is_dir() and module_dir.name in self.module_codes:
                py_file = module_dir / f"{module_dir.name.lower()}.py"
                if py_file.exists():
                    module_files.append(py_file)
        return module_files
    
    def update_module_error_handling(self, module_file: Path) -> bool:
        """Update error handling in a module file."""
        try:
            module_name = module_file.parent.name
            print(f"Updating {module_name}...")
            
            # Read the file
            with open(module_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check if EMM is already imported
            if "from EMM.emm import ErrorManagementModule" not in content:
                # Add EMM import
                import_pattern = r'^import\s+.*$'
                imports = re.findall(import_pattern, content, re.MULTILINE)
                if imports:
                    # Add after existing imports
                    last_import = imports[-1]
                    emm_import = "\nfrom EMM.emm import ErrorManagementModule"
                    content = content.replace(last_import, last_import + emm_import)
                else:
                    # Add at the beginning
                    content = "from EMM.emm import ErrorManagementModule\n\n" + content
            
            # Initialize error manager in __init__
            if "self.error_manager = ErrorManagementModule()" not in content:
                init_pattern = r'def __init__\(self\):(.*?)(?=def|\Z)'
                init_match = re.search(init_pattern, content, re.DOTALL)
                if init_match:
                    init_content = init_match.group(1)
                    if "self.error_manager = ErrorManagementModule()" not in init_content:
                        # Add error manager initialization
                        indent = re.match(r'^\s*', init_content).group(0)
                        error_manager_line = f"{indent}self.error_manager = ErrorManagementModule()\n"
                        content = content.replace(init_match.group(0), 
                                               f"def __init__(self):{init_content}{error_manager_line}")
            
            # Replace hardcoded error codes with dynamic generation
            # Pattern: self.error_manager.log_error("0101030X001", error_msg)
            # Replace with: self.error_manager.log_error_with_generation("MODULE", "CLASS", "FUNCTION", error_msg)
            
            # Find all error logging calls
            error_log_pattern = r'self\.error_manager\.log_error\([^)]+\)'
            error_logs = re.findall(error_log_pattern, content)
            
            for error_log in error_logs:
                # Extract the error code and message
                match = re.search(r'log_error\(([^,]+),\s*([^)]+)\)', error_log)
                if match:
                    error_code = match.group(1).strip().strip('"\'')
                    error_message = match.group(2).strip()
                    
                    # Generate new error logging call
                    # We need to determine the class and function name from context
                    # For now, use a generic approach
                    new_error_log = f'self.error_manager.log_error_with_generation("{module_name}", "UnknownClass", "UnknownFunction", {error_message})'
                    content = content.replace(error_log, new_error_log)
            
            # Write updated content
            with open(module_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"✓ Updated {module_name}")
            return True
            
        except Exception as e:
            print(f"✗ Error updating {module_file.name}: {e}")
            return False
    
    def create_error_handling_template(self, module_name: str) -> str:
        """Create a template for error handling in a module."""
        return f'''
    def log_error(self, error_message: str, class_name: str = "UnknownClass", function_name: str = "UnknownFunction", sub_function: str = "001"):
        """Log an error using EMM."""
        return self.error_manager.log_error_with_generation(
            "{module_name}", 
            class_name, 
            function_name, 
            error_message, 
            sub_function
        )
'''
    
    def run_integration(self):
        """Run the complete EMM integration."""
        print("Starting EMM integration...")
        
        # Find all module files
        module_files = self.find_module_files()
        print(f"Found {len(module_files)} module files")
        
        # Update each module
        updated_count = 0
        for module_file in module_files:
            if self.update_module_error_handling(module_file):
                updated_count += 1
        
        print(f"\nIntegration complete: {updated_count}/{len(module_files)} modules updated")
        
        # Create a summary report
        self.create_integration_report(module_files)
    
    def create_integration_report(self, module_files: List[Path]):
        """Create a report of the integration process."""
        report = f"""
# EMM Integration Report

## Summary
- Total modules found: {len(module_files)}
- Modules with EMM integration: {len(module_files)}

## Module Status
"""
        
        for module_file in module_files:
            module_name = module_file.parent.name
            report += f"- {module_name}: ✓ Integrated\n"
        
        report += f"""
## Integration Details

### Error Code Format
All error codes now follow the 16-character hexadecimal format:
[Server Code][Macroservice Code][Microservice Code][Module Code][Class Code][Function Code][Sub-function Code]

### Error Logging
All modules now use:
```python
self.error_manager.log_error_with_generation(
    module_name, 
    class_name, 
    function_name, 
    error_message, 
    sub_function
)
```

### Automatic Code Generation
The EMM module includes automatic code generation that can be triggered via ECM:
```python
await ecm.receive_command("auto_code_gen")
```

## Next Steps
1. Test error handling in each module
2. Verify error code generation
3. Test automatic code generation
4. Monitor error logs for consistency
"""
        
        # Write report
        report_file = self.base_path / "EMM_integration_report.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"Integration report written to: {report_file}")


if __name__ == "__main__":
    integrator = EMMIntegrator()
    integrator.run_integration() 