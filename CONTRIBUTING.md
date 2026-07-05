# Contributing to Horus

Thank you for your interest in this project. Horus is a personal portfolio codebase; contributions are welcome via issues and pull requests.

## Getting started

1. Read [docs/development.md](docs/development.md) for setup.
2. Fork the repository and create a feature branch from `main`.
3. Install dev dependencies: `pip install -r requirements/dev.txt`.

## Pull request guidelines

- Keep changes focused; one logical change per PR.
- Follow existing patterns in the service you modify.
- Run lint and relevant tests before opening a PR:

  ```bash
  ruff check services mocks horus_startup.py
  pytest services/<service>/TMM -q --maxfail=5
  ```

- Update [CHANGELOG.md](CHANGELOG.md) under **Unreleased** for user-visible changes.
- Do not commit secrets, `.env`, databases, logs, or TLS private keys.

## Code style

- Python 3.13+
- Line length: 100 (see `pyproject.toml`)
- Format with `black` and sort imports with `isort` when touching a file
- Ruff error rules: syntax and undefined-name checks in CI

## Reporting issues

Include:

- Python version and OS
- Steps to reproduce
- Expected vs actual behavior
- Relevant logs (redact API keys and paths with personal data)

## Security

Report vulnerabilities privately — see [SECURITY.md](SECURITY.md). Do not open public issues for undisclosed security problems.

## License

By contributing, you agree that your contributions are licensed under the MIT License.
