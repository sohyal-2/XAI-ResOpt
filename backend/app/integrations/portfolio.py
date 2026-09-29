"""Portfolio reader module for extracting project, experience, and supporting evidence records."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse
from uuid import UUID

from bs4 import BeautifulSoup
import httpx
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.integrations.base import BaseTool, ToolResult
from app.integrations.evidence_rules import build_supporting_evidence_item
from app.integrations.policy import PrivacyScrubber, robots_policy, PolicyViolationError
from app.parsing.url_safety import validate_public_url, UnsafeUrlError, MAX_PUBLIC_PAGE_BYTES
from app.parsing.validation import IngestionError


class PortfolioProject(BaseModel):
    """Structured portfolio project item."""

    title: str
    description: str
    technologies: list[str] = Field(default_factory=list)
    link: str | None = None


class PortfolioExperience(BaseModel):
    """Structured portfolio experience item."""

    role: str
    organization: str | None = None
    dates: str | None = None
    summary: str


class PortfolioExtractionResult(BaseModel):
    """Normalized extraction from a personal or professional portfolio URL."""

    url: str
    title: str | None = None
    about_text: str | None = None
    projects: list[PortfolioProject] = Field(default_factory=list)
    experience: list[PortfolioExperience] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    raw_text: str


async def fetch_portfolio_html(url: str, timeout_seconds: float = 10.0) -> tuple[str, str | None]:
    """Safely fetches public portfolio page HTML, enforcing SSRF validation and robots.txt."""
    parsed = validate_public_url(url)
    clean_url = str(parsed)

    # Check robots.txt compliance
    allowed = await robots_policy.is_allowed(clean_url, timeout_seconds=min(5.0, timeout_seconds))
    if not allowed:
        raise PolicyViolationError(f"Crawling is disallowed by robots.txt for domain {parsed.hostname}.")

    try:
        async with httpx.AsyncClient(
            timeout=timeout_seconds,
            follow_redirects=False,
            headers={"User-Agent": "XAI-ResOpt-Agent/1.0"},
        ) as client:
            async with client.stream("GET", clean_url) as stream_resp:
                if stream_resp.is_redirect:
                    raise UnsafeUrlError("Redirects are not followed automatically; submit the canonical URL.")
                stream_resp.raise_for_status()
                content_type = stream_resp.headers.get("content-type", "")
                if "text/html" not in content_type and "text/plain" not in content_type:
                    raise IngestionError("The URL does not return HTML or plain text.")

                body_chunks = []
                total_bytes = 0
                async for chunk in stream_resp.aiter_bytes(chunk_size=65536):
                    total_bytes += len(chunk)
                    if total_bytes > MAX_PUBLIC_PAGE_BYTES:
                        raise IngestionError(f"Remote document exceeds maximum allowed size of {MAX_PUBLIC_PAGE_BYTES} bytes.")
                    body_chunks.append(chunk)

                full_body = b"".join(body_chunks).decode("utf-8", errors="replace")
                return full_body, clean_url
    except (httpx.TimeoutException, httpx.RequestError) as error:
        raise IngestionError("Portfolio URL could not be retrieved within timeout.") from error
    except httpx.HTTPStatusError as error:
        raise IngestionError(f"Portfolio URL returned HTTP {error.response.status_code}.") from error


def parse_portfolio_content(html: str, url: str) -> PortfolioExtractionResult:
    """Parses portfolio HTML into structured project, experience, and skill evidence."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg", "header", "footer", "nav"]):
        tag.decompose()

    page_title = soup.title.get_text(strip=True) if soup.title else None

    # Detect project elements
    projects: list[PortfolioProject] = []
    experience: list[PortfolioExperience] = []
    skills: list[str] = []

    # Common project card identifiers
    project_candidates = soup.find_all(
        lambda tag: tag.name in ["article", "div", "section", "li"]
        and any(k in " ".join(tag.get("class", [])).lower() for k in ["project", "portfolio-item", "work-item", "case-study"])
    )

    for item in project_candidates[:12]:
        h_tag = item.find(["h2", "h3", "h4", "h5"])
        title = h_tag.get_text(strip=True) if h_tag else None
        p_tag = item.find("p")
        desc = p_tag.get_text(strip=True) if p_tag else item.get_text(strip=True)[:300]
        a_tag = item.find("a", href=True)
        link = a_tag["href"] if a_tag else None

        if title and len(title) > 2 and len(desc) > 10:
            # Look for tech badges/tags
            tech_tags = [
                t.get_text(strip=True)
                for t in item.find_all(lambda el: el.name in ["span", "badge", "li"] and len(el.get_text(strip=True)) < 25)
            ]
            projects.append(
                PortfolioProject(
                    title=PrivacyScrubber.scrub(title),
                    description=PrivacyScrubber.scrub(desc[:500]),
                    technologies=tech_tags[:6],
                    link=link,
                )
            )

    # Detect general text
    full_text = "\n".join(line.strip() for line in soup.get_text("\n").splitlines() if line.strip())
    scrubbed_text = PrivacyScrubber.scrub(full_text)

    # If no structured projects were identified by class, fall back to heading-based grouping
    if not projects:
        for heading in soup.find_all(["h2", "h3", "h4"]):
            h_text = heading.get_text(strip=True)
            if any(k in h_text.lower() for k in ["project", "work", "built", "featured"]):
                sibling = heading.find_next_sibling(["p", "ul", "div"])
                if sibling:
                    s_text = sibling.get_text(strip=True)
                    if len(s_text) > 15:
                        projects.append(
                            PortfolioProject(
                                title=PrivacyScrubber.scrub(h_text),
                                description=PrivacyScrubber.scrub(s_text[:400]),
                            )
                        )

    return PortfolioExtractionResult(
        url=url,
        title=page_title,
        projects=projects,
        experience=experience,
        skills=skills,
        raw_text=scrubbed_text,
    )


async def extract_portfolio_evidence(
    url: str,
    owner_id: UUID,
    timeout_seconds: float = 10.0,
) -> tuple[PortfolioExtractionResult, list[Any]]:
    """Extracts portfolio projects and creates supporting evidence records."""
    html, clean_url = await fetch_portfolio_html(url, timeout_seconds=timeout_seconds)
    result = parse_portfolio_content(html, clean_url)

    evidence_items = []
    domain = urlparse(clean_url).hostname or "Portfolio"
    doc_name = f"Portfolio: {result.title or domain}"

    # 1. Project-specific supporting evidence items
    for p in result.projects:
        tech_str = f" Technologies: {', '.join(p.technologies)}." if p.technologies else ""
        link_str = f" Link: {p.link}." if p.link else ""
        text = f"Project: {p.title}. Description: {p.description}.{tech_str}{link_str}"

        evidence_items.append(
            build_supporting_evidence_item(
                owner_id=owner_id,
                source_type="portfolio",
                source_uri=clean_url,
                source_document=doc_name,
                source_location=f"portfolio:{p.title}",
                raw_text=text,
                confidence=0.68,
            )
        )

    # 2. General page overview supporting evidence item
    overview_snippet = result.raw_text[:1200]
    if overview_snippet:
        evidence_items.append(
            build_supporting_evidence_item(
                owner_id=owner_id,
                source_type="portfolio",
                source_uri=clean_url,
                source_document=doc_name,
                source_location="portfolio:overview",
                raw_text=f"Portfolio summary from {clean_url}:\n{overview_snippet}",
                confidence=0.62,
            )
        )

    return result, evidence_items


# ==============================================================================
# Modular Tool: portfolio_reader
# ==============================================================================

class PortfolioReaderTool(BaseTool):
    """Modular tool to read and extract project and experience information from a portfolio URL."""

    name = "portfolio_reader"
    description = "Fetches a public personal or portfolio website, extracting structured project descriptions, technologies, and supporting evidence."
    parameters_schema = {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "The public HTTP/HTTPS URL of the portfolio page."},
            "timeout_seconds": {"type": "number", "description": "Fetch timeout in seconds.", "default": 10.0},
        },
        "required": ["url"],
    }

    async def execute(self, params: dict[str, Any], context: dict[str, Any] | None = None) -> ToolResult:
        url = params.get("url", "").strip()
        timeout = float(params.get("timeout_seconds", 10.0))
        if not url:
            return ToolResult.fail("Parameter 'url' is required.")

        try:
            html, clean_url = await fetch_portfolio_html(url, timeout_seconds=timeout)
            result = parse_portfolio_content(html, clean_url)
            return ToolResult.ok(
                data={
                    "url": clean_url,
                    "title": result.title,
                    "projects_found": len(result.projects),
                    "projects": [p.model_dump() for p in result.projects],
                    "raw_text_length": len(result.raw_text),
                },
                provenance={"source": clean_url, "is_supporting_only": True},
            )
        except Exception as error:
            return ToolResult.fail(f"Failed to read portfolio URL: {error}")
