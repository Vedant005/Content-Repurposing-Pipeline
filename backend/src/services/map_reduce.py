import asyncio
import logging

from src.core.config import settings
from src.schemas.content import CanonicalVideoBrief
from src.schemas.transcript import ChunkSummary, TranscriptChunk, VideoMetadata
from src.services.llm_provider import llm_provider

logger = logging.getLogger("repurpose_api.map_reduce")


class MapReduceSummarizer:
    """Hierarchical Map-Reduce summarization engine that processes timestamped transcript chunks

    in parallel (Map stage) and synthesizes them into an authoritative Canonical Video Brief (Reduce stage).
    """

    def __init__(self, concurrency_limit: int = 3):
        self.semaphore = asyncio.Semaphore(concurrency_limit)
        self.fast_model = settings.GROQ_FAST_MODEL
        self.deep_model = settings.GROQ_DEEP_MODEL

    async def _summarize_chunk(self, chunk: TranscriptChunk) -> ChunkSummary:
        async with self.semaphore:
            prompt = (
                f"Transcript Chunk #{chunk.chunk_index + 1} ({chunk.time_range})\n"
                f"Segments: {chunk.start_segment_id} to {chunk.end_segment_id}\n\n"
                f"<chunk_transcript>\n{chunk.text}\n</chunk_transcript>"
            )

            system_instruction = (
                "You are an expert video content analyst.\n"
                "Extract the core information from this timestamped chunk of transcript:\n"
                "1. Key analytical points (1 to 5 points).\n"
                "2. 1 to 3 quotable moments, citing the exact [seg:ID] segment ID and timestamp.\n"
                "Never invent quotes or segment IDs. Rely strictly on the text provided."
            )

            logger.info(
                "Starting Map summary for chunk %d (%s)", chunk.chunk_index, chunk.time_range
            )
            summary = await llm_provider.generate_structured(
                system_instruction=system_instruction,
                user_content=prompt,
                response_schema=ChunkSummary,
                model=self.fast_model,
                temperature=0.3,
            )
            # Ensure chunk_index and time_range match
            summary.chunk_index = chunk.chunk_index
            summary.time_range = chunk.time_range
            return summary

    async def map_chunks(self, chunks: list[TranscriptChunk]) -> list[ChunkSummary]:
        tasks = [self._summarize_chunk(chunk) for chunk in chunks]
        results = await asyncio.gather(*tasks)
        return list(results)

    async def reduce_summaries(
        self, summaries: list[ChunkSummary], metadata: VideoMetadata
    ) -> CanonicalVideoBrief:
        summaries_formatted = []
        for s in sorted(summaries, key=lambda x: x.chunk_index):
            quotes_str = ", ".join(
                [
                    f'"{q.quote}" (seg:{q.segment_id} @ {q.timestamp_formatted})'
                    for q in s.key_quotes
                ]
            )
            summaries_formatted.append(
                f"### Section {s.chunk_index + 1} ({s.time_range})\n"
                f"Key Points:\n- " + "\n- ".join(s.key_points) + "\n"
                f"Quotes: {quotes_str or 'None'}\n"
            )

        combined_input = (
            f"Video Title: {metadata.title or 'Unknown'}\n"
            f"Duration: {metadata.duration_seconds or 'Unknown'} seconds\n\n"
            f"Chronological Section Summaries:\n\n" + "\n".join(summaries_formatted)
        )

        system_instruction = (
            "You are a master content strategist.\n"
            "Synthesize the provided sequential section summaries into a single comprehensive Canonical Video Brief.\n"
            "Guidelines:\n"
            "- 'title': An engaging, SEO-friendly title representing the full content.\n"
            "- 'executive_summary': A 150-400 word cohesive narrative capturing the start, middle, and conclusion of the video.\n"
            "- 'core_arguments': 4 to 8 distinct takeaways or central thesis points.\n"
            "- 'quotable_moments': 3 to 6 high-impact verbatim quotes from the sections with exact segment IDs and timestamps.\n"
            "- 'suggested_chapters': 3 to 8 logical chapter divisions with titles and timestamps.\n"
            "Do not invent segment IDs or timestamps; preserve them from the input summaries."
        )

        logger.info(
            "Starting Reduce synthesis for CanonicalVideoBrief across %d sections", len(summaries)
        )
        brief = await llm_provider.generate_structured(
            system_instruction=system_instruction,
            user_content=combined_input,
            response_schema=CanonicalVideoBrief,
            model=self.deep_model,
            temperature=0.4,
        )
        return brief

    async def run(
        self, chunks: list[TranscriptChunk], metadata: VideoMetadata
    ) -> tuple[list[ChunkSummary], CanonicalVideoBrief]:
        summaries = await self.map_chunks(chunks)
        brief = await self.reduce_summaries(summaries, metadata)
        return summaries, brief


map_reduce_summarizer = MapReduceSummarizer()
