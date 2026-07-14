import json
from collections.abc import Iterator
from functools import lru_cache

import httpx

from app.core.config import settings


class GroqClient:
    """Thin transport wrapper around Groq Cloud's OpenAI-compatible chat
    completions API. Holds no domain logic — prompt construction, grounding
    rules, and response interpretation live in AnswerService."""

    def __init__(self) -> None:
        self._http: httpx.Client | None = None

    @property
    def configured(self) -> bool:
        return bool(settings.GROQ_API_KEY)

    @property
    def client(self) -> httpx.Client:
        if self._http is None:
            self._http = httpx.Client(
                base_url=settings.GROQ_API_BASE_URL,
                headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}"},
                timeout=settings.GROQ_TIMEOUT_SECONDS,
            )
        return self._http

    def chat_json(self, messages: list[dict]) -> dict:
        """Sends a chat completion request in JSON mode and returns the
        model's response parsed as a dict. Raises on transport failure,
        non-2xx status, or a response that isn't valid JSON."""
        response = self.client.post(
            "/chat/completions",
            json={
                "model": settings.GROQ_MODEL,
                "messages": messages,
                "temperature": 0.1,
                "max_tokens": 700,
                "response_format": {"type": "json_object"},
            },
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        return json.loads(content)

    def chat_stream(self, messages: list[dict]) -> Iterator[str]:
        """Streams token deltas from the chat completions endpoint (SSE).

        Uses a `with` block around the HTTP stream so that if the caller stops
        iterating early (e.g. the browser cancels generation and this generator
        is closed), Python injects GeneratorExit at the current yield and the
        `with` block's __exit__ closes the underlying connection to Groq.
        """
        payload = {
            "model": settings.GROQ_MODEL,
            "messages": messages,
            "temperature": 0.1,
            "max_tokens": 700,
            "stream": True,
        }
        with self.client.stream("POST", "/chat/completions", json=payload) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if not line or not line.startswith("data: "):
                    continue
                data = line[len("data: "):]
                if data == "[DONE]":
                    break
                try:
                    event = json.loads(data)
                except json.JSONDecodeError:
                    continue
                delta = event.get("choices", [{}])[0].get("delta", {}).get("content")
                if delta:
                    yield delta


@lru_cache
def get_groq_client() -> GroqClient:
    return GroqClient()
