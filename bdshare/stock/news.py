import logging
import pandas as pd
from typing import Optional
from bs4 import BeautifulSoup
from bdshare.util import vars as vs
from bdshare.util.helper import _fetch_table, _parse_html, safe_post, safe_get, BDShareError, _to_frame

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _post_news(url: str, alt_url: str, params: dict, retry_count: int, pause: float) -> BeautifulSoup:
    """POST to a news endpoint and return a parsed BeautifulSoup object."""
    r = safe_post(url, data=params, alt_url=alt_url, retries=retry_count, pause=pause)
    return _parse_html(r.content)

def _get_news(url: str, alt_url: str, params: dict, retry_count: int, pause: float) -> BeautifulSoup:
    """GET to a news endpoint and return a parsed BeautifulSoup object."""
    r = safe_get(url, params=params, alt_url=alt_url, retries=retry_count, pause=pause)
    return _parse_html(r.content)

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_agm_news(retry_count: int = 3, pause: float = 0.2, as_polars: bool = False) -> pd.DataFrame:
    """Get AGM / dividend declarations.

    :param as_polars: Return a polars DataFrame instead of pandas (requires polars installed).
    """
    table = _fetch_table(
        vs.DSE_URL + vs.DSE_AGM_URL,
        vs.DSE_ALT_URL + vs.DSE_AGM_URL,
        retries=retry_count,
        pause=pause,
    )

    rows = []
    for row in table.find_all("tr")[4:-6]:   # original slice preserved
        cols = row.find_all("td")
        if len(cols) < 7:
            continue
        rows.append({
            "company":    cols[0].text.strip(),
            "yearEnd":    cols[1].text.strip(),
            "dividend":   cols[2].text.strip(),
            "agmDate":    cols[3].text.strip(),
            "recordDate": cols[4].text.strip(),
            "venue":      cols[5].text.strip(),
            "time":       cols[6].text.strip(),
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

    params: dict = {"archive": "news"}
    if code:
        params["inst"] = code
        params["criteria"] = 3  # news for a specific company
    else:
        params["criteria"] = 4  # news for all companies
    if start:
        params["startDate"] = start
    if end:
        params["endDate"] = end

    soup = _get_news(
        vs.DSE_URL + vs.DSE_NEWS_URL,
        vs.DSE_ALT_URL + vs.DSE_NEWS_URL,
        params,
        retry_count,
        pause,
    )

    table = soup.find("table", attrs={"class": "table-news"}) or soup.find("table")
    if table is None:
        raise BDShareError("News table not found.")

    rows = _parse_news_rows(table, code_key="symbol")
    return _to_frame(pd.DataFrame(rows), as_polars)


def _parse_news_rows(table, code_key: str = "code") -> list:
    """Parse a DSE news table's label/value row pairs.

    Each news item is rendered as four separate <tr>s — a <th> label
    ("Trading Code:", "News Title:", "News:", "Post Date:") paired with
    a <td> value — not four <td>s in a single row.
    """
    rows = []
    current: dict = {}
    for row in table.find_all("tr"):
        heads = row.find_all("th")
        cols  = row.find_all("td")
        if not (heads and cols):
            continue
        label = heads[0].text.strip()
        value = cols[0].text.strip()
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
    soup = _get_news(
        vs.DSE_URL + vs.DSE_NEWS_URL,
        vs.DSE_ALT_URL + vs.DSE_NEWS_URL,
        {"inst": code, "criteria": 2, "archive": "news"},
        retry_count,
        pause,
    )
    table = soup.find("table", attrs={"class": "table-news"}) or soup.find("table")
    if table is None:
        raise BDShareError("Corporate announcements table not found.")
    rows = _parse_news_rows(table)
    if not rows:
        raise BDShareError("No corporate announcements found.")
    return _to_frame(pd.DataFrame(rows), as_polars)


def get_price_sensitive_news(
    code: Optional[str] = None,
    retry_count: int = 3,
    pause: float = 0.2,
    as_polars: bool = False,
) -> pd.DataFrame:
    """Get price-sensitive news (criteria=1).

    :param as_polars: Return a polars DataFrame instead of pandas (requires polars installed).
    """
    soup = _get_news(
        vs.DSE_URL + vs.DSE_NEWS_URL,
        vs.DSE_ALT_URL + vs.DSE_NEWS_URL,
        {"inst": code, "criteria": 1, "archive": "news"},
        retry_count,
        pause,
    )
    table = soup.find("table", attrs={"class": "table-news"}) or soup.find("table")
    if table is None:
        raise BDShareError("Price sensitive news table not found.")
    rows = _parse_news_rows(table)
    if not rows:
        raise BDShareError("No price-sensitive news found.")
    return _to_frame(pd.DataFrame(rows), as_polars)


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

    :param news_type: One of 'all', 'agm', 'corporate', 'psn'
    :param code: Optional trading code filter
    :param as_polars: Return a polars DataFrame instead of pandas (requires polars installed).
    """
    _dispatch = {
        "all":       lambda: get_all_news(code=code, retry_count=retry_count, pause=pause, as_polars=as_polars),
        "agm":       lambda: get_agm_news(retry_count=retry_count, pause=pause, as_polars=as_polars),
        "corporate": lambda: get_corporate_announcements(code=code, retry_count=retry_count, pause=pause, as_polars=as_polars),
        "psn":       lambda: get_price_sensitive_news(code=code, retry_count=retry_count, pause=pause, as_polars=as_polars),
    }
    if news_type not in _dispatch:
        raise ValueError(f"Invalid news_type '{news_type}'. Choose from: {list(_dispatch)}")
    return _dispatch[news_type]()
