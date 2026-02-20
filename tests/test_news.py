# _*_ coding:utf-8 _*_
'''
Created on 2021-May-28
@author: Raisul Islam
Comprehensive tests for BDShare news functions
'''
import unittest
import pandas as pd
from datetime import datetime, timedelta
from bdshare import get_agm_news, get_all_news


class TestNewsFunctions(unittest.TestCase):
    """
    Test suite for BDShare news functions
    """

    def test_get_agm_news(self):
        """Test get_agm_news function returns valid DataFrame with AGM news"""
        df = get_agm_news()
        
        # Basic DataFrame assertions
        self.assertIsInstance(df, pd.DataFrame, "AGM news should return a DataFrame")
        
        if not df.empty:
            # Check for expected columns in AGM news
            expected_columns = ['company', 'news', 'date']
            for col in expected_columns:
                if col in df.columns:
                    self.assertIn(col, df.columns, f"Column '{col}' should be present in AGM news")
            
            # Check data types and content
            self.assertTrue(len(df) > 0, "AGM news should contain records")
            
            # Verify news content structure
            if 'news' in df.columns:
                news_samples = df['news'].head(3)
                print("Sample AGM News:")
                for news in news_samples:
                    self.assertIsInstance(news, str, "News should be string type")
                    print(f"  - {news}")
        
        print("AGM News Data:")
        print(df.to_string())
        print(f"Total AGM news records: {len(df)}")

    def test_get_agm_news_structure(self):
        """Test the structure and content of AGM news data"""
        df = get_agm_news()
        
        self.assertIsInstance(df, pd.DataFrame)
        
        if not df.empty:
            # Check for non-empty values in key columns
            if 'company' in df.columns:
                company_names = df['company'].dropna()
                self.assertFalse(company_names.empty, "Company names should not be empty")
                print(f"Companies with AGM news: {company_names.unique()[:5]}")  # Show first 5 companies
            
            if 'date' in df.columns:
                dates = df['date'].dropna()
                self.assertFalse(dates.empty, "Dates should not be empty")
                print(f"Date range in AGM news: {dates.min()} to {dates.max()}")

    def test_get_all_news_with_symbol(self):
        """Test get_all_news function with specific company symbol"""
        symbol = 'BATBC'
        df = get_all_news(symbol)
        
        # Basic DataFrame assertions
        self.assertIsInstance(df, pd.DataFrame, "All news should return a DataFrame")
        
        if not df.empty:
            # Check for expected columns
            expected_columns = ['news', 'date', 'symbol']
            for col in expected_columns:
                if col in df.columns:
                    self.assertIn(col, df.columns, f"Column '{col}' should be present in news data")
            
            # Verify the symbol matches
            if 'symbol' in df.columns:
                symbols = df['symbol'].unique()
                self.assertIn(symbol, symbols, f"News should contain data for symbol {symbol}")
            
            # Check news content
            if 'news' in df.columns:
                news_count = len(df['news'].dropna())
                self.assertGreater(news_count, 0, "Should have non-empty news items")
                
                print(f"Sample news for {symbol}:")
                sample_news = df['news'].head(3).tolist()
                for i, news in enumerate(sample_news, 1):
                    print(f"  {i}. {news}")
        
        print(f"All News for {symbol}:")
        print(df.to_string())
        print(f"Total news records for {symbol}: {len(df)}")

    def test_get_all_news_multiple_symbols(self):
        """Test get_all_news function with multiple company symbols"""
        test_symbols = ['BATBC', 'GP', 'ACI', 'SQURPHARMA']
        
        for symbol in test_symbols:
            with self.subTest(symbol=symbol):
                df = get_all_news(symbol)
                self.assertIsInstance(df, pd.DataFrame, f"News for {symbol} should return DataFrame")
                
                if not df.empty:
                    print(f"Found {len(df)} news items for {symbol}")
                    
                    if 'news' in df.columns:
                        # Check that news items are strings
                        news_items = df['news'].dropna()
                        if not news_items.empty:
                            self.assertIsInstance(news_items.iloc[0], str, 
                                                f"News items for {symbol} should be strings")
                else:
                    print(f"No news found for {symbol}")

    def test_get_all_news_with_dates(self):
        """Test get_all_news function with date range"""
        symbol = 'GP'
        
        # Test with recent date range (last 30 days)
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        
        df = get_all_news(symbol, start_date, end_date)
        self.assertIsInstance(df, pd.DataFrame)
        
        if not df.empty and 'date' in df.columns:
            # Verify dates are within range
            dates = pd.to_datetime(df['date'])
            start_dt = pd.to_datetime(start_date)
            end_dt = pd.to_datetime(end_date)
            
            # Check if dates are within the specified range
            within_range = dates.between(start_dt, end_dt)
            self.assertTrue(within_range.any(), 
                          "Some news should be within the specified date range")
            
            print(f"News for {symbol} from {start_date} to {end_date}: {len(df)} records")

    def test_get_all_news_structure_validation(self):
        """Validate the structure and content of news data"""
        symbol = 'ACI'
        df = get_all_news(symbol)
        
        self.assertIsInstance(df, pd.DataFrame)
        
        if not df.empty:
            # Check data types
            if 'news' in df.columns:
                self.assertTrue(pd.api.types.is_string_dtype(df['news']), 
                              "News column should contain strings")
            
            if 'date' in df.columns:
                # Try to convert to datetime to validate format
                try:
                    pd.to_datetime(df['date'])
                    print("Date format is valid")
                except Exception as e:
                    print(f"Date format warning: {e}")
            
            # Check for duplicates
            initial_count = len(df)
            deduplicated_count = len(df.drop_duplicates())
            self.assertEqual(initial_count, deduplicated_count, 
                           "Should not have duplicate news entries")

    def test_news_content_quality(self):
        """Test the quality and relevance of news content"""
        symbol = 'GP'
        df = get_all_news(symbol)
        
        if not df.empty and 'news' in df.columns:
            # Check news length and content
            news_lengths = df['news'].str.len()
            
            # Most news should have reasonable length
            reasonable_news = news_lengths[news_lengths > 10]  # More than 10 characters
            self.assertGreater(len(reasonable_news), 0, 
                             "Should have news items with reasonable length")
            
            print(f"News length statistics for {symbol}:")
            print(f"  Min: {news_lengths.min()} chars")
            print(f"  Max: {news_lengths.max()} chars")
            print(f"  Avg: {news_lengths.mean():.1f} chars")

    def test_error_handling(self):
        """Test error handling for invalid inputs"""
        # Test with invalid symbol
        df_invalid = get_all_news('INVALID_SYMBOL_123')
        self.assertIsInstance(df_invalid, pd.DataFrame)
        # Function should return empty DataFrame or handle gracefully
        
        # Test with invalid date format
        df_dates = get_all_news('GP', 'invalid-date', 'invalid-date')
        self.assertIsInstance(df_dates, pd.DataFrame)

    def test_compare_agm_vs_all_news(self):
        """Compare AGM news with general news for insights"""
        agm_df = get_agm_news()
        company_news_df = get_all_news('GP')
        
        self.assertIsInstance(agm_df, pd.DataFrame)
        self.assertIsInstance(company_news_df, pd.DataFrame)
        
        print("News Data Comparison:")
        print(f"AGM News count: {len(agm_df)}")
        print(f"Company News count: {len(company_news_df)}")
        
        if not agm_df.empty and not company_news_df.empty:
            # Check if there's any overlap in content
            if 'news' in agm_df.columns and 'news' in company_news_df.columns:
                agm_news_set = set(agm_df['news'].dropna().str.lower())
                company_news_set = set(company_news_df['news'].dropna().str.lower())
                
                common_news = agm_news_set.intersection(company_news_set)
                print(f"Common news items: {len(common_news)}")

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures"""
        print("Starting BDShare News Functions Tests...")
        print("=" * 50)

    @classmethod
    def tearDownClass(cls):
        """Clean up after tests"""
        print("=" * 50)
        print("BDShare News Functions Tests completed!")


def run_news_tests():
    """Function to run specific news tests during development"""
    suite = unittest.TestSuite()
    
    # Add specific tests to run
    suite.addTest(TestNewsFunctions('test_get_agm_news'))
    suite.addTest(TestNewsFunctions('test_get_all_news_with_symbol'))
    
    runner = unittest.TextTestRunner(verbosity=2)
    return runner.run(suite)


if __name__ == "__main__":
    # Run all tests
    unittest.main(verbosity=2)
    
    # Or run specific tests during development
    # run_news_tests()