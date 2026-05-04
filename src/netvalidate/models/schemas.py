"""Pydantic schemas for API requests and responses."""
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, IPvAnyAddress

Vendor = Literal["cisco", "huawei", "raisecom"]
JobState = Literal["queued", "running", "completed", "failed", "cancelled"]
Severity = Literal["info", "warning", "critical"]


class ValidateRequest(BaseModel):
    """Request body for creating a validation job."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "device_ip": "192.0.2.10",
                "vendor": "cisco",
                "profile": "cisco_basic",
                "pivot_host": "192.0.2.1",
                "credentials_ref": "default",
            }
        }
    )

    device_ip: IPvAnyAddress = Field(description="Target device IP address")
    vendor: Vendor = Field(description="Device vendor")
    profile: str = Field(description="Name of the validation profile (YAML file basename)")
    pivot_host: IPvAnyAddress | None = Field(
        default=None,
        description="Optional SSH pivot host for telnet-only devices",
    )
    credentials_ref: str = Field(
        default="default",
        description="Reference to a stored credential set, never the password itself",
    )


class JobCreated(BaseModel):
    """Response after creating a job."""

    job_id: UUID
    status: JobState
    created_at: datetime
    poll_url: str


class CheckResult(BaseModel):
    """Outcome of a single validation check."""

    check_name: str
    passed: bool
    expected: Any
    actual: Any
    severity: Severity
    message: str


class ValidationResult(BaseModel):
    """Aggregated result of a validation job."""

    device_ip: str
    vendor: Vendor
    profile: str
    total_checks: int
    passed: int
    failed: int
    duration_seconds: float
    checks: list[CheckResult]


class JobStatus(BaseModel):
    """Full status of a validation job."""

    job_id: UUID
    status: JobState
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    progress: int = Field(ge=0, le=100)
    result: ValidationResult | None = None
    error: str | None = None


class JobSummary(BaseModel):
    """Compact job representation for listings."""

    job_id: UUID
    status: JobState
    vendor: Vendor
    device_ip: str
    profile: str
    created_at: datetime


class JobList(BaseModel):
    items: list[JobSummary]
    total: int


class ProfileSummary(BaseModel):
    name: str
    vendor: Vendor
    description: str
    check_count: int


class ProfileDetail(ProfileSummary):
    checks: list[dict[str, Any]]


class HealthResponse(BaseModel):
    status: Literal["ok"]
    version: str


class ReadyResponse(BaseModel):
    status: Literal["ready", "not_ready"]
    database: bool
    profiles_loaded: bool
