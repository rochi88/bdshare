"""
bdshare Streamlit demo
~~~~~~~~~~~~~~~~~~~~~~~
Showcases (almost) every public feature of bdshare in one app: live
trading data, historical charts with technical indicators, market
movers, news, portfolio tracking, live tick polling, and the tool
surface exposed to AI agents via the MCP server.

Run locally (from the repo root):
    pip install -e ".[ta,stream]"
    pip install -r demo/streamlit/requirements.txt
    streamlit run demo/streamlit/streamlit_app.py

Or with Docker — see demo/README.md.
"""
import datetime as dt

import plotly.graph_objects as go
import streamlit as st

import bdshare
from bdshare import BDShareError
from bdshare.indicators import add_bollinger_bands, add_ema, add_macd, add_rsi, add_sma
from bdshare.portfolio import Portfolio

st.set_page_config(page_title="bdshare demo", page_icon="📈", layout="wide")

_FALLBACK_SYMBOLS = ["GP", "ACI", "SQURPHARMA", "BEXIMCO", "RENATA", "BRACBANK"]


# ---------------------------------------------------------------------------
# Cached data access — TTLs mirror BDShare's own documented cache TTLs, so
# repeatedly switching tabs/widgets doesn't hammer dsebd.org.
# ---------------------------------------------------------------------------

@st.cache_data(ttl=60)
def cached_market_status():
    return bdshare.get_market_status()


@st.cache_data(ttl=30)
def cached_current_trades(symbol):
    return bdshare.get_current_trade_data(symbol)


@st.cache_data(ttl=60)
def cached_dsex_data(symbol):
    return bdshare.get_dsex_data(symbol)


@st.cache_data(ttl=86400)
def cached_trading_codes():
    return bdshare.get_current_trading_code()


@st.cache_data(ttl=60)
def cached_market_info():
    return bdshare.get_market_info()


@st.cache_data(ttl=3600)
def cached_latest_pe():
    return bdshare.get_latest_pe()


@st.cache_data(ttl=300)
def cached_top_ten(limit):
    return bdshare.get_top_ten_gainers_losers(limit=limit)


@st.cache_data(ttl=300)
def cached_top_twenty(limit):
    return bdshare.get_top_twenty_shares(limit=limit)


@st.cache_data(ttl=3600)
def cached_company_info(symbol):
    return bdshare.get_company_info(symbol)


@st.cache_data(ttl=30)
def cached_market_depth(symbol):
    return bdshare.get_market_depth_data(symbol)


@st.cache_data(ttl=3600)
def cached_historical(start, end, code):
    return bdshare.get_basic_historical_data(str(start), str(end), code)


@st.cache_data(ttl=300)
def cached_news(news_type, code):
    return bdshare.get_news(news_type=news_type, code=code)


@st.cache_data(ttl=86400)
def all_symbols():
    try:
        return sorted(cached_trading_codes()["symbol"].tolist())
    except BDShareError:
        return _FALLBACK_SYMBOLS


def default_symbol_index(symbols, preferred="GP"):
    return symbols.index(preferred) if preferred in symbols else 0


symbols = all_symbols()

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
st.sidebar.title("📈 bdshare demo")
st.sidebar.caption("Live Dhaka Stock Exchange data, end to end.")
try:
    st.sidebar.metric("Market status", cached_market_status())
except BDShareError as e:
    st.sidebar.error(f"Market status unavailable: {e}")
st.sidebar.caption(f"{len(symbols)} tradeable symbols loaded")
st.sidebar.markdown("[GitHub](https://github.com/rochi88/bdshare) · [PyPI](https://pypi.org/project/bdshare/)")

tab_live, tab_hist, tab_movers, tab_news, tab_portfolio, tab_ticks, tab_mcp = st.tabs([
    "Live Trading", "Historical & Indicators", "Market Movers",
    "News", "Portfolio", "Live Ticks", "AI Agents (MCP)",
])

# ---------------------------------------------------------------------------
# Tab: Live Trading
# ---------------------------------------------------------------------------
with tab_live:
    st.header("Live Trading Data")
    symbol_filter = st.selectbox("Filter by symbol (optional)", ["All"] + symbols, key="lt_symbol")
    try:
        df = cached_current_trades(None if symbol_filter == "All" else symbol_filter)
        st.dataframe(df, width="stretch", hide_index=True)
        st.caption(f"{len(df)} rows — cached 30s · get_current_trade_data()")
    except BDShareError as e:
        st.error(str(e))

    st.subheader("DSEX Index Entries")
    dsex_filter = st.selectbox("Filter by symbol (optional)", ["All"] + symbols, key="dsex_symbol")
    try:
        st.dataframe(
            cached_dsex_data(None if dsex_filter == "All" else dsex_filter),
            width="stretch", hide_index=True,
        )
        st.caption("get_dsex_data()")
    except BDShareError as e:
        st.error(str(e))

# ---------------------------------------------------------------------------
# Tab: Historical & Indicators
# ---------------------------------------------------------------------------
with tab_hist:
    st.header("Historical Data + Technical Indicators")
    c1, c2, c3 = st.columns(3)
    with c1:
        h_symbol = st.selectbox("Symbol", symbols, index=default_symbol_index(symbols), key="hist_symbol")
    with c2:
        h_start = st.date_input("Start date", dt.date.today() - dt.timedelta(days=180), key="hist_start")
    with c3:
        h_end = st.date_input("End date", dt.date.today(), key="hist_end")

    indicator_choices = st.multiselect(
        "Indicators (bdshare.indicators)",
        ["SMA 20", "EMA 20", "Bollinger Bands", "RSI 14", "MACD"],
        default=["SMA 20", "Bollinger Bands"],
        key="hist_indicators",
    )

    try:
        hist_df = cached_historical(h_start, h_end, h_symbol)
        if hist_df.empty:
            st.warning("No data for this range.")
        else:
            if "SMA 20" in indicator_choices:
                hist_df = add_sma(hist_df, window=20)
            if "EMA 20" in indicator_choices:
                hist_df = add_ema(hist_df, window=20)
            if "Bollinger Bands" in indicator_choices:
                hist_df = add_bollinger_bands(hist_df, window=20)
            if "RSI 14" in indicator_choices:
                hist_df = add_rsi(hist_df, window=14)
            if "MACD" in indicator_choices:
                hist_df = add_macd(hist_df)

            price_fig = go.Figure(data=[go.Candlestick(
                x=hist_df["date"], open=hist_df["open"], high=hist_df["high"],
                low=hist_df["low"], close=hist_df["close"], name=h_symbol,
            )])
            for col in ("sma_20", "ema_20", "bb_high", "bb_mid", "bb_low"):
                if col in hist_df.columns:
                    price_fig.add_trace(go.Scatter(x=hist_df["date"], y=hist_df[col], name=col, line=dict(width=1)))
            price_fig.update_layout(
                title=f"{h_symbol} — Candlestick", xaxis_title="Date", yaxis_title="Price (BDT)",
                height=500, template="plotly_white",
            )
            st.plotly_chart(price_fig, width="stretch")

            if "rsi_14" in hist_df.columns:
                rsi_fig = go.Figure(data=[go.Scatter(x=hist_df["date"], y=hist_df["rsi_14"], name="RSI 14")])
                rsi_fig.update_layout(height=220, title="RSI 14", yaxis_range=[0, 100], template="plotly_white")
                st.plotly_chart(rsi_fig, width="stretch")

            if "macd" in hist_df.columns:
                macd_fig = go.Figure()
                macd_fig.add_trace(go.Scatter(x=hist_df["date"], y=hist_df["macd"], name="MACD"))
                macd_fig.add_trace(go.Scatter(x=hist_df["date"], y=hist_df["macd_signal"], name="Signal"))
                macd_fig.add_trace(go.Bar(x=hist_df["date"], y=hist_df["macd_diff"], name="Histogram"))
                macd_fig.update_layout(height=220, title="MACD", template="plotly_white")
                st.plotly_chart(macd_fig, width="stretch")

            st.dataframe(hist_df.tail(20), width="stretch", hide_index=True)
            st.caption("get_basic_historical_data() + bdshare.indicators")
    except BDShareError as e:
        st.error(str(e))

# ---------------------------------------------------------------------------
# Tab: Market Movers
# ---------------------------------------------------------------------------
with tab_movers:
    st.header("Market Overview & Movers")
    try:
        st.dataframe(cached_market_info().tail(10), width="stretch", hide_index=True)
        st.caption("get_market_info() — last 30 days, showing 10")
    except BDShareError as e:
        st.error(str(e))

    mc1, mc2 = st.columns(2)
    with mc1:
        st.subheader("Top Gainers / Losers")
        gl_limit = st.slider("Limit", 5, 20, 10, key="movers_limit")
        try:
            st.dataframe(cached_top_ten(gl_limit), width="stretch", hide_index=True)
            st.caption("get_top_ten_gainers_losers()")
        except BDShareError as e:
            st.error(str(e))
    with mc2:
        st.subheader("Top Shares by Volume")
        vol_limit = st.slider("Limit", 5, 20, 20, key="volume_limit")
        try:
            st.dataframe(cached_top_twenty(vol_limit), width="stretch", hide_index=True)
            st.caption("get_top_twenty_shares()")
        except BDShareError as e:
            st.error(str(e))

    st.subheader("P/E Ratios")
    try:
        st.dataframe(cached_latest_pe().head(15), width="stretch", hide_index=True)
        st.caption("get_latest_pe() — first 15 rows")
    except BDShareError as e:
        st.error(str(e))

    st.subheader("Market Depth & Company Profile")
    depth_symbol = st.selectbox("Symbol", symbols, index=default_symbol_index(symbols), key="depth_symbol")
    dc1, dc2 = st.columns(2)
    with dc1:
        st.markdown("**Order book** — `get_market_depth_data()`")
        try:
            depth_df = cached_market_depth(depth_symbol)
            if depth_df.empty:
                st.info("No depth data (market may be closed).")
            else:
                st.dataframe(depth_df, width="stretch", hide_index=True)
        except BDShareError as e:
            st.info(str(e))
    with dc2:
        st.markdown("**Company info (first table)** — `get_company_info()`")
        try:
            tables = cached_company_info(depth_symbol)
            if tables:
                st.dataframe(tables[0], width="stretch", hide_index=True)
                st.caption(f"{len(tables)} tables available for this symbol")
            else:
                st.info("No company info tables found.")
        except BDShareError as e:
            st.info(str(e))

# ---------------------------------------------------------------------------
# Tab: News
# ---------------------------------------------------------------------------
with tab_news:
    st.header("News & Announcements")
    st.caption("Unified dispatcher — get_news(news_type, code)")
    news_type = st.radio("Type", ["all", "agm", "corporate", "psn"], horizontal=True, key="news_type")
    news_symbol = st.selectbox("Filter by symbol (optional)", ["All"] + symbols, key="news_symbol")
    try:
        news_df = cached_news(news_type, None if news_symbol == "All" else news_symbol)
        st.dataframe(news_df, width="stretch", hide_index=True)
        st.caption(f"{len(news_df)} items")
    except BDShareError as e:
        st.info(str(e))

# ---------------------------------------------------------------------------
# Tab: Portfolio
# ---------------------------------------------------------------------------
with tab_portfolio:
    st.header("Portfolio Tracker")
    st.caption("bdshare.portfolio.Portfolio — cost basis + live P&L, one network call for all positions.")

    if "portfolio" not in st.session_state:
        st.session_state.portfolio = Portfolio()
    pf: Portfolio = st.session_state.portfolio

    with st.form("add_position", clear_on_submit=True):
        c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
        with c1:
            p_symbol = st.selectbox("Symbol", symbols, key="pf_symbol")
        with c2:
            p_qty = st.number_input("Quantity", min_value=1, value=100, key="pf_qty")
        with c3:
            p_cost = st.number_input("Avg cost", min_value=0.0, value=100.0, key="pf_cost")
        with c4:
            st.markdown("&nbsp;")
            submitted = st.form_submit_button("Add position")
        if submitted:
            pf.add_position(p_symbol, quantity=p_qty, avg_cost=p_cost)
            st.success(f"Added {p_qty} × {p_symbol} @ {p_cost}")

    if pf.positions:
        remove_col, _ = st.columns([1, 3])
        with remove_col:
            remove_symbol = st.selectbox("Remove a position", list(pf.positions.keys()), key="pf_remove")
            if st.button("Remove"):
                pf.remove_position(remove_symbol)
                st.rerun()

        try:
            valuation = pf.valuation()
            st.dataframe(valuation, width="stretch", hide_index=True)

            summary = pf.summary()
            m1, m2, m3 = st.columns(3)
            m1.metric("Total cost", f"{summary['total_cost']:,.2f}")
            m2.metric("Total value", f"{summary['total_value']:,.2f}")
            m3.metric("Total P&L", f"{summary['total_pnl']:+,.2f}", f"{summary['total_pnl_pct']:+.2f}%")

            valued = valuation.dropna(subset=["market_value"])
            if not valued.empty:
                pie = go.Figure(data=[go.Pie(labels=valued["symbol"], values=valued["market_value"])])
                pie.update_layout(title="Allocation by market value", height=350, template="plotly_white")
                st.plotly_chart(pie, width="stretch")
        except BDShareError as e:
            st.error(str(e))
    else:
        st.info("Add a position above to see live valuation and P&L.")

# ---------------------------------------------------------------------------
# Tab: Live Ticks
# ---------------------------------------------------------------------------
with tab_ticks:
    st.header("Live Ticks (poll-and-diff)")
    st.caption(
        "DSE has no push API, so this mirrors what `bdshare.stream` does under the "
        "hood: poll `get_current_trade_data()` on an interval and show what changed. "
        "The real `bdshare-stream` command runs this as an actual WebSocket server "
        "other programs can subscribe to — see below."
    )
    tick_symbols = st.multiselect(
        "Symbols to watch", symbols,
        default=[s for s in ("GP", "ACI") if s in symbols],
        key="tick_symbols",
    )
    tick_interval = st.slider("Poll interval (seconds)", 3, 30, 5, key="tick_interval")

    if "tick_previous" not in st.session_state:
        st.session_state.tick_previous = {}

    @st.fragment(run_every=tick_interval)
    def live_ticks_fragment():
        if not tick_symbols:
            st.info("Pick at least one symbol above.")
            return
        try:
            df = bdshare.get_current_trade_data()
            df = df[df["symbol"].isin(tick_symbols)]
        except BDShareError as e:
            st.error(str(e))
            return

        previous = st.session_state.tick_previous
        current = {row["symbol"]: row for row in df.to_dict(orient="records")}
        changed = [s for s, row in current.items() if previous.get(s) != row]
        st.session_state.tick_previous = current

        st.caption(f"Last poll: {dt.datetime.now().strftime('%H:%M:%S')} — changed: {', '.join(changed) or 'none yet'}")
        st.dataframe(df, width="stretch", hide_index=True)

    live_ticks_fragment()

    st.divider()
    st.subheader("Run the real WebSocket server")
    st.code("pip install \"bdshare[stream]\"\nbdshare-stream --symbols GP,ACI --interval 5", language="bash")
    st.code(
        "import asyncio, json, websockets\n\n"
        "async def main():\n"
        "    async with websockets.connect('ws://localhost:8765') as ws:\n"
        "        async for message in ws:\n"
        "            print(json.loads(message))   # {'type': 'ticks', 'data': [...]}\n\n"
        "asyncio.run(main())",
        language="python",
    )

# ---------------------------------------------------------------------------
# Tab: AI Agents (MCP)
# ---------------------------------------------------------------------------
with tab_mcp:
    st.header("AI Agents via MCP")
    st.caption(
        "bdshare ships an MCP (Model Context Protocol) server so agents like "
        "Claude Desktop or Claude Code can call this data directly as tools, "
        "from another program entirely."
    )
    st.code('pip install "bdshare[mcp]"\nbdshare-mcp', language="bash")
    st.code("claude mcp add bdshare -- bdshare-mcp", language="bash")

    st.subheader("Try a tool call")
    st.caption("Runs the same bdshare function the MCP tool wraps, and shows the JSON an agent would get back.")
    mcp_symbol = st.selectbox("Symbol (for tools that need one)", symbols, index=default_symbol_index(symbols), key="mcp_symbol")
    mcp_tool = st.selectbox(
        "Tool",
        ["market_status", "market_summary", "top_ten_gainers_losers", "top_twenty_shares",
         "current_trades", "dsex_index", "company_info"],
        key="mcp_tool",
    )

    if st.button("Call tool"):
        try:
            if mcp_tool == "market_status":
                result = bdshare.get_market_status()
            elif mcp_tool == "market_summary":
                result = bdshare.get_market_info().tail(5).to_dict(orient="records")
            elif mcp_tool == "top_ten_gainers_losers":
                result = bdshare.get_top_ten_gainers_losers(limit=5).to_dict(orient="records")
            elif mcp_tool == "top_twenty_shares":
                result = bdshare.get_top_twenty_shares(limit=5).to_dict(orient="records")
            elif mcp_tool == "current_trades":
                result = bdshare.get_current_trade_data(mcp_symbol).to_dict(orient="records")
            elif mcp_tool == "dsex_index":
                result = bdshare.get_dsex_data(mcp_symbol).to_dict(orient="records")
            else:  # company_info
                tables = bdshare.get_company_info(mcp_symbol)
                result = tables[0].to_dict(orient="records") if tables else []
            st.json(result)
        except BDShareError as e:
            st.error(str(e))

    st.subheader("Full tool list")
    st.markdown(
        "`market_status` · `market_summary` · `market_summary_range` · `market_depth` · "
        "`latest_pe_ratios` · `top_ten_gainers_losers` · `top_twenty_shares` · `company_info` · "
        "`current_trades` · `dsex_index` · `trading_codes` · `historical_data` · "
        "`basic_historical_data` · `news` · `agm_news`"
    )

st.divider()
st.caption(
    "bdshare is intended for educational and research use. Data is scraped live from "
    "dsebd.org on every request — please respect DSE's terms of service."
)
