"""
bdshare.portfolio
~~~~~~~~~~~~~~~~~~
Lightweight portfolio tracking: cost basis, live market value, and P&L
against current DSE prices.
"""
from dataclasses import dataclass
from typing import Dict

import pandas as pd

from bdshare.stock.trading import get_current_trade_data
from bdshare.util.helper import BDShareError

_HOLDINGS_COLUMNS = ["symbol", "quantity", "avg_cost", "cost_basis"]
_VALUATION_COLUMNS = _HOLDINGS_COLUMNS + ["ltp", "market_value", "pnl", "pnl_pct"]


@dataclass
class Position:
    symbol: str
    quantity: float
    avg_cost: float

    @property
    def cost_basis(self) -> float:
        return self.quantity * self.avg_cost


class Portfolio:
    """Tracks positions and values them against live DSE prices.

    Example::

        pf = Portfolio()
        pf.add_position('GP', quantity=100, avg_cost=450.50)
        pf.add_position('ACI', quantity=50, avg_cost=225.75)

        print(pf.valuation().to_string())
        print(pf.summary())
    """

    def __init__(self) -> None:
        self._positions: Dict[str, Position] = {}

    def add_position(self, symbol: str, quantity: float, avg_cost: float) -> None:
        """Add to (or open) a position.

        Calling this again for a symbol already held blends the cost basis
        (like a real buy) rather than replacing the position. Passing a
        negative ``quantity`` reduces the position; if it nets to zero the
        position is dropped.
        """
        symbol = symbol.upper()
        existing = self._positions.get(symbol)
        if existing is None:
            self._positions[symbol] = Position(symbol, quantity, avg_cost)
            return

        total_qty = existing.quantity + quantity
        if total_qty == 0:
            del self._positions[symbol]
            return
        blended_cost = (
            existing.quantity * existing.avg_cost + quantity * avg_cost
        ) / total_qty
        self._positions[symbol] = Position(symbol, total_qty, blended_cost)

    def remove_position(self, symbol: str) -> None:
        """Remove a position entirely, regardless of quantity."""
        self._positions.pop(symbol.upper(), None)

    @property
    def positions(self) -> Dict[str, Position]:
        return dict(self._positions)

    def holdings(self) -> pd.DataFrame:
        """Positions as a DataFrame — no network call, cost-basis only."""
        if not self._positions:
            return pd.DataFrame(columns=_HOLDINGS_COLUMNS)
        return pd.DataFrame([
            {
                "symbol": p.symbol,
                "quantity": p.quantity,
                "avg_cost": p.avg_cost,
                "cost_basis": p.cost_basis,
            }
            for p in self._positions.values()
        ])

    def valuation(self, retry_count: int = 3, pause: float = 0.2) -> pd.DataFrame:
        """Fetch current prices (one live call for all instruments) and compute P&L.

        Symbols not present in the live feed (delisted, halted, bad symbol)
        get ``None`` for ``ltp``, ``market_value``, and ``pnl`` rather than
        raising, so one bad symbol doesn't block valuing the rest.
        """
        if not self._positions:
            return pd.DataFrame(columns=_VALUATION_COLUMNS)

        try:
            prices = get_current_trade_data(retry_count=retry_count, pause=pause)
            price_map = dict(zip(prices["symbol"], prices["ltp"]))
        except BDShareError:
            price_map = {}

        rows = []
        for p in self._positions.values():
            ltp = price_map.get(p.symbol)
            market_value = ltp * p.quantity if ltp is not None else None
            pnl = market_value - p.cost_basis if market_value is not None else None
            pnl_pct = (pnl / p.cost_basis * 100) if pnl is not None and p.cost_basis else None
            rows.append({
                "symbol": p.symbol,
                "quantity": p.quantity,
                "avg_cost": p.avg_cost,
                "cost_basis": p.cost_basis,
                "ltp": ltp,
                "market_value": market_value,
                "pnl": pnl,
                "pnl_pct": pnl_pct,
            })
        return pd.DataFrame(rows, columns=_VALUATION_COLUMNS)

    def summary(self, retry_count: int = 3, pause: float = 0.2) -> dict:
        """Aggregate portfolio totals against live prices."""
        df = self.valuation(retry_count=retry_count, pause=pause)
        total_cost = float(df["cost_basis"].sum()) if not df.empty else 0.0
        total_value = float(df["market_value"].sum(skipna=True)) if not df.empty else 0.0
        total_pnl = total_value - total_cost
        total_pnl_pct = (total_pnl / total_cost * 100) if total_cost else 0.0
        return {
            "positions": len(self._positions),
            "total_cost": total_cost,
            "total_value": total_value,
            "total_pnl": total_pnl,
            "total_pnl_pct": total_pnl_pct,
        }
