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
        _to_frame,
    )
"""

import time
import logging
import warnings
from datetime import date, datetime, timedelta, timezone
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, TypeVar

import certifi
import requests
import tempfile
import atexit
from pathlib import Path
from bs4 import BeautifulSoup

from bdshare.util import vars as vs

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
# CA bundle — dsebd.org sends an incomplete chain (missing the Sectigo DV R36
# intermediate).  We ship that intermediate and combine it with certifi at
# startup so verification passes without disabling SSL.
# Intermediate validity: 2021-03-22 → 2036-03-21  (safe to bundle long-term)
# ---------------------------------------------------------------------------

def _build_ca_bundle() -> str:
    """Return path to a combined PEM bundle: certifi + bundled intermediate."""
    intermediate = Path(__file__).parent / "sectigo_dv_r36.pem"
    with open(certifi.where(), "rb") as f:
        certifi_pem = f.read()
    with open(intermediate, "rb") as f:
        intermediate_pem = f.read()
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pem")
    tmp.write(certifi_pem + b"\n" + intermediate_pem)
    tmp.close()
    atexit.register(lambda: Path(tmp.name).unlink(missing_ok=True))
    return tmp.name


_CA_BUNDLE = _build_ca_bundle()


# ---------------------------------------------------------------------------
# Shared HTTP session
# ---------------------------------------------------------------------------

# One session for the entire process lifetime — reuses TCP connections and
# centralises headers/cookies so sub-modules don't each manage them.
_session = requests.Session()
_session.verify = _CA_BUNDLE
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
# dsebd.org JSON API helpers
# ---------------------------------------------------------------------------

# Bangladesh has no DST, so a fixed offset is exact and needs no tzdata.
_DHAKA_TZ = timezone(timedelta(hours=6))


def _dhaka_today() -> str:
    """Today's date in Dhaka as 'YYYY-MM-DD' (the API's date format)."""
    return datetime.now(_DHAKA_TZ).date().isoformat()


def _date_range(start: Optional[str], end: Optional[str]) -> tuple:
    """Fill in a missing start/end: end defaults to today, start to end."""
    end = end or _dhaka_today()
    return start or end, end


def _fetch_json(
    path: str,
    params: Optional[Dict] = None,
    retries: int = 3,
    pause: float = 0.2,
    timeout: int = 15,
) -> Any:
    """
    GET a dsebd.org JSON API endpoint and return the decoded body.

    The API occasionally stalls a request for about a minute while an
    immediate retry answers in well under a second, so the timeout is kept
    short and a stalled request is retried rather than waited out.
    """
    r = safe_get(vs.DSE_URL + path, params=params,
                 alt_url=vs.DSE_ALT_URL + path,
                 retries=retries, pause=pause, timeout=timeout)
    try:
        return r.json()
    except ValueError as exc:
        raise BDShareError(f"Invalid JSON from {r.url}") from exc


def _fetch_json_range(
    path: str,
    start: str,
    end: str,
    params: Optional[Dict] = None,
    retries: int = 3,
    pause: float = 0.2,
    max_rows: Optional[int] = None,
) -> List[Dict]:
    """
    Fetch every row of a ``from``/``to`` dsebd.org endpoint.

    The API silently caps each response (``truncated: true``, a ``total``
    larger than the rows returned, or simply ``max_rows`` rows), so a capped
    range is split in half and each half fetched recursively. Rows are
    returned newest range first, matching the API's own ordering.
    """
    data = _fetch_json(path, {**(params or {}), "from": start, "to": end},
                       retries=retries, pause=pause)
    rows = data.get("rows") or []
    capped = (
        bool(data.get("truncated"))
        or (data.get("total") or 0) > len(rows)
        or (max_rows is not None and len(rows) >= max_rows)
    )
    first, last = date.fromisoformat(start), date.fromisoformat(end)
    if not capped or first >= last:
        return rows
    mid = first + (last - first) // 2
    newer = _fetch_json_range(path, (mid + timedelta(days=1)).isoformat(), end,
                              params, retries, pause, max_rows)
    older = _fetch_json_range(path, start, mid.isoformat(),
                              params, retries, pause, max_rows)
    return newer + older


# ---------------------------------------------------------------------------
# dsebd.org → legacy fallback
# ---------------------------------------------------------------------------

T = TypeVar("T")

# Failures that mean "this site didn't work": network/HTTP errors (surfaced as
# BDShareError by safe_get) and parse errors from an unexpected page layout.
_SOURCE_ERRORS = (BDShareError, requests.RequestException,
                  AttributeError, IndexError, KeyError, TypeError)


def _with_fallback(legacy: Callable[[], T], new: Callable[[], T], what: str) -> T:
    """
    Run a fetch against the configured DSE site(s).

    ``vs.DSE_SOURCE`` selects the site: ``"legacy"`` (old.dsebd.org only),
    ``"new"`` (dsebd.org only) or ``"auto"`` (dsebd.org first, legacy if
    that fails). Both callables must return data in the same shape.
    """
    source = vs.DSE_SOURCE
    if source == "legacy":
        return legacy()
    if source == "new":
        return new()
    if source != "auto":
        raise ValueError(
            f"Invalid DSE_SOURCE {source!r}; expected 'auto', 'legacy' or 'new'."
        )
    try:
        return new()
    except _SOURCE_ERRORS as new_exc:
        logger.info("%s: dsebd.org failed (%s); trying legacy site", what, new_exc)
        try:
            return legacy()
        except _SOURCE_ERRORS as legacy_exc:
            raise BDShareError(
                f"{what} failed on both sites. "
                f"Current ({vs.DSE_URL}): {new_exc}. "
                f"Legacy ({vs.DSE_LEGACY_URL}): {legacy_exc}"
            ) from legacy_exc


# ---------------------------------------------------------------------------
# DataFrame conversion helper
# ---------------------------------------------------------------------------

def _to_frame(df, as_polars: bool):
    """Convert a pandas DataFrame to a polars DataFrame when as_polars=True.

    The pandas index (if named) is reset to a regular column before conversion
    so it is not silently dropped.

    Uses dict-based construction to avoid a pyarrow dependency.

    Raises ImportError if polars is not installed.
    """
    if not as_polars:
        return df
    try:
        import polars as pl
    except ImportError:
        raise ImportError(
            "polars is not installed. Install it with: pip install polars"
            " or pip install bdshare[polars]"
        )
    if getattr(df.index, "name", None):
        df = df.reset_index()
    # Source columns (e.g. pd.read_html output) can mix strings with NaN
    # floats in the same column. .tolist() alone surfaces the NaN sentinel
    # regardless of dtype, so missing values are swapped for None via an
    # explicit isna() mask before handing the list to polars.
    def _column_values(col):
        mask = df[col].isna().tolist()
        return [None if is_na else v for v, is_na in zip(df[col].tolist(), mask)]

    return pl.DataFrame({str(col): _column_values(col) for col in df.columns})


# ---------------------------------------------------------------------------
# Numeric conversion helper
# ---------------------------------------------------------------------------

def _safe_num(value: str, cast: type) -> Optional[Any]:
    """
    Strip formatting characters and cast a scraped string to a numeric type.

    Handles common DSE formatting quirks:
      - Thousands separators: ``","``
      - Dash-only placeholders: ``"-"``, ``"--"``
      - Surrounding whitespace
      - Sentinel strings: ``"N/A"``, ``"NaN"``

    Returns ``None`` for any value that cannot be meaningfully converted
    rather than raising, so a single malformed cell never aborts an entire
    page scrape.

    :param value: Raw text scraped from a ``<td>`` element.
    :param cast:  Target Python type — typically ``int`` or ``float``.
    :returns:     Converted value, or ``None`` on failure.
    """
    cleaned = value.strip().replace(",", "")  # thousands separator e.g. "1,234"
    # Dash-only cells ("-", "--") are placeholders; a leading minus on a real
    # number (e.g. "-1.20") is a sign and must be kept.
    if not cleaned.strip("-") or cleaned.lower() in {"n/a", "nan"}:
        return None
    try:
        return cast(cleaned)
    except (ValueError, TypeError):
        logger.debug("_safe_num: could not cast %r to %s", value, cast.__name__)
        return None
