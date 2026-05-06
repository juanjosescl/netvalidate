# netvalidate

Multi-vendor network configuration validator exposed as a REST API.

Submit validation jobs against Cisco, Huawei, and Raisecom devices using
declarative YAML profiles. Results are persisted and queryable.

## Why

Network teams operate heterogeneous infrastructure across multiple vendors.
Validating that devices comply with operational policies — OSPF adjacencies,
NTP sync, link-aggregation health, etc. — is typically done with vendor-specific
scripts that drift out of sync. This project unifies that workflow behind a
single API with a plugin-based vendor architecture (Strategy pattern), so adding
a new vendor is a self-contained module.

## Architecture

```
                ┌────────────────────────────────┐
                │       FastAPI (REST API)       │
                │  /api/v1/validate, /jobs, ...  │
                └───────────────┬────────────────┘
                                │
                ┌───────────────▼────────────────┐
                │        Job Manager (async)     │
                │  - persists jobs in SQLite     │
                │  - dispatches to BackgroundTasks│
                └───────────────┬────────────────┘
                                │
                ┌───────────────▼────────────────┐
                │       Validator Strategy       │
                │  Cisco | Huawei | Raisecom     │
                │  collect() → evaluate()        │
                └───────────────┬────────────────┘
                                │
                ┌───────────────▼────────────────┐
                │     YAML Profile Engine        │
                │  declarative checks            │
                └────────────────────────────────┘
```

See [`docs/architecture.md`](docs/architecture.md) for details.

## Quick start

```bash
git clone https://github.com/your-user/netvalidate.git
cd netvalidate
cp .env.example .env
docker compose up --build
```

Open the interactive API docs: <http://localhost:8000/docs>

### Submit a validation job

```bash
curl -X POST http://localhost:8000/api/v1/validate \
  -H "X-API-Key: dev-key-change-me" \
  -H "Content-Type: application/json" \
  -d '{
    "device_ip": "192.0.2.10",
    "vendor": "cisco",
    "profile": "cisco_basic"
  }'
```

Response:

```json
{
  "job_id": "f3c9...e2",
  "status": "queued",
  "created_at": "2026-05-01T17:30:00",
  "poll_url": "/api/v1/jobs/f3c9...e2"
}
```

### Poll for results

```bash
curl http://localhost:8000/api/v1/jobs/<job_id> \
  -H "X-API-Key: dev-key-change-me"
```

## Local development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Run the server with hot reload
uvicorn netvalidate.main:app --reload

# Run tests
pytest -v

# Lint
ruff check src tests
```

## Profiles

Validation profiles are YAML files under `examples/profiles/`. Each profile
declares the vendor it targets and a list of checks. Adding a check is a
matter of:

1. Adding the YAML entry in the profile.
2. Implementing the corresponding `kind` in the vendor validator.

Example (`examples/profiles/cisco_basic.yaml`):

```yaml
vendor: cisco
description: Basic operational checks for Cisco IOS XE devices
checks:
  - name: ospf_full_adjacencies
    kind: ospf_neighbors_full
    expected_min: 2
    severity: critical
```

## Adding a new vendor

1. Create `src/netvalidate/vendors/<vendor>.py` extending `BaseValidator`.
2. Implement `collect()` (device interaction) and `evaluate()` (rule logic).
3. Register it in the `_VALIDATORS` mapping in `src/netvalidate/vendors/__init__.py`.
4. Add a profile under `examples/profiles/`.

## Status

This is an active personal project. The current `collect()` methods return
mock data so the full pipeline runs end-to-end without real devices —
intentional, so the repo is reproducible. Real connectivity uses
Paramiko + Netmiko via SSH-pivot-then-telnet.

## License

MIT

