"""Base interfaces and data structures for modular, provider-agnostic, MCP-ready tools."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any
from pydantic import BaseModel, Field


class ToolResult(BaseModel):
    """Normalized execution result returned by all tools."""

    success: bool
    data: Any = None
    error: str | None = None
    provenance: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def ok(cls, data: Any, provenance: dict[str, Any] | None = None) -> ToolResult:
        return cls(success=True, data=data, error=None, provenance=provenance or {})

    @classmethod
    def fail(cls, error: str, provenance: dict[str, Any] | None = None) -> ToolResult:
        return cls(success=False, data=None, error=error, provenance=provenance or {})


class BaseTool(ABC):
    """Provider-agnostic tool base class designed for direct MCP tool exposure and multi-LLM function calling."""

    name: str
    description: str
    parameters_schema: dict[str, Any]

    @abstractmethod
    async def execute(self, params: dict[str, Any], context: dict[str, Any] | None = None) -> ToolResult:
        """Executes the tool with given parameters and contextual state."""
        ...

    def to_mcp_tool(self) -> dict[str, Any]:
        """Converts the tool definition into standard Model Context Protocol (MCP) format."""
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.parameters_schema,
        }

    def to_openai_tool(self) -> dict[str, Any]:
        """Converts the tool definition into standard OpenAI / OpenAI-compatible function calling format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters_schema,
            },
        }

    def to_anthropic_tool(self) -> dict[str, Any]:
        """Converts the tool definition into Anthropic Claude tool calling format."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.parameters_schema,
        }

    def to_gemini_tool(self) -> dict[str, Any]:
        """Converts the tool definition into Google Gemini FunctionDeclaration format."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters_schema,
        }


class ToolRegistry:
    """Central registry of modular tools accessible by agents, copilot, and MCP servers."""

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool | None:
        return self._tools.get(name)

    def list_tools(self) -> list[BaseTool]:
        return list(self._tools.values())

    def to_mcp_manifest(self) -> list[dict[str, Any]]:
        return [tool.to_mcp_tool() for tool in self._tools.values()]

    def to_openai_tools(self) -> list[dict[str, Any]]:
        return [tool.to_openai_tool() for tool in self._tools.values()]

    def to_anthropic_tools(self) -> list[dict[str, Any]]:
        return [tool.to_anthropic_tool() for tool in self._tools.values()]

    def to_gemini_tools(self) -> list[dict[str, Any]]:
        return [tool.to_gemini_tool() for tool in self._tools.values()]

    async def execute(
        self, name: str, params: dict[str, Any], context: dict[str, Any] | None = None
    ) -> ToolResult:
        tool = self.get(name)
        if not tool:
            return ToolResult.fail(f"Tool '{name}' is not registered in the ToolRegistry.")
        try:
            return await tool.execute(params, context)
        except Exception as error:
            return ToolResult.fail(f"Execution of tool '{name}' failed: {error}")
