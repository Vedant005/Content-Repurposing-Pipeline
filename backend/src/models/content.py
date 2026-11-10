from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from src.db.base import Base


class ContentJob(Base):
    __tablename__ = "content_jobs"

    id = Column(Integer, primary_key=True, index=True)
    youtube_url = Column(String, index=True)
    video_id = Column(String(32), nullable=True, index=True)

    status = Column(
        String(32), default="processing", index=True
    )  # queued, processing, completed, partial_success, failed
    error_message = Column(Text, nullable=True)

    # Legacy columns kept for direct compatibility
    blog_content = Column(Text, nullable=True)
    tweets = Column(JSON, nullable=True)
    linkedin_post = Column(Text, nullable=True)

    transcript_id = Column(
        Integer, ForeignKey("video_transcripts.id", ondelete="SET NULL"), nullable=True
    )
    brand_profile_id = Column(
        Integer, ForeignKey("brand_profiles.id", ondelete="SET NULL"), nullable=True
    )

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    session_id = Column(String(64), nullable=True, index=True)
    user_id = Column(Integer, nullable=True, index=True)

    # Relationships
    assets = relationship(
        "ContentAsset", back_populates="job", cascade="all, delete-orphan", lazy="selectin"
    )
    events = relationship(
        "JobEvent", back_populates="job", cascade="all, delete-orphan", lazy="selectin"
    )
    transcript = relationship("VideoTranscript", lazy="joined")
    brand_profile = relationship("BrandProfile", lazy="joined")

    def get_asset(self, asset_type: str) -> "ContentAsset | None":
        for a in self.assets:
            if a.asset_type == asset_type:
                return a
        return None

    def get_effective_blog(self) -> str | None:
        if self.blog_content:
            return self.blog_content
        asset = self.get_asset("blog")
        if asset and asset.content:
            if isinstance(asset.content, dict):
                return asset.content.get("markdown_body") or asset.content.get("content")
            return str(asset.content)
        return None

    def get_effective_tweets(self) -> list[str] | dict | None:
        if self.tweets is not None:
            return self.tweets
        asset = self.get_asset("twitter_thread")
        if asset and asset.content:
            if isinstance(asset.content, dict) and "thread" in asset.content:
                return [t.get("content", "") for t in asset.content["thread"]]
            if isinstance(asset.content, list):
                return asset.content
        return None

    def get_effective_linkedin(self) -> str | None:
        if self.linkedin_post:
            return self.linkedin_post
        asset = self.get_asset("linkedin_post")
        if asset and asset.content:
            if isinstance(asset.content, dict):
                paragraphs = asset.content.get("body_paragraphs", [])
                hook = asset.content.get("hook_line", "")
                cta = asset.content.get("call_to_action", "")
                tags = " ".join([f"#{t.lstrip('#')}" for t in asset.content.get("hashtags", [])])
                parts = [p for p in [hook, "\n\n".join(paragraphs), cta, tags] if p]
                return "\n\n".join(parts)
            return str(asset.content)
        return None


class ContentAsset(Base):
    __tablename__ = "content_assets"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(
        Integer, ForeignKey("content_jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    asset_type = Column(
        String(32), nullable=False, index=True
    )  # blog, twitter_thread, linkedin_post, chapters
    status = Column(
        String(32), default="pending", nullable=False, index=True
    )  # pending, generating, completed, failed
    content = Column(JSON, nullable=True)
    validation_errors = Column(JSON, nullable=True)
    critique_score = Column(Float, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    job = relationship("ContentJob", back_populates="assets")


class JobEvent(Base):
    __tablename__ = "job_events"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(
        Integer, ForeignKey("content_jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sequence_num = Column(Integer, nullable=False, index=True)
    event_type = Column(String(64), nullable=False, index=True)
    payload = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    job = relationship("ContentJob", back_populates="events")


class VideoTranscript(Base):
    __tablename__ = "video_transcripts"

    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(String(32), unique=True, index=True, nullable=False)
    title = Column(String(255), nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    segments = Column(JSON, nullable=False)  # list of {id, start_ms, end_ms, text}
    canonical_brief = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class BrandProfile(Base):
    __tablename__ = "brand_profiles"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(64), nullable=False, index=True)
    brand_name = Column(String(128), nullable=False)
    tone_guidelines = Column(Text, nullable=True)
    target_audience = Column(Text, nullable=True)
    few_shot_examples = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
