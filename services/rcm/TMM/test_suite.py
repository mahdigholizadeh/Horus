"""
RCM modular architecture test runner.

Individual tests live in ``test_t*.py`` modules in this directory.
Use pytest to execute them:

    pytest services/rcm/TMM -q
"""

from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path
from typing import Any, Dict, List


TMM_DIR = Path(__file__).resolve().parent


def _discover_test_modules() -> List[Path]:
    return sorted(TMM_DIR.glob("test_t*.py"))


def _load_async_test(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for name in dir(module):
        if name.startswith("test_") and asyncio.iscoroutinefunction(getattr(module, name)):
            return getattr(module, name)
    raise RuntimeError(f"No async test function found in {path.name}")


class RCMTestSuite:
    """Runs RCM TMM modules discovered on disk."""

    async def run_all_tests(self) -> Dict[str, Any]:
        modules = _discover_test_modules()
        results: Dict[str, Any] = {}

        for path in modules:
            test_id = path.stem.replace("test_", "").upper()
            try:
                test_fn = _load_async_test(path)
                await test_fn()
                results[test_id] = {"status": "PASS", "module": path.name, "error": None}
            except Exception as exc:
                results[test_id] = {"status": "FAIL", "module": path.name, "error": str(exc)}

        passed = sum(1 for r in results.values() if r["status"] == "PASS")
        total = len(results)
        return {
            "total_tests": total,
            "passed_tests": passed,
            "failed_tests": total - passed,
            "success_rate": (passed / total * 100) if total else 0.0,
            "results": results,
        }


async def main() -> Dict[str, Any]:
    suite = RCMTestSuite()
    return await suite.run_all_tests()


if __name__ == "__main__":
    summary = asyncio.run(main())
    print(summary)
