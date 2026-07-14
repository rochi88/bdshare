# _*_ coding:utf-8 _*_
'''
Created on 2026-Jun-26
@author: Raisul Islam
Tests for polars output support (as_polars=True) across all public functions.
'''
import unittest
import datetime as dt
import pandas as pd

try:
    import polars as pl
    POLARS_AVAILABLE = True
except ImportError:
    POLARS_AVAILABLE = False

from bdshare import (
    get_market_info,
    get_latest_pe,
    get_market_info_more_data,
    get_market_depth_data,
    get_sector_performance,
    get_top_gainers_losers,
    get_current_trade_data,
    get_dsex_data,
    get_current_trading_code,
    get_historical_data,
    get_basic_historical_data,
    get_close_price_data,
    get_agm_news,
    get_all_news,
    get_corporate_announcements,
    get_price_sensitive_news,
    get_news,
    get_company_info,
)

_SKIP_MSG = "polars is not installed"
_SEP = "─" * 60

_TODAY = dt.datetime.now().date()
_30_DAYS_AGO = _TODAY - dt.timedelta(days=30)


def _assert_polars(test, result, name: str):
    """Assert result is a non-empty polars DataFrame."""
    test.assertIsInstance(result, pl.DataFrame, f"{name}: expected polars DataFrame")
    test.assertFalse(result.is_empty(), f"{name}: polars DataFrame should not be empty")


def _assert_same_columns(test, pd_df: pd.DataFrame, pl_df, name: str):
    """Assert both frames have the same column names.

    Column names are compared as strings since polars requires string
    column names while pandas allows other hashables (e.g. get_latest_pe
    returns integer-labelled columns in its pandas form).
    """
    pd_cols = {str(c) for c in (pd_df.reset_index().columns if pd_df.index.name else pd_df.columns)}
    pl_cols = {str(c) for c in pl_df.columns}
    test.assertEqual(pd_cols, pl_cols, f"{name}: column mismatch between pandas and polars")


@unittest.skipUnless(POLARS_AVAILABLE, _SKIP_MSG)
class TestPolarsPandasDefault(unittest.TestCase):
    """Verify that the default (as_polars=False) still returns pandas DataFrames."""

    def test_default_returns_pandas_market_info(self):
        df = get_market_info()
        self.assertIsInstance(df, pd.DataFrame)

    def test_default_returns_pandas_current_trade(self):
        df = get_current_trade_data()
        self.assertIsInstance(df, pd.DataFrame)

    def test_default_returns_pandas_agm_news(self):
        df = get_agm_news()
        self.assertIsInstance(df, pd.DataFrame)

    def test_default_returns_pandas_historical(self):
        df = get_historical_data(start=str(_30_DAYS_AGO), end=str(_TODAY), code="GP")
        self.assertIsInstance(df, pd.DataFrame)

    @classmethod
    def setUpClass(cls):
        print(f"\n{_SEP}\n  Default pandas output tests\n{_SEP}")

    @classmethod
    def tearDownClass(cls):
        print(f"\n{_SEP}")


@unittest.skipUnless(POLARS_AVAILABLE, _SKIP_MSG)
class TestPolarsMarket(unittest.TestCase):
    """as_polars=True tests for market module functions."""

    @classmethod
    def setUpClass(cls):
        print(f"\n{_SEP}\n  Polars — market module\n{_SEP}")

    @classmethod
    def tearDownClass(cls):
        print(f"\n{_SEP}")

    def test_get_market_info_polars(self):
        result = get_market_info(as_polars=True)
        _assert_polars(self, result, "get_market_info")
        print(f"  get_market_info      : {result.shape[0]} rows × {result.shape[1]} cols")

    def test_get_market_info_columns_match_pandas(self):
        pd_df  = get_market_info()
        pl_df  = get_market_info(as_polars=True)
        _assert_same_columns(self, pd_df, pl_df, "get_market_info")

    def test_get_latest_pe_polars(self):
        result = get_latest_pe(as_polars=True)
        _assert_polars(self, result, "get_latest_pe")
        print(f"  get_latest_pe        : {result.shape[0]} rows × {result.shape[1]} cols")

    def test_get_latest_pe_columns_match_pandas(self):
        pd_df = get_latest_pe()
        pl_df = get_latest_pe(as_polars=True)
        _assert_same_columns(self, pd_df, pl_df, "get_latest_pe")

    def test_get_market_info_more_data_polars(self):
        result = get_market_info_more_data(start=str(_30_DAYS_AGO), end=str(_TODAY), as_polars=True)
        _assert_polars(self, result, "get_market_info_more_data")
        print(f"  get_market_info_more_data : {result.shape[0]} rows × {result.shape[1]} cols")

    def test_get_market_info_more_data_date_as_column_when_indexed(self):
        """When index='date', polars output should expose 'Date' as a plain column."""
        result = get_market_info_more_data(
            start=str(_30_DAYS_AGO), end=str(_TODAY), index="date", as_polars=True
        )
        self.assertIsInstance(result, pl.DataFrame)
        self.assertIn("Date", result.columns, "Date should be a column in polars output")

    def test_get_market_depth_data_polars(self):
        result = get_market_depth_data("GP", as_polars=True)
        self.assertIsInstance(result, pl.DataFrame)
        print(f"  get_market_depth_data: {result.shape[0]} rows (may be 0 off-hours)")

    def test_get_sector_performance_polars(self):
        result = get_sector_performance(as_polars=True)
        _assert_polars(self, result, "get_sector_performance")
        print(f"  get_sector_performance: {result.shape[0]} rows × {result.shape[1]} cols")

    def test_get_top_gainers_losers_polars(self):
        result = get_top_gainers_losers(as_polars=True)
        _assert_polars(self, result, "get_top_gainers_losers")
        self.assertIn("symbol", result.columns)
        self.assertIn("ltp",    result.columns)
        self.assertIn("change", result.columns)
        print(f"  get_top_gainers_losers: {result.shape[0]} rows")

    def test_get_top_gainers_losers_limit_respected(self):
        limit  = 5
        result = get_top_gainers_losers(limit=limit, as_polars=True)
        self.assertIsInstance(result, pl.DataFrame)
        self.assertLessEqual(result.shape[0], limit)


@unittest.skipUnless(POLARS_AVAILABLE, _SKIP_MSG)
class TestPolarsTrading(unittest.TestCase):
    """as_polars=True tests for trading module functions."""

    @classmethod
    def setUpClass(cls):
        print(f"\n{_SEP}\n  Polars — trading module\n{_SEP}")

    @classmethod
    def tearDownClass(cls):
        print(f"\n{_SEP}")

    def test_get_current_trade_data_polars(self):
        result = get_current_trade_data(as_polars=True)
        _assert_polars(self, result, "get_current_trade_data")
        print(f"  get_current_trade_data: {result.shape[0]} rows × {result.shape[1]} cols")

    def test_get_current_trade_data_columns_match_pandas(self):
        pd_df = get_current_trade_data()
        pl_df = get_current_trade_data(as_polars=True)
        _assert_same_columns(self, pd_df, pl_df, "get_current_trade_data")

    def test_get_current_trade_data_with_symbol_polars(self):
        result = get_current_trade_data(symbol="GP", as_polars=True)
        self.assertIsInstance(result, pl.DataFrame)
        self.assertIn("symbol", result.columns)
        print(f"  get_current_trade_data(GP): {result.shape[0]} rows")

    def test_get_dsex_data_polars(self):
        result = get_dsex_data(as_polars=True)
        _assert_polars(self, result, "get_dsex_data")
        print(f"  get_dsex_data: {result.shape[0]} rows × {result.shape[1]} cols")

    def test_get_current_trading_code_polars(self):
        result = get_current_trading_code(as_polars=True)
        _assert_polars(self, result, "get_current_trading_code")
        self.assertIn("symbol", result.columns)
        print(f"  get_current_trading_code: {result.shape[0]} symbols")

    def test_get_historical_data_polars(self):
        result = get_historical_data(
            start=str(_30_DAYS_AGO), end=str(_TODAY), code="GP", as_polars=True
        )
        self.assertIsInstance(result, pl.DataFrame)
        # date index is reset to a column
        self.assertIn("date", result.columns)
        print(f"  get_historical_data: {result.shape[0]} rows × {result.shape[1]} cols")

    def test_get_historical_data_date_is_column_not_index(self):
        """Polars has no index — 'date' must be a plain column."""
        pd_df = get_historical_data(start=str(_30_DAYS_AGO), end=str(_TODAY), code="GP")
        pl_df = get_historical_data(start=str(_30_DAYS_AGO), end=str(_TODAY), code="GP", as_polars=True)
        self.assertEqual(pd_df.index.name, "date", "pandas result should have date as index")
        self.assertIn("date", pl_df.columns,       "polars result should have date as column")

    def test_get_basic_historical_data_polars(self):
        result = get_basic_historical_data(
            start=str(_30_DAYS_AGO), end=str(_TODAY), code="GP", as_polars=True
        )
        self.assertIsInstance(result, pl.DataFrame)
        for col in ("date", "open", "high", "low", "close", "volume"):
            self.assertIn(col, result.columns, f"missing column: {col}")
        print(f"  get_basic_historical_data: {result.shape[0]} rows")

    def test_get_basic_historical_data_with_date_index_polars(self):
        result = get_basic_historical_data(
            start=str(_30_DAYS_AGO), end=str(_TODAY), code="GP",
            index="date", as_polars=True,
        )
        self.assertIsInstance(result, pl.DataFrame)
        self.assertIn("date", result.columns)

    def test_get_close_price_data_polars(self):
        result = get_close_price_data(
            start=str(_30_DAYS_AGO), end=str(_TODAY), code="GP", as_polars=True
        )
        self.assertIsInstance(result, pl.DataFrame)
        self.assertIn("date",   result.columns)
        self.assertIn("close",  result.columns)
        self.assertIn("ycp",    result.columns)
        print(f"  get_close_price_data: {result.shape[0]} rows")


@unittest.skipUnless(POLARS_AVAILABLE, _SKIP_MSG)
class TestPolarsNews(unittest.TestCase):
    """as_polars=True tests for news module functions."""

    @classmethod
    def setUpClass(cls):
        print(f"\n{_SEP}\n  Polars — news module\n{_SEP}")

    @classmethod
    def tearDownClass(cls):
        print(f"\n{_SEP}")

    def test_get_agm_news_polars(self):
        result = get_agm_news(as_polars=True)
        _assert_polars(self, result, "get_agm_news")
        print(f"  get_agm_news: {result.shape[0]} rows × {result.shape[1]} cols")

    def test_get_agm_news_columns_match_pandas(self):
        pd_df = get_agm_news()
        pl_df = get_agm_news(as_polars=True)
        _assert_same_columns(self, pd_df, pl_df, "get_agm_news")

    def test_get_corporate_announcements_polars(self):
        result = get_corporate_announcements(as_polars=True)
        _assert_polars(self, result, "get_corporate_announcements")
        print(f"  get_corporate_announcements: {result.shape[0]} rows")

    def test_get_price_sensitive_news_polars(self):
        result = get_price_sensitive_news(as_polars=True)
        _assert_polars(self, result, "get_price_sensitive_news")
        print(f"  get_price_sensitive_news: {result.shape[0]} rows")

    def test_get_news_dispatcher_all_polars(self):
        result = get_news(news_type="all", as_polars=True)
        self.assertIsInstance(result, pl.DataFrame)
        print(f"  get_news(all): {result.shape[0]} rows")

    def test_get_news_dispatcher_agm_polars(self):
        result = get_news(news_type="agm", as_polars=True)
        self.assertIsInstance(result, pl.DataFrame)

    def test_get_news_dispatcher_corporate_polars(self):
        result = get_news(news_type="corporate", as_polars=True)
        self.assertIsInstance(result, pl.DataFrame)

    def test_get_news_dispatcher_psn_polars(self):
        result = get_news(news_type="psn", as_polars=True)
        self.assertIsInstance(result, pl.DataFrame)


@unittest.skipUnless(POLARS_AVAILABLE, _SKIP_MSG)
class TestPolarsCompanyInfo(unittest.TestCase):
    """as_polars=True for get_company_info (returns list of DataFrames)."""

    @classmethod
    def setUpClass(cls):
        print(f"\n{_SEP}\n  Polars — company info\n{_SEP}")

    @classmethod
    def tearDownClass(cls):
        print(f"\n{_SEP}")

    def test_get_company_info_returns_list(self):
        result = get_company_info("GP", as_polars=True)
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)

    def test_get_company_info_all_items_are_polars(self):
        result = get_company_info("GP", as_polars=True)
        for i, item in enumerate(result):
            self.assertIsInstance(item, pl.DataFrame, f"item[{i}] should be polars DataFrame")

    def test_get_company_info_default_still_pandas(self):
        result = get_company_info("GP")
        self.assertIsInstance(result, list)
        for i, item in enumerate(result):
            self.assertIsInstance(item, pd.DataFrame, f"item[{i}] should be pandas DataFrame")


@unittest.skipUnless(POLARS_AVAILABLE, _SKIP_MSG)
class TestPolarsImportError(unittest.TestCase):
    """Verify ImportError is raised with a helpful message when polars is absent."""

    def test_import_error_message(self):
        """_to_frame raises ImportError with install hint when polars is missing."""
        from unittest.mock import patch
        import sys
        from bdshare.util.helper import _to_frame
        import pandas as pd

        df = pd.DataFrame({"a": [1, 2]})

        with patch.dict(sys.modules, {"polars": None}):
            with self.assertRaises(ImportError) as ctx:
                _to_frame(df, as_polars=True)
        self.assertIn("polars", str(ctx.exception).lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
