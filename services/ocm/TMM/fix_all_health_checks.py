#!/usr/bin/env python3
"""
Comprehensive script to fix all health_check methods and indentation issues in OCM modules.
"""

import os
import re
from pathlib import Path

# Modules that need fixing
modules_to_fix = [
    'EMM/emm.py',
    'MSM/msm.py', 
    'PRFPM/prfpm.py',
    'OCVM/ocvm.py',
    'HRPM/hrpm.py',
    'BTM/btm.py',
    'RMM/rmm.py',
    'RCMIM/rcmim.py',
    'DSM/dsm.py',
    'DCM/dcm.py',
    'TDIM/tdim.py',
    'TMM/tmm.py'
]

def fix_health_check_methods(file_path: str):
    """Fix health_check methods to return Dict[str, Any] instead of bool."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Pattern to match health_check method that returns bool
        pattern = r'async def health_check\(self\) -> bool:\s*\n\s*"""Perform health check\."""\s*\n\s*return (.+?)(?=\n\s*\n|\n\s*def|\n\s*async def|\Z)'
        
        match = re.search(pattern, content, re.DOTALL)
        if match:
            return_statement = match.group(1).strip()
            
            # Create new health_check method
            new_method = f'''    async def health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        try:
            is_healthy = {return_statement}
            
            return {{
                'healthy': is_healthy,
                'is_active': self.is_active,
                'module': '{Path(file_path).stem}'
            }}
        except Exception as e:
            return {{
                'healthy': False,
                'error': str(e),
                'module': '{Path(file_path).stem}'
            }}'''
            
            # Replace the old method
            new_content = re.sub(pattern, new_method, content, flags=re.DOTALL)
            
            # Write back to file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            print(f"Fixed health_check in {file_path}")
            return True
        else:
            print(f"No health_check method found in {file_path}")
            return False
            
    except Exception as e:
        print(f"Error fixing {file_path}: {e}")
        return False

def fix_indentation_issues(file_path: str):
    """Fix indentation issues in health_check methods."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Pattern to match incorrectly indented health_check method
        pattern = r'(\s+)async def health_check\(self\) -> Dict\[str, Any\]:\s*\n\s+"""Perform health check\."""\s*\n\s+'
        
        # Check if there's an indentation issue
        if re.search(pattern, content):
            # Fix the indentation
            content = re.sub(r'(\s+)async def health_check\(self\) -> Dict\[str, Any\]:', r'    async def health_check(self) -> Dict[str, Any]:', content)
            content = re.sub(r'(\s+)"""Perform health check\."""', r'        """Perform health check."""', content)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"Fixed indentation in {file_path}")
            return True
        else:
            return False
            
    except Exception as e:
        print(f"Error fixing indentation in {file_path}: {e}")
        return False

def main():
    """Main function to fix all health_check methods and indentation issues."""
    base_path = Path(__file__).parent.parent
    
    fixed_count = 0
    for module_file in modules_to_fix:
        file_path = base_path / module_file
        if file_path.exists():
            # Fix health_check methods
            if fix_health_check_methods(str(file_path)):
                fixed_count += 1
            
            # Fix indentation issues
            fix_indentation_issues(str(file_path))
        else:
            print(f"File not found: {file_path}")
    
    print(f"\nFixed {fixed_count} out of {len(modules_to_fix)} modules")

if __name__ == "__main__":
    main() 