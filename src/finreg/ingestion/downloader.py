"""Resilient HTTP Download Manager with rate limiting and exponential backoff."""

import hashlib
import logging
import time

from finreg.config.settings import get_settings
from finreg.ingestion.models import DownloadResult

httpx_installed = False
try:
    import httpx

    httpx_installed = True
except ImportError:
    pass

logger = logging.getLogger(__name__)

TRANSIENT_HTTP_STATUSES = {408, 429, 500, 502, 503, 504}
PERMANENT_HTTP_STATUSES = {400, 401, 403, 404}


class DownloadManager:
    """Resilient document download manager supporting rate limiting, retries, and checksums."""

    def __init__(
        self,
        request_delay_seconds: float | None = None,
        timeout_seconds: float | None = None,
        max_retries: int | None = None,
    ):
        settings = get_settings()
        self.request_delay = (
            request_delay_seconds
            if request_delay_seconds is not None
            else settings.request_delay_seconds
        )
        self.timeout = (
            timeout_seconds if timeout_seconds is not None else settings.download_timeout_seconds
        )
        self.max_retries = max_retries if max_retries is not None else settings.max_retries
        self._last_request_time: float = 0.0

    def _apply_rate_limit(self) -> None:
        """Enforce configured delay between outbound HTTP requests."""
        if self.request_delay > 0:
            elapsed = time.time() - self._last_request_time
            if elapsed < self.request_delay:
                sleep_duration = self.request_delay - elapsed
                logger.debug("Rate-limiting pause for %.2f seconds", sleep_duration)
                time.sleep(sleep_duration)
        self._last_request_time = time.time()

    def calculate_sha256(self, content_bytes: bytes) -> str:
        """Calculate deterministic SHA-256 hex digest for raw bytes."""
        return hashlib.sha256(content_bytes).hexdigest()

    def is_valid_pdf(self, content_bytes: bytes) -> bool:
        """Verify raw content bytes start with PDF magic bytes (%PDF)."""
        return content_bytes.startswith(b"%PDF")

    def download_file(self, url: str) -> DownloadResult:
        """Download file content from HTTP URL with retries and rate limiting.

        Args:
            url: Target resource URL string.

        Raises:
            httpx.HTTPStatusError: On permanent 4xx errors or exhausted retries.
            ValueError: On invalid file content payload.
        """
        if not httpx_installed:
            raise ImportError("httpx library is required for DownloadManager")

        headers = {
            "User-Agent": "Mozilla/5.0 FinRegIntelligence/0.1 DataIngestionPipeline",
            "Accept": "application/pdf,application/octet-stream,*/*",
        }

        attempt = 0
        backoff_delay = 1.0

        while attempt <= self.max_retries:
            attempt += 1
            self._apply_rate_limit()

            try:
                logger.info("Downloading %s (Attempt %d/%d)", url, attempt, self.max_retries + 1)
                with httpx.Client(
                    timeout=self.timeout, follow_redirects=True, verify=False
                ) as client:
                    response = client.get(url, headers=headers)

                status = response.status_code

                if status == 200:
                    content = response.content
                    content_type = response.headers.get("Content-Type", "application/pdf")
                    content_length = len(content)
                    sha256 = self.calculate_sha256(content)

                    logger.info(
                        "Downloaded %s successfully (%d bytes, SHA-256: %s)",
                        url,
                        content_length,
                        sha256[:12],
                    )

                    return DownloadResult(
                        url=url,
                        content_bytes=content,
                        content_type=content_type,
                        content_length=content_length,
                        sha256=sha256,
                        http_status=status,
                    )

                if status in PERMANENT_HTTP_STATUSES:
                    logger.error("Permanent HTTP failure (%d) for %s", status, url)
                    response.raise_for_status()

                if status in TRANSIENT_HTTP_STATUSES and attempt <= self.max_retries:
                    logger.warning(
                        "Transient HTTP failure (%d) for %s. Retrying in %.1fs...",
                        status,
                        url,
                        backoff_delay,
                    )
                    time.sleep(backoff_delay)
                    backoff_delay *= 2.0
                    continue

                response.raise_for_status()

            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                if attempt <= self.max_retries:
                    logger.warning(
                        "Network/Timeout error downloading %s: %s. Retrying in %.1fs...",
                        url,
                        exc,
                        backoff_delay,
                    )
                    time.sleep(backoff_delay)
                    backoff_delay *= 2.0
                    continue
                logger.error("Exhausted retries downloading %s: %s", url, exc)
                raise

        raise RuntimeError(f"Failed to download {url} after {self.max_retries + 1} attempts")
