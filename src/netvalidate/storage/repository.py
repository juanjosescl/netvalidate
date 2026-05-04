"""Repository for job persistence."""
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from netvalidate.models.db import JobRecord


class JobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        job_id: UUID,
        vendor: str,
        device_ip: str,
        profile: str,
    ) -> JobRecord:
        record = JobRecord(
            job_id=job_id,
            status="queued",
            vendor=vendor,
            device_ip=device_ip,
            profile=profile,
            progress=0,
            created_at=datetime.now(UTC),
        )
        self.session.add(record)
        await self.session.commit()
        await self.session.refresh(record)
        return record

    async def get(self, job_id: UUID) -> JobRecord | None:
        return await self.session.get(JobRecord, job_id)

    async def list(self, *, limit: int = 50, offset: int = 0) -> tuple[list[JobRecord], int]:
        stmt = select(JobRecord).order_by(JobRecord.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        items = list(result.scalars().all())

        count_stmt = select(JobRecord)
        count_result = await self.session.execute(count_stmt)
        total = len(list(count_result.scalars().all()))
        return items, total

    async def update_status(
        self,
        job_id: UUID,
        *,
        status: str,
        progress: int | None = None,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
        result: dict | None = None,
        error: str | None = None,
    ) -> None:
        record = await self.get(job_id)
        if record is None:
            return
        record.status = status
        if progress is not None:
            record.progress = progress
        if started_at is not None:
            record.started_at = started_at
        if completed_at is not None:
            record.completed_at = completed_at
        if result is not None:
            record.result = result
        if error is not None:
            record.error = error
        await self.session.commit()

    async def delete(self, job_id: UUID) -> bool:
        record = await self.get(job_id)
        if record is None:
            return False
        await self.session.delete(record)
        await self.session.commit()
        return True
