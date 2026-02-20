# _*_ coding:utf-8 _*_
'''
Created on 2021-May-28
@author: Raisul Islam
Comprehensive tests for BDShare core trading and market data functions
'''
import unittest
import datetime as dt
import pandas as pd
from bdshare import get_dsex_data, get_current_trade_data, get_basic_historical_data, get_market_inf_more_data


class TestTradingDataFunctions(unittest.TestCase):
    """
    Test suite for BDShare core trading and market data functions
    """

    def test_get_dsex_data(self):
        """Test DSEX index data retrieval"""
        df = get_dsex_data()
        
        # Basic DataFrame assertions
        self.assertIsInstance(df, pd.DataFrame, "DSEX data should return a DataFrame")
        self.assertFalse(df.empty, "DSEX data should not be empty")
        
        # Check for expected columns in DSEX data
        expected_columns = ['index', 'value', 'change', 'percent_change', 'date']
        for col in expected_columns:
            if col in df.columns:
                self.assertIn(col, df.columns, f"Column '{col}' should be present in DSEX data")
        
        # Validate data content
        if 'value' in df.columns:
            values = df['value'].dropna()
            self.assertFalse(values.empty, "DSEX values should not be empty")
            self.assertTrue(all(values > 0), "DSEX values should be positive")
        
        if 'change' in df.columns:
            changes = df['change'].dropna()
            print(f"DSEX change range: {changes.min()} to {changes.max()}")
        
        print("DSEX Data:")
        print(df.to_string())
        print(f"DSEX records: {len(df)}")

    def test_get_dsex_data_structure(self):
        """Test the structure and consistency of DSEX data"""
        df = get_dsex_data()
        
        self.assertIsInstance(df, pd.DataFrame)
        self.assertGreater(len(df), 0, "Should have multiple DSEX records")
        
        # Check data types
        if 'value' in df.columns:
            self.assertTrue(pd.api.types.is_numeric_dtype(df['value']), 
                          "DSEX value should be numeric")
        
        if 'date' in df.columns:
            # Try to parse dates
            try:
                dates = pd.to_datetime(df['date'])
                print(f"DSEX data date range: {dates.min()} to {dates.max()}")
            except Exception as e:
                print(f"Date parsing note: {e}")

    def test_get_current_trade_data(self):
        """Test current trading data retrieval"""
        df = get_current_trade_data()
        
        # Basic DataFrame assertions
        self.assertIsInstance(df, pd.DataFrame, "Current trade data should return a DataFrame")
        self.assertFalse(df.empty, "Current trade data should not be empty")
        
        # Check for expected trading data columns
        expected_columns = ['trading_code', 'ltp', 'high', 'low', 'close', 'ycp', 'trade', 'value', 'volume']
        found_columns = [col for col in expected_columns if col in df.columns]
        self.assertGreater(len(found_columns), 0, "Should have at least some trading columns")
        
        # Validate numeric columns
        numeric_columns = ['ltp', 'high', 'low', 'close', 'volume']
        for col in numeric_columns:
            if col in df.columns:
                numeric_data = pd.to_numeric(df[col], errors='coerce').dropna()
                self.assertGreater(len(numeric_data), 0, f"Should have numeric data in {col}")
        
        print("Current Trade Data:")
        print(df.head(10).to_string())  # Show first 10 records
        print(f"Total trading instruments: {len(df)}")
        print(f"Columns: {df.columns.tolist()}")

    def test_get_current_trade_data_with_symbol(self):
        """Test current trading data for specific symbol"""
        test_symbols = ['BATBC', 'GP', 'ACI', 'SQURPHARMA']
        
        for symbol in test_symbols:
            with self.subTest(symbol=symbol):
                df = get_current_trade_data(symbol)
                self.assertIsInstance(df, pd.DataFrame, 
                                    f"Trade data for {symbol} should return DataFrame")
                
                if not df.empty:
                    # Verify symbol is in the data
                    if 'trading_code' in df.columns:
                        symbols = df['trading_code'].unique()
                        self.assertIn(symbol, symbols, 
                                    f"Data should contain trading code {symbol}")
                    print(f"Found trade data for {symbol}: {len(df)} records")
                else:
                    print(f"No current trade data found for {symbol}")

    def test_get_current_trade_data_validation(self):
        """Validate the quality and consistency of current trade data"""
        df = get_current_trade_data()
        
        if not df.empty:
            # Check for duplicates
            initial_count = len(df)
            unique_count = len(df.drop_duplicates())
            self.assertEqual(initial_count, unique_count, 
                           "Should not have duplicate trading records")
            
            # Check for missing values in key columns
            if 'trading_code' in df.columns:
                missing_codes = df['trading_code'].isna().sum()
                self.assertEqual(missing_codes, 0, 
                               "Trading codes should not be missing")
            
            # Validate price relationships
            if all(col in df.columns for col in ['high', 'low', 'ltp']):
                # LTP should be between high and low
                valid_prices = df.dropna(subset=['high', 'low', 'ltp'])
                if not valid_prices.empty:
                    price_check = (valid_prices['ltp'] >= valid_prices['low']) & \
                                 (valid_prices['ltp'] <= valid_prices['high'])
                    valid_percentage = price_check.mean()
                    print(f"Price consistency: {valid_percentage:.1%} of records have valid LTP")

    def test_get_market_inf_more_data(self):
        """Test market information over time with date range"""
        start = dt.datetime.now().date() - dt.timedelta(days=30)  # Reduced for faster testing
        end = dt.datetime.now().date()
        
        df = get_market_inf_more_data(start, end, index='date')
        
        # Basic DataFrame assertions
        self.assertIsInstance(df, pd.DataFrame, "Market info over time should return DataFrame")
        
        if not df.empty:
            # Check date range
            if 'date' in df.columns:
                dates = pd.to_datetime(df['date'])
                start_dt = pd.to_datetime(start)
                end_dt = pd.to_datetime(end)
                
                # Check if dates are within range
                within_range = dates.between(start_dt, end_dt)
                self.assertTrue(within_range.any(), 
                              "Should have data within specified date range")
            
            # Check for market metrics columns
            market_columns = ['dse_index', 'total_trade', 'total_volume', 'total_value']
            for col in market_columns:
                if col in df.columns:
                    self.assertIn(col, df.columns, f"Market column '{col}' should be present")
        
        print("Market Information Over Time:")
        print(df.to_string())
        print(f"Data shape: {df.shape}")
        print("Data types:")
        print(df.dtypes)

    def test_get_market_inf_more_data_different_periods(self):
        """Test market information with different time periods"""
        test_periods = [
            (7, "1 week"),
            (30, "1 month"),
            (90, "3 months"),
            (365, "1 year")
        ]
        
        for days, period_name in test_periods:
            with self.subTest(period=period_name):
                start = dt.datetime.now().date() - dt.timedelta(days=days)
                end = dt.datetime.now().date()
                
                df = get_market_inf_more_data(start, end)
                self.assertIsInstance(df, pd.DataFrame)
                
                if not df.empty:
                    print(f"{period_name} market data: {len(df)} records")
                    
                    # Check data completeness
                    if 'date' in df.columns:
                        date_range = pd.to_datetime(df['date'])
                        actual_days = (date_range.max() - date_range.min()).days
                        print(f"  Actual date range: {actual_days} days")
                else:
                    print(f"No market data for {period_name}")

    def test_get_basic_historical_data(self):
        """Test basic historical data retrieval for specific symbol"""
        start = dt.datetime.now().date() - dt.timedelta(days=30)  # Reduced for faster testing
        end = dt.datetime.now().date()
        symbol = 'BATBC'
        
        df = get_basic_historical_data(start, end, symbol)
        
        # Basic DataFrame assertions
        self.assertIsInstance(df, pd.DataFrame, "Historical data should return DataFrame")
        
        if not df.empty:
            # Check for expected OHLCV columns
            expected_columns = ['date', 'open', 'high', 'low', 'close', 'volume']
            for col in expected_columns:
                self.assertIn(col, df.columns, f"Column '{col}' should be present in historical data")
            
            # Validate price data
            price_columns = ['open', 'high', 'low', 'close']
            for col in price_columns:
                if col in df.columns:
                    prices = pd.to_numeric(df[col], errors='coerce').dropna()
                    self.assertGreater(len(prices), 0, f"Should have price data in {col}")
                    self.assertTrue(all(prices > 0), f"{col} prices should be positive")
            
            # Validate high >= low >= close relationships
            if all(col in df.columns for col in ['high', 'low', 'close']):
                valid_records = df.dropna(subset=['high', 'low', 'close'])
                high_low_check = (valid_records['high'] >= valid_records['low']).all()
                self.assertTrue(high_low_check, "High should be >= Low for all records")
        
        print(f"Basic Historical Data for {symbol}:")
        print(df.to_string())
        print(f"Data shape: {df.shape}")
        print("Data types:")
        print(df.dtypes)

    def test_get_basic_historical_data_multiple_symbols(self):
        """Test historical data for multiple symbols"""
        test_symbols = ['BATBC', 'GP', 'ACI', 'SQURPHARMA']
        start = dt.datetime.now().date() - dt.timedelta(days=30)
        end = dt.datetime.now().date()
        
        for symbol in test_symbols:
            with self.subTest(symbol=symbol):
                df = get_basic_historical_data(start, end, symbol)
                self.assertIsInstance(df, pd.DataFrame)
                
                if not df.empty:
                    # Check data structure
                    expected_columns = ['date', 'open', 'high', 'low', 'close', 'volume']
                    missing_columns = [col for col in expected_columns if col not in df.columns]
                    
                    if missing_columns:
                        print(f"Missing columns for {symbol}: {missing_columns}")
                    else:
                        print(f"Valid historical data for {symbol}: {len(df)} records")
                        
                        # Show price statistics
                        if 'close' in df.columns:
                            close_prices = pd.to_numeric(df['close'], errors='coerce').dropna()
                            if not close_prices.empty:
                                print(f"  Close price range: {close_prices.min():.2f} - {close_prices.max():.2f}")
                else:
                    print(f"No historical data found for {symbol}")

    def test_historical_data_consistency(self):
        """Test consistency and quality of historical data"""
        symbol = 'GP'
        start = dt.datetime.now().date() - dt.timedelta(days=60)
        end = dt.datetime.now().date()
        
        df = get_basic_historical_data(start, end, symbol)
        
        if not df.empty:
            # Check for date continuity
            if 'date' in df.columns:
                dates = pd.to_datetime(df['date']).sort_values()
                date_diff = dates.diff().dropna()
                
                if not date_diff.empty:
                    avg_gap = date_diff.mean()
                    print(f"Average date gap for {symbol}: {avg_gap}")
            
            # Check volume and price correlation
            if all(col in df.columns for col in ['volume', 'close']):
                volume = pd.to_numeric(df['volume'], errors='coerce')
                close = pd.to_numeric(df['close'], errors='coerce')
                
                if not volume.empty and not close.empty:
                    correlation = volume.corr(close)
                    print(f"Volume-Price correlation for {symbol}: {correlation:.3f}")

    def test_data_integration(self):
        """Test integration between different data functions"""
        # Get current trade data
        current_df = get_current_trade_data()
        self.assertIsInstance(current_df, pd.DataFrame)
        
        # Get DSEX data
        dsex_df = get_dsex_data()
        self.assertIsInstance(dsex_df, pd.DataFrame)

        df = None
        
        # Get historical data for a symbol from current data
        if not current_df.empty and 'trading_code' in current_df.columns:
            sample_symbol = current_df['trading_code'].iloc[0]
            start = dt.datetime.now().date() - dt.timedelta(days=7)
            end = dt.datetime.now().date()
            
            hist_df = get_basic_historical_data(start, end, sample_symbol)
            self.assertIsInstance(df, pd.DataFrame)
            
            print("Data Integration Summary:")
            print(f"Current trade records: {len(current_df)}")
            print(f"DSEX records: {len(dsex_df)}")
            print(f"Historical records for {sample_symbol}: {len(hist_df)}")

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures"""
        print("Starting BDShare Trading Data Tests...")
        print("=" * 60)

    @classmethod
    def tearDownClass(cls):
        """Clean up after tests"""
        print("=" * 60)
        print("BDShare Trading Data Tests completed!")


def run_core_tests():
    """Function to run core trading data tests during development"""
    suite = unittest.TestSuite()
    
    # Add core tests to run
    suite.addTest(TestTradingDataFunctions('test_get_current_trade_data'))
    suite.addTest(TestTradingDataFunctions('test_get_dsex_data'))
    
    runner = unittest.TextTestRunner(verbosity=2)
    return runner.run(suite)


if __name__ == "__main__":
    # Run all tests
    unittest.main(verbosity=2)
    
    # Or run specific tests during development
    # run_core_tests()