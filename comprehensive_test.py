#!/usr/bin/env python3
"""
Comprehensive Test Suite for BDShare v1.1.4 using pytest
"""

import pytest
import bdshare
import pandas as pd
from datetime import datetime, timedelta
import os


class TestBDShare:
    """Comprehensive test suite for BDShare v1.1.4"""
    
    @classmethod
    def setup_class(cls):
        cls.end_date = datetime.now().strftime("%Y-%m-%d")
        cls.start_date = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
        cls.test_symbol = "GP"

    # Trading Data Tests
    def test_get_current_trade_data(self):
        result = bdshare.get_current_trade_data()
        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0

    def test_get_current_trade_data_with_symbol(self):
        result = bdshare.get_current_trade_data(self.test_symbol)
        assert isinstance(result, pd.DataFrame)

    def test_get_dsex_data(self):
        result = bdshare.get_dsex_data()
        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0

    def test_get_current_trading_code(self):
        result = bdshare.get_current_trading_code()
        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0

    def test_get_hist_data(self):
        result = bdshare.get_hist_data(self.start_date, self.end_date)
        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0

    def test_get_hist_data_with_symbol(self):
        result = bdshare.get_hist_data(self.start_date, self.end_date, self.test_symbol)
        assert isinstance(result, pd.DataFrame)

    def test_get_basic_hist_data(self):
        result = bdshare.get_basic_hist_data(self.start_date, self.end_date)
        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0

    def test_get_basic_hist_data_with_symbol(self):
        result = bdshare.get_basic_hist_data(self.start_date, self.end_date, self.test_symbol)
        assert isinstance(result, pd.DataFrame)

    def test_get_close_price_data(self):
        result = bdshare.get_close_price_data(self.start_date, self.end_date, self.test_symbol)
        assert isinstance(result, pd.DataFrame)

    def test_get_last_trade_price_data(self):
        result = bdshare.get_last_trade_price_data()
        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0

    # News Functions Tests
    def test_get_agm_news(self):
        result = bdshare.get_agm_news()
        assert isinstance(result, pd.DataFrame)

    def test_get_all_news(self):
        result = bdshare.get_all_news(self.start_date, self.end_date)
        assert isinstance(result, pd.DataFrame)

    def test_get_all_news_with_symbol(self):
        result = bdshare.get_all_news(self.start_date, self.end_date, self.test_symbol)
        assert isinstance(result, pd.DataFrame)

    # Market Data Tests
    def test_get_market_inf(self):
        result = bdshare.get_market_inf()
        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0

    def test_get_latest_pe(self):
        result = bdshare.get_latest_pe()
        assert isinstance(result, pd.DataFrame)

    def test_get_market_inf_more_data(self):
        result = bdshare.get_market_inf_more_data(self.start_date, self.end_date)
        assert isinstance(result, pd.DataFrame)

    def test_get_market_depth_data(self):
        result = bdshare.get_market_depth_data(self.test_symbol)
        assert isinstance(result, pd.DataFrame)

    def test_get_company_inf(self):
        result = bdshare.get_company_inf(self.test_symbol)
        assert isinstance(result, pd.DataFrame)

    # Utility Functions Tests
    def test_get_session(self):
        session = bdshare.get_session()
        assert session is not None

    def test_set_session(self):
        # This should not raise an exception
        bdshare.set_session("test")

    def test_get_token(self):
        token = bdshare.get_token()
        assert token is not None

    def test_set_token(self):
        # This should not raise an exception
        bdshare.set_token("test")

    def test_store_functionality(self):
        df = bdshare.get_current_trade_data()
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0
        
        filename = "test_output.csv"
        store = bdshare.Store(df)
        store.save(filename)
        
        # Verify file was created
        assert os.path.exists(filename)
        
        # Clean up
        if os.path.exists(filename):
            os.remove(filename)

    def test_tickers_functionality(self):
        tickers = bdshare.Tickers()
        assert tickers is not None

    def test_package_version(self):
        version = bdshare.__version__
        assert isinstance(version, str)
        assert len(version) > 0


# Keep your original standalone runner as well for backward compatibility
def main():
    """Original standalone test runner"""
    print("🔍 BDShare v1.1.4 Comprehensive Test Suite")
    print("=" * 50)

    def test_function(func_name, func, *args, **kwargs):
        """Test a single function and return results"""
        try:
            result = func(*args, **kwargs)
            if isinstance(result, pd.DataFrame):
                return f"✅ {func_name}: {len(result)} records"
            elif isinstance(result, dict):
                return f"✅ {func_name}: {len(result)} items"
            elif isinstance(result, list):
                return f"✅ {func_name}: {len(result)} items"
            else:
                return f"✅ {func_name}: {type(result).__name__}"
        except Exception as e:
            return f"❌ {func_name}: {str(e)[:50]}..."

    # Test Trading Data Functions
    print("\n📊 TRADING DATA FUNCTIONS:")
    print("-" * 30)

    results = []
    results.append(test_function("get_current_trade_data()", bdshare.get_current_trade_data))
    results.append(test_function("get_current_trade_data('GP')", bdshare.get_current_trade_data, "GP"))
    results.append(test_function("get_dsex_data()", bdshare.get_dsex_data))
    results.append(test_function("get_current_trading_code()", bdshare.get_current_trading_code))

    # Historical data (last 2 days)
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")

    results.append(test_function("get_hist_data(start, end)", bdshare.get_hist_data, start_date, end_date))
    results.append(test_function("get_hist_data(start, end, 'GP')", bdshare.get_hist_data, start_date, end_date, "GP"))
    results.append(test_function("get_basic_hist_data(start, end)", bdshare.get_basic_hist_data, start_date, end_date))
    results.append(test_function("get_basic_hist_data(start, end, 'GP')", bdshare.get_basic_hist_data, start_date, end_date, "GP"))
    results.append(test_function("get_close_price_data(start, end, 'GP')", bdshare.get_close_price_data, start_date, end_date, "GP"))
    results.append(test_function("get_last_trade_price_data()", bdshare.get_last_trade_price_data))

    for result in results:
        print(result)

    # Test News Functions
    print("\n📰 NEWS FUNCTIONS:")
    print("-" * 20)

    news_results = []
    news_results.append(test_function("get_agm_news()", bdshare.get_agm_news))
    news_results.append(test_function("get_all_news(start, end)", bdshare.get_all_news, start_date, end_date))
    news_results.append(test_function("get_all_news(start, end, 'GP')", bdshare.get_all_news, start_date, end_date, "GP"))

    for result in news_results:
        print(result)

    # Test Market Data Functions
    print("\n📈 MARKET DATA FUNCTIONS:")
    print("-" * 25)

    market_results = []
    market_results.append(test_function("get_market_inf()", bdshare.get_market_inf))
    market_results.append(test_function("get_latest_pe()", bdshare.get_latest_pe))
    market_results.append(test_function("get_market_inf_more_data(start, end)", bdshare.get_market_inf_more_data, start_date, end_date))
    market_results.append(test_function("get_market_depth_data('GP')", bdshare.get_market_depth_data, "GP"))
    market_results.append(test_function("get_company_inf('GP')", bdshare.get_company_inf, "GP"))

    for result in market_results:
        print(result)

    # Test Utility Functions
    print("\n🔧 UTILITY FUNCTIONS:")
    print("-" * 20)

    utility_results = []
    utility_results.append(test_function("get_session()", bdshare.get_session))
    utility_results.append(test_function("set_session('test')", bdshare.set_session, "test"))
    utility_results.append(test_function("get_token()", bdshare.get_token))
    utility_results.append(test_function("set_token('test')", bdshare.set_token, "test"))

    # Test Store and Tickers
    try:
        df = bdshare.get_current_trade_data()
        if len(df) > 0:
            store_result = test_function("Store(df).save()", lambda: bdshare.Store(df).save("test_output.csv"))
            utility_results.append(store_result)
    except Exception as e:
        utility_results.append(f"❌ Store(df).save(): {str(e)[:50]}...")

    try:
        tickers_result = test_function("Tickers()", bdshare.Tickers)
        utility_results.append(tickers_result)
    except Exception as e:
        utility_results.append(f"❌ Tickers(): {str(e)[:50]}...")

    for result in utility_results:
        print(result)

    # Summary
    print("\n" + "=" * 50)
    print("📊 SUMMARY:")

    all_results = results + news_results + market_results + utility_results
    working = len([r for r in all_results if r.startswith("✅")])
    total = len(all_results)

    print(f"✅ Working Functions: {working}/{total} ({working/total*100:.1f}%)")
    print(f"❌ Broken Functions: {total-working}/{total} ({(total-working)/total*100:.1f}%)")

    if working == total:
        print("\n🎉 ALL FUNCTIONS WORKING! BDShare v1.1.4 is fully functional!")
    else:
        print(f"\n⚠️  {total-working} functions still need attention.")

    print(f"\n📦 Package Version: {bdshare.__version__}")
    print("🏁 Test completed!")


if __name__ == "__main__":
    # Run the standalone version when executed directly
    main()