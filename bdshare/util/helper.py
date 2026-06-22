"""
bdshare.util.helper
~~~~~~~~~~~~~~~~~~~
Shared HTTP session, fetch helpers, numeric conversion, and exceptions
used across all bdshare sub-modules (trading, market, news).

Import surface expected by other modules:
    from bdshare.util.helper import (
        _fetch_table, _safe_num, _parse_html,
        safe_get, safe_post,
        BDShareError, _session, deprecated,
    )
"""

import time
import logging
import warnings
from functools import wraps
from typing import Any, Dict, Optional

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Custom exception
# ---------------------------------------------------------------------------

class BDShareError(Exception):
    """Raised whenever a DSE scraping or network operation fails."""


# ---------------------------------------------------------------------------
# Deprecation decorator
# ---------------------------------------------------------------------------

def deprecated(message: str):
    """Mark a function as deprecated; emits DeprecationWarning on every call."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            warnings.warn(
                f"{func.__name__} is deprecated: {message}",
                DeprecationWarning,
                stacklevel=2,
            )
            return func(*args, **kwargs)
        return wrapper
    return decorator


# ---------------------------------------------------------------------------
# Shared HTTP session
# ---------------------------------------------------------------------------

# One session for the entire process lifetime — reuses TCP connections and
# centralises headers/cookies so sub-modules don't each manage them.
_session = requests.Session()
_session.headers.update({
    "User-Agent":      "bdshare/2.0 (https://github.com/bdshare/bdshare)",
    "Accept-Encoding": "gzip, deflate",
    "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
})


# ---------------------------------------------------------------------------
# HTML parsing helper
# ---------------------------------------------------------------------------

def _parse_html(content: bytes) -> BeautifulSoup:
    """Parse HTML bytes with lxml (fast), falling back to html.parser."""
    try:
        return BeautifulSoup(content, "lxml")
    except Exception:
        return BeautifulSoup(content, "html.parser")


# ---------------------------------------------------------------------------
# Low-level GET helper
# ---------------------------------------------------------------------------

def safe_get(
    url: str,
    params: Optional[Dict] = None,
    alt_url: Optional[str] = None,
    retries: int = 3,
    pause: float = 0.2,
    timeout: int = 10,
) -> requests.Response:
    """
    Fetch a URL via GET with retries, an optional fallback URL, and
    exponential back-off between attempts.

    Strategy per attempt:
      1. Try the primary ``url``.
      2. If status is not 200 *or* an exception is raised, try ``alt_url``
         (when provided) before moving to the next attempt.
      3. Sleep for ``pause * 2^(attempt-1)`` seconds before each retry
         (no sleep before the first attempt).

    :param url:      Primary URL to fetch.
    :param params:   Optional query-string parameters dict.
    :param alt_url:  Fallback URL tried within the same attempt.
    :param retries:  Total number of attempts.
    :param pause:    Base pause in seconds (doubles each retry).
    :param timeout:  Per-request socket timeout in seconds.
    :returns:        The first successful :class:`requests.Response`.
    :raises BDShareError: After all retries are exhausted without success.
    """
    return _request("GET", url, alt_url=alt_url, params=params,
                    retries=retries, pause=pause, timeout=timeout)


# ---------------------------------------------------------------------------
# Low-level POST helper
# ---------------------------------------------------------------------------

def safe_post(
    url: str,
    data: Optional[Dict] = None,
    alt_url: Optional[str] = None,
    retries: int = 3,
    pause: float = 0.2,
    timeout: int = 10,
) -> requests.Response:
    """
    POST to a URL with retries, an optional fallback URL, and exponential
    back-off between attempts. Mirrors :func:`safe_get` for POST requests.

    :param url:      Primary URL.
    :param data:     Form-encoded POST body dict.
    :param alt_url:  Fallback URL tried within the same attempt.
    :param retries:  Total number of attempts.
    :param pause:    Base pause in seconds (doubles each retry).
    :param timeout:  Per-request socket timeout in seconds.
    :returns:        The first successful :class:`requests.Response`.
    :raises BDShareError: After all retries are exhausted without success.
    """
    return _request("POST", url, alt_url=alt_url, data=data,
                    retries=retries, pause=pause, timeout=timeout)


# ---------------------------------------------------------------------------
# Shared retry engine (used by safe_get and safe_post)
# ---------------------------------------------------------------------------

def _request(
    method: str,
    url: str,
    alt_url: Optional[str] = None,
    params: Optional[Dict] = None,
    data: Optional[Dict] = None,
    retries: int = 3,
    pause: float = 0.2,
    timeout: int = 10,
) -> requests.Response:
    urls = [u for u in (url, alt_url) if u]
    last_exc: Optional[Exception] = None

    for attempt in range(retries):
        if attempt:
            time.sleep(pause * (2 ** (attempt - 1)))  # exponential back-off on retries only

        for target in urls:
            try:
                r = _session.request(
                    method, target, params=params, data=data, timeout=timeout
                )
                if r.status_code == 200:
                    return r
                logger.warning(
                    "HTTP %s from %s (attempt %d/%d)",
                    r.status_code, target, attempt + 1, retries,
                )
            except requests.RequestException as exc:
                last_exc = exc
                logger.error(
                    "Request error on %s (attempt %d/%d): %s",
                    target, attempt + 1, retries, exc,
                )

    raise BDShareError(
        f"Failed to {method} after {retries} retries. "
        f"URLs tried: {urls}. "
        f"Last error: {last_exc}"
    )


# ---------------------------------------------------------------------------
# Table fetch helper
# ---------------------------------------------------------------------------

def _fetch_table(
    url: str,
    alt_url: Optional[str] = None,
    params: Optional[Dict] = None,
    retries: int = 3,
    pause: float = 0.2,
    timeout: int = 10,
    table_class: Optional[str] = None,
    table_id: Optional[str] = None,
) -> Any:  # returns a bs4 Tag
    """
    Fetch a page and return the matching ``<table>`` element as a
    BeautifulSoup tag.

    Parser preference: ``lxml`` → ``html.parser`` (stdlib fallback).

    :param url:         Primary page URL.
    :param alt_url:     Optional fallback URL.
    :param params:      Optional query-string parameters.
    :param retries:     Passed through to :func:`safe_get`.
    :param pause:       Passed through to :func:`safe_get`.
    :param timeout:     Passed through to :func:`safe_get`.
    :param table_class: CSS class string to locate the target table.
    :param table_id:    HTML id attribute of the target table.
    :returns:           BeautifulSoup Tag for the matched table.
    :raises BDShareError: If the page cannot be fetched or the table is not found.
    """
    r = safe_get(url, params=params, alt_url=alt_url,
                 retries=retries, pause=pause, timeout=timeout)

    soup = _parse_html(r.content)

    table = None
    if table_class or table_id:
        attrs: Dict[str, str] = {}
        if table_class:
            attrs["class"] = table_class
        if table_id:
            table = soup.find("table", attrs={**attrs, "id": table_id})
            if table is None:
                table = soup.find("table", attrs={**attrs, "_id": table_id})
        else:
            table = soup.find("table", attrs=attrs)
    else:
        table = soup.find("table")

    if table is None:
        parts = []
        if table_class:
            parts.append(f"class={table_class!r}")
        if table_id:
            parts.append(f"id={table_id!r}")
        detail = " with " + ", ".join(parts) if parts else ""
        raise BDShareError(f"Table{detail} not found at {url}")

    return table


# ---------------------------------------------------------------------------
# Numeric conversion helper
# ---------------------------------------------------------------------------

def _safe_num(value: str, cast: type) -> Optional[Any]:
    """
    Strip formatting characters and cast a scraped string to a numeric type.

    Handles common DSE formatting quirks:
      - Thousands separators: ``","``
      - Double-dash placeholders: ``"--"``
      - Lone leading/trailing dashes
      - Surrounding whitespace
      - Sentinel strings: ``"N/A"``, ``"NaN"``

    Returns ``None`` for any value that cannot be meaningfully converted
    rather than raising, so a single malformed cell never aborts an entire
    page scrape.

    :param value: Raw text scraped from a ``<td>`` element.
    :param cast:  Target Python type — typically ``int`` or ``float``.
    :returns:     Converted value, or ``None`` on failure.
    """
    cleaned = (
        value
        .strip()
        .replace(",", "")   # thousands separator  e.g. "1,234"
        .replace("--", "")  # DSE placeholder      e.g. "--"
        .strip("-")         # lone leading/trailing dash
        .strip()
    )
    if not cleaned or cleaned.lower() in {"n/a", "nan"}:
        return None
    try:
        return cast(cleaned)
    except (ValueError, TypeError):
        logger.debug("_safe_num: could not cast %r to %s", value, cast.__name__)
        return None
