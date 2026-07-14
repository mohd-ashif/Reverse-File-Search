import json


def sse_event(event: dict) -> str:
    """Frames a dict as a single Server-Sent Events `data:` line."""
    return f"data: {json.dumps(event)}\n\n"
