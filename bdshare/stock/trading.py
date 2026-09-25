import io
import logging
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
from typing import Optional
from bdshare.util import vars as vs
from bdshare.util.helper import (
    _fetch_table, _safe_num, BDShareError, deprecated, _to_frame, safe_get,
    _fetch_json, _fetch_json_range, _date_range, _with_fallback,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Table class constants
# ---------------------------------------------------------------------------
_CLS_FIXED  = "table table-bordered background-white shares-table fixedHeader"
_CLS_SHARES = "table table-bordered background-white shares-table"
_CLS_PLAIN  = "table table-bordered background-white"

# dsebd.org's day-end archive endpoint returns at most this many rows.
_DAY_END_CAP = 500
# Parallel requests used to fill in instruments cut off by that cap
# (stays under requests' default per-host pool size of 10).
_DAY_END_WORKERS = 8


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


def _parse_historical_rows(table) -> list:
    """Parse all OHLCV + metadata columns from a DSE day-end archive table."""
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
        vs.DSE_LEGACY_ALT_URL + vs.DSE_DEA_URL,
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
            vs.DSE_LEGACY_ALT_URL + vs.DSE_LSP_URL,
            retries=retry_count,
            pause=pause,
            table_class=_CLS_FIXED,
        ))
    return _with_fallback(legacy, lambda: _trade_rows_new(retry_count, pause),
                          "Current trade data")


def _day_end_rows_new(start: str, end: str, code: Optional[str], retry_count: int, pause: float) -> list:
    """
    Raw dsebd.org day-end archive rows for one instrument or all of them.

    The endpoint returns at most 500 rows per request with no paging, and one
    day of all instruments exceeds that, so a single capped day is cut off
    alphabetically. Instruments missing from a capped day are therefore
    fetched one at a time over the whole range (each fits under the cap).
    """
    if code:
        return _fetch_json_range(vs.DSE_API_DAY_END, start, end, {"inst": code},
                                 retries=retry_count, pause=pause)

    rows = _fetch_json_range(vs.DSE_API_DAY_END, start, end,
                             retries=retry_count, pause=pause)
    codes_by_date: dict = {}
    for r in rows:
        codes_by_date.setdefault(r["date"], set()).add(r["tradingCode"])
    capped = [codes for codes in codes_by_date.values() if len(codes) >= _DAY_END_CAP]
    if not capped:
        return rows

    instruments = _fetch_json(vs.DSE_API_DAY_END_INSTRUMENTS, retries=retry_count,
                              pause=pause).get("instruments") or []
    missing = sorted({i for i in instruments for codes in capped if i not in codes})
    logger.info("Day-end archive capped at %d rows; fetching %d instruments individually",
                _DAY_END_CAP, len(missing))
    def fetch(inst):
        return _fetch_json_range(vs.DSE_API_DAY_END, start, end, {"inst": inst},
                                 retries=retry_count, pause=pause)

    seen = {(r["date"], r["tradingCode"]) for r in rows}
    with ThreadPoolExecutor(max_workers=_DAY_END_WORKERS) as pool:
        for inst_rows in pool.map(fetch, missing):
            for r in inst_rows:
                if (r["date"], r["tradingCode"]) not in seen:
                    seen.add((r["date"], r["tradingCode"]))
                    rows.append(r)
    return rows


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
            vs.DSE_LEGACY_ALT_URL + vs.DSEX_INDEX_VALUE,
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
            vs.DSE_LEGACY_ALT_URL + vs.DSE_CLOSE_PRICE_URL,
            params={"startDate": start, "endDate": end, "inst": code, "archive": "data"},
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
    Get last trade price data from the DSE fixed-width text file.

    :param as_polars: Return a polars DataFrame instead of pandas (requires polars installed).
    :return: DataFrame parsed from dsebd.org/datafile/quotes.txt.
    """
    # dsebd.org has no quotes.txt of its own; it redirects to the legacy file.
    r = safe_get(
        vs.DSE_LEGACY_URL + "datafile/quotes.txt",
        alt_url=vs.DSE_LEGACY_ALT_URL + "datafile/quotes.txt",
        retries=retry_count,
        pause=pause,
    )
    df = pd.read_fwf(io.BytesIO(r.content), sep="\t", skiprows=4)
    if df.empty:
        raise BDShareError("quotes.txt returned an empty dataset.")
    return _to_frame(df, as_polars)


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
