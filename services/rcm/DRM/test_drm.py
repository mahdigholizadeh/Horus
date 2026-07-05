"""
Unit tests for Disk Restoration Module (DRM)
"""
import os
import json
import shutil
import pytest
from EMM.emm import ErrorManagementModule
from EMM.api_error_handler import api_error_handler
from pathlib import Path
from DRM.drm import DiskRestorationModule

@pytest.fixture
def drm_tmp(tmp_path):
    # Create a DRM instance with a temp cache dir
    drm = DiskRestorationModule(cache_dir=tmp_path)
    return drm, tmp_path

def test_restore_file_success(drm_tmp):
    drm, tmp_path = drm_tmp
    # Create a spill file
    data = {"foo": "bar"}
    file_path = tmp_path / "test1.spill"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f)
    restored = {}
    drm.set_notify_callback(lambda path, d: restored.update({"path": path, "data": d}))
    drm.restore_file(file_path)
    assert restored["path"].endswith("test1.spill")
    assert restored["data"] == data
    assert not file_path.exists()
    assert drm.stats["total_restored"] == 1

def test_restore_file_error(drm_tmp):
    drm, tmp_path = drm_tmp
    # Create a corrupted spill file
    file_path = tmp_path / "bad.spill"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("not json")
    drm.restore_file(file_path)
    assert "Failed to restore" in drm.last_error
    assert file_path.exists()  # Should not delete on error

def test_restore_all(drm_tmp):
    drm, tmp_path = drm_tmp
    # Create multiple spill files
    for i in range(3):
        with open(tmp_path / f"f{i}.spill", "w", encoding="utf-8") as f:
            json.dump({"i": i}, f)
    called = []
    drm.set_notify_callback(lambda path, d: called.append((path, d)))
    drm.restore_all()
    assert len(called) == 3
    assert drm.stats["total_restored"] == 3
    assert not any(f.exists() for f in tmp_path.glob("*.spill"))

def test_scan_spill_files(drm_tmp):
    drm, tmp_path = drm_tmp
    # No files
    assert drm.scan_spill_files() == []
    # Add a file
    file_path = tmp_path / "a.spill"
    file_path.write_text("{}")
    files = drm.scan_spill_files()
    assert len(files) == 1
    assert files[0].name == "a.spill"

def test_status(drm_tmp):
    drm, tmp_path = drm_tmp
    status = drm.get_status()
    assert status["cache_dir"] == str(tmp_path)
    assert status["restored_files"] == []
    assert status["last_error"] is None
    assert status["stats"]["total_restored"] == 0 