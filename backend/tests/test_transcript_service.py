from unittest.mock import MagicMock

import pytest

from src.services.transcript_service import (
    TranscriptService,
    TranscriptUnavailableError,
    VideoTooLongError,
)


def test_normalize_content_with_supadata_chunks():
    service = TranscriptService(client=MagicMock())
    raw_chunks = [
        {"text": "Hello world", "offset": 0, "duration": 2500},
        {"text": "Welcome to the presentation", "offset": 2500, "duration": 3000},
    ]
    segments = service._normalize_content(raw_chunks)
    assert len(segments) == 2
    assert segments[0].id == 0
    assert segments[0].text == "Hello world"
    assert segments[0].start_ms == 0
    assert segments[0].end_ms == 2500
    assert segments[0].start_formatted == "00:00"

    assert segments[1].id == 1
    assert segments[1].start_ms == 2500
    assert segments[1].end_ms == 5500
    assert segments[1].start_formatted == "00:02"


def test_normalize_content_with_plain_text():
    service = TranscriptService(client=MagicMock())
    text = "First sentence here. Second sentence starts now. And the third concludes it."
    segments = service._normalize_content(text)
    assert len(segments) == 3
    assert segments[0].text == "First sentence here."
    assert segments[1].text == "Second sentence starts now."
    assert segments[2].text == "And the third concludes it."
    assert segments[0].start_ms == 0
    assert segments[2].start_ms > segments[0].start_ms


def test_normalize_content_empty_raises_error():
    service = TranscriptService(client=MagicMock())
    with pytest.raises(TranscriptUnavailableError):
        service._normalize_content([])

    with pytest.raises(TranscriptUnavailableError):
        service._normalize_content("")


def test_poll_batch_job_sync_completed():
    mock_client = MagicMock()
    mock_batch_results = MagicMock()
    mock_batch_results.status = "completed"
    mock_batch_results.results = [
        MagicMock(content=[{"text": "Async transcript text", "offset": 0, "duration": 1500}])
    ]
    mock_client.youtube.batch.get_batch_results.return_value = mock_batch_results

    service = TranscriptService(client=mock_client)
    # Monkeypatch time.sleep to avoid waiting in tests
    import time

    orig_sleep = time.sleep
    time.sleep = lambda s: None
    try:
        segments = service._poll_batch_job_sync("job_123", max_wait_seconds=10)
        assert len(segments) == 1
        assert segments[0].text == "Async transcript text"
    finally:
        time.sleep = orig_sleep


def test_video_too_long_error():
    err = VideoTooLongError(duration_seconds=185 * 60, limit_minutes=180)
    assert "185m 0s" in str(err)
    assert "180-minute" in str(err)
