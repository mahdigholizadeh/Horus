# TLS certificates

Private keys (`key.pem`, `*.key`) must never be committed. They are listed in `.gitignore`.

Place development certificates here:

- `dev/cert.pem` — public certificate
- `dev/key.pem` — private key (local only)

Generate a self-signed dev pair:

```bash
openssl req -x509 -newkey rsa:4096 -keyout dev/key.pem -out dev/cert.pem -days 365 -nodes
```
