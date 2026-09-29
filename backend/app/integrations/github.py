"""GitHub integration module for extracting profile metadata, repositories, READMEs, and languages."""

from __future__ import annotations

import base64
import re
from typing import Any
from urllib.parse import urlparse
from uuid import UUID, uuid4

import httpx
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.integrations.base import BaseTool, ToolResult
from app.integrations.evidence_rules import (
    MAX_SUPPORTING_CONFIDENCE,
    SUPPORTING_EVIDENCE_TYPE,
    build_supporting_evidence_item,
)
from app.integrations.policy import PrivacyScrubber, rate_limiter, RateLimitExceededError


class GitHubRepoSummary(BaseModel):
    """Structured summary of a public GitHub repository."""

    name: str
    full_name: str
    description: str | None = None
    language: str | None = None
    languages: dict[str, int] = Field(default_factory=dict)
    stars: int = 0
    forks: int = 0
    topics: list[str] = Field(default_factory=list)
    default_branch: str = "main"
    readme_text: str | None = None
    pushed_at: str | None = None
    url: str


class GitHubProfileMetadata(BaseModel):
    """Structured summary of a public GitHub user profile."""

    username: str
    name: str | None = None
    bio: str | None = None
    company: str | None = None
    location: str | None = None
    blog: str | None = None
    public_repos_count: int = 0
    followers: int = 0
    following: int = 0
    url: str
    recent_activity_summary: str | None = None
    repositories: list[GitHubRepoSummary] = Field(default_factory=list)


def clean_markdown_for_evidence(markdown_text: str) -> str:
    """Removes badges, images, raw HTML, and noise from repository READMEs."""
    if not markdown_text:
        return ""
    # Remove image links and badges: [![badge](url)](link) or ![alt](url)
    text = re.sub(r"\[!\[.*?\]\(.*?\)\]\(.*?\)", "", markdown_text)
    text = re.sub(r"!\[.*?\]\(.*?\)", "", text)
    # Remove HTML tags
    text = re.sub(r"<[^>]+>", "", text)
    # Remove excessive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return PrivacyScrubber.scrub(text.strip())


class GitHubClient:
    """Client for GitHub REST API v3 respecting rate limits and tokens."""

    BASE_URL = "https://api.github.com"

    def __init__(self, token: str | None = None, timeout_seconds: float = 10.0) -> None:
        self.token = token or get_settings().github_token
        self.timeout = timeout_seconds

    def _get_headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "XAI-ResOpt-Agent/1.0",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    async def fetch_user_profile(self, username: str) -> dict[str, Any]:
        rate_limiter.check_rate_limit()
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(f"{self.BASE_URL}/users/{username}", headers=self._get_headers())
            rate_limiter.update_from_headers(resp.headers)
            if resp.status_code == 404:
                raise ValueError(f"GitHub user '{username}' was not found.")
            if resp.status_code == 403:
                raise RateLimitExceededError("GitHub API rate limit exceeded or access forbidden.")
            resp.raise_for_status()
            return resp.json()

    async def fetch_user_repos(self, username: str, limit: int = 10) -> list[dict[str, Any]]:
        rate_limiter.check_rate_limit()
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(
                f"{self.BASE_URL}/users/{username}/repos",
                params={"sort": "updated", "per_page": min(limit, 30)},
                headers=self._get_headers(),
            )
            rate_limiter.update_from_headers(resp.headers)
            if resp.status_code == 403:
                raise RateLimitExceededError("GitHub API rate limit exceeded.")
            resp.raise_for_status()
            return resp.json()

    async def fetch_repo_details(self, owner: str, repo: str) -> dict[str, Any]:
        rate_limiter.check_rate_limit()
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(f"{self.BASE_URL}/repos/{owner}/{repo}", headers=self._get_headers())
            rate_limiter.update_from_headers(resp.headers)
            if resp.status_code == 404:
                raise ValueError(f"Repository '{owner}/{repo}' was not found.")
            resp.raise_for_status()
            return resp.json()

    async def fetch_repo_languages(self, owner: str, repo: str) -> dict[str, int]:
        rate_limiter.check_rate_limit()
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(f"{self.BASE_URL}/repos/{owner}/{repo}/languages", headers=self._get_headers())
            rate_limiter.update_from_headers(resp.headers)
            if resp.status_code == 200:
                return resp.json()
            return {}

    async def fetch_repo_readme(self, owner: str, repo: str) -> str | None:
        rate_limiter.check_rate_limit()
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(f"{self.BASE_URL}/repos/{owner}/{repo}/readme", headers=self._get_headers())
            rate_limiter.update_from_headers(resp.headers)
            if resp.status_code == 200:
                data = resp.json()
                content_base64 = data.get("content", "")
                if content_base64:
                    try:
                        raw_bytes = base64.b64decode(content_base64)
                        return clean_markdown_for_evidence(raw_bytes.decode("utf-8", errors="ignore"))
                    except Exception:
                        return None
            return None

    async def fetch_user_events(self, username: str) -> list[dict[str, Any]]:
        rate_limiter.check_rate_limit()
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(
                    f"{self.BASE_URL}/users/{username}/events/public",
                    params={"per_page": 10},
                    headers=self._get_headers(),
                )
                rate_limiter.update_from_headers(resp.headers)
                if resp.status_code == 200:
                    return resp.json()
        except Exception:
            pass
        return []

    async def search_repositories(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        rate_limiter.check_rate_limit()
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(
                f"{self.BASE_URL}/search/repositories",
                params={"q": query, "per_page": min(limit, 10)},
                headers=self._get_headers(),
            )
            rate_limiter.update_from_headers(resp.headers)
            if resp.status_code == 200:
                return resp.json().get("items", [])
            return []


def parse_github_url(url: str) -> tuple[str, str | None]:
    """Parses a GitHub URL into (username, repo_name or None)."""
    parsed = urlparse(url)
    parts = [p for p in parsed.path.strip("/").split("/") if p]
    if not parts:
        raise ValueError("Invalid GitHub URL: no username detected.")
    username = parts[0]
    repo = parts[1] if len(parts) > 1 else None
    return username, repo


async def extract_github_evidence(
    url: str,
    owner_id: UUID,
    client: GitHubClient | None = None,
) -> tuple[GitHubProfileMetadata, list[Any]]:
    """Extracts complete GitHub profile metadata, repositories, and supporting evidence records."""
    gh = client or GitHubClient()
    username, specific_repo = parse_github_url(url)

    if specific_repo:
        # User supplied a specific repository URL
        repo_data = await gh.fetch_repo_details(username, specific_repo)
        languages = await gh.fetch_repo_languages(username, specific_repo)
        readme = await gh.fetch_repo_readme(username, specific_repo)
        repo_summary = GitHubRepoSummary(
            name=repo_data.get("name", specific_repo),
            full_name=repo_data.get("full_name", f"{username}/{specific_repo}"),
            description=repo_data.get("description"),
            language=repo_data.get("language"),
            languages=languages,
            stars=repo_data.get("stargazers_count", 0),
            forks=repo_data.get("forks_count", 0),
            topics=repo_data.get("topics", []),
            default_branch=repo_data.get("default_branch", "main"),
            readme_text=readme,
            pushed_at=repo_data.get("pushed_at"),
            url=repo_data.get("html_url", url),
        )
        metadata = GitHubProfileMetadata(
            username=username,
            url=f"https://github.com/{username}",
            public_repos_count=1,
            repositories=[repo_summary],
        )
    else:
        # User supplied a profile URL
        profile_data = await gh.fetch_user_profile(username)
        raw_repos = await gh.fetch_user_repos(username, limit=6)
        events = await gh.fetch_user_events(username)

        # Summarize public activity
        activity_types = [e.get("type", "").replace("Event", "") for e in events if e.get("type")]
        activity_summary = f"Recent activities: {', '.join(set(activity_types))}" if activity_types else "Active public contributor"

        repos: list[GitHubRepoSummary] = []
        for r in raw_repos:
            repo_name = r.get("name", "")
            langs = await gh.fetch_repo_languages(username, repo_name)
            # Only fetch README for top 3 repos to conserve calls
            readme = await gh.fetch_repo_readme(username, repo_name) if len(repos) < 3 else None
            repos.append(
                GitHubRepoSummary(
                    name=repo_name,
                    full_name=r.get("full_name", f"{username}/{repo_name}"),
                    description=r.get("description"),
                    language=r.get("language"),
                    languages=langs,
                    stars=r.get("stargazers_count", 0),
                    forks=r.get("forks_count", 0),
                    topics=r.get("topics", []),
                    default_branch=r.get("default_branch", "main"),
                    readme_text=readme,
                    pushed_at=r.get("pushed_at"),
                    url=r.get("html_url", ""),
                )
            )

        metadata = GitHubProfileMetadata(
            username=username,
            name=profile_data.get("name"),
            bio=profile_data.get("bio"),
            company=profile_data.get("company"),
            location=profile_data.get("location"),
            blog=profile_data.get("blog"),
            public_repos_count=profile_data.get("public_repos", len(repos)),
            followers=profile_data.get("followers", 0),
            following=profile_data.get("following", 0),
            url=profile_data.get("html_url", url),
            recent_activity_summary=activity_summary,
            repositories=repos,
        )

    # Build supporting evidence items
    evidence_items = []

    # 1. Profile metadata evidence
    if metadata.bio or metadata.company:
        bio_text = f"GitHub Profile: @{metadata.username}. "
        if metadata.name:
            bio_text += f"Name: {metadata.name}. "
        if metadata.company:
            bio_text += f"Company/Org: {metadata.company}. "
        if metadata.bio:
            bio_text += f"Bio: {metadata.bio}. "
        if metadata.recent_activity_summary:
            bio_text += f"Activity: {metadata.recent_activity_summary}."

        evidence_items.append(
            build_supporting_evidence_item(
                owner_id=owner_id,
                source_type="github",
                source_uri=metadata.url,
                source_document="GitHub Profile",
                source_location=f"github:@{metadata.username}",
                raw_text=bio_text,
                confidence=0.65,
            )
        )

    # 2. Repository & README evidence items
    for repo in metadata.repositories:
        desc_snippet = repo.description or "Public codebase repository"
        lang_str = f"Primary Language: {repo.language}" if repo.language else ""
        if repo.languages:
            top_langs = ", ".join(list(repo.languages.keys())[:3])
            lang_str += f" (Languages used: {top_langs})"

        repo_text = f"Repository {repo.full_name}: {desc_snippet}. {lang_str}. Stars: {repo.stars}."
        if repo.topics:
            repo_text += f" Topics: {', '.join(repo.topics)}."

        evidence_items.append(
            build_supporting_evidence_item(
                owner_id=owner_id,
                source_type="github",
                source_uri=repo.url,
                source_document=f"GitHub Repo: {repo.name}",
                source_location=f"github:{repo.full_name}#metadata",
                raw_text=repo_text,
                confidence=0.70,
            )
        )

        # Include README excerpt if available
        if repo.readme_text:
            excerpt = repo.readme_text[:1200]
            evidence_items.append(
                build_supporting_evidence_item(
                    owner_id=owner_id,
                    source_type="github",
                    source_uri=repo.url,
                    source_document=f"GitHub Repo: {repo.name} README",
                    source_location=f"github:{repo.full_name}#readme",
                    raw_text=f"README for {repo.name}:\n{excerpt}",
                    confidence=0.68,
                )
            )

    return metadata, evidence_items


# ==============================================================================
# Modular Tools: github_search and github_repo_reader
# ==============================================================================

class GitHubSearchTool(BaseTool):
    """Modular tool to search public GitHub repositories and topics."""

    name = "github_search"
    description = "Searches public GitHub repositories and topic keywords for candidate projects and technical evidence."
    parameters_schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "The search term, repository name, or technology query."},
            "limit": {"type": "integer", "description": "Maximum number of repository matches (1 to 10).", "default": 5},
        },
        "required": ["query"],
    }

    def __init__(self, client: GitHubClient | None = None) -> None:
        self.client = client or GitHubClient()

    async def execute(self, params: dict[str, Any], context: dict[str, Any] | None = None) -> ToolResult:
        query = params.get("query", "").strip()
        limit = params.get("limit", 5)
        if not query:
            return ToolResult.fail("Parameter 'query' must not be empty.")

        try:
            items = await self.client.search_repositories(query, limit)
            summaries = [
                {
                    "name": item.get("name"),
                    "full_name": item.get("full_name"),
                    "description": item.get("description"),
                    "language": item.get("language"),
                    "stars": item.get("stargazers_count", 0),
                    "url": item.get("html_url"),
                }
                for item in items
            ]
            return ToolResult.ok(
                data={"query": query, "count": len(summaries), "repositories": summaries},
                provenance={"source": "api.github.com/search/repositories", "is_supporting_only": True},
            )
        except Exception as error:
            return ToolResult.fail(f"GitHub search failed: {error}")


class GitHubRepoReaderTool(BaseTool):
    """Modular tool to read details, README, and language metrics of a specific GitHub repository."""

    name = "github_repo_reader"
    description = "Fetches comprehensive details, README documentation, and language metrics for a specified GitHub repository."
    parameters_schema = {
        "type": "object",
        "properties": {
            "owner": {"type": "string", "description": "GitHub repository owner username or organization."},
            "repo": {"type": "string", "description": "Repository name."},
        },
        "required": ["owner", "repo"],
    }

    def __init__(self, client: GitHubClient | None = None) -> None:
        self.client = client or GitHubClient()

    async def execute(self, params: dict[str, Any], context: dict[str, Any] | None = None) -> ToolResult:
        owner = params.get("owner", "").strip()
        repo = params.get("repo", "").strip()
        if not owner or not repo:
            return ToolResult.fail("Both 'owner' and 'repo' parameters are required.")

        try:
            details = await self.client.fetch_repo_details(owner, repo)
            languages = await self.client.fetch_repo_languages(owner, repo)
            readme = await self.client.fetch_repo_readme(owner, repo)

            result = {
                "owner": owner,
                "repo": repo,
                "full_name": details.get("full_name"),
                "description": details.get("description"),
                "primary_language": details.get("language"),
                "languages": languages,
                "stars": details.get("stargazers_count", 0),
                "forks": details.get("forks_count", 0),
                "topics": details.get("topics", []),
                "readme_snippet": readme[:2000] if readme else None,
                "url": details.get("html_url"),
            }
            return ToolResult.ok(
                data=result,
                provenance={"source": f"github.com/{owner}/{repo}", "is_supporting_only": True},
            )
        except Exception as error:
            return ToolResult.fail(f"Failed to read repository {owner}/{repo}: {error}")
