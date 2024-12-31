# _*_ coding:utf-8 _*_
'''
Created on 2021-May-28
@author: Raisul Islam
'''
import unittest
import datetime as dt
from bdshare import get_dsex_data, get_current_trade_data, get_basic_hist_data, get_market_inf_more_data


class Test(unittest.TestCase):

    def test_get_dsex_data(self):
        df = get_dsex_data()
        print(df.to_string())

    def test_get_current_trade_data(self):
        df = get_current_trade_data()
        print(df.to_string())

    def test_get_market_inf_more_data(self):
        start = dt.datetime.now().date() - dt.timedelta(days=2 * 365)
        end = dt.datetime.now().date()
        df = get_market_inf_more_data(start, end, index='date')
        print(df.to_string())
        print(df.dtypes)

    def test_get_basic_hist_data(self):
        start = dt.datetime.now().date() - dt.timedelta(days=2 * 365)
        end = dt.datetime.now().date()
        df = get_basic_hist_data(start, end, 'BATBC')
        print(df.to_string())
        print(df.dtypes)


if __name__ == "__main__":
    unittest.main()
