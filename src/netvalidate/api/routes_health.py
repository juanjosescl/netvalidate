"""Health and readiness endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from netvalidate import __version__
from netvalidate.models.db import get_session
from netvalidate.models.schemas import HealthResponse, ReadyResponse
from netvalidate.profiles.loader import list_profiles

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Liveness probe."""
    return HealthResponse(status="ok", version=__version__)


@router.get("/ready", response_model=ReadyResponse)
async def ready(session: AsyncSession = Depends(get_session)) -> ReadyResponse:
    """Readiness probe: checks DB and profiles."""
    db_ok = False
    try:
        await session.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False

    profiles_ok = len(list_profiles()) > 0
    overall = "ready" if (db_ok and profiles_ok) else "not_ready"
    return ReadyResponse(status=overall, database=db_ok, profiles_loaded=profiles_ok)
