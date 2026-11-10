from unittest.mock import AsyncMock, MagicMock

import pytest
from groq import AuthenticationError, RateLimitError

from src.schemas.content import TwitterThreadOutput
from src.services.llm_provider import (
    LLMAuthenticationError,
    LLMProvider,
    LLMStructuredOutputError,
)


@pytest.mark.asyncio
async def test_llm_provider_structured_output_success():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(
            message=MagicMock(
                content="""{
                    "thread": [
                        {"tweet_number": 1, "content": "First tweet", "hook_or_takeaway": "hook"},
                        {"tweet_number": 2, "content": "Second tweet", "hook_or_takeaway": "point"},
                        {"tweet_number": 3, "content": "Third tweet", "hook_or_takeaway": "cta"}
                    ]
                }"""
            )
        )
    ]
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    provider = LLMProvider(client=mock_client)
    result = await provider.generate_structured(
        system_instruction="Create thread",
        user_content="Transcript content",
        response_schema=TwitterThreadOutput,
        model="openai/gpt-oss-20b",
    )

    assert isinstance(result, TwitterThreadOutput)
    assert len(result.thread) == 3
    assert result.thread[0].content == "First tweet"


@pytest.mark.asyncio
async def test_llm_provider_structured_output_schema_failure():
    mock_client = MagicMock()
    # Invalid JSON output: missing required fields
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(
            message=MagicMock(
                content='{"thread": [{"tweet_number": 1, "content": "Only one tweet"}]}'
            )
        )
    ]
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    provider = LLMProvider(client=mock_client)
    with pytest.raises(LLMStructuredOutputError):
        await provider.generate_structured(
            system_instruction="Create thread",
            user_content="Content",
            response_schema=TwitterThreadOutput,
            max_retries=1,
        )


@pytest.mark.asyncio
async def test_llm_provider_authentication_error():
    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(
        side_effect=AuthenticationError(
            "Invalid API key", response=MagicMock(status_code=401), body={}
        )
    )

    provider = LLMProvider(client=mock_client)
    with pytest.raises(LLMAuthenticationError):
        await provider.generate_structured(
            system_instruction="Sys",
            user_content="User",
            response_schema=TwitterThreadOutput,
            max_retries=1,
        )


@pytest.mark.asyncio
async def test_llm_provider_rate_limit_retry():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="Generated text content"))]

    # First call fails with 429 RateLimitError, second succeeds
    mock_client.chat.completions.create = AsyncMock(
        side_effect=[
            RateLimitError("Rate limit exceeded", response=MagicMock(status_code=429), body={}),
            mock_response,
        ]
    )

    provider = LLMProvider(client=mock_client)
    text = await provider.generate_text(
        system_instruction="Sys",
        user_content="User",
        model="openai/gpt-oss-120b",
        max_retries=2,
    )
    assert text == "Generated text content"
    assert mock_client.chat.completions.create.call_count == 2
