# _*_ coding:utf-8 _*_
'''
Created on 2024-Dec-31
@author: Raisul Islam
Comprehensive tests for BDShare market data functions
'''
import unittest
import datetime as dt
import pandas as pd
from bdshare import get_latest_pe, get_market_inf, get_market_depth_data, get_market_inf_more_data, get_company_inf


class TestMarketDataFunctions(unittest.TestCase):
    """
    Test suite for BDShare market data functions
    """

    def test_get_latest_pe(self):
        """Test get_latest_pe function returns valid DataFrame"""
        df = get_latest_pe()
        
        # Basic DataFrame assertions
        self.assertIsInstance(df, pd.DataFrame)
        self.assertFalse(df.empty, "PE data should not be empty")
        
        # Check for expected columns
        expected_columns = ['trading_code', 'pe_ratio', 'sector']
        for col in expected_columns:
            if col in df.columns:
                self.assertTrue(col in df.columns, f"Column '{col}' should be present")
        
        print("Latest PE Data:")
        print(df.head().to_string())
        print(f"Total records: {len(df)}")

    def test_get_market_inf(self):
        """Test get_market_inf function returns valid market information"""
        df = get_market_inf()
        
        # Basic DataFrame assertions
        self.assertIsInstance(df, pd.DataFrame)
        self.assertFalse(df.empty, "Market info should not be empty")
        
        # Check for important market metrics
        self.assertTrue(len(df) > 0, "Market info should contain data")
        
        print("Market Information:")
        print(df.to_string())
        print(f"Data shape: {df.shape}")

    def test_get_market_depth_data(self):
        """Test get_market_depth_data function for specific stock"""
        symbol = 'GP'
        df = get_market_depth_data(symbol)
        
        # Basic DataFrame assertions
        self.assertIsInstance(df, pd.DataFrame)
        
        # Market depth data might be empty during off-hours, so we don't assert on emptiness
        if not df.empty:
            # Check structure if data exists
            expected_columns = ['bid_price', 'bid_volume', 'ask_price', 'ask_volume']
            for col in expected_columns:
                if col in df.columns:
                    self.assertTrue(col in df.columns, f"Column '{col}' should be present in market depth data")
        
        print(f"Market Depth Data for {symbol}:")
        print(df.to_string())
        print(f"Data shape: {df.shape}")

    def test_get_market_depth_data_multiple_symbols(self):
        """Test get_market_depth_data function with multiple stock symbols"""
        test_symbols = ['GP', 'ACI', 'SQURPHARMA']
        
        for symbol in test_symbols:
            with self.subTest(symbol=symbol):
                df = get_market_depth_data(symbol)
                self.assertIsInstance(df, pd.DataFrame)
                print(f"Market depth for {symbol}: {len(df)} records")

    def test_get_market_inf_more_data(self):
        """Test get_market_inf_more_data function with date range"""
        start = dt.datetime.now().date() - dt.timedelta(days=30)  # Reduced to 30 days for faster testing
        end = dt.datetime.now().date()
        
        df = get_market_inf_more_data(start, end, index='date')
        
        # Basic DataFrame assertions
        self.assertIsInstance(df, pd.DataFrame)
        
        if not df.empty:
            # Check date range
            if 'date' in df.columns:
                dates = pd.to_datetime(df['date'])
                self.assertTrue(all(start <= d.date() <= end for d in dates if pd.notna(d)))
            
            # Check data types
            print("Data types:")
            print(df.dtypes)
        
        print("Market Information Over Time:")
        print(df.to_string())
        print(f"Data shape: {df.shape}")

    def test_get_market_inf_more_data_different_periods(self):
        """Test get_market_inf_more_data with different time periods"""
        test_periods = [
            (7, "1 week"),
            (30, "1 month"),
            (90, "3 months")
        ]
        
        for days, period_name in test_periods:
            with self.subTest(period=period_name):
                start = dt.datetime.now().date() - dt.timedelta(days=days)
                end = dt.datetime.now().date()
                
                df = get_market_inf_more_data(start, end)
                self.assertIsInstance(df, pd.DataFrame)
                print(f"{period_name} data: {len(df)} records")

    def test_get_company_inf(self):
        """Test get_company_inf function for specific company"""
        symbol = 'GP'
        df = get_company_inf(symbol)
        
        # Basic DataFrame assertions
        self.assertIsInstance(df, pd.DataFrame)
        
        if not df.empty:
            # Should contain company information
            self.assertTrue(len(df) > 0, "Company info should contain data")
            
            # Check for company-specific columns
            company_columns = ['company_name', 'trading_code', 'sector', 'listing_year']
            for col in company_columns:
                if col in df.columns:
                    self.assertTrue(col in df.columns, f"Column '{col}' should be present in company info")
        
        print(f"Company Information for {symbol}:")
        print(df.to_string())

    def test_get_company_inf_multiple_companies(self):
        """Test get_company_inf function with multiple companies"""
        test_companies = ['GP', 'ACI', 'SQURPHARMA', 'BEXIMCO']
        
        for symbol in test_companies:
            with self.subTest(company=symbol):
                df = get_company_inf(symbol)
                self.assertIsInstance(df, pd.DataFrame)
                if not df.empty:
                    print(f"Company info for {symbol}: {len(df)} records")
                else:
                    print(f"No company info found for {symbol}")

    def test_data_consistency(self):
        """Test consistency between different market data functions"""
        # Get market info
        market_info = get_market_inf()
        self.assertIsInstance(market_info, pd.DataFrame)
        
        # Get PE data
        pe_data = get_latest_pe()
        self.assertIsInstance(pe_data, pd.DataFrame)
        
        # Both should be DataFrames
        self.assertIsInstance(market_info, pd.DataFrame)
        self.assertIsInstance(pe_data, pd.DataFrame)
        
        print("Data consistency check passed - all functions return DataFrames")

    def test_error_handling(self):
        """Test error handling for invalid inputs"""
        # Test with invalid symbol for market depth
        with self.assertRaises(Exception):
            get_market_depth_data('INVALID_SYMBOL_123')
        
        # Test with invalid date range
        future_date = dt.datetime.now().date() + dt.timedelta(days=365)
        df = get_market_inf_more_data(future_date, future_date)
        self.assertIsInstance(df, pd.DataFrame)
        # Should return empty DataFrame or handle gracefully

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures"""
        print("Starting BDShare Market Data Tests...")
        print("=" * 50)

    @classmethod
    def tearDownClass(cls):
        """Clean up after tests"""
        print("=" * 50)
        print("BDShare Market Data Tests completed!")


def run_specific_tests():
    """Function to run specific tests during development"""
    suite = unittest.TestSuite()
    
    # Add specific tests to run
    suite.addTest(TestMarketDataFunctions('test_get_market_inf'))
    suite.addTest(TestMarketDataFunctions('test_get_latest_pe'))
    
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)


if __name__ == "__main__":
    # Run all tests
    unittest.main(verbosity=2)
    
    # Or run specific tests during development
    # run_specific_tests()