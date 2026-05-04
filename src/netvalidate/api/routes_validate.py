"""Validation job creation endpoint."""
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from netvalidate.auth import require_api_key
from netvalidate.core.runner import run_validation_job
from netvalidate.models.db import get_session
from netvalidate.models.schemas import JobCreated, ValidateRequest
from netvalidate.profiles.loader import load_profile
from netvalidate.storage.repository import JobRepository

router = APIRouter()


@router.post(
    "/validate",
    response_model=JobCreated,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_api_key)],
    summary="Create a validation job",
)
async def create_validation(
    req: ValidateRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
) -> JobCreated:
    # Validate that the profile exists before queueing.
    try:
        load_profile(req.profile)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    job_id = uuid4()
    repo = JobRepository(session)
    await repo.create(
        job_id=job_id,
        vendor=req.vendor,
        device_ip=str(req.device_ip),
        profile=req.profile,
    )

    background_tasks.add_task(
        run_validation_job,
        job_id,
        str(req.device_ip),
        req.vendor,
        req.profile,
        str(req.pivot_host) if req.pivot_host else None,
    )

    return JobCreated(
        job_id=job_id,
        status="queued",
        created_at=datetime.now(UTC),
        poll_url=f"/api/v1/jobs/{job_id}",
    )
