# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common commands

```bash
# Local development (Python 3.11+)
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
uvicorn netvalidate.main:app --reload          # API at :8000, /docs for Swagger

# Service helpers (load .env, kill prior uvicorn, run in background, write /tmp/uvicorn.log)
./scripts/start.sh
./scripts/stop.sh
./scripts/smoke_test.sh [base_url]              # end-to-end: health → auth → create → poll

# Tests / lint
pytest -v
pytest tests/test_cisco_collect.py::test_name -v   # single test
ruff check src tests

# Docker (binds ./data and ./examples/profiles, loads .env)
docker compose up --build
```

CI (`.github/workflows/tests.yml`) runs `ruff check src tests` and `pytest -v --cov=netvalidate` on Python 3.12.

## Architecture

FastAPI service that accepts validation jobs, runs them as `BackgroundTasks`, and persists state in SQLite via async SQLAlchemy. Each vendor is a `BaseValidator` subclass (Strategy pattern) with two methods: `collect()` (device I/O) and `evaluate()` (apply YAML rules to collected data).

**Request lifecycle** (`api/routes_validate.py` → `core/runner.py`):
1. `POST /api/v1/validate` validates the profile exists, creates a job row (`status=queued`), and schedules `run_validation_job` as a BackgroundTask.
2. Runner flips status to `running`, calls `get_validator(vendor).run(...)`, persists `ValidationResult` (or error trace), and sets `status=completed|failed`.
3. Client polls `GET /api/v1/jobs/{job_id}`.

Because BackgroundTasks is in-process, jobs in `running` are orphaned on API restart. This is acknowledged in `docs/architecture.md` and is the reason the job model exists at all — to make the future swap to Arq/RQ a non-breaking change.

**Connectivity** (`connectivity/manager.py`): `open_session()` is a context manager that supports two modes — direct SSH via Netmiko, or SSH-into-pivot-then-telnet using `netmiko.redispatch`. Vendor → Netmiko `device_type` lookup tables (`VENDOR_DEVICE_TYPE_SSH`, `VENDOR_DEVICE_TYPE_TELNET`) and `VENDORS_NEED_ENABLE` live here; extending vendors means updating these dicts too.

**Mock-by-default for collect().** Cisco's `collect()` checks for `NETVALIDATE_CISCO_USERNAME` and falls back to `_mock_collect()` if absent. This is intentional so the full pipeline runs end-to-end without real devices (CI, demos, smoke tests). Don't remove this fallback when adding real-device features. Huawei and Raisecom currently return hardcoded mocks unconditionally.

**Parsing is split from collection.** `vendors/cisco.py` separates `_collect_sync()` (Netmiko I/O) from the pure `_shape_raw()` function and the parsers in `vendors/parsers/cisco_parsers.py`. Shape functions and parsers must stay pure — tests in `tests/test_parsers_cisco.py` and `tests/test_cisco_collect.py` feed canned strings/dicts. Don't add I/O to `_shape_raw` or `parse_*`.

**Profile/check coupling.** Profiles in `examples/profiles/*.yaml` declare `kind` strings (e.g. `ospf_neighbors_full`, `ntp_synced`). Each `kind` must have an `if kind == "..."` branch in the corresponding vendor's `evaluate()`; unknown kinds are silently skipped. When adding a check: add the YAML entry **and** the matching branch.

## Configuration

All settings come from env vars with the `NETVALIDATE_` prefix, parsed by `pydantic-settings` in `config.py`. `get_settings()` is `@lru_cache`d — restart the process to pick up `.env` changes. Key vars: `NETVALIDATE_API_KEY` (required for `X-API-Key` header auth on `/api/v1/*`), `NETVALIDATE_DB_URL`, `NETVALIDATE_PROFILES_DIR`, `NETVALIDATE_CISCO_{USERNAME,PASSWORD,ENABLE}`, `NETVALIDATE_PIVOT_{PORT,USERNAME,PASSWORD}`. See `.env.example` for the full list.

The API never accepts plaintext passwords in payloads — requests use `credentials_ref` (resolved out-of-band) and `pivot_host` only. Keep it that way.

## Test conventions

`pyproject.toml` sets `asyncio_mode = "auto"` and `pythonpath = ["src"]`, so `async def test_*` functions run without `@pytest.mark.asyncio` and imports use the package name directly. `tests/test_api.py` uses FastAPI's `TestClient`; `tests/test_cisco_collect.py` monkeypatches Netmiko via the `try/except ImportError` shim in `connectivity/manager.py`.
