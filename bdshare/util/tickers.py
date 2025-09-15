# -*- coding:utf-8 -*-

"""
Created on 2024/03/04
@author: Raisul Islam
@group : bdshare.xyz
@contact: raisul.me@gmail.com
"""
import json
import os


class Tickers(object):
    def __init__(self):
        # Get the directory where this file is located
        current_dir = os.path.dirname(os.path.abspath(__file__))
        tickers_file = os.path.join(current_dir, "tickers.json")

        if os.path.exists(tickers_file):
            self.f = open(tickers_file)
            self.data = json.load(self.f)
        else:
            # Fallback: try to find tickers.json in current working directory
            if os.path.exists("tickers.json"):
                self.f = open("tickers.json")
                self.data = json.load(self.f)
            else:
                raise FileNotFoundError(
                    "tickers.json file not found. Please ensure it exists in the util directory."
                )

    def close(self):
        self.f.close()

    def ticker_data(self, ticker=None):
        if ticker:
            self.data["data"]["companies" == ticker]
        else:
            self.data["data"]["companies"]
