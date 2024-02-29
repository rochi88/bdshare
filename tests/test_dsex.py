# _*_ coding:utf-8 _*_
'''
Created on 2021-Jun-09
@author: Raisul Islam
'''
from bdshare import get_dsex_data, Store

df = get_dsex_data()

print(df.to_string())
Store(data=df).save()