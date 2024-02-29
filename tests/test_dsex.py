# _*_ coding:utf-8 _*_
'''
Created on 2021-Jun-09
@author: Raisul Islam
'''
from bdshare import get_dsex_data, Store

df = get_dsex_data()
Store(data=df)
print(df.to_string())