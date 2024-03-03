# -*- coding:utf-8 -*- 

"""
Created on 2024/03/03
@author: Raisul Islam
@group : bdshare.xyz
@contact: raisul.me@gmail.com
"""

import pandas as pd
import os
from . import cons as ct

def set_session(session):
    df = pd.DataFrame([session], columns=['session'])
    user_home = os.path.expanduser('~')
    fp = os.path.join(user_home, ct.SESSION_F_P)
    df.to_csv(fp, index=False)


def get_session():
    user_home = os.path.expanduser('~')
    fp = os.path.join(user_home, ct.SESSION_F_P)
    if os.path.exists(fp):
        df = pd.read_csv(fp)
        return str(df.ix[0]['session'])
    else:
        print(ct.SESSION_ERR_MSG)
        return None