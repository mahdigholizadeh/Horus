#!/usr/bin/env python3
"""
T0000049: Fix Remaining Module Aliases Test

This test checks and fixes any remaining missing aliases in modules to ensure
100% compatibility and proper global instance definitions.
"""

import asyncio
import os
from pathlib import Path
from typing import Dict, Any

# Add parent directory to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

class AliasFixTester:
    """Test and fix remaining module aliases."""
    
    def __init__(self):
        self.test_results = {
            "modules_checked": 0,
            "aliases_fixed": 0,
            "already_correct": 0,
            "errors": []
        }
        
        # Modules that might need aliases
        self.modules_to_check = [
            "BAAIM", "SAAIM", "AAAIM", "OCMIM", "JFAIM", "SMSM", "SMCM", "DCMM"
        ]
    
    def check_module_alias(self, module_name: str) -> bool:
        """Check if a module has proper aliases."""
        try:
            module_file = Path(f"../{module_name}/{module_name.lower()}.py")
            
            if not module_file.exists():
                self.test_results["errors"].append(f"Module file not found: {module_file}")
                return False
            
            with open(module_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for both lowercase and uppercase aliases
            has_lowercase = f"{module_name.lower()} = " in content
            has_uppercase = f"{module_name} = " in content
            
            if has_lowercase and has_uppercase:
                print(f"✓ {module_name} already has proper aliases")
                self.test_results["already_correct"] += 1
                return True
            else:
                print(f"✗ {module_name} missing aliases")
                return False
                
        except Exception as e:
            self.test_results["errors"].append(f"Error checking {module_name}: {e}")
            return False
    
    def fix_module_alias(self, module_name: str) -> bool:
        """Fix missing aliases in a module."""
        try:
            module_file = Path(f"../{module_name}/{module_name.lower()}.py")
            
            if not module_file.exists():
                self.test_results["errors"].append(f"Module file not found: {module_file}")
                return False
            
            with open(module_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Get the correct class name based on module
            class_names = {
                "BAAIM": "BasicAPIActivationModule",
                "SAAIM": "SpecialAPIActivationModule", 
                "AAAIM": "AgenticAPIActivationModule",
                "OCMIM": "OCMInteractionModule",
                "JFAIM": "JFAInteractionModule",
                "SMSM": "SystemMessageSubjoinModule",
                "SMCM": "SystemModelChangerModule",
                "DCMM": "DatabaseControlAndManagementModule"
            }
            
            class_name = class_names.get(module_name, f"{module_name}Module")
            
            # Check if aliases already exist
            if f"{module_name.lower()} = " in content and f"{module_name} = " in content:
                print(f"✓ {module_name} already has proper aliases")
                return True
            
            # Add aliases at the end of the file
            alias_code = f"""

# Global instances for compatibility
{module_name.lower()} = {class_name}()
{module_name} = {class_name}()
"""
            
            with open(module_file, 'w', encoding='utf-8') as f:
                f.write(content + alias_code)
            
            print(f"✓ Fixed aliases for {module_name}")
            self.test_results["aliases_fixed"] += 1
            return True
            
        except Exception as e:
            self.test_results["errors"].append(f"Error fixing {module_name}: {e}")
            return False
    
    async def run_test(self) -> Dict[str, Any]:
        """Run the alias fixing test."""
        print("=" * 60)
        print("T0000049: FIX REMAINING MODULE ALIASES TEST")
        print("=" * 60)
        
        print(f"\nChecking {len(self.modules_to_check)} modules for proper aliases...")
        
        for module_name in self.modules_to_check:
            self.test_results["modules_checked"] += 1
            
            # Check if aliases are correct
            if not self.check_module_alias(module_name):
                # Fix the aliases
                self.fix_module_alias(module_name)
        
        # Verify all fixes
        print(f"\nVerifying all aliases are now correct...")
        all_correct = True
        for module_name in self.modules_to_check:
            if not self.check_module_alias(module_name):
                all_correct = False
        
        success = all_correct and len(self.test_results["errors"]) == 0
        
        return {
            "success": success,
            "test_code": "T0000049",
            "test_name": "Fix Remaining Module Aliases Test",
            "message": f"Fixed {self.test_results['aliases_fixed']} modules, {self.test_results['already_correct']} were already correct",
            "details": self.test_results
        }


async def main():
    """Main test function."""
    tester = AliasFixTester()
    result = await tester.run_test()
    
    print(f"\nTest Result: {result}")
    return result


if __name__ == "__main__":
    result = asyncio.run(main())
    print(f"\nFinal Result: {result}") 