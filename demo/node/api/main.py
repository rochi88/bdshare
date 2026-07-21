"""
bdshare demo API (FastAPI)
~~~~~~~~~~~~~~~~~~~~~~~~~~
Node.js can't import a Python library directly, so this exposes bdshare's
data-fetching functions as JSON REST endpoints for demo/node/server (Express)
to consume.

Run:
    uvicorn main:app --host 0.0.0.0 --port 8000
"""
import math
from typing import List, Optional

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import bdshare
from bdshare import BDShareError
from bdshare.indicators import add_bollinger_bands, add_ema, add_macd, add_rsi, add_sma
from bdshare.portfolio import Portfolio

app = FastAPI(title="bdshare demo API")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

_INDICATOR_FUNCS = {
    "sma": add_sma, "ema": add_ema, "rsi": add_rsi, "macd": add_macd, "bbands": add_bollinger_bands,
}


def _records(df: pd.DataFrame) -> list:
    """Convert a DataFrame to JSON-serializable records (named index becomes a column).

    Indicator columns (SMA/RSI/...) are NaN during their warm-up window, and
    Starlette's JSON renderer uses allow_nan=False (strict JSON) — NaN would
    crash the response instead of serializing, so it's swapped for None here.
    """
    if getattr(df.index, "name", None):
        df = df.reset_index()
    records = df.to_dict(orient="records")
    for record in records:
        for key, value in record.items():
            if isinstance(value, float) and math.isnan(value):
                record[key] = None
    return records


def _call(fn, *args, **kwargs):
    """Call a bdshare function, turning BDShareError into a clean HTTP error."""
    try:
        return fn(*args, **kwargs)
    except BDShareError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/market/status")
def market_status():
    return {"status": _call(bdshare.get_market_status)}


@app.get("/market/info")
def market_info():
    return _records(_call(bdshare.get_market_info))


@app.get("/market/movers/top-ten")
def top_ten_gainers_losers(limit: int = 10):
    return _records(_call(bdshare.get_top_ten_gainers_losers, limit=limit))


@app.get("/market/movers/top-twenty")
def top_twenty_shares(limit: int = 20):
    return _records(_call(bdshare.get_top_twenty_shares, limit=limit))


@app.get("/market/pe")
def latest_pe():
    return _records(_call(bdshare.get_latest_pe))


@app.get("/market/depth/{symbol}")
def market_depth(symbol: str):
    return _records(_call(bdshare.get_market_depth_data, symbol))


@app.get("/company/{symbol}")
def company_info(symbol: str):
    tables = _call(bdshare.get_company_info, symbol)
    return [_records(t) for t in tables]


@app.get("/trading/current")
def current_trades(symbol: Optional[str] = None):
    return _records(_call(bdshare.get_current_trade_data, symbol))


@app.get("/trading/dsex")
def dsex_data(symbol: Optional[str] = None):
    return _records(_call(bdshare.get_dsex_data, symbol))


@app.get("/trading/codes")
def trading_codes():
    return _records(_call(bdshare.get_current_trading_code))


@app.get("/trading/historical")
def historical(
    start: str,
    end: str,
    symbol: Optional[str] = None,
    indicators: Optional[str] = Query(
        None, description="Comma-separated: sma, ema, rsi, macd, bbands"
    ),
):
    df = _call(
        bdshare.get_basic_historical_data,
        start=start, end=end, code=symbol or "All Instrument",
    )
    if indicators:
        for name in (n.strip() for n in indicators.split(",")):
            fn = _INDICATOR_FUNCS.get(name)
            if fn is None:
                raise HTTPException(status_code=400, detail=f"Unknown indicator '{name}'")
            df = fn(df)
    return _records(df)


@app.get("/news")
def news(news_type: str = "all", code: Optional[str] = None):
    return _records(_call(bdshare.get_news, news_type=news_type, code=code))


class PortfolioPosition(BaseModel):
    symbol: str
    quantity: float
    avg_cost: float


@app.post("/portfolio/valuation")
def portfolio_valuation(positions: List[PortfolioPosition]):
    """Stateless valuation: send the full position list each time, get back
    per-position P&L plus a summary. No server-side portfolio state — the
    Node frontend owns that.
    """
    pf = Portfolio()
    for p in positions:
        pf.add_position(p.symbol, quantity=p.quantity, avg_cost=p.avg_cost)
    return {
        "valuation": _records(_call(pf.valuation)),
        "summary": pf.summary(),
    }
