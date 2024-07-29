# _*_ coding:utf-8 _*_
'''
Created on 2024-July-29
@author: Raisul Islam
'''
from bdshare import get_latest_pe

df = get_latest_pe()

print(df.to_string())