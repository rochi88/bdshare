# _*_ coding:utf-8 _*_
'''
Created on 2021-May-28
@author: Raisul Islam
'''
import unittest
import datetime as dt
from bdshare import get_current_trade_data, get_basic_hist_data, get_market_inf_more_data

class Test(unittest.TestCase):

    def test_get_current_trade_data(self):
        df = get_current_trade_data()
        print(df.to_string())

    def test_get_market_inf_more_data(self):
        end = dt.datetime.now().date()
        df = get_market_inf_more_data('2020-01-01', end, index='date')
        print(df.to_string())
        print(df.dtypes)

    def test_get_basic_hist_data(self):
        end = dt.datetime.now().date()
        df = get_basic_hist_data('2020-01-01', end,'BATBC')
        print(df.to_string())
        print(df.dtypes)

if __name__ == "__main__":
    unittest.main()
