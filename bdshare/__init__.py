import codecs
import os

__version__ = codecs.open(os.path.join(os.path.dirname(__file__), 'VERSION.txt')).read()
__author__ = 'Raisul Islam'

"""
for trading data
"""
from bdshare.stock.trading import (get_current_trade_data, get_hist_data)