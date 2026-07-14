from app.schemas.search import ChatMessage, SearchResultItem

INSUFFICIENT_CONTEXT_MESSAGE = "I couldn't find enough information."

# Bounds prompt size/cost regardless of how much history the client sends.
MAX_HISTORY_MESSAGES = 12


def build_context(results: list[SearchResultItem]) -> tuple[str, list[str]]:
    """Builds the excerpt block fed to the model, and separately collects the
    source filenames straight from retrieval. Sources are never taken from the
    model's own output, so citations can't be hallucinated."""
    blocks: list[str] = []
    sources: list[str] = []
    for item in results:
        if not item.chunk_text:
            continue
        blocks.append(f"[Source: {item.filename}]\n{item.chunk_text}")
        if item.filename not in sources:
            sources.append(item.filename)
    return "\n\n".join(blocks), sources


def history_to_messages(history: list[ChatMessage] | None) -> list[dict]:
    """Converts prior conversation turns into chat-completion messages, capped
    to the most recent MAX_HISTORY_MESSAGES regardless of what the client sent."""
    if not history:
        return []
    trimmed = history[-MAX_HISTORY_MESSAGES:]
    return [{"role": message.role, "content": message.content} for message in trimmed]


def confidence_from_scores(results: list[SearchResultItem]) -> float:
    """Deterministic confidence derived from retrieval similarity scores, used
    where an LLM-reported confidence isn't available (e.g. streaming)."""
    scores = [item.score for item in results if item.score is not None]
    if not scores:
        return 0.0
    return max(0.0, min(1.0, sum(scores) / len(scores)))
