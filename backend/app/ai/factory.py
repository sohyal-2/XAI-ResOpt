"""Factory and lifecycle management for AI model providers with auto-selection and offline fallback."""

from __future__ import annotations

import logging
from typing import Any

from app.ai.anthropic_adapter import AnthropicProvider
from app.ai.base import LLMProvider
from app.ai.gemini_adapter import GeminiProvider
from app.ai.mock_adapter import DevelopmentMockProvider
from app.ai.ollama_adapter import OllamaProvider
from app.ai.openai_adapter import OpenAIProvider
from app.core.config import get_settings

logger = logging.getLogger("xai_resopt.ai")


def get_llm_provider(name: str | None = None) -> LLMProvider:
    """Returns an initialized LLMProvider based on explicit name, environment setting, or auto-selection.

    If the chosen provider lacks API credentials, automatically falls back to DevelopmentMockProvider
    so that local development and automated testing continue without interruption.
    """
    settings = get_settings()
    target_provider = (name or settings.ai_provider or "auto").strip().lower()

    if target_provider == "openrouter":
        if settings.openrouter_api_key:
            prov = OpenAIProvider(
                api_key=settings.openrouter_api_key,
                base_url=settings.openrouter_base_url,
                model=settings.openrouter_model,
            )
            prov.provider_name = "openrouter"
            return prov
        logger.warning("OpenRouter provider requested but OPENROUTER_API_KEY is missing. Falling back to DevelopmentMockProvider.")
        return DevelopmentMockProvider()

    if target_provider == "openai":
        prov = OpenAIProvider()
        if prov.is_available():
            return prov
        logger.warning("OpenAI provider requested but OPENAI_API_KEY is missing. Falling back to DevelopmentMockProvider.")
        return DevelopmentMockProvider()

    if target_provider == "anthropic":
        prov = AnthropicProvider()
        if prov.is_available():
            return prov
        logger.warning("Anthropic provider requested but ANTHROPIC_API_KEY is missing. Falling back to DevelopmentMockProvider.")
        return DevelopmentMockProvider()

    if target_provider == "gemini":
        prov = GeminiProvider()
        if prov.is_available():
            return prov
        logger.warning("Gemini provider requested but GEMINI_API_KEY/GOOGLE_API_KEY is missing. Falling back to DevelopmentMockProvider.")
        return DevelopmentMockProvider()

    if target_provider == "ollama":
        prov = OllamaProvider()
        if prov.is_available():
            return prov
        logger.warning("Ollama provider requested but local Ollama server is unreachable. Falling back to DevelopmentMockProvider.")
        return DevelopmentMockProvider()

    if target_provider in {"mock", "development", "dev"}:
        return DevelopmentMockProvider()

    # "auto" resolution mode:
    # 1. Check OpenRouter
    if settings.openrouter_api_key:
        prov = OpenAIProvider(
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
            model=settings.openrouter_model,
        )
        prov.provider_name = "openrouter"
        return prov

    # 2. Check OpenAI
    openai_prov = OpenAIProvider()
    if openai_prov.is_available():
        return openai_prov

    # 3. Check Gemini
    gemini_prov = GeminiProvider()
    if gemini_prov.is_available():
        return gemini_prov

    # 4. Check Anthropic
    anthropic_prov = AnthropicProvider()
    if anthropic_prov.is_available():
        return anthropic_prov

    # 5. Check Ollama
    ollama_prov = OllamaProvider()
    if ollama_prov.is_available():
        return ollama_prov

    # 6. Default fallback to DevelopmentMockProvider
    logger.info("No external AI keys configured; activating DevelopmentMockProvider for offline development.")
    return DevelopmentMockProvider()


def get_ai_status() -> dict[str, Any]:
    """Returns provider status metadata for UI and diagnostics without exposing secrets."""
    settings = get_settings()
    active = get_llm_provider()

    providers_status = [
        {
            "name": "openrouter",
            "configured": bool(settings.openrouter_api_key),
            "model": settings.openrouter_model,
        },
        {
            "name": "openai",
            "configured": bool(settings.openai_api_key),
            "model": settings.openai_model,
        },
        {
            "name": "anthropic",
            "configured": bool(settings.anthropic_api_key),
            "model": settings.anthropic_model,
        },
        {
            "name": "gemini",
            "configured": bool(settings.gemini_api_key or settings.google_api_key),
            "model": settings.gemini_model,
        },
        {
            "name": "ollama",
            "configured": True,  # Accessible locally without key
            "model": settings.ollama_model,
        },
        {
            "name": "development_mock",
            "configured": True,
            "model": "heuristic-dev-v1",
        },
    ]

    return {
        "active_provider": active.provider_name,
        "active_model": active.default_model,
        "is_development_fallback": isinstance(active, DevelopmentMockProvider),
        "configured_providers": providers_status,
    }
