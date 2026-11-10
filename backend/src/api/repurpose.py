import asyncio
import json
import logging
import re

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import AsyncSessionLocal, get_db
from src.main import limiter
from src.models.content import ContentAsset, ContentJob
from src.schemas.content import (
    AssetDetailResponse,
    HistoryResponse,
    JobStatusResponse,
    VideoRequest,
)
from src.services.youtube_service import ContentProcessor

logger = logging.getLogger("repurpose_api")
logger.setLevel(logging.INFO)

router = APIRouter()

JOB_TIMEOUT_SECONDS = 600
SESSION_COOKIE = "rsid"
HISTORY_MAX_LIMIT = 50


def get_session_id(request: Request) -> str:
    session_id = getattr(request.state, "session_id", None)
    if not session_id:
        raise HTTPException(
            status_code=500,
            detail="Session middleware not configured. Add SessionMiddleware to the app.",
        )
    return session_id


def clean_json_string(json_str: str) -> str:
    if not json_str:
        return "[]"
    cleaned = re.sub(r"```json\s*", "", json_str)
    cleaned = re.sub(r"```", "", cleaned)
    return cleaned.strip()


async def _mark_job_failed(job_id: int, reason: str) -> None:
    async with AsyncSessionLocal() as fail_db:
        try:
            result = await fail_db.execute(select(ContentJob).where(ContentJob.id == job_id))
            job = result.scalar_one_or_none()
            if job:
                job.status = "failed"
                job.error_message = reason[:1000]
                await fail_db.commit()
                logger.info(
                    "Job marked failed",
                    extra={"job_id": job_id, "reason": reason[:200]},
                )
        except Exception as e:
            logger.error(
                "Could not persist failure status",
                extra={"job_id": job_id, "error": str(e)},
            )


async def _run_job(job_id: int, url: str) -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(ContentJob).where(ContentJob.id == job_id))
        job = result.scalar_one_or_none()

        if not job:
            logger.error("Job not found in background task", extra={"job_id": job_id})
            return

        try:
            video_id = ContentProcessor.get_video_id(url)
            if not video_id:
                raise ValueError("Could not extract video ID from URL.")

            logger.info("Starting transcript fetch", extra={"job_id": job_id, "video_id": video_id})

            transcript = await ContentProcessor.get_transcript(video_id)
            if not transcript:
                raise ValueError(
                    "Transcript unavailable: captions missing and audio fallback failed."
                )

            logger.info("Transcript ready", extra={"job_id": job_id, "chars": len(transcript)})

            content = await ContentProcessor.generate_assets(transcript)

            try:
                raw_tweets = content.get("tweets") or "[]"
                tweets_json = json.loads(clean_json_string(raw_tweets))
                if not isinstance(tweets_json, list):
                    raise TypeError("Tweets response is not a JSON list")
            except (json.JSONDecodeError, TypeError, ValueError) as parse_err:
                logger.warning(
                    "Tweet JSON parse failed, saving raw",
                    extra={"job_id": job_id, "error": str(parse_err)},
                )
                tweets_json = {"parse_error": str(parse_err), "raw": content.get("tweets")}

            blog_val = content.get("blog")
            linkedin_val = content.get("linkedin")

            # Update legacy job columns for immediate backward compatibility
            job.blog_content = blog_val
            job.tweets = tweets_json
            job.linkedin_post = linkedin_val
            job.status = "completed"

            # Populate relational ContentAsset rows
            assets_to_add = [
                ContentAsset(
                    job_id=job.id,
                    asset_type="blog",
                    status="completed" if blog_val else "failed",
                    content={"markdown_body": blog_val} if blog_val else None,
                ),
                ContentAsset(
                    job_id=job.id,
                    asset_type="twitter_thread",
                    status="completed" if isinstance(tweets_json, list) else "failed",
                    content={"thread": tweets_json}
                    if isinstance(tweets_json, list)
                    else tweets_json,
                ),
                ContentAsset(
                    job_id=job.id,
                    asset_type="linkedin_post",
                    status="completed" if linkedin_val else "failed",
                    content={"body": linkedin_val} if linkedin_val else None,
                ),
            ]
            db.add_all(assets_to_add)

            await db.commit()
            logger.info("Job completed with relational assets", extra={"job_id": job_id})

        except Exception as e:
            await db.rollback()
            logger.error("Job failed", extra={"job_id": job_id, "error": str(e)})
            await _mark_job_failed(job_id, str(e))


async def process_video_task(job_id: int, url: str) -> None:
    logger.info("Background task started", extra={"job_id": job_id, "url": url})
    try:
        await asyncio.wait_for(_run_job(job_id, url), timeout=JOB_TIMEOUT_SECONDS)
    except TimeoutError:
        logger.error("Job timed out", extra={"job_id": job_id, "timeout": JOB_TIMEOUT_SECONDS})
        await _mark_job_failed(
            job_id,
            f"Job exceeded the {JOB_TIMEOUT_SECONDS}s timeout and was cancelled.",
        )


@router.post("/repurpose", status_code=202)
@limiter.limit("5/minute;20/hour")
async def repurpose_video(
    request: Request,
    payload: VideoRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    url_str = str(payload.url)

    video_id = ContentProcessor.get_video_id(url_str)
    if not video_id:
        raise HTTPException(
            status_code=422,
            detail="Invalid YouTube URL. Please provide a valid youtube.com or youtu.be link.",
        )

    session_id = get_session_id(request)

    existing = await db.execute(
        select(ContentJob).where(
            ContentJob.session_id == session_id,
            ContentJob.youtube_url == url_str,
            ContentJob.status.in_(["processing", "queued"]),
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail="A job for this URL is already processing.",
        )

    new_job = ContentJob(
        youtube_url=url_str,
        video_id=video_id,
        status="processing",
        session_id=session_id,
        brand_profile_id=payload.brand_profile_id,
    )
    db.add(new_job)
    await db.commit()
    await db.refresh(new_job)

    background_tasks.add_task(process_video_task, new_job.id, url_str)

    logger.info(
        "Job created",
        extra={"job_id": new_job.id, "video_id": video_id, "session_id": session_id},
    )

    return {
        "job_id": new_job.id,
        "status": "processing",
        "message": "Job accepted. Poll /status/{job_id} for results.",
    }


@router.get("/history", response_model=list[HistoryResponse])
async def get_history(
    request: Request,
    db: AsyncSession = Depends(get_db),
    limit: int = 20,
    offset: int = 0,
):
    limit = min(limit, HISTORY_MAX_LIMIT)
    session_id = get_session_id(request)

    result = await db.execute(
        select(ContentJob)
        .where(ContentJob.session_id == session_id)
        .order_by(desc(ContentJob.created_at))
        .limit(limit)
        .offset(offset)
    )
    return result.scalars().all()


@router.get("/status/{job_id}", response_model=JobStatusResponse)
async def check_status(
    job_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    session_id = get_session_id(request)

    result = await db.execute(
        select(ContentJob).where(
            ContentJob.id == job_id,
            ContentJob.session_id == session_id,
        )
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found.")

    return JobStatusResponse(
        id=job.id,
        status=job.status,
        error_message=job.error_message,
        blog_content=job.get_effective_blog(),
        tweets=job.get_effective_tweets(),
        linkedin_post=job.get_effective_linkedin(),
        assets=[AssetDetailResponse.model_validate(a) for a in job.assets] if job.assets else None,
    )


@router.get("/jobs/{job_id}/assets", response_model=list[AssetDetailResponse])
async def get_job_assets(
    job_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    session_id = get_session_id(request)

    result = await db.execute(
        select(ContentJob).where(
            ContentJob.id == job_id,
            ContentJob.session_id == session_id,
        )
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found.")

    return [AssetDetailResponse.model_validate(a) for a in job.assets]
