import logging
import pandas as pd
from datetime import date, timedelta
from io import BytesIO
from typing import Optional
from bdshare.util import vars as vs
from bdshare.util.helper import (
    _fetch_table, _safe_num, _parse_html,
    safe_get, safe_post,
    BDShareError, _session, deprecated,
    _to_frame, _fetch_json, _fetch_json_range, _date_range, _dhaka_today,
    _with_fallback,
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
            alt_url=vs.DSE_LEGACY_ALT_URL,
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
            vs.DSE_LEGACY_ALT_URL + vs.DSE_MARKET_INFO_URL,
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


def get_company_info(symbol: str, retry_count: int = 3, pause: float = 0.2, as_polars: bool = False) -> list:
    """
    Get company information tables for a given symbol.

    Only available from the legacy site (old.dsebd.org); dsebd.org renders
    company pages client-side with no equivalent tables.

    :param as_polars: Return polars DataFrames instead of pandas (requires polars installed).
    :return: list of DataFrames (relevant tables start at index 400 in the page).
    """
    r = safe_get(
        vs.DSE_LEGACY_URL + vs.DSE_COMPANY_INFO_URL,
        params={"name": symbol},
        alt_url=vs.DSE_LEGACY_ALT_URL + vs.DSE_COMPANY_INFO_URL,
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
    # dsebd.org/pe server-renders a table with the same columns as the legacy
    # latest_PE.php page, so only the table lookup differs between the sites.
    table = _with_fallback(
        lambda: _fetch_table(
            vs.DSE_LEGACY_URL + vs.DSE_LPE_URL,
            vs.DSE_LEGACY_ALT_URL + vs.DSE_LPE_URL,
            retries=retry_count,
            pause=pause,
            table_class=_CLS_FIXED,
        ),
        lambda: _fetch_table(
            vs.DSE_URL + vs.DSE_NEW_PE_URL,
            vs.DSE_ALT_URL + vs.DSE_NEW_PE_URL,
            retries=retry_count,
            pause=pause,
            timeout=30,
        ),
        "Latest P/E",
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

    def legacy():
        r = safe_post(
            vs.DSE_LEGACY_URL + vs.DSE_MARKET_INFO_MORE_URL,
            data={
                "startDate": start,
                "endDate": end,
                "searchRecentMarket": "Search Recent Market",
            },
            alt_url=vs.DSE_LEGACY_ALT_URL + vs.DSE_MARKET_INFO_MORE_URL,
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
            vs.DSE_LEGACY_ALT_URL + vs.DSE_TOP_TEN_GAINERS_URL,
            retries=retry_count,
            pause=pause,
            table_class=_CLS_SHARES,
        )
        rows = []
        for row in table.find_all("tr")[1:limit + 1]:
            cols = row.find_all("td")
            if len(cols) < 7:
                continue
            rows.append({
                "symbol": cols[1].text.strip(),
                "close":    _safe_num(cols[2].text, float),
                "high":    _safe_num(cols[3].text, float),
                "low":    _safe_num(cols[4].text, float),
                "ycp":    _safe_num(cols[5].text, float),
                "change": _safe_num(cols[6].text, float),
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
            vs.DSE_LEGACY_ALT_URL + vs.DSE_TOP_TWENTY_SHARES_URL,
            retries=retry_count,
            pause=pause,
            table_class=_CLS_SHARES,
        )
        # Columns: #, code, LTP, HIGH, LOW, YCP, CLOSEP, TRADE, VALUE(mn), VOLUME
        rows = []
        for row in table.find_all("tr")[1:limit + 1]:
            cols = row.find_all("td")
            if len(cols) < 10:
                continue
            rows.append({
                "symbol": cols[1].text.strip(),
                "ltp":    _safe_num(cols[2].text, float),
                "high":    _safe_num(cols[3].text, float),
                "low":    _safe_num(cols[4].text, float),
                "ycp":    _safe_num(cols[5].text, float),
                "trade": _safe_num(cols[7].text, int),
                "volume": _safe_num(cols[9].text, int),
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


@deprecated("Use get_company_info() instead.")
def get_company_inf(symbol: str, retry_count: int = 3, pause: float = 0.2, as_polars: bool = False) -> list:
    return get_company_info(symbol, retry_count=retry_count, pause=pause, as_polars=as_polars)
