"""Extensible External-Evidence Integration Layer and Modular MCP Tools."""

from app.integrations.base import BaseTool, ToolRegistry, ToolResult
from app.integrations.evidence_rules import (
    MAX_SUPPORTING_CONFIDENCE,
    SUPPORTING_EVIDENCE_TYPE,
    SUPPORTING_RELATIONSHIP_TYPE,
    build_supporting_evidence_item,
    create_supporting_claim_link,
    evaluate_skill_provenance,
)
from app.integrations.github import (
    GitHubClient,
    GitHubProfileMetadata,
    GitHubRepoReaderTool,
    GitHubRepoSummary,
    GitHubSearchTool,
    extract_github_evidence,
)
from app.integrations.policy import (
    PolicyViolationError,
    PrivacyScrubber,
    RateLimitExceededError,
    RobotsPolicyManager,
    rate_limiter,
    robots_policy,
)
from app.integrations.portfolio import (
    PortfolioExtractionResult,
    PortfolioProject,
    PortfolioReaderTool,
    extract_portfolio_evidence,
)
from app.integrations.registry import get_mcp_manifest, get_tool_registry, tool_registry
from app.integrations.tools import (
    AtsEvaluatorTool,
    EvidenceSearchTool,
    JobParserTool,
    ResumeParserTool,
    ResumeRendererTool,
    VectorSearchTool,
)

__all__ = [
    "BaseTool",
    "ToolResult",
    "ToolRegistry",
    "tool_registry",
    "get_tool_registry",
    "get_mcp_manifest",
    "RobotsPolicyManager",
    "robots_policy",
    "rate_limiter",
    "PrivacyScrubber",
    "PolicyViolationError",
    "RateLimitExceededError",
    "SUPPORTING_EVIDENCE_TYPE",
    "MAX_SUPPORTING_CONFIDENCE",
    "SUPPORTING_RELATIONSHIP_TYPE",
    "build_supporting_evidence_item",
    "create_supporting_claim_link",
    "evaluate_skill_provenance",
    "GitHubClient",
    "GitHubProfileMetadata",
    "GitHubRepoSummary",
    "extract_github_evidence",
    "GitHubSearchTool",
    "GitHubRepoReaderTool",
    "PortfolioExtractionResult",
    "PortfolioProject",
    "extract_portfolio_evidence",
    "PortfolioReaderTool",
    "ResumeParserTool",
    "JobParserTool",
    "EvidenceSearchTool",
    "VectorSearchTool",
    "AtsEvaluatorTool",
    "ResumeRendererTool",
]
