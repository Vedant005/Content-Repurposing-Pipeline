from sqlalchemy import Column, Integer, String, Text, DateTime, JSON
from sqlalchemy.sql import func
from src.db.base import Base 

class ContentJob(Base):
    __tablename__ = "content_jobs"

    id = Column(Integer, primary_key=True, index=True)
    youtube_url = Column(String, index=True)
    
    status = Column(String, default="processing", index=True)
    error_message = Column(Text, nullable=True)

    blog_content = Column(Text, nullable=True)
    tweets = Column(JSON, nullable=True) 
    linkedin_post = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    session_id    = Column(String(64), nullable=True, index=True)  
    user_id       = Column(Integer, nullable=True, index=True)      # future auth