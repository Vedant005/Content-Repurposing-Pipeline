import uuid
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from src.db.session import AsyncSessionLocal
from src.models.content import ContentAsset, ContentJob
from src.pipeline.graph import repurposing_pipeline
from src.pipeline.state import PipelineState
from src.pipeline.verification import DeterministicVerifier
from src.schemas.content import (
    BlogPostOutput,
    CanonicalVideoBrief,
    ChapterItem,
    ChaptersOutput,
    LinkedInPostOutput,
    TweetItem,
    TwitterThreadOutput,
)
from src.schemas.transcript import TranscriptSegment, VideoMetadata


def test_deterministic_verifier_quotes_grounding():
    transcript = "We noticed that building AI agents requires structured outputs and bounded loops. That is key."

    # Grounded quote
    grounded_text = 'The author mentioned: "building AI agents requires structured outputs and bounded loops" as essential.'
    hallucinations = DeterministicVerifier.verify_quotes_grounding(grounded_text, transcript)
    assert len(hallucinations) == 0

    # Hallucinated quote
    hallucinated_text = 'The speaker said: "Quantum computers will completely replace all databases next month" during the talk.'
    hallucinations = DeterministicVerifier.verify_quotes_grounding(hallucinated_text, transcript)
    assert len(hallucinations) == 1
    assert "Quantum computers" in hallucinations[0]["quote"]


def test_deterministic_verifier_blog_format():
    # Valid blog
    valid_blog = {
        "markdown_body": "# Introduction\n\n"
        + "This is a detailed analysis of content architectures and systems. " * 60
    }
    valid, errors = DeterministicVerifier.verify_blog_format(valid_blog)
    assert valid is True
    assert len(errors) == 0

    # Invalid blog (no headings and too short)
    invalid_blog = {"markdown_body": "Just a small sentence with no headings."}
    valid, errors = DeterministicVerifier.verify_blog_format(invalid_blog)
    assert valid is False
    assert any("headings" in e for e in errors)
    assert any("minimum" in e for e in errors)


def test_deterministic_verifier_twitter_and_chapters():
    # Tweet too long
    invalid_tweets = {
        "thread": [
            {"tweet_number": 1, "content": "A" * 300, "hook_or_takeaway": "hook"},
            {"tweet_number": 2, "content": "Short tweet", "hook_or_takeaway": "core"},
            {"tweet_number": 3, "content": "Another tweet", "hook_or_takeaway": "cta"},
        ]
    }
    valid, errors = DeterministicVerifier.verify_twitter_format(invalid_tweets)
    assert valid is False
    assert any("280 characters" in e for e in errors)

    # Chapters out of order and exceeding duration
    invalid_chapters = {
        "chapters": [
            {"timestamp_seconds": 120, "title": "Part 1"},
            {"timestamp_seconds": 60, "title": "Part 2 (Out of order)"},
            {"timestamp_seconds": 800, "title": "Part 3 (Exceeds duration 600s)"},
        ]
    }
    valid, errors = DeterministicVerifier.verify_chapters_format(
        invalid_chapters, duration_seconds=600
    )
    assert valid is False
    assert any("chronological order" in e for e in errors)
    assert any("exceeds video duration" in e for e in errors)


@pytest.mark.asyncio
async def test_langgraph_pipeline_full_execution():
    unique_id = uuid.uuid4().hex[:8]
    video_id = f"test_yt_{unique_id}"
    url = f"https://www.youtube.com/watch?v={video_id}"

    # Create test job in db
    async with AsyncSessionLocal() as db:
        job = ContentJob(
            session_id=f"sess_{unique_id}",
            youtube_url=url,
            status="queued",
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)
        job_id = job.id

    mock_segments = [
        TranscriptSegment(
            id=1,
            start_ms=0,
            end_ms=5000,
            text="Welcome to our deep dive on building resilient software architectures.",
        ),
        TranscriptSegment(
            id=2,
            start_ms=5000,
            end_ms=10000,
            text="The single most important principle is keeping background jobs idempotent and bounded.",
        ),
    ]
    mock_metadata = VideoMetadata(
        video_id=video_id,
        title="Resilient Architectures",
        duration_seconds=600,
    )

    mock_brief = CanonicalVideoBrief(
        title="Resilient Architectures",
        executive_summary="An exhaustive analysis of background job resiliency, idempotency, bounded retry loops, and Map-Reduce summarization for high scale applications.",
        core_arguments=[
            "Idempotency guards against duplicate processing",
            "Bounded loops prevent infinite resource exhaustion",
            "Structured outputs eliminate JSON parsing failures",
        ],
        quotable_moments=[
            {
                "quote": "The single most important principle is keeping background jobs idempotent and bounded.",
                "segment_id": 2,
                "timestamp_formatted": "00:05",
            }
        ],
        suggested_chapters=[
            {
                "timestamp_seconds": 0,
                "timestamp_formatted": "00:00",
                "title": "Introduction",
                "summary": "Welcome and overview",
                "source_segment_id": 1,
            },
            {
                "timestamp_seconds": 300,
                "timestamp_formatted": "05:00",
                "title": "Idempotency Deep Dive",
                "summary": "Core architectural principles",
                "source_segment_id": 2,
            },
        ],
    )

    mock_blog = BlogPostOutput(
        title="Building Resilient Architectures in 2026",
        meta_description="A guide to idempotent background processing and structured outputs in modern Python applications.",
        reading_time_minutes=4,
        markdown_body="# Resilient Systems\n\n"
        + "Here is an in-depth exploration of background processing and reliable systems. " * 50
        + '\n\nAs stated in the talk: "The single most important principle is keeping background jobs idempotent and bounded."\n\n## Conclusion\nAlways bind your loops.',
        key_takeaways=["Idempotency is king", "Bound all retries", "Use structured schemas"],
    )

    mock_twitter = TwitterThreadOutput(
        thread=[
            TweetItem(
                tweet_number=1,
                content="How do you build bulletproof AI workflows? Here is what we learned:",
                hook_or_takeaway="hook",
            ),
            TweetItem(
                tweet_number=2,
                content="1/ Background jobs must be completely idempotent. Never execute twice.",
                hook_or_takeaway="core point",
            ),
            TweetItem(
                tweet_number=3,
                content="2/ Bound your loops and verify LLM outputs with deterministic code.",
                hook_or_takeaway="core point",
            ),
            TweetItem(
                tweet_number=4,
                content="Found this useful? Follow for more architectural deep dives!",
                hook_or_takeaway="cta",
            ),
        ]
    )

    mock_linkedin = LinkedInPostOutput(
        hook_line="Most AI pipelines break because they rely on fragile error recovery.",
        body_paragraphs=[
            "In our latest architecture review, we examined background processing at scale.",
            "The key takeaway: always ensure idempotency and test deterministic boundary constraints.",
            "When you ground LLM generation in verifiable facts, hallucinations drop to zero.",
        ],
        call_to_action="How does your team handle idempotent background jobs?",
        hashtags=["#SoftwareEngineering", "#Architecture", "#Python"],
    )

    mock_chapters = ChaptersOutput(
        chapters=[
            ChapterItem(
                timestamp_seconds=0,
                timestamp_formatted="00:00",
                title="Intro",
                summary="Opening remarks",
                source_segment_id=1,
            ),
            ChapterItem(
                timestamp_seconds=300,
                timestamp_formatted="05:00",
                title="Core Principles",
                summary="Idempotency discussion",
                source_segment_id=2,
            ),
        ]
    )

    async def fake_generate_structured(system_instruction, user_content, response_schema, **kwargs):
        if response_schema == BlogPostOutput:
            return mock_blog
        elif response_schema == TwitterThreadOutput:
            return mock_twitter
        elif response_schema == LinkedInPostOutput:
            return mock_linkedin
        elif response_schema == ChaptersOutput:
            return mock_chapters
        elif response_schema == CanonicalVideoBrief:
            return mock_brief
        raise ValueError(f"Unexpected schema {response_schema}")

    with (
        patch(
            "src.pipeline.nodes.transcript_service.get_or_fetch_transcript",
            AsyncMock(return_value=(mock_segments, mock_metadata)),
        ),
        patch(
            "src.pipeline.nodes.transcript_service.get_cached_brief",
            AsyncMock(return_value=mock_brief),
        ),
        patch(
            "src.pipeline.nodes.llm.generate_structured",
            AsyncMock(side_effect=fake_generate_structured),
        ),
    ):
        initial_state: PipelineState = {
            "job_id": job_id,
            "video_id": video_id,
            "url": url,
            "session_id": f"sess_{unique_id}",
            "brand_profile_id": None,
            "attempt_counts": {},
            "assets": {},
        }

        final_state = await repurposing_pipeline.ainvoke(initial_state)

        assert final_state["final_status"] == "completed"
        assert "blog" in final_state["assets"]
        assert "twitter_thread" in final_state["assets"]
        assert "linkedin_post" in final_state["assets"]
        assert "chapters" in final_state["assets"]

        # Verify database persistence
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(ContentJob).where(ContentJob.id == job_id))
            persisted_job = result.scalar_one()
            assert persisted_job.status == "completed"
            assert persisted_job.blog_content is not None
            assert len(persisted_job.tweets) == 4
            assert persisted_job.linkedin_post is not None

            assets_res = await db.execute(select(ContentAsset).where(ContentAsset.job_id == job_id))
            persisted_assets = assets_res.scalars().all()
            assert len(persisted_assets) == 4
            asset_types = {a.asset_type for a in persisted_assets}
            assert asset_types == {"blog", "twitter_thread", "linkedin_post", "chapters"}
            assert all(a.status == "completed" for a in persisted_assets)


@pytest.mark.asyncio
async def test_langgraph_pipeline_targeted_retry_on_hallucination():
    unique_id = uuid.uuid4().hex[:8]
    video_id = f"test_retry_{unique_id}"
    url = f"https://www.youtube.com/watch?v={video_id}"

    async with AsyncSessionLocal() as db:
        job = ContentJob(
            session_id=f"sess_{unique_id}",
            youtube_url=url,
            status="queued",
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)
        job_id = job.id

    mock_segments = [
        TranscriptSegment(id=1, start_ms=0, end_ms=5000, text="Real transcript text here."),
    ]
    mock_metadata = VideoMetadata(video_id=video_id, title="Test Video", duration_seconds=300)
    mock_brief = CanonicalVideoBrief(
        title="Test Video",
        executive_summary="Summary text exceeding one hundred characters strictly required for schema validation purposes and verification in testing.",
        core_arguments=["Arg 1", "Arg 2", "Arg 3"],
        suggested_chapters=[
            {
                "timestamp_seconds": 0,
                "timestamp_formatted": "00:00",
                "title": "Intro",
                "summary": "Introduction and overview of the topic",
                "source_segment_id": 1,
            },
            {
                "timestamp_seconds": 150,
                "timestamp_formatted": "02:30",
                "title": "Discussion",
                "summary": "Detailed technical discussion section",
                "source_segment_id": 1,
            },
        ],
    )

    # Blog with hallucinated quote on attempt 1, clean blog on attempt 2
    blog_attempt = 0

    async def fake_generate_structured(system_instruction, user_content, response_schema, **kwargs):
        nonlocal blog_attempt
        if response_schema == BlogPostOutput:
            blog_attempt += 1
            if blog_attempt == 1:
                # Hallucinated quote
                return BlogPostOutput(
                    title="Attempt 1 Title",
                    meta_description="Attempt 1 meta description description description.",
                    reading_time_minutes=3,
                    markdown_body="# Section\n\n"
                    + "Body words here and detailed sentences. " * 60
                    + '\n\n"Completely fabricated quote not in the video transcript at all."\n\n',
                    key_takeaways=["T1", "T2", "T3"],
                )
            else:
                # Grounded quote
                return BlogPostOutput(
                    title="Attempt 2 Title",
                    meta_description="Attempt 2 meta description description description.",
                    reading_time_minutes=3,
                    markdown_body="# Section\n\n"
                    + "Body words here and detailed sentences. " * 60
                    + '\n\n"Real transcript text here."\n\n',
                    key_takeaways=["T1", "T2", "T3"],
                )
        elif response_schema == TwitterThreadOutput:
            return TwitterThreadOutput(
                thread=[
                    TweetItem(tweet_number=1, content="Tweet 1", hook_or_takeaway="hook"),
                    TweetItem(tweet_number=2, content="Tweet 2", hook_or_takeaway="core"),
                    TweetItem(tweet_number=3, content="Tweet 3", hook_or_takeaway="cta"),
                ]
            )
        elif response_schema == LinkedInPostOutput:
            return LinkedInPostOutput(
                hook_line="Hook line for LinkedIn post",
                body_paragraphs=["Paragraph 1", "Paragraph 2"],
                call_to_action="Call to action line",
                hashtags=["#Tag"],
            )
        elif response_schema == ChaptersOutput:
            return ChaptersOutput(
                chapters=[
                    ChapterItem(
                        timestamp_seconds=0,
                        timestamp_formatted="00:00",
                        title="Intro",
                        summary="Introductory section overview",
                        source_segment_id=1,
                    ),
                    ChapterItem(
                        timestamp_seconds=100,
                        timestamp_formatted="01:40",
                        title="Outro",
                        summary="Concluding remarks and review",
                        source_segment_id=1,
                    ),
                ]
            )
        raise ValueError(f"Unexpected schema {response_schema}")

    with (
        patch(
            "src.pipeline.nodes.transcript_service.get_or_fetch_transcript",
            AsyncMock(return_value=(mock_segments, mock_metadata)),
        ),
        patch(
            "src.pipeline.nodes.transcript_service.get_cached_brief",
            AsyncMock(return_value=mock_brief),
        ),
        patch(
            "src.pipeline.nodes.llm.generate_structured",
            AsyncMock(side_effect=fake_generate_structured),
        ),
    ):
        initial_state: PipelineState = {
            "job_id": job_id,
            "video_id": video_id,
            "url": url,
            "session_id": f"sess_{unique_id}",
            "brand_profile_id": None,
            "attempt_counts": {},
            "assets": {},
        }

        final_state = await repurposing_pipeline.ainvoke(initial_state)

        assert final_state["final_status"] == "completed"
        # Verify blog was retried exactly once
        assert blog_attempt == 2
        assert final_state["attempt_counts"].get("blog") == 1

        # Check DB record retry_count
        async with AsyncSessionLocal() as db:
            blog_asset_res = await db.execute(
                select(ContentAsset).where(
                    ContentAsset.job_id == job_id, ContentAsset.asset_type == "blog"
                )
            )
            blog_asset = blog_asset_res.scalar_one()
            assert blog_asset.retry_count == 1
            assert blog_asset.status == "completed"


@pytest.mark.asyncio
async def test_langgraph_pipeline_partial_success_when_retry_exhausted():
    unique_id = uuid.uuid4().hex[:8]
    video_id = f"test_exhaust_{unique_id}"
    url = f"https://www.youtube.com/watch?v={video_id}"

    async with AsyncSessionLocal() as db:
        job = ContentJob(
            session_id=f"sess_{unique_id}",
            youtube_url=url,
            status="queued",
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)
        job_id = job.id

    mock_segments = [
        TranscriptSegment(id=1, start_ms=0, end_ms=5000, text="Real transcript text here."),
    ]
    mock_metadata = VideoMetadata(
        video_id=video_id, title="Exhaust Test Video", duration_seconds=300
    )
    mock_brief = CanonicalVideoBrief(
        title="Exhaust Test Video",
        executive_summary="Summary text exceeding one hundred characters strictly required for schema validation purposes and verification in testing.",
        core_arguments=["Arg 1", "Arg 2", "Arg 3"],
        suggested_chapters=[
            {
                "timestamp_seconds": 0,
                "timestamp_formatted": "00:00",
                "title": "Intro",
                "summary": "Introduction and overview of the topic",
                "source_segment_id": 1,
            },
            {
                "timestamp_seconds": 150,
                "timestamp_formatted": "02:30",
                "title": "Discussion",
                "summary": "Detailed technical discussion section",
                "source_segment_id": 1,
            },
        ],
    )

    # Blog that always has invalid word count (too short for deterministic verifier)
    async def fake_generate_structured(system_instruction, user_content, response_schema, **kwargs):
        if response_schema == BlogPostOutput:
            return BlogPostOutput(
                title="Always Short Blog",
                meta_description="Meta description description description.",
                reading_time_minutes=1,
                markdown_body="# Short\n\n" + "This is a sentence repeated to satisfy pydantic minimum character length while failing word count check. " * 3,
                key_takeaways=["T1", "T2", "T3"],
            )
        elif response_schema == TwitterThreadOutput:
            return TwitterThreadOutput(
                thread=[
                    TweetItem(tweet_number=1, content="Tweet 1", hook_or_takeaway="hook"),
                    TweetItem(tweet_number=2, content="Tweet 2", hook_or_takeaway="core"),
                    TweetItem(tweet_number=3, content="Tweet 3", hook_or_takeaway="cta"),
                ]
            )
        elif response_schema == LinkedInPostOutput:
            return LinkedInPostOutput(
                hook_line="Hook line for LinkedIn post",
                body_paragraphs=["Paragraph 1", "Paragraph 2"],
                call_to_action="Call to action line",
                hashtags=["#Tag"],
            )
        elif response_schema == ChaptersOutput:
            return ChaptersOutput(
                chapters=[
                    ChapterItem(
                        timestamp_seconds=0,
                        timestamp_formatted="00:00",
                        title="Intro",
                        summary="Introductory section overview",
                        source_segment_id=1,
                    ),
                    ChapterItem(
                        timestamp_seconds=100,
                        timestamp_formatted="01:40",
                        title="Outro",
                        summary="Concluding remarks and review",
                        source_segment_id=1,
                    ),
                ]
            )
        raise ValueError(f"Unexpected schema {response_schema}")

    with (
        patch(
            "src.pipeline.nodes.transcript_service.get_or_fetch_transcript",
            AsyncMock(return_value=(mock_segments, mock_metadata)),
        ),
        patch(
            "src.pipeline.nodes.transcript_service.get_cached_brief",
            AsyncMock(return_value=mock_brief),
        ),
        patch(
            "src.pipeline.nodes.llm.generate_structured",
            AsyncMock(side_effect=fake_generate_structured),
        ),
    ):
        initial_state: PipelineState = {
            "job_id": job_id,
            "video_id": video_id,
            "url": url,
            "session_id": f"sess_{unique_id}",
            "brand_profile_id": None,
            "attempt_counts": {},
            "assets": {},
        }

        final_state = await repurposing_pipeline.ainvoke(initial_state)

        # Loop must bound out cleanly to partial_success
        assert final_state["final_status"] == "partial_success"
        assert final_state["attempt_counts"].get("blog") == 2

        # In DB, job is marked partial_success, blog is failed, but twitter/linkedin are completed
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(ContentJob).where(ContentJob.id == job_id))
            persisted_job = result.scalar_one()
            assert persisted_job.status == "partial_success"

            blog_asset_res = await db.execute(
                select(ContentAsset).where(
                    ContentAsset.job_id == job_id, ContentAsset.asset_type == "blog"
                )
            )
            blog_asset = blog_asset_res.scalar_one()
            assert blog_asset.status == "failed"
            assert blog_asset.retry_count == 2
