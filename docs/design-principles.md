# Design principles

Horus is intentionally scoped as a **pure proxy and orchestration platform**. These principles guide architecture decisions and what belongs in the repository.

## 1. Proxy, not domain engine

Horus routes, validates, and forwards AI API requests. It does **not** embed business-domain computation (electrical sizing, geo analytics, industry-specific solvers, etc.).

| In scope | Out of scope |
|----------|--------------|
| HTTP ingress, sanitization, rate limits | Domain calculators and solvers |
| Priority queues and async AI I/O | Geo databases and location engines |
| Task routing (`forward`, `parallel`, `sequential`) | Industry-specific report templates |
| Control-plane lifecycle (CCU WebSocket) | Legacy binary template ecosystems |

## 2. Separation of control and data planes

- **Control plane** — CCU supervises workers over WebSocket (start/stop, health, activation).
- **Data plane** — Request payloads move over HTTP between services and external APIs.

This keeps operational concerns separate from request throughput.

## 3. Fail closed on startup

`horus_startup.py` uses three strict phases. If any service or ECM connection is missing, startup fails rather than running a partially connected system.

## 4. Configuration over hardcoded paths

Runtime paths resolve from `HORUS_ROOT`, project markers (`services/`, `README.md`), and `config/paths/global_paths.json`. No machine-specific absolute paths in source.

## 5. Secrets stay out of the tree

API keys and TLS private keys belong in environment variables or a secrets manager. Tests use obvious mock values (e.g. `sk-proj-mock-test-key-replace-in-env`).

## 6. Modular services, thin boundaries

Each microservice is a package of focused modules (ECM, EMM, TMM, …). Cross-service coupling happens through documented HTTP/WebSocket contracts, not shared domain libraries.

## Related docs

- [Architecture](./architecture.md)
- [Security policy](../SECURITY.md)
- [TD proxy role](../services/td/README.md)
