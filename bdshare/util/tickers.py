"""
bdshare.util.tickers
~~~~~~~~~~~~~~~~~~~~
Tickers utility — fetch and cache the list of tradeable symbols.
"""

from __future__ import annotations
from typing import List, Optional


class Tickers:
    """
    Manage the list of currently tradeable DSE symbols.

    Usage::

        from bdshare.util import Tickers

        t = Tickers()
        symbols = t.symbols       # list of symbol strings, fetched on demand
        t.refresh()               # force a fresh fetch
    """

    def __init__(self):
        self._symbols: Optional[List[str]] = None

    @property
    def symbols(self) -> List[str]:
        """Return the cached symbol list, fetching it if necessary."""
        if self._symbols is None:
            self.refresh()
        return self._symbols

    def refresh(self) -> List[str]:
        """Fetch the current symbol list from DSE and cache it."""
        # Import here to avoid circular imports at module load time
        from bdshare.stock.trading import get_current_trading_code
        df = get_current_trading_code()
        self._symbols = df["symbol"].tolist()
        return self._symbols

    def __len__(self) -> int:
        return len(self.symbols)

    def __iter__(self):
        return iter(self.symbols)

    def __contains__(self, symbol: str) -> bool:
        return symbol.upper() in (s.upper() for s in self.symbols)

    def __repr__(self) -> str:  # pragma: no cover
        count = len(self._symbols) if self._symbols is not None else "not loaded"
        return f"Tickers({count} symbols)"