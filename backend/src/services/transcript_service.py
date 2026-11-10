import asyncio
import logging
from typing import Any

from sqlalchemy import select
from supadata import Supadata, SupadataError
from supadata.types import BatchJob, Transcript

from src.core.config import settings
from src.db.session import AsyncSessionLocal
from src.models.content import VideoTranscript
from src.schemas.content import CanonicalVideoBrief
from src.schemas.transcript import TranscriptSegment, VideoMetadata

logger = logging.getLogger("repurpose_api.transcript")


class TranscriptUnavailableError(Exception):
    """Raised when transcript extraction fails completely."""

    pass


class VideoTooLongError(Exception):
    """Raised when video exceeds system maximum duration."""

    def __init__(self, duration_seconds: int, limit_minutes: int = 180):
        self.duration_seconds = duration_seconds
        self.limit_minutes = limit_minutes
        super().__init__(
            f"Video duration ({duration_seconds // 60}m {duration_seconds % 60}s) "
            f"exceeds the maximum {limit_minutes}-minute threshold."
        )


class TranscriptService:
    """Supadata provider abstraction supporting timestamped segment normalization,

    asynchronous batch job polling, and PostgreSQL caching of raw transcripts and briefs.
    """

    def __init__(self, client: Supadata | None = None):
        self.client = client or Supadata(api_key=settings.SUPADATA_API_KEY)

    def _sync_get_metadata(self, video_url: str) -> VideoMetadata:
        try:
            meta = self.client.metadata(url=video_url)
            duration = (
                meta.media.duration if (meta.media and meta.media.duration is not None) else None
            )
            title = getattr(meta, "title", None)
            return VideoMetadata(video_id="", title=title, duration_seconds=duration)
        except Exception as e:
            logger.warning("Could not fetch metadata for %s: %s", video_url, e)
            return VideoMetadata(video_id="")

    def _sync_fetch_transcript(self, video_url: str) -> list[TranscriptSegment]:
        try:
            result = self.client.transcript(url=video_url, lang="en", text=False)

            # Case A: Asynchronous BatchJob returned for long videos
            if isinstance(result, BatchJob):
                logger.info("Supadata returned BatchJob (%s), initiating polling...", result.job_id)
                return self._poll_batch_job_sync(result.job_id)

            # Case B: Immediate Transcript returned
            if isinstance(result, Transcript):
                return self._normalize_content(result.content)

            raise TranscriptUnavailableError(f"Unexpected Supadata return type: {type(result)}")

        except SupadataError as e:
            logger.error("Supadata transcript API error: %s", e)
            raise TranscriptUnavailableError(f"Supadata API error: {e}") from e
        except Exception as e:
            logger.error("Unexpected error fetching transcript: %s", e)
            raise TranscriptUnavailableError(f"Transcript extraction failed: {e}") from e

    def _poll_batch_job_sync(
        self, job_id: str, max_wait_seconds: int = 90
    ) -> list[TranscriptSegment]:
        poll_interval = 3.0
        elapsed = 0.0

        while elapsed < max_wait_seconds:
            import time

            time.sleep(poll_interval)
            elapsed += poll_interval

            try:
                batch_res = self.client.youtube.batch.get_batch_results(job_id=job_id)
                status = getattr(batch_res, "status", "").lower()
                logger.info("Batch job %s status: %s (elapsed %.1fs)", job_id, status, elapsed)

                if status == "completed":
                    if batch_res.results and len(batch_res.results) > 0:
                        content = getattr(batch_res.results[0], "content", None)
                        if content:
                            return self._normalize_content(content)
                    raise TranscriptUnavailableError(
                        "Batch job completed but returned empty results."
                    )
                elif status == "failed":
                    raise TranscriptUnavailableError(f"Batch job {job_id} failed on provider side.")

            except Exception as poll_err:
                logger.warning("Error checking batch job %s: %s", job_id, poll_err)

            poll_interval = min(poll_interval * 1.3, 10.0)

        raise TranscriptUnavailableError(
            f"Batch transcript job timed out after {max_wait_seconds}s."
        )

    def _normalize_content(self, content: Any) -> list[TranscriptSegment]:
        """Normalizes various Supadata content formats into a clean list of TranscriptSegment objects."""
        segments: list[TranscriptSegment] = []

        if isinstance(content, list):
            for i, chunk in enumerate(content):
                text = getattr(chunk, "text", None) or (
                    chunk.get("text") if isinstance(chunk, dict) else str(chunk)
                )
                raw_offset = (
                    getattr(chunk, "offset", None)
                    if not isinstance(chunk, dict)
                    else chunk.get("offset")
                )
                raw_duration = (
                    getattr(chunk, "duration", None)
                    if not isinstance(chunk, dict)
                    else chunk.get("duration")
                )

                offset_ms = int(raw_offset) if raw_offset is not None else (i * 3000)
                dur_ms = int(raw_duration) if raw_duration is not None else 3000

                clean_text = str(text).strip()
                if clean_text:
                    segments.append(
                        TranscriptSegment(
                            id=len(segments),
                            start_ms=offset_ms,
                            end_ms=offset_ms + dur_ms,
                            text=clean_text,
                        )
                    )

        elif isinstance(content, str):
            # Fallback for plain text: split into sentence-based segments with estimated timing
            import re

            sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", content) if s.strip()]
            current_ms = 0
            for i, sent in enumerate(sentences):
                # Assume average 150 words per minute ~ 400ms per word
                est_duration = max(len(sent.split()) * 400, 2000)
                segments.append(
                    TranscriptSegment(
                        id=i,
                        start_ms=current_ms,
                        end_ms=current_ms + est_duration,
                        text=sent,
                    )
                )
                current_ms += est_duration

        if not segments:
            raise TranscriptUnavailableError(
                "No readable transcript segments extracted from provider content."
            )

        return segments

    async def get_or_fetch_transcript(
        self, video_id: str, video_url: str
    ) -> tuple[list[TranscriptSegment], VideoMetadata]:
        """Loads transcript segments from PostgreSQL cache if present; otherwise fetches from Supadata and caches."""
        # 1. Check PostgreSQL Cache
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(VideoTranscript).where(VideoTranscript.video_id == video_id)
            )
            cached = result.scalar_one_or_none()
            if cached and cached.segments:
                logger.info(
                    "Loaded transcript from cache for video %s (%d segments)",
                    video_id,
                    len(cached.segments),
                )
                segments = [TranscriptSegment.model_validate(s) for s in cached.segments]
                metadata = VideoMetadata(
                    video_id=video_id,
                    title=cached.title,
                    duration_seconds=cached.duration_seconds,
                )
                return segments, metadata

        # 2. Fetch Metadata & Validate Duration
        metadata = await asyncio.to_thread(self._sync_get_metadata, video_url)
        metadata.video_id = video_id
        if metadata.duration_seconds and metadata.duration_seconds > 180 * 60:
            raise VideoTooLongError(metadata.duration_seconds)

        # 3. Fetch Transcript Segments
        segments = await asyncio.to_thread(self._sync_fetch_transcript, video_url)

        # 4. Save to PostgreSQL Cache
        async with AsyncSessionLocal() as db:
            try:
                new_cached = VideoTranscript(
                    video_id=video_id,
                    title=metadata.title,
                    duration_seconds=metadata.duration_seconds,
                    segments=[s.model_dump() for s in segments],
                )
                db.add(new_cached)
                await db.commit()
                logger.info("Cached %d transcript segments for video %s", len(segments), video_id)
            except Exception as cache_err:
                await db.rollback()
                logger.warning("Could not persist transcript cache: %s", cache_err)

        return segments, metadata

    async def get_cached_brief(self, video_id: str) -> CanonicalVideoBrief | None:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(VideoTranscript).where(VideoTranscript.video_id == video_id)
            )
            cached = result.scalar_one_or_none()
            if cached and cached.canonical_brief:
                return CanonicalVideoBrief.model_validate(cached.canonical_brief)
        return None

    async def cache_brief(self, video_id: str, brief: CanonicalVideoBrief) -> None:
        async with AsyncSessionLocal() as db:
            try:
                result = await db.execute(
                    select(VideoTranscript).where(VideoTranscript.video_id == video_id)
                )
                cached = result.scalar_one_or_none()
                if cached:
                    cached.canonical_brief = brief.model_dump()
                    await db.commit()
                    logger.info("Saved CanonicalVideoBrief to cache for video %s", video_id)
            except Exception as e:
                await db.rollback()
                logger.warning("Could not cache CanonicalVideoBrief: %s", e)


transcript_service = TranscriptService()
