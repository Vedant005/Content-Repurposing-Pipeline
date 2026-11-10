from langgraph.graph import END, START, StateGraph

from src.pipeline.nodes import (
    node_ai_critique,
    node_deterministic_verification,
    node_generate_blog,
    node_generate_chapters,
    node_generate_linkedin,
    node_generate_twitter,
    node_ingest_and_normalize,
    node_load_brand_context,
    node_map_reduce_brief,
    node_persist_state,
    node_targeted_retry,
    route_after_critique,
)
from src.pipeline.state import PipelineState


def build_repurposing_graph() -> StateGraph:
    """Builds and compiles the production LangGraph workflow for YouTube Content Repurposing."""
    builder = StateGraph(PipelineState)

    # 1. Register Nodes
    builder.add_node("ingest_and_normalize", node_ingest_and_normalize)
    builder.add_node("map_reduce_brief", node_map_reduce_brief)
    builder.add_node("load_brand_context", node_load_brand_context)

    # Parallel Generation Nodes
    builder.add_node("generate_blog", node_generate_blog)
    builder.add_node("generate_twitter", node_generate_twitter)
    builder.add_node("generate_linkedin", node_generate_linkedin)
    builder.add_node("generate_chapters", node_generate_chapters)

    # Verification & Quality Nodes
    builder.add_node("deterministic_verification", node_deterministic_verification)
    builder.add_node("ai_critique", node_ai_critique)
    builder.add_node("targeted_retry", node_targeted_retry)
    builder.add_node("persist_state", node_persist_state)

    # 2. Sequential linear ingestion
    builder.add_edge(START, "ingest_and_normalize")
    builder.add_edge("ingest_and_normalize", "map_reduce_brief")
    builder.add_edge("map_reduce_brief", "load_brand_context")

    # 3. Parallel Fan-Out
    builder.add_edge("load_brand_context", "generate_blog")
    builder.add_edge("load_brand_context", "generate_twitter")
    builder.add_edge("load_brand_context", "generate_linkedin")
    builder.add_edge("load_brand_context", "generate_chapters")

    # 4. Fan-In to Deterministic Verification
    builder.add_edge("generate_blog", "deterministic_verification")
    builder.add_edge("generate_twitter", "deterministic_verification")
    builder.add_edge("generate_linkedin", "deterministic_verification")
    builder.add_edge("generate_chapters", "deterministic_verification")

    # 5. Critique & Conditional Targeted Retry
    builder.add_edge("deterministic_verification", "ai_critique")
    builder.add_conditional_edges(
        "ai_critique",
        route_after_critique,
        {
            "targeted_retry": "targeted_retry",
            "persist_state": "persist_state",
        },
    )

    # 6. Retry loop back to verification
    builder.add_edge("targeted_retry", "deterministic_verification")

    # 7. Final persistence to END
    builder.add_edge("persist_state", END)

    return builder.compile()


repurposing_pipeline = build_repurposing_graph()
