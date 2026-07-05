# Security policy

## Supported versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | Best effort (alpha) |

## Reporting a vulnerability

Do **not** open a public GitHub issue for security vulnerabilities.

Contact the maintainer privately with:

- Description of the issue
- Steps to reproduce
- Impact assessment
- Suggested fix (if any)

Allow reasonable time for a fix before public disclosure.

## Secrets and credentials

Never commit:

- `.env` files with real API keys
- TLS private keys (`key.pem`, `*.key`)
- Database files with production data
- Personal machine paths tied to identity

Use `.env.example` as a template. Production keys belong in environment variables or a secrets manager.

## Repository history audit

This repository was cleaned before its first public release. If you forked or cloned an older copy, audit history for leaked secrets:

```bash
# Search current tree
git grep -i "sk-" 
git grep -i "api_key"
git grep "BEGIN.*PRIVATE KEY"

# Search full history (requires git-filter-repo or trufflehog)
pip install trufflehog
trufflehog git file://. --only-verified
```

To remove secrets from history before publishing:

```bash
pip install git-filter-repo
# Example: remove a leaked file from all commits
git filter-repo --path path/to/leaked/file --invert-paths
```

Rotate any credential that was ever committed, even after history rewrite.

## TLS

- Generate dev certificates locally; see `services/ccu/certificates/README.md`
- Private keys are listed in `.gitignore`
- Rotate certificates on a defined schedule in production

## Dependency updates

- Review `requirements/base.txt` periodically
- CI does not yet run automated dependency scanning; consider `pip-audit` locally:

  ```bash
  pip install pip-audit
  pip-audit -r requirements/base.txt
  ```

## Secure defaults

- `ENABLE_API_KEY_VALIDATION=true` in `.env.example`
- Mock servers are for local testing only; do not expose them to the public internet without authentication
