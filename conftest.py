"""Shared pytest configuration for Horus service modules."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SERVICE_DIRS = [
    ROOT / "services" / "ccu",
    ROOT / "services" / "rla",
    ROOT / "services" / "rcm",
    ROOT / "services" / "tpp",
    ROOT / "services" / "td",
    ROOT / "services" / "jfa",
    ROOT / "services" / "ocm",
]

for path in [ROOT, *SERVICE_DIRS]:
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)
