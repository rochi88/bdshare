import logging
import pandas as pd
from io import BytesIO
from typing import Optional
from bdshare.util import vars as vs
from bdshare.util.helper import (
    _fetch_table, _safe_num, _parse_html,
    safe_get, safe_post,
    BDShareError, _session, deprecated,
    _to_frame,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Table class constants
# ---------------------------------------------------------------------------
_CLS_FIXED    = "table table-bordered background-white shares-table fixedHeader"
_CLS_SHARES   = "table table-bordered background-white shares-table"
_CLS_CENTER   = "table table-bordered background-white text-center"
_CLS_PLAIN    = "table table-bordered background-white"
_CLS_STRIPPED = "table table-stripped"

# DSE displayCompany.php renders ~400 invisible layout/navigation tables before
# the actual company data tables begin; all earlier tables are structural noise.
_COMPANY_INFO_TABLE_OFFSET = 400


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def get_market_status(retry_count: int = 3, pause: float = 0.2) -> str:
    """Get current market status (Open, Closed, Holiday, etc.)."""
    r = safe_get(
        vs.DSE_URL,
        alt_url=vs.DSE_ALT_URL,
        retries=retry_count,
        pause=pause,
    )
    soup = _parse_html(r.content)
    for div_class in ("HeaderTop", "HeaderTopMobile"):
        header = soup.find("div", class_=div_class)
        if header is None:
            continue
        for span in header.find_all("span", class_="time"):
            if "Market Status" in span.text:
                status_span = span.find("span", class_="green") or span.find("b")
                if status_span:
                    return status_span.text.strip()
    raise BDShareError("Market status not found.")


def get_market_info(retry_count: int = 3, pause: float = 0.2, as_polars: bool = False) -> pd.DataFrame:
    """Get current market summary (indices, volumes, market cap).

    :param as_polars: Return a polars DataFrame instead of pandas (requires polars installed).
    """
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
    return _to_frame(pd.DataFrame(rows), as_polars)


def get_company_info(symbol: str, retry_count: int = 3, pause: float = 0.2, as_polars: bool = False) -> list:
    """
    Get company information tables for a given symbol.

    :param as_polars: Return polars DataFrames instead of pandas (requires polars installed).
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
        tables = pd.read_html(BytesIO(r.content))
        result = tables[_COMPANY_INFO_TABLE_OFFSET:]
        if as_polars:
            return [_to_frame(t, True) for t in result]
        return result
    except Exception as exc:
        raise BDShareError(f"Failed to parse company info for {symbol}: {exc}") from exc


def get_latest_pe(retry_count: int = 3, pause: float = 0.2, as_polars: bool = False) -> pd.DataFrame:
    """Get latest P/E ratios for all listed companies.

    :param as_polars: Return a polars DataFrame instead of pandas (requires polars installed).
    """
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
    return _to_frame(pd.DataFrame(rows), as_polars)


def get_market_info_more_data(
    start: Optional[str] = None,
    end: Optional[str] = None,
    code: Optional[str] = None,
    index: Optional[str] = None,
    retry_count: int = 3,
    pause: float = 0.2,
    as_polars: bool = False,
) -> pd.DataFrame:
    """Get extended historical market summary data via POST.

    Args:
        code: Optional index code to filter columns. One of:
              'DSEX', 'DSES', 'DS30', 'DGEN'. Returns all columns if None.
        as_polars: Return a polars DataFrame instead of pandas (requires polars installed).
    """
    _VALID_CODES = {"DSEX", "DSES", "DS30", "DGEN"}
    _CODE_COLUMN_MAP = {
        "DSEX": "DSEX Index",
        "DSES": "DSES Index",
        "DS30": "DS30 Index",
        "DGEN": "DGEN Index",
    }

    if code is not None and code.upper() not in _VALID_CODES:
        raise ValueError(
            f"Invalid code '{code}'. Must be one of: {', '.join(sorted(_VALID_CODES))}"
        )

    r = safe_post(
        vs.DSE_URL + vs.DSE_MARKET_INFO_MORE_URL,
        data={
            "startDate": start,
            "endDate": end,
            "searchRecentMarket": "Search Recent Market",
        },
        alt_url=vs.DSE_ALT_URL + vs.DSE_MARKET_INFO_MORE_URL,
        retries=retry_count,
        pause=pause,
    )

    soup = _parse_html(r.content)
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

    df = pd.DataFrame(rows, columns=[
        "Date", "Total Trade", "Total Volume", "Total Value in Taka(mn)",
        "Total Market Cap. in Taka(mn)", "DSEX Index", "DSES Index",
        "DS30 Index", "DGEN Index",
    ])

    if code is not None:
        target_col = _CODE_COLUMN_MAP[code.upper()]
        df = df[["Date", target_col]]

    if index == "date" and "Date" in df.columns:
        df = df.set_index("Date")

    return _to_frame(df.sort_index(ascending=True), as_polars)


def get_market_depth_data(symbol: str, retry_count: int = 3, pause: float = 0.2, as_polars: bool = False) -> pd.DataFrame:
    """Get market depth (order book) for a specific symbol.

    :param as_polars: Return a polars DataFrame instead of pandas (requires polars installed).
    """
    # Establish referer cookie and AJAX header before the POST (done once, not per retry).
    _session.head(vs.DSE_URL + vs.DSE_MARKET_DEPTH_REFERER_URL, timeout=10)
    _session.headers.update({"X-Requested-With": "XMLHttpRequest"})

    r = safe_post(
        vs.DSE_URL + vs.DSE_MARKET_DEPTH_URL,
        data={"inst": symbol},
        retries=retry_count,
        pause=pause,
    )

    soup = _parse_html(r.content)
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

    return _to_frame(pd.DataFrame(result), as_polars)


def get_sector_performance(retry_count: int = 3, pause: float = 0.2, as_polars: bool = False) -> pd.DataFrame:
    """Get sector-wise performance data.

    :param as_polars: Return a polars DataFrame instead of pandas (requires polars installed).
    """
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
    return _to_frame(pd.DataFrame(rows), as_polars)


def get_top_gainers_losers(limit: int = 10, retry_count: int = 3, pause: float = 0.2, as_polars: bool = False) -> pd.DataFrame:
    """Get top gainers and losers.

    :param as_polars: Return a polars DataFrame instead of pandas (requires polars installed).
    """
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
    return _to_frame(pd.DataFrame(rows), as_polars)


# ---------------------------------------------------------------------------
# Deprecated aliases — old short names, will be removed in 2.0.0.
# ---------------------------------------------------------------------------

@deprecated("Use get_market_info() instead.")
def get_market_inf(retry_count: int = 3, pause: float = 0.2, as_polars: bool = False) -> pd.DataFrame:
    return get_market_info(retry_count=retry_count, pause=pause, as_polars=as_polars)


@deprecated("Use get_market_info_more_data() instead.")
def get_market_inf_more_data(
    start=None, end=None, index=None, retry_count=3, pause=0.2, as_polars: bool = False,
) -> pd.DataFrame:
    return get_market_info_more_data(start=start, end=end, index=index,
                                     retry_count=retry_count, pause=pause, as_polars=as_polars)


@deprecated("Use get_company_info() instead.")
def get_company_inf(symbol: str, retry_count: int = 3, pause: float = 0.2, as_polars: bool = False) -> list:
    return get_company_info(symbol, retry_count=retry_count, pause=pause, as_polars=as_polars)
