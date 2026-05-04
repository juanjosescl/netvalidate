"""Job retrieval and listing endpoints."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from netvalidate.auth import require_api_key
from netvalidate.models.db import get_session
from netvalidate.models.schemas import (
    JobList,
    JobStatus,
    JobSummary,
    ValidationResult,
)
from netvalidate.storage.repository import JobRepository

router = APIRouter()


@router.get(
    "/jobs/{job_id}",
    response_model=JobStatus,
    dependencies=[Depends(require_api_key)],
)
async def get_job(job_id: UUID, session: AsyncSession = Depends(get_session)) -> JobStatus:
    repo = JobRepository(session)
    record = await repo.get(job_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Job not found")

    result = ValidationResult.model_validate(record.result) if record.result else None
    return JobStatus(
        job_id=record.job_id,
        status=record.status,  # type: ignore[arg-type]
        created_at=record.created_at,
        started_at=record.started_at,
        completed_at=record.completed_at,
        progress=record.progress,
        result=result,
        error=record.error,
    )


@router.get(
    "/jobs",
    response_model=JobList,
    dependencies=[Depends(require_api_key)],
)
async def list_jobs(
    limit: int = 50,
    offset: int = 0,
    session: AsyncSession = Depends(get_session),
) -> JobList:
    repo = JobRepository(session)
    records, total = await repo.list(limit=limit, offset=offset)
    items = [
        JobSummary(
            job_id=r.job_id,
            status=r.status,  # type: ignore[arg-type]
            vendor=r.vendor,  # type: ignore[arg-type]
            device_ip=r.device_ip,
            profile=r.profile,
            created_at=r.created_at,
        )
        for r in records
    ]
    return JobList(items=items, total=total)


@router.delete(
    "/jobs/{job_id}",
    status_code=204,
    dependencies=[Depends(require_api_key)],
)
async def delete_job(job_id: UUID, session: AsyncSession = Depends(get_session)) -> None:
    repo = JobRepository(session)
    deleted = await repo.delete(job_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Job not found")
