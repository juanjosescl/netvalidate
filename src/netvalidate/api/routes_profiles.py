"""Profile listing endpoints."""
from fastapi import APIRouter, Depends, HTTPException

from netvalidate.auth import require_api_key
from netvalidate.models.schemas import ProfileDetail, ProfileSummary
from netvalidate.profiles.loader import list_profiles, load_profile

router = APIRouter()


@router.get(
    "/profiles",
    response_model=list[ProfileSummary],
    dependencies=[Depends(require_api_key)],
)
async def get_profiles() -> list[ProfileSummary]:
    return [ProfileSummary(**p) for p in list_profiles()]


@router.get(
    "/profiles/{name}",
    response_model=ProfileDetail,
    dependencies=[Depends(require_api_key)],
)
async def get_profile(name: str) -> ProfileDetail:
    try:
        data = load_profile(name)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ProfileDetail(
        name=name,
        vendor=data.get("vendor", "unknown"),
        description=data.get("description", ""),
        check_count=len(data.get("checks", [])),
        checks=data.get("checks", []),
    )
