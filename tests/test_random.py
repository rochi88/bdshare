# _*_ coding:utf-8 _*_
'''
Created on 2021-May-29
@author: Raisul Islam
'''
from bdshare import get_current_trade_data

df = get_current_trade_data()
print(df.to_json(orient ='records'))
print(df.to_string())
