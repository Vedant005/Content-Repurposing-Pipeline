from src.schemas.transcript import TranscriptChunk, TranscriptSegment


class TranscriptChunker:
    """Configurable chunker that groups timestamped segments into chunks based on token/character budgets,

    preserving video start, middle, and end, and retaining exact segment references.
    """

    def __init__(self, target_chars: int = 6000, overlap_segments: int = 2):
        self.target_chars = target_chars
        self.overlap_segments = overlap_segments

    def create_chunks(self, segments: list[TranscriptSegment]) -> list[TranscriptChunk]:
        if not segments:
            return []

        chunks: list[TranscriptChunk] = []
        n = len(segments)
        idx = 0
        chunk_idx = 0

        while idx < n:
            current_segments: list[TranscriptSegment] = []
            current_chars = 0
            start_i = idx

            while idx < n:
                seg = segments[idx]
                seg_text_len = len(seg.text)
                if current_chars + seg_text_len > self.target_chars and current_segments:
                    # Target budget reached for this chunk
                    break
                current_segments.append(seg)
                current_chars += seg_text_len + 1
                idx += 1

            # Format the chunk text with segment anchors
            formatted_lines = [
                f"[seg:{s.id}][{s.start_formatted}] {s.text}" for s in current_segments
            ]
            chunk_text = "\n".join(formatted_lines)

            chunks.append(
                TranscriptChunk(
                    chunk_index=chunk_idx,
                    start_segment_id=current_segments[0].id,
                    end_segment_id=current_segments[-1].id,
                    start_ms=current_segments[0].start_ms,
                    end_ms=current_segments[-1].end_ms,
                    text=chunk_text,
                    segment_ids=[s.id for s in current_segments],
                )
            )
            chunk_idx += 1

            if idx >= n:
                break

            # Apply overlap if we advanced past the start
            if self.overlap_segments > 0 and idx > start_i + self.overlap_segments:
                idx -= self.overlap_segments

        return chunks
