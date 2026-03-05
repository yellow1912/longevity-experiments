"""
Fetcher Abstraction Layer
Pluggable fetcher backends with retry logic, exponential backoff, and proxy support.
"""
import time
from abc import ABC, abstractmethod
from scrapling import StealthyFetcher
from .config import SCRAPING_SETTINGS


class FetchError(Exception):
    """Raised when all retry attempts are exhausted."""
    pass


class BaseFetcher(ABC):
    """Abstract base class for fetcher backends."""

    def __init__(self, proxy=None, retry_attempts=None, backoff_base=None):
        self.proxy = proxy
        self.retry_attempts = retry_attempts or SCRAPING_SETTINGS["retry_attempts"]
        self.backoff_base = backoff_base or SCRAPING_SETTINGS["backoff_base"]

    def fetch(self, url, **kwargs):
        """
        Fetch URL with retry and exponential backoff.

        Raises:
            FetchError: After exhausting all retry attempts.
        """
        last_error = None
        for attempt in range(self.retry_attempts):
            try:
                return self._fetch(url, **kwargs)
            except Exception as e:
                last_error = e
                if attempt < self.retry_attempts - 1:
                    wait = self.backoff_base * (2 ** attempt)
                    print(f"    Fetch failed (attempt {attempt + 1}/{self.retry_attempts}): {str(e)[:100]}")
                    print(f"    Retrying in {wait}s...")
                    time.sleep(wait)
        raise FetchError(
            f"Failed after {self.retry_attempts} attempts: {last_error}"
        )

    @abstractmethod
    def _fetch(self, url, **kwargs):
        """Subclasses implement actual fetch logic."""
        pass


class StealthyFetcherBackend(BaseFetcher):
    """Fetcher backend using scrapling's StealthyFetcher."""

    def _fetch(self, url, **kwargs):
        fetch_kwargs = {
            "headless": True,
            "network_idle": True,
            "block_webrtc": True,
            "google_search": True,
            "timeout": SCRAPING_SETTINGS["page_load_timeout"] * 1000,
        }
        if self.proxy:
            fetch_kwargs["proxy"] = self.proxy
        fetch_kwargs.update(kwargs)
        response = StealthyFetcher.fetch(url, **fetch_kwargs)
        if response.status >= 400:
            raise Exception(f"HTTP {response.status} for {url}")
        # Detect CAPTCHA pages (200 status but no real content)
        html = str(response.html_content) if hasattr(response, 'html_content') else ''
        if 'captcha' in html.lower() and 'productTitle' not in html:
            raise Exception(f"CAPTCHA detected for {url}")
        return response


FETCHER_BACKENDS = {
    "stealthy": StealthyFetcherBackend,
}


def create_fetcher(backend=None, proxy=None, retry_attempts=None, backoff_base=None):
    """
    Factory function to create a fetcher instance.

    Args:
        backend: Name of fetcher backend (default: config value)
        proxy: Proxy URL string
        retry_attempts: Number of retry attempts
        backoff_base: Base seconds for exponential backoff
    """
    backend = backend or SCRAPING_SETTINGS["fetcher_backend"]
    if backend not in FETCHER_BACKENDS:
        raise ValueError(
            f"Unknown fetcher backend '{backend}'. "
            f"Available: {', '.join(FETCHER_BACKENDS.keys())}"
        )
    cls = FETCHER_BACKENDS[backend]
    return cls(proxy=proxy, retry_attempts=retry_attempts, backoff_base=backoff_base)
