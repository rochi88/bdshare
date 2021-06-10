# _*_ coding:utf-8 _*_
'''
Created on 2021-Jun-09
@author: Raisul Islam
'''
# from bdshare import get_market_inf_more_data

# df = get_market_inf_more_data('2020-03-01','2020-03-02')

from bdshare import get_market_inf

df = get_market_inf()

print(df.to_string())