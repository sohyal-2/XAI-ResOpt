"""Anthropic Claude API adapter supporting Messages API and tool calling."""

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


class AnthropicProvider(LLMProvider):
    """Adapter for Anthropic Claude (Claude 3.5 Sonnet, Haiku, Opus)."""

    provider_name = "anthropic"

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
        self.api_key = api_key or settings.anthropic_api_key
        self.default_model = model or settings.anthropic_model
        raw_base = base_url or settings.anthropic_base_url or "https://api.anthropic.com"
        self.base_url = raw_base.rstrip("/")
        self.timeout = timeout_seconds or settings.ai_timeout_seconds

    def is_available(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    def _get_headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "x-api-key": self.api_key or "",
            "anthropic-version": "2023-06-01",
        }

    def _split_system_and_messages(
        self, messages: list[ChatMessage]
    ) -> tuple[str | None, list[dict[str, Any]]]:
        system_parts = []
        formatted = []
        for msg in messages:
            if msg.role == "system":
                system_parts.append(msg.content)
            elif msg.role in {"user", "assistant"}:
                formatted.append({"role": msg.role, "content": msg.content})
            elif msg.role == "tool":
                formatted.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": msg.tool_call_id or "tool_call",
                            "content": msg.content,
                        }
                    ],
                })
        system_prompt = "\n\n".join(system_parts) if system_parts else None
        return system_prompt, formatted

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
        sys_text, formatted_msgs = self._split_system_and_messages(messages)

        payload: dict[str, Any] = {
            "model": model or self.default_model,
            "messages": formatted_msgs,
            "max_tokens": max_tokens or 4096,
            "temperature": temperature,
        }
        if sys_text:
            payload["system"] = sys_text

        async with httpx.AsyncClient(timeout=self.timeout, transport=self.transport) as client:
            resp = await client.post(
                f"{self.base_url}/v1/messages",
                headers=self._get_headers(),
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        text_blocks = [
            b.get("text", "") for b in data.get("content", []) if b.get("type") == "text"
        ]
        content = "\n".join(text_blocks)
        usage_data = data.get("usage", {})

        return LLMResponse(
            content=content,
            model=data.get("model", model or self.default_model),
            provider=self.provider_name,
            usage=TokenUsage(
                prompt_tokens=usage_data.get("input_tokens", 0),
                completion_tokens=usage_data.get("output_tokens", 0),
                total_tokens=usage_data.get("input_tokens", 0) + usage_data.get("output_tokens", 0),
            ),
            finish_reason=data.get("stop_reason"),
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
            f"\nYou must respond ONLY with a raw JSON object strictly adhering to this schema. "
            f"Do not include markdown code block backticks:\n{schema_json}"
        )
        effective_system = (system_prompt or "") + instruction

        res = await self.generate(
            prompt=prompt,
            system_prompt=effective_system,
            model=model,
            temperature=temperature,
            **kwargs,
        )
        cleaned = res.content.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("```")[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
            cleaned = cleaned.strip()

        return schema.model_validate_json(cleaned)

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
        sys_text, formatted_msgs = self._split_system_and_messages(messages)

        payload: dict[str, Any] = {
            "model": model or self.default_model,
            "messages": formatted_msgs,
            "max_tokens": 4096,
            "temperature": temperature,
            "tools": [t.to_anthropic_tool() for t in tools],
        }
        if sys_text:
            payload["system"] = sys_text

        async with httpx.AsyncClient(timeout=self.timeout, transport=self.transport) as client:
            resp = await client.post(
                f"{self.base_url}/v1/messages",
                headers=self._get_headers(),
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        tool_calls: list[LLMToolCall] = []
        text_parts: list[str] = []

        for block in data.get("content", []):
            if block.get("type") == "text":
                text_parts.append(block.get("text", ""))
            elif block.get("type") == "tool_use":
                tool_calls.append(
                    LLMToolCall(
                        id=block.get("id", ""),
                        tool_name=block.get("name", ""),
                        arguments=block.get("input", {}),
                    )
                )

        usage_data = data.get("usage", {})
        return LLMToolResponse(
            content="\n".join(text_parts) if text_parts else None,
            tool_calls=tool_calls,
            model=data.get("model", model or self.default_model),
            provider=self.provider_name,
            usage=TokenUsage(
                prompt_tokens=usage_data.get("input_tokens", 0),
                completion_tokens=usage_data.get("output_tokens", 0),
                total_tokens=usage_data.get("input_tokens", 0) + usage_data.get("output_tokens", 0),
            ),
            finish_reason=data.get("stop_reason"),
            raw_response=data,
        )
