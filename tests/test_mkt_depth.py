# _*_ coding:utf-8 _*_
'''
Created on 2024-Mar-01
@author: Raisul Islam
'''

from bdshare import get_market_depth_data

df = get_market_depth_data('AAMRANET')

print(df.to_string())