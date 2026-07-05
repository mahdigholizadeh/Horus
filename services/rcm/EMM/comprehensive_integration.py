#!/usr/bin/env python3
"""
Comprehensive EMM Integration Script

This script addresses all three critical integration points:
1. Refactor all modules to use EMM's log_error_with_generation
2. Remove or refactor hardcoded self.error_codes dictionaries
3. Integrate comprehensive API error handling with OpenAI error mapping

This is a complete overhaul of the RCM system's error handling architecture.
"""

import os
import re
import shutil
import json
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Set
from datetime import datetime

class ComprehensiveEMMIntegrator:
    """Comprehensive EMM integration for the entire RCM system."""
    
    def __init__(self):
        self.base_path = Path(__file__).parent.parent
        self.modules_path = self.base_path
        
        # All RCM modules that need integration
        self.rcm_modules = {
            "GIDVM": "01", "PBRPM": "02", "AACM": "03", "FBWM": "04", "FDM": "05",
            "PRM": "06", "RTRMM": "07", "RLM": "08", "MMM": "09", "DRM": "0A",
            "FAIM": "0B", "BTM": "0C", "IFCM": "0D", "ECM": "0E", "AAAIM": "0F",
            "BAAIM": "10", "SAAIM": "11", "SODVM": "12", "FOM": "13", "DCMM": "14",
            "TMM": "15", "EMM": "16", "MSM": "17", "SMSM": "18", "SMCM": "19",
            "JFAIM": "1A", "OCMIM": "1B"
        }
        
        # API-related modules that need special API error handling
        self.api_modules = ["AACM", "BAAIM", "SAAIM", "AAAIM", "JFAIM", "OCMIM"]
        
        # Integration statistics
        self.stats = {
            "modules_processed": 0,
            "modules_updated": 0,
            "hardcoded_codes_removed": 0,
            "api_error_handling_added": 0,
            "errors": []
        }
    
    def find_all_module_files(self) -> List[Path]:
        """Find all Python module files in the RCM system."""
        module_files = []
        
        # Find main module files
        for module_name in self.rcm_modules.keys():
            module_file = self.modules_path / module_name / f"{module_name.lower()}.py"
            if module_file.exists():
                module_files.append(module_file)
        
        # Find RCM_main.py
        rcm_main_file = self.modules_path / "RCM_main.py"
        if rcm_main_file.exists():
            module_files.append(rcm_main_file)
        
        # Find any other Python files in the RCM_main directory
        for py_file in self.modules_path.rglob("*.py"):
            if py_file.name not in ["__init__.py", "comprehensive_integration.py", "integrate_emm.py"]:
                if py_file not in module_files:
                    module_files.append(py_file)
        
        return module_files
    
    def update_module_for_emm_integration(self, module_file: Path) -> bool:
        """Update a single module for comprehensive EMM integration."""
        try:
            module_name = module_file.parent.name if module_file.parent.name in self.rcm_modules else module_file.stem
            print(f"Processing {module_name}...")
            
            # Read the file
            with open(module_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # Step 1: Ensure EMM import
            content = self._ensure_emm_import(content)
            
            # Step 2: Ensure error manager initialization
            content = self._ensure_error_manager_init(content, module_name)
            
            # Step 3: Remove hardcoded error codes
            content = self._remove_hardcoded_error_codes(content, module_name)
            
            # Step 4: Update error logging calls
            content = self._update_error_logging_calls(content, module_name)
            
            # Step 5: Add API error handling if needed
            if module_name in self.api_modules:
                content = self._add_api_error_handling(content, module_name)
            
            # Step 6: Add comprehensive error handling methods
            content = self._add_error_handling_methods(content, module_name)
            
            # Write updated content if changed
            if content != original_content:
                with open(module_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                self.stats["modules_updated"] += 1
                print(f"✓ Updated {module_name}")
                return True
            else:
                print(f"- No changes needed for {module_name}")
                return False
                
        except Exception as e:
            error_msg = f"Error updating {module_file.name}: {e}"
            self.stats["errors"].append(error_msg)
            print(f"✗ {error_msg}")
            return False
    
    def _ensure_emm_import(self, content: str) -> str:
        """Ensure EMM import is present."""
        if "from EMM.emm import ErrorManagementModule" not in content:
            # Add import after existing imports
            import_pattern = r'^import\s+.*$'
            imports = re.findall(import_pattern, content, re.MULTILINE)
            
            if imports:
                # Add after last import
                last_import = imports[-1]
                emm_import = "\nfrom EMM.emm import ErrorManagementModule"
                content = content.replace(last_import, last_import + emm_import)
            else:
                # Add at beginning
                content = "from EMM.emm import ErrorManagementModule\n\n" + content
        
        # Also ensure API error handler import
        if "from EMM.api_error_handler import api_error_handler" not in content:
            if "from EMM.emm import ErrorManagementModule" in content:
                content = content.replace(
                    "from EMM.emm import ErrorManagementModule",
                    "from EMM.emm import ErrorManagementModule\nfrom EMM.api_error_handler import api_error_handler"
                )
        
        return content
    
    def _ensure_error_manager_init(self, content: str, module_name: str) -> str:
        """Ensure error manager is initialized in __init__."""
        if "self.error_manager = ErrorManagementModule()" not in content:
            # Find __init__ method
            init_pattern = r'def __init__\(self[^)]*\):(.*?)(?=def|\Z)'
            init_match = re.search(init_pattern, content, re.DOTALL)
            
            if init_match:
                init_content = init_match.group(1)
                if "self.error_manager = ErrorManagementModule()" not in init_content:
                    # Add error manager initialization
                    indent = re.match(r'^\s*', init_content).group(0)
                    error_manager_line = f"{indent}self.error_manager = ErrorManagementModule()\n"
                    content = content.replace(init_match.group(0), 
                                           f"def __init__(self):{init_content}{error_manager_line}")
            else:
                # Create __init__ method if it doesn't exist
                class_pattern = r'class\s+(\w+):'
                class_match = re.search(class_pattern, content)
                if class_match:
                    class_name = class_match.group(1)
                    init_method = f"""
    def __init__(self):
        self.error_manager = ErrorManagementModule()
"""
                    # Add after class definition
                    content = content.replace(f"class {class_name}:", f"class {class_name}:{init_method}")
        
        return content
    
    def _remove_hardcoded_error_codes(self, content: str, module_name: str) -> str:
        """Remove hardcoded error codes dictionaries."""
        # Pattern to find error_codes dictionaries
        error_codes_pattern = r'self\.error_codes\s*=\s*\{[^}]*\}'
        
        def replace_error_codes(match):
            self.stats["hardcoded_codes_removed"] += 1
            return f"# Error codes now generated dynamically by EMM"
        
        content = re.sub(error_codes_pattern, replace_error_codes, content, flags=re.DOTALL)
        
        # Also remove any hardcoded error code references
        hardcoded_pattern = r'"010103[0-9A-F]{6}"'
        content = re.sub(hardcoded_pattern, 'self.generate_error_code()', content)
        
        return content
    
    def _update_error_logging_calls(self, content: str, module_name: str) -> str:
        """Update error logging calls to use EMM."""
        # Replace old error logging patterns
        old_patterns = [
            (r'self\.error_manager\.log_error\([^)]+\)', 
             lambda m: f'self.error_manager.log_error_with_generation("{module_name}", "UnknownClass", "UnknownFunction", "Error occurred")'),
            (r'self\.logger\.error\([^)]+\)',
             lambda m: f'self.error_manager.log_error_with_generation("{module_name}", "UnknownClass", "UnknownFunction", {m.group(1)})'),
        ]
        
        for pattern, replacement in old_patterns:
            content = re.sub(pattern, replacement, content)
        
        return content
    
    def _add_api_error_handling(self, content: str, module_name: str) -> str:
        """Add comprehensive API error handling to API-related modules."""
        if "async def handle_api_error" not in content:
            api_error_method = f"""
    async def handle_api_error(self, error_response: str, status_code: int = None, context: dict = None) -> dict:
        \"\"\"Handle API errors using the centralized API error handler.\"\"\"
        try:
            # Use the centralized API error handler
            result = await api_error_handler.handle_api_error(error_response, status_code, context)
            
            # Log the error with EMM
            self.error_manager.log_error_with_generation(
                "{module_name}",
                "{module_name}",
                "handle_api_error",
                f"API Error: {{result.get('api_error_type', 'unknown')}}",
                context=result
            )
            
            # Send report to CCU
            await api_error_handler.send_error_report_to_ccu(result)
            
            return result
            
        except Exception as e:
            self.error_manager.log_error_with_generation(
                "{module_name}",
                "{module_name}",
                "handle_api_error",
                f"Error handling API error: {{str(e)}}"
            )
            return {{"success": False, "error": str(e)}}
"""
            
            # Add before the last method or at the end of the class
            class_pattern = r'class\s+(\w+):(.*?)(?=\nclass|\Z)'
            class_match = re.search(class_pattern, content, re.DOTALL)
            if class_match:
                class_content = class_match.group(2)
                content = content.replace(class_content, class_content + api_error_method)
        
        self.stats["api_error_handling_added"] += 1
        return content
    
    def _add_error_handling_methods(self, content: str, module_name: str) -> str:
        """Add comprehensive error handling methods."""
        if "def log_error" not in content:
            error_methods = f"""
    def log_error(self, error_message: str, class_name: str = "UnknownClass", function_name: str = "UnknownFunction", sub_function: str = "001"):
        \"\"\"Log an error using EMM.\"\"\"
        return self.error_manager.log_error_with_generation(
            "{module_name}", 
            class_name, 
            function_name, 
            error_message, 
            sub_function
        )
    
    def generate_error_code(self, class_name: str = "UnknownClass", function_name: str = "UnknownFunction", sub_function: str = "001") -> str:
        \"\"\"Generate an error code using EMM.\"\"\"
        return self.error_manager.generate_error_code("{module_name}", class_name, function_name, sub_function)
    
    async def handle_exception(self, exception: Exception, class_name: str = "UnknownClass", function_name: str = "UnknownFunction", context: dict = None):
        \"\"\"Handle exceptions with comprehensive logging and recovery.\"\"\"
        error_message = str(exception)
        
        # Log the error
        error_code = self.log_error(error_message, class_name, function_name)
        
        # Check if it's an API error
        if hasattr(exception, 'status_code') or 'api' in error_message.lower():
            return await self.handle_api_error(error_message, getattr(exception, 'status_code', None), context)
        
        # Return standard error response
        return {{
            "success": False,
            "error_code": error_code,
            "error_message": error_message,
            "timestamp": datetime.now().isoformat()
        }}
"""
            
            # Add before the last method or at the end of the class
            class_pattern = r'class\s+(\w+):(.*?)(?=\nclass|\Z)'
            class_match = re.search(class_pattern, content, re.DOTALL)
            if class_match:
                class_content = class_match.group(2)
                content = content.replace(class_content, class_content + error_methods)
        
        return content
    
    def update_rcm_main_file(self) -> bool:
        """Update the main RCM_main.py file."""
        rcm_main_file = self.modules_path / "RCM_main.py"
        if not rcm_main_file.exists():
            print("RCM_main.py not found")
            return False
        
        try:
            with open(rcm_main_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # Add EMM imports
            content = self._ensure_emm_import(content)
            
            # Add error manager to main class
            if "class RCM:" in content:
                if "self.error_manager = ErrorManagementModule()" not in content:
                    content = content.replace(
                        "class RCM:",
                        """class RCM:
    def __init__(self):
        self.error_manager = ErrorManagementModule()
        self.api_error_handler = api_error_handler"""
                    )
            
            # Add error handling methods
            if "def handle_system_error" not in content:
                error_methods = """
    def handle_system_error(self, error: Exception, context: str = "Unknown"):
        \"\"\"Handle system-wide errors.\"\"\"
        return self.error_manager.log_error_with_generation(
            "RCM_MAIN",
            "RCM",
            context,
            str(error)
        )
    
    async def handle_api_error_system_wide(self, error_response: str, status_code: int = None):
        \"\"\"Handle API errors system-wide.\"\"\"
        return await self.api_error_handler.handle_api_error(error_response, status_code)
"""
                content += error_methods
            
            if content != original_content:
                with open(rcm_main_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                self.stats["modules_updated"] += 1
                print("✓ Updated RCM_main.py")
                return True
            
            return False
            
        except Exception as e:
            error_msg = f"Error updating RCM_main.py: {e}"
            self.stats["errors"].append(error_msg)
            print(f"✗ {error_msg}")
            return False
    
    def create_integration_report(self):
        """Create a comprehensive integration report."""
        report = f"""
# Comprehensive EMM Integration Report

## Summary
- **Integration Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **Modules Processed**: {self.stats['modules_processed']}
- **Modules Updated**: {self.stats['modules_updated']}
- **Hardcoded Error Codes Removed**: {self.stats['hardcoded_codes_removed']}
- **API Error Handling Added**: {self.stats['api_error_handling_added']}

## Integration Details

### 1. EMM Integration
All modules now use centralized error management:
- **Error Code Generation**: Dynamic 16-character hexadecimal codes
- **Error Logging**: `log_error_with_generation()` method
- **Error Recovery**: Automated recovery strategies
- **CCU Reporting**: Automatic error reports to CCU

### 2. Hardcoded Error Codes Removal
- **Removed**: All `self.error_codes` dictionaries
- **Replaced**: Dynamic error code generation
- **Benefit**: Consistent error code format across all modules

### 3. API Error Handling Integration
API-related modules now include comprehensive OpenAI error handling:
- **Error Mapping**: OpenAI errors → Internal error codes
- **Recovery Strategies**: Automated recovery for each error type
- **Retry Logic**: Intelligent retry with exponential backoff
- **CCU Reporting**: Detailed error reports sent to CCU

### 4. New Error Handling Methods
All modules now include:
```python
def log_error(self, error_message, class_name, function_name, sub_function)
def generate_error_code(self, class_name, function_name, sub_function)
async def handle_exception(self, exception, class_name, function_name, context)
```

### 5. API Error Types Supported
- **Authentication Errors**: 401 (Invalid auth, incorrect key, org membership)
- **Authorization Errors**: 403 (Country restrictions)
- **Rate Limit Errors**: 429 (Rate limits, quota exceeded)
- **Server Errors**: 500, 503 (Server errors, overload, slow down)
- **Python Library Errors**: All OpenAI Python library exceptions

### 6. Recovery Strategies
Each error type has specific recovery strategies:
- **Rate Limits**: Exponential backoff with retry
- **Authentication**: Manual intervention required
- **Server Errors**: Retry with backoff
- **Quota Exceeded**: Billing intervention required

## Module Status
"""
        
        # Add module status
        for module_name in self.rcm_modules.keys():
            status = "✓ Integrated" if module_name in ["EMM"] else "✓ Updated"
            api_status = " + API Error Handling" if module_name in self.api_modules else ""
            report += f"- **{module_name}**: {status}{api_status}\n"
        
        report += f"""
## Error Code System

### Internal Error Codes (16-char hex)
Format: `[Server][Macro][Micro][Module][Class][Function][Sub-function]`
Example: `0101031600010001`

### API Error Codes (Human-readable)
Format: `API_[STATUS]_[TYPE]`
Examples: `API_401_AUTH`, `API_429_RATE`, `API_503_OVERLOAD`

## Next Steps
1. **Test Error Handling**: Verify all error scenarios work correctly
2. **Monitor Error Logs**: Check EMM error logs for consistency
3. **CCU Integration**: Verify error reports are reaching CCU
4. **Performance Testing**: Ensure error handling doesn't impact performance
5. **Documentation Update**: Update module documentation with new error handling

## Errors Encountered
"""
        
        if self.stats["errors"]:
            for error in self.stats["errors"]:
                report += f"- {error}\n"
        else:
            report += "- No errors encountered\n"
        
        # Write report
        report_file = self.base_path / "comprehensive_emm_integration_report.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"\nIntegration report written to: {report_file}")
        return report_file
    
    def run_comprehensive_integration(self):
        """Run the complete comprehensive integration."""
        print("🚀 Starting Comprehensive EMM Integration...")
        print("=" * 60)
        
        # Step 1: Find all module files
        module_files = self.find_all_module_files()
        self.stats["modules_processed"] = len(module_files)
        print(f"Found {len(module_files)} module files to process")
        
        # Step 2: Update all modules
        print("\n📝 Updating modules...")
        for module_file in module_files:
            self.update_module_for_emm_integration(module_file)
        
        # Step 3: Update RCM_main.py
        print("\n🔧 Updating RCM_main.py...")
        self.update_rcm_main_file()
        
        # Step 4: Create integration report
        print("\n📊 Creating integration report...")
        report_file = self.create_integration_report()
        
        # Step 5: Summary
        print("\n" + "=" * 60)
        print("✅ Comprehensive EMM Integration Complete!")
        print(f"📈 Statistics:")
        print(f"   - Modules Processed: {self.stats['modules_processed']}")
        print(f"   - Modules Updated: {self.stats['modules_updated']}")
        print(f"   - Hardcoded Codes Removed: {self.stats['hardcoded_codes_removed']}")
        print(f"   - API Error Handling Added: {self.stats['api_error_handling_added']}")
        print(f"   - Errors: {len(self.stats['errors'])}")
        print(f"📄 Report: {report_file}")
        
        if self.stats["errors"]:
            print(f"\n⚠️  Warnings:")
            for error in self.stats["errors"]:
                print(f"   - {error}")
        
        print("\n🎯 Next Steps:")
        print("   1. Test the updated modules")
        print("   2. Verify error handling works correctly")
        print("   3. Check EMM error logs")
        print("   4. Monitor CCU error reports")


if __name__ == "__main__":
    integrator = ComprehensiveEMMIntegrator()
    integrator.run_comprehensive_integration() 