import asyncio
import re
import os
import uuid
import logging
import httpx
from groq import AsyncGroq
from urllib.parse import urlparse
from src.core.config import settings

logger = logging.getLogger("repurpose_api")

groq_client = AsyncGroq(api_key=settings.GROQ_API_KEY)

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
    async def get_transcript(video_id: str) -> str | None:
        """
        Fetches the transcript via Supadata's API.

        Supadata runs the YouTube fetch on their own infrastructure, so your
        server never opens a connection to youtube.com at all. This bypasses
        Render's egress proxy block entirely.

        Free tier: 500 requests/month — enough for a portfolio/MVP.
        Sign up at supadata.ai → copy the API key → add SUPADATA_API_KEY to
        your Render environment variables.

        Fallback: if Supadata fails (quota exceeded, video has no captions),
        the method returns None and the job is marked failed with a clear message.
        If you later upgrade to Render paid tier, you can re-add yt-dlp here.
        """
        api_key = getattr(settings, "SUPADATA_API_KEY", None)
        if not api_key:
            logger.error("SUPADATA_API_KEY not set — cannot fetch transcript")
            return None

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(
                    "https://api.supadata.ai/v1/youtube/transcript",
                    params={"videoId": video_id, "lang": "en", "text": "true"},
                    headers={"x-api-key": api_key},
                )

            if response.status_code == 200:
                data = response.json()
                # `text=true` returns a flat string; fall back to joining chunks
                transcript = data.get("content") or ""
                if isinstance(transcript, list):
                    transcript = " ".join(
                        chunk.get("text", "") for chunk in transcript
                    )
                if transcript:
                    logger.info("Transcript fetched via Supadata", extra={"video_id": video_id, "chars": len(transcript)})
                    return transcript.strip()
                logger.warning("Supadata returned empty transcript", extra={"video_id": video_id})
                return None

            elif response.status_code == 404:
                logger.warning("No transcript available (Supadata 404)", extra={"video_id": video_id})
                return None

            elif response.status_code == 402:
                logger.error("Supadata quota exceeded — upgrade plan or wait for reset")
                return None

            else:
                logger.error(
                    "Supadata unexpected response",
                    extra={"video_id": video_id, "status": response.status_code, "body": response.text[:200]},
                )
                return None

        except httpx.TimeoutException:
            logger.error("Supadata request timed out", extra={"video_id": video_id})
            return None
        except Exception as e:
            logger.error("Supadata request failed", extra={"video_id": video_id, "error": str(e)})
            return None

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