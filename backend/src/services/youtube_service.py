import asyncio
import json
import re
from google import genai
from google.genai import types
from youtube_transcript_api import YouTubeTranscriptApi
from src.core.config import settings


client = genai.Client(api_key=settings.GEMINI_API_KEY)

ytt_api = YouTubeTranscriptApi()

class ContentProcessor:
    @staticmethod
    def get_video_id(url: str):
        regex = r"(?:v=|\/)([0-9A-Za-z_-]{11}).*"
        match = re.search(regex, url)
        if match:
            return match.group(1)
        return None

    @staticmethod
    def get_transcript(video_id: str):
        try:
            transcript = ytt_api.fetch(video_id)
            return " ".join([t.text for t in transcript])
        except Exception as e:
            print(f"Error fetching transcript: {e}")
            return None

    @staticmethod
    async def generate_assets(transcript: str):
        safe_transcript = transcript[:30000]

        async def call_gemini(prompt_type, system_instruction):
            try:
                response = await client.aio.models.generate_content(
                    model='gemini-3-flash-preview',
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        temperature=0.7
                    ),
                    contents=[safe_transcript]
                )
                return prompt_type, response.text
            except Exception as e:
                print(f"Gemini Error ({prompt_type}): {e}")
                return prompt_type, f"Error generating content: {str(e)}"

        results = await asyncio.gather(
            call_gemini(
                "blog", 
                "You are an expert SEO copywriter. Write a detailed, SEO-optimized blog post based on this transcript. Use Markdown formatting."
            ),
            call_gemini(
                "tweets", 
                "You are a viral social media manager. Create a viral Twitter thread (max 10 tweets) based on this transcript. output ONLY a raw JSON list of strings. No markdown formatting around the JSON."
            ),
            call_gemini(
                "linkedin", 
                "You are a B2B thought leader. Write a professional, engaging LinkedIn summary of this video."
            )
        )
        
        return {k: v for k, v in results}