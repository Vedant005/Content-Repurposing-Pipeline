import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_db
from src.models.content import BrandProfile
from src.schemas.brand import (
    BrandProfileCreate,
    BrandProfileResponse,
    BrandProfileUpdate,
)

logger = logging.getLogger("repurpose_api.brand")
router = APIRouter()


def get_session_id(request: Request) -> str:
    session_id = getattr(request.state, "session_id", None)
    if not session_id:
        raise HTTPException(
            status_code=500,
            detail="Session middleware not configured. Add SessionMiddleware to the app.",
        )
    return session_id


@router.post("/brand-profiles", response_model=BrandProfileResponse, status_code=201)
async def create_brand_profile(
    request: Request,
    payload: BrandProfileCreate,
    db: AsyncSession = Depends(get_db),
):
    session_id = get_session_id(request)

    profile = BrandProfile(
        session_id=session_id,
        brand_name=payload.brand_name,
        tone_guidelines=payload.tone_guidelines,
        target_audience=payload.target_audience,
        few_shot_examples=payload.few_shot_examples or {},
    )
    db.add(profile)
    await db.commit()
    await db.refresh(profile)

    logger.info("Created brand profile %d for session %s", profile.id, session_id)
    return profile


@router.get("/brand-profiles", response_model=list[BrandProfileResponse])
async def list_brand_profiles(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    session_id = get_session_id(request)
    result = await db.execute(
        select(BrandProfile)
        .where(BrandProfile.session_id == session_id)
        .order_by(desc(BrandProfile.created_at))
    )
    return result.scalars().all()


@router.get("/brand-profiles/{profile_id}", response_model=BrandProfileResponse)
async def get_brand_profile(
    profile_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    session_id = get_session_id(request)
    result = await db.execute(
        select(BrandProfile).where(
            BrandProfile.id == profile_id,
            BrandProfile.session_id == session_id,
        )
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail=f"Brand profile {profile_id} not found.")
    return profile


@router.put("/brand-profiles/{profile_id}", response_model=BrandProfileResponse)
async def update_brand_profile(
    profile_id: int,
    payload: BrandProfileUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    session_id = get_session_id(request)
    result = await db.execute(
        select(BrandProfile).where(
            BrandProfile.id == profile_id,
            BrandProfile.session_id == session_id,
        )
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail=f"Brand profile {profile_id} not found.")

    if payload.brand_name is not None:
        profile.brand_name = payload.brand_name
    if payload.tone_guidelines is not None:
        profile.tone_guidelines = payload.tone_guidelines
    if payload.target_audience is not None:
        profile.target_audience = payload.target_audience
    if payload.few_shot_examples is not None:
        profile.few_shot_examples = payload.few_shot_examples

    await db.commit()
    await db.refresh(profile)
    logger.info("Updated brand profile %d", profile.id)
    return profile


@router.delete("/brand-profiles/{profile_id}", status_code=204)
async def delete_brand_profile(
    profile_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    session_id = get_session_id(request)
    result = await db.execute(
        select(BrandProfile).where(
            BrandProfile.id == profile_id,
            BrandProfile.session_id == session_id,
        )
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail=f"Brand profile {profile_id} not found.")

    await db.delete(profile)
    await db.commit()
    logger.info("Deleted brand profile %d", profile_id)
    return None
