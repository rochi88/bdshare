# -*- coding:utf-8 -*-

import pandas as pd
from datetime import datetime
import os

class Store(object):
    """
        Store dataframe
        :param data: dataframe,
        :param name: str,
        :param path: str,
        :return: none
    """
    def __init__(self, data=None, name=None, path=None):
        if isinstance(data, pd.DataFrame):
            self.data = data
        else:
            raise RuntimeError('data type is incorrect')
        self.name = name
        self.path = path

    def save(self, to='csv'):
        if self.name is None:
            self.name = f'{datetime.now().strftime("%Y%m%d-%H%M%S")}'

        file_path = '%s%s%s.%s'
        if isinstance(self.name, str) and self.name is not '':
            if (self.path is None) or (self.path == ''):
                file_path = '.'.join([self.name, to])
                self.data.to_csv(file_path, index=False)
            else:
                try:
                    if os.path.exists(self.path) is False:
                        os.mkdir(self.path) 
                    file_path = file_path%(self.path, '', self.name, to)
                    self.data.to_csv(file_path, index=False)
                except:
                    pass
            
        else:
            print('input error')

