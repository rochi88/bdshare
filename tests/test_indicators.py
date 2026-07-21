# _*_ coding:utf-8 _*_
'''
Tests for bdshare.indicators (technical indicators via the optional `ta` extra).
'''
import unittest
import numpy as np
import pandas as pd

try:
    import ta  # noqa: F401
    TA_AVAILABLE = True
except ImportError:
    TA_AVAILABLE = False

if TA_AVAILABLE:
    from bdshare.indicators import (
        add_sma, add_ema, add_rsi, add_macd, add_bollinger_bands, add_indicators,
    )


def _synthetic_ohlcv(n: int = 60) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    close = 100 + np.cumsum(rng.normal(0, 1, n))
    return pd.DataFrame({
        "date":   pd.date_range("2024-01-01", periods=n, freq="D").astype(str),
        "open":   close - 0.5,
        "high":   close + 1.0,
        "low":    close - 1.0,
        "close":  close,
        "volume": rng.integers(1000, 10000, n),
    })


@unittest.skipUnless(TA_AVAILABLE, "ta is not installed")
class TestIndicators(unittest.TestCase):

    def setUp(self):
        self.df = _synthetic_ohlcv()

    def test_add_sma(self):
        out = add_sma(self.df, window=10)
        self.assertIn("sma_10", out.columns)
        self.assertEqual(len(out), len(self.df))

    def test_add_ema(self):
        out = add_ema(self.df, window=10)
        self.assertIn("ema_10", out.columns)

    def test_add_rsi(self):
        out = add_rsi(self.df, window=14)
        self.assertIn("rsi_14", out.columns)
        valid = out["rsi_14"].dropna()
        self.assertTrue(((valid >= 0) & (valid <= 100)).all())

    def test_add_macd(self):
        out = add_macd(self.df)
        for col in ("macd", "macd_signal", "macd_diff"):
            self.assertIn(col, out.columns)

    def test_add_bollinger_bands(self):
        out = add_bollinger_bands(self.df, window=20)
        for col in ("bb_high", "bb_mid", "bb_low"):
            self.assertIn(col, out.columns)
        valid = out.dropna(subset=["bb_high", "bb_low"])
        self.assertTrue((valid["bb_high"] >= valid["bb_low"]).all())

    def test_add_indicators_all(self):
        out = add_indicators(self.df)
        for col in ("sma_20", "ema_20", "rsi_14", "macd", "bb_high"):
            self.assertIn(col, out.columns)

    def test_add_indicators_subset(self):
        out = add_indicators(self.df, indicators=["sma", "rsi"])
        self.assertIn("sma_20", out.columns)
        self.assertIn("rsi_14", out.columns)
        self.assertNotIn("macd", out.columns)

    def test_add_indicators_unknown_raises(self):
        with self.assertRaises(ValueError):
            add_indicators(self.df, indicators=["not_a_real_indicator"])

    def test_original_dataframe_not_mutated(self):
        original_cols = list(self.df.columns)
        add_sma(self.df, window=10)
        self.assertEqual(list(self.df.columns), original_cols)


if __name__ == "__main__":
    unittest.main(verbosity=2)
