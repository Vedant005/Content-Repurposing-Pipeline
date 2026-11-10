from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class BrandProfileCreate(BaseModel):
    brand_name: str = Field(
        ..., min_length=2, max_length=128, description="Name of the brand or creator"
    )
    tone_guidelines: str | None = Field(
        None,
        max_length=2000,
        description="Tone rules, e.g., 'punchy, witty, no jargon, data-first'",
    )
    target_audience: str | None = Field(
        None,
        max_length=1000,
        description="Target demographic, e.g., 'Senior software engineers and CTOs'",
    )
    few_shot_examples: dict[str, Any] | None = Field(
        default_factory=dict,
        description="Key-value mapping of format examples: blog, twitter, linkedin",
    )


class BrandProfileUpdate(BaseModel):
    brand_name: str | None = Field(None, min_length=2, max_length=128)
    tone_guidelines: str | None = Field(None, max_length=2000)
    target_audience: str | None = Field(None, max_length=1000)
    few_shot_examples: dict[str, Any] | None = None


class BrandProfileResponse(BaseModel):
    id: int
    session_id: str
    brand_name: str
    tone_guidelines: str | None = None
    target_audience: str | None = None
    few_shot_examples: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
