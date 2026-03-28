import json
import re
import asyncio
import logging
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from src.schemas.content import JobStatusResponse, VideoRequest, HistoryResponse
from src.db.session import get_db, AsyncSessionLocal
from src.models.content import ContentJob
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
            result = await fail_db.execute(
                select(ContentJob).where(ContentJob.id == job_id)
            )
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
                    raise ValueError("Tweets response is not a JSON list")
            except (json.JSONDecodeError, ValueError) as parse_err:
                logger.warning(
                    "Tweet JSON parse failed, saving raw",
                    extra={"job_id": job_id, "error": str(parse_err)},
                )
                tweets_json = {"parse_error": str(parse_err), "raw": content.get("tweets")}

            job.blog_content  = content.get("blog")
            job.tweets        = tweets_json
            job.linkedin_post = content.get("linkedin")
            job.status        = "completed"

            await db.commit()
            logger.info("Job completed", extra={"job_id": job_id})

        except Exception as e:
            await db.rollback()
            logger.error("Job failed", extra={"job_id": job_id, "error": str(e)})
            await _mark_job_failed(job_id, str(e))


async def process_video_task(job_id: int, url: str) -> None:
    logger.info("Background task started", extra={"job_id": job_id, "url": url})
    try:
        await asyncio.wait_for(_run_job(job_id, url), timeout=JOB_TIMEOUT_SECONDS)
    except asyncio.TimeoutError:
        logger.error("Job timed out", extra={"job_id": job_id, "timeout": JOB_TIMEOUT_SECONDS})
        await _mark_job_failed(
            job_id,
            f"Job exceeded the {JOB_TIMEOUT_SECONDS}s timeout and was cancelled.",
        )

@router.post("/repurpose", status_code=202)
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

    new_job = ContentJob(
        youtube_url=url_str,
        status="processing",
        session_id=session_id,               
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
    """
    Supports pagination:
      GET /history            → first 20 jobs
      GET /history?offset=20  → next 20 jobs
      GET /history?limit=5    → only 5 jobs

    Only lightweight fields are returned (no blog_content / tweets body)
    to keep the payload small. Use GET /status/{job_id} for full results.
    """
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

    return job