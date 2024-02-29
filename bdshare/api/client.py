# !/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Created on 2024/02/29
@author: Raisul Islam
@group : bdshare.xyz
"""

import pandas as pd
import simplejson as json
from functools import partial
import requests


class DataApi:

    __token = ''
    __http_url = 'https://api.bdshare.xyz'

    def __init__(self, token, timeout=10):
        """
        Parameters
        ----------
        token: str
            API TOKEN, Used for user authentication
        """
        self.__token = token
        self.__timeout = timeout

    def query(self, api_name, fields='', **kwargs):
        req_params = {
            'api_name': api_name,
            'token': self.__token,
            'params': kwargs,
            'fields': fields
        }

        res = requests.post(self.__http_url, json=req_params, timeout=self.__timeout)
        result = json.loads(res.text)
        if result['code'] != 0:
            raise Exception(result['msg'])
        data = result['data']
        columns = data['fields']
        items = data['items']

        return pd.DataFrame(items, columns=columns)

    def __getattr__(self, name):
        return partial(self.query, name)