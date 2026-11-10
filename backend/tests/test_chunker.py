from src.schemas.transcript import TranscriptSegment
from src.services.chunker import TranscriptChunker


def test_chunker_empty_segments():
    chunker = TranscriptChunker(target_chars=1000)
    chunks = chunker.create_chunks([])
    assert chunks == []


def test_chunker_single_chunk():
    segments = [
        TranscriptSegment(id=0, start_ms=0, end_ms=2000, text="Welcome to the video."),
        TranscriptSegment(id=1, start_ms=2000, end_ms=4500, text="Today we discuss system design."),
    ]
    chunker = TranscriptChunker(target_chars=1000)
    chunks = chunker.create_chunks(segments)
    assert len(chunks) == 1
    assert chunks[0].chunk_index == 0
    assert chunks[0].start_segment_id == 0
    assert chunks[0].end_segment_id == 1
    assert "[seg:0][00:00] Welcome to the video." in chunks[0].text
    assert "[seg:1][00:02] Today we discuss system design." in chunks[0].text


def test_chunker_multiple_chunks_preserves_start_middle_end():
    # Create 30 segments each ~50 chars
    segments = [
        TranscriptSegment(
            id=i,
            start_ms=i * 5000,
            end_ms=(i + 1) * 5000,
            text=f"Segment number {i}: discussing important architecture principle and practice.",
        )
        for i in range(30)
    ]

    # Target 300 chars per chunk with 1 segment overlap
    chunker = TranscriptChunker(target_chars=300, overlap_segments=1)
    chunks = chunker.create_chunks(segments)

    assert len(chunks) > 1
    # First chunk contains segment 0
    assert chunks[0].start_segment_id == 0
    # Last chunk contains segment 29 (the very end of the video)
    assert chunks[-1].end_segment_id == 29
    # Every chunk has valid segment IDs
    for chunk in chunks:
        assert chunk.end_segment_id >= chunk.start_segment_id
        assert len(chunk.segment_ids) > 0
