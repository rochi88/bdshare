from ._version import __version__
from typing import List, Optional, Dict, Union, Any
from functools import wraps
from datetime import datetime
import warnings
import time

# ---------------------------------------------------------------------------
# Sub-module imports
# ---------------------------------------------------------------------------

# Trading data
from bdshare.stock.trading import (
    get_current_trade_data,
    get_dsex_data,
    get_current_trading_code,
    get_historical_data,
    get_basic_historical_data,
    get_close_price_data,
    get_last_trade_price_data,
)

# Market data
from bdshare.stock.market import (
    get_company_info,
    get_market_info,
    get_latest_pe,
    get_market_info_more_data,
    get_market_depth_data,
    get_sector_performance,
    get_top_gainers_losers,
)

# News
from bdshare.stock.news import (
    get_agm_news,
    get_all_news,
    get_corporate_announcements,
    get_price_sensitive_news,
    get_news,
)

# Utilities
from bdshare.util import (
    Store,
    Tickers,
    get_token,
    set_token,
    get_session,
    set_session,
    clear_cache,
    configure_proxy,
)

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------
MarketData     = Dict[str, Union[str, float, int]]
CompanyInfo    = Dict[str, Union[str, float, int, List[Dict]]]
TradeData      = Dict[str, Union[str, float, int]]
NewsItem       = Dict[str, Union[str, int]]
HistoricalData = Dict[str, Union[str, float, int, datetime]]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def deprecated(message: str):
    """Decorator to mark functions as deprecated."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            warnings.warn(
                f"{func.__name__} is deprecated: {message}",
                DeprecationWarning,
                stacklevel=2,
            )
            return func(*args, **kwargs)
        return wrapper
    return decorator


def _validate_symbol(symbol: str) -> None:
    if not symbol or not isinstance(symbol, str):
        raise ValueError("Symbol must be a non-empty string.")
    if len(symbol) > 20:
        raise ValueError("Symbol is too long.")


def _validate_date_range(start_date: str, end_date: str) -> None:
    try:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt   = datetime.strptime(end_date,   "%Y-%m-%d")
    except ValueError:
        raise ValueError("Dates must be in YYYY-MM-DD format.")
    if start_dt > end_dt:
        raise ValueError("start_date cannot be after end_date.")
    if (end_dt - start_dt).days > 365 * 5:
        raise ValueError("Date range cannot exceed 5 years.")


class BDShareError(Exception):
    """Top-level client exception."""


# ---------------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------------

class RateLimiter:
    """Sliding-window rate limiter (default: 5 calls / second)."""

    def __init__(self, max_calls: int = 5, period: float = 1.0):
        self.max_calls = max_calls
        self.period    = period
        self.calls: list = []

    def __call__(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            now = time.monotonic()
            self.calls = [t for t in self.calls if now - t < self.period]
            if len(self.calls) >= self.max_calls:
                sleep_for = self.period - (now - self.calls[0])
                if sleep_for > 0:
                    time.sleep(sleep_for)
                self.calls.clear()
            self.calls.append(time.monotonic())
            return func(*args, **kwargs)
        return wrapper


# ---------------------------------------------------------------------------
# Main client
# ---------------------------------------------------------------------------

class BDShare:
    """
    OOP client for Bangladesh DSE market data.

    Supports both direct use and context-manager style::

        with BDShare() as bd:
            df = bd.get_current_trades("ACI")
    """

    _rate_limiter = RateLimiter(max_calls=5, period=1.0)

    def __init__(self, api_key: Optional[str] = None, cache_enabled: bool = True):
        self._session      = get_session()
        self._store        = Store() if cache_enabled else None
        self.cache_enabled = cache_enabled
        if api_key:
            set_token(api_key)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.clear_cache()
        set_session(None)

    @property
    def version(self) -> str:
        return __version__

    # -- Cache helpers -------------------------------------------------------

    def _get_cache(self, key: str) -> Optional[Any]:
        if self.cache_enabled and self._store:
            return self._store.get(key)
        return None

    def _set_cache(self, key: str, data: Any, ttl: int = 300) -> None:
        if self.cache_enabled and self._store:
            self._store.set(key, data, ttl=ttl)

    # -- Market data ---------------------------------------------------------

    @_rate_limiter
    def get_market_summary(self, use_cache: bool = True) -> MarketData:
        """Current market summary (indices, volume, market cap)."""
        key = "market_summary"
        if use_cache and (hit := self._get_cache(key)):
            return hit
        data = get_market_info()
        self._set_cache(key, data, ttl=60)
        return data

    @_rate_limiter
    def get_company_profile(self, symbol: str, use_cache: bool = True) -> CompanyInfo:
        """Detailed company profile."""
        _validate_symbol(symbol)
        key = f"company_profile:{symbol.upper()}"
        if use_cache and (hit := self._get_cache(key)):
            return hit
        data = get_company_info(symbol)
        self._set_cache(key, data, ttl=3600)
        return data

    @_rate_limiter
    def get_latest_pe_ratios(self, use_cache: bool = True) -> Dict[str, float]:
        """Latest P/E ratios for all companies."""
        key = "pe_ratios"
        if use_cache and (hit := self._get_cache(key)):
            return hit
        data = get_latest_pe()
        self._set_cache(key, data, ttl=3600)
        return data

    @_rate_limiter
    def get_top_movers(self, limit: int = 10, use_cache: bool = True):
        """Top gainers and losers."""
        key = f"top_movers:{limit}"
        if use_cache and (hit := self._get_cache(key)):
            return hit
        data = get_top_gainers_losers(limit)
        self._set_cache(key, data, ttl=300)
        return data

    @_rate_limiter
    def get_sector_performance(self, use_cache: bool = True):
        """Sector-wise performance."""
        key = "sector_performance"
        if use_cache and (hit := self._get_cache(key)):
            return hit
        data = get_sector_performance()
        self._set_cache(key, data, ttl=300)
        return data

    # -- Trading data --------------------------------------------------------

    @_rate_limiter
    def get_historical_data(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        use_cache: bool = False,
    ) -> HistoricalData:
        """Historical OHLCV data for a symbol."""
        _validate_symbol(symbol)
        _validate_date_range(start_date, end_date)
        key = f"hist:{symbol}:{start_date}:{end_date}"
        if use_cache and (hit := self._get_cache(key)):
            return hit
        data = get_historical_data(start=start_date, end=end_date, code=symbol)
        if use_cache:
            self._set_cache(key, data, ttl=86400)
        return data

    @_rate_limiter
    def get_current_trades(self, symbol: Optional[str] = None, use_cache: bool = True):
        """Live trade data (last prices)."""
        key = f"current_trades:{symbol or 'all'}"
        if use_cache and (hit := self._get_cache(key)):
            return hit
        data = get_current_trade_data(symbol)
        self._set_cache(key, data, ttl=30)
        return data

    @_rate_limiter
    def get_dsex_index(self, symbol: Optional[str] = None, use_cache: bool = True):
        """DSEX index data."""
        key = f"dsex_index:{symbol or 'all'}"
        if use_cache and (hit := self._get_cache(key)):
            return hit
        data = get_dsex_data(symbol)
        self._set_cache(key, data, ttl=60)
        return data

    @_rate_limiter
    def get_trading_codes(self, use_cache: bool = True):
        """All current trading codes."""
        key = "trading_codes"
        if use_cache and (hit := self._get_cache(key)):
            return hit
        data = get_current_trading_code()
        self._set_cache(key, data, ttl=86400)
        return data

    # -- News ----------------------------------------------------------------

    @_rate_limiter
    def get_news(
        self,
        news_type: str = "all",
        code: Optional[str] = None,
        use_cache: bool = True,
    ):
        """
        Fetch DSE news.

        :param news_type: 'all', 'agm', 'corporate', or 'psn'
        :param code: Optional trading code filter.
        """
        key = f"news:{news_type}:{code or 'all'}"
        if use_cache and (hit := self._get_cache(key)):
            return hit
        data = get_news(news_type=news_type, code=code)
        self._set_cache(key, data, ttl=300)
        return data

    # -- Misc ----------------------------------------------------------------

    def clear_cache(self) -> None:
        if self.cache_enabled and self._store:
            self._store.clear()
        clear_cache()

    def configure(self, proxy_url: Optional[str] = None) -> None:
        if proxy_url:
            configure_proxy(proxy_url)


# ---------------------------------------------------------------------------
# Deprecated aliases re-exported from sub-modules for backward compatibility.
# All will be removed in 2.0.0.
# ---------------------------------------------------------------------------
# get_hist_data, get_basic_hist_data  — imported from trading.py 
# get_market_inf, get_market_inf_more_data, get_company_inf — imported from market.py 

# Trading data
from bdshare.stock.trading import (
    get_hist_data,
    get_basic_hist_data,
)

from bdshare.stock.market import (
    get_market_inf,
    get_market_inf_more_data,
    get_company_inf,
)


@deprecated("Use BDShare().get_market_summary() instead.")
def market_summary():
    return get_market_info()


# ---------------------------------------------------------------------------
# Public API surface
# ---------------------------------------------------------------------------

__all__ = [
    # Core client
    "BDShare",
    "BDShareError",

    # Trading — canonical public names
    "get_current_trade_data",
    "get_dsex_data",
    "get_current_trading_code",
    "get_historical_data",
    "get_basic_historical_data",
    "get_close_price_data",
    "get_last_trade_price_data",

    # Trading — deprecated aliases (removed in 2.0.0)
    "get_hist_data",
    "get_basic_hist_data",

    # News
    "get_agm_news",
    "get_all_news",
    "get_corporate_announcements",
    "get_price_sensitive_news",
    "get_news",

    # Market — canonical public names
    "get_company_info",
    "get_market_info",
    "get_latest_pe",
    "get_market_info_more_data",
    "get_market_depth_data",
    "get_sector_performance",
    "get_top_gainers_losers",

    # Market — deprecated aliases (removed in 2.0.0)
    "get_company_inf",
    "get_market_inf",
    "get_market_inf_more_data",

    # Utilities
    "Store",
    "Tickers",
    "configure_proxy",

    # Types
    "MarketData",
    "CompanyInfo",
    "TradeData",
    "NewsItem",
    "HistoricalData",
]