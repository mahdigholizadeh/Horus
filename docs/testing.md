# Testing

Horus uses per-service **TMM (Test Management Module)** directories with `test_t*.py` modules and pytest.

## Quick start

```bash
pip install -r requirements/dev.txt

# RLA gateway tests
pytest services/rla/TMM -q

# RCM module tests (discover only)
pytest services/rcm/TMM --collect-only

# CCU central tests
pytest services/ccu/CTMM -q --maxfail=3
```

Root [`conftest.py`](../conftest.py) adds each service directory to `sys.path`.

## Layout

| Service | Test directory | Notes |
|---------|----------------|-------|
| CCU | `services/ccu/CTMM/` | Central test management |
| RLA | `services/rla/TMM/` | 24 gateway/integration tests |
| RCM | `services/rcm/TMM/` | Module + workflow tests; `test_suite.py` discovers `test_t*.py` |
| TPP | `services/tpp/TMM/` | Input filtering tests |
| TD | `services/td/TMM/` | Task routing tests |
| JFA | `services/jfa/TMM/` | Analysis pipeline tests |
| OCM | `services/ocm/TMM/` | Output formatting tests |

## RCM test runner

```bash
cd services/rcm/TMM
python test_suite.py
```

Runs all `test_t*.py` modules sequentially and prints a pass/fail summary.

## CI

GitHub Actions (`.github/workflows/ci.yml`):

- **lint** — `ruff check` on `services`, `mocks`, `horus_startup.py`
- **test** — smoke tests on RLA TMM; RCM collect-only

Expand CI coverage incrementally as flaky or environment-specific tests are stabilized.

## Writing tests

- Prefer async test functions with `pytest-asyncio` (`asyncio_mode = auto` in `pyproject.toml`).
- Use temporary directories for file-based workflows (see RCM `test_t0000001.py`).
- Mock external APIs; use `mocks/openai_server.py` for integration runs.
- Mark slow or integration tests with `@pytest.mark.integration` when added.

## Coverage (optional)

```bash
pytest services/rla/TMM --cov=services/rla --cov-report=term-missing
```
