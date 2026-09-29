import ipaddress
import re
import socket
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from app.parsing.models import ExtractedItem, ExternalContentExtraction
from app.parsing.validation import IngestionError

MAX_PUBLIC_PAGE_BYTES = 5 * 1024 * 1024  # 5 MB maximum response size to prevent streaming bombs

CLOUD_METADATA_IPS = {
    "169.254.169.254",  # AWS/Azure/GCP link-local metadata
    "169.254.169.253",  # AWS DNS
    "100.100.100.200",  # Alibaba Cloud metadata
    "fd00:ec2::254",     # AWS IPv6 metadata
}

CLOUD_METADATA_HOSTS = {
    "metadata.google.internal",
    "metadata",
    "instance-data",
}


class UnsafeUrlError(IngestionError):
    pass


async def fetch_public_url(url: str, timeout_seconds: float) -> ExternalContentExtraction:
    parsed = validate_public_url(url)
    clean_url = str(parsed.geturl())
    try:
        async with httpx.AsyncClient(
            timeout=timeout_seconds,
            follow_redirects=False,
            headers={"User-Agent": "XAI-ResOpt-ingestion/1.0"},
        ) as client:
            # Stream response to strictly enforce maximum size limit
            async with client.stream("GET", clean_url) as response:
                if response.is_redirect:
                    location = response.headers.get("location")
                    if not location:
                        raise UnsafeUrlError("The remote server returned an invalid redirect.")
                    validate_public_url(urljoin(clean_url, location))
                    raise UnsafeUrlError("Redirects are not followed automatically; submit the final public URL.")
                response.raise_for_status()

                content_type = response.headers.get("content-type", "")
                if "text/html" not in content_type and "text/plain" not in content_type:
                    raise IngestionError("The URL did not return readable text content.")

                chunks = []
                total_bytes = 0
                async for chunk in response.aiter_bytes():
                    chunks.append(chunk)
                    total_bytes += len(chunk)
                    if total_bytes > MAX_PUBLIC_PAGE_BYTES:
                        raise IngestionError("The remote page exceeds the 5 MB download limit.")

                body_bytes = b"".join(chunks)
                body_text = body_bytes.decode(response.encoding or "utf-8", errors="replace")

    except (httpx.TimeoutException, httpx.RequestError) as error:
        raise IngestionError("The URL could not be fetched within the configured timeout.") from error
    except httpx.HTTPStatusError as error:
        raise IngestionError(f"The URL returned HTTP {error.response.status_code}.") from error

    soup = BeautifulSoup(body_text, "html.parser")
    for element in soup(["script", "style", "noscript", "svg"]):
        element.decompose()
    text = "\n".join(line.strip() for line in soup.get_text("\n").splitlines() if line.strip())
    if not text:
        raise IngestionError("The URL returned no readable text.")
    title = soup.title.get_text(strip=True) if soup.title else None
    items = [ExtractedItem(type="external_content", text=text[:5000], source=clean_url, location="Public page text", confidence=0.70)]
    return ExternalContentExtraction(source=parsed, title=title, text=text, items=items)


def validate_public_url(url: str):
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise UnsafeUrlError("Only public HTTP and HTTPS schemes are permitted.")
    if parsed.username or parsed.password or not parsed.hostname:
        raise UnsafeUrlError("Only public HTTP(S) URLs without credentials are allowed.")
    if parsed.port not in {None, 80, 443}:
        raise UnsafeUrlError("Non-standard URL ports are not allowed.")

    host = parsed.hostname.rstrip(".").lower()

    # Block metadata hosts
    if host in CLOUD_METADATA_HOSTS or host.endswith(".internal"):
        raise UnsafeUrlError("Access to internal metadata service hostnames is forbidden.")

    # Block local domains
    if host in {"localhost", "localhost.localdomain"} or host.endswith(".local"):
        raise UnsafeUrlError("Local network hosts are not allowed.")

    # Block octal / hex / integer IP bypass tricks (e.g. 0177.0.0.1, 0x7f000001, 2130706433)
    if re.match(r"^(0[xX][0-9a-fA-F]+|[0-9]+)$", host):
        raise UnsafeUrlError("Integer or hexadecimal IP representations are not allowed.")
    if re.match(r"^0[0-7]+\.", host) or ".0" in host:
        # Check for leading zero octal components
        parts = host.split(".")
        if any(p.startswith("0") and len(p) > 1 and p.isdigit() for p in parts):
            raise UnsafeUrlError("Octal IP representations are not allowed.")

    try:
        records = socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM)
        addresses = list({record[4][0] for record in records})
    except (socket.gaierror, OSError) as error:
        raise UnsafeUrlError("The URL host could not be resolved.") from error

    if not addresses:
        raise UnsafeUrlError("Could not resolve IP addresses for host.")

    for address in addresses:
        if address in CLOUD_METADATA_IPS:
            raise UnsafeUrlError("Access to cloud metadata endpoints is strictly forbidden.")
        if _is_private_address(address):
            raise UnsafeUrlError("Private and loopback network addresses are not allowed.")

    return parsed


def _is_private_address(address: str) -> bool:
    ip = ipaddress.ip_address(address)
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )
