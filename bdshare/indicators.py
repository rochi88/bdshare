"""
bdshare.indicators
~~~~~~~~~~~~~~~~~~~
Optional technical-indicator helpers built on the `ta` library, for use with
the OHLCV DataFrames returned by get_basic_historical_data() and friends.

Requires the optional 'ta' extra:
    pip install bdshare[ta]
"""
from typing import Iterable, Optional

import pandas as pd

try:
    from ta.momentum import RSIIndicator
    from ta.trend import EMAIndicator, MACD, SMAIndicator
    from ta.volatility import BollingerBands
except ImportError as exc:
    raise ImportError(
        "Technical indicators require the 'ta' package. "
        "Install it with: pip install bdshare[ta]"
    ) from exc


def add_sma(df: pd.DataFrame, window: int = 20, column: str = "close") -> pd.DataFrame:
    """Add a Simple Moving Average column named ``sma_{window}``."""
    out = df.copy()
    out[f"sma_{window}"] = SMAIndicator(out[column], window=window).sma_indicator()
    return out


def add_ema(df: pd.DataFrame, window: int = 20, column: str = "close") -> pd.DataFrame:
    """Add an Exponential Moving Average column named ``ema_{window}``."""
    out = df.copy()
    out[f"ema_{window}"] = EMAIndicator(out[column], window=window).ema_indicator()
    return out


def add_rsi(df: pd.DataFrame, window: int = 14, column: str = "close") -> pd.DataFrame:
    """Add a Relative Strength Index column named ``rsi_{window}``."""
    out = df.copy()
    out[f"rsi_{window}"] = RSIIndicator(out[column], window=window).rsi()
    return out


def add_macd(
    df: pd.DataFrame,
    window_fast: int = 12,
    window_slow: int = 26,
    window_sign: int = 9,
    column: str = "close",
) -> pd.DataFrame:
    """Add ``macd``, ``macd_signal``, and ``macd_diff`` (histogram) columns."""
    out = df.copy()
    macd = MACD(
        out[column], window_fast=window_fast, window_slow=window_slow, window_sign=window_sign
    )
    out["macd"] = macd.macd()
    out["macd_signal"] = macd.macd_signal()
    out["macd_diff"] = macd.macd_diff()
    return out


def add_bollinger_bands(
    df: pd.DataFrame, window: int = 20, window_dev: int = 2, column: str = "close"
) -> pd.DataFrame:
    """Add ``bb_high``, ``bb_mid``, and ``bb_low`` Bollinger Band columns."""
    out = df.copy()
    bb = BollingerBands(out[column], window=window, window_dev=window_dev)
    out["bb_high"] = bb.bollinger_hband()
    out["bb_mid"] = bb.bollinger_mavg()
    out["bb_low"] = bb.bollinger_lband()
    return out


_INDICATORS = {
    "sma": add_sma,
    "ema": add_ema,
    "rsi": add_rsi,
    "macd": add_macd,
    "bbands": add_bollinger_bands,
}


def add_indicators(df: pd.DataFrame, indicators: Optional[Iterable[str]] = None) -> pd.DataFrame:
    """Add several indicators at once, each with its default parameters.

    For custom parameters (e.g. a different SMA window), call the individual
    ``add_*`` function directly instead.

    :param indicators: Names from 'sma', 'ema', 'rsi', 'macd', 'bbands'.
                        Defaults to all of them.
    """
    names = list(indicators) if indicators is not None else list(_INDICATORS)
    out = df
    for name in names:
        if name not in _INDICATORS:
            raise ValueError(f"Unknown indicator '{name}'. Choose from: {list(_INDICATORS)}")
        out = _INDICATORS[name](out)
    return out
