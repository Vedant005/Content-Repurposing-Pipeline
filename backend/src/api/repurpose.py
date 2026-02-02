import json
import re
import logging
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, HttpUrl, validator

from src.schemas.content import JobStatusResponse, VideoRequest
from src.db.session import get_db, AsyncSessionLocal
from src.models.content import ContentJob
from src.services.youtube_service import ContentProcessor

logger = logging.getLogger("repurpose_api")
logger.setLevel(logging.INFO)

router = APIRouter()

def clean_json_string(json_str: str):
    if not json_str:
        return []
    cleaned = re.sub(r"```json\s*", "", json_str)
    cleaned = re.sub(r"```", "", cleaned)
    return cleaned.strip()

#  Background Task Logic 
async def process_video_task(job_id: int, url: str):
    """
    Runs in background. MUST manage its own DB session.
    """
    logger.info(f"Starting job {job_id} for URL: {url}")
    
    # Create fresh session for this background task
    async with AsyncSessionLocal() as db:
        try:
            # 1. Fetch the job record
            result = await db.execute(select(ContentJob).where(ContentJob.id == job_id))
            job = result.scalar_one_or_none()
            
            if not job:
                logger.error(f"Job {job_id} not found in background task.")
                return

            # 2. Extract Video ID
            processor = ContentProcessor()
            video_id = processor.get_video_id(url)
            
            if not video_id:
                raise ValueError("Could not extract Video ID from URL.")

            # 3. Get Transcript
            transcript = processor.get_transcript(video_id)
            if not transcript:
                raise ValueError("No transcript found (video might not have captions).")

            # 4. Generate AI Content
            content = await processor.generate_assets(transcript)

            # 5. Parse JSON specifically for Tweets
            # We treat the blog and linkedin as pure text, but tweets need to be a list
            try:
                raw_tweets = content.get('tweets', '[]')
                cleaned_tweets = clean_json_string(raw_tweets)
                tweets_json = json.loads(cleaned_tweets)
            except json.JSONDecodeError:
                logger.warning(f"Job {job_id}: Failed to parse tweets JSON. Saving as raw text.")
                tweets_json = {"raw_error": "JSON Parse Fail", "content": content.get('tweets')}

            job.blog_content = content.get('blog')
            job.tweets = tweets_json
            job.linkedin_post = content.get('linkedin')
            job.status = "completed"
            
            await db.commit()
            logger.info(f"Job {job_id} completed successfully.")

        except Exception as e:
            logger.error(f"Job {job_id} failed: {str(e)}")
            await db.rollback() 
            
            # Re-fetch job to update status (in case session state is messy)
            result = await db.execute(select(ContentJob).where(ContentJob.id == job_id))
            job = result.scalar_one_or_none()
            
            if job:
                job.status = "failed"
                job.error_message = str(e)
                await db.commit()


@router.post("/repurpose", status_code=202)
async def repurpose_video(
    request: VideoRequest, 
    background_tasks: BackgroundTasks, 
    db: AsyncSession = Depends(get_db)
):
   
    new_job = ContentJob(youtube_url=str(request.url), status="processing")
    db.add(new_job)
    await db.commit()
    await db.refresh(new_job)

    background_tasks.add_task(process_video_task, new_job.id, str(request.url))

    return {"job_id": new_job.id, "status": "processing", "message": "Job started in background"}

@router.get("/status/{job_id}", response_model=JobStatusResponse)
async def check_status(job_id: int, db: AsyncSession = Depends(get_db)):
  
    result = await db.execute(select(ContentJob).where(ContentJob.id == job_id))
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    return job