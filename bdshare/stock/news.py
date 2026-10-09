import logging
import re
import warnings
from datetime import date, timedelta
import lxml.html
import pandas as pd
from typing import Optional
from bdshare.util import vars as vs
from bdshare.util.helper import (
    _fetch_table, _parse_html, _find, _first, _rows, _cells,
    safe_post, safe_get, BDShareError, _to_frame,
    _fetch_json, _fetch_json_range, _date_range, _with_fallback, deprecated,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _post_news(url: str, params: dict, retry_count: int, pause: float) -> lxml.html.HtmlElement:
    """POST to a news endpoint and return the parsed page."""
    r = safe_post(url, data=params, retries=retry_count, pause=pause)
    return _parse_html(r.content)

def _get_news(url: str, params: dict, retry_count: int, pause: float) -> lxml.html.HtmlElement:
    """GET to a news endpoint and return the parsed page."""
    r = safe_get(url, params=params, retries=retry_count, pause=pause)
    return _parse_html(r.content)


def _legacy_news_rows(params: dict, code_key: str, retry_count: int, pause: float) -> list:
    """Fetch and parse the legacy old_news.php table."""
    root = _get_news(
        vs.DSE_LEGACY_URL + vs.DSE_NEWS_URL,
        params,
        retry_count,
        pause,
    )
    table = _first(_find(root, "table", "table-news"), _find(root, "table"))
    if table is None:
        raise BDShareError("News table not found.")
    return _parse_news_rows(table, code_key=code_key)


def _news_rows_new(
    code: Optional[str],
    start: Optional[str],
    end: Optional[str],
    code_key: str,
    retry_count: int,
    pause: float,
    news_type: Optional[str] = None,
) -> list:
    """
    News rows from dsebd.org in the legacy row schema.

    Without a date range the API returns its latest-news feed.
    ``news_type`` filters on the API's type label (e.g. "Price sensitive").
    """
    params = {"code": code} if code else {}
    if start or end:
        rows = _fetch_json_range(vs.DSE_API_NEWS, *_date_range(start, end), params,
                                 retries=retry_count, pause=pause)
    else:
        rows = _fetch_json(vs.DSE_API_NEWS, params, retries=retry_count, pause=pause).get("rows") or []
    return [
        {code_key: r.get("code"), "title": r.get("summary"),
         "news": r.get("body"), "date": r.get("filedAt")}
        for r in rows
        if news_type is None or r.get("type") == news_type
    ]

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

@deprecated("The legacy AGM page has not been updated since 2020. "
            "Use get_dividend_declarations() instead.")
def get_agm_news(retry_count: int = 3, pause: float = 0.2, as_polars: bool = False) -> pd.DataFrame:
    """Get AGM / dividend declarations from the legacy site's AGM page.

    .. deprecated:: 1.2.8
       The legacy page has not been updated since 2020. Use
       :func:`get_dividend_declarations`, which reads current declarations
       from the DSE news feed.

    :param as_polars: Return a polars DataFrame instead of pandas (requires polars installed).
    """
    table = _fetch_table(
        vs.DSE_LEGACY_URL + vs.DSE_AGM_URL,
        retries=retry_count,
        pause=pause,
    )

    rows = []
    for row in _rows(table)[4:-6]:   # original slice preserved
        cols = [c.strip() for c in _cells(row)]
        if len(cols) < 7:
            continue
        rows.append({
            "company":    cols[0],
            "yearEnd":    cols[1],
            "dividend":   cols[2],
            "agmDate":    cols[3],
            "recordDate": cols[4],
            "venue":      cols[5],
            "time":       cols[6],
        })

    if not rows:
        raise BDShareError("No AGM news found.")
    return _to_frame(pd.DataFrame(rows), as_polars)


def get_all_news(
    start: Optional[str] = None,
    end: Optional[str] = None,
    code: Optional[str] = None,
    retry_count: int = 3,
    pause: float = 0.2,
    as_polars: bool = False,
) -> pd.DataFrame:
    """
    Get all DSE news items.

    Backward-compatible: get_all_news(code) still works — if only the first
    positional arg is supplied with no end/code, it is treated as ``code``.

    :param as_polars: Return a polars DataFrame instead of pandas (requires polars installed).
    """
    # Backward-compatibility shim
    if start is not None and end is None and code is None:
        code, start = start, None

    def legacy():
        # The legacy archive answers three queries: one company's news
        # (criteria 3, no date filter), all news in a date range (criteria 4,
        # which returns nothing without both dates), and the latest-news feed
        # (criteria 2).
        if code:
            rows = _legacy_news_rows({"archive": "news", "criteria": 3, "inst": code},
                                     "symbol", retry_count, pause)
            if start or end:
                lo, hi = _date_range(start, end)
                rows = [r for r in rows if lo <= (r.get("date") or "") <= hi]
            return rows
        if start or end:
            lo, hi = _date_range(start, end)
            return _legacy_news_rows({"archive": "news", "criteria": 4,
                                      "startDate": lo, "endDate": hi},
                                     "symbol", retry_count, pause)
        return _legacy_news_rows({"archive": "news", "criteria": 2},
                                 "symbol", retry_count, pause)

    rows = _with_fallback(
        legacy,
        lambda: _news_rows_new(code, start, end, "symbol", retry_count, pause),
        "News",
    )
    return _to_frame(pd.DataFrame(rows), as_polars)


def _parse_news_rows(table, code_key: str = "code") -> list:
    """Parse a DSE news table's label/value row pairs.

    Each news item is rendered as four separate <tr>s — a <th> label
    ("Trading Code:", "News Title:", "News:", "Post Date:") paired with
    a <td> value — not four <td>s in a single row.
    """
    rows = []
    current: dict = {}
    for row in _rows(table):
        heads = _cells(row, "th")
        cols  = _cells(row)
        if not (heads and cols):
            continue
        label = heads[0].strip()
        value = cols[0].strip()
        if label == "Trading Code:":
            if current:
                rows.append(current)
            current = {code_key: value}
        elif label == "News Title:":
            current["title"] = value
        elif label == "News:":
            current["news"] = value
        elif label == "Post Date:":
            current["date"] = value
    if current:
        rows.append(current)
    return rows


def get_corporate_announcements(
    code: Optional[str] = None,
    retry_count: int = 3,
    pause: float = 0.2,
    as_polars: bool = False,
) -> pd.DataFrame:
    """Get corporate announcements (criteria=2).

    :param as_polars: Return a polars DataFrame instead of pandas (requires polars installed).
    """
    rows = _with_fallback(
        lambda: _legacy_news_rows({"inst": code, "criteria": 2, "archive": "news"},
                                  "code", retry_count, pause),
        lambda: _news_rows_new(code, None, None, "code", retry_count, pause),
        "Corporate announcements",
    )
    if not rows:
        raise BDShareError("No corporate announcements found.")
    return _to_frame(pd.DataFrame(rows), as_polars)


def get_price_sensitive_news(
    code: Optional[str] = None,
    retry_count: int = 3,
    pause: float = 0.2,
    as_polars: bool = False,
) -> pd.DataFrame:
    """Get price-sensitive news.

    Only available from dsebd.org; the legacy news archive does not mark
    which items are price sensitive.

    :param as_polars: Return a polars DataFrame instead of pandas (requires polars installed).
    """
    def legacy():
        raise BDShareError("Price-sensitive news is only available from dsebd.org.")

    rows = _with_fallback(
        legacy,
        lambda: _news_rows_new(code, None, None, "code", retry_count, pause,
                               news_type="Price sensitive"),
        "Price sensitive news",
    )
    if not rows:
        raise BDShareError("No price-sensitive news found.")
    return _to_frame(pd.DataFrame(rows), as_polars)


# ---------------------------------------------------------------------------
# Dividend declarations (current site's news feed)
# ---------------------------------------------------------------------------

# How far back get_dividend_declarations() looks when no start date is given.
_DIVIDEND_DEFAULT_DAYS = 180

# News summaries ("CODE: <summary>") that announce a company's own dividend.
_DIVIDEND_DECLARATION = re.compile(
    r"^(?:Interim |Final )?(?:Cash |Stock )?Dividend Declaration$"
    r"|^Declaration of (?:Interim |Final )?(?:Cash |Stock )?Dividend(?: and .*)?$",
    re.I,
)
# Long items are split into parts; later parts start "(cont. news of X):"
# or "(Continuation news of X):", and parts end "(cont.)" or "(end)".
_CONTINUATION = re.compile(r"\s*\((?:cont|continuation)", re.I)
_PART_MARKER = re.compile(r"\((?:cont(?:inuation)?\.?(?: news of [^)]*)?|end)\)\s*:?", re.I)

_DATE = (r"(\d{1,2}[./-]\d{1,2}[./-]\d{2,4}"
         r"|\d{1,2}(?:st|nd|rd|th)?[\s-]+[A-Za-z]{3,9}[\s,-]+\d{4}"
         r"|[A-Za-z]{3,9}\s+\d{1,2}(?:st|nd|rd|th)?,?\s*\d{4})")
_TIME = r"(\d{1,2}(?:[:.]\d{2})?\s*[ap]\.?\s*m\b\.?)"
_AGM = r"Date of (?:the\s+)?(?:\d+\w*\s+)?AGM\s*:\s*"
# DSE words declarations in a standard form, e.g. "The Board of Directors has
# recommended 20% Cash Dividend for the year ended June 30, 2026. Date of AGM:
# 26.11.2026, Time: 11:30 AM, Venue: Digital Platform. Record Date: 27.10.2026."
# Each field lists (pattern, template) pairs in order of preference; the
# template builds the value from the match's groups.
_DIVIDEND_FIELDS = {
    "yearEnd":    [(r"(?:year|period) end(?:ed|ing)\s+(?:on\s+)?" + _DATE, r"\1")],
    "dividend":   [
        # "declared Interim Cash Dividend for the year 2026 at the rate of 105%"
        (r"(?:recommended|declared|approved)\s+((?:Interim |Final )?(?:Cash |Stock )?Dividend)\b"
         r"[^.]{0,80}?at the rate of\s+(\d+(?:\.\d+)?\s*%)", r"\2 \1"),
        (r"(?:recommended|declared|approved)\s+(.+?)\s+for (?:all shareholders for )?"
         r"the (?:financial\s+)?(?:year|period)", r"\1"),
    ],
    "agmDate":    [(_AGM + _DATE, r"\1")],
    "recordDate": [(r"Record\s+Date(?:\s+for [^:]{0,60}?)?\s*(?::|\bis\b)\s*" + _DATE, r"\1")],
    "venue":      [(r"Venue(?:\s*/\s*Mode)?\s*:\s*(.+?)\.?\s*Record\s+Date", r"\1")],
    "time":       [(r"\bTime\s*:\s*" + _TIME, r"\1"),
                   (_AGM + _DATE + r"\s*(?:,\s*)?at\s+" + _TIME, r"\2")],
}
_DIVIDEND_COLUMNS = ["symbol", "company", "yearEnd", "dividend", "agmDate",
                     "recordDate", "venue", "time", "date"]


def _declaration_text(parts: list) -> Optional[str]:
    """Join a news item's parts into one text, or None if its opening part is missing."""
    first = [p for p in parts if not _CONTINUATION.match(p.get("body") or "")]
    if not first:
        return None
    rest = sorted((p for p in parts if p not in first), key=lambda p: str(p.get("id")))
    text = " ".join(p.get("body") or "" for p in first + rest)
    return re.sub(r"\s+", " ", _PART_MARKER.sub(" ", text)).strip()


def _parse_dividend_declarations(rows: list) -> list:
    """Dividend declaration rows, one per news item, from raw news API rows."""
    items: dict = {}
    for r in rows:
        summary = (r.get("summary") or "").split(":", 1)[-1].strip()
        if r.get("type") == "Dividend" and _DIVIDEND_DECLARATION.search(summary):
            items.setdefault((r.get("code"), r.get("filedAt"), r.get("summary")), []).append(r)

    out = []
    for (code, filed, _), parts in items.items():
        text = _declaration_text(parts)
        if text is None:
            continue
        row = {"symbol": code, "company": parts[0].get("name"), "date": filed}
        for name, patterns in _DIVIDEND_FIELDS.items():
            row[name] = None
            for pattern, template in patterns:
                match = re.search(pattern, text, re.I)
                if match:
                    row[name] = match.expand(template).strip(" ,;")
                    break
        out.append(row)
    return out


def get_dividend_declarations(
    start: Optional[str] = None,
    end: Optional[str] = None,
    code: Optional[str] = None,
    retry_count: int = 3,
    pause: float = 0.2,
    as_polars: bool = False,
) -> pd.DataFrame:
    """
    Get dividend declarations with their AGM and record dates.

    Reads the "Dividend Declaration" items in the current site's news feed
    and pulls out the declared dividend, year end, AGM date, time and venue,
    and record date. Replaces the deprecated :func:`get_agm_news`, whose
    legacy page stopped updating in 2020.

    Fields come from the announcement text, so one the announcement leaves
    out (a fund holds no AGM; some companies announce the AGM later) is
    ``None``.

    :param start: Start date 'YYYY-MM-DD' (default: 180 days before ``end``).
    :param end:   End date 'YYYY-MM-DD' (default: today).
    :param code:  Optional trading code filter.
    :param as_polars: Return a polars DataFrame instead of pandas (requires polars installed).
    :return: DataFrame, newest first - symbol, company, yearEnd, dividend,
             agmDate, recordDate, venue, time, date (the announcement date).
    """
    end = end or _date_range(None, None)[1]
    start = start or (date.fromisoformat(end) - timedelta(days=_DIVIDEND_DEFAULT_DAYS)).isoformat()
    rows = _fetch_json_range(vs.DSE_API_NEWS, start, end, {"code": code} if code else None,
                             retries=retry_count, pause=pause)
    df = pd.DataFrame(_parse_dividend_declarations(rows), columns=_DIVIDEND_COLUMNS)
    df = df.sort_values("date", ascending=False, kind="stable").reset_index(drop=True)
    return _to_frame(df, as_polars)


# Unified dispatcher (matches __init__.py import)
def get_news(
    news_type: str = "all",
    code: Optional[str] = None,
    retry_count: int = 3,
    pause: float = 0.2,
    as_polars: bool = False,
) -> pd.DataFrame:
    """
    Unified news dispatcher.

    :param news_type: One of 'all', 'dividend', 'corporate', 'psn', or the
                      deprecated 'agm' (use 'dividend').
    :param code: Optional trading code filter
    :param as_polars: Return a polars DataFrame instead of pandas (requires polars installed).
    """
    if news_type == "agm":
        warnings.warn("news_type='agm' is deprecated: the legacy AGM page has not been "
                      "updated since 2020. Use news_type='dividend' instead.",
                      DeprecationWarning, stacklevel=2)
    _dispatch = {
        "all":       lambda: get_all_news(code=code, retry_count=retry_count, pause=pause, as_polars=as_polars),
        "dividend":  lambda: get_dividend_declarations(code=code, retry_count=retry_count, pause=pause, as_polars=as_polars),
        "agm":       lambda: get_agm_news.__wrapped__(retry_count=retry_count, pause=pause, as_polars=as_polars),
        "corporate": lambda: get_corporate_announcements(code=code, retry_count=retry_count, pause=pause, as_polars=as_polars),
        "psn":       lambda: get_price_sensitive_news(code=code, retry_count=retry_count, pause=pause, as_polars=as_polars),
    }
    if news_type not in _dispatch:
        raise ValueError(f"Invalid news_type '{news_type}'. Choose from: {list(_dispatch)}")
    return _dispatch[news_type]()
