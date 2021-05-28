# _*_ coding:utf-8 _*_
'''
Created on 2021-May-28
@author: Raisul Islam
'''
import unittest
import datetime as dt
from bdshare import get_agm_news, get_all_news

class Test(unittest.TestCase):

    def test_get_agm_news(self):
        df = get_agm_news()
        print(df.to_string())

    def test_get_all_news(self):
        end = dt.datetime.now().date()
        df = get_all_news('BATBC')
        print(df.to_string())


if __name__ == "__main__":
    unittest.main()
