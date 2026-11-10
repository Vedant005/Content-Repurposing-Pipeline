import asyncio
import logging
import re
from urllib.parse import urlparse

from supadata import Supadata, SupadataError

from src.core.config import settings
from src.services.llm_provider import llm_provider

logger = logging.getLogger("repurpose_api")

supadata_client = Supadata(api_key=settings.SUPADATA_API_KEY)

MAX_TRANSCRIPT_CHARS = 50_000
MAX_VIDEO_MINUTES = 25
MAX_VIDEO_SECONDS = MAX_VIDEO_MINUTES * 60  # 1500 seconds


class VideoTooLongError(Exception):
    """Raised when a video exceeds MAX_VIDEO_MINUTES."""

    def __init__(self, duration_seconds: int):
        self.duration_seconds = duration_seconds
        minutes = duration_seconds // 60
        seconds = duration_seconds % 60
        super().__init__(
            f"Video is {minutes}m {seconds}s long, which exceeds the current "
            f"{MAX_VIDEO_MINUTES}-minute limit. Support for longer videos will "
            f"be added in a future update."
        )


class ContentProcessor:
    @staticmethod
    def get_video_id(url: str) -> str | None:
        try:
            parsed = urlparse(url)
        except Exception:
            return None
        valid_hosts = {"www.youtube.com", "youtube.com", "youtu.be", "m.youtube.com"}
        if parsed.hostname not in valid_hosts:
            return None
        regex = r"(?:v=|\/)([0-9A-Za-z_-]{11}).*"
        match = re.search(regex, url)
        return match.group(1) if match else None

    @staticmethod
    def _check_duration_sync(video_url: str) -> None:
        """Fetches video metadata via Supadata and raises VideoTooLongError

        if the duration exceeds MAX_VIDEO_SECONDS.
        """
        try:
            meta = supadata_client.metadata(url=video_url)
        except SupadataError as e:
            logger.warning(
                "Could not fetch metadata for duration check — proceeding",
                extra={"url": video_url, "error": str(e)},
            )
            return

        duration = meta.media.duration if meta.media and meta.media.duration is not None else None

        if duration is None:
            logger.warning(
                "Duration not available in metadata — proceeding without check",
                extra={"url": video_url},
            )
            return

        logger.info(
            "Video duration checked",
            extra={"url": video_url, "duration_seconds": duration, "limit": MAX_VIDEO_SECONDS},
        )

        if duration > MAX_VIDEO_SECONDS:
            raise VideoTooLongError(duration)

    @staticmethod
    def _fetch_transcript_sync(video_url: str) -> str | None:
        try:
            result = supadata_client.transcript(
                url=video_url,
                lang="en",
                text=True,
            )

            from supadata.types import BatchJob

            if isinstance(result, BatchJob):
                logger.warning(
                    "Supadata returned async BatchJob — video too long for sync fetch",
                    extra={"job_id": result.job_id, "url": video_url},
                )
                return None

            content = result.content
            if not content:
                logger.warning("Supadata returned empty content", extra={"url": video_url})
                return None

            return content.strip() if isinstance(content, str) else None

        except SupadataError as e:
            logger.error(
                "Supadata API error",
                extra={
                    "url": video_url,
                    "error": str(e),
                    "status": getattr(e, "status_code", None),
                },
            )
            return None
        except Exception as e:
            logger.error("Supadata unexpected error", extra={"url": video_url, "error": str(e)})
            return None

    @staticmethod
    async def get_transcript(video_id: str) -> str | None:
        video_url = f"https://www.youtube.com/watch?v={video_id}"

        await asyncio.to_thread(ContentProcessor._check_duration_sync, video_url)

        transcript = await asyncio.to_thread(ContentProcessor._fetch_transcript_sync, video_url)

        if transcript:
            logger.info(
                "Transcript fetched via Supadata",
                extra={"video_id": video_id, "chars": len(transcript)},
            )
        else:
            logger.error(
                "Transcript unavailable — Supadata returned nothing",
                extra={"video_id": video_id},
            )

        return transcript

    @staticmethod
    def truncate_transcript(text: str, max_chars: int = MAX_TRANSCRIPT_CHARS) -> str:
        if len(text) <= max_chars:
            return text
        truncated = text[:max_chars]
        last_period = truncated.rfind(".")
        return truncated[: last_period + 1] if last_period > 0 else truncated

    @staticmethod
    async def _generate_asset_safe(
        prompt_type: str,
        system_instruction: str,
        content: str,
        model: str,
    ) -> tuple[str, str | None]:
        try:
            result = await llm_provider.generate_text(
                system_instruction=system_instruction,
                user_content=f"<untrusted_transcript>\n{content}\n</untrusted_transcript>",
                model=model,
            )
            return prompt_type, result
        except Exception as e:
            logger.error("Failed to generate asset %s: %s", prompt_type, e)
            return prompt_type, None

    @staticmethod
    async def generate_assets(transcript: str) -> dict:
        safe_transcript = ContentProcessor.truncate_transcript(transcript)

        results = await asyncio.gather(
            ContentProcessor._generate_asset_safe(
                "blog",
                (
                    "You are an expert SEO copywriter. "
                    "Write a detailed, SEO-optimized blog post based on the transcript. "
                    "Use Markdown formatting with clear H2/H3 headers."
                ),
                safe_transcript,
                model=settings.GROQ_DEEP_MODEL,
            ),
            ContentProcessor._generate_asset_safe(
                "tweets",
                (
                    "You are a viral social media manager. "
                    "Create a viral Twitter thread (between 3 and 10 tweets) based on the transcript. "
                    'Output ONLY a raw JSON array of strings (e.g. ["tweet 1", "tweet 2"]). '
                    "No markdown fences, no extra text, strictly valid JSON."
                ),
                safe_transcript,
                model=settings.GROQ_FAST_MODEL,
            ),
            ContentProcessor._generate_asset_safe(
                "linkedin",
                (
                    "You are an executive thought leader. "
                    "Write a professional, engaging LinkedIn post summarising this video with takeaways and CTA."
                ),
                safe_transcript,
                model=settings.GROQ_FAST_MODEL,
            ),
            return_exceptions=True,
        )

        output: dict[str, str | None] = {}
        for result in results:
            if isinstance(result, Exception):
                logger.error("Asset generation task failed", extra={"error": str(result)})
            else:
                key, value = result
                output[key] = value

        return output
