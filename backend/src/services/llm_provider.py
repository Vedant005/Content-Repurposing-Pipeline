import asyncio
import json
import logging
import random
from typing import TypeVar

from groq import APIStatusError, AsyncGroq, AuthenticationError, RateLimitError
from pydantic import BaseModel, ValidationError

from src.core.config import settings

logger = logging.getLogger("repurpose_api.llm")

T = TypeVar("T", bound=BaseModel)


class LLMProviderError(Exception):
    """Base exception for LLM provider errors."""

    pass


class LLMAuthenticationError(LLMProviderError):
    """Raised when API credentials are rejected."""

    pass


class LLMRateLimitError(LLMProviderError):
    """Raised when rate limits are exceeded."""

    def __init__(self, message: str, retry_after: float | None = None):
        super().__init__(message)
        self.retry_after = retry_after


class LLMStructuredOutputError(LLMProviderError):
    """Raised when LLM output violates schema or fails JSON parsing."""

    def __init__(
        self, message: str, raw_output: str | None = None, validation_errors: dict | None = None
    ):
        super().__init__(message)
        self.raw_output = raw_output
        self.validation_errors = validation_errors


class LLMTimeoutError(LLMProviderError):
    """Raised when LLM call exceeds duration budget."""

    pass


class LLMProvider:
    """Production Groq LLM provider abstraction with native structured outputs,

    typed errors, and bounded retries with exponential backoff.
    """

    def __init__(self, client: AsyncGroq | None = None):
        self.client = client or AsyncGroq(api_key=settings.GROQ_API_KEY)
        self.deep_model = settings.GROQ_DEEP_MODEL
        self.fast_model = settings.GROQ_FAST_MODEL
        self.fallback_model = settings.GROQ_FALLBACK_MODEL

    async def generate_structured(
        self,
        system_instruction: str,
        user_content: str,
        response_schema: type[T],
        model: str | None = None,
        temperature: float = 0.5,
        max_retries: int = 3,
        timeout: float = 60.0,
    ) -> T:
        """Executes a completion requiring strict JSON structured output matching response_schema."""
        target_model = model or self.fast_model
        schema_prompt = (
            f"{system_instruction}\n\n"
            f"IMPORTANT: Output MUST be a valid JSON object strictly matching this schema:\n"
            f"{json.dumps(response_schema.model_json_schema(), indent=2)}\n"
            f"Do not include code markdown fences (like ```json), explanations, or preamble."
        )

        last_error: Exception | None = None
        for attempt in range(max_retries):
            try:
                response = await asyncio.wait_for(
                    self.client.chat.completions.create(
                        model=target_model,
                        messages=[
                            {"role": "system", "content": schema_prompt},
                            {"role": "user", "content": user_content},
                        ],
                        response_format={"type": "json_object"},
                        temperature=temperature,
                    ),
                    timeout=timeout,
                )

                raw_content = response.choices[0].message.content or "{}"
                try:
                    data = json.loads(raw_content)
                    return response_schema.model_validate(data)
                except (json.JSONDecodeError, ValidationError) as parse_err:
                    logger.warning(
                        "Schema validation failed on attempt %d: %s",
                        attempt + 1,
                        parse_err,
                        extra={"model": target_model, "raw": raw_content[:300]},
                    )
                    last_error = LLMStructuredOutputError(
                        f"Output failed schema validation: {parse_err}",
                        raw_output=raw_content,
                    )

            except AuthenticationError as auth_err:
                logger.error("Groq authentication failure: %s", auth_err)
                raise LLMAuthenticationError(f"Invalid Groq credentials: {auth_err}") from auth_err

            except RateLimitError as rl_err:
                retry_after = getattr(rl_err, "retry_after", None)
                wait_time = (
                    float(retry_after) if retry_after else (2**attempt + random.uniform(0.5, 1.5))
                )
                logger.warning(
                    "Rate limit hit on %s, backing off %.1fs (attempt %d/%d)",
                    target_model,
                    wait_time,
                    attempt + 1,
                    max_retries,
                )
                last_error = LLMRateLimitError(str(rl_err), retry_after=wait_time)
                if attempt < max_retries - 1:
                    await asyncio.sleep(wait_time)

            except TimeoutError:
                logger.warning(
                    "LLM call timed out after %.1fs (attempt %d/%d)",
                    timeout,
                    attempt + 1,
                    max_retries,
                )
                last_error = LLMTimeoutError(f"Groq API timed out after {timeout}s")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2**attempt)

            except APIStatusError as api_err:
                status_code = getattr(api_err, "status_code", None)
                logger.error("Groq API status error: status=%s, err=%s", status_code, api_err)
                last_error = LLMProviderError(f"Groq API error ({status_code}): {api_err}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2**attempt + random.uniform(0.1, 0.5))

            except Exception as unk_err:
                logger.error("Unexpected error in LLM call: %s", unk_err)
                last_error = LLMProviderError(f"Unexpected LLM error: {unk_err}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1.0)

        raise last_error or LLMProviderError(
            "Exhausted retries without producing structured output."
        )

    async def generate_text(
        self,
        system_instruction: str,
        user_content: str,
        model: str | None = None,
        temperature: float = 0.7,
        max_retries: int = 3,
        timeout: float = 60.0,
    ) -> str:
        """Executes a completion returning raw text (e.g. for markdown articles)."""
        target_model = model or self.deep_model
        last_error: Exception | None = None

        for attempt in range(max_retries):
            try:
                response = await asyncio.wait_for(
                    self.client.chat.completions.create(
                        model=target_model,
                        messages=[
                            {"role": "system", "content": system_instruction},
                            {"role": "user", "content": user_content},
                        ],
                        temperature=temperature,
                    ),
                    timeout=timeout,
                )
                text = response.choices[0].message.content or ""
                return text.strip()

            except RateLimitError as rl_err:
                wait_time = 2**attempt + random.uniform(0.5, 1.5)
                logger.warning("Rate limit hit on %s, retrying in %.1fs", target_model, wait_time)
                last_error = LLMRateLimitError(str(rl_err), retry_after=wait_time)
                if attempt < max_retries - 1:
                    await asyncio.sleep(wait_time)

            except Exception as e:
                logger.error("Groq text generation error: %s", e)
                last_error = LLMProviderError(str(e))
                if attempt < max_retries - 1:
                    await asyncio.sleep(2**attempt)

        raise last_error or LLMProviderError("Exhausted retries in text generation.")


llm_provider = LLMProvider()
