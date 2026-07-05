"""
TPP-PMM Integration Demonstration Script

This script demonstrates how the TPPIM module in CCU and the TPP microservice
now integrate with PMM (Path Management Module) for centralized path management.

Shows:
1. TPPIM receiving PMM-managed configuration from CCU
2. TPP microservice using PMM-aware path detection  
3. ECM module using PMM installation root detection
4. Cross-platform file processing path resolution
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# Add the current directory to the path
sys.path.insert(0, str(Path(__file__).parent))

from PMM.pmm import PathManagementModule, Environment
from TPPIM.tppim import TPPInteractionModule


async def demonstrate_tpp_pmm_integration():
    """Demonstrate TPP-PMM integration."""
    print("=" * 80)
    print("TPP-PMM Integration Demonstration")
    print("=" * 80)
    
    # Initialize PMM
    print("\n1. Initializing PMM...")
    pmm = PathManagementModule(environment=Environment.DEVELOPMENT)
    await pmm.start()
    
    # Show PMM paths for TPP service
    print(f"\n2. PMM-Managed Paths for TPP Service:")
    tpp_paths = pmm.distribute_paths_to_service("TPP")
    for key, path in tpp_paths.items():
        print(f"   {key}: {path}")
    
    # Create mock CCU configuration with PMM paths
    print(f"\n3. CCU Configuration with PMM Integration:")
    ccu_config = {
        "tpp_setting": {
            "service_name": "TPP",
            "host": "localhost",
            "ports": {
                "api": 8080,
                "health": 9091,
                "websocket": 11490
            },
            "timeout": 30,
            "max_retries": 3,
            "retry_delay": 5,
            "pmm_paths": tpp_paths,  # PMM paths injected by CCU
            "file_processing": {
                "temp_directory": f"{tpp_paths.get('temp', '')}/",
                "input_directory": f"{tpp_paths.get('input', '')}/",
                "output_directory": f"{tpp_paths.get('output', '')}/"
            }
        },
        "pmm_info": pmm.get_path_info()
    }
    
    print("   CCU config includes PMM paths: ✓")
    print(f"   File processing paths: {ccu_config['tpp_setting']['file_processing']}")
    
    # Initialize TPPIM with PMM-enabled configuration
    print(f"\n4. Initializing TPPIM with PMM Configuration:")
    tppim = TPPInteractionModule(ccu_config)
    
    print(f"   TPPIM TPP config host: {tppim.tpp_config['host']}")
    print(f"   TPPIM network configuration:")
    for key, value in tppim.tpp_config.items():
        if key in ['api_port', 'health_port', 'websocket_port']:
            print(f"     {key}: {value}")
    
    # Demonstrate PMM environment variable for TPP microservice
    print(f"\n5. Setting PMM Environment for TPP Microservice:")
    
    # Set PMM paths as environment variable (how CCU would communicate with TPP)
    pmm_env_data = {
        "installation_root": str(pmm.get_installation_root()),
        "service_root": tpp_paths.get("service_root", ""),
        "config": tpp_paths.get("config", ""),
        "logs": tpp_paths.get("logs", ""),
        "temp": tpp_paths.get("temp", ""),
        "input": tpp_paths.get("input", ""),
        "output": tpp_paths.get("output", "")
    }
    
    os.environ["PMM_PATHS"] = json.dumps(pmm_env_data)
    print(f"   PMM_PATHS environment variable set")
    print(f"   Installation root: {pmm_env_data['installation_root']}")
    print(f"   TPP service root: {pmm_env_data['service_root']}")
    
    # Show path detection improvement
    print(f"\n6. Path Detection Improvements:")
    print(f"   BEFORE PMM (hardcoded):")
    print(f"     config_path = Path('config/tpp_setting.json')  # Breaks on different working dirs")
    print(f"     temp_directory = 'temp'                        # Relative, no installation awareness")
    print(f"     Path(__file__).parent.parent.parent...         # Complex navigation")
    
    print(f"\n   AFTER PMM (centralized):")
    print(f"     Multiple config locations tried:")
    print(f"       - {pmm.get_installation_root()}/services/tpp/config/tpp_setting.json")
    print(f"       - {pmm.get_installation_root()}/config/tpp_setting.json")
    print(f"       - config/tpp_setting.json (fallback)")
    print(f"     File processing paths: PMM-managed under service directories")
    print(f"     Installation root: Auto-detected via markers")
    
    # Show cross-platform compatibility
    print(f"\n7. Cross-Platform Compatibility:")
    print(f"   Platform: {pmm.get_platform()}")
    print(f"   All paths use platform-appropriate separators")
    print(f"   Installation root detection works on Windows and Linux")
    
    # Show TPP-specific benefits
    print(f"\n8. TPP-Specific PMM Integration Benefits:")
    benefits = [
        "✓ TPPIM gets network configuration from CCU/PMM",
        "✓ TPP microservice finds config files installation-aware",
        "✓ ECM module uses PMM installation root detection",
        "✓ File processing paths are PMM-managed",
        "✓ Temp directories under PMM control",
        "✓ Spam word lists can use PMM-managed storage",
        "✓ Cross-platform text processing compatibility",
        "✓ Centralized path management for multilingual support"
    ]
    
    for benefit in benefits:
        print(f"   {benefit}")
    
    await pmm.stop()
    
    # Clean up
    if "PMM_PATHS" in os.environ:
        del os.environ["PMM_PATHS"]
    
    print(f"\n" + "=" * 80)
    print("TPP-PMM Integration Demonstration Complete!")
    print("=" * 80)


def demonstrate_tpp_ecm_improvements():
    """Show TPP ECM path detection improvements."""
    print(f"\n" + "=" * 80)
    print("TPP ECM Path Detection Improvements")
    print("=" * 80)
    
    print(f"\nBEFORE PMM Integration:")
    print(f"  ❌ Complex relative navigation:")
    print(f"     codebase_path = Path(__file__).parent.parent.parent.parent.parent.parent")
    print(f"  ❌ Brittle - breaks if file moves or directory structure changes")
    print(f"  ❌ Platform-dependent path assumptions")
    
    print(f"\nAFTER PMM Integration:")
    print(f"  ✓ Multiple detection methods:")
    print(f"    1. PMM environment variable (preferred)")  
    print(f"    2. Installation marker detection (JFA_CONFIGURATION_PLAN.md, LICENSE.txt, etc.)")
    print(f"    3. Fallback to old method if needed")
    print(f"  ✓ Robust across different deployment scenarios")
    print(f"  ✓ Cross-platform compatible")
    print(f"  ✓ Self-healing - automatically finds installation root")


async def main():
    """Main demonstration function."""
    try:
        await demonstrate_tpp_pmm_integration()
        demonstrate_tpp_ecm_improvements()
        
        print(f"\n" + "=" * 80)
        print("SUMMARY - What Was Updated:")
        print("=" * 80)
        print("1. TPPIM Module (CCU):")
        print("   - Now accepts CCU configuration with PMM paths")
        print("   - Dynamic network configuration from CCU")
        print("   - No more hardcoded service settings")
        
        print("\n2. TPP Microservice (TPP_main.py):")
        print("   - PMM-aware configuration loading")
        print("   - Multiple config file location attempts")
        print("   - Installation root detection")
        print("   - PMM-managed file processing paths")
        
        print("\n3. TPP ECM Module:")
        print("   - Replaced complex relative path navigation")
        print("   - Uses PMM installation root detection")
        print("   - Multiple fallback methods for robustness")
        
        print(f"\n" + "=" * 80)
        print("DEPLOYMENT IMPACT:")
        print("=" * 80)
        print("✓ Linux deployment: No more hardcoded Windows paths")
        print("✓ Installation flexibility: Works from any root directory")
        print("✓ Configuration management: Centralized through CCU/PMM")
        print("✓ File processing: PMM-managed temp/input/output directories")
        print("✓ Text processing: Cross-platform spam word list management")
        
    except Exception as e:
        print(f"Error running TPP-PMM integration demo: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main()) 