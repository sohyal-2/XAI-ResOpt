"""Central registry registering all 9 modular tools and exposing MCP tool manifests."""

from __future__ import annotations

from app.integrations.base import ToolRegistry
from app.integrations.github import GitHubRepoReaderTool, GitHubSearchTool
from app.integrations.portfolio import PortfolioReaderTool
from app.integrations.tools import (
    AtsEvaluatorTool,
    EvidenceSearchTool,
    JobParserTool,
    ResumeParserTool,
    ResumeRendererTool,
    VectorSearchTool,
)

# Instantiate the central tool registry
tool_registry = ToolRegistry()

# Register all 9 modular, provider-agnostic MCP tools
tool_registry.register(GitHubSearchTool())
tool_registry.register(GitHubRepoReaderTool())
tool_registry.register(PortfolioReaderTool())
tool_registry.register(ResumeParserTool())
tool_registry.register(JobParserTool())
tool_registry.register(EvidenceSearchTool())
tool_registry.register(VectorSearchTool())
tool_registry.register(AtsEvaluatorTool())
tool_registry.register(ResumeRendererTool())


def get_tool_registry() -> ToolRegistry:
    """Returns the initialized global tool registry."""
    return tool_registry


def get_mcp_manifest() -> list[dict]:
    """Returns all registered tools in the Model Context Protocol (MCP) JSON schema format."""
    return tool_registry.to_mcp_manifest()
