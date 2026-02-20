import logging
import pandas as pd
from typing import Optional
from bdshare.util import vars as vs
from bdshare.util.helper import _fetch_table, _safe_num, safe_get, BDShareError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Table class constants
# ---------------------------------------------------------------------------
_CLS_FIXED  = "table table-bordered background-white shares-table fixedHeader"
_CLS_SHARES = "table table-bordered background-white shares-table"
_CLS_PLAIN  = "table table-bordered background-white"


# ---------------------------------------------------------------------------
# Shared internal helpers
# ---------------------------------------------------------------------------

def _parse_trade_rows(table) -> list:
    """Parse standard 10-column trade rows from a DSE table."""
    rows = []
    for row in table.find_all("tr")[1:]:
        cols = row.find_all("td")
        if len(cols) < 11:
            continue
        rows.append({
            "symbol": cols[1].text.strip(),
            "ltp":    _safe_num(cols[2].text, float),
            "high":   _safe_num(cols[3].text, float),
            "low":    _safe_num(cols[4].text, float),
            "close":  _safe_num(cols[5].text, float),
            "ycp":    _safe_num(cols[6].text, float),
            "change": _safe_num(cols[7].text, float),
            "trade":  _safe_num(cols[8].text, int),
            "value":  _safe_num(cols[9].text, float),
            "volume": _safe_num(cols[10].text, int),
        })
    return rows


def _filter_symbol(df: pd.DataFrame, symbol: Optional[str]) -> pd.DataFrame:
    """Filter DataFrame by symbol if provided; raise BDShareError if no match."""
    if not symbol:
        return df
    filtered = df[df["symbol"].str.upper() == symbol.upper()]
    if filtered.empty:
        raise BDShareError(f"Symbol not found: {symbol!r}")
    return filtered


# ---------------------------------------------------------------------------
# Public API  (canonical names as of v1.2.0)
# ---------------------------------------------------------------------------

def get_current_trade_data(
    symbol: Optional[str] = None,
    retry_count: int = 3,
    pause: float = 0.2,
) -> pd.DataFrame:
    """
    Get live trade data (last stock prices) for all symbols or a specific one.

    :param symbol: Instrument symbol e.g. 'ACI' (case-insensitive). None returns all.
    :param retry_count: Number of fetch attempts.
    :param pause: Base pause in seconds (exponential back-off applied).
    :return: DataFrame - symbol, ltp, high, low, close, ycp, change, trade, value, volume.
    """
    table = _fetch_table(
        vs.DSE_URL + vs.DSE_LSP_URL,
        vs.DSE_ALT_URL + vs.DSE_LSP_URL,
        retries=retry_count,
        pause=pause,
        table_class=_CLS_FIXED,
    )
    rows = _parse_trade_rows(table)
    if not rows:
        raise BDShareError("No current trade data found.")
    return _filter_symbol(pd.DataFrame(rows), symbol)


def get_dsex_data(
    symbol: Optional[str] = None,
    retry_count: int = 3,
    pause: float = 0.2,
) -> pd.DataFrame:
    """
    Get DSEX index share price data.

    :param symbol: Optional symbol filter.
    :return: DataFrame with the same schema as get_current_trade_data.
    """
    table = _fetch_table(
        vs.DSE_URL + vs.DSEX_INDEX_VALUE,
        vs.DSE_ALT_URL + vs.DSEX_INDEX_VALUE,
        retries=retry_count,
        pause=pause,
        table_class=_CLS_SHARES,
    )
    rows = _parse_trade_rows(table)
    if not rows:
        raise BDShareError("No DSEX data found.")
    return _filter_symbol(pd.DataFrame(rows), symbol)


def get_current_trading_code(retry_count: int = 3, pause: float = 0.2) -> pd.DataFrame:
    """
    Get the list of all currently traded stock symbols.

    :return: Single-column DataFrame with column 'symbol'.
    """
    table = _fetch_table(
        vs.DSE_URL + vs.DSE_LSP_URL,
        vs.DSE_ALT_URL + vs.DSE_LSP_URL,
        retries=retry_count,
        pause=pause,
        table_class=_CLS_FIXED,
    )
    rows = [
        {"symbol": row.find_all("td")[1].text.strip()}
        for row in table.find_all("tr")[1:]
        if len(row.find_all("td")) >= 2
    ]
    if not rows:
        raise BDShareError("No trading codes found.")
    return pd.DataFrame(rows)


def get_historical_data(
    start: Optional[str] = None,
    end: Optional[str] = None,
    code: str = "All Instrument",
    retry_count: int = 3,
    pause: float = 0.2,
) -> pd.DataFrame:
    """
    Get full historical OHLCV + metadata, indexed by date (descending).

    :param start: Start date 'YYYY-MM-DD'.
    :param end:   End date 'YYYY-MM-DD'.
    :param code:  Instrument symbol or 'All Instrument'.
    :return: DataFrame indexed by date - symbol, ltp, high, low, open, close,
             ycp, trade, value, volume.
    """
    params = {"startDate": start, "endDate": end, "inst": code, "archive": "data"}
    table = _fetch_table(
        vs.DSE_URL + vs.DSE_DEA_URL,
        vs.DSE_ALT_URL + vs.DSE_DEA_URL,
        params=params,
        retries=retry_count,
        pause=pause,
        table_class=_CLS_FIXED,
    )
    rows = []
    for row in table.find_all("tr")[1:]:
        cols = row.find_all("td")
        if len(cols) < 12:
            continue
        rows.append({
            "date":   cols[1].text.strip(),
            "symbol": cols[2].text.strip(),
            "ltp":    _safe_num(cols[3].text, float),
            "high":   _safe_num(cols[4].text, float),
            "low":    _safe_num(cols[5].text, float),
            "open":   _safe_num(cols[6].text, float),
            "close":  _safe_num(cols[7].text, float),
            "ycp":    _safe_num(cols[8].text, float),
            "trade":  _safe_num(cols[9].text, int),
            "value":  _safe_num(cols[10].text, float),
            "volume": _safe_num(cols[11].text, int),
        })
    if not rows:
        raise BDShareError("No historical data found.")
    return pd.DataFrame(rows).set_index("date").sort_index(ascending=False)


def get_basic_historical_data(
    start: Optional[str] = None,
    end: Optional[str] = None,
    code: str = "All Instrument",
    index: Optional[str] = None,
    retry_count: int = 3,
    pause: float = 0.2,
) -> pd.DataFrame:
    """
    Get simplified historical OHLCV, sorted ascending (TA-library ready).

    :param index: Pass 'date' to set date as the DataFrame index.
    :return: DataFrame - date (or index), open, high, low, close, volume.
    """
    params = {"startDate": start, "endDate": end, "inst": code, "archive": "data"}
    table = _fetch_table(
        vs.DSE_URL + vs.DSE_DEA_URL,
        vs.DSE_ALT_URL + vs.DSE_DEA_URL,
        params=params,
        retries=retry_count,
        pause=pause,
        table_class=_CLS_FIXED,
    )
    rows = []
    for row in table.find_all("tr")[1:]:
        cols = row.find_all("td")
        if len(cols) < 12:
            continue
        rows.append({
            "date":   cols[1].text.strip(),
            "open":   _safe_num(cols[6].text, float),
            "high":   _safe_num(cols[4].text, float),
            "low":    _safe_num(cols[5].text, float),
            "close":  _safe_num(cols[7].text, float),
            "volume": _safe_num(cols[11].text, int),
        })
    if not rows:
        raise BDShareError("No basic historical data found.")
    df = pd.DataFrame(rows)
    if index == "date":
        df = df.set_index("date")
    return df.sort_index(ascending=True)


def get_close_price_data(
    start: Optional[str] = None,
    end: Optional[str] = None,
    code: str = "All Instrument",
    retry_count: int = 3,
    pause: float = 0.2,
) -> pd.DataFrame:
    """
    Get closing prices and prior close (ycp), indexed by date (descending).

    :return: DataFrame - symbol, close, ycp.
    """
    params = {"startDate": start, "endDate": end, "inst": code, "archive": "data"}
    table = _fetch_table(
        vs.DSE_URL + vs.DSE_CLOSE_PRICE_URL,
        vs.DSE_ALT_URL + vs.DSE_CLOSE_PRICE_URL,
        params=params,
        retries=retry_count,
        pause=pause,
        table_class=_CLS_PLAIN,
    )
    rows = []
    for row in table.find_all("tr")[1:]:
        cols = row.find_all("td")
        if len(cols) < 5:
            continue
        rows.append({
            "date":   cols[1].text.strip(),
            "symbol": cols[2].text.strip(),
            "close":  _safe_num(cols[3].text, float),
            "ycp":    _safe_num(cols[4].text, float),
        })
    if not rows:
        raise BDShareError("No close price data found.")
    return pd.DataFrame(rows).set_index("date").sort_index(ascending=False)


def get_last_trade_price_data(retry_count: int = 3, pause: float = 0.2) -> pd.DataFrame:
    """
    Get last trade price data from the DSE fixed-width text file.

    :return: DataFrame parsed from dsebd.org/datafile/quotes.txt.
    """
    import time
    for attempt in range(retry_count):
        time.sleep(pause * (2 ** attempt))
        try:
            df = pd.read_fwf(
                "https://dsebd.org/datafile/quotes.txt",
                sep="\t",
                skiprows=4,
            )
            if not df.empty:
                return df
        except Exception as exc:
            logger.error("Attempt %d failed for quotes.txt: %s", attempt + 1, exc)
    raise BDShareError(f"Failed to fetch quotes.txt after {retry_count} retries.")


# ---------------------------------------------------------------------------
# Deprecated aliases — old short names, will be removed in 2.0.0.
# ---------------------------------------------------------------------------

def get_hist_data(
    start=None, end=None, code="All Instrument",
    retry_count=3, pause=0.2,
):
    """Deprecated: use get_historical_data() instead."""
    import warnings
    warnings.warn(
        "get_hist_data() is deprecated. Use get_historical_data() instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return get_historical_data(start=start, end=end, code=code,
                               retry_count=retry_count, pause=pause)


def get_basic_hist_data(
    start=None, end=None, code="All Instrument",
    index=None, retry_count=3, pause=0.2,
):
    """Deprecated: use get_basic_historical_data() instead."""
    import warnings
    warnings.warn(
        "get_basic_hist_data() is deprecated. Use get_basic_historical_data() instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return get_basic_historical_data(start=start, end=end, code=code, index=index,
                                     retry_count=retry_count, pause=pause)