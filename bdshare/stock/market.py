import os
import requests 
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
from bdshare.util import vars as vs

def get_market_inf():
    """
        get stock market information.
        :return: dataframe
    """
    r = requests.get(vs.DSE_MARKET_INF_URL)
    soup = BeautifulSoup(r.text, 'html.parser')
    quotes=[] # a list to store quotes 

    table = soup.find('table', attrs={'class' : 'TFtable', 'cellpadding' : '0'}) 

    for row in table.find_all('tr'):
        cols = row.find_all('td')
        quotes.append((cols[1].text.strip().replace(",", ""), 
                        cols[2].text.strip().replace(",", ""), 
                        cols[3].text.strip().replace(",", ""), 
                        cols[4].text.strip().replace(",", ""), 
                        cols[5].text.strip().replace(",", ""), 
                        cols[6].text.strip().replace(",", ""), 
                        cols[7].text.strip().replace(",", ""), 
                        cols[8].text.strip().replace(",", "")
                        ))
    df = pd.DataFrame(quotes)
    return df


def get_latest_pe():
    """
        get last stock P/E.
        :return: dataframe
    """
    r = requests.get(vs.DSE_LPE_URL)
    soup = BeautifulSoup(r.text, 'html.parser')
    quotes=[] # a list to store quotes 
    table = soup.find('table') 
    for row in table.find_all('tr'):
        cols = row.find_all('td')
        quotes.append((cols[1].text.strip().replace(",", ""), 
                        cols[2].text.strip().replace(",", ""), 
                        cols[3].text.strip().replace(",", ""), 
                        cols[4].text.strip().replace(",", ""), 
                        cols[5].text.strip().replace(",", ""), 
                        cols[6].text.strip().replace(",", ""), 
                        cols[7].text.strip().replace(",", ""), 
                        cols[8].text.strip().replace(",", ""), 
                        cols[9].text.strip().replace(",", "")
                        ))
    df = pd.DataFrame(quotes)
    return df