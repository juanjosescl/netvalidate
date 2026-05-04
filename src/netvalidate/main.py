"""FastAPI application entrypoint."""
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from netvalidate.api import routes_health, routes_jobs, routes_profiles, routes_validate
from netvalidate.config import get_settings
from netvalidate.models.db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Initialize database on startup."""
    await init_db()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="netvalidate",
        description=(
            "Multi-vendor network configuration validator. "
            "Submit validation jobs against Cisco, Huawei, and Raisecom devices "
            "using declarative YAML profiles."
        ),
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(routes_health.router, tags=["health"])
    app.include_router(routes_validate.router, prefix="/api/v1", tags=["validation"])
    app.include_router(routes_jobs.router, prefix="/api/v1", tags=["jobs"])
    app.include_router(routes_profiles.router, prefix="/api/v1", tags=["profiles"])

    return app


app = create_app()
