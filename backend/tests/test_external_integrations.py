"""Comprehensive integration tests for the external-evidence integration layer, policies, and modular tools."""

import json
from uuid import uuid4
import pytest

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
    clean_markdown_for_evidence,
    extract_github_evidence,
    parse_github_url,
)
from app.integrations.policy import (
    PolicyViolationError,
    PrivacyScrubber,
    RateLimitExceededError,
    RateLimitTracker,
    RobotsPolicyManager,
)
from app.integrations.portfolio import (
    PortfolioExtractionResult,
    PortfolioProject,
    PortfolioReaderTool,
    extract_portfolio_evidence,
    parse_portfolio_content,
)
from app.integrations.registry import get_mcp_manifest, get_tool_registry
from app.integrations.tools import (
    AtsEvaluatorTool,
    EvidenceSearchTool,
    JobParserTool,
    ResumeParserTool,
    ResumeRendererTool,
    VectorSearchTool,
)
from app.models import EvidenceItem


# ==============================================================================
# 1. Policy, Compliance & Privacy Tests
# ==============================================================================

def test_privacy_scrubber_redacts_credentials():
    raw_text = (
        "Project built with secret key AKIAIOSFODNN7EXAMPLE and GitHub token "
        "ghp_1234567890abcdefghijklmnopqrstuvwxyz123456. "
        "Database is postgres://admin:supersecret@db.internal:5432/db. "
        "Also OpenAI key sk-abcdef1234567890abcdef1234567890. "
        "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0."
    )
    scrubbed = PrivacyScrubber.scrub(raw_text)

    assert "AKIAIOSFODNN7EXAMPLE" not in scrubbed
    assert "[REDACTED_AWS_KEY]" in scrubbed
    assert "ghp_1234567890abcdef" not in scrubbed
    assert "[REDACTED_GITHUB_TOKEN]" in scrubbed
    assert "supersecret" not in scrubbed
    assert "[REDACTED_PASSWORD]" in scrubbed
    assert "sk-abcdef" not in scrubbed
    assert "[REDACTED_API_KEY]" in scrubbed


def test_rate_limit_tracker():
    tracker = RateLimitTracker()
    import httpx

    headers = httpx.Headers({
        "x-ratelimit-remaining": "0",
        "x-ratelimit-limit": "60",
        "x-ratelimit-reset": "9999999999",  # Far in the future
    })
    tracker.update_from_headers(headers)

    assert tracker.remaining == 0
    assert tracker.limit == 60

    with pytest.raises(RateLimitExceededError) as exc_info:
        tracker.check_rate_limit()
    assert "rate limit reached" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_robots_policy_manager_disallow():
    manager = RobotsPolicyManager()
    # Mock cache with a disallowed parser
    from urllib.robotparser import RobotFileParser
    parser = RobotFileParser()
    parser.parse([
        "User-agent: *",
        "Disallow: /private/",
        "Disallow: /admin/",
        "Allow: /projects",
    ])
    manager._cache["https://example.com"] = (parser, 9999999999.0)

    assert await manager.is_allowed("https://example.com/projects") is True
    assert await manager.is_allowed("https://example.com/private/resume.html") is False
    assert await manager.is_allowed("https://example.com/admin/secret") is False


# ==============================================================================
# 2. Invariant Enforcement: External Data is Supporting Evidence ONLY
# ==============================================================================

def test_external_data_never_automatically_proves_skill():
    owner_id = uuid4()
    ext_item = build_supporting_evidence_item(
        owner_id=owner_id,
        source_type="github",
        source_uri="https://github.com/alice/distributed-kv",
        source_document="GitHub Repo: distributed-kv",
        source_location="github:alice/distributed-kv#readme",
        raw_text="Production Raft consensus key-value store written in Rust and Go.",
        confidence=0.95,  # Requesting 0.95 confidence
    )

    # Confidence must be strictly capped
    assert ext_item.evidence_type == SUPPORTING_EVIDENCE_TYPE
    assert ext_item.confidence <= MAX_SUPPORTING_CONFIDENCE
    assert ext_item.confidence == 0.70

    # Invariant check: Skill NOT in resume cannot be automatically proven
    result_unclaimed = evaluate_skill_provenance(
        skill_name="Rust",
        has_resume_mention=False,
        supporting_items=[ext_item],
    )
    assert result_unclaimed.is_proven is False
    assert result_unclaimed.status == "unsupported_in_resume"
    assert "cannot automatically prove a skill" in result_unclaimed.rationale

    # Invariant check: Skill IS in resume, corroborated by external evidence
    result_claimed = evaluate_skill_provenance(
        skill_name="Rust",
        has_resume_mention=True,
        supporting_items=[ext_item],
    )
    assert result_claimed.is_proven is True
    assert result_claimed.status == "corroborated"
    assert len(result_claimed.supporting_evidence_ids) == 1


def test_supporting_claim_link():
    claim_id = uuid4()
    evidence_id = uuid4()
    link = create_supporting_claim_link(claim_id, evidence_id, "Corroborated by GitHub README")

    assert link.relationship_type == SUPPORTING_RELATIONSHIP_TYPE
    assert link.support_confidence <= MAX_SUPPORTING_CONFIDENCE
    assert "[Supporting Evidence Only]" in link.rationale


# ==============================================================================
# 3. GitHub Extraction & Tools
# ==============================================================================

def test_parse_github_url():
    user, repo = parse_github_url("https://github.com/octocat")
    assert user == "octocat"
    assert repo is None

    user, repo = parse_github_url("https://github.com/octocat/Hello-World")
    assert user == "octocat"
    assert repo == "Hello-World"

    user, repo = parse_github_url("https://github.com/octocat/Hello-World/tree/main/src")
    assert user == "octocat"
    assert repo == "Hello-World"


def test_clean_markdown_for_evidence():
    md = (
        "# My Awesome Project\n\n"
        "[![Build](https://img.shields.io/badge/build-passing.svg)](https://ci.example.com)\n"
        "![Logo](https://example.com/logo.png)\n\n"
        "This project implements high-throughput stream ingestion.\n\n"
        "<div class='info'>Some html</div>"
    )
    cleaned = clean_markdown_for_evidence(md)
    assert "Build" not in cleaned
    assert "shields.io" not in cleaned
    assert "logo.png" not in cleaned
    assert "<div" not in cleaned
    assert "This project implements high-throughput stream ingestion." in cleaned


@pytest.mark.asyncio
async def test_extract_github_evidence_mocked():
    class MockGitHubClient(GitHubClient):
        async def fetch_user_profile(self, username: str):
            return {
                "name": "Jane Doe",
                "bio": "Senior Backend & Distributed Systems Engineer",
                "company": "Tech Corp",
                "location": "San Francisco, CA",
                "blog": "https://janedoe.dev",
                "public_repos": 12,
                "html_url": f"https://github.com/{username}",
            }

        async def fetch_user_repos(self, username: str, limit: int = 10):
            return [
                {
                    "name": "raft-kv",
                    "full_name": f"{username}/raft-kv",
                    "description": "High performance Raft consensus engine in Go",
                    "language": "Go",
                    "stargazers_count": 240,
                    "forks_count": 35,
                    "topics": ["raft", "consensus", "go", "distributed-systems"],
                    "html_url": f"https://github.com/{username}/raft-kv",
                    "pushed_at": "2026-03-01T12:00:00Z",
                }
            ]

        async def fetch_repo_languages(self, owner: str, repo: str):
            return {"Go": 85000, "Shell": 1200}

        async def fetch_repo_readme(self, owner: str, repo: str):
            return "# raft-kv\n\nA resilient distributed key-value store using Raft consensus protocol."

        async def fetch_user_events(self, username: str):
            return [{"type": "PushEvent"}, {"type": "CreateEvent"}]

    mock_client = MockGitHubClient()
    owner_id = uuid4()
    meta, items = await extract_github_evidence("https://github.com/janedoe", owner_id, client=mock_client)

    assert meta.username == "janedoe"
    assert meta.name == "Jane Doe"
    assert len(meta.repositories) == 1
    assert meta.repositories[0].name == "raft-kv"
    assert meta.repositories[0].languages == {"Go": 85000, "Shell": 1200}
    assert meta.repositories[0].stars == 240

    # Evidence items check
    assert len(items) >= 2  # Profile bio item + repo item + readme item
    for item in items:
        assert item.evidence_type == SUPPORTING_EVIDENCE_TYPE
        assert item.confidence <= MAX_SUPPORTING_CONFIDENCE
        assert item.owner_id == owner_id


@pytest.mark.asyncio
async def test_github_tools_execution():
    class MockSearchClient(GitHubClient):
        async def search_repositories(self, query: str, limit: int = 5):
            return [
                {
                    "name": "resopt-engine",
                    "full_name": "xai/resopt-engine",
                    "description": "Explainable ATS optimization engine",
                    "language": "Python",
                    "stargazers_count": 42,
                    "html_url": "https://github.com/xai/resopt-engine",
                }
            ]

        async def fetch_repo_details(self, owner: str, repo: str):
            return {
                "name": repo,
                "full_name": f"{owner}/{repo}",
                "description": "Repository details for testing",
                "language": "Python",
                "stargazers_count": 10,
                "forks_count": 2,
                "topics": ["testing", "ats"],
                "html_url": f"https://github.com/{owner}/{repo}",
            }

        async def fetch_repo_languages(self, owner: str, repo: str):
            return {"Python": 90000}

        async def fetch_repo_readme(self, owner: str, repo: str):
            return "# Documentation\nTesting repository details."

    mock_client = MockSearchClient()

    # 1. github_search tool
    search_tool = GitHubSearchTool(client=mock_client)
    res_search = await search_tool.execute({"query": "resopt", "limit": 3})
    assert res_search.success is True
    assert res_search.data["count"] == 1
    assert res_search.data["repositories"][0]["name"] == "resopt-engine"

    # 2. github_repo_reader tool
    reader_tool = GitHubRepoReaderTool(client=mock_client)
    res_reader = await reader_tool.execute({"owner": "xai", "repo": "resopt-engine"})
    assert res_reader.success is True
    assert res_reader.data["primary_language"] == "Python"
    assert res_reader.data["languages"] == {"Python": 90000}
    assert "Testing repository details" in res_reader.data["readme_snippet"]


# ==============================================================================
# 4. Portfolio Extraction & Tools
# ==============================================================================

def test_parse_portfolio_content():
    html = """
    <!DOCTYPE html>
    <html>
      <head><title>Alex Rivera - Portfolio</title></head>
      <body>
        <header><nav><a href="/">Home</a></nav></header>
        <section id="about">
          <h1>Alex Rivera</h1>
          <p>Full stack engineer specializing in Python, React, and cloud architecture.</p>
        </section>
        <section id="projects">
          <h2>Featured Projects</h2>
          <div class="project-card">
            <h3>CloudWatch Pipeline</h3>
            <p>Real-time distributed telemetry pipeline handling 10k metrics/sec.</p>
            <span class="badge">Go</span>
            <span class="badge">Kafka</span>
            <a href="https://example.com/cloudwatch">View Project</a>
          </div>
          <div class="project-card">
            <h3>NLP Parser</h3>
            <p>Deterministic syntactic parser with token alignment.</p>
            <span class="badge">Python</span>
            <span class="badge">PyTorch</span>
          </div>
        </section>
      </body>
    </html>
    """
    result = parse_portfolio_content(html, "https://alexrivera.dev")

    assert result.title == "Alex Rivera - Portfolio"
    assert len(result.projects) == 2
    assert result.projects[0].title == "CloudWatch Pipeline"
    assert "10k metrics/sec" in result.projects[0].description
    assert "Go" in result.projects[0].technologies
    assert "Kafka" in result.projects[0].technologies


# ==============================================================================
# 5. Modular Tools Registry & MCP Manifest
# ==============================================================================

def test_tool_registry_manifest():
    registry = get_tool_registry()
    tools = registry.list_tools()

    expected_tool_names = {
        "github_search",
        "github_repo_reader",
        "portfolio_reader",
        "resume_parser",
        "job_parser",
        "evidence_search",
        "vector_search",
        "ats_evaluator",
        "resume_renderer",
    }
    actual_names = {t.name for t in tools}
    assert expected_tool_names.issubset(actual_names)

    # Test MCP Manifest export
    manifest = get_mcp_manifest()
    assert len(manifest) >= 9
    for m in manifest:
        assert "name" in m
        assert "description" in m
        assert "inputSchema" in m
        assert m["inputSchema"]["type"] == "object"


@pytest.mark.asyncio
async def test_core_modular_tools_execution():
    registry = get_tool_registry()

    # 1. resume_parser
    resume_text = (
        "Jane Doe\njane@example.com | San Francisco, CA\n\n"
        "Summary\nSenior software architect.\n\n"
        "Experience\nLead Developer at Acme Corp\n- Built scalable microservices in Python\n\n"
        "Skills\nPython, Docker, PostgreSQL"
    )
    res_parse = await registry.execute("resume_parser", {"text": resume_text})
    assert res_parse.success is True
    assert res_parse.data["name"] == "Jane Doe"
    assert "experience" in res_parse.data["sections"]

    # 2. job_parser
    job_text = (
        "Senior Backend Engineer\n\n"
        "Requirements:\n"
        "- 5+ years experience\n"
        "- Strong proficiency in Python and FastAPI (mandatory)\n"
        "- Experience with Docker and Kubernetes"
    )
    res_job = await registry.execute("job_parser", {"text": job_text})
    assert res_job.success is True
    assert res_job.data["title"] == "Senior Backend Engineer"
    assert any("python" in s.lower() for s in res_job.data["mandatory_skills"] + res_job.data["keywords"])

    # 3. ats_evaluator
    res_ats = await registry.execute("ats_evaluator", {
        "resume_text": resume_text,
        "job_text": job_text,
    })
    assert res_ats.success is True
    assert res_ats.data["score_name"] == "XAI-ResOpt ATS Compatibility Score"
    assert isinstance(res_ats.data["overall_score"], float)

    # 4. resume_renderer
    res_render = await registry.execute("resume_renderer", {
        "text": resume_text,
        "format": "markdown",
    })
    assert res_render.success is True
    assert "# Jane Doe" in res_render.data["rendered_text"]

    # 5. evidence_search
    fake_item = EvidenceItem(
        id=uuid4(),
        owner_id=uuid4(),
        source_type="resume",
        source_document="Resume",
        source_uri="resume.pdf",
        evidence_type="resume_statement",
        text="Built scalable microservices in Python",
        confidence=0.95,
    )
    res_search = await registry.execute(
        "evidence_search",
        {"query": "microservices"},
        context={"evidence_items": [fake_item]},
    )
    assert res_search.success is True
    assert res_search.data["count"] == 1
    assert "microservices in Python" in res_search.data["matches"][0]["text"]

    # 6. vector_search
    res_vec = await registry.execute(
        "vector_search",
        {"query": "Python microservices"},
        context={"evidence_items": [fake_item]},
    )
    assert res_vec.success is True
    assert res_vec.data["count"] == 1
    assert res_vec.data["results"][0]["similarity_score"] > 0


@pytest.mark.asyncio
async def test_tools_api_endpoint():
    import httpx
    from app.main import app

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/tools")
        assert resp.status_code == 200
        tools = resp.json()
        assert len(tools) >= 9
        names = {t["name"] for t in tools}
        assert "github_search" in names
        assert "github_repo_reader" in names
        assert "portfolio_reader" in names
        assert "resume_parser" in names
        assert "job_parser" in names
        assert "evidence_search" in names
        assert "vector_search" in names
        assert "ats_evaluator" in names
        assert "resume_renderer" in names
