import logging
import pandas as pd
from typing import Optional
from bs4 import BeautifulSoup
from bdshare.util import vars as vs
from bdshare.util.helper import _fetch_table, safe_get, BDShareError, _session

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _post_news(url: str, alt_url: str, params: dict, retry_count: int, pause: float) -> BeautifulSoup:
    """POST to a news endpoint and return a parsed BeautifulSoup object."""
    import time
    for attempt in range(retry_count):
        time.sleep(pause * (2 ** attempt))
        try:
            r = _session.post(url, params=params, timeout=10)
            if r.status_code != 200:
                r = _session.post(alt_url, params=params, timeout=10)
            r.raise_for_status()
            try:
                return BeautifulSoup(r.content, "lxml")
            except Exception:
                return BeautifulSoup(r.content, "html.parser")
        except Exception as exc:
            if attempt == retry_count - 1:
                raise BDShareError(f"Failed to POST news from {url}: {exc}") from exc


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_agm_news(retry_count: int = 3, pause: float = 0.2) -> pd.DataFrame:
    """Get AGM / dividend declarations."""
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
            "agmDate":    cols[3].text.strip(),   # fixed typo: agmData → agmDate
            "recordDate": cols[4].text.strip(),
            "venue":      cols[5].text.strip(),   # fixed typo: vanue → venue
            "time":       cols[6].text.strip(),
        })

    if not rows:
        raise BDShareError("No AGM news found.")
    return pd.DataFrame(rows)


def get_all_news(
    start: Optional[str] = None,
    end: Optional[str] = None,
    code: Optional[str] = None,
    retry_count: int = 3,
    pause: float = 0.2,
) -> pd.DataFrame:
    """
    Get all DSE news items.

    Backward-compatible: get_all_news(code) still works — if only the first
    positional arg is supplied with no end/code, it is treated as ``code``.
    """
    # Backward-compatibility shim
    if start is not None and end is None and code is None:
        code, start = start, None

    params: dict = {"inst": code, "criteria": 3, "archive": "news"}
    if start:
        params["startDate"] = start
    if end:
        params["endDate"] = end

    soup = _post_news(
        vs.DSE_URL + vs.DSE_NEWS_URL,
        vs.DSE_ALT_URL + vs.DSE_NEWS_URL,
        params,
        retry_count,
        pause,
    )

    table = soup.find("table", attrs={"class": "table-news"}) or soup.find("table")
    if table is None:
        raise BDShareError("News table not found.")

    rows = []
    for row in table.find_all("tr"):
        heads = row.find_all("th")
        cols  = row.find_all("td")
        if heads and cols:
            label = heads[0].text.strip()
            value = cols[0].text.strip()
            if label in {"News Title:", "News:", "Post Date:"}:
                rows.append({label.rstrip(":"): value})

    if not rows:
        raise BDShareError("No news items parsed from table.")
    return pd.DataFrame(rows)


def get_corporate_announcements(
    code: Optional[str] = None,
    retry_count: int = 3,
    pause: float = 0.2,
) -> pd.DataFrame:
    """Get corporate announcements (criteria=2)."""
    params = {"inst": code, "criteria": 2, "archive": "news"}
    soup = _post_news(
        vs.DSE_URL + vs.DSE_NEWS_URL,
        vs.DSE_ALT_URL + vs.DSE_NEWS_URL,
        params,
        retry_count,
        pause,
    )

    table = soup.find("table", attrs={"class": "table-news"}) or soup.find("table")
    if table is None:
        raise BDShareError("Corporate announcements table not found.")

    rows = []
    for row in table.find_all("tr")[1:]:
        cols = row.find_all("td")
        if len(cols) < 3:
            continue
        rows.append({
            "code":    cols[0].text.strip(),
            "news":    cols[1].text.strip(),
            "date":    cols[2].text.strip(),
        })

    if not rows:
        raise BDShareError("No corporate announcements found.")
    return pd.DataFrame(rows)


def get_price_sensitive_news(
    code: Optional[str] = None,
    retry_count: int = 3,
    pause: float = 0.2,
) -> pd.DataFrame:
    """Get price-sensitive news (criteria=1)."""
    params = {"inst": code, "criteria": 1, "archive": "news"}
    soup = _post_news(
        vs.DSE_URL + vs.DSE_NEWS_URL,
        vs.DSE_ALT_URL + vs.DSE_NEWS_URL,
        params,
        retry_count,
        pause,
    )

    table = soup.find("table", attrs={"class": "table-news"}) or soup.find("table")
    if table is None:
        raise BDShareError("Price sensitive news table not found.")

    rows = []
    for row in table.find_all("tr")[1:]:
        cols = row.find_all("td")
        if len(cols) < 3:
            continue
        rows.append({
            "code":    cols[0].text.strip(),
            "news":    cols[1].text.strip(),
            "date":    cols[2].text.strip(),
        })

    if not rows:
        raise BDShareError("No price-sensitive news found.")
    return pd.DataFrame(rows)


# Unified dispatcher (matches __init__.py import)
def get_news(
    news_type: str = "all",
    code: Optional[str] = None,
    retry_count: int = 3,
    pause: float = 0.2,
) -> pd.DataFrame:
    """
    Unified news dispatcher.

    :param news_type: One of 'all', 'agm', 'corporate', 'psn'
    :param code: Optional trading code filter
    """
    _dispatch = {
        "all":       lambda: get_all_news(code=code, retry_count=retry_count, pause=pause),
        "agm":       lambda: get_agm_news(retry_count=retry_count, pause=pause),
        "corporate": lambda: get_corporate_announcements(code=code, retry_count=retry_count, pause=pause),
        "psn":       lambda: get_price_sensitive_news(code=code, retry_count=retry_count, pause=pause),
    }
    if news_type not in _dispatch:
        raise ValueError(f"Invalid news_type '{news_type}'. Choose from: {list(_dispatch)}")
    return _dispatch[news_type]()