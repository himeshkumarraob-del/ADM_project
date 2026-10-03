"""Chat completion providers (OpenAI, Anthropic, Gemini) over httpx."""

from __future__ import annotations

import httpx

from ..config import settings
from .base import LLMProvider


class _BaseHTTP:
    name = "base"
    model = ""

    def __init__(self) -> None:
        self.timeout = settings.http_timeout_seconds
        self.temperature = settings.llm_temperature
        self.max_tokens = settings.llm_max_tokens

    def complete(self, messages, *, temperature=None, max_tokens=None, json_mode=False) -> str:
        raise NotImplementedError

    @staticmethod
    def _split(messages: list[dict]) -> tuple[str, list[dict]]:
        """Return (system_prompt, remaining_messages)."""
        system = "\n\n".join(m["content"] for m in messages if m.get("role") == "system")
        rest = [m for m in messages if m.get("role") != "system"]
        return system, rest


class OpenAIProvider(_BaseHTTP):
    name = "openai"

    def __init__(self) -> None:
        super().__init__()
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required for LLM_PROVIDER=openai")
        self.model = settings.openai_chat_model
        self._client = httpx.Client(
            base_url="https://api.openai.com/v1",
            headers={"Authorization": f"Bearer {settings.openai_api_key}"},
            timeout=self.timeout,
        )

    def complete(self, messages, *, temperature=None, max_tokens=None, json_mode=False) -> str:
        payload: dict = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature if temperature is None else temperature,
            "max_tokens": self.max_tokens if max_tokens is None else max_tokens,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        resp = self._client.post("/chat/completions", json=payload)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"] or ""


class AnthropicProvider(_BaseHTTP):
    name = "anthropic"

    def __init__(self) -> None:
        super().__init__()
        if not settings.anthropic_api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is required for LLM_PROVIDER=anthropic")
        self.model = settings.anthropic_chat_model
        self._client = httpx.Client(
            base_url="https://api.anthropic.com/v1",
            headers={
                "x-api-key": settings.anthropic_api_key,
                "anthropic-version": "2023-06-01",
            },
            timeout=self.timeout,
        )

    def complete(self, messages, *, temperature=None, max_tokens=None, json_mode=False) -> str:
        system, rest = self._split(messages)
        payload: dict = {
            "model": self.model,
            "system": system,
            "messages": rest,
            "temperature": self.temperature if temperature is None else temperature,
            "max_tokens": self.max_tokens if max_tokens is None else max_tokens,
        }
        resp = self._client.post("/messages", json=payload)
        resp.raise_for_status()
        blocks = resp.json().get("content", [])
        return "".join(b.get("text", "") for b in blocks if b.get("type") == "text")


class GeminiProvider(_BaseHTTP):
    name = "gemini"

    def __init__(self) -> None:
        super().__init__()
        if not settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY is required for LLM_PROVIDER=gemini")
        self.model = settings.gemini_chat_model
        self._client = httpx.Client(timeout=self.timeout)

    def complete(self, messages, *, temperature=None, max_tokens=None, json_mode=False) -> str:
        system, rest = self._split(messages)
        parts: list[dict] = []
        for m in rest:
            prefix = "User: " if m["role"] == "user" else "Assistant: "
            parts.append({"text": prefix + m["content"]})
        payload = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": {
                "temperature": self.temperature if temperature is None else temperature,
                "maxOutputTokens": self.max_tokens if max_tokens is None else max_tokens,
            },
        }
        if json_mode:
            payload["generationConfig"]["responseMimeType"] = "application/json"
        resp = self._client.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent",
            params={"key": settings.gemini_api_key},
            json=payload,
        )
        resp.raise_for_status()
        cand = resp.json().get("candidates", [{}])[0]
        return cand.get("content", {}).get("parts", [{}])[0].get("text", "") or ""


class MockLLMProvider(_BaseHTTP):
    name = "mock"
    model = "mock-mahabharata-v1"

    def complete(self, messages: list[dict], *, temperature=None, max_tokens=None, json_mode=False) -> str:
        import json
        import re
        system, rest = self._split(messages)
        user_content = "\n".join(m.get("content", "") for m in rest if m.get("role") == "user")

        passage_ids = re.findall(r"\[([a-zA-Z0-9_\-]+)\]", user_content)
        passage_ids = [p for p in dict.fromkeys(passage_ids) if len(p) > 2]

        if not passage_ids:
            return json.dumps({
                "situation_summary": "Dilemma query",
                "episode": "",
                "episode_reference": "",
                "episode_characters": [],
                "primary_text": [],
                "interpretation": "I could not find a sufficiently direct passage in the source material to support this conclusion.",
                "application": "",
                "reflection_questions": [
                    "What fundamental duty or principle applies in your situation?",
                    "Are your choices driven by long-term consequences or immediate desires?",
                    "How might an impartial advisor view this dilemma?"
                ],
                "perspectives": [],
                "support_level": "insufficient_evidence",
                "evidence_note": "I could not find a sufficiently direct passage in the source material to support this conclusion."
            })

        primary_id = passage_ids[0]
        return json.dumps({
            "situation_summary": "Analysis of the dilemma based on Mahabharata teachings.",
            "episode": "An episode retrieved from the Mahabharata corpus.",
            "episode_reference": "Mahabharata Source",
            "episode_characters": ["Krishna", "Arjuna"],
            "primary_text": [primary_id],
            "interpretation": "This passage highlights the importance of adhering to one's core duty and maintaining equanimity.",
            "application": "When facing pressure or dilemma, separate your immediate desires from your higher duty (dharma).",
            "reflection_questions": [
                "Which choice aligns best with your fundamental duty?",
                "What are the long-term consequences of compromising your values?",
                "How can you remain steadfast under external pressure?"
            ],
            "perspectives": [
                {
                    "character": "Krishna",
                    "character_slug": "krishna",
                    "stance": "Perform your duty without clinging to immediate outcomes.",
                    "basis": "Bhagavad Gita teachings on selfless action.",
                    "passage_ids": [primary_id]
                }
            ],
            "support_level": "strong_textual_support",
            "evidence_note": "Verified primary text supports this principle."
        })


ProviderName = str


def build_provider(name: ProviderName) -> LLMProvider:
    if name in ("mock", "local", "none"):
        return MockLLMProvider()
    if name == "openai":
        return OpenAIProvider()
    if name == "anthropic":
        return AnthropicProvider()
    if name == "gemini":
        return GeminiProvider()
    raise ValueError(f"Unknown LLM_PROVIDER: {name!r}")

