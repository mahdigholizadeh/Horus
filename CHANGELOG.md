# Changelog

All notable changes to Horus are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- [Design principles](./docs/design-principles.md) documenting the pure-proxy scope model

### Changed
- TD refactored to routing proxy (`forward`, `parallel`, `sequential`) — all domain calculators removed
- JFA, CCU, OCM tests and configs updated to generic pipeline terminology
- README repositioned as portfolio-grade microservice platform

### Removed
- Electrical/solar calculation modules (OFGSSC, ONGSSC, HSSC, LSSPPC, etc.)
- `database/` geo fixtures and RCM domain JSON prompt templates
- 70+ TD domain-specific TMM tests replaced with proxy smoke tests

## [0.1.0-alpha] - 2026-07-05

First public alpha after repository cleanup and rebrand.

### Added
- Seven microservices under `services/` (CCU, RLA, TPP, RCM, TD, JFA, OCM)
- `horus_startup.py` orchestrator with three-phase WebSocket startup
- Mock servers in `mocks/` (website client, OpenAI API)
- `pyproject.toml`, `conftest.py`, split requirements (`base` / `dev`)
- GitHub Actions CI (ruff + pytest smoke)
- Documentation: `docs/`, `CONTRIBUTING.md`, `SECURITY.md`
- Docker Compose profiles for mocks and full stack

### Changed
- Rebranded from legacy EnvoAI naming to **Horus**
- Flattened nested `MicroServices/` paths to `services/{name}/`
- Portable paths via `HORUS_ROOT` and project-relative resolution
- Strict startup: no partial-system bypass on failed services or WebSocket connections
- RCM `test_suite.py` rewritten to discover `test_t*.py` modules

### Removed
- Generated fixture data, build artifacts, and marketing/session documentation
- Simulator, legacy deployment scripts, and duplicate mock server files
- Empty root folders (`input/`, `error/`, `default/`, `test/`, `tests/`)

[Unreleased]: https://github.com/mahdigholizadeh/horus/compare/v0.1.0-alpha...HEAD
[0.1.0-alpha]: https://github.com/mahdigholizadeh/horus/releases/tag/v0.1.0-alpha
