"""
bdshare.mcp_server
~~~~~~~~~~~~~~~~~~
MCP (Model Context Protocol) server exposing bdshare's Dhaka Stock
Exchange (DSE) data functions as tools for AI agents — Claude Desktop,
Claude Code, or any other MCP-compatible client.

Run directly:
    python -m bdshare.mcp_server

Or via the installed console script:
    bdshare-mcp

Defaults to stdio transport (what Claude Desktop/Code expect). For a
network-reachable server — e.g. so a non-Python program in another
container can connect — pass --transport streamable-http --host 0.0.0.0:
    bdshare-mcp --transport streamable-http --host 0.0.0.0 --port 8000

Requires the optional 'mcp' extra:
    pip install bdshare[mcp]
"""
from typing import Any, Optional

import pandas as pd

try:
    from mcp.server.fastmcp import FastMCP
    from mcp.server.fastmcp.exceptions import ToolError
except ImportError as exc:
    raise ImportError(
        "The bdshare MCP server requires the 'mcp' package. "
        "Install it with: pip install bdshare[mcp]"
    ) from exc

from bdshare import (
    BDShareError,
    get_agm_news,
    get_basic_historical_data,
    get_company_info,
    get_current_trade_data,
    get_current_trading_code,
    get_dsex_data,
    get_historical_data,
    get_latest_pe,
    get_market_depth_data,
    get_market_info,
    get_market_info_more_data,
    get_market_status,
    get_news,
    get_top_ten_gainers_losers,
    get_top_twenty_shares,
)

mcp = FastMCP(
    "bdshare",
    instructions=(
        "Tools for fetching live and historical Dhaka Stock Exchange (DSE) "
        "market data: prices, indices, order books, P/E ratios, top movers, "
        "company profiles, and news/announcements. All data is scraped live "
        "from dsebd.org, so a tool call can occasionally fail — surface the "
        "error message to the user rather than retrying in a tight loop."
    ),
)


def _clean(**kwargs) -> dict:
    """Drop None-valued kwargs so callees fall back to their own defaults."""
    return {k: v for k, v in kwargs.items() if v is not None}


def _records(df: pd.DataFrame) -> list:
    """Convert a DataFrame to JSON-serializable records (named index becomes a column)."""
    if getattr(df.index, "name", None):
        df = df.reset_index()
    return df.to_dict(orient="records")


def _call(fn, *args, **kwargs) -> Any:
    """Call a bdshare function, turning BDShareError into a clean tool-facing error."""
    try:
        return fn(*args, **kwargs)
    except BDShareError as exc:
        raise ToolError(str(exc)) from exc


@mcp.tool()
def market_status() -> str:
    """Current DSE market status (e.g. Open, Closed, Holiday)."""
    return _call(get_market_status)


@mcp.tool()
def market_summary() -> list:
    """Last 30 days of DSE market summary: indices, trade/volume, market cap."""
    return _records(_call(get_market_info))


@mcp.tool()
def market_summary_range(start: str, end: str, code: Optional[str] = None) -> list:
    """Historical DSE market summary between two dates.

    :param start: Start date, 'YYYY-MM-DD'.
    :param end: End date, 'YYYY-MM-DD'.
    :param code: Optional index filter — one of DSEX, DSES, DS30, DGEN.
    """
    return _records(_call(get_market_info_more_data, start, end, **_clean(code=code)))


@mcp.tool()
def market_depth(symbol: str) -> list:
    """Live order book (buy/sell price and volume) for a DSE trading symbol."""
    return _records(_call(get_market_depth_data, symbol))


@mcp.tool()
def latest_pe_ratios() -> list:
    """Latest price-to-earnings (P/E) ratios for all DSE-listed companies."""
    return _records(_call(get_latest_pe))


@mcp.tool()
def top_ten_gainers_losers(limit: int = 10) -> list:
    """Top gainers/losers by price change, up to `limit` rows (default 10)."""
    return _records(_call(get_top_ten_gainers_losers, limit=limit))


@mcp.tool()
def top_twenty_shares(limit: int = 20) -> list:
    """Top shares by traded volume, up to `limit` rows (default 20)."""
    return _records(_call(get_top_twenty_shares, limit=limit))


@mcp.tool()
def company_info(symbol: str) -> list:
    """Detailed company profile tables (financials, directors, shareholding) for a symbol.

    Returns a list of tables, each as a list of row records.
    """
    tables = _call(get_company_info, symbol)
    return [_records(t) for t in tables]


@mcp.tool()
def current_trades(symbol: Optional[str] = None) -> list:
    """Live trade data — all instruments, or a single symbol if provided."""
    return _records(_call(get_current_trade_data, **_clean(symbol=symbol)))


@mcp.tool()
def dsex_index(symbol: Optional[str] = None) -> list:
    """DSEX index entries — all, or filtered to one symbol."""
    return _records(_call(get_dsex_data, **_clean(symbol=symbol)))


@mcp.tool()
def trading_codes() -> list:
    """All currently tradeable DSE symbols."""
    return _records(_call(get_current_trading_code))


@mcp.tool()
def historical_data(start: str, end: str, code: Optional[str] = None) -> list:
    """Full historical OHLCV + metadata between two dates, optionally for one symbol.

    :param start: Start date, 'YYYY-MM-DD'.
    :param end: End date, 'YYYY-MM-DD'.
    :param code: Instrument symbol; omit for all instruments.
    """
    return _records(_call(get_historical_data, start=start, end=end, **_clean(code=code)))


@mcp.tool()
def basic_historical_data(start: str, end: str, code: Optional[str] = None) -> list:
    """Simplified OHLCV (open, high, low, close, volume) between two dates, oldest-first.

    Column order matches TA libraries such as ``ta``, ``pandas-ta``, and ``backtrader``.
    """
    return _records(_call(get_basic_historical_data, start=start, end=end, **_clean(code=code)))


@mcp.tool()
def news(news_type: str = "all", code: Optional[str] = None) -> list:
    """DSE news and announcements.

    :param news_type: One of 'all', 'agm', 'corporate', 'psn' (price-sensitive).
    :param code: Optional trading code filter.
    """
    return _records(_call(get_news, news_type=news_type, **_clean(code=code)))


@mcp.tool()
def agm_news() -> list:
    """AGM / dividend declaration announcements."""
    return _records(_call(get_agm_news))


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="bdshare MCP server.")
    parser.add_argument(
        "--transport", choices=["stdio", "sse", "streamable-http"], default="stdio",
        help="MCP transport (default: stdio, for desktop/CLI agent clients like Claude Desktop/Code)",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind for sse/streamable-http")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind for sse/streamable-http")
    args = parser.parse_args()

    if args.transport != "stdio":
        mcp.settings.host = args.host
        mcp.settings.port = args.port
        if args.host not in ("127.0.0.1", "localhost"):
            # Binding beyond loopback (e.g. inside a container network) means every
            # legitimate client arrives with a non-localhost Host header — DNS-rebinding
            # protection would otherwise reject all of them.
            mcp.settings.transport_security.enable_dns_rebinding_protection = False

    mcp.run(transport=args.transport)


if __name__ == "__main__":
    main()
