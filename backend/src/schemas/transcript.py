from pydantic import BaseModel, ConfigDict, Field


class TranscriptSegment(BaseModel):
    id: int = Field(..., ge=0, description="Sequential 0-based segment index")
    start_ms: int = Field(..., ge=0, description="Start timestamp in milliseconds")
    end_ms: int = Field(..., ge=0, description="End timestamp in milliseconds")
    text: str = Field(..., description="Verbatim spoken transcript text")

    @property
    def start_formatted(self) -> str:
        total_seconds = self.start_ms // 1000
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return f"{minutes:02d}:{seconds:02d}"

    @property
    def end_formatted(self) -> str:
        total_seconds = self.end_ms // 1000
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return f"{minutes:02d}:{seconds:02d}"

    model_config = ConfigDict(from_attributes=True)


class VideoMetadata(BaseModel):
    video_id: str
    title: str | None = None
    duration_seconds: int | None = None


class TranscriptChunk(BaseModel):
    chunk_index: int = Field(..., ge=0)
    start_segment_id: int
    end_segment_id: int
    start_ms: int
    end_ms: int
    text: str
    segment_ids: list[int]

    @property
    def time_range(self) -> str:
        def fmt(ms: int) -> str:
            s = ms // 1000
            return f"{s // 60:02d}:{s % 60:02d}"

        return f"{fmt(self.start_ms)} - {fmt(self.end_ms)}"


class ChunkQuote(BaseModel):
    quote: str
    segment_id: int
    timestamp_formatted: str


class ChunkSummary(BaseModel):
    chunk_index: int
    time_range: str
    key_points: list[str] = Field(..., min_length=1, max_length=5)
    key_quotes: list[ChunkQuote] = Field(default_factory=list)
