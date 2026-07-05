# TD (Task Divider) Microservice

## Overview

TD is a **routing and orchestration proxy** in the Horus pipeline. It receives structured requests from upstream services (typically RCM via CCU), applies routing rules, and forwards payloads toward JFA and OCM. TD does **not** run domain-specific computations (no electrical, solar, or geo calculations).

## Role in the pipeline

```text
RCM → TD → JFA → OCM
         ↑
        CCU (control via TDIM/ECM)
```

## Module architecture

```text
services/td/
├── TD_main.py       # Service entry point
├── BFPM/            # Binary/JSON passthrough parsing
├── AFM/             # Routing flag analysis
├── ROM/             # Orchestration scheduling
├── CAM/             # Result aggregation (passthrough metadata)
├── CIM/             # Task routing interface (proxy — no local compute)
├── ARM/             # CCU/API communication
├── ECM/             # External control (CCU lifecycle)
├── EMM/             # Error management
├── RMM/, FIM/, MSM/, BTM/, OCMIM/, TMM/
```

## Supported routes

| Route | Purpose |
|-------|---------|
| `forward` | Single-hop passthrough to the next pipeline stage |
| `parallel` | Fan-out to multiple downstream handlers |
| `sequential` | Ordered multi-step routing |

## Quick start

```bash
cd services/td
pip install -r requirements.txt
python TD_main.py
```

Health: `http://localhost:8003/health`

## Configuration

CCU settings: `services/ccu/ccu_setting/td_setting.json`

## License

MIT — part of the Horus project.
