# Horus — Public Release Roadmap

**Repository name:** `horus`  
**Current release:** `v0.1.0-alpha`

---

## Sprint 1 — Repository hygiene ✅

- [x] Rebrand to Horus, remove business/marketing docs
- [x] Delete generated runtime data and build artifacts
- [x] Expand `.gitignore`, remove TLS private keys
- [x] Portable `horus_startup.py`
- [x] Fix hardcoded Windows paths in TD geo modules

---

## Sprint 2 — Structure and portability ✅

- [x] Flatten `MicroServices/` → `services/{ccu,rla,rcm,tpp,td,jfa,ocm}`
- [x] Consolidate mocks → `mocks/`
- [x] Add `.env.example`, `Dockerfile`, `docker-compose.yml`
- [x] Replace `/opt/envoai` with `HORUS_ROOT`
- [x] Removed `simulator/` folder

---

## Sprint 3 — Code quality and CI ✅

- [x] RCM test suite discovery runner
- [x] Strict startup (no bypasses)
- [x] `pyproject.toml`, `conftest.py`, split requirements
- [x] GitHub Actions CI

---

## Sprint 4 — Documentation polish ✅

- [x] Consolidated docs in `docs/` (architecture, development, deployment, testing)
- [x] Mermaid architecture diagram in README
- [x] `CONTRIBUTING.md`, `CHANGELOG.md`, `SECURITY.md`
- [x] `v0.1.0-alpha` documented in CHANGELOG (tag after commit — see below)
- [x] Git history audit instructions in `SECURITY.md`

---

## Tag release (after commit)

Once changes are committed on `main`:

```bash
git tag -a v0.1.0-alpha -m "First public alpha"
git push origin v0.1.0-alpha
```

---

## Layout

```text
horus/
├── docs/
├── services/
├── mocks/
├── horus_startup.py
├── CONTRIBUTING.md
├── CHANGELOG.md
├── SECURITY.md
└── .github/workflows/ci.yml
```

---

## Sprint 5 — Pure proxy refactor ✅

- [x] Remove all domain calculation modules from TD
- [x] Delete `database/` geo fixtures and RCM domain templates
- [x] Refactor TD/JFA/CCU/OCM to routing proxy terminology
- [x] Add [design principles](./docs/design-principles.md)
- [x] Professional README and CHANGELOG update

---

## Post-release

- Expand CI test coverage (OCM, CCU CTMM)
- `pip-audit` in CI
- Optional: `git filter-repo` if history scan finds secrets
