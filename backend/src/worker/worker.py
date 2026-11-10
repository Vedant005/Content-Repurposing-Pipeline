import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from arq.connections import RedisSettings
from sqlalchemy import select

from src.core.config import settings
from src.db.session import AsyncSessionLocal
from src.models.content import ContentJob
from src.services.event_service import event_service
from src.services.youtube_service import ContentProcessor

logger = logging.getLogger("repurpose_worker")


def clean_json_string(json_str: str) -> str:
    if not json_str:
        return "[]"
    import re

    cleaned = re.sub(r"```json\s*", "", json_str)
    cleaned = re.sub(r"```", "", cleaned)
    return cleaned.strip()


async def recover_stale_jobs() -> int:
    """Finds jobs stranded in 'processing' state older than 15 minutes and transitions them to failed."""
    cutoff = datetime.now(UTC) - timedelta(minutes=15)
    recovered = 0

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(ContentJob).where(
                ContentJob.status == "processing",
                ContentJob.updated_at < cutoff,
            )
        )
        stale_jobs = result.scalars().all()
        for job in stale_jobs:
            job.status = "failed"
            job.error_message = "Worker execution timed out or was interrupted during processing."
            recovered += 1
            logger.warning("Reaped stale job %d", job.id)
            await event_service.emit(
                job.id,
                "job_failed",
                {"error": "Job timed out or worker process was restarted."},
            )
        if recovered > 0:
            await db.commit()

    return recovered


async def worker_startup(ctx: dict[str, Any]) -> None:
    logger.info("ARQ Worker starting up. Checking for stale in-flight jobs...")
    recovered = await recover_stale_jobs()
    logger.info("Worker startup complete. Reaped %d stale jobs.", recovered)


async def worker_shutdown(ctx: dict[str, Any]) -> None:
    logger.info("ARQ Worker shutting down cleanly.")


async def process_repurpose_job(ctx: dict[str, Any], job_id: int, url: str) -> str:
    """Idempotent background execution of video transcription, Map-Reduce, and asset generation via LangGraph."""
    logger.info("ARQ processing task started for job %d (url: %s)", job_id, url)

    session_id = "default"
    brand_profile_id = None
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(ContentJob).where(ContentJob.id == job_id))
        job = result.scalar_one_or_none()

        if not job:
            logger.error("Job %d not found in database", job_id)
            return "job_not_found"

        # Idempotency guard: do not re-process jobs already completed or failed
        if job.status in ("completed", "failed", "partial_success"):
            logger.warning(
                "Job %d is already in final state '%s' — skipping execution.", job_id, job.status
            )
            return f"already_{job.status}"

        session_id = job.session_id
        brand_profile_id = job.brand_profile_id
        job.status = "processing"
        await db.commit()

    # Emit job_started event
    await event_service.emit(
        job_id, "job_started", {"message": "Job picked up by background worker."}
    )

    try:
        video_id = ContentProcessor.get_video_id(url)
        if not video_id:
            raise ValueError("Could not extract a valid YouTube video ID from URL.")

        from src.pipeline.graph import repurposing_pipeline
        from src.pipeline.state import PipelineState

        initial_state: PipelineState = {
            "job_id": job_id,
            "video_id": video_id,
            "url": url,
            "session_id": session_id,
            "brand_profile_id": brand_profile_id,
            "attempt_counts": {},
            "assets": {},
        }

        final_state = await repurposing_pipeline.ainvoke(initial_state)
        final_status = final_state.get("final_status", "completed")
        logger.info("Pipeline completed for job %d with status %s", job_id, final_status)
        return final_status

    except Exception as e:
        logger.error("Job %d failed during worker execution: %s", job_id, e)
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(ContentJob).where(ContentJob.id == job_id))
            job = result.scalar_one_or_none()
            if job:
                job.status = "failed"
                job.error_message = str(e)[:1000]
                await db.commit()

        await event_service.emit(job_id, "job_failed", {"error": str(e)})
        return f"failed: {e}"


class WorkerSettings:
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    functions = [process_repurpose_job]
    on_startup = worker_startup
    on_shutdown = worker_shutdown
    max_jobs = 10
    job_timeout = 900
    keep_result = 3600
