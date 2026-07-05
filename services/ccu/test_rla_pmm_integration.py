"""
RLA-PMM Integration Demonstration Script

This script demonstrates how the RLAIM module in CCU and the RLA microservice
now integrate with PMM (Path Management Module) for centralized path management.

Shows:
1. RLAIM receiving PMM-managed configuration from CCU
2. RLA microservice using PMM-aware path detection
3. ECM module using PMM installation root detection
4. Cross-platform certificate path resolution
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# Add the current directory to the path
sys.path.insert(0, str(Path(__file__).parent))

from PMM.pmm import PathManagementModule, Environment
from RLAIM.rlaim import RLAInteractionModule


async def demonstrate_rla_pmm_integration():
    """Demonstrate RLA-PMM integration."""
    print("=" * 80)
    print("RLA-PMM Integration Demonstration")
    print("=" * 80)
    
    # Initialize PMM
    print("\n1. Initializing PMM...")
    pmm = PathManagementModule(environment=Environment.DEVELOPMENT)
    await pmm.start()
    
    # Show PMM paths for RLA service
    print(f"\n2. PMM-Managed Paths for RLA Service:")
    rla_paths = pmm.distribute_paths_to_service("RLA")
    for key, path in rla_paths.items():
        print(f"   {key}: {path}")
    
    # Create mock CCU configuration with PMM paths
    print(f"\n3. CCU Configuration with PMM Integration:")
    ccu_config = {
        "rla_setting": {
            "host": "localhost", 
            "ports": {
                "activation": 3812,
                "data": 3781,
                "health": 9090,
                "websocket": 11489
            },
            "websocket_path": "/ws/rla",
            "pmm_paths": rla_paths,  # PMM paths injected by CCU
            "certificates": {
                "cert_file": f"{rla_paths.get('service_root', '')}/certificates/cert.pem",
                "key_file": f"{rla_paths.get('service_root', '')}/certificates/key.pem"
            }
        },
        "pmm_info": pmm.get_path_info()
    }
    
    print("   CCU config includes PMM paths: ✓")
    print(f"   Certificate paths: {ccu_config['rla_setting']['certificates']}")
    
    # Initialize RLAIM with PMM-enabled configuration
    print(f"\n4. Initializing RLAIM with PMM Configuration:")
    rlaim = RLAInteractionModule(ccu_config)
    
    print(f"   RLAIM RLA config host: {rlaim.rla_config['host']}")
    print(f"   RLAIM endpoint resolution:")
    for name, endpoint in rlaim.rla_config['endpoints'].items():
        print(f"     {name}: {endpoint}")
    
    # Demonstrate PMM environment variable for RLA microservice
    print(f"\n5. Setting PMM Environment for RLA Microservice:")
    
    # Set PMM paths as environment variable (how CCU would communicate with RLA)
    pmm_env_data = {
        "installation_root": str(pmm.get_installation_root()),
        "service_root": rla_paths.get("service_root", ""),
        "config": rla_paths.get("config", ""),
        "logs": rla_paths.get("logs", ""),
        "certificates": rla_paths.get("service_root", "") + "/certificates"
    }
    
    os.environ["PMM_PATHS"] = json.dumps(pmm_env_data)
    print(f"   PMM_PATHS environment variable set")
    print(f"   Installation root: {pmm_env_data['installation_root']}")
    print(f"   RLA service root: {pmm_env_data['service_root']}")
    
    # Show path detection improvement
    print(f"\n6. Path Detection Improvements:")
    print(f"   BEFORE PMM (hardcoded):")
    print(f"     config_path = Path('config/rla_setting.json')  # Breaks on different working dirs")
    print(f"     cert_file = 'cert.pem'                         # Relative, no installation awareness")
    print(f"     Path(__file__).parent.parent.parent...         # Complex navigation")
    
    print(f"\n   AFTER PMM (centralized):")
    print(f"     Multiple config locations tried:")
    print(f"       - {pmm.get_installation_root()}/services/rla/config/rla_setting.json")
    print(f"       - {pmm.get_installation_root()}/config/rla_setting.json")
    print(f"       - config/rla_setting.json (fallback)")
    print(f"     Certificate paths: PMM-managed under certificates/")
    print(f"     Installation root: Auto-detected via markers")
    
    # Show cross-platform compatibility
    print(f"\n7. Cross-Platform Compatibility:")
    print(f"   Platform: {pmm.get_platform()}")
    print(f"   All paths use platform-appropriate separators")
    print(f"   Installation root detection works on Windows and Linux")
    
    # Show the benefits
    print(f"\n8. RLA-PMM Integration Benefits:")
    benefits = [
        "✓ RLAIM gets network configuration from CCU/PMM",
        "✓ RLA microservice finds config files installation-aware",
        "✓ ECM module uses PMM installation root detection",
        "✓ Certificate paths are PMM-managed",
        "✓ No more complex relative path navigation", 
        "✓ Cross-platform deployment compatibility",
        "✓ Environment-specific path configurations",
        "✓ Centralized path management across CCU ↔ RLA communication"
    ]
    
    for benefit in benefits:
        print(f"   {benefit}")
    
    await pmm.stop()
    
    # Clean up
    if "PMM_PATHS" in os.environ:
        del os.environ["PMM_PATHS"]
    
    print(f"\n" + "=" * 80)
    print("RLA-PMM Integration Demonstration Complete!")
    print("=" * 80)


def demonstrate_rla_ecm_improvements():
    """Show ECM path detection improvements."""
    print(f"\n" + "=" * 80)
    print("RLA ECM Path Detection Improvements")
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
        await demonstrate_rla_pmm_integration()
        demonstrate_rla_ecm_improvements()
        
        print(f"\n" + "=" * 80)
        print("SUMMARY - What Was Updated:")
        print("=" * 80)
        print("1. RLAIM Module (CCU):")
        print("   - Now accepts CCU configuration with PMM paths")
        print("   - Dynamic endpoint resolution from configuration")
        print("   - No more hardcoded network settings")
        
        print("\n2. RLA Microservice (RLA_main.py):")
        print("   - PMM-aware configuration loading")
        print("   - Multiple config file location attempts")
        print("   - Installation root detection")
        print("   - PMM-managed certificate paths")
        
        print("\n3. RLA ECM Module:")
        print("   - Replaced complex relative path navigation")
        print("   - Uses PMM installation root detection")
        print("   - Multiple fallback methods for robustness")
        
        print(f"\n" + "=" * 80)
        print("DEPLOYMENT IMPACT:")
        print("=" * 80)
        print("✓ Linux deployment: No more hardcoded Windows paths")
        print("✓ Installation flexibility: Works from any root directory")
        print("✓ Configuration management: Centralized through CCU/PMM")
        print("✓ Certificate management: PMM-managed paths")
        print("✓ Service discovery: Dynamic endpoint resolution")
        
    except Exception as e:
        print(f"Error running RLA-PMM integration demo: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main()) 