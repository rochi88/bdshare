"""
bdshare.util.helper
~~~~~~~~~~~~~~~~~~~
Shared HTTP session, fetch helpers, numeric conversion, and exceptions
used across all bdshare sub-modules (trading, market, news).

Import surface expected by other modules:
    from bdshare.util.helper import (
        _fetch_table, _safe_num, _parse_html,
        _find, _find_all, _first, _rows, _cells,
        safe_get, safe_post,
        BDShareError, _session, deprecated,
        _to_frame, _parallel_map,
    )
"""

import json
import math
import re
import time
import logging
import warnings
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from functools import wraps
from typing import Any, Callable, Dict, Iterable, List, Optional, TypeVar

import certifi
import lxml.html
import requests
import tempfile
import atexit
from pathlib import Path
from requests.adapters import HTTPAdapter

from bdshare.util import vars as vs

logger = logging.getLogger(__name__)

T = TypeVar("T")


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
# Parallel fetches (paged archives, split date ranges) run up to
# _MAX_WORKERS requests at once; size the per-host pool to match so
# connections are reused rather than opened and discarded.
_MAX_WORKERS = 8
for _scheme in ("http://", "https://"):
    _session.mount(_scheme, HTTPAdapter(pool_connections=4, pool_maxsize=_MAX_WORKERS))
_session.headers.update({
    "User-Agent":      "bdshare/2.0 (https://github.com/bdshare/bdshare)",
    "Accept-Encoding": "gzip, deflate",
    "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
})


# ---------------------------------------------------------------------------
# HTML parsing helpers
# ---------------------------------------------------------------------------
# lxml is used directly rather than through BeautifulSoup: on DSE's large
# table pages it is roughly 10x faster and yields the same text.

def _parse_html(content: bytes) -> lxml.html.HtmlElement:
    """Parse HTML bytes into an lxml element tree (charset from <meta>)."""
    # lxml rejects an empty document; treat it as a page with no content.
    return lxml.html.document_fromstring(content if content.strip() else b"<html></html>")


def _class_test(cls: str) -> str:
    """XPath predicate matching a class attribute the way BeautifulSoup does.

    A multi-word value must equal the whole (whitespace-normalised) attribute;
    a single word matches any one of the element's classes.
    """
    if " " in cls:
        return f"normalize-space(@class)='{cls}'"
    return f"contains(concat(' ', normalize-space(@class), ' '), ' {cls} ')"


def _xpath(tag: str, cls: Optional[str] = None, **attrs: str) -> str:
    preds = [_class_test(cls)] if cls else []
    preds += [f"@{k}='{v}'" for k, v in attrs.items()]
    return f".//{tag}" + "".join(f"[{p}]" for p in preds)


def _find_all(el, tag: str, cls: Optional[str] = None, **attrs: str) -> list:
    """All descendants of ``el`` named ``tag`` with the given class/attributes."""
    return el.xpath(_xpath(tag, cls, **attrs))


def _find(el, tag: str, cls: Optional[str] = None, **attrs: str):
    """First match of :func:`_find_all`, or ``None``."""
    found = _find_all(el, tag, cls, **attrs)
    return found[0] if found else None


def _first(*elements):
    """First of ``elements`` that is not ``None``.

    Use this instead of ``a or b``: an lxml element with no children is falsy.
    """
    return next((e for e in elements if e is not None), None)


def _cells(row, tag: str = "td") -> List[str]:
    """Text of every ``tag`` cell under ``row`` (nested ones included)."""
    return [c.text_content() for c in row.iter(tag)]


def _rows(table) -> list:
    """Every ``<tr>`` under ``table``, nested ones included, in document order."""
    return list(table.iter("tr"))


# ---------------------------------------------------------------------------
# Next.js page data (React Server Components payload)
# ---------------------------------------------------------------------------
# Pages on the current DSE site carry their data inline as an RSC payload
# split across ``self.__next_f.push([1, "..."])`` scripts. The payload is a
# series of rows, each ``<hex id>:<JSON>\n`` or ``<hex id>:T<hex byte
# length>,<text>`` (long text, not newline-terminated). Values point at other
# rows with ``"$<id>"`` or at part of one with ``"$<id>:key:key..."``.

_RSC_CHUNK = re.compile(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)</script>', re.S)
_RSC_REF = re.compile(r"\$([0-9a-f]+)((?::[^:]+)*)")
_RSC_SPECIAL = {"$undefined": None, "$NaN": float("nan"),
                "$Infinity": float("inf"), "$-Infinity": float("-inf"), "$-0": -0.0}


def _rsc_rows(html: str) -> Dict[str, Any]:
    """Decode a Next.js page's inline RSC payload into ``{row id: value}``.

    Rows that are not JSON (component and asset references) are kept as raw
    strings.
    """
    chunks = _RSC_CHUNK.findall(html)
    data = "".join(json.loads(f'"{c}"') for c in chunks).encode("utf-8")
    rows: Dict[str, Any] = {}
    i = 0
    while i < len(data):
        colon = data.find(b":", i)
        if colon < 0:
            break
        rid, j = data[i:colon].decode(), colon + 1
        if data[j:j + 1] == b"T":  # length is in bytes, so slice the bytes
            comma = data.index(b",", j)
            end = comma + 1 + int(data[j + 1:comma], 16)
            rows[rid] = data[comma + 1:end].decode("utf-8")
            i = end
            continue
        nl = data.find(b"\n", j)
        end = len(data) if nl < 0 else nl
        raw = data[j:end].decode("utf-8")
        try:
            rows[rid] = json.loads(raw)
        except ValueError:
            rows[rid] = raw
        i = end + 1
    return rows


def _rsc_resolve(value: Any, rows: Dict[str, Any], _hops: int = 0) -> Any:
    """``value`` with RSC references and special ``$`` strings replaced."""
    if isinstance(value, dict):
        return {k: _rsc_resolve(v, rows, _hops) for k, v in value.items()}
    if isinstance(value, list):
        return [_rsc_resolve(v, rows, _hops) for v in value]
    if not isinstance(value, str) or not value.startswith("$"):
        return value
    if value in _RSC_SPECIAL:
        return _RSC_SPECIAL[value]
    if value.startswith("$$"):
        return value[1:]
    if value.startswith("$D"):  # Date
        return value[2:]
    if value.startswith("$n"):  # BigInt
        return int(value[2:])
    target = _rsc_follow(value, rows, _hops)
    return value if target is value else _rsc_resolve(target, rows, _hops + 1)


def _rsc_follow(value: Any, rows: Dict[str, Any], hops: int) -> Any:
    """The raw value a reference string points at (``value`` itself if not one).

    Only the reference chain is followed; the target is not resolved, so a
    path into a large row (such as the whole page tree) stays cheap.
    """
    while isinstance(value, str):
        ref = _RSC_REF.fullmatch(value)
        if ref is None or ref.group(1) not in rows:
            return value
        if hops > 50:
            raise BDShareError("RSC payload references form a cycle.")
        hops += 1
        target = rows[ref.group(1)]
        for key in filter(None, ref.group(2).split(":")):
            target = _rsc_follow(target, rows, hops)
            target = _rsc_step(target, key)
        value = target
    return value


# A React element is serialised as ["$", type, key, props]; paths name these
# slots rather than index them.
_RSC_ELEMENT_SLOTS = {"type": 1, "key": 2, "props": 3}


def _rsc_step(target: Any, key: str) -> Any:
    """``target[key]`` for one segment of a reference path."""
    if isinstance(target, list):
        if target[:1] == ["$"] and key in _RSC_ELEMENT_SLOTS:
            return target[_RSC_ELEMENT_SLOTS[key]]
        return target[int(key)]
    return target[key]


def _rsc_find(value: Any, match: Callable[[dict], bool]) -> Optional[dict]:
    """First dict in ``value`` (searched depth-first) for which ``match`` is true."""
    stack = [value]
    while stack:
        cur = stack.pop()
        if isinstance(cur, dict):
            if match(cur):
                return cur
            stack.extend(reversed(list(cur.values())))
        elif isinstance(cur, list):
            stack.extend(reversed(cur))
    return None


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
) -> lxml.html.HtmlElement:
    """
    Fetch a page and return the matching ``<table>`` element.

    :param url:         Primary page URL.
    :param alt_url:     Optional fallback URL.
    :param params:      Optional query-string parameters.
    :param retries:     Passed through to :func:`safe_get`.
    :param pause:       Passed through to :func:`safe_get`.
    :param timeout:     Passed through to :func:`safe_get`.
    :param table_class: CSS class string to locate the target table.
    :param table_id:    HTML id attribute of the target table.
    :returns:           lxml element for the matched table.
    :raises BDShareError: If the page cannot be fetched or the table is not found.
    """
    r = safe_get(url, params=params, alt_url=alt_url,
                 retries=retries, pause=pause, timeout=timeout)

    root = _parse_html(r.content)

    if table_id:
        table = _first(_find(root, "table", table_class, id=table_id),
                       _find(root, "table", table_class, _id=table_id))
    else:
        table = _find(root, "table", table_class)

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
# Parallel fetch helper
# ---------------------------------------------------------------------------

def _parallel_map(fn: Callable[[Any], T], items: Iterable[Any]) -> List[T]:
    """``[fn(x) for x in items]``, run concurrently on the shared session."""
    items = list(items)
    if len(items) <= 1:
        return [fn(x) for x in items]
    with ThreadPoolExecutor(max_workers=min(_MAX_WORKERS, len(items))) as pool:
        return list(pool.map(fn, items))


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
    range is split in half and both halves re-fetched. Each round of splits
    is fetched in parallel. Rows are returned newest range first, matching
    the API's own ordering.
    """
    def fetch(span):
        return _fetch_json(path, {**(params or {}), "from": span[0], "to": span[1]},
                           retries=retries, pause=pause)

    done: List[tuple] = []  # (range start, rows) of ranges that came back whole
    pending = [(start, end)]
    while pending:
        split = []
        for (lo, hi), data in zip(pending, _parallel_map(fetch, pending)):
            rows = data.get("rows") or []
            capped = (
                bool(data.get("truncated"))
                or (data.get("total") or 0) > len(rows)
                or (max_rows is not None and len(rows) >= max_rows)
            )
            first, last = date.fromisoformat(lo), date.fromisoformat(hi)
            if not capped or first >= last:
                done.append((lo, rows))
                continue
            mid = first + (last - first) // 2
            split += [(lo, mid.isoformat()), ((mid + timedelta(days=1)).isoformat(), hi)]
        pending = split
    done.sort(key=lambda d: d[0], reverse=True)
    return [r for _, rows in done for r in rows]


def _fetch_json_pages(
    path: str,
    params: Optional[Dict] = None,
    retries: int = 3,
    pause: float = 0.2,
) -> List[Dict]:
    """
    Fetch every row of a paged dsebd.org endpoint.

    Paged endpoints report ``total`` and ``pageSize`` and take a 1-based
    ``page`` parameter. The first page gives the page count; the rest are
    fetched in parallel and returned in page order.
    """
    params = params or {}
    first = _fetch_json(path, params, retries=retries, pause=pause)
    rows = list(first.get("rows") or [])
    size = first.get("pageSize") or len(rows)
    pages = math.ceil((first.get("total") or 0) / size) if size else 1

    def fetch(page):
        data = _fetch_json(path, {**params, "page": page}, retries=retries, pause=pause)
        return data.get("rows") or []

    for page_rows in _parallel_map(fetch, range(2, pages + 1)):
        rows += page_rows
    return rows


# ---------------------------------------------------------------------------
# dsebd.org → legacy fallback
# ---------------------------------------------------------------------------

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
