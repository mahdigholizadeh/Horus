# Mock servers for local integration testing

| File | Role |
|------|------|
| `website_server.py` | Simulated client sending JSON requests to RLA |
| `openai_server.py` | Simulated OpenAI API for RCM |

```bash
python mocks/website_server.py
python mocks/openai_server.py
```

Configure hosts and ports via `.env` (see `.env.example`).
