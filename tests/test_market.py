# _*_ coding:utf-8 _*_
'''
Created on 2024-Dec-31
@author: Raisul Islam
Comprehensive tests for BDShare market data functions
'''
import unittest
import datetime as dt
import pandas as pd
from bdshare import (
    get_latest_pe, get_market_info, get_market_depth_data, get_market_info_more_data,
    get_company_info, get_top_ten_gainers_losers, get_top_twenty_shares,
)
from bdshare.stock.market import get_market_status

_SEP = "─" * 60


def _header(title: str) -> str:
    return f"\n{_SEP}\n  {title}\n{_SEP}"


def _shape(df) -> str:
    return f"({df.shape[0]} rows × {df.shape[1]} cols)"


class TestMarketDataFunctions(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        print(_header("BDShare Market Data Tests"))

    @classmethod
    def tearDownClass(cls):
        print(f"\n{_SEP}")
        print("  All tests completed.")
        print(_SEP)

    def test_get_market_status(self):
        """Market status returns a non-empty string."""
        status = get_market_status()
        self.assertIsInstance(status, str)
        self.assertTrue(len(status) > 0)
        print(_header("Market Status"))
        print(f"  Status : {status}")

    def test_get_market_info(self):
        """Market summary DataFrame is valid and non-empty."""
        df = get_market_info()
        self.assertIsInstance(df, pd.DataFrame)
        self.assertFalse(df.empty)
        print(_header("Market Info"))
        print(df.to_string(index=False))
        print(f"\n  Shape  : {_shape(df)}")

    def test_get_latest_pe(self):
        """P/E ratio DataFrame is valid and non-empty."""
        df = get_latest_pe()
        self.assertIsInstance(df, pd.DataFrame)
        self.assertFalse(df.empty)
        print(_header("Latest P/E Ratios (first 5 rows)"))
        print(df.head().to_string(index=False))
        print(f"\n  Shape  : {_shape(df)}")

    def test_get_top_ten_gainers_losers(self):
        """Top ten gainers/losers DataFrame is valid and non-empty."""
        df = get_top_ten_gainers_losers()
        self.assertIsInstance(df, pd.DataFrame)
        self.assertFalse(df.empty)
        self.assertLessEqual(len(df), 10)
        print(_header("Top Ten Gainers/Losers"))
        print(df.to_string(index=False))
        print(f"\n  Shape  : {_shape(df)}")

    def test_get_top_twenty_shares(self):
        """Top twenty shares DataFrame is valid and non-empty."""
        df = get_top_twenty_shares()
        self.assertIsInstance(df, pd.DataFrame)
        self.assertFalse(df.empty)
        self.assertLessEqual(len(df), 20)
        print(_header("Top Twenty Shares"))
        print(df.to_string(index=False))
        print(f"\n  Shape  : {_shape(df)}")

    def test_get_market_depth_data(self):
        """Market depth DataFrame is returned (may be empty off-hours)."""
        symbol = "GP"
        df = get_market_depth_data(symbol)
        self.assertIsInstance(df, pd.DataFrame)
        print(_header(f"Market Depth — {symbol}"))
        if df.empty:
            print("  (no data — market may be closed)")
        else:
            print(df.to_string(index=False))
            print(f"\n  Shape  : {_shape(df)}")

    def test_get_market_depth_data_multiple_symbols(self):
        """Market depth works for several symbols."""
        for symbol in ("GP", "ACI", "SQURPHARMA"):
            with self.subTest(symbol=symbol):
                df = get_market_depth_data(symbol)
                self.assertIsInstance(df, pd.DataFrame)
                print(f"  {symbol:<12} {len(df):>3} records")

    def test_get_market_info_more_data(self):
        """Extended market data for the last 30 days is valid."""
        end   = dt.datetime.now().date()
        start = end - dt.timedelta(days=30)
        df = get_market_info_more_data(start, end, index="date")
        self.assertIsInstance(df, pd.DataFrame)
        print(_header("Extended Market Data — last 30 days"))
        if df.empty:
            print("  (no data returned)")
        else:
            print(df.tail(5).to_string())
            print(f"\n  Shape  : {_shape(df)}")

    def test_get_market_info_more_data_different_periods(self):
        """Extended market data works for 1 week, 1 month, and 3 months."""
        for days, label in ((7, "1 week"), (30, "1 month"), (90, "3 months")):
            with self.subTest(period=label):
                end   = dt.datetime.now().date()
                start = end - dt.timedelta(days=days)
                df = get_market_info_more_data(start, end)
                self.assertIsInstance(df, pd.DataFrame)
                print(f"  {label:<10} {len(df):>3} records")

    def test_get_company_info(self):
        """Company info returns a list of DataFrames."""
        symbol = "GP"
        tables = get_company_info(symbol)
        self.assertIsInstance(tables, list)
        self.assertTrue(len(tables) > 0)
        print(_header(f"Company Info — {symbol}"))
        print(f"  Tables returned : {len(tables)}")
        if tables:
            print(f"  First table shape : {_shape(tables[0])}")
            print(tables[0].to_string(index=False))

    def test_get_company_info_multiple_companies(self):
        """Company info works for several symbols."""
        for symbol in ("GP", "ACI", "SQURPHARMA", "BEXIMCO"):
            with self.subTest(company=symbol):
                tables = get_company_info(symbol)
                self.assertIsInstance(tables, list)
                print(f"  {symbol:<12} {len(tables):>3} tables")

    def test_data_consistency(self):
        """Both market_info and pe_data return DataFrames in the same run."""
        market_info = get_market_info()
        pe_data     = get_latest_pe()
        self.assertIsInstance(market_info, pd.DataFrame)
        self.assertIsInstance(pe_data, pd.DataFrame)
        print(_header("Data Consistency"))
        print(f"  market_info : {_shape(market_info)}")
        print(f"  pe_data     : {_shape(pe_data)}")

    def test_error_handling(self):
        """Invalid symbol raises an exception; future date range returns empty/graceful result."""
        with self.assertRaises(Exception):
            get_market_depth_data("INVALID_SYMBOL_123")

        future = dt.datetime.now().date() + dt.timedelta(days=365)
        df = get_market_info_more_data(future, future)
        self.assertIsInstance(df, pd.DataFrame)
        print(_header("Error Handling"))
        print("  Invalid symbol raised exception   : OK")
        print(f"  Future date returned DataFrame    : OK ({len(df)} rows)")


if __name__ == "__main__":
    unittest.main(verbosity=2)
