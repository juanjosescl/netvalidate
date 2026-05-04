"""Background job execution."""
import time
import traceback
from datetime import UTC, datetime
from uuid import UUID

from netvalidate.models.db import get_session_factory
from netvalidate.models.schemas import ValidationResult
from netvalidate.profiles.loader import load_profile
from netvalidate.storage.repository import JobRepository
from netvalidate.vendors.raisecom import get_validator


async def run_validation_job(
    job_id: UUID,
    device_ip: str,
    vendor: str,
    profile_name: str,
    pivot_host: str | None,
) -> None:
    """Execute a validation job and persist its result."""
    factory = get_session_factory()
    started = datetime.now(UTC)
    t0 = time.monotonic()

    try:
        async with factory() as session:
            repo = JobRepository(session)
            await repo.update_status(job_id, status="running", started_at=started, progress=10)

        profile = load_profile(profile_name)
        validator = get_validator(vendor)
        checks = await validator.run(device_ip, pivot_host, profile)

        passed = sum(1 for c in checks if c.passed)
        failed = len(checks) - passed
        duration = time.monotonic() - t0

        result = ValidationResult(
            device_ip=device_ip,
            vendor=vendor,  # type: ignore[arg-type]
            profile=profile_name,
            total_checks=len(checks),
            passed=passed,
            failed=failed,
            duration_seconds=round(duration, 3),
            checks=checks,
        )

        async with factory() as session:
            repo = JobRepository(session)
            await repo.update_status(
                job_id,
                status="completed",
                progress=100,
                completed_at=datetime.now(UTC),
                result=result.model_dump(mode="json"),
            )

    except Exception as exc:  # pragma: no cover
        err_msg = f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"
        async with factory() as session:
            repo = JobRepository(session)
            await repo.update_status(
                job_id,
                status="failed",
                progress=100,
                completed_at=datetime.now(UTC),
                error=err_msg[:1900],
            )
