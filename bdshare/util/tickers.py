# -*- coding:utf-8 -*- 

"""
Created on 2024/03/04
@author: Raisul Islam
@group : bdshare.xyz
@contact: raisul.me@gmail.com
"""
import json

class Tickers(object):
    def __init__(self):
        self.f = open('tickers.json')
        self.data = json.load(self.f)

    def close(self):
        self.f.close()

    def ticker_data(self, ticker=None):
        if ticker:
            self.data['data']['companies' == ticker]
        else:
            self.data['data']['companies']
