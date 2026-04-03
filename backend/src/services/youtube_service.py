import asyncio
import re
import logging
from groq import AsyncGroq
from supadata import Supadata, SupadataError
from urllib.parse import urlparse
from src.core.config import settings

logger = logging.getLogger("repurpose_api")

groq_client = AsyncGroq(api_key=settings.GROQ_API_KEY)

# Supadata client — uses requests internally (sync), so we wrap calls in
# asyncio.to_thread to avoid blocking the async event loop
supadata_client = Supadata(api_key=settings.SUPADATA_API_KEY)

MAX_TRANSCRIPT_CHARS = 50_000


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
    def _fetch_transcript_sync(video_url: str) -> str | None:
        """
        Synchronous Supadata call — runs in a thread via asyncio.to_thread.

        FIXES vs previous httpx approach:
          1. Correct endpoint: SDK calls /v1/transcript (not /v1/youtube/transcript)
          2. Correct param:    `url=` full YouTube URL (not `videoId=` bare ID)
          3. text=True:       Returns content as a plain str, not a list of chunks
          4. BatchJob guard:  Some long videos return a job_id for async processing;
                              we detect and reject those rather than crashing on .content
        """
        try:
            result = supadata_client.transcript(
                url=video_url,
                lang="en",
                text=True,   
            )

            # If the video is very long, Supadata may return a BatchJob instead
            # of an immediate Transcript — we can't poll for it in this flow.
            from supadata.types import BatchJob
            if isinstance(result, BatchJob):
                logger.warning(
                    "Supadata returned async BatchJob — video too long for sync fetch",
                    extra={"job_id": result.job_id, "url": video_url},
                )
                return None

            content = result.content  # str when text=True
            if not content:
                logger.warning("Supadata returned empty content", extra={"url": video_url})
                return None

            return content.strip() if isinstance(content, str) else None

        except SupadataError as e:
            logger.error(
                "Supadata API error",
                extra={"url": video_url, "error": str(e), "status": getattr(e, "status_code", None)},
            )
            return None
        except Exception as e:
            logger.error("Supadata unexpected error", extra={"url": video_url, "error": str(e)})
            return None

    @staticmethod
    async def get_transcript(video_id: str) -> str | None:
        """
        Fetches the transcript via Supadata. The Supadata SDK uses the
        `requests` library (synchronous), so the call is offloaded to a
        thread pool with asyncio.to_thread to keep the event loop free.
        """
        video_url = f"https://www.youtube.com/watch?v={video_id}"

        transcript = await asyncio.to_thread(
            ContentProcessor._fetch_transcript_sync, video_url
        )

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
    async def _call_groq_with_retry(
        prompt_type: str,
        system_instruction: str,
        content: str,
        model: str = "llama-3.3-70b-versatile",
        retries: int = 3,
    ) -> tuple[str, str]:
        last_error = None
        for attempt in range(retries):
            try:
                response = await groq_client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_instruction},
                        {"role": "user", "content": f"<transcript>\n{content}\n</transcript>"},
                    ],
                    temperature=0.7,
                )
                return prompt_type, response.choices[0].message.content
            except Exception as e:
                last_error = e
                if attempt < retries - 1:
                    await asyncio.sleep(2 ** attempt)
        return prompt_type, f"Error: {last_error}"

    @staticmethod
    async def generate_assets(transcript: str) -> dict:
        safe_transcript = ContentProcessor.truncate_transcript(transcript)

        results = await asyncio.gather(
            ContentProcessor._call_groq_with_retry(
                "blog",
                (
                    "You are an expert SEO copywriter. "
                    "Write a detailed, SEO-optimized blog post based on the transcript. "
                    "Use Markdown formatting."
                ),
                safe_transcript,
                model="llama-3.3-70b-versatile",
            ),
            ContentProcessor._call_groq_with_retry(
                "tweets",
                (
                    "You are a viral social media manager. "
                    "Create a viral Twitter thread (max 10 tweets) based on the transcript. "
                    "Output ONLY a raw JSON list of strings. "
                    "No markdown, no code fences, no preamble — just the JSON array."
                ),
                safe_transcript,
                model="llama-3.3-70b-versatile",
            ),
            ContentProcessor._call_groq_with_retry(
                "linkedin",
                (
                    "You are a B2B thought leader. "
                    "Write a professional, engaging LinkedIn post summarising this video."
                ),
                safe_transcript,
                model="llama-3.1-8b-instant",
            ),
            return_exceptions=True,
        )

        output: dict[str, str | None] = {}
        for result in results:
            if isinstance(result, Exception):
                logger.error("Asset generation failed", extra={"error": str(result)})
            else:
                key, value = result
                output[key] = value

        return output