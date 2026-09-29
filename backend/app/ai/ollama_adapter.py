"""Local model / Ollama adapter supporting local private inference and tool calling."""

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


class OllamaProvider(LLMProvider):
    """Adapter for local models hosted on Ollama (e.g., Llama 3.2, Qwen 2.5)."""

    provider_name = "ollama"

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout_seconds: float | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.transport = transport
        settings = get_settings()
        raw_base = base_url or settings.ollama_base_url or "http://localhost:11434"
        self.base_url = raw_base.rstrip("/")
        self.default_model = model or settings.ollama_model
        self.timeout = timeout_seconds or settings.ai_timeout_seconds

    def is_available(self) -> bool:
        # Check basic connectivity to local Ollama server
        try:
            with httpx.Client(timeout=0.4) as client:
                res = client.get(f"{self.base_url}/api/tags")
                return res.status_code == 200
        except Exception:
            return False

    def _format_messages(self, messages: list[ChatMessage]) -> list[dict[str, Any]]:
        formatted = []
        for msg in messages:
            item: dict[str, Any] = {"role": msg.role, "content": msg.content}
            if msg.tool_calls:
                item["tool_calls"] = [
                    {
                        "function": {
                            "name": tc.tool_name,
                            "arguments": tc.arguments,
                        }
                    }
                    for tc in msg.tool_calls
                ]
            formatted.append(item)
        return formatted

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
        payload: dict[str, Any] = {
            "model": model or self.default_model,
            "messages": self._format_messages(messages),
            "stream": False,
            "options": {"temperature": temperature},
        }
        if max_tokens:
            payload["options"]["num_predict"] = max_tokens

        async with httpx.AsyncClient(timeout=self.timeout, transport=self.transport) as client:
            resp = await client.post(f"{self.base_url}/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()

        msg = data.get("message", {})
        content = msg.get("content", "")

        return LLMResponse(
            content=content,
            model=data.get("model", model or self.default_model),
            provider=self.provider_name,
            usage=TokenUsage(
                prompt_tokens=data.get("prompt_eval_count", 0),
                completion_tokens=data.get("eval_count", 0),
                total_tokens=data.get("prompt_eval_count", 0) + data.get("eval_count", 0),
            ),
            finish_reason=data.get("done_reason"),
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
            f"\nYou must output JSON conforming to this schema:\n{schema_json}"
        )
        effective_system = (system_prompt or "") + instruction

        messages = self._normalize_messages(prompt, effective_system)
        payload: dict[str, Any] = {
            "model": model or self.default_model,
            "messages": self._format_messages(messages),
            "format": "json",
            "stream": False,
            "options": {"temperature": temperature},
        }

        async with httpx.AsyncClient(timeout=self.timeout, transport=self.transport) as client:
            resp = await client.post(f"{self.base_url}/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()

        content = data.get("message", {}).get("content", "{}")
        return schema.model_validate_json(content)

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
        payload: dict[str, Any] = {
            "model": model or self.default_model,
            "messages": self._format_messages(messages),
            "tools": [t.to_openai_tool() for t in tools],
            "stream": False,
            "options": {"temperature": temperature},
        }

        async with httpx.AsyncClient(timeout=self.timeout, transport=self.transport) as client:
            resp = await client.post(f"{self.base_url}/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()

        msg = data.get("message", {})
        raw_tools = msg.get("tool_calls", [])

        tool_calls: list[LLMToolCall] = []
        for idx, tc in enumerate(raw_tools):
            fn = tc.get("function", {})
            args = fn.get("arguments", {})
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except Exception:
                    args = {"raw": args}
            tool_calls.append(
                LLMToolCall(
                    id=f"call_{idx}",
                    tool_name=fn.get("name", ""),
                    arguments=args,
                )
            )

        return LLMToolResponse(
            content=msg.get("content"),
            tool_calls=tool_calls,
            model=data.get("model", model or self.default_model),
            provider=self.provider_name,
            usage=TokenUsage(
                prompt_tokens=data.get("prompt_eval_count", 0),
                completion_tokens=data.get("eval_count", 0),
                total_tokens=data.get("prompt_eval_count", 0) + data.get("eval_count", 0),
            ),
            finish_reason=data.get("done_reason"),
            raw_response=data,
        )
