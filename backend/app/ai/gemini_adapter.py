"""Google Gemini API adapter supporting Google AI Studio REST API and Function Declarations."""

from __future__ import annotations

import json
from typing import Any, TypeVar
import httpx
from pydantic import BaseModel

from app.ai.base import (
    ChatMessage,
    LLMProvider,
    LLMResponse,
    LLMToolCall,
    LLMToolResponse,
    TokenUsage,
)
from app.core.config import get_settings
from app.integrations.base import BaseTool

T = TypeVar("T", bound=BaseModel)


class GeminiProvider(LLMProvider):
    """Adapter for Google Gemini models via Google AI Studio API."""

    provider_name = "gemini"

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        timeout_seconds: float | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.transport = transport
        settings = get_settings()
        self.api_key = api_key or settings.gemini_api_key or settings.google_api_key
        self.default_model = model or settings.gemini_model
        raw_base = base_url or settings.gemini_base_url or "https://generativelanguage.googleapis.com"
        self.base_url = raw_base.rstrip("/")
        self.timeout = timeout_seconds or settings.ai_timeout_seconds

    def is_available(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    def _format_contents(
        self, messages: list[ChatMessage]
    ) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
        system_instruction = None
        system_texts = [m.content for m in messages if m.role == "system"]
        if system_texts:
            system_instruction = {"parts": [{"text": "\n\n".join(system_texts)}]}

        contents = []
        for msg in messages:
            if msg.role == "system":
                continue
            role = "user" if msg.role in {"user", "tool"} else "model"
            contents.append({"role": role, "parts": [{"text": msg.content}]})

        return system_instruction, contents

    async def generate(
        self,
        prompt: str | list[ChatMessage],
        system_prompt: str | None = None,
        model: str | None = None,
        temperature: float = 0.0,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        messages = self._normalize_messages(prompt, system_prompt)
        sys_inst, contents = self._format_contents(messages)

        target_model = model or self.default_model
        url = f"{self.base_url}/v1beta/models/{target_model}:generateContent?key={self.api_key or ''}"

        payload: dict[str, Any] = {
            "contents": contents,
            "generationConfig": {"temperature": temperature},
        }
        if sys_inst:
            payload["systemInstruction"] = sys_inst
        if max_tokens:
            payload["generationConfig"]["maxOutputTokens"] = max_tokens

        async with httpx.AsyncClient(timeout=self.timeout, transport=self.transport) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()

        candidate = data.get("candidates", [{}])[0]
        parts = candidate.get("content", {}).get("parts", [])
        text_content = "".join(p.get("text", "") for p in parts)
        usage_meta = data.get("usageMetadata", {})

        return LLMResponse(
            content=text_content,
            model=target_model,
            provider=self.provider_name,
            usage=TokenUsage(
                prompt_tokens=usage_meta.get("promptTokenCount", 0),
                completion_tokens=usage_meta.get("candidatesTokenCount", 0),
                total_tokens=usage_meta.get("totalTokenCount", 0),
            ),
            finish_reason=candidate.get("finishReason"),
            raw_response=data,
        )

    async def generate_structured(
        self,
        prompt: str | list[ChatMessage],
        schema: type[T],
        system_prompt: str | None = None,
        model: str | None = None,
        temperature: float = 0.0,
        **kwargs: Any,
    ) -> T:
        schema_json = json.dumps(schema.model_json_schema(), indent=2)
        instruction = (
            f"\nYou must respond ONLY with a raw JSON object strictly adhering to this schema:\n{schema_json}"
        )
        effective_system = (system_prompt or "") + instruction

        messages = self._normalize_messages(prompt, effective_system)
        sys_inst, contents = self._format_contents(messages)

        target_model = model or self.default_model
        url = f"{self.base_url}/v1beta/models/{target_model}:generateContent?key={self.api_key or ''}"

        payload: dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "responseMimeType": "application/json",
            },
        }
        if sys_inst:
            payload["systemInstruction"] = sys_inst

        async with httpx.AsyncClient(timeout=self.timeout, transport=self.transport) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()

        candidate = data.get("candidates", [{}])[0]
        text_content = candidate.get("content", {}).get("parts", [{}])[0].get("text", "")
        return schema.model_validate_json(text_content)

    async def generate_with_tools(
        self,
        prompt: str | list[ChatMessage],
        tools: list[BaseTool],
        system_prompt: str | None = None,
        model: str | None = None,
        temperature: float = 0.0,
        **kwargs: Any,
    ) -> LLMToolResponse:
        messages = self._normalize_messages(prompt, system_prompt)
        sys_inst, contents = self._format_contents(messages)

        target_model = model or self.default_model
        url = f"{self.base_url}/v1beta/models/{target_model}:generateContent?key={self.api_key or ''}"

        gemini_tools = [
            {"functionDeclarations": [t.to_gemini_tool() for t in tools]}
        ]

        payload: dict[str, Any] = {
            "contents": contents,
            "tools": gemini_tools,
            "generationConfig": {"temperature": temperature},
        }
        if sys_inst:
            payload["systemInstruction"] = sys_inst

        async with httpx.AsyncClient(timeout=self.timeout, transport=self.transport) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()

        candidate = data.get("candidates", [{}])[0]
        parts = candidate.get("content", {}).get("parts", [])

        tool_calls: list[LLMToolCall] = []
        text_parts: list[str] = []

        for p in parts:
            if "text" in p:
                text_parts.append(p["text"])
            elif "functionCall" in p:
                fc = p["functionCall"]
                tool_calls.append(
                    LLMToolCall(
                        id=f"call_{fc.get('name')}",
                        tool_name=fc.get("name", ""),
                        arguments=fc.get("args", {}),
                    )
                )

        usage_meta = data.get("usageMetadata", {})
        return LLMToolResponse(
            content="".join(text_parts) if text_parts else None,
            tool_calls=tool_calls,
            model=target_model,
            provider=self.provider_name,
            usage=TokenUsage(
                prompt_tokens=usage_meta.get("promptTokenCount", 0),
                completion_tokens=usage_meta.get("candidatesTokenCount", 0),
                total_tokens=usage_meta.get("totalTokenCount", 0),
            ),
            finish_reason=candidate.get("finishReason"),
            raw_response=data,
        )
