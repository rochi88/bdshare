#!/usr/bin/env python3
"""
Comprehensive Test Suite for BDShare v1.1.4
Tests all functions to verify fixes are working
"""

import bdshare
import pandas as pd
from datetime import datetime, timedelta
import sys


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


def main():
    print("🔍 BDShare v1.1.4 Comprehensive Test Suite")
    print("=" * 50)

    # Test Trading Data Functions
    print("\n📊 TRADING DATA FUNCTIONS:")
    print("-" * 30)

    results = []
    results.append(
        test_function("get_current_trade_data()", bdshare.get_current_trade_data)
    )
    results.append(
        test_function(
            "get_current_trade_data('GP')", bdshare.get_current_trade_data, "GP"
        )
    )
    results.append(test_function("get_dsex_data()", bdshare.get_dsex_data))
    results.append(
        test_function("get_current_trading_code()", bdshare.get_current_trading_code)
    )

    # Historical data (last 2 days)
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")

    results.append(
        test_function(
            "get_hist_data(start, end)", bdshare.get_hist_data, start_date, end_date
        )
    )
    results.append(
        test_function(
            "get_hist_data(start, end, 'GP')",
            bdshare.get_hist_data,
            start_date,
            end_date,
            "GP",
        )
    )
    results.append(
        test_function(
            "get_basic_hist_data(start, end)",
            bdshare.get_basic_hist_data,
            start_date,
            end_date,
        )
    )
    results.append(
        test_function(
            "get_basic_hist_data(start, end, 'GP')",
            bdshare.get_basic_hist_data,
            start_date,
            end_date,
            "GP",
        )
    )
    results.append(
        test_function(
            "get_close_price_data(start, end, 'GP')",
            bdshare.get_close_price_data,
            start_date,
            end_date,
            "GP",
        )
    )
    results.append(
        test_function("get_last_trade_price_data()", bdshare.get_last_trade_price_data)
    )

    for result in results:
        print(result)

    # Test News Functions
    print("\n📰 NEWS FUNCTIONS:")
    print("-" * 20)

    news_results = []
    news_results.append(test_function("get_agm_news()", bdshare.get_agm_news))
    news_results.append(
        test_function(
            "get_all_news(start, end)", bdshare.get_all_news, start_date, end_date
        )
    )
    news_results.append(
        test_function(
            "get_all_news(start, end, 'GP')",
            bdshare.get_all_news,
            start_date,
            end_date,
            "GP",
        )
    )

    for result in news_results:
        print(result)

    # Test Market Data Functions
    print("\n📈 MARKET DATA FUNCTIONS:")
    print("-" * 25)

    market_results = []
    market_results.append(test_function("get_market_inf()", bdshare.get_market_inf))
    market_results.append(test_function("get_latest_pe()", bdshare.get_latest_pe))
    market_results.append(
        test_function(
            "get_market_inf_more_data(start, end)",
            bdshare.get_market_inf_more_data,
            start_date,
            end_date,
        )
    )
    market_results.append(
        test_function(
            "get_market_depth_data('GP')", bdshare.get_market_depth_data, "GP"
        )
    )
    market_results.append(
        test_function("get_company_inf('GP')", bdshare.get_company_inf, "GP")
    )

    for result in market_results:
        print(result)

    # Test Utility Functions
    print("\n🔧 UTILITY FUNCTIONS:")
    print("-" * 20)

    utility_results = []
    utility_results.append(test_function("get_session()", bdshare.get_session))
    utility_results.append(
        test_function("set_session('test')", bdshare.set_session, "test")
    )
    utility_results.append(test_function("get_token()", bdshare.get_token))
    utility_results.append(
        test_function("set_token('test')", bdshare.set_token, "test")
    )

    # Test Store and Tickers
    try:
        df = bdshare.get_current_trade_data()
        if len(df) > 0:
            store_result = test_function(
                "Store(df).save()", lambda: bdshare.Store(df).save("test_output.csv")
            )
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
    print(
        f"❌ Broken Functions: {total-working}/{total} ({(total-working)/total*100:.1f}%)"
    )

    if working == total:
        print("\n🎉 ALL FUNCTIONS WORKING! BDShare v1.1.4 is fully functional!")
    else:
        print(f"\n⚠️  {total-working} functions still need attention.")

    print(f"\n📦 Package Version: {bdshare.__version__}")
    print("🏁 Test completed!")


if __name__ == "__main__":
    main()
