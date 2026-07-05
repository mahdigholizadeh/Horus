# Development guide

## Prerequisites

- Python 3.13+
- Git
- Optional: Docker for containerized mocks

## Setup

```bash
git clone <repo-url> horus
cd horus

python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
# source .venv/bin/activate

pip install -r requirements/dev.txt
cp .env.example .env
```

Set `HORUS_ROOT` in `.env` to the absolute path of the repository if auto-detection fails.

## Project layout

```text
services/          # Microservices (ccu, rla, rcm, tpp, td, jfa, ocm)
mocks/             # Local mock client and OpenAI server
config/            # Global path and service configuration
horus_startup.py   # Orchestrator CLI
pyproject.toml     # pytest, ruff, mypy
conftest.py        # pytest path setup
requirements/
  base.txt         # Runtime dependencies
  dev.txt          # base + test/lint tools
```

## Running services

Full stack (orchestrated):

```bash
python horus_startup.py --start
```

Individual service (from its directory):

```bash
cd services/rla
python RLA_main.py --service
```

Mock integration servers:

```bash
python mocks/website_server.py
python mocks/openai_server.py
```

## Lint and format

```bash
ruff check services mocks horus_startup.py conftest.py
black services mocks horus_startup.py conftest.py
isort services mocks horus_startup.py conftest.py
mypy services --ignore-missing-imports
```

CI runs `ruff check` on core paths; see [`.github/workflows/ci.yml`](../.github/workflows/ci.yml).

## Code conventions

- Match existing module naming (acronym folders: `ECM/`, `EMM/`, `TMM/`).
- Use `Path(__file__)` for file paths; avoid hardcoded machine-specific paths.
- Keep service boundaries: CCU controls via WebSocket; workers handle payloads over HTTP.
- Do not commit `.env`, `*.db`, logs, or TLS private keys.

## Adding a change

1. Create a branch from `main`.
2. Make focused changes with tests where applicable.
3. Run `ruff check` and relevant `pytest` targets.
4. Open a pull request using the template in [CONTRIBUTING.md](../CONTRIBUTING.md).

See [testing.md](./testing.md) for the test layout.
