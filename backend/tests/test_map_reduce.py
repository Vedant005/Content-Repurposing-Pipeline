from unittest.mock import AsyncMock, patch

import pytest

from src.schemas.content import CanonicalVideoBrief
from src.schemas.transcript import (
    ChunkQuote,
    ChunkSummary,
    TranscriptChunk,
    VideoMetadata,
)
from src.services.map_reduce import MapReduceSummarizer


@pytest.mark.asyncio
async def test_map_chunks_success():
    chunk = TranscriptChunk(
        chunk_index=0,
        start_segment_id=0,
        end_segment_id=1,
        start_ms=0,
        end_ms=5000,
        text="[seg:0][00:00] First segment\n[seg:1][00:02] Second segment",
        segment_ids=[0, 1],
    )

    mock_summary = ChunkSummary(
        chunk_index=0,
        time_range="00:00 - 00:05",
        key_points=["Point 1", "Point 2"],
        key_quotes=[ChunkQuote(quote="First segment", segment_id=0, timestamp_formatted="00:00")],
    )

    summarizer = MapReduceSummarizer()
    with patch(
        "src.services.map_reduce.llm_provider.generate_structured",
        new=AsyncMock(return_value=mock_summary),
    ):
        summaries = await summarizer.map_chunks([chunk])
        assert len(summaries) == 1
        assert summaries[0].chunk_index == 0
        assert summaries[0].key_points == ["Point 1", "Point 2"]
        assert summaries[0].key_quotes[0].segment_id == 0


@pytest.mark.asyncio
async def test_reduce_summaries_success():
    summary = ChunkSummary(
        chunk_index=0,
        time_range="00:00 - 05:00",
        key_points=["Central theme of microservices"],
        key_quotes=[
            ChunkQuote(quote="Design for failure", segment_id=2, timestamp_formatted="01:15")
        ],
    )

    mock_brief = CanonicalVideoBrief(
        title="Microservices Architecture Masterclass",
        executive_summary=(
            "A comprehensive overview of building resilient microservices architectures. "
            "We examine decoupling domains, handling network failures, and designing reliable asynchronous messaging systems."
        ),
        core_arguments=["Decoupling domains", "Circuit breakers", "Async messaging"],
        quotable_moments=[
            {"quote": "Design for failure", "segment_id": 2, "timestamp_formatted": "01:15"}
        ],
        suggested_chapters=[
            {"title": "Introduction", "timestamp_seconds": 0, "summary": "Setting the stage."}
        ],
    )

    summarizer = MapReduceSummarizer()
    with patch(
        "src.services.map_reduce.llm_provider.generate_structured",
        new=AsyncMock(return_value=mock_brief),
    ):
        metadata = VideoMetadata(video_id="xyz123", title="Masterclass", duration_seconds=300)
        brief = await summarizer.reduce_summaries([summary], metadata)

        assert isinstance(brief, CanonicalVideoBrief)
        assert brief.title == "Microservices Architecture Masterclass"
        assert len(brief.core_arguments) == 3
        assert brief.quotable_moments[0]["segment_id"] == 2
