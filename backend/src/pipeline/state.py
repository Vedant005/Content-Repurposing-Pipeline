from typing import Annotated, Any, TypedDict


def merge_dicts(existing: dict[str, Any] | None, new_val: dict[str, Any] | None) -> dict[str, Any]:
    merged = dict(existing or {})
    if new_val:
        merged.update(new_val)
    return merged


class PipelineState(TypedDict, total=False):
    job_id: int
    video_id: str
    url: str
    session_id: str
    brand_profile_id: int | None
    brand_profile: dict[str, Any] | None
    raw_segments: list[dict[str, Any]]
    duration_seconds: int
    video_title: str
    chunks: list[dict[str, Any]]
    chunk_summaries: list[dict[str, Any]]
    canonical_brief: dict[str, Any] | None
    assets: Annotated[dict[str, Any], merge_dicts]
    validation_results: Annotated[dict[str, dict[str, Any]], merge_dicts]
    critique_results: Annotated[dict[str, dict[str, Any]], merge_dicts]
    retry_targets: list[str]
    attempt_counts: Annotated[dict[str, int], merge_dicts]
    error_message: str | None
    final_status: str
