import logging
import pandas as pd
from typing import Optional
from bdshare.util import vars as vs
from bdshare.util.helper import (
    _fetch_table, _safe_num, _rows, _cells, BDShareError, deprecated, _to_frame, safe_get,
    _fetch_json, _fetch_json_pages, _date_range, _with_fallback,
)

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
    for row in _rows(table)[1:]:
        cols = _cells(row)
        if len(cols) < 11:
            continue
        rows.append({
            "symbol": cols[1].strip(),
            "ltp":    _safe_num(cols[2], float),
            "high":   _safe_num(cols[3], float),
            "low":    _safe_num(cols[4], float),
            "close":  _safe_num(cols[5], float),
            "ycp":    _safe_num(cols[6], float),
            "change": _safe_num(cols[7], float),
            "trade":  _safe_num(cols[8], int),
            "value":  _safe_num(cols[9], float),
            "volume": _safe_num(cols[10], int),
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


def _parse_historical_rows(table) -> list:
    """Parse all OHLCV + metadata columns from a DSE day-end archive table."""
    rows = []
    for row in _rows(table)[1:]:
        cols = _cells(row)
        if len(cols) < 12:
            continue
        rows.append({
            "date":   cols[1].strip(),
            "symbol": cols[2].strip(),
            "ltp":    _safe_num(cols[3], float),
            "high":   _safe_num(cols[4], float),
            "low":    _safe_num(cols[5], float),
            "open":   _safe_num(cols[6], float),
            "close":  _safe_num(cols[7], float),
            "ycp":    _safe_num(cols[8], float),
            "trade":  _safe_num(cols[9], int),
            "value":  _safe_num(cols[10], float),
            "volume": _safe_num(cols[11], int),
        })
    return rows


def _fetch_archive_table(
    start: Optional[str],
    end: Optional[str],
    code: str,
    retry_count: int,
    pause: float,
) -> object:
    """Fetch the DSE day-end archive table for the given parameters."""
    return _fetch_table(
        vs.DSE_LEGACY_URL + vs.DSE_DEA_URL,
        params={"startDate": start, "endDate": end, "inst": code, "archive": "data"},
        retries=retry_count,
        pause=pause,
        table_class=_CLS_FIXED,
    )


def _change(ltp, ycp, percent):
    """Absolute change as shown on the legacy LSP page; None when untraded."""
    if percent is None or ltp is None or ycp is None:
        return None
    return round(ltp - ycp, 2)


def _trade_rows_new(retry_count: int, pause: float) -> list:
    """Live trade rows for the main (PUBLIC) board from dsebd.org."""
    data = _fetch_json(vs.DSE_API_PRICES, retries=retry_count, pause=pause)
    cols = data["cols"]
    rows = []
    for values in data["rows"]:
        r = dict(zip(cols, values))
        if r.get("board") != "PUBLIC":  # the legacy page lists only this board
            continue
        rows.append({
            "symbol": r["code"],
            "ltp":    r["ltp"],
            "high":   r["high"],
            "low":    r["low"],
            "close":  r["close"],
            "ycp":    r["ycp"],
            "change": _change(r["ltp"], r["ycp"], r.get("percent")),
            "trade":  r["trades"],
            "value":  r["value"],
            "volume": r["volume"],
        })
    return rows


def _trade_rows(retry_count: int, pause: float) -> list:
    """Live trade rows (legacy LSP page, falling back to dsebd.org)."""
    def legacy():
        return _parse_trade_rows(_fetch_table(
            vs.DSE_LEGACY_URL + vs.DSE_LSP_URL,
            retries=retry_count,
            pause=pause,
            table_class=_CLS_FIXED,
        ))
    return _with_fallback(legacy, lambda: _trade_rows_new(retry_count, pause),
                          "Current trade data")


def _day_end_rows_new(start: str, end: str, code: Optional[str], retry_count: int, pause: float) -> list:
    """
    Raw dsebd.org day-end archive rows for one instrument or all of them.

    The endpoint returns 500 rows per page (one day of all instruments is
    about 650), so every page of the range is fetched, in parallel.
    """
    params = {"from": start, "to": end}
    if code:
        params["inst"] = code
    return _fetch_json_pages(vs.DSE_API_DAY_END, params, retries=retry_count, pause=pause)


def _historical_rows_new(start, end, code, retry_count, pause) -> list:
    """Day-end archive rows from dsebd.org, in the legacy row schema."""
    start, end = _date_range(start, end)
    inst = None if not code or code == "All Instrument" else code
    return [
        {
            "date":   r["date"],
            "symbol": r["tradingCode"],
            "ltp":    r["ltp"],
            "high":   r["high"],
            "low":    r["low"],
            "open":   r["openp"],
            "close":  r["closep"],
            "ycp":    r["ycp"],
            "trade":  r["trade"],
            "value":  r["value"],
            "volume": r["volume"],
        }
        for r in _day_end_rows_new(start, end, inst, retry_count, pause)
    ]


def _historical_rows(start, end, code, retry_count, pause) -> list:
    """Day-end archive rows (legacy archive page, falling back to dsebd.org)."""
    def legacy():
        rows = _parse_historical_rows(_fetch_archive_table(start, end, code, retry_count, pause))
        if not rows:
            raise BDShareError("No historical data found.")
        return rows
    return _with_fallback(
        legacy,
        lambda: _historical_rows_new(start, end, code, retry_count, pause),
        "Historical data",
    )


# ---------------------------------------------------------------------------
# Public API  (canonical names as of v1.1.5)
# ---------------------------------------------------------------------------

def get_current_trade_data(
    symbol: Optional[str] = None,
    retry_count: int = 3,
    pause: float = 0.2,
    as_polars: bool = False,
) -> pd.DataFrame:
    """
    Get live trade data (last stock prices) for all symbols or a specific one.

    :param symbol: Instrument symbol e.g. 'ACI' (case-insensitive). None returns all.
    :param retry_count: Number of fetch attempts.
    :param pause: Base pause in seconds (exponential back-off applied).
    :param as_polars: Return a polars DataFrame instead of pandas (requires polars installed).
    :return: DataFrame - symbol, ltp, high, low, close, ycp, change, trade, value, volume.
    """
    rows = _trade_rows(retry_count, pause)
    if not rows:
        raise BDShareError("No current trade data found.")
    return _to_frame(_filter_symbol(pd.DataFrame(rows), symbol), as_polars)


def get_dsex_data(
    symbol: Optional[str] = None,
    retry_count: int = 3,
    pause: float = 0.2,
    as_polars: bool = False,
) -> pd.DataFrame:
    """
    Get DSEX index share price data.

    :param symbol: Optional symbol filter.
    :param as_polars: Return a polars DataFrame instead of pandas (requires polars installed).
    :return: DataFrame with the same schema as get_current_trade_data,
             except ``change`` is the percentage change.
    """
    def legacy():
        rows = _parse_trade_rows(_fetch_table(
            vs.DSE_LEGACY_URL + vs.DSEX_INDEX_VALUE,
            retries=retry_count,
            pause=pause,
            table_class=_CLS_SHARES,
        ))
        if not rows:
            raise BDShareError("No DSEX data found.")
        return rows

    def new():
        data = _fetch_json(vs.DSE_API_INDEX_CONSTITUENTS, {"code": "DSEX"},
                           retries=retry_count, pause=pause)
        rows = [
            {
                "symbol": r["code"],
                "ltp":    r["ltp"],
                "high":   r["high"],
                "low":    r["low"],
                "close":  r["closep"],
                "ycp":    r["ycp"],
                # the legacy page's "% CHANGE" column, shown to 2 decimals
                "change": (None if not r.get("ltp") or r.get("changePct") is None
                           else round(r["changePct"], 2)),
                "trade":  r["trades"],
                "value":  r["value"],
                "volume": r["volume"],
            }
            for r in data.get("rows") or []
        ]
        return sorted(rows, key=lambda r: r["symbol"])

    rows = _with_fallback(legacy, new, "DSEX data")
    if not rows:
        raise BDShareError("No DSEX data found.")
    return _to_frame(_filter_symbol(pd.DataFrame(rows), symbol), as_polars)


def get_current_trading_code(retry_count: int = 3, pause: float = 0.2, as_polars: bool = False) -> pd.DataFrame:
    """
    Get the list of all currently traded stock symbols.

    :param as_polars: Return a polars DataFrame instead of pandas (requires polars installed).
    :return: Single-column DataFrame with column 'symbol'.
    """
    rows = [{"symbol": r["symbol"]} for r in _trade_rows(retry_count, pause)]
    if not rows:
        raise BDShareError("No trading codes found.")
    return _to_frame(pd.DataFrame(rows), as_polars)


def get_historical_data(
    start: Optional[str] = None,
    end: Optional[str] = None,
    code: str = "All Instrument",
    retry_count: int = 3,
    pause: float = 0.2,
    as_polars: bool = False,
) -> pd.DataFrame:
    """
    Get full historical OHLCV + metadata, indexed by date (descending).

    :param start: Start date 'YYYY-MM-DD'.
    :param end:   End date 'YYYY-MM-DD'.
    :param code:  Instrument symbol or 'All Instrument'.
    :param as_polars: Return a polars DataFrame instead of pandas (requires polars installed).
    :return: DataFrame indexed by date - symbol, ltp, high, low, open, close,
             ycp, trade, value, volume.
    """
    rows = _historical_rows(start, end, code, retry_count, pause)
    if not rows:
        raise BDShareError("No historical data found.")
    return _to_frame(pd.DataFrame(rows).set_index("date").sort_index(ascending=False), as_polars)


def get_basic_historical_data(
    start: Optional[str] = None,
    end: Optional[str] = None,
    code: str = "All Instrument",
    index: Optional[str] = None,
    retry_count: int = 3,
    pause: float = 0.2,
    as_polars: bool = False,
) -> pd.DataFrame:
    """
    Get simplified historical OHLCV, sorted ascending (TA-library ready).

    :param index: Pass 'date' to set date as the DataFrame index.
    :param as_polars: Return a polars DataFrame instead of pandas (requires polars installed).
    :return: DataFrame - date (or index), open, high, low, close, volume.
    """
    rows = _historical_rows(start, end, code, retry_count, pause)
    if not rows:
        raise BDShareError("No basic historical data found.")
    df = pd.DataFrame(rows)[["date", "open", "high", "low", "close", "volume"]]
    if index == "date":
        df = df.set_index("date")
    return _to_frame(df.sort_index(ascending=True), as_polars)


def get_close_price_data(
    start: Optional[str] = None,
    end: Optional[str] = None,
    code: str = "All Instrument",
    retry_count: int = 3,
    pause: float = 0.2,
    as_polars: bool = False,
) -> pd.DataFrame:
    """
    Get closing prices and prior close (ycp), indexed by date (descending).

    :param as_polars: Return a polars DataFrame instead of pandas (requires polars installed).
    :return: DataFrame - symbol, close, ycp.
    """
    def legacy():
        table = _fetch_table(
            vs.DSE_LEGACY_URL + vs.DSE_CLOSE_PRICE_URL,
            params={"startDate": start, "endDate": end, "inst": code, "archive": "data"},
            retries=retry_count,
            pause=pause,
            table_class=_CLS_PLAIN,
        )
        rows = []
        for row in _rows(table)[1:]:
            cols = _cells(row)
            if len(cols) < 5:
                continue
            rows.append({
                "date":   cols[1].strip(),
                "symbol": cols[2].strip(),
                "close":  _safe_num(cols[3], float),
                "ycp":    _safe_num(cols[4], float),
            })
        if not rows:
            raise BDShareError("No close price data found.")
        return rows

    def new():
        return [
            {"date": r["date"], "symbol": r["symbol"], "close": r["close"], "ycp": r["ycp"]}
            for r in _historical_rows_new(start, end, code, retry_count, pause)
        ]

    rows = _with_fallback(legacy, new, "Close price data")
    if not rows:
        raise BDShareError("No close price data found.")
    return _to_frame(pd.DataFrame(rows).set_index("date").sort_index(ascending=False), as_polars)


def get_last_trade_price_data(retry_count: int = 3, pause: float = 0.2, as_polars: bool = False) -> pd.DataFrame:
    """
    Get the last trade price of every main-board instrument.

    The figures match the legacy site's ``quotes.txt``: the last trade price
    during the session, the closing price after it.

    :param as_polars: Return a polars DataFrame instead of pandas (requires polars installed).
    :return: DataFrame - symbol, ltp.
    """
    def legacy():
        r = safe_get(
            vs.DSE_LEGACY_URL + "datafile/quotes.txt",
            retries=retry_count,
            pause=pause,
        )
        return _parse_quotes(r.text)

    def new():
        data = _fetch_json(vs.DSE_API_PRICES, retries=retry_count, pause=pause)
        cols = data["cols"]
        rows = (dict(zip(cols, values)) for values in data["rows"])
        return sorted(
            (r["code"], r["close"] or r["ltp"])
            for r in rows if r.get("board") == "PUBLIC"
        )

    df = pd.DataFrame(_with_fallback(legacy, new, "Last trade prices"), columns=["symbol", "ltp"])
    if df.empty:
        raise BDShareError("No last trade price data found.")
    return _to_frame(df, as_polars)


def _parse_quotes(text: str) -> list:
    """
    Parse quotes.txt: a two-line title and column header, then one
    ``CODE <tabs> PRICE`` line per instrument.
    """
    rows = []
    for line in text.splitlines():
        parts = line.split()
        if len(parts) != 2:
            continue
        price = _safe_num(parts[1], float)
        if price is not None:
            rows.append((parts[0], price))
    return rows


# ---------------------------------------------------------------------------
# Deprecated aliases — old short names, will be removed in 2.0.0.
# ---------------------------------------------------------------------------

@deprecated("Use get_historical_data() instead.")
def get_hist_data(
    start=None, end=None, code="All Instrument",
    retry_count=3, pause=0.2, as_polars: bool = False,
):
    return get_historical_data(start=start, end=end, code=code,
                               retry_count=retry_count, pause=pause, as_polars=as_polars)


@deprecated("Use get_basic_historical_data() instead.")
def get_basic_hist_data(
    start=None, end=None, code="All Instrument",
    index=None, retry_count=3, pause=0.2, as_polars: bool = False,
):
    return get_basic_historical_data(start=start, end=end, code=code, index=index,
                                     retry_count=retry_count, pause=pause, as_polars=as_polars)
