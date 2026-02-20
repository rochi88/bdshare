import logging
import pandas as pd
from typing import Optional
from bdshare.util import vars as vs
from bdshare.util.helper import _fetch_table, _safe_num, safe_get, BDShareError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Table class constants
# ---------------------------------------------------------------------------
_CLS_FIXED    = "table table-bordered background-white shares-table fixedHeader"
_CLS_SHARES   = "table table-bordered background-white shares-table"
_CLS_CENTER   = "table table-bordered background-white text-center"
_CLS_PLAIN    = "table table-bordered background-white"
_CLS_STRIPPED = "table table-stripped"


# ---------------------------------------------------------------------------
# Public API  (canonical names as of v1.2.0)
# ---------------------------------------------------------------------------

def get_market_info(retry_count: int = 3, pause: float = 0.2) -> pd.DataFrame:
    """Get current market summary (indices, volumes, market cap)."""
    table = _fetch_table(
        vs.DSE_URL + vs.DSE_MARKET_INFO_URL,
        vs.DSE_ALT_URL + vs.DSE_MARKET_INFO_URL,
        retries=retry_count,
        pause=pause,
        table_class=_CLS_CENTER,
        table_id="data-table",
    )
    rows = []
    for row in table.find_all("tr")[1:]:
        cols = row.find_all("td")
        if len(cols) < 9:
            continue
        try:
            rows.append({
                "Date":                   cols[0].text.strip(),
                "Total Trade":            _safe_num(cols[1].text, int),
                "Total Volume":           _safe_num(cols[2].text, int),
                "Total Value (mn)":       _safe_num(cols[3].text, float),
                "Total Market Cap. (mn)": _safe_num(cols[4].text, float),
                "DSEX Index":             _safe_num(cols[5].text, float),
                "DSES Index":             _safe_num(cols[6].text, float),
                "DS30 Index":             _safe_num(cols[7].text, float),
                "DGEN Index":             _safe_num(cols[8].text, float),
            })
        except (IndexError, AttributeError) as exc:
            logger.warning("Skipping malformed market info row: %s", exc)

    if not rows:
        raise BDShareError("No market info data found.")
    return pd.DataFrame(rows)


def get_company_info(symbol: str, retry_count: int = 3, pause: float = 0.2) -> list:
    """
    Get company information tables for a given symbol.

    :return: list of DataFrames (relevant tables start at index 400 in the page).
    """
    r = safe_get(
        vs.DSE_URL + vs.DSE_COMPANY_INFO_URL,
        params={"name": symbol},
        alt_url=vs.DSE_ALT_URL + vs.DSE_COMPANY_INFO_URL,
        retries=retry_count,
        pause=pause,
    )
    try:
        tables = pd.read_html(r.content)
        return tables[400:]
    except Exception as exc:
        raise BDShareError(f"Failed to parse company info for {symbol}: {exc}") from exc


def get_latest_pe(retry_count: int = 3, pause: float = 0.2) -> pd.DataFrame:
    """Get latest P/E ratios for all listed companies."""
    table = _fetch_table(
        vs.DSE_URL + vs.DSE_LPE_URL,
        vs.DSE_ALT_URL + vs.DSE_LPE_URL,
        retries=retry_count,
        pause=pause,
        table_class=_CLS_FIXED,
    )
    rows = []
    for row in table.find_all("tr")[1:]:
        cols = row.find_all("td")
        if len(cols) < 10:
            continue
        try:
            rows.append(tuple(c.text.strip().replace(",", "") for c in cols[1:10]))
        except (IndexError, AttributeError) as exc:
            logger.warning("Skipping malformed P/E row: %s", exc)

    if not rows:
        raise BDShareError("No P/E data found.")
    return pd.DataFrame(rows)


def get_market_info_more_data(
    start: Optional[str] = None,
    end: Optional[str] = None,
    index: Optional[str] = None,
    retry_count: int = 3,
    pause: float = 0.2,
) -> pd.DataFrame:
    """Get extended historical market summary data via POST."""
    from bdshare.util.helper import _session
    import time

    payload = {
        "startDate": start,
        "endDate": end,
        "searchRecentMarket": "Search Recent Market",
    }

    for attempt in range(retry_count):
        time.sleep(pause * (2 ** attempt))
        try:
            r = _session.post(
                vs.DSE_URL + vs.DSE_MARKET_INFO_MORE_URL, data=payload, timeout=10
            )
            if r.status_code != 200:
                r = _session.post(
                    vs.DSE_ALT_URL + vs.DSE_MARKET_INFO_MORE_URL, data=payload, timeout=10
                )
            r.raise_for_status()
            break
        except Exception as exc:
            if attempt == retry_count - 1:
                raise BDShareError(
                    f"Failed to fetch extended market data: {exc}"
                ) from exc

    from bs4 import BeautifulSoup
    try:
        soup = BeautifulSoup(r.content, "lxml")
    except Exception:
        soup = BeautifulSoup(r.content, "html.parser")

    table = (
        soup.find("table", attrs={"class": _CLS_CENTER})
        or soup.find("table", attrs={"class": _CLS_PLAIN})
        or soup.find("table")
    )
    if table is None:
        raise BDShareError("Extended market data table not found.")

    rows = []
    for row in table.find_all("tr")[1:]:
        cols = row.find_all("td")
        if len(cols) < 9:
            continue
        try:
            rows.append({
                "Date":                          cols[0].text.strip(),
                "Total Trade":                   _safe_num(cols[1].text, int),
                "Total Volume":                  _safe_num(cols[2].text, int),
                "Total Value in Taka(mn)":       _safe_num(cols[3].text, float),
                "Total Market Cap. in Taka(mn)": _safe_num(cols[4].text, float),
                "DSEX Index":                    _safe_num(cols[5].text, float),
                "DSES Index":                    _safe_num(cols[6].text, float),
                "DS30 Index":                    _safe_num(cols[7].text, float),
                "DGEN Index":                    _safe_num(cols[8].text.replace("-", "0"), float),
            })
        except (IndexError, AttributeError) as exc:
            logger.warning("Skipping malformed extended market row: %s", exc)

    if not rows:
        raise BDShareError("No extended market data found.")

    df = pd.DataFrame(rows)
    if index == "date" and "Date" in df.columns:
        df = df.set_index("Date")
    return df.sort_index(ascending=True)


def get_market_depth_data(symbol: str, retry_count: int = 3, pause: float = 0.2) -> pd.DataFrame:
    """Get market depth (order book) for a specific symbol."""
    from bdshare.util.helper import _session
    import time

    for attempt in range(retry_count):
        time.sleep(pause * (2 ** attempt))
        try:
            # Establish referer cookie first (required by DSE)
            _session.head(vs.DSE_URL + vs.DSE_MARKET_DEPTH_REFERER_URL, timeout=10)
            _session.headers.update({"X-Requested-With": "XMLHttpRequest"})
            r = _session.post(
                vs.DSE_URL + vs.DSE_MARKET_DEPTH_URL,
                data={"inst": symbol},
                timeout=10,
            )
            r.raise_for_status()
            break
        except Exception as exc:
            if attempt == retry_count - 1:
                raise BDShareError(
                    f"Failed to fetch market depth for {symbol}: {exc}"
                ) from exc

    from bs4 import BeautifulSoup
    try:
        soup = BeautifulSoup(r.content, "html5lib")
    except Exception:
        soup = BeautifulSoup(r.content, "html.parser")

    table = soup.find("table", attrs={"class": _CLS_STRIPPED})
    if table is None:
        raise BDShareError(f"Market depth table not found for {symbol}.")

    result = []
    matrix = ["buy_price", "buy_volume", "sell_price", "sell_volume"]

    for row in table.find_all("tr")[:1]:
        cols = row.find_all("td", valign="top")
        for idx, mainrow in enumerate(cols):
            for inner_row in mainrow.find_all("tr")[2:]:
                newcols = inner_row.find_all("td")
                if len(newcols) >= 2:
                    m = idx * 2
                    result.append({
                        matrix[m]:     _safe_num(newcols[0].text, float),
                        matrix[m + 1]: _safe_num(newcols[1].text, int),
                    })

    if not result:
        raise BDShareError(f"No market depth data parsed for {symbol}.")
    return pd.DataFrame(result)


def get_sector_performance(retry_count: int = 3, pause: float = 0.2) -> pd.DataFrame:
    """Get sector-wise performance data."""
    table = _fetch_table(
        vs.DSE_URL + vs.DSE_SECTOR_PERF_URL,
        vs.DSE_ALT_URL + vs.DSE_SECTOR_PERF_URL,
        retries=retry_count,
        pause=pause,
    )
    rows = []
    for row in table.find_all("tr")[1:]:
        cols = row.find_all("td")
        if len(cols) < 2:
            continue
        rows.append({
            c["class"][0] if c.get("class") else f"col_{i}": c.text.strip()
            for i, c in enumerate(cols)
        })

    if not rows:
        raise BDShareError("No sector performance data found.")
    return pd.DataFrame(rows)


def get_top_gainers_losers(limit: int = 10, retry_count: int = 3, pause: float = 0.2) -> pd.DataFrame:
    """Get top gainers and losers."""
    table = _fetch_table(
        vs.DSE_URL + vs.DSE_TOP_GAINERS_URL,
        vs.DSE_ALT_URL + vs.DSE_TOP_GAINERS_URL,
        retries=retry_count,
        pause=pause,
        table_class=_CLS_FIXED,
    )
    rows = []
    for row in table.find_all("tr")[1:limit + 1]:
        cols = row.find_all("td")
        if len(cols) < 4:
            continue
        rows.append({
            "symbol": cols[1].text.strip(),
            "ltp":    _safe_num(cols[2].text, float),
            "change": _safe_num(cols[3].text, float),
        })

    if not rows:
        raise BDShareError("No top gainers/losers data found.")
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Deprecated aliases — old short names, will be removed in 2.0.0.
# ---------------------------------------------------------------------------

def get_market_inf(retry_count: int = 3, pause: float = 0.2) -> pd.DataFrame:
    """Deprecated: use get_market_info() instead."""
    import warnings
    warnings.warn(
        "get_market_inf() is deprecated. Use get_market_info() instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return get_market_info(retry_count=retry_count, pause=pause)


def get_market_inf_more_data(
    start=None, end=None, index=None, retry_count=3, pause=0.2,
) -> pd.DataFrame:
    """Deprecated: use get_market_info_more_data() instead."""
    import warnings
    warnings.warn(
        "get_market_inf_more_data() is deprecated. Use get_market_info_more_data() instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return get_market_info_more_data(start=start, end=end, index=index,
                                     retry_count=retry_count, pause=pause)


def get_company_inf(symbol: str, retry_count: int = 3, pause: float = 0.2) -> list:
    """Deprecated: use get_company_info() instead."""
    import warnings
    warnings.warn(
        "get_company_inf() is deprecated. Use get_company_info() instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return get_company_info(symbol, retry_count=retry_count, pause=pause)