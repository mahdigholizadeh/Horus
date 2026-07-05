# Deployment

Horus is designed for local development and single-host deployment. Production hardening is ongoing (`v0.1.0-alpha`).

## Environment variables

Copy [`.env.example`](../.env.example) to `.env`:

| Variable | Description |
|----------|-------------|
| `HORUS_ROOT` | Absolute path to the repository |
| `HORUS_ENV` | `development`, `staging`, or `production` |
| `OPENAI_API_KEY` | API key for RCM (omit when using mocks) |
| `RLA_HOST` / `RLA_PORT` | Gateway address for mock clients |
| `OCM_HOST` / `OCM_PORT` | Output delivery address for mocks |

Service port defaults are listed in `.env.example`.

## Docker

Build and run mock servers:

```bash
cp .env.example .env
docker compose --profile mocks up mock-openai mock-website
```

Full stack (experimental):

```bash
docker compose --profile full up horus
```

The Dockerfile installs `requirements/base.txt` and starts `horus_startup.py --start`.

## systemd (Linux)

CCU includes a systemd integrator (`services/ccu/SEM/systemd_integration.py`) that generates a unit file for service name `horusd`:

- `WorkingDirectory` and `HORUS_ROOT` resolve from the environment or CCU file location.
- `ExecStart` / `ExecStop` invoke `horus_startup.py`.

Generate certificates locally before enabling TLS; see [`services/ccu/certificates/README.md`](../services/ccu/certificates/README.md). Private keys must never be committed.

## TLS certificates

- Development: self-signed certs under `services/ccu/certificates/dev/`
- Production: place certs on the host and configure CERTM paths in CCU settings
- `key.pem` files are gitignored

## Path and config files

- Global paths: `config/paths/global_paths.json`
- CCU settings: `services/ccu/ccu_setting/`
- Per-service settings: each service's `config/` directory

After moving the repository, update `HORUS_ROOT` or rely on PMM auto-detection (looks for `services/` and `README.md` at the root).
