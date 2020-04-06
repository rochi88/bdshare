import os

__version__ = '0.0.1'
__author__ = 'Raisul Islam'

"""
for trading data
"""
from dshare.stock.trading import (get_hist_data, get_tick_data,
                                   get_today_all, get_realtime_quotes,
                                   get_h_data, get_today_ticks,
                                   get_index, get_hists,
                                   get_k_data, get_day_all,
                                   get_sina_dd, bar, tick,
                                   get_markets, quotes,
                                   get_instrument, reset_instrument)