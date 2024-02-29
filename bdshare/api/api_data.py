# -*- coding:utf-8 -*- 
"""
Created on 2024/02/29
@author: Raisul Islam
@group : bdshare.xyz
@contact: raisul.me@gmail.com
"""
from bdshare.api import client
from bdshare.util import upass


PRICE_COLS = ['open', 'close', 'high', 'low', 'pre_close']
FORMAT = lambda x: '%.2f' % x
FREQS = {'D': '1DAY',
         'W': '1WEEK',
         'Y': '1YEAR',
        }


def api_data(token=''):
    """
    Initialize the API. For the first time, you can record your token credentials through bs.set_token('your token'). The temporary token can be passed in through this parameter.
    """
    if token == '' or token is None:
        token = upass.get_token()
    if token is not None and token != '':
        api = client.DataApi(token)
        return api
    else:
        raise Exception('api init error.') 