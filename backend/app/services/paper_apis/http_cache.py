"""Synchronous HTTP JSON cache for paper API clients."""

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Dict, Optional
from urllib.parse import urlencode, urlparse

import requests
from loguru import logger

_LAST_REQUEST_AT = {}


def _default_cache_dir() -> Path:
    """Return the default backend-local API cache directory."""
    return Path(__file__).resolve().parents[3] / "data" / "cache" / "api"


def _resolve_cache_dir(cache_dir=None) -> Path:
    """Resolve and create the cache directory."""
    directory = Path(cache_dir or os.getenv("PIPELINE_API_CACHE_DIR") or _default_cache_dir())
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def cache_path(url: str, params: Optional[Dict] = None, cache_dir=None) -> Path:
    """Return the cache file path for a URL and query parameters."""
    params = params or {}
    query = urlencode(sorted(params.items()))
    key = hashlib.sha256(f"{url}?{query}".encode("utf-8")).hexdigest()
    return _resolve_cache_dir(cache_dir) / f"{key}.json"


def clear_cache(cache_dir=None) -> int:
    """Remove cached API JSON files and return the number deleted."""
    directory = _resolve_cache_dir(cache_dir)
    deleted = 0
    for path in directory.glob("*.json"):
        if path.is_file():
            path.unlink()
            deleted += 1
    return deleted


def _rate_limit(host: str, min_interval: float) -> None:
    """Sleep as needed to keep requests to a host spaced apart."""
    if min_interval <= 0:
        return

    now = time.time()
    last_request_at = _LAST_REQUEST_AT.get(host)
    if last_request_at is not None:
        wait_seconds = min_interval - (now - last_request_at)
        if wait_seconds > 0:
            logger.debug(f"Rate limiting {host}: sleeping {wait_seconds:.2f}s")
            time.sleep(wait_seconds)
    _LAST_REQUEST_AT[host] = time.time()


def get_json(
    url: str,
    params: Optional[Dict] = None,
    headers: Optional[Dict] = None,
    cache_dir=None,
    ttl_seconds: int = 2592000,
    min_interval: float = 1.0,
    max_retries: int = 4,
    timeout: float = 30.0,
) -> Optional[dict]:
    """Fetch JSON with disk caching, per-host rate limiting, and retry backoff."""
    params = params or {}
    path = cache_path(url, params, cache_dir)

    if path.exists():
        try:
            cached = json.loads(path.read_text(encoding="utf-8"))
            cached_at = cached.get("cached_at", 0)
            if time.time() - cached_at <= ttl_seconds:
                logger.debug(f"Using cached API response for {url}")
                return cached.get("body")
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning(f"Failed to read API cache {path}: {exc}")

    host = urlparse(url).netloc

    for attempt in range(max_retries + 1):
        _rate_limit(host, min_interval)
        try:
            response = requests.get(url, params=params, headers=headers, timeout=timeout)
        except requests.RequestException as exc:
            logger.warning(f"HTTP request failed for {url}: {exc}")
            return None

        if response.status_code == 200:
            try:
                body = response.json()
            except ValueError as exc:
                logger.warning(f"Failed to parse JSON from {url}: {exc}")
                return None

            payload = {
                "cached_at": time.time(),
                "url": url,
                "params": params,
                "body": body,
            }
            try:
                path.write_text(json.dumps(payload), encoding="utf-8")
            except OSError as exc:
                logger.warning(f"Failed to write API cache {path}: {exc}")
            return body

        if response.status_code == 429 or response.status_code >= 500:
            if attempt >= max_retries:
                logger.warning(f"HTTP {response.status_code} from {url} after retries")
                return None
            sleep_seconds = min(2 ** attempt, 30)
            logger.warning(
                f"HTTP {response.status_code} from {url}; retrying in {sleep_seconds}s"
            )
            time.sleep(sleep_seconds)
            continue

        logger.warning(f"HTTP {response.status_code} from {url}; not caching response")
        return None

    return None


if __name__ == "__main__":
    data = get_json("https://api.openalex.org/works?search=forensics&per-page=1")
    results = data.get("results", []) if data else []
    print(f"OpenAlex results: {len(results)}")
