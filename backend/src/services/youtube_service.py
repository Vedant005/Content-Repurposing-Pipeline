import asyncio
import re
import os
import uuid
import logging
import tempfile
import yt_dlp
from groq import AsyncGroq

from youtube_transcript_api import YouTubeTranscriptApi
from urllib.parse import urlparse
from src.core.config import settings

logger = logging.getLogger("repurpose_api")

groq_client = AsyncGroq(api_key=settings.GROQ_API_KEY)
ytt_api = YouTubeTranscriptApi()

DOWNLOADS_DIR = "downloads"
MAX_TRANSCRIPT_CHARS = 50_000
MAX_AUDIO_MB = 25

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
    def download_audio(video_url: str, job_token: str) -> str | None:
       
        os.makedirs(DOWNLOADS_DIR, exist_ok=True)

        ydl_opts = {
            "max_filesize": MAX_AUDIO_MB * 1024 * 1024,
            "format": "bestaudio/best",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "128",
            }],
            "outtmpl": f"{DOWNLOADS_DIR}/%(id)s_{job_token}.%(ext)s",
            "quiet": True,
        }

        cookie_file_path = None
        youtube_cookies = os.environ.get("YOUTUBE_COOKIES")

        if youtube_cookies:
            try:
                fd, cookie_file_path = tempfile.mkstemp(suffix=".txt")
                with os.fdopen(fd, 'w') as f:
                    f.write(youtube_cookies)
                
                ydl_opts["cookiefile"] = cookie_file_path
            except Exception as e:
                logger.warning(f"Failed to write temp cookie file: {e}")

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=True)
                video_id = info["id"]
                return f"{DOWNLOADS_DIR}/{video_id}_{job_token}.mp3"
        except Exception as e:
            logger.error("yt-dlp download error", extra={"error": str(e), "url": video_url})
            return None
        finally:
            if cookie_file_path and os.path.exists(cookie_file_path):
                try:
                    os.remove(cookie_file_path)
                except Exception as e:
                    logger.warning(f"Failed to delete temp cookie file: {e}")

    
    @staticmethod
    async def transcribe_with_groq_whisper(audio_path: str) -> str | None:
        size_mb = os.path.getsize(audio_path) / (1024 * 1024)
        if size_mb > MAX_AUDIO_MB:
            logger.warning("Audio too large for Whisper", extra={"size_mb": round(size_mb, 1)})
            return None
        try:
            with open(audio_path, "rb") as f:
                response = await groq_client.audio.transcriptions.create(
                    file=(audio_path, f.read()),
                    model="whisper-large-v3",
                    response_format="text",
                    language="en",
                )
            return response
        except Exception as e:
            logger.error("Groq Whisper error", extra={"error": str(e)})
            return None

    @staticmethod
    async def get_transcript(video_id: str) -> str | None:
      
        try:
            transcript_list = await asyncio.to_thread(ytt_api.fetch, video_id)
            logger.info("Captions found", extra={"video_id": video_id})
            return " ".join([t.text for t in transcript_list])
        except Exception as e:
            logger.warning(
                "No captions, switching to audio fallback",
                extra={"video_id": video_id, "reason": str(e)},
            )

        video_url = f"https://www.youtube.com/watch?v={video_id}"
        job_token = uuid.uuid4().hex[:10] 

        audio_path = await asyncio.to_thread(
            ContentProcessor.download_audio, video_url, job_token
        )
        if not audio_path:
            return None

        try:
            transcript_text = await ContentProcessor.transcribe_with_groq_whisper(audio_path)
        finally:
            
            if os.path.exists(audio_path):
                os.remove(audio_path)

        return transcript_text



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