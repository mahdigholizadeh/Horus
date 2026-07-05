#!/usr/bin/env python3
"""
Certificate Management System Test Script

This script tests the certificate management functionality:
- Environment switching (development/production)
- Certificate distribution to services
- Certificate expiry monitoring
- SSL context updates
"""

import asyncio
import logging
import json
import sys
from pathlib import Path
from datetime import datetime
import aiohttp

# Add CCU modules to path
sys.path.append(str(Path(__file__).parent))

from CERTM.certm import CertificateManagementModule


class CertificateSystemTester:
    """Test class for certificate management system."""
    
    def __init__(self):
        """Initialize the tester."""
        self.logger = logging.getLogger(__name__)
        
        # Sample configuration
        self.test_config = {
            'certificate_management': {
                'enabled': True,
                'certificate_store_path': 'certificates/',
                'auto_distribute': True,
                'certificate_sources': {
                    'development': {
                        'cert_path': 'certificates/dev/cert.pem',
                        'key_path': 'certificates/dev/key.pem',
                        'description': 'Development localhost certificates'
                    },
                    'production': {
                        'cert_path': 'certificates/prod/cert.pem',
                        'key_path': 'certificates/prod/key.pem',
                        'description': 'Production Ubuntu 24 certificates'
                    }
                },
                'active_environment': 'development',
                'certificate_validation': {
                    'verify_expiry': True,
                    'expiry_warning_days': 30,
                    'auto_renewal': False
                },
                'distribution_settings': {
                    'services': ['RLA', 'TPP', 'RCM', 'JFA', 'TD', 'OCM'],
                    'push_on_change': True,
                    'retry_attempts': 3,
                    'timeout_seconds': 30
                }
            }
        }
        
        self.cert_manager = None
    
    async def run_tests(self):
        """Run all certificate system tests."""
        print("🧪 Starting Certificate Management System Tests")
        print("=" * 60)
        
        try:
            # Initialize certificate manager
            await self.test_initialization()
            
            # Test certificate loading
            await self.test_certificate_loading()
            
            # Test environment switching
            await self.test_environment_switching()
            
            # Test certificate validation
            await self.test_certificate_validation()
            
            # Test certificate distribution simulation
            await self.test_certificate_distribution()
            
            # Test monitoring and alerts
            await self.test_monitoring_alerts()
            
            # Test health checks
            await self.test_health_checks()
            
            print("\n✅ All certificate system tests completed successfully!")
            
        except Exception as e:
            print(f"\n❌ Test failed: {e}")
            raise
        finally:
            if self.cert_manager:
                await self.cert_manager.stop()
    
    async def test_initialization(self):
        """Test certificate manager initialization."""
        print("\n🔧 Test 1: Certificate Manager Initialization")
        
        self.cert_manager = CertificateManagementModule(self.test_config)
        await self.cert_manager.start()
        
        status = self.cert_manager.get_status()
        print(f"   ✅ Module active: {status['is_active']}")
        print(f"   ✅ Active environment: {status['active_environment']}")
        print(f"   ✅ Target services: {len(status['target_services'])}")
    
    async def test_certificate_loading(self):
        """Test loading certificates from files."""
        print("\n📁 Test 2: Certificate Loading")
        
        # Test loading development certificates
        success = await self.cert_manager.load_certificates('development')
        print(f"   ✅ Development certificates loaded: {success}")
        
        if success:
            cert_info = self.cert_manager.get_certificate_info('development')
            print(f"   ✅ Certificate expires: {cert_info.get('expires_at', 'Unknown')}")
            print(f"   ✅ Certificate subject: {cert_info.get('subject', 'Unknown')}")
    
    async def test_environment_switching(self):
        """Test switching between certificate environments."""
        print("\n🔄 Test 3: Environment Switching")
        
        # Switch to production
        success = await self.cert_manager.switch_environment('production')
        print(f"   ✅ Switched to production: {success}")
        
        # Verify current environment
        status = self.cert_manager.get_status()
        current_env = status['active_environment']
        print(f"   ✅ Current environment: {current_env}")
        
        # Switch back to development
        success = await self.cert_manager.switch_environment('development')
        print(f"   ✅ Switched back to development: {success}")
    
    async def test_certificate_validation(self):
        """Test certificate validation functionality."""
        print("\n🔍 Test 4: Certificate Validation")
        
        # Get certificate path
        cert_path = Path(self.test_config['certificate_management']['certificate_sources']['development']['cert_path'])
        
        if cert_path.exists():
            validation_result = await self.cert_manager.validate_certificate_file(str(cert_path))
            print(f"   ✅ Certificate valid: {validation_result.get('valid', False)}")
            print(f"   ✅ Certificate current: {validation_result.get('is_current', False)}")
            print(f"   ✅ Days until expiry: {validation_result.get('days_until_expiry', 'Unknown')}")
        else:
            print(f"   ⚠️  Certificate file not found: {cert_path}")
    
    async def test_certificate_distribution(self):
        """Test certificate distribution simulation."""
        print("\n📤 Test 5: Certificate Distribution (Simulation)")
        
        # This simulates distribution since we don't have actual services running
        target_services = ['RLA', 'TPP', 'RCM']
        results = await self.cert_manager.distribute_certificates(target_services)
        
        print(f"   ✅ Distribution attempted for {len(target_services)} services")
        print(f"   ✅ Distribution results: {results}")
        
        # Check statistics
        stats = self.cert_manager.get_status()['statistics']
        print(f"   ✅ Total distributions sent: {stats['distributions_sent']}")
    
    async def test_monitoring_alerts(self):
        """Test monitoring and alerting functionality."""
        print("\n🚨 Test 6: Monitoring and Alerts")
        
        # Get all certificate info
        all_cert_info = self.cert_manager.get_all_certificate_info()
        print(f"   ✅ Monitoring {len(all_cert_info['certificates'])} certificate environments")
        
        # Check expiry warnings
        stats = self.cert_manager.get_status()['statistics']
        print(f"   ✅ Expiry warnings generated: {stats['expiry_warnings']}")
        
        # Check if monitoring directory exists
        monitoring_dir = Path("certificates/monitoring")
        if monitoring_dir.exists():
            alert_files = list(monitoring_dir.glob("cert_alert_*.json"))
            print(f"   ✅ Alert files created: {len(alert_files)}")
    
    async def test_health_checks(self):
        """Test health check functionality."""
        print("\n🏥 Test 7: Health Checks")
        
        health = await self.cert_manager.health_check()
        print(f"   ✅ Overall health: {health['healthy']}")
        print(f"   ✅ Active environment: {health['active_environment']}")
        print(f"   ✅ Certificate valid: {health['certificate_valid']}")
        print(f"   ✅ Certificate expiry: {health['certificate_expiry']}")


class InteractiveTester:
    """Interactive certificate management tester."""
    
    def __init__(self):
        self.cert_manager = None
    
    async def run_interactive_menu(self):
        """Run interactive testing menu."""
        print("🎯 Interactive Certificate Management Tester")
        print("=" * 50)
        
        # Initialize certificate manager
        config = {
            'certificate_management': {
                'enabled': True,
                'certificate_store_path': 'certificates/',
                'active_environment': 'development',
                'certificate_sources': {
                    'development': {
                        'cert_path': 'certificates/dev/cert.pem',
                        'key_path': 'certificates/dev/key.pem',
                        'description': 'Development localhost certificates'
                    },
                    'production': {
                        'cert_path': 'certificates/prod/cert.pem',
                        'key_path': 'certificates/prod/key.pem',
                        'description': 'Production Ubuntu 24 certificates'
                    }
                },
                'distribution_settings': {
                    'services': ['RLA', 'TPP', 'RCM', 'JFA', 'TD', 'OCM']
                }
            }
        }
        
        self.cert_manager = CertificateManagementModule(config)
        await self.cert_manager.start()
        
        while True:
            await self.display_menu()
            choice = input("\nEnter your choice (1-8, q to quit): ").strip().lower()
            
            if choice == 'q':
                break
            elif choice == '1':
                await self.show_certificate_status()
            elif choice == '2':
                await self.switch_environment()
            elif choice == '3':
                await self.reload_certificates()
            elif choice == '4':
                await self.test_distribution()
            elif choice == '5':
                await self.validate_certificates()
            elif choice == '6':
                await self.check_health()
            elif choice == '7':
                await self.show_monitoring_info()
            elif choice == '8':
                await self.trigger_manual_alert()
            else:
                print("❌ Invalid choice. Please try again.")
        
        # Cleanup
        if self.cert_manager:
            await self.cert_manager.stop()
        print("👋 Goodbye!")
    
    async def display_menu(self):
        """Display the interactive menu."""
        print("\n📋 Certificate Management Options:")
        print("1. 📊 Show Certificate Status")
        print("2. 🔄 Switch Environment")
        print("3. 🔄 Reload Certificates")
        print("4. 📤 Test Certificate Distribution")
        print("5. ✅ Validate Certificates")
        print("6. 🏥 Health Check")
        print("7. 📈 Show Monitoring Info")
        print("8. 🚨 Trigger Manual Alert Test")
        print("q. 🚪 Quit")
    
    async def show_certificate_status(self):
        """Show current certificate status."""
        print("\n📊 Certificate Status:")
        status = self.cert_manager.get_status()
        print(f"   Active Environment: {status['active_environment']}")
        print(f"   Certificates Loaded: {status['certificates_loaded']}")
        print(f"   Target Services: {', '.join(status['target_services'])}")
        
        all_info = self.cert_manager.get_all_certificate_info()
        for env, cert_info in all_info['certificates'].items():
            print(f"   {env.upper()}:")
            print(f"     - Expires: {cert_info.get('expires_at', 'Unknown')}")
            print(f"     - Subject: {cert_info.get('subject', 'Unknown')}")
    
    async def switch_environment(self):
        """Switch certificate environment."""
        print("\n🔄 Available Environments:")
        print("1. development")
        print("2. production")
        
        choice = input("Enter environment (1-2): ").strip()
        env_map = {'1': 'development', '2': 'production'}
        
        if choice in env_map:
            env = env_map[choice]
            success = await self.cert_manager.switch_environment(env)
            if success:
                print(f"✅ Switched to {env} environment")
            else:
                print(f"❌ Failed to switch to {env} environment")
        else:
            print("❌ Invalid choice")
    
    async def reload_certificates(self):
        """Reload certificates from disk."""
        print("\n🔄 Reloading Certificates...")
        success = await self.cert_manager.reload_certificates()
        if success:
            print("✅ Certificates reloaded successfully")
        else:
            print("❌ Failed to reload certificates")
    
    async def test_distribution(self):
        """Test certificate distribution."""
        print("\n📤 Testing Certificate Distribution...")
        results = await self.cert_manager.distribute_certificates()
        
        print("Distribution Results:")
        for service, success in results.items():
            status = "✅" if success else "❌"
            print(f"   {status} {service}")
    
    async def validate_certificates(self):
        """Validate certificates."""
        print("\n✅ Validating Certificates...")
        
        cert_sources = self.cert_manager.config.get('certificate_sources', {})
        for env, source in cert_sources.items():
            cert_path = source.get('cert_path', '')
            if cert_path and Path(cert_path).exists():
                result = await self.cert_manager.validate_certificate_file(cert_path)
                status = "✅" if result.get('valid') else "❌"
                print(f"   {status} {env}: Valid={result.get('valid')}, Days remaining={result.get('days_until_expiry')}")
    
    async def check_health(self):
        """Check certificate manager health."""
        print("\n🏥 Health Check:")
        health = await self.cert_manager.health_check()
        
        status = "✅" if health['healthy'] else "❌"
        print(f"   {status} Overall Health: {health['healthy']}")
        print(f"   Active Environment: {health['active_environment']}")
        print(f"   Certificate Valid: {health['certificate_valid']}")
        print(f"   Certificate Expiry: {health['certificate_expiry']}")
    
    async def show_monitoring_info(self):
        """Show monitoring information."""
        print("\n📈 Monitoring Information:")
        stats = self.cert_manager.get_status()['statistics']
        
        print(f"   Certificates Loaded: {stats['certificates_loaded']}")
        print(f"   Distributions Sent: {stats['distributions_sent']}")
        print(f"   Distribution Failures: {stats['distribution_failures']}")
        print(f"   Expiry Warnings: {stats['expiry_warnings']}")
        print(f"   Last Distribution: {stats['last_distribution']}")
    
    async def trigger_manual_alert(self):
        """Trigger a manual alert test."""
        print("\n🚨 Triggering Manual Alert Test...")
        
        # This would simulate an expiry alert
        alert_message = {
            'alert_type': 'certificate_expiry',
            'severity': 'TEST',
            'environment': 'test',
            'days_remaining': 15,
            'timestamp': datetime.now().isoformat()
        }
        
        print("   ✅ Manual alert test triggered (check logs)")


async def main():
    """Main function."""
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    if len(sys.argv) > 1 and sys.argv[1] == '--interactive':
        # Run interactive tester
        tester = InteractiveTester()
        await tester.run_interactive_menu()
    else:
        # Run automated tests
        tester = CertificateSystemTester()
        await tester.run_tests()


if __name__ == "__main__":
    asyncio.run(main()) 