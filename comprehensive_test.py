#!/usr/bin/env python3
"""
Comprehensive Test Suite for BDShare v1.1.6 using pytest
"""

import os
import warnings
import pytest
import pandas as pd
import bdshare
from datetime import datetime, timedelta


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def dates():
    """Date range covering the last 2 trading days."""
    return {
        "start": (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d"),
        "end":   datetime.now().strftime("%Y-%m-%d"),
    }


@pytest.fixture(scope="session")
def symbol():
    return "GP"


# ---------------------------------------------------------------------------
# Trading Data
# ---------------------------------------------------------------------------

class TestTradingData:
    """Tests for live and historical trading data functions."""

    def test_get_current_trade_data_all(self):
        result = bdshare.get_current_trade_data()
        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0
        assert set(result.columns) >= {"symbol", "ltp", "high", "low", "close", "volume"}

    def test_get_current_trade_data_symbol(self, symbol):
        result = bdshare.get_current_trade_data(symbol)
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1
        assert result.iloc[0]["symbol"] == symbol

    def test_get_dsex_data_all(self):
        result = bdshare.get_dsex_data()
        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0

    def test_get_dsex_data_symbol(self, symbol):
        result = bdshare.get_dsex_data(symbol)
        assert isinstance(result, pd.DataFrame)

    def test_get_current_trading_code(self):
        result = bdshare.get_current_trading_code()
        assert isinstance(result, pd.DataFrame)
        assert "symbol" in result.columns
        assert len(result) > 0

    def test_get_historical_data_all(self, dates):
        result = bdshare.get_historical_data(dates["start"], dates["end"])
        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0
        assert set(result.columns) >= {"symbol", "open", "high", "low", "close", "volume"}

    def test_get_historical_data_symbol(self, dates, symbol):
        result = bdshare.get_historical_data(dates["start"], dates["end"], symbol)
        assert isinstance(result, pd.DataFrame)

    def test_get_basic_historical_data_all(self, dates):
        result = bdshare.get_basic_historical_data(dates["start"], dates["end"])
        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0
        assert set(result.columns) >= {"open", "high", "low", "close", "volume"}

    def test_get_basic_historical_data_symbol(self, dates, symbol):
        result = bdshare.get_basic_historical_data(dates["start"], dates["end"], symbol)
        assert isinstance(result, pd.DataFrame)

    def test_get_basic_historical_data_date_index(self, dates, symbol):
        result = bdshare.get_basic_historical_data(
            dates["start"], dates["end"], symbol, index="date"
        )
        assert isinstance(result, pd.DataFrame)
        assert result.index.name == "date"

    def test_get_close_price_data(self, dates, symbol):
        result = bdshare.get_close_price_data(dates["start"], dates["end"], symbol)
        assert isinstance(result, pd.DataFrame)
        assert set(result.columns) >= {"symbol", "close", "ycp"}

    def test_get_last_trade_price_data(self):
        result = bdshare.get_last_trade_price_data()
        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0

    # -- Deprecated alias tests ------------------------------------------

    def test_deprecated_get_hist_data(self, dates):
        """get_hist_data() must still work but emit DeprecationWarning."""
        with pytest.warns(DeprecationWarning, match="get_historical_data"):
            result = bdshare.get_hist_data(dates["start"], dates["end"])
        assert isinstance(result, pd.DataFrame)

    def test_deprecated_get_basic_hist_data(self, dates):
        """get_basic_hist_data() must still work but emit DeprecationWarning."""
        with pytest.warns(DeprecationWarning, match="get_basic_historical_data"):
            result = bdshare.get_basic_hist_data(dates["start"], dates["end"])
        assert isinstance(result, pd.DataFrame)


# ---------------------------------------------------------------------------
# News
# ---------------------------------------------------------------------------

class TestNews:
    """Tests for all news and announcement functions."""

    def test_get_agm_news(self):
        result = bdshare.get_agm_news()
        assert isinstance(result, pd.DataFrame)
        assert set(result.columns) >= {"company", "dividend", "agmDate", "venue"}

    def test_get_all_news(self, dates):
        result = bdshare.get_all_news(dates["start"], dates["end"])
        assert isinstance(result, pd.DataFrame)

    def test_get_all_news_with_symbol(self, dates, symbol):
        result = bdshare.get_all_news(dates["start"], dates["end"], symbol)
        assert isinstance(result, pd.DataFrame)

    def test_get_corporate_announcements(self):
        result = bdshare.get_corporate_announcements()
        assert isinstance(result, pd.DataFrame)

    def test_get_corporate_announcements_with_symbol(self, symbol):
        result = bdshare.get_corporate_announcements(code=symbol)
        assert isinstance(result, pd.DataFrame)

    def test_get_price_sensitive_news(self):
        result = bdshare.get_price_sensitive_news()
        assert isinstance(result, pd.DataFrame)

    def test_get_price_sensitive_news_with_symbol(self, symbol):
        result = bdshare.get_price_sensitive_news(code=symbol)
        assert isinstance(result, pd.DataFrame)

    @pytest.mark.parametrize("news_type", ["all", "agm", "corporate", "psn"])
    def test_get_news_dispatcher(self, news_type):
        """get_news() dispatcher must return a DataFrame for every valid news_type."""
        result = bdshare.get_news(news_type=news_type)
        assert isinstance(result, pd.DataFrame)

    def test_get_news_invalid_type(self):
        """get_news() must raise ValueError for an unrecognised news_type."""
        with pytest.raises(ValueError, match="Invalid news_type"):
            bdshare.get_news(news_type="invalid")


# ---------------------------------------------------------------------------
# Market Data
# ---------------------------------------------------------------------------

class TestMarketData:
    """Tests for market summary, P/E, depth, and company data."""

    def test_get_market_info(self):
        result = bdshare.get_market_info()
        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0
        assert set(result.columns) >= {"DSEX Index", "Total Trade", "Total Volume"}

    def test_get_market_info_more_data(self, dates):
        result = bdshare.get_market_info_more_data(dates["start"], dates["end"])
        assert isinstance(result, pd.DataFrame)

    def test_get_latest_pe(self):
        result = bdshare.get_latest_pe()
        assert isinstance(result, pd.DataFrame)

    def test_get_market_depth_data(self, symbol):
        result = bdshare.get_market_depth_data(symbol)
        assert isinstance(result, pd.DataFrame)
        assert set(result.columns) >= {"buy_price", "buy_volume", "sell_price", "sell_volume"}

    def test_get_company_info_returns_list(self, symbol):
        """get_company_info() returns a list of DataFrames, not a single DataFrame."""
        result = bdshare.get_company_info(symbol)
        assert isinstance(result, list)
        assert len(result) > 0
        assert all(isinstance(t, pd.DataFrame) for t in result)

    def test_get_sector_performance(self):
        result = bdshare.get_sector_performance()
        assert isinstance(result, pd.DataFrame)

    def test_get_top_gainers_losers_default(self):
        result = bdshare.get_top_gainers_losers()
        assert isinstance(result, pd.DataFrame)
        assert len(result) <= 10

    def test_get_top_gainers_losers_custom_limit(self):
        result = bdshare.get_top_gainers_losers(limit=5)
        assert isinstance(result, pd.DataFrame)
        assert len(result) <= 5

    # -- Deprecated alias tests ------------------------------------------

    def test_deprecated_get_market_inf(self):
        """get_market_inf() must still work but emit DeprecationWarning."""
        with pytest.warns(DeprecationWarning, match="get_market_info"):
            result = bdshare.get_market_inf()
        assert isinstance(result, pd.DataFrame)

    def test_deprecated_get_market_inf_more_data(self, dates):
        """get_market_inf_more_data() must still work but emit DeprecationWarning."""
        with pytest.warns(DeprecationWarning, match="get_market_info_more_data"):
            result = bdshare.get_market_inf_more_data(dates["start"], dates["end"])
        assert isinstance(result, pd.DataFrame)

    def test_deprecated_get_company_inf(self, symbol):
        """get_company_inf() must still work but emit DeprecationWarning."""
        with pytest.warns(DeprecationWarning, match="get_company_info"):
            result = bdshare.get_company_inf(symbol)
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# BDShare OOP Client
# ---------------------------------------------------------------------------

class TestBDShareClient:
    """Tests for the BDShare class and its methods."""

    def test_instantiation(self):
        bd = bdshare.BDShare()
        assert bd is not None

    def test_context_manager(self):
        with bdshare.BDShare() as bd:
            assert bd is not None

    def test_version_property(self):
        bd = bdshare.BDShare()
        assert isinstance(bd.version, str)
        assert len(bd.version) > 0

    def test_get_market_summary(self):
        with bdshare.BDShare() as bd:
            result = bd.get_market_summary()
            assert isinstance(result, pd.DataFrame)

    def test_get_company_profile(self, symbol):
        with bdshare.BDShare() as bd:
            result = bd.get_company_profile(symbol)
            assert isinstance(result, list)

    def test_get_latest_pe_ratios(self):
        with bdshare.BDShare() as bd:
            result = bd.get_latest_pe_ratios()
            assert isinstance(result, pd.DataFrame)

    def test_get_top_movers(self):
        with bdshare.BDShare() as bd:
            result = bd.get_top_movers(limit=5)
            assert isinstance(result, pd.DataFrame)

    def test_get_sector_performance(self):
        with bdshare.BDShare() as bd:
            result = bd.get_sector_performance()
            assert isinstance(result, pd.DataFrame)

    def test_get_historical_data(self, dates, symbol):
        with bdshare.BDShare() as bd:
            result = bd.get_historical_data(symbol, dates["start"], dates["end"])
            assert isinstance(result, pd.DataFrame)

    def test_get_historical_data_invalid_symbol(self, dates):
        with bdshare.BDShare() as bd:
            with pytest.raises(ValueError):
                bd.get_historical_data("", dates["start"], dates["end"])

    def test_get_historical_data_invalid_dates(self, symbol):
        with bdshare.BDShare() as bd:
            with pytest.raises(ValueError):
                bd.get_historical_data(symbol, "2024-03-01", "2024-01-01")

    def test_get_current_trades_all(self):
        with bdshare.BDShare() as bd:
            result = bd.get_current_trades()
            assert isinstance(result, pd.DataFrame)
            assert len(result) > 0

    def test_get_current_trades_symbol(self, symbol):
        with bdshare.BDShare() as bd:
            result = bd.get_current_trades(symbol)
            assert isinstance(result, pd.DataFrame)

    def test_get_dsex_index(self):
        with bdshare.BDShare() as bd:
            result = bd.get_dsex_index()
            assert isinstance(result, pd.DataFrame)

    def test_get_trading_codes(self):
        with bdshare.BDShare() as bd:
            result = bd.get_trading_codes()
            assert isinstance(result, pd.DataFrame)
            assert "symbol" in result.columns

    def test_get_news(self):
        with bdshare.BDShare() as bd:
            result = bd.get_news(news_type="all")
            assert isinstance(result, pd.DataFrame)

    def test_cache_enabled(self):
        """Second call with use_cache=True must return the same object (cache hit)."""
        with bdshare.BDShare(cache_enabled=True) as bd:
            first  = bd.get_trading_codes(use_cache=True)
            second = bd.get_trading_codes(use_cache=True)
            assert first is second

    def test_cache_disabled(self):
        bd = bdshare.BDShare(cache_enabled=False)
        assert bd._store is None

    def test_clear_cache(self):
        bd = bdshare.BDShare(cache_enabled=True)
        bd.get_trading_codes(use_cache=True)
        bd.clear_cache()  # must not raise

    def test_configure_no_proxy(self):
        """configure() with no args must not raise."""
        bd = bdshare.BDShare()
        bd.configure()


# ---------------------------------------------------------------------------
# Utility Functions
# ---------------------------------------------------------------------------

class TestUtilities:
    """Tests for Store, Tickers, session, and token helpers."""

    def test_get_session(self):
        session = bdshare.get_session()
        assert session is not None

    def test_set_session(self):
        bdshare.set_session("test")  # must not raise

    def test_get_token(self):
        token = bdshare.get_token()
        assert token is not None

    def test_set_token(self):
        bdshare.set_token("test")   # must not raise

    def test_store_save_and_cleanup(self, tmp_path):
        """Store.save() must write a readable CSV file."""
        df       = bdshare.get_current_trade_data()
        filename = str(tmp_path / "test_output.csv")
        bdshare.Store(df).save(filename)

        assert os.path.exists(filename)
        loaded = pd.read_csv(filename)
        assert len(loaded) > 0

    def test_tickers_instantiation(self):
        tickers = bdshare.Tickers()
        assert tickers is not None

    def test_package_version(self):
        assert isinstance(bdshare.__version__, str)
        assert len(bdshare.__version__) > 0


# ---------------------------------------------------------------------------
# Standalone runner (backward-compatible, executable directly)
# ---------------------------------------------------------------------------

def main():
    """Standalone test runner — prints a human-readable summary."""
    print("🔍 BDShare Comprehensive Test Suite")
    print(f"📦 Package Version: {bdshare.__version__}")
    print("=" * 55)

    end_date   = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
    sym        = "GP"

    def run(label, func, *args, **kwargs):
        try:
            result = func(*args, **kwargs)
            if isinstance(result, pd.DataFrame):
                return f"✅ {label}: {len(result)} rows"
            if isinstance(result, list):
                return f"✅ {label}: {len(result)} tables"
            return f"✅ {label}: {type(result).__name__}"
        except Exception as exc:
            return f"❌ {label}: {str(exc)[:60]}"

    sections = {
        "📊 TRADING DATA": [
            ("get_current_trade_data()",             bdshare.get_current_trade_data),
            (f"get_current_trade_data('{sym}')",     bdshare.get_current_trade_data, sym),
            ("get_dsex_data()",                      bdshare.get_dsex_data),
            ("get_current_trading_code()",           bdshare.get_current_trading_code),
            ("get_historical_data(start, end)",      bdshare.get_historical_data,       start_date, end_date),
            (f"get_historical_data(…, '{sym}')",     bdshare.get_historical_data,       start_date, end_date, sym),
            ("get_basic_historical_data(start, end)",bdshare.get_basic_historical_data, start_date, end_date),
            (f"get_basic_historical_data(…, '{sym}')",bdshare.get_basic_historical_data,start_date, end_date, sym),
            (f"get_close_price_data(…, '{sym}')",    bdshare.get_close_price_data,      start_date, end_date, sym),
            ("get_last_trade_price_data()",          bdshare.get_last_trade_price_data),
        ],
        "📰 NEWS": [
            ("get_agm_news()",                       bdshare.get_agm_news),
            ("get_all_news(start, end)",             bdshare.get_all_news,              start_date, end_date),
            (f"get_all_news(…, '{sym}')",            bdshare.get_all_news,              start_date, end_date, sym),
            ("get_corporate_announcements()",        bdshare.get_corporate_announcements),
            ("get_price_sensitive_news()",           bdshare.get_price_sensitive_news),
            ("get_news('all')",                      bdshare.get_news,                  ),
            ("get_news('agm')",                      bdshare.get_news,                  ),
        ],
        "📈 MARKET DATA": [
            ("get_market_info()",                    bdshare.get_market_info),
            ("get_market_info_more_data(start, end)",bdshare.get_market_info_more_data, start_date, end_date),
            ("get_latest_pe()",                      bdshare.get_latest_pe),
            (f"get_market_depth_data('{sym}')",      bdshare.get_market_depth_data,     sym),
            (f"get_company_info('{sym}')",           bdshare.get_company_info,          sym),
            ("get_sector_performance()",             bdshare.get_sector_performance),
            ("get_top_gainers_losers()",             bdshare.get_top_gainers_losers),
        ],
        "⚠️  DEPRECATED ALIASES": [
            ("get_hist_data(start, end)",            bdshare.get_hist_data,             start_date, end_date),
            ("get_basic_hist_data(start, end)",      bdshare.get_basic_hist_data,       start_date, end_date),
            ("get_market_inf()",                     bdshare.get_market_inf),
            ("get_market_inf_more_data(start, end)", bdshare.get_market_inf_more_data,  start_date, end_date),
            (f"get_company_inf('{sym}')",            bdshare.get_company_inf,           sym),
        ],
        "🔧 UTILITIES": [
            ("get_session()",                        bdshare.get_session),
            ("get_token()",                          bdshare.get_token),
            ("Tickers()",                            bdshare.Tickers),
        ],
    }

    all_results = []
    for section, cases in sections.items():
        print(f"\n{section}")
        print("-" * 40)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            for case in cases:
                label, func, *args = case
                line = run(label, func, *args)
                print(line)
                all_results.append(line)

    # Store test
    print("\n🔧 UTILITIES (continued)")
    print("-" * 40)
    try:
        df = bdshare.get_current_trade_data()
        bdshare.Store(df).save("test_output.csv")
        exists = os.path.exists("test_output.csv")
        os.remove("test_output.csv")
        all_results.append(f"{'✅' if exists else '❌'} Store(df).save()")
        print(all_results[-1])
    except Exception as exc:
        all_results.append(f"❌ Store(df).save(): {str(exc)[:60]}")
        print(all_results[-1])

    # Summary
    passed = sum(1 for r in all_results if r.startswith("✅"))
    total  = len(all_results)
    print("\n" + "=" * 55)
    print(f"✅ Passed : {passed}/{total} ({passed/total*100:.1f}%)")
    print(f"❌ Failed : {total - passed}/{total} ({(total-passed)/total*100:.1f}%)")
    if passed == total:
        print(f"\n🎉 ALL FUNCTIONS WORKING — BDShare {bdshare.__version__} fully functional!")
    else:
        print(f"\n⚠️  {total - passed} function(s) need attention.")
    print("🏁 Done.")


if __name__ == "__main__":
    main()