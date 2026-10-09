import logging
import lxml.html
import pandas as pd
from datetime import date, timedelta
from io import BytesIO
from typing import Any, Optional
from urllib.parse import quote
from bdshare.util import vars as vs
from bdshare.util.helper import (
    _fetch_table, _safe_num, _parse_html, _find, _find_all, _first, _rows, _cells,
    safe_get, safe_post,
    BDShareError, _session, deprecated,
    _to_frame, _fetch_json, _fetch_json_range, _date_range, _dhaka_today,
    _with_fallback, _rsc_rows, _rsc_resolve, _rsc_find,
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

# The legacy recent_market_information.php page lists the last 30 sessions.
_MARKET_INFO_ROWS = 30

# dsebd.org's recent-market-info endpoint returns at most this many rows.
_RECENT_MARKET_INFO_CAP = 400


def _to_legacy_date(iso: str) -> str:
    """'2026-09-24' → '24-09-2026', the legacy market-summary date format."""
    return date.fromisoformat(iso).strftime("%d-%m-%Y")


def _market_summary_rows_new(
    start: str, end: str, value_col: str, cap_col: str, retry_count: int, pause: float,
) -> list:
    """Daily market summary rows from dsebd.org, newest first.

    ``value_col``/``cap_col`` are the turnover and market-cap column names,
    which differ between the legacy pages this mirrors.
    """
    return [
        {
            "Date":         _to_legacy_date(r["date"]),
            "Total Trade":  r["trades"],
            "Total Volume": r["volume"],
            value_col:      r["value"],
            # the API reports market cap in Taka; the legacy pages in millions
            cap_col:        None if r.get("marketCap") is None else round(r["marketCap"] / 1e6, 3),
            "DSEX Index":   r["dsex"],
            "DSES Index":   r["dses"],
            "DS30 Index":   r["ds30"],
            "DGEN Index":   r["dgen"],
        }
        for r in _fetch_json_range(vs.DSE_API_RECENT_MARKET_INFO, start, end,
                                   retries=retry_count, pause=pause,
                                   max_rows=_RECENT_MARKET_INFO_CAP)
    ]


def _company_tables_html(content: bytes) -> bytes:
    """
    The company page reduced to its data tables (those from
    ``_COMPANY_INFO_TABLE_OFFSET`` on), so pandas only converts those
    instead of all ~400 layout tables.
    """
    tables = _parse_html(content).xpath("//table")[_COMPANY_INFO_TABLE_OFFSET:]
    # A table nested in another kept table is serialised with its parent,
    # and pandas finds it there again; emitting it twice would duplicate it.
    kept = set(tables)
    top = [t for t in tables if not any(a in kept for a in t.iterancestors("table"))]
    return b"<html><body>" + b"".join(lxml.html.tostring(t) for t in top) + b"</body></html>"


def _price_rows_new(retry_count: int, pause: float) -> list:
    """Main-board (PUBLIC) price rows from dsebd.org as dicts."""
    data = _fetch_json(vs.DSE_API_PRICES, retries=retry_count, pause=pause)
    cols = data["cols"]
    rows = (dict(zip(cols, values)) for values in data["rows"])
    return [r for r in rows if r.get("board") == "PUBLIC"]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def get_market_status(retry_count: int = 3, pause: float = 0.2) -> str:
    """Get current market status (Open, Closed, Holiday, etc.)."""
    def legacy():
        r = safe_get(
            vs.DSE_LEGACY_URL,
            retries=retry_count,
            pause=pause,
        )
        root = _parse_html(r.content)
        for div_class in ("HeaderTop", "HeaderTopMobile"):
            header = _find(root, "div", div_class)
            if header is None:
                continue
            for span in _find_all(header, "span", "time"):
                if "Market Status" in span.text_content():
                    status_span = _first(_find(span, "span", "green"), _find(span, "b"))
                    if status_span is not None:
                        return status_span.text_content().strip()
        raise BDShareError("Market status not found.")

    def new():
        data = _fetch_json(vs.DSE_API_MARKET, retries=retry_count, pause=pause)
        phase = (data.get("session") or {}).get("phase")
        if not phase:
            raise BDShareError("Market status not found.")
        return phase.replace("_", " ").title()  # "closed" → "Closed"

    return _with_fallback(legacy, new, "Market status")


def get_market_info(retry_count: int = 3, pause: float = 0.2, as_polars: bool = False) -> pd.DataFrame:
    """Get current market summary (indices, volumes, market cap).

    :param as_polars: Return a polars DataFrame instead of pandas (requires polars installed).
    """
    def legacy():
        table = _fetch_table(
            vs.DSE_LEGACY_URL + vs.DSE_MARKET_INFO_URL,
            retries=retry_count,
            pause=pause,
            table_class=_CLS_CENTER,
            table_id="data-table",
        )
        rows = []
        for row in _rows(table)[1:]:
            cols = _cells(row)
            if len(cols) < 9:
                continue
            rows.append({
                "Date":                   cols[0].strip(),
                "Total Trade":            _safe_num(cols[1], int),
                "Total Volume":           _safe_num(cols[2], int),
                "Total Value (mn)":       _safe_num(cols[3], float),
                "Total Market Cap. (mn)": _safe_num(cols[4], float),
                "DSEX Index":             _safe_num(cols[5], float),
                "DSES Index":             _safe_num(cols[6], float),
                "DS30 Index":             _safe_num(cols[7], float),
                "DGEN Index":             _safe_num(cols[8], float),
            })
        if not rows:
            raise BDShareError("No market info data found.")
        return rows

    def new():
        # 30 sessions span roughly six weeks; fetch generously, keep the newest 30.
        end = _dhaka_today()
        start = (date.fromisoformat(end) - timedelta(days=90)).isoformat()
        rows = _market_summary_rows_new(start, end, "Total Value (mn)",
                                        "Total Market Cap. (mn)", retry_count, pause)
        return rows[:_MARKET_INFO_ROWS]

    rows = _with_fallback(legacy, new, "Market info")
    if not rows:
        raise BDShareError("No market info data found.")
    return _to_frame(pd.DataFrame(rows), as_polars)


@deprecated("It reads the legacy site's company page. "
            "Use get_company_details() for the current site's company data.")
def get_company_info(symbol: str, retry_count: int = 3, pause: float = 0.2, as_polars: bool = False) -> list:
    """
    Get company information tables for a given symbol from the legacy site.

    .. deprecated:: 1.2.8
       Use :func:`get_company_details`, which returns the current site's
       company data (profile, capital, AGM date, shareholding, dividends,
       financials) as a dict.

    :param as_polars: Return polars DataFrames instead of pandas (requires polars installed).
    :return: list of DataFrames (relevant tables start at index 400 in the page).
    """
    r = safe_get(
        vs.DSE_LEGACY_URL + vs.DSE_COMPANY_INFO_URL,
        params={"name": symbol},
        retries=retry_count,
        pause=pause,
    )
    try:
        result = pd.read_html(BytesIO(_company_tables_html(r.content)))
        if as_polars:
            return [_to_frame(t, True) for t in result]
        return result
    except Exception as exc:
        raise BDShareError(f"Failed to parse company info for {symbol}: {exc}") from exc


# Paging state in the company page payload, not company data.
_COMPANY_DETAILS_DROP = {"disclosuresNextCursor"}


def _tabulate(value: Any, as_polars: bool) -> Any:
    """Turn the tabular parts of a company payload into DataFrames.

    A list of records becomes one row per record (nested dicts flattened
    into ``parent_child`` columns); a dict of equal-length lists becomes one
    column per key. Other values are returned as they are.
    """
    if isinstance(value, list) and all(isinstance(v, dict) for v in value):
        return _to_frame(pd.json_normalize(value, sep="_") if value else pd.DataFrame(), as_polars)
    if isinstance(value, dict):
        lists = list(value.values())
        if lists and all(isinstance(v, list) and not any(isinstance(x, dict) for x in v)
                         for v in lists) and len({len(v) for v in lists}) == 1:
            return _to_frame(pd.DataFrame(value), as_polars)
        return {k: _tabulate(v, as_polars) for k, v in value.items()}
    return value


def get_company_details(symbol: str, retry_count: int = 3, pause: float = 0.2, as_polars: bool = False) -> dict:
    """
    Get a company's details from the current DSE site.

    Reads the data behind the site's company page: profile and contact
    fields, capital, market data, AGM date and year end, plus tables for
    the shareholding pattern, dividend history, multi-year and interim
    financials, P/E trend and recent announcements.

    Only available from the current site (dse.com.bd). For the legacy
    site's company tables, see the deprecated :func:`get_company_info`.

    :param symbol: Trading code, e.g. 'GP' (case-insensitive).
    :param as_polars: Return polars DataFrames instead of pandas (requires polars installed).
    :return: dict keyed by the site's field names (``name``, ``sector``,
             ``authorizedCapital``, ``agmDate``...). Tabular fields such as
             ``dividendHistory`` and ``sharePattern`` are DataFrames.
    :raises BDShareError: If the page cannot be fetched or has no data for ``symbol``.
    """
    code = symbol.strip().upper()
    r = safe_get(vs.DSE_URL + vs.DSE_COMPANY_PAGE_URL + quote(code),
                 retries=retry_count, pause=pause, timeout=30)
    rows = _rsc_rows(r.text)
    company = _rsc_find(
        list(rows.values()),
        lambda d: str(d.get("code", "")).upper() == code and "authorizedCapital" in d,
    )
    if company is None:
        raise BDShareError(f"Company not found: {symbol!r}")
    details = _rsc_resolve(company, rows)
    return {k: _tabulate(v, as_polars) for k, v in details.items()
            if k not in _COMPANY_DETAILS_DROP}


def get_latest_pe(retry_count: int = 3, pause: float = 0.2, as_polars: bool = False) -> pd.DataFrame:
    """Get latest P/E ratios for all listed companies.

    :param as_polars: Return a polars DataFrame instead of pandas (requires polars installed).
    """
    # dsebd.org/pe server-renders a table with the same columns as the legacy
    # latest_PE.php page, so only the table lookup differs between the sites.
    table = _with_fallback(
        lambda: _fetch_table(
            vs.DSE_LEGACY_URL + vs.DSE_LPE_URL,
            retries=retry_count,
            pause=pause,
            table_class=_CLS_FIXED,
        ),
        lambda: _fetch_table(
            vs.DSE_URL + vs.DSE_NEW_PE_URL,
            retries=retry_count,
            pause=pause,
            timeout=30,
        ),
        "Latest P/E",
    )
    rows = []
    for row in _rows(table)[1:]:
        cols = _cells(row)
        if len(cols) < 10:
            continue
        rows.append(tuple(c.strip().replace(",", "") for c in cols[1:10]))

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

    def legacy():
        r = safe_post(
            vs.DSE_LEGACY_URL + vs.DSE_MARKET_INFO_MORE_URL,
            data={
                "startDate": start,
                "endDate": end,
                "searchRecentMarket": "Search Recent Market",
            },
            retries=retry_count,
            pause=pause,
        )

        root = _parse_html(r.content)
        table = _first(
            _find(root, "table", _CLS_CENTER),
            _find(root, "table", _CLS_PLAIN),
            _find(root, "table"),
        )
        if table is None:
            raise BDShareError("Extended market data table not found.")

        rows = []
        for row in _rows(table)[1:]:
            cols = _cells(row)
            if len(cols) < 9:
                continue
            rows.append({
                "Date":                          cols[0].strip(),
                "Total Trade":                   _safe_num(cols[1], int),
                "Total Volume":                  _safe_num(cols[2], int),
                "Total Value in Taka(mn)":       _safe_num(cols[3], float),
                "Total Market Cap. in Taka(mn)": _safe_num(cols[4], float),
                "DSEX Index":                    _safe_num(cols[5], float),
                "DSES Index":                    _safe_num(cols[6], float),
                "DS30 Index":                    _safe_num(cols[7], float),
                "DGEN Index":                    _safe_num(cols[8].replace("-", "0"), float),
            })
        return rows

    def new():
        rows = _market_summary_rows_new(*_date_range(start, end), "Total Value in Taka(mn)",
                                        "Total Market Cap. in Taka(mn)", retry_count, pause)
        for r in rows:
            if r["DGEN Index"] is None:  # the legacy parser maps "-" to 0
                r["DGEN Index"] = 0.0
        return rows

    rows = _with_fallback(legacy, new, "Extended market info")

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
    def legacy():
        # Establish referer cookie and AJAX header before the POST (done once, not per retry).
        _session.head(vs.DSE_LEGACY_URL + vs.DSE_MARKET_DEPTH_REFERER_URL, timeout=10)
        _session.headers.update({"X-Requested-With": "XMLHttpRequest"})

        r = safe_post(
            vs.DSE_LEGACY_URL + vs.DSE_MARKET_DEPTH_URL,
            data={"inst": symbol},
            retries=retry_count,
            pause=pause,
        )

        table = _find(_parse_html(r.content), "table", _CLS_STRIPPED)
        if table is None:
            raise BDShareError(f"Market depth table not found for {symbol}.")

        result = []
        matrix = ["buy_price", "buy_volume", "sell_price", "sell_volume"]

        for row in _rows(table)[:1]:
            cols = _find_all(row, "td", valign="top")
            for idx, mainrow in enumerate(cols):
                for inner_row in _rows(mainrow)[2:]:
                    newcols = _cells(inner_row)
                    if len(newcols) >= 2:
                        m = idx * 2
                        result.append({
                            matrix[m]:     _safe_num(newcols[0], float),
                            matrix[m + 1]: _safe_num(newcols[1], int),
                        })
        return result

    def new():
        data = _fetch_json(vs.DSE_API_DEPTH, {"code": symbol},
                           retries=retry_count, pause=pause)
        # Same row layout as the legacy parser: all buy levels, then all sell levels.
        return (
            [{"buy_price": lv["price"], "buy_volume": lv["quantity"]}
             for lv in data.get("bids") or []]
            + [{"sell_price": lv["price"], "sell_volume": lv["quantity"]}
               for lv in data.get("asks") or []]
        )

    result = _with_fallback(legacy, new, f"Market depth for {symbol}")
    return _to_frame(pd.DataFrame(result), as_polars)


def get_top_ten_gainers_losers(limit: int = 10, retry_count: int = 3, pause: float = 0.2, as_polars: bool = False) -> pd.DataFrame:
    """Get top ten gainers and losers.

    :param as_polars: Return a polars DataFrame instead of pandas (requires polars installed).
    """
    def legacy():
        table = _fetch_table(
            vs.DSE_LEGACY_URL + vs.DSE_TOP_TEN_GAINERS_URL,
            retries=retry_count,
            pause=pause,
            table_class=_CLS_SHARES,
        )
        rows = []
        for row in _rows(table)[1:limit + 1]:
            cols = _cells(row)
            if len(cols) < 7:
                continue
            rows.append({
                "symbol": cols[1].strip(),
                "close":  _safe_num(cols[2], float),
                "high":   _safe_num(cols[3], float),
                "low":    _safe_num(cols[4], float),
                "ycp":    _safe_num(cols[5], float),
                "change": _safe_num(cols[6], float),
            })
        if not rows:
            raise BDShareError("No top gainers/losers data found.")
        return rows

    def new():
        # dsebd.org has no top-gainer table; rank by % change of close over ycp,
        # which is how the legacy top_ten_gainer.php page computes "change".
        rows = [
            {
                "symbol": r["code"],
                "close":  r["close"],
                "high":   r["high"],
                "low":    r["low"],
                "ycp":    r["ycp"],
                "change": round((r["close"] - r["ycp"]) / r["ycp"] * 100, 4),
            }
            for r in _price_rows_new(retry_count, pause)
            if r.get("ycp") and r.get("close") is not None
        ]
        rows.sort(key=lambda r: r["change"], reverse=True)
        return rows[:limit]

    rows = _with_fallback(legacy, new, "Top gainers/losers")
    if not rows:
        raise BDShareError("No top gainers/losers data found.")
    return _to_frame(pd.DataFrame(rows), as_polars)

def get_top_twenty_shares(limit: int = 20, retry_count: int = 3, pause: float = 0.2, as_polars: bool = False) -> pd.DataFrame:
    """Get top twenty shares by volume.

    :param as_polars: Return a polars DataFrame instead of pandas (requires polars installed).
    """
    def legacy():
        table = _fetch_table(
            vs.DSE_LEGACY_URL + vs.DSE_TOP_TWENTY_SHARES_URL,
            retries=retry_count,
            pause=pause,
            table_class=_CLS_SHARES,
        )
        # Columns: #, code, LTP, HIGH, LOW, YCP, CLOSEP, TRADE, VALUE(mn), VOLUME
        rows = []
        for row in _rows(table)[1:limit + 1]:
            cols = _cells(row)
            if len(cols) < 10:
                continue
            rows.append({
                "symbol": cols[1].strip(),
                "ltp":    _safe_num(cols[2], float),
                "high":   _safe_num(cols[3], float),
                "low":    _safe_num(cols[4], float),
                "ycp":    _safe_num(cols[5], float),
                "trade":  _safe_num(cols[7], int),
                "volume": _safe_num(cols[9], int),
            })
        if not rows:
            raise BDShareError("No top shares data found.")
        return rows

    def new():
        # The legacy top_20_share.php page ranks by traded value.
        ranked = sorted(_price_rows_new(retry_count, pause),
                        key=lambda r: r.get("value") or 0, reverse=True)
        return [
            {
                "symbol": r["code"],
                "ltp":    r["ltp"],
                "high":   r["high"],
                "low":    r["low"],
                "ycp":    r["ycp"],
                "trade":  r["trades"],
                "volume": r["volume"],
            }
            for r in ranked[:limit]
        ]

    rows = _with_fallback(legacy, new, "Top twenty shares")
    if not rows:
        raise BDShareError("No top shares data found.")
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


@deprecated("Use get_company_details() instead.")
def get_company_inf(symbol: str, retry_count: int = 3, pause: float = 0.2, as_polars: bool = False) -> list:
    return get_company_info.__wrapped__(symbol, retry_count=retry_count, pause=pause, as_polars=as_polars)
