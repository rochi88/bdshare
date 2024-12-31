# _*_ coding:utf-8 _*_
'''
Created on 2024-Dec-31
@author: Raisul Islam
'''

from bdshare import get_company_inf

df = get_company_inf('GP')

print(f'Total tables: {len(df)}')

# for i in range(len(df)):
#     print(f'Table {i}')
#     print(df[i].to_string())

print(df[8])
