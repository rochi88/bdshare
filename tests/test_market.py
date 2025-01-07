# _*_ coding:utf-8 _*_
'''
Created on 2024-Dec-31
@author: Raisul Islam
'''
import unittest
import datetime as dt
from bdshare import get_latest_pe, get_market_inf, get_market_depth_data, get_market_inf_more_data  # noqa


class Test(unittest.TestCase):

    def test_get_latest_pe(self):
        df = get_latest_pe()
        print(df.to_string())

    def test_get_market_inf(self):
        df = get_market_inf()
        print(df.to_string())

    def test_get_market_depth(self):
        df = get_market_depth_data('AAMRANET')
        print(df.to_string())

    def test_get_market_inf_more_data(self):
        start = dt.datetime.now().date() - dt.timedelta(days=2 * 365)
        end = dt.datetime.now().date()
        df = get_market_inf_more_data(start, end, index='date')
        print(df.to_string())
        print(df.dtypes)


if __name__ == "__main__":
    unittest.main()
