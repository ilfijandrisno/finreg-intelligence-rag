"""Base adapter helper utilities for HTTP requests and HTML parsing."""

import logging
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36 FinRegIntelligence/0.1"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
}


def fetch_html_content(
    url: str,
    timeout: float = 30.0,
    headers: dict[str, str] | None = None,
) -> tuple[str, str]:
    """Fetch HTML content from a URL, returning raw HTML string and final URL after redirects.

    Args:
        url: Target HTTP URL string.
        timeout: Request timeout in seconds.
        headers: Optional custom headers override.
    """
    req_headers = {**DEFAULT_HEADERS, **(headers or {})}
    with httpx.Client(timeout=timeout, follow_redirects=True, verify=False) as client:
        response = client.get(url, headers=req_headers)
        response.raise_for_status()
        return response.text, str(response.url)


def parse_html_document(html_content: str) -> BeautifulSoup:
    """Parse raw HTML string into a BeautifulSoup object."""
    return BeautifulSoup(html_content, "html.parser")


def build_absolute_url(base_url: str, relative_path: str) -> str:
    """Resolve a relative URL path against a base URL."""
    return urljoin(base_url, relative_path)
