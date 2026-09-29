"""Multi-turn tool execution orchestrator coordinating LLM providers and ToolRegistry."""

from __future__ import annotations

import json
from typing import Any
from pydantic import BaseModel, Field

from app.ai.base import ChatMessage, LLMProvider, LLMToolCall
from app.ai.factory import get_llm_provider
from app.integrations.base import ToolRegistry, ToolResult
from app.integrations.registry import get_tool_registry


class ToolExecutionRecord(BaseModel):
    """Log of an individual tool call executed during an LLM conversational turn."""
    tool_name: str
    arguments: dict[str, Any]
    result: ToolResult


class ToolRunResult(BaseModel):
    """Complete outcome of a multi-turn tool-augmented execution."""
    final_response: str
    tool_history: list[ToolExecutionRecord] = Field(default_factory=list)
    iterations: int = 0
    provider: str
    model: str


class ToolRunner:
    """Coordinates tool calling loops across any configured provider and ToolRegistry."""

    def __init__(
        self,
        provider: LLMProvider | None = None,
        registry: ToolRegistry | None = None,
        max_iterations: int = 5,
    ) -> None:
        self.provider = provider or get_llm_provider()
        self.registry = registry or get_tool_registry()
        self.max_iterations = max_iterations

    async def run(
        self,
        prompt: str,
        system_prompt: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> ToolRunResult:
        messages: list[ChatMessage] = [ChatMessage(role="user", content=prompt)]
        tool_history: list[ToolExecutionRecord] = []
        available_tools = self.registry.list_tools()

        last_content = ""

        for iteration in range(self.max_iterations):
            resp = await self.provider.generate_with_tools(
                prompt=messages,
                tools=available_tools,
                system_prompt=system_prompt,
            )

            if resp.content:
                last_content = resp.content

            if not resp.has_tool_calls:
                return ToolRunResult(
                    final_response=resp.content or last_content,
                    tool_history=tool_history,
                    iterations=iteration + 1,
                    provider=self.provider.provider_name,
                    model=resp.model,
                )

            # Record assistant turn with tool calls
            messages.append(
                ChatMessage(
                    role="assistant",
                    content=resp.content or "",
                    tool_calls=resp.tool_calls,
                )
            )

            # Execute model-requested tools
            for tc in resp.tool_calls:
                result = await self.registry.execute(tc.tool_name, tc.arguments, context=context)
                tool_history.append(
                    ToolExecutionRecord(
                        tool_name=tc.tool_name,
                        arguments=tc.arguments,
                        result=result,
                    )
                )
                messages.append(
                    ChatMessage(
                        role="tool",
                        name=tc.tool_name,
                        tool_call_id=tc.id,
                        content=json.dumps(result.model_dump(mode="json")),
                    )
                )

        return ToolRunResult(
            final_response=last_content or "Tool execution completed with maximum iterations.",
            tool_history=tool_history,
            iterations=self.max_iterations,
            provider=self.provider.provider_name,
            model=self.provider.default_model,
        )
