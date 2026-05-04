"""End-to-end smoke tests against the FastAPI app."""
import asyncio
import os

import pytest
from httpx import ASGITransport, AsyncClient

os.environ["NETVALIDATE_DB_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["NETVALIDATE_API_KEY"] = "test-key"

from netvalidate.main import app
from netvalidate.models.db import init_db


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True, scope="session")
async def _setup_db():
    await init_db()


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def test_health(client):
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


async def test_validate_requires_auth(client):
    r = await client.post(
        "/api/v1/validate",
        json={
            "device_ip": "192.0.2.10",
            "vendor": "cisco",
            "profile": "cisco_basic",
        },
    )
    assert r.status_code == 401


async def test_validate_creates_job(client):
    r = await client.post(
        "/api/v1/validate",
        headers={"X-API-Key": "test-key"},
        json={
            "device_ip": "192.0.2.10",
            "vendor": "cisco",
            "profile": "cisco_basic",
        },
    )
    assert r.status_code == 202, r.text
    body = r.json()
    assert body["status"] == "queued"
    assert "job_id" in body
    assert body["poll_url"].startswith("/api/v1/jobs/")


async def test_unknown_profile_returns_404(client):
    r = await client.post(
        "/api/v1/validate",
        headers={"X-API-Key": "test-key"},
        json={
            "device_ip": "192.0.2.10",
            "vendor": "cisco",
            "profile": "does_not_exist",
        },
    )
    assert r.status_code == 404


async def test_list_profiles(client):
    r = await client.get("/api/v1/profiles", headers={"X-API-Key": "test-key"})
    assert r.status_code == 200
    names = [p["name"] for p in r.json()]
    assert "cisco_basic" in names
