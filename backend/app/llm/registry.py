"""LLM registry."""

from __future__ import annotations

from functools import lru_cache

from ..config import settings
from .base import LLMProvider

__all__ = ["get_llm", "LLMProvider", "has_llm"]


@lru_cache(maxsize=1)
def get_llm() -> LLMProvider:
    provider = settings.llm_provider
    if provider in {"none", "", "off", "disabled", "mock", "local"}:
        from .remote import MockLLMProvider
        return MockLLMProvider()
    from .remote import build_provider
    try:
        return build_provider(provider)
    except Exception:
        from .remote import MockLLMProvider
        return MockLLMProvider()


def has_llm() -> bool:
    if settings.llm_provider in {"none", "", "off", "disabled"}:
        return False
    return bool(
        {
            "openai": settings.openai_api_key,
            "anthropic": settings.anthropic_api_key,
            "gemini": settings.gemini_api_key,
            "mock": True,
            "local": True,
        }.get(settings.llm_provider))

