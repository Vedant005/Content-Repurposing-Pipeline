import difflib
import re
from typing import Any


class DeterministicVerifier:
    """Performs strict, non-LLM validation on generated content assets."""

    @staticmethod
    def extract_quotes(text: str) -> list[str]:
        """Extracts text within standard double quotes or smart quotes (>= 15 chars)."""
        pattern = r'["“]([^"”]{15,})["”]'
        return [q.strip() for q in re.findall(pattern, text)]

    @classmethod
    def verify_quotes_grounding(
        cls,
        text: str,
        full_transcript_text: str,
        threshold: float = 0.85,
    ) -> list[dict[str, Any]]:
        """Verifies that quotes in the generated text exist in the source transcript.

        Returns a list of hallucinated / ungrounded quotes.
        """
        quotes = cls.extract_quotes(text)
        if not quotes or not full_transcript_text:
            return []

        clean_source = re.sub(r"\s+", " ", full_transcript_text.lower())
        hallucinations = []

        for quote in quotes:
            clean_quote = re.sub(r"\s+", " ", quote.lower())
            # Exact substring match
            if clean_quote in clean_source:
                continue

            # Sliding window similarity match across transcript
            q_len = len(clean_quote)
            best_ratio = 0.0
            # Step in increments of 1/3 of quote length for efficiency
            step = max(1, q_len // 3)
            for i in range(0, max(1, len(clean_source) - q_len + 1), step):
                window = clean_source[i : i + q_len]
                ratio = difflib.SequenceMatcher(None, clean_quote, window).ratio()
                if ratio > best_ratio:
                    best_ratio = ratio
                if best_ratio >= threshold:
                    break

            if best_ratio < threshold:
                hallucinations.append(
                    {
                        "quote": quote,
                        "best_similarity": round(best_ratio, 3),
                        "reason": f"Quote similarity ({round(best_ratio, 3)}) is below grounding threshold ({threshold})",
                    }
                )

        return hallucinations

    @staticmethod
    def verify_blog_format(blog_data: dict[str, Any]) -> tuple[bool, list[str]]:
        """Validates blog post structure, headings, and minimum word count."""
        errors: list[str] = []
        body = blog_data.get("markdown_body", "")
        if not body:
            return False, ["Blog post markdown body is empty."]

        # Check for headings (# or ##)
        if not re.search(r"^#{1,3}\s+", body, re.MULTILINE):
            errors.append("Blog post lacks standard Markdown headings (# or ##).")

        words = len(re.findall(r"\b\w+\b", body))
        if words < 350:
            errors.append(f"Blog post length ({words} words) is below the minimum 350 words.")

        return len(errors) == 0, errors

    @staticmethod
    def verify_twitter_format(tweets_data: dict[str, Any]) -> tuple[bool, list[str]]:
        """Validates tweet thread length and individual tweet character limits."""
        errors: list[str] = []
        thread = tweets_data.get("thread", [])
        if not isinstance(thread, list) or len(thread) < 3:
            errors.append(
                f"Tweet thread has {len(thread) if isinstance(thread, list) else 0} tweets; minimum required is 3."
            )
            return False, errors

        if len(thread) > 12:
            errors.append(f"Tweet thread exceeds maximum 12 tweets (found {len(thread)}).")

        for i, tweet in enumerate(thread):
            content = tweet.get("content", "") if isinstance(tweet, dict) else str(tweet)
            if len(content) > 280:
                errors.append(
                    f"Tweet #{i + 1} exceeds 280 characters limit ({len(content)} chars)."
                )

        return len(errors) == 0, errors

    @staticmethod
    def verify_linkedin_format(linkedin_data: dict[str, Any]) -> tuple[bool, list[str]]:
        """Validates LinkedIn structure (hook line, paragraphs, call to action)."""
        errors: list[str] = []
        hook = linkedin_data.get("hook_line", "")
        body_paras = linkedin_data.get("body_paragraphs", [])
        cta = linkedin_data.get("call_to_action", "")

        if not hook or len(hook.strip()) < 10:
            errors.append("LinkedIn post lacks a compelling hook line.")

        if not body_paras or not isinstance(body_paras, list) or len(body_paras) < 2:
            errors.append("LinkedIn post requires at least 2 structured body paragraphs.")

        if not cta or len(cta.strip()) < 5:
            errors.append("LinkedIn post lacks a call to action.")

        return len(errors) == 0, errors

    @staticmethod
    def verify_chapters_format(
        chapters_data: dict[str, Any], duration_seconds: int
    ) -> tuple[bool, list[str]]:
        """Validates chapter timestamps are non-decreasing and bounded by video duration."""
        errors: list[str] = []
        chapters = chapters_data.get("chapters", [])
        if not isinstance(chapters, list) or not chapters:
            errors.append("No chapters provided.")
            return False, errors

        last_time = -1
        for i, ch in enumerate(chapters):
            t_sec = ch.get("timestamp_seconds", -1) if isinstance(ch, dict) else -1
            if t_sec < 0:
                errors.append(f"Chapter #{i + 1} has invalid negative timestamp.")
            elif duration_seconds > 0 and t_sec > duration_seconds + 30:
                errors.append(
                    f"Chapter #{i + 1} timestamp ({t_sec}s) exceeds video duration ({duration_seconds}s)."
                )
            elif t_sec < last_time:
                errors.append(
                    f"Chapter #{i + 1} timestamp ({t_sec}s) is out of chronological order (previous was {last_time}s)."
                )
            last_time = t_sec

        return len(errors) == 0, errors

    @staticmethod
    def evaluate_tone_compliance(text: str, tone_guidelines: str | None) -> tuple[int, list[str]]:
        """Evaluates textual content against specific brand tone constraints."""
        if not tone_guidelines or not text:
            return 9, []

        guidelines_lower = tone_guidelines.lower()
        violations: list[str] = []
        score = 10

        # 1. No emojis constraint
        if any(term in guidelines_lower for term in ["no emoji", "no emojis", "without emoji"]):
            emoji_matches = re.findall(r"[\U00010000-\U0010ffff]", text)
            if emoji_matches:
                score -= 4
                violations.append(
                    f"Content contains emojis ({''.join(set(emoji_matches))[:5]}) despite 'no emojis' guideline."
                )

        # 2. No jargon / buzzwords constraint
        if any(term in guidelines_lower for term in ["no jargon", "no buzzwords", "plain english"]):
            buzzwords = ["synergy", "paradigm shift", "leverage", "move the needle", "hyper-growth"]
            found = [
                b for b in buzzwords if re.search(r"\b" + re.escape(b) + r"\b", text, re.IGNORECASE)
            ]
            if found:
                score -= 3
                violations.append(f"Content contains forbidden buzzwords: {', '.join(found)}.")

        # 3. No excessive exclamation marks
        if any(
            term in guidelines_lower for term in ["understated", "no exclamation", "calm", "formal"]
        ):
            exclamations = len(re.findall(r"!", text))
            if exclamations > 2:
                score -= 3
                violations.append(
                    f"Content contains {exclamations} exclamation marks which violates calm/formal tone."
                )

        score = max(1, min(10, score))
        return score, violations

    @staticmethod
    def evaluate_tone_compliance(
        text: str, tone_guidelines: str | None
    ) -> tuple[int, list[str]]:
        """Evaluates textual content against specific brand tone constraints."""
        if not tone_guidelines or not text:
            return 9, []

        guidelines_lower = tone_guidelines.lower()
        violations: list[str] = []
        score = 10

        # 1. No emojis constraint
        if any(term in guidelines_lower for term in ["no emoji", "no emojis", "without emoji"]):
            emoji_matches = re.findall(r"[\U00010000-\U0010ffff]", text)
            if emoji_matches:
                score -= 4
                violations.append(
                    f"Content contains emojis ({''.join(set(emoji_matches))[:5]}) despite 'no emojis' guideline."
                )

        # 2. No jargon / buzzwords constraint
        if any(term in guidelines_lower for term in ["no jargon", "no buzzwords", "plain english"]):
            buzzwords = ["synergy", "paradigm shift", "leverage", "move the needle", "hyper-growth"]
            found = [
                b
                for b in buzzwords
                if re.search(r"\b" + re.escape(b) + r"\b", text, re.IGNORECASE)
            ]
            if found:
                score -= 3
                violations.append(f"Content contains forbidden buzzwords: {', '.join(found)}.")

        # 3. No excessive exclamation marks
        if any(
            term in guidelines_lower for term in ["understated", "no exclamation", "calm", "formal"]
        ):
            exclamations = len(re.findall(r"!", text))
            if exclamations > 2:
                score -= 3
                violations.append(
                    f"Content contains {exclamations} exclamation marks which violates calm/formal tone."
                )

        score = max(1, min(10, score))
        return score, violations
