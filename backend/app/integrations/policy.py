"""Platform governance, robots.txt compliance, rate limiting, and privacy scrubbing."""

from __future__ import annotations

import re
import time
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx

from app.parsing.url_safety import validate_public_url, UnsafeUrlError


class PolicyViolationError(Exception):
    """Raised when an external fetch violates platform policies or robots.txt."""
    pass


class RateLimitExceededError(PolicyViolationError):
    """Raised when an external platform API rate limit has been reached."""
    def __init__(self, message: str, retry_after_seconds: int | None = None) -> None:
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


class RobotsPolicyManager:
    """Caches and evaluates robots.txt rules for remote domains."""

    def __init__(self) -> None:
        self._cache: dict[str, tuple[RobotFileParser, float]] = {}
        self._ttl_seconds: float = 3600.0  # 1 hour cache

    async def is_allowed(
        self,
        url: str,
        user_agent: str = "XAI-ResOpt-Agent/1.0",
        timeout_seconds: float = 5.0,
    ) -> bool:
        parsed = urlparse(url)
        if not parsed.hostname:
            return False

        origin = f"{parsed.scheme}://{parsed.netloc}"
        now = time.time()

        if origin in self._cache:
            parser, timestamp = self._cache[origin]
            if now - timestamp < self._ttl_seconds:
                return parser.can_fetch(user_agent, url)

        robots_url = urljoin(origin, "/robots.txt")
        parser = RobotFileParser()
        try:
            # Enforce strict SSRF check on robots target
            validate_public_url(robots_url)
            async with httpx.AsyncClient(timeout=timeout_seconds, follow_redirects=False) as client:
                resp = await client.get(robots_url, headers={"User-Agent": user_agent})
                if resp.status_code == 200:
                    # Guard against robots.txt decompression bombs (max 128KB)
                    parser.parse(resp.text[:131072].splitlines())
                elif resp.status_code in {401, 403}:
                    # Disallow all if robots.txt is forbidden
                    parser.disallow_all = True
                else:
                    # 404 or other errors mean no robots restrictions per standard
                    parser.allow_all = True
        except UnsafeUrlError:
            # Hostile/internal address target is strictly disallowed
            parser.disallow_all = True
            self._cache[origin] = (parser, now)
            return False
        except Exception:
            # If robots.txt cannot be reached, fallback to allow per standard
            parser.allow_all = True

        self._cache[origin] = (parser, now)
        return parser.can_fetch(user_agent, url)


class RateLimitTracker:
    """Tracks platform rate limit headers (GitHub, etc.)."""

    def __init__(self) -> None:
        self.remaining: int | None = None
        self.limit: int | None = None
        self.reset_timestamp: float | None = None

    def update_from_headers(self, headers: httpx.Headers) -> None:
        remaining = headers.get("x-ratelimit-remaining")
        limit = headers.get("x-ratelimit-limit")
        reset = headers.get("x-ratelimit-reset")

        if remaining is not None:
            try:
                self.remaining = int(remaining)
            except ValueError:
                pass
        if limit is not None:
            try:
                self.limit = int(limit)
            except ValueError:
                pass
        if reset is not None:
            try:
                self.reset_timestamp = float(reset)
            except ValueError:
                pass

    def check_rate_limit(self) -> None:
        if self.remaining is not None and self.remaining <= 0 and self.reset_timestamp is not None:
            now = time.time()
            wait_seconds = max(0, int(self.reset_timestamp - now))
            if wait_seconds > 0:
                raise RateLimitExceededError(
                    f"Platform API rate limit reached. Resets in {wait_seconds} seconds.",
                    retry_after_seconds=wait_seconds,
                )


class PrivacyScrubber:
    """Redacts private credentials, tokens, secrets, and sensitive PII from extracted content."""

    _PATTERNS = [
        # AWS Access Keys
        (re.compile(r"\b(AKIA[0-9A-Z]{16})\b"), "[REDACTED_AWS_KEY]"),
        # GitHub Personal Access Tokens
        (re.compile(r"\b(gh[pousr]_[A-Za-z0-9_]{36,255})\b"), "[REDACTED_GITHUB_TOKEN]"),
        # OpenAI API Keys
        (re.compile(r"\b(sk-[A-Za-z0-9]{20,})\b"), "[REDACTED_API_KEY]"),
        # Generic Bearer Tokens
        (re.compile(r"(?i)bearer\s+[a-zA-Z0-9_\-\.]{25,}"), "Bearer [REDACTED_TOKEN]"),
        # Private RSA / SSH Keys
        (re.compile(r"-----BEGIN (?:RSA )?PRIVATE KEY-----[\s\S]*?-----END (?:RSA )?PRIVATE KEY-----"), "[REDACTED_PRIVATE_KEY]"),
        # Passwords in URLs
        (re.compile(r"://([^:]+):([^@]+)@"), r"://\1:[REDACTED_PASSWORD]@"),
    ]

    @classmethod
    def scrub(cls, text: str) -> str:
        if not text:
            return ""
        scrubbed = text
        for pattern, replacement in cls._PATTERNS:
            scrubbed = pattern.sub(replacement, scrubbed)
        return scrubbed


# Global policy instances
robots_policy = RobotsPolicyManager()
rate_limiter = RateLimitTracker()
