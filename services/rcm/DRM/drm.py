"""
Disk Restoration Module (DRM)

Restores cached or queued data from disk back into memory when resources become available.
Works in tandem with the Memory Management Module (MMM).
"""

import os
import logging
from pathlib import Path
from typing import Callable, Optional, List, Dict, Any
import json
import asyncio
import threading
import time
from datetime import datetime
from EMM.emm import ErrorManagementModule
from EMM.api_error_handler import api_error_handler

class DiskRestorationModule:
    """
    Disk Restoration Module (DRM)
    - Scans for spill files on disk.
    - Restores data to memory when resources are available.
    - Notifies MMM or a callback when restoration is complete.
    - Logs all actions and errors via EMM.
    - Works with MMM to automatically restore when memory is available.
    """
    def __init__(self, cache_dir: Optional[str] = None):
        self.logger = logging.getLogger(__name__)
        self.error_manager = ErrorManagementModule()
        self.cache_dir = Path(cache_dir) if cache_dir else Path(__file__).parent / "cache"
        self.restored_files: List[str] = []
        self.last_error: Optional[str] = None
        self.stats: Dict[str, Any] = {
            "total_restored": 0,
            "last_restored": None,
            "last_error": None,
            "auto_restore_enabled": False,
            "restoration_attempts": 0,
            "successful_restorations": 0
        }
        self.notify_callback: Optional[Callable[[str, Any], None]] = None
        self.mmm_callback: Optional[Callable] = None
        
        # Auto-restoration settings
        self.auto_restore_enabled = False
        self.restore_check_interval = 30.0  # seconds
        self.is_monitoring = False
        self.monitoring_task = None
        
        # Ensure cache directory exists
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def set_notify_callback(self, callback: Callable[[str, Any], None]):
        """Set a callback to notify when restoration is complete."""
        self.notify_callback = callback

    def set_mmm_callback(self, callback: Callable):
        """Set callback to MMM for memory status checks."""
        self.mmm_callback = callback

    def enable_auto_restoration(self, enabled: bool = True):
        """Enable or disable automatic restoration."""
        self.auto_restore_enabled = enabled
        self.stats["auto_restore_enabled"] = enabled
        self.logger.info(f"Auto-restoration {'enabled' if enabled else 'disabled'}")

    async def start_monitoring(self):
        """Start monitoring for restoration opportunities."""
        if self.is_monitoring:
            return
        
        self.is_monitoring = True
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        self.logger.info("DRM monitoring started")

    async def stop_monitoring(self):
        """Stop monitoring for restoration opportunities."""
        self.is_monitoring = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        self.logger.info("DRM monitoring stopped")

    async def _monitoring_loop(self):
        """Monitor for restoration opportunities."""
        while self.is_monitoring:
            try:
                if self.auto_restore_enabled and self.mmm_callback:
                    # Check if memory is available for restoration
                    memory_status = await self.mmm_callback()
                    if memory_status and memory_status.get("system", {}).get("percent", 100) < 30:
                        # Memory is below 30%, safe to restore
                        await self._auto_restore_spilled_data()
                
                await asyncio.sleep(self.restore_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in DRM monitoring loop: {e}")
                await asyncio.sleep(10)

    async def _auto_restore_spilled_data(self):
        """Automatically restore spilled data when memory is available."""
        try:
            spill_files = self.scan_spill_files()
            if not spill_files:
                return
            
            self.stats["restoration_attempts"] += 1
            restored_count = 0
            
            # Sort by creation time (oldest first for FIFO)
            spill_files.sort(key=lambda x: x.stat().st_ctime)
            
            for spill_file in spill_files:
                try:
                    success = self.restore_file(spill_file)
                    if success:
                        restored_count += 1
                        self.stats["successful_restorations"] += 1
                    
                    # Limit restoration to avoid overwhelming memory
                    if restored_count >= 5:  # Restore max 5 at a time
                        break
                        
                except Exception as e:
                    self.logger.error(f"Failed to auto-restore {spill_file}: {e}")
            
            if restored_count > 0:
                self.logger.info(f"Auto-restored {restored_count} spilled files")
                
        except Exception as e:
            error_msg = f"Error in auto-restoration: {e}"
            self.error_manager.log_error_with_generation("DRM", "DiskRestorationModule", "_auto_restore_spilled_data", error_msg)

    def scan_spill_files(self) -> List[Path]:
        """Scan the cache directory for spill files."""
        try:
            return list(self.cache_dir.glob("*.spill"))
        except Exception as e:
            self.logger.error(f"Error scanning spill files: {e}")
            return []

    def restore_all(self) -> int:
        """Restore all spill files from disk to memory."""
        files = self.scan_spill_files()
        restored_count = 0
        
        for file_path in files:
            try:
                if self.restore_file(file_path):
                    restored_count += 1
            except Exception as e:
                self.logger.error(f"Failed to restore {file_path}: {e}")
        
        self.logger.info(f"Restored {restored_count} files out of {len(files)} found")
        return restored_count

    def restore_file(self, file_path: Path) -> bool:
        """Restore a single spill file from disk to memory."""
        try:
            if not file_path.exists():
                self.logger.warning(f"Spill file not found: {file_path}")
                return False
            
            # Read JSON data
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # Notify callback if set
            if self.notify_callback:
                try:
                    self.notify_callback(str(file_path), data)
                except Exception as e:
                    self.logger.error(f"Error in notify callback: {e}")
            
            # Update statistics
            self.restored_files.append(str(file_path))
            self.stats["total_restored"] += 1
            self.stats["last_restored"] = str(file_path)
            self.stats["last_error"] = None
            
            self.logger.info(f"Restored data from {file_path}")
            
            # Remove the file after successful restoration
            file_path.unlink()
            return True
            
        except Exception as e:
            error_msg = f"Failed to restore {file_path}: {e}"
            self.last_error = error_msg
            self.stats["last_error"] = error_msg
            self.logger.error(error_msg)
            self.error_manager.log_error_with_generation("DRM", "DiskRestorationModule", "restore_file", error_msg)
            return False

    def get_spill_file_info(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Get information about a spill file."""
        try:
            if not file_path.exists():
                return None
            
            stat = file_path.stat()
            return {
                "file_path": str(file_path),
                "size_bytes": stat.st_size,
                "created_time": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "modified_time": datetime.fromtimestamp(stat.st_mtime).isoformat()
            }
        except Exception as e:
            self.logger.error(f"Error getting file info for {file_path}: {e}")
            return None

    def get_status(self) -> Dict[str, Any]:
        """Get current status and statistics."""
        spill_files = self.scan_spill_files()
        spill_info = []
        
        for spill_file in spill_files:
            info = self.get_spill_file_info(spill_file)
            if info:
                spill_info.append(info)
        
        return {
            "cache_dir": str(self.cache_dir),
            "restored_files": self.restored_files.copy(),
            "last_error": self.last_error,
            "stats": self.stats.copy(),
            "auto_restore_enabled": self.auto_restore_enabled,
            "is_monitoring": self.is_monitoring,
            "spill_files_count": len(spill_files),
            "spill_files_info": spill_info
        }

    async def handle_api_error(self, error: Exception, context: str = "unknown") -> dict:
        return api_error_handler.handle_error(error, context, "DRM")

# Global instances
drm = DiskRestorationModule()
DRM = DiskRestorationModule()