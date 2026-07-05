"""
Configuration file for RCM ( Requests Cache Manager) system.
Contains all constants, directory paths, and API settings.
Updated to support PMM (Path Management Module) integration.
"""

import os
import socket
import json
from EMM.emm import ErrorManagementModule
from EMM.api_error_handler import api_error_handler
from pathlib import Path

# PMM-aware base directory resolution
def _get_base_directory():
    """Get base directory using PMM-aware detection."""
    # Method 1: Try PMM environment variable
    if "PMM_PATHS" in os.environ:
        try:
            pmm_paths = json.loads(os.environ["PMM_PATHS"])
            installation_root = Path(pmm_paths.get("installation_root", Path.cwd()))
            service_root = pmm_paths.get("service_root")
            if service_root:
                return Path(service_root)
            # Fallback to installation root + service path
            return installation_root / "MicroServices" / "RCM" / "RCM_main" / "RCM_main" / "RCM_main"
        except (json.JSONDecodeError, KeyError):
            pass
    
    # Method 2: Look for installation markers (PMM detection method)
    current_path = Path(__file__).resolve()
    markers = ["JFA_CONFIGURATION_PLAN.md", "LICENSE.txt", "MicroServices", ".git"]
    
    for parent in current_path.parents:
        if any((parent / marker).exists() for marker in markers):
            # Found installation root, construct service path
            return parent / "MicroServices" / "RCM" / "RCM_main" / "RCM_main" / "RCM_main"
    
    # Method 3: Fallback to original method
    return Path(__file__).parent

# Base directory for the RCM system (PMM-aware)
BASE_DIR = _get_base_directory()

# Input and Output directory paths
RCM_TEMP_INPUT = BASE_DIR / "RCM_TEMP_INPUT"
RCM_TEMP_OUTPUT = BASE_DIR / "RCM_TEMP_OUTPUT"

# Response storage directories (OIAPO integration)
RCM_RESPONSE_INPUT = BASE_DIR / "RCM_RESPONSE_INPUT"
RCM_RESPONSE_OUTPUT = BASE_DIR / "RCM_RESPONSE_OUTPUT"

# Priority-based subdirectories
PRIORITY_DIRS = {
    "A": "A",
    "B": "B", 
    "C": "C",
    "D": "D"
}

# Create full paths for each priority level
INPUT_PATHS = {
    priority: RCM_TEMP_INPUT / subdir
    for priority, subdir in PRIORITY_DIRS.items()
}

OUTPUT_PATHS = {
    priority: RCM_TEMP_OUTPUT / subdir
    for priority, subdir in PRIORITY_DIRS.items()
}

# Response storage paths for each priority
RESPONSE_INPUT_PATHS = {
    priority: RCM_RESPONSE_INPUT / subdir
    for priority, subdir in PRIORITY_DIRS.items()
}

RESPONSE_OUTPUT_PATHS = {
    priority: RCM_RESPONSE_OUTPUT / subdir
    for priority, subdir in PRIORITY_DIRS.items()
}

# Priority-based port allocation (for future use if needed)
DEFAULT_PORTS = {
    "A": 50132,
    "B": 51717,
    "C": 52981,
    "D": 53617
}

# OpenAI API Configuration - API key should be distributed by CCU for security
OPENAI_API_KEY = None  # Will be set by individual modules via CCU→ECM
OPENAI_API_BASE_URL = "https://api.openai.com/v1/chat/completions"
OPENAI_API_TIMEOUT = 30  # seconds
OPENAI_API_MAX_RETRIES = 3

# Request Processing Configuration
MAX_CONCURRENT_REQUESTS = 50
REQUEST_BATCH_SIZE = 10
FILE_WATCH_INTERVAL = 1.0  # seconds

# Keys to remove from JSON for OpenAI API compliance
KEYS_TO_REMOVE = [
    "validation_flag",
    "TPP_flag", 
    "attempts_number",
    "priority_flag",
    "request_ID"
]

# Allowed keys in cleaned JSON (only these will be kept)
ALLOWED_KEYS = ["model", "messages"]

# Logging Configuration
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_FILE = BASE_DIR / "rcm.log"

# File extensions
INPUT_EXTENSIONS = [".json"]
OUTPUT_SUFFIX = "_edit"

# Request tracking configuration
REQUEST_MAP_CLEANUP_INTERVAL = 300  # seconds (5 minutes)
MAX_REQUEST_AGE = 600  # seconds (10 minutes)

# OIAPO Configuration (for future socket implementation if needed)
OIAPO_HOST = "127.0.0.1"
OIAPO_REQUEST_MESSAGE = "GET /json\n"
OIAPO_BUFFER_SIZE = 4096
OIAPO_TIMEOUT = 30  # seconds

# CCU WebSocket Configuration for ECM handoff (NEW ARCHITECTURE)
# RCM ECM connects to CCU RCMIM WebSocket server
CCU_WS_URI = os.environ.get("CCU_WS_URI", None)
if CCU_WS_URI is None:
    CCU_WS_HOST = os.environ.get("CCU_WS_HOST", "localhost")
    # Updated default port to match CCU RCMIM server port from websocket_ports.json
    CCU_WS_PORT = int(os.environ.get("CCU_WS_PORT", 4443))  # CCU RCMIM WebSocket server port
    CCU_WS_URI = f"ws://{CCU_WS_HOST}:{CCU_WS_PORT}/ws"  # Standard WebSocket path
CCU_SERVICE_ID = os.environ.get("CCU_SERVICE_ID", "RCM_PRIMARY")
CCU_HEARTBEAT_INTERVAL = int(os.environ.get("CCU_HEARTBEAT_INTERVAL", 30))


def is_port_available(port):
    """Check if a port is available."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            result = sock.connect_ex(('127.0.0.1', port))
            return result != 0  # Port is available if connection fails
    except Exception:
        return False


def find_available_port(base_port):
    """Find an available port starting from base_port."""
    port = base_port
    while not is_port_available(port):
        port += 1
        if port > base_port + 100:  # Prevent infinite loop
            raise RuntimeError(f"Could not find available port starting from {base_port}")
    return port


def get_priority_ports():
    """Get available ports for each priority level."""
    ports = {}
    for priority, base_port in DEFAULT_PORTS.items():
        try:
            ports[priority] = find_available_port(base_port)
            print(f"Priority {priority}: Using port {ports[priority]}")
        except RuntimeError as e:
            print(f"Warning: {e}")
            ports[priority] = None
    return ports


def ensure_directories():
    """Create all necessary directories if they don't exist."""
    # Create input/output directories
    for path in INPUT_PATHS.values():
        path.mkdir(parents=True, exist_ok=True)
    
    for path in OUTPUT_PATHS.values():
        path.mkdir(parents=True, exist_ok=True)
    
    # Create response directories
    for path in RESPONSE_INPUT_PATHS.values():
        path.mkdir(parents=True, exist_ok=True)
    
    for path in RESPONSE_OUTPUT_PATHS.values():
        path.mkdir(parents=True, exist_ok=True)
    
    print(f"✅ Created/verified directories:")
    print(f"   Input: {RCM_TEMP_INPUT}")
    print(f"   Output: {RCM_TEMP_OUTPUT}")
    print(f"   Response Input: {RCM_RESPONSE_INPUT}")
    print(f"   Response Output: {RCM_RESPONSE_OUTPUT}")


if __name__ == "__main__":
    ensure_directories()
    print("\n🔍 Checking port availability:")
    get_priority_ports()