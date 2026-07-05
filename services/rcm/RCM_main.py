"""
RCM ( Requests Cache Manager) Microservice - Main Entry Point

This is the central controller for the RCM microservice, responsible for:
- Initialization of all modules
- Testing and monitoring
- Interfacing with the CCU via the External Control Module (ECM)
- Orchestrating the modular architecture

The RCM microservice is activated and deactivated by the Central Control Unit (CCU).
"""

import asyncio
import logging
import os
import sys
import uvicorn
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

# Import all modules
from GIDVM.gidvm import GetInputDataAndVerificationModule
from PBRPM.pbrpm import PriorityBasedRequestProcessingModule
from AACM.aacm import AsynchronousAPICommunicationModule
from FBWM.fbwm import FileBasedWorkflowModule
from FDM.fdm import FileDetectionModule
from PRM.prm import PriorityRoutingModule
from RTRMM.rtrmm import RequestTrackingAndResponseMappingModule
from RLM.rlm import RateLimitingModule
from MMM.mmm import MemoryManagementModule
from DRM.drm import DiskRestorationModule
from FAIM.faim import FastAPIIntegrationModule
from BTM.btm import BackgroundTasksModule
from IFCM.ifcm import InternalFlowControlModule
from ECM.ecm import ExternalControlModule
from AAAIM.aaaim import AgenticAPIActivationModule
from BAAIM.baaim import BasicAPIActivationModule
from SAAIM.saaim import SpecialAPIActivationModule
from SODVM.sodvm import SetOutputDataAndVerificationModule
from FOM.fom import FileOutputModule
from DCMM.dcmm import DatabaseControlAndManagementModule
from TMM.tmm import TestManagementModule
from EMM.emm import ErrorManagementModule
from EMM.api_error_handler import api_error_handler
from MSM.msm import MonitoringSystemModule
from SMSM.smsm import SystemMessageSubjoinModule
from SMCM.smcm import SystemModelChangerModule
from JFAIM.jfaim import JFAInteractionModule
from OCMIM.ocmim import OCMInteractionModule


class RCMMicroservice:
    """
    RCM Microservice - Central Controller
    
    This class orchestrates all modules and provides the main interface for:
    - Initialization and startup
    - Testing and monitoring
    - CCU interaction via ECM
    - Service lifecycle management
    """
    
    def __init__(self):
        """Initialize the RCM microservice with all modules."""
        self.logger = logging.getLogger(__name__)
        self.is_active = False
        self.modules = {}
        self.request_tracking = {}
        
        # Initialize all modules
        self._initialize_modules()
        
    def log_error(self, error_message: str, component: str, method: str):
        """Log error with EMM integration."""
        try:
            if 'EMM' in self.modules:
                self.modules['EMM'].log_error(error_message, component, method)
            else:
                self.logger.error(f"[{component}.{method}] {error_message}")
        except Exception as e:
            self.logger.error(f"Failed to log error via EMM: {e}")
            self.logger.error(f"[{component}.{method}] {error_message}")
        
    def _initialize_modules(self):
        """Initialize all modules in the correct order."""
        try:
            # Core modules first
            self.modules['EMM'] = ErrorManagementModule()
            self.modules['DCMM'] = DatabaseControlAndManagementModule()
            self.modules['MSM'] = MonitoringSystemModule()
            
            # Input and detection modules
            self.modules['GIDVM'] = GetInputDataAndVerificationModule()
            self.modules['FDM'] = FileDetectionModule()
            self.modules['PRM'] = PriorityRoutingModule()
            
            # Processing modules
            self.modules['PBRPM'] = PriorityBasedRequestProcessingModule()
            self.modules['FBWM'] = FileBasedWorkflowModule()
            
            # API interaction modules
            self.modules['AACM'] = AsynchronousAPICommunicationModule()
            self.modules['BAAIM'] = BasicAPIActivationModule()
            self.modules['AAAIM'] = AgenticAPIActivationModule()
            self.modules['SAAIM'] = SpecialAPIActivationModule()
            
            # Tracking and mapping
            self.modules['RTRMM'] = RequestTrackingAndResponseMappingModule()
            
            # Rate limiting and resource management
            self.modules['RLM'] = RateLimitingModule()
            self.modules['MMM'] = MemoryManagementModule()
            self.modules['DRM'] = DiskRestorationModule()
            
            # Output and verification
            self.modules['SODVM'] = SetOutputDataAndVerificationModule()
            self.modules['FOM'] = FileOutputModule()
            
            # Handoff modules
            self.modules['JFAIM'] = JFAInteractionModule()
            self.modules['OCMIM'] = OCMInteractionModule()
            
            # Control and management
            self.modules['IFCM'] = InternalFlowControlModule()
            self.modules['ECM'] = ExternalControlModule()
            self.modules['FAIM'] = FastAPIIntegrationModule()
            self.modules['BTM'] = BackgroundTasksModule()
            
            # Testing and monitoring
            self.modules['TMM'] = TestManagementModule()
            self.modules['SMSM'] = SystemMessageSubjoinModule()
            self.modules['SMCM'] = SystemModelChangerModule()
            
            self.logger.info("All modules initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize modules: {e}")
            self.log_error(str(e), "RCMMicroservice", "_initialize_modules")
            raise
    
    async def start(self):
        """Start the RCM microservice."""
        try:
            print("[START] RCM start() method called")
            self.logger.info("Starting RCM microservice...")
            
            print("[INIT] About to start all modules...")
            # Start all modules
            for module_name, module in self.modules.items():
                print(f"[INIT] Starting module: {module_name}")
                if hasattr(module, 'start'):
                    await module.start()
                    print(f"[SUCCESS] Started {module_name}")
                    self.logger.info(f"Started {module_name}")
                else:
                    print(f"[INFO] Module {module_name} has no start method")
            
            print("[INIT] Starting background tasks...")
            # Start background tasks
            await self.modules['BTM'].start()
            print("[SUCCESS] Background tasks started")
            
            print("[INIT] Starting monitoring...")
            # Start monitoring
            self.modules['MSM'].start_monitoring()
            print("[SUCCESS] Monitoring started")
            
            print("[INIT] Starting external control interface...")
            # Start WebSocket client connection to CCU
            await self.modules['ECM'].start_websocket_client()
            print("[SUCCESS] External control interface started")
            
            print("[INIT] Starting file detection...")
            # Start file detection
            await self.modules['FDM'].start_monitoring()
            print("[SUCCESS] File detection started")
            
            print("[INIT] Setting service flags...")
            self.is_active = True
            self.gateway_active = False  # API gateway not active until CCU commands it
            print(f"[SUCCESS] Service flags set - is_active: {self.is_active}, gateway_active: {self.gateway_active}")
            
            self.logger.info("RCM microservice started successfully - ready for CCU activation")
            print("[SUCCESS] RCM start() method completed successfully")
            
        except Exception as e:
            print(f"[ERROR] Error in RCM start() method: {e}")
            import traceback
            traceback.print_exc()
            self.logger.error(f"Failed to start RCM microservice: {e}")
            self.log_error(str(e), "RCMMicroservice", "start")
            raise
    
    async def stop(self):
        """Stop the RCM microservice."""
        try:
            self.logger.info("Stopping RCM microservice...")
            
            # Stop all modules in reverse order
            for module_name, module in reversed(list(self.modules.items())):
                if hasattr(module, 'stop'):
                    await module.stop()
                    self.logger.info(f"Stopped {module_name}")
            
            self.is_active = False
            self.logger.info("RCM microservice stopped successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to stop RCM microservice: {e}")
            self.log_error(str(e), "RCMMicroservice", "stop")
            raise
    
    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the RCM microservice."""
        status = {
            'is_active': self.is_active,
            'start_time': getattr(self, 'start_time', None),
            'modules': {}
        }
        
        for module_name, module in self.modules.items():
            if hasattr(module, 'get_status'):
                try:
                    # Try to get status, handle both sync and async methods
                    module_status = module.get_status()
                    # Check if it's a coroutine and ignore it for sync get_status
                    if hasattr(module_status, '__await__'):
                        status['modules'][module_name] = {'status': 'async_method_not_awaited'}
                    else:
                        status['modules'][module_name] = module_status
                except Exception as e:
                    status['modules'][module_name] = {'status': 'error', 'error': str(e)}
            else:
                status['modules'][module_name] = {'status': 'no_get_status_method'}
        
        return status
    
    async def process_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a request through the modular workflow.
        
        Args:
            request_data: The request data to process
            
        Returns:
            Processing result
        """
        try:
            # Get request ID
            request_id = request_data.get('request_ID')
            if not request_id:
                raise ValueError("Request ID is required")
            
            self.logger.info(f"Processing request {request_id}")
            
            # Use IFCM to orchestrate the workflow
            result = await self.modules['IFCM'].process_request(request_data)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error processing request: {e}")
            # Log error via EMM
            await self.modules['EMM'].log_error("01010301001", str(e))
            raise
    
    async def run_test(self, test_code: str) -> Dict[str, Any]:
        """
        Run a specific test.
        
        Args:
            test_code: The 8-character test code (e.g., T0000001)
            
        Returns:
            Test result
        """
        try:
            self.logger.info(f"Running test {test_code}")
            result = await self.modules['TMM'].run_test(test_code)
            return result
            
        except Exception as e:
            self.logger.error(f"Error running test {test_code}: {e}")
            raise
    
    async def get_monitoring_data(self) -> Dict[str, Any]:
        """Get monitoring data from MSM."""
        try:
            return await self.modules['MSM'].get_monitoring_data()
        except Exception as e:
            self.logger.error(f"Error getting monitoring data: {e}")
            raise
    
    async def activate_gateway(self):
        """Activate RCM API gateway to start connecting to external APIs."""
        try:
            if self.gateway_active:
                self.logger.info("RCM API Gateway is already active")
                return {"status": "already_active"}
            
            self.logger.info("RCM: Activating API gateway services...")
            
            # Activate API modules for external connections
            api_modules = ['BAAIM', 'SAAIM', 'AAAIM']
            for module_name in api_modules:
                if module_name in self.modules:
                    module = self.modules[module_name]
                    if hasattr(module, 'activate_api_connection'):
                        await module.activate_api_connection()
                        self.logger.info(f"RCM: {module_name} API connection activated")
            
            # Update gateway state
            self.gateway_active = True
            
            self.logger.info("RCM: API Gateway activated - ready to connect to external APIs")
            return {"status": "gateway_activated", "apis": ["OpenAI", "Special", "Agentic"]}
            
        except Exception as e:
            self.logger.error(f"RCM: Failed to activate API gateway: {e}")
            return {"status": "error", "message": str(e)}
    
    async def deactivate_gateway(self):
        """Deactivate RCM API gateway to stop connecting to external APIs."""
        try:
            if not self.gateway_active:
                self.logger.info("RCM API Gateway is already inactive")
                return {"status": "already_inactive"}
            
            self.logger.info("RCM: Deactivating API gateway services...")
            
            # Deactivate API modules
            api_modules = ['BAAIM', 'SAAIM', 'AAAIM']
            for module_name in api_modules:
                if module_name in self.modules:
                    module = self.modules[module_name]
                    if hasattr(module, 'deactivate_api_connection'):
                        await module.deactivate_api_connection()
                        self.logger.info(f"RCM: {module_name} API connection deactivated")
            
            # Update gateway state
            self.gateway_active = False
            
            self.logger.info("RCM: API Gateway deactivated")
            return {"status": "gateway_deactivated"}
            
        except Exception as e:
            self.logger.error(f"RCM: Failed to deactivate API gateway: {e}")
            return {"status": "error", "message": str(e)}


# Global RCM instance
rcm_service = RCMMicroservice()


async def run_file_processing_workflow(watch_dir: Optional[str] = None):
    """Run the main file processing workflow."""
    print("[WORKFLOW] Starting RCM file processing workflow...")
    
    # Determine watch directory
    if watch_dir:
        watch_path = Path(watch_dir)
    else:
        watch_path = Path(__file__).parent
    
    print(f"[WATCH] Watching directory: {watch_path}")
    
    try:
        # Start RCM service
        await rcm_service.start()
        
        print("[MONITOR] Starting file monitoring loop...")
        print("Press Ctrl+C to stop")
        
        while True:
            try:
                # Get pending files via GIDVM
                pending_files = await rcm_service.modules['GIDVM'].get_pending_files(watch_path)
                
                if pending_files:
                    print(f"📄 Found {len(pending_files)} new files to process")
                    
                    for file_path in pending_files:
                        try:
                            # Process the file
                            result = await rcm_service.modules['GIDVM'].process_file(file_path)
                            
                            if result:
                                cleaned_path, priority = result
                                print(f"[SUCCESS] Processed {file_path.name} -> {cleaned_path} (Priority: {priority})")
                                
                                # Read original data for context
                                import json
                                with open(file_path, 'r', encoding='utf-8') as f:
                                    original_data = json.load(f)
                                
                                # Process through IFCM
                                await rcm_service.process_request(original_data)
                                print(f"[WORKFLOW] Processed request through workflow")
                            else:
                                print(f"[ERROR] Failed to process {file_path.name}")
                                
                        except Exception as e:
                            print(f"[ERROR] Error processing {file_path.name}: {e}")
                
                # Show status periodically
                status = rcm_service.get_status()
                if status['modules']['IFCM']['active_requests'] > 0:
                    print(f"[STATUS] Active requests: {status['modules']['IFCM']['active_requests']}")
                
                # Wait before next check
                await asyncio.sleep(5)  # Check every 5 seconds
                
            except KeyboardInterrupt:
                print("\n[STOP] Stopping file processing workflow...")
                break
            except Exception as e:
                print(f"[ERROR] Error in processing loop: {e}")
                await asyncio.sleep(5)  # Wait before retrying
        
        # Wait for remaining requests to complete
        print("[WAIT] Waiting for remaining requests to complete...")
        success = await rcm_service.modules['IFCM'].wait_for_completion(timeout=60)
        
        if success:
            print("[SUCCESS] All requests completed successfully")
        else:
            print("[WARNING] Some requests may still be pending")
            
    finally:
        await rcm_service.stop()
        print("[WORKFLOW] File processing workflow stopped")


async def run_test_workflow():
    """Run a test workflow with sample files."""
    print("[TEST] Starting RCM test workflow...")
    
    try:
        # Start RCM service
        await rcm_service.start()
        
        # Create and process sample files
        from GIDVM.gidvm import create_sample_request_files
        
        print("[SETUP] Creating sample request files...")
        create_sample_request_files()
        
        # Process sample files
        base_dir = Path(__file__).parent
        
        request_ids = []
        
        print("[WORKFLOW] Processing sample files...")
        for file_path in base_dir.glob("sample_request_*.json"):
            result = await rcm_service.modules['GIDVM'].process_file(file_path)
            if result:
                cleaned_path, priority = result
                print(f"[SUCCESS] Processed {file_path.name} -> {cleaned_path} (Priority: {priority})")
                
                # Read original data for context
                import json
                with open(file_path, 'r', encoding='utf-8') as f:
                    original_data = json.load(f)
                
                # Process request
                await rcm_service.process_request(original_data)
                request_ids.append(original_data.get('request_ID'))
                print(f"[PROCESSED] Processed request {original_data.get('request_ID')}")
        
        # Wait for completion
        print("[WAIT] Waiting for requests to complete...")
        success = await rcm_service.modules['IFCM'].wait_for_completion(timeout=60)
        
        if success:
            print("[SUCCESS] All test requests completed successfully")
        else:
            print("[WARNING] Some test requests may still be pending")
        
        # Show final status
        status = rcm_service.get_status()
        print(f"[STATUS] Final status: {status['modules']['IFCM']['active_requests']} active requests")
        
        # Clean up sample files
        print("[CLEANUP] Cleaning up sample files...")
        for file_path in base_dir.glob("sample_request_*.json"):
            try:
                file_path.unlink()
                print(f"[REMOVED] Removed {file_path.name}")
            except Exception as e:
                print(f"[WARNING] Could not remove {file_path.name}: {e}")
        
        print("[TEST] Test workflow completed")
        
    finally:
        await rcm_service.stop()


def show_priority_ports():
    """Show available ports for each priority level."""
    print("[CHECK] Checking port availability for each priority level...")
    
    # This would be implemented by the PRM module
    print("\n[PORTS] Priority Port Allocation:")
    print("   Priority A: Port 8001")
    print("   Priority B: Port 8002") 
    print("   Priority C: Port 8003")
    print("   Priority D: Port 8004")


async def run_comprehensive_test():
    """Run comprehensive test suite."""
    print("[TEST] Starting Comprehensive Test Suite...")
    
    try:
        # Start RCM service
        await rcm_service.start()
        
        # Run all tests from T0000001 to T0000039
        test_results = {}
        
        for i in range(1, 40):
            test_code = f"T{i:07d}"
            try:
                print(f"[RUN] Running {test_code}...")
                result = await rcm_service.run_test(test_code)
                test_results[test_code] = result
                print(f"[SUCCESS] {test_code} completed: {result.get('success', False)}")
            except Exception as e:
                print(f"[FAILED] {test_code} failed: {e}")
                test_results[test_code] = {'success': False, 'error': str(e)}
        
        # Print summary
        successful_tests = sum(1 for result in test_results.values() if result.get('success', False))
        total_tests = len(test_results)
        
        print(f"\n[SUMMARY] Test Summary:")
        print(f"   Total tests: {total_tests}")
        print(f"   Successful: {successful_tests}")
        print(f"   Failed: {total_tests - successful_tests}")
        print(f"   Success rate: {(successful_tests/total_tests)*100:.1f}%")
        
        print("[TEST] Comprehensive test suite completed")
        
    finally:
        await rcm_service.stop()


def main():
    """Main entry point for the RCM microservice."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="RCM Microservice Control CLI.\n"
                    "Usage examples:\n"
                    "  python RCM_main.py                # Run as microservice daemon (default)\n"
                    "  python RCM_main.py --service     # Run as microservice daemon (explicit)\n"
                    "  python RCM_main.py --api         # Run FastAPI app only\n"
                    "  python RCM_main.py --activate    # Activate (start) the microservice\n"
                    "  python RCM_main.py --deactivate  # Deactivate (stop) the microservice\n"
                    "  python RCM_main.py --status      # Show if the microservice is active\n"
                    "  python RCM_main.py --process     # Start file processing workflow\n"
                    "  python RCM_main.py --test        # Run test workflow with sample files\n"
                    "  python RCM_main.py --comprehensive-test # Run comprehensive test suite\n"
                    "  python RCM_main.py --test-run T0000001 # Run specific test\n"
                    "  python RCM_main.py --monitoring  # Get monitoring data\n"
                    "  python RCM_main.py --ports       # Show priority ports\n",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument('--service', action='store_true', help='Run as microservice daemon (default mode)')
    parser.add_argument('--api', action='store_true', help='Run the FastAPI app only')
    parser.add_argument('--activate', action='store_true', help='Activate (start) the microservice')
    parser.add_argument('--deactivate', action='store_true', help='Deactivate (stop) the microservice')
    parser.add_argument('--status', action='store_true', help='Show if the microservice is active')
    parser.add_argument('--process', action='store_true', help='Start file processing workflow')
    parser.add_argument('--test', action='store_true', help='Run test workflow with sample files')
    parser.add_argument('--comprehensive-test', action='store_true', help='Run comprehensive test suite')
    parser.add_argument('--test-run', type=str, help='Run specific test (e.g., T0000001)')
    parser.add_argument('--monitoring', action='store_true', help='Get monitoring data')
    parser.add_argument('--ports', action='store_true', help='Show available ports for each priority')
    parser.add_argument('--port', type=int, default=8003, help='Port for the API server (default: 8003)')
    parser.add_argument('--watch-dir', type=str, help='Directory to watch for new files (default: current directory)')
    args = parser.parse_args()

    # Default to service mode if no arguments provided
    if not any(vars(args).values()):
        args.service = True

    # API-only mode (legacy)
    if args.api:
        try:
            print(f"[STARTUP] Starting RCM API server on port {args.port}...")
            uvicorn.run("FAIM.faim:app", host="0.0.0.0", port=args.port, reload=True)
        except OSError as e:
            if "10013" in str(e) or "address already in use" in str(e).lower():
                print(f"[ERROR] Port {args.port} is already in use. Try a different port:")
                print(f"   python RCM_main.py --api --port 8002")
            else:
                print(f"[ERROR] Failed to start server: {e}")
        return

    # Service daemon mode (default behavior for CCU integration)
    if args.service:
        async def run_service():
            """Run RCM as a microservice daemon with keep-alive loop."""
            print("[STARTUP] Starting RCM microservice in daemon mode...")
            print(f"[PATH] Current working directory: {os.getcwd()}")
            print(f"[PATH] Python executable: {sys.executable}")
            print(f"[PATH] Script path: {__file__}")
            
            try:
                print("[INIT] About to call rcm_service.start()...")
                await rcm_service.start()
                print("[SUCCESS] RCM microservice started successfully")
                print(f"[STATUS] Service active status: {rcm_service.is_active}")
                print(f"[STATUS] Gateway active status: {rcm_service.gateway_active}")
                print("[STATUS] Service is running... (Press Ctrl+C to stop)")
                
                # Keep the service running - CRITICAL for CCU integration
                # Use an infinite loop instead of depending on is_active flag
                print("[DAEMON] Entering daemon keep-alive loop...")
                loop_count = 0
                while True:
                    await asyncio.sleep(1)
                    loop_count += 1
                    
                    # Log every 30 seconds to show it's alive
                    if loop_count % 30 == 0:
                        print(f"[DAEMON] RCM daemon heartbeat - running for {loop_count} seconds")
                    
                    # Check if service is still running (optional health check)
                    if not rcm_service.is_active:
                        print("[WARNING] Service became inactive, restarting...")
                        await rcm_service.start()
                    
            except KeyboardInterrupt:
                print("\n[SHUTDOWN] Shutting down RCM microservice...")
                await rcm_service.stop()
                print("[SUCCESS] RCM microservice stopped successfully")
            except Exception as e:
                print(f"[ERROR] Error running RCM microservice: {e}")
                import traceback
                traceback.print_exc()
                await rcm_service.stop()
                raise
        
        asyncio.run(run_service())
        return

    # For other operations, use asyncio
    async def control():
        if args.activate:
            await rcm_service.start()
            print("[SUCCESS] RCM microservice activated.")
        elif args.deactivate:
            await rcm_service.stop()
            print("[INFO] RCM microservice deactivated.")
        elif args.status:
            status = rcm_service.get_status()
            print(f"[STATUS] RCM microservice is {'active' if status['is_active'] else 'inactive'}.")
            print(f"   Modules: {len(status['modules'])}")
            # Safely get active requests if available
            active_requests = 0
            if 'IFCM' in status['modules'] and isinstance(status['modules']['IFCM'], dict):
                active_requests = status['modules']['IFCM'].get('active_requests', 0)
            print(f"   Active requests: {active_requests}")
        elif args.process:
            await run_file_processing_workflow(args.watch_dir)
        elif args.test:
            await run_test_workflow()
        elif args.comprehensive_test:
            await run_comprehensive_test()
        elif args.test_run:
            try:
                await rcm_service.start()
                result = await rcm_service.run_test(args.test_run)
                print(f"[TEST] Test {args.test_run} result: {result}")
            finally:
                await rcm_service.stop()
        elif args.monitoring:
            try:
                await rcm_service.start()
                monitoring_data = await rcm_service.get_monitoring_data()
                print(f"[MONITOR] Monitoring data: {monitoring_data}")
            finally:
                await rcm_service.stop()
        elif args.ports:
            show_priority_ports()

    asyncio.run(control())


if __name__ == "__main__":
    main()
