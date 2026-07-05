"""Discover and run TD TMM smoke tests."""

import asyncio
import importlib.util
from pathlib import Path
from typing import Any, Dict, List


def _load_async_test(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for name in dir(module):
        if name.startswith("test_") and asyncio.iscoroutinefunction(getattr(module, name)):
            return getattr(module, name)
    return None


class TDTestSuite:
    def __init__(self):
        self.tmm_dir = Path(__file__).parent
        self.results: List[Dict[str, Any]] = []

    async def run_all(self) -> Dict[str, Any]:
        for test_file in sorted(self.tmm_dir.glob("test_t*.py")):
            test_fn = _load_async_test(test_file)
            if test_fn is None:
                continue
            try:
                await test_fn()
                self.results.append({"test": test_file.name, "status": "passed"})
            except Exception as exc:
                self.results.append({"test": test_file.name, "status": "failed", "error": str(exc)})
        passed = sum(1 for r in self.results if r["status"] == "passed")
        return {
            "total": len(self.results),
            "passed": passed,
            "failed": len(self.results) - passed,
            "results": self.results,
        }


async def main() -> Dict[str, Any]:
    return await TDTestSuite().run_all()


if __name__ == "__main__":
    print(asyncio.run(main()))
