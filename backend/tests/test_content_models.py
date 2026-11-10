from src.models.content import ContentAsset, ContentJob


def test_content_job_effective_blog_fallback():
    # 1. Direct column takes precedence
    job1 = ContentJob(blog_content="Direct column blog")
    assert job1.get_effective_blog() == "Direct column blog"

    # 2. Falls back to relational ContentAsset
    job2 = ContentJob(blog_content=None)
    asset = ContentAsset(
        asset_type="blog",
        status="completed",
        content={"markdown_body": "# Relational Markdown Body"},
    )
    job2.assets.append(asset)
    assert job2.get_effective_blog() == "# Relational Markdown Body"


def test_content_job_effective_tweets_fallback():
    # 1. Direct column takes precedence
    job1 = ContentJob(tweets=["T1", "T2"])
    assert job1.get_effective_tweets() == ["T1", "T2"]

    # 2. Falls back to relational ContentAsset structured thread
    job2 = ContentJob(tweets=None)
    asset = ContentAsset(
        asset_type="twitter_thread",
        status="completed",
        content={"thread": [{"content": "Tweet 1"}, {"content": "Tweet 2"}]},
    )
    job2.assets.append(asset)
    assert job2.get_effective_tweets() == ["Tweet 1", "Tweet 2"]


def test_content_job_effective_linkedin_fallback():
    # 1. Direct column
    job1 = ContentJob(linkedin_post="Direct LinkedIn post")
    assert job1.get_effective_linkedin() == "Direct LinkedIn post"

    # 2. Falls back to structured dict in ContentAsset
    job2 = ContentJob(linkedin_post=None)
    asset = ContentAsset(
        asset_type="linkedin_post",
        status="completed",
        content={
            "hook_line": "The future of AI engineering.",
            "body_paragraphs": ["Paragraph 1", "Paragraph 2"],
            "call_to_action": "Share your thoughts.",
            "hashtags": ["AI", "Tech"],
        },
    )
    job2.assets.append(asset)
    effective = job2.get_effective_linkedin()
    assert "The future of AI engineering." in effective
    assert "Paragraph 1" in effective
    assert "#AI #Tech" in effective
