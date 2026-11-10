from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


class AssetStatusEnum(StrEnum):
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


class VideoRequest(BaseModel):
    url: HttpUrl
    brand_profile_id: int | None = None

    @field_validator("url", mode="before")
    @classmethod
    def validate_youtube_url(cls, v: Any) -> str:
        url_str = str(v)
        if "youtube.com" not in url_str and "youtu.be" not in url_str:
            raise ValueError("URL must be from YouTube (youtube.com or youtu.be)")
        return url_str


# ── Structured Asset Outputs ───────────────────────────────────────────────────


class TweetItem(BaseModel):
    tweet_number: int = Field(..., ge=1, le=15, description="1-based index in the thread")
    content: str = Field(..., min_length=1, max_length=280, description="Tweet copy, max 280 chars")
    hook_or_takeaway: str = Field(
        ..., description="Editorial role: hook, core point, quote, or CTA"
    )


class TwitterThreadOutput(BaseModel):
    thread: list[TweetItem] = Field(
        ...,
        min_length=3,
        max_length=10,
        description="Thread of 3 to 10 viral, cohesive tweets",
    )


class BlogPostOutput(BaseModel):
    title: str = Field(..., min_length=5, max_length=150, description="SEO optimized headline")
    meta_description: str = Field(..., min_length=20, max_length=200, description="Search snippet")
    reading_time_minutes: int = Field(..., ge=1, le=60)
    markdown_body: str = Field(
        ..., min_length=200, description="Full blog post formatted in markdown"
    )
    key_takeaways: list[str] = Field(..., min_length=3, max_length=7)


class LinkedInPostOutput(BaseModel):
    hook_line: str = Field(
        ..., min_length=10, max_length=200, description="Attention grabbing first line"
    )
    body_paragraphs: list[str] = Field(..., min_length=2, max_length=6, description="Core insights")
    call_to_action: str = Field(..., min_length=10, max_length=200, description="Closing CTA")
    hashtags: list[str] = Field(default_factory=list, max_length=7)


class ChapterItem(BaseModel):
    timestamp_seconds: int = Field(..., ge=0)
    timestamp_formatted: str = Field(..., description="e.g. 02:45")
    title: str = Field(..., min_length=3, max_length=100)
    summary: str = Field(..., min_length=10, max_length=300)
    source_segment_id: int = Field(..., ge=0)


class ChaptersOutput(BaseModel):
    chapters: list[ChapterItem] = Field(..., min_length=2, description="Chronological chapters")


class CanonicalVideoBrief(BaseModel):
    title: str = Field(..., description="Video topic / title")
    executive_summary: str = Field(..., min_length=100, max_length=2500)
    core_arguments: list[str] = Field(..., min_length=3, max_length=10)
    quotable_moments: list[dict[str, Any]] = Field(
        default_factory=list,
        description="List of {quote: str, segment_id: int, timestamp_formatted: str}",
    )
    suggested_chapters: list[dict[str, Any]] = Field(default_factory=list)


class AssetCritiqueItem(BaseModel):
    asset_name: str
    tone_score: int = Field(..., ge=1, le=10)
    clarity_score: int = Field(..., ge=1, le=10)
    passed: bool
    critique_notes: str
    actionable_revisions: list[str] = Field(default_factory=list)


class AICritiqueOutput(BaseModel):
    critiques: list[AssetCritiqueItem]


# ── API Responses (Preserving Backward Compatibility) ──────────────────────────


class AssetDetailResponse(BaseModel):
    id: int
    asset_type: str
    status: str
    content: dict[str, Any] | list[Any] | str | None = None
    validation_errors: list[str] | dict[str, Any] | None = None
    critique_score: float | None = None
    retry_count: int = 0
    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class JobStatusResponse(BaseModel):
    id: int
    status: str
    error_message: str | None = None
    blog_content: str | None = None
    tweets: list[str] | dict[str, Any] | None = None
    linkedin_post: str | None = None
    assets: list[AssetDetailResponse] | None = None

    model_config = ConfigDict(from_attributes=True)


class HistoryResponse(BaseModel):
    id: int
    youtube_url: str
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
