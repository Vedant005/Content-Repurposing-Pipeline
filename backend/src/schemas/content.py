import json
import re
from typing import Optional, Any, Dict, List, Union
from pydantic import BaseModel, HttpUrl, validator, Field
from datetime import datetime

class VideoRequest(BaseModel):
    url: HttpUrl

    @validator("url")
    def validate_youtube_url(cls, v):
        url_str = str(v)
        if "youtube.com" not in url_str and "youtu.be" not in url_str:
            raise ValueError("URL must be from YouTube")
        return url_str

class JobStatusResponse(BaseModel):
    id: int
    status: str
    error_message: Optional[str] = None
    blog_content: Optional[str] = None
    tweets: Optional[Union[List[str], Dict[str, Any]]] = None 
    linkedin_post: Optional[str] = None
    
    class Config:
        from_attributes = True

class HistoryResponse(BaseModel):
    id:           int
    youtube_url:  str
    status:       str
    created_at:   datetime

    model_config = {"from_attributes": True}