import pytest
from pydantic import ValidationError

from src.schemas.content import (
    BlogPostOutput,
    ChapterItem,
    ChaptersOutput,
    JobStatusResponse,
    LinkedInPostOutput,
    TweetItem,
    TwitterThreadOutput,
    VideoRequest,
)


def test_video_request_valid_urls():
    req1 = VideoRequest(url="https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert "youtube.com" in str(req1.url)

    req2 = VideoRequest(url="https://youtu.be/dQw4w9WgXcQ")
    assert "youtu.be" in str(req2.url)


def test_video_request_invalid_url():
    with pytest.raises(ValidationError):
        VideoRequest(url="https://vimeo.com/12345678")

    with pytest.raises(ValidationError):
        VideoRequest(url="https://example.com/not-youtube")


def test_tweet_item_and_thread_validation():
    valid_thread = TwitterThreadOutput(
        thread=[
            TweetItem(tweet_number=1, content="Hook tweet #1", hook_or_takeaway="hook"),
            TweetItem(tweet_number=2, content="Insight tweet #2", hook_or_takeaway="insight"),
            TweetItem(tweet_number=3, content="Call to action tweet #3", hook_or_takeaway="cta"),
        ]
    )
    assert len(valid_thread.thread) == 3

    # Thread with too few tweets (< 3) should fail
    with pytest.raises(ValidationError):
        TwitterThreadOutput(
            thread=[TweetItem(tweet_number=1, content="Only tweet", hook_or_takeaway="hook")]
        )

    # Tweet exceeding 280 characters should fail
    with pytest.raises(ValidationError):
        TweetItem(
            tweet_number=1,
            content="A" * 281,
            hook_or_takeaway="too long",
        )


def test_blog_post_output_validation():
    valid_blog = BlogPostOutput(
        title="10 Key Lessons from Distributed Systems",
        meta_description="A comprehensive guide to building resilient distributed software architectures.",
        reading_time_minutes=5,
        markdown_body="# Introduction\n\n" + ("This is detailed body text about systems. " * 20),
        key_takeaways=["Lesson 1", "Lesson 2", "Lesson 3"],
    )
    assert valid_blog.reading_time_minutes == 5
    assert len(valid_blog.key_takeaways) == 3

    # Blog with too short markdown body should fail
    with pytest.raises(ValidationError):
        BlogPostOutput(
            title="Short Title",
            meta_description="Too short description.",
            reading_time_minutes=1,
            markdown_body="Too short body",
            key_takeaways=["One", "Two", "Three"],
        )


def test_linkedin_post_output_validation():
    valid_linkedin = LinkedInPostOutput(
        hook_line="Most software teams get asynchronous background jobs wrong.",
        body_paragraphs=[
            "Here is why in-process queues fail during deploys.",
            "Instead, use persistent queues like Redis + ARQ.",
        ],
        call_to_action="How do you handle background workers in production? Let me know below.",
        hashtags=["Python", "SystemDesign", "FastAPI"],
    )
    assert valid_linkedin.hook_line.startswith("Most software")
    assert len(valid_linkedin.body_paragraphs) == 2


def test_chapters_output_validation():
    chapters = ChaptersOutput(
        chapters=[
            ChapterItem(
                timestamp_seconds=0,
                timestamp_formatted="00:00",
                title="Introduction & Overview",
                summary="The speaker outlines the agenda and main themes of the talk.",
                source_segment_id=0,
            ),
            ChapterItem(
                timestamp_seconds=185,
                timestamp_formatted="03:05",
                title="Deep Dive into Architecture",
                summary="Detailed explanation of the multi-agent orchestration pattern.",
                source_segment_id=12,
            ),
        ]
    )
    assert len(chapters.chapters) == 2
    assert chapters.chapters[1].timestamp_seconds == 185


def test_job_status_response_backward_compatibility():
    # Legacy flat format
    legacy_resp = JobStatusResponse(
        id=1,
        status="completed",
        blog_content="# Blog title\n\nContent here...",
        tweets=["Tweet 1", "Tweet 2"],
        linkedin_post="LinkedIn text",
    )
    assert legacy_resp.blog_content is not None
    assert isinstance(legacy_resp.tweets, list)
    assert legacy_resp.assets is None

    # Relational format with rich assets
    relational_resp = JobStatusResponse(
        id=2,
        status="completed",
        assets=[
            {
                "id": 101,
                "asset_type": "blog",
                "status": "completed",
                "content": {"markdown_body": "# Rich Blog"},
                "retry_count": 0,
                "created_at": "2026-11-10T12:00:00Z",
            }
        ],
    )
    assert relational_resp.assets is not None
    assert relational_resp.assets[0].asset_type == "blog"
