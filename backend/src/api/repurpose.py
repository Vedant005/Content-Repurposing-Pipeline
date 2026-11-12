import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_db
from src.main import limiter
from src.models.content import ContentJob
from src.queue.redis import get_redis_pool
from src.schemas.content import (
    AssetDetailResponse,
    HistoryResponse,
    JobStatusResponse,
    VideoRequest,
)
from src.services.event_service import event_service
from src.services.youtube_service import ContentProcessor
from src.worker.worker import process_repurpose_job

logger = logging.getLogger("repurpose_api")
logger.setLevel(logging.INFO)

router = APIRouter()

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
            detail="A job for this URL is already queued or processing.",
        )

    new_job = ContentJob(
        youtube_url=url_str,
        video_id=video_id,
        status="queued",
        session_id=session_id,
        brand_profile_id=payload.brand_profile_id,
    )
    db.add(new_job)
    await db.commit()
    await db.refresh(new_job)

    # Initial event persistence
    await event_service.emit(
        new_job.id,
        "job_created",
        {"job_id": new_job.id, "video_id": video_id, "url": url_str},
    )

    # Dispatch to Redis ARQ worker with fallback to in-memory task
    dispatched_to_arq = False
    try:
        redis = await get_redis_pool()
        await redis.enqueue_job(
            "process_repurpose_job",
            new_job.id,
            url_str,
            _job_id=f"job_{new_job.id}",
        )
        dispatched_to_arq = True
        logger.info("Job %d enqueued to ARQ worker queue", new_job.id)
    except Exception as q_err:
        logger.warning(
            "Redis queue unavailable (%s) — falling back to background worker task",
            q_err,
        )
        background_tasks.add_task(process_repurpose_job, {}, new_job.id, url_str)

    logger.info(
        "Job accepted",
        extra={
            "job_id": new_job.id,
            "video_id": video_id,
            "session_id": session_id,
            "arq": dispatched_to_arq,
        },
    )

    return {
        "job_id": new_job.id,
        "status": "queued",
        "message": "Job accepted and queued. Stream /jobs/{job_id}/events for live updates.",
    }


@router.get("/jobs/{job_id}/events")
async def stream_job_events(
    job_id: int,
    request: Request,
    last_event_id: int | None = Query(None, alias="last_event_id"),
    db: AsyncSession = Depends(get_db),
):
    """Server-Sent Events endpoint streaming real-time stage progress with Last-Event-ID replay."""
    session_id = get_session_id(request)

    # Validate session ownership
    result = await db.execute(
        select(ContentJob).where(
            ContentJob.id == job_id,
            ContentJob.session_id == session_id,
        )
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(
            status_code=404,
            detail=f"Job {job_id} not found or not owned by session.",
        )

    # Check header or query parameter for reconnect replay sequence
    raw_header = request.headers.get("last-event-id")
    effective_last_id = None
    if raw_header and raw_header.isdigit():
        effective_last_id = int(raw_header)
    elif last_event_id is not None:
        effective_last_id = last_event_id

    return StreamingResponse(
        event_service.subscribe_events(job_id, effective_last_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


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


@router.post("/jobs/{job_id}/assets/{asset_type}/retry", status_code=202)
async def retry_single_asset(
    job_id: int,
    asset_type: str,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Targeted retry endpoint to regenerate a single failed or disputed asset."""
    valid_types = {"blog", "twitter_thread", "linkedin_post", "chapters"}
    if asset_type not in valid_types:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid asset_type '{asset_type}'. Valid types: {', '.join(sorted(valid_types))}",
        )

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

    try:
        redis = await get_redis_pool()
        await redis.enqueue_job(
            "process_repurpose_job",
            job.id,
            job.youtube_url,
        )
    except Exception:
        background_tasks.add_task(process_repurpose_job, {}, job.id, job.youtube_url)

    job.status = "queued"
    await db.commit()

    await event_service.emit(
        job.id,
        "retrying_assets",
        {"targets": [asset_type], "message": f"Targeted retry for '{asset_type}' queued."},
    )

    return {
        "job_id": job.id,
        "asset_type": asset_type,
        "status": "queued",
        "message": f"Targeted retry for '{asset_type}' accepted.",
    }


@router.delete("/jobs/{job_id}", status_code=200)
async def delete_job(
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
        raise HTTPException(
            status_code=404,
            detail=f"Job {job_id} not found or not owned by session.",
        )

    await db.delete(job)
    await db.commit()

    return {"status": "success", "message": f"Job {job_id} deleted successfully."}
