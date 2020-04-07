import os
import requests 
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
from bdshare.stock import vars as vs


def get_current_trade_data():
    r = requests.get(vs.DSE_LSP_URL)
    soup = BeautifulSoup(r.text, 'html.parser')
    quotes=[] # a list to store quotes 
    table = soup.find('table') 
    for row in table.find_all('tr'):
        cols = row.find_all('td')
        quotes.append((cols[1].text.strip().replace(",", ""), cols[2].text.strip().replace(",", ""), cols[3].text.strip().replace(",", ""), cols[4].text.strip().replace(",", ""), cols[5].text.strip().replace(",", ""), cols[6].text.strip().replace(",", ""), cols[7].text.strip().replace("--", "0"), cols[8].text.strip().replace(",", ""), cols[9].text.strip().replace(",", ""),cols[10].text.strip().replace(",", "")))
    df = pd.DataFrame(quotes)
    return df


def get_hist_data(start=None, end=None, code='All Instrument'):
    # data to be sent to api 
    data = {'DayEndSumDate1': start,
            'DayEndSumDate2': end,
            'Symbol': code,
            'ViewDayEndArchive': 'View Day End Archive'}

    r = requests.post(url = vs.DSE_DEA_URL, data = data) 

    soup = BeautifulSoup(r.text, 'html.parser')

    quotes=[] # a list to store quotes 


    table = soup.find('table', attrs={'cellspacing' : '1'})

    for row in table.find_all('tr'):
        cols = row.find_all('td')
        quotes.append((cols[1].text.strip().replace(",", ""), cols[2].text.strip().replace(",", ""), cols[3].text.strip().replace(",", ""), cols[4].text.strip().replace(",", ""), cols[5].text.strip().replace(",", ""), cols[6].text.strip().replace(",", ""), cols[7].text.strip().replace(",", ""), cols[8].text.strip().replace(",", ""), cols[9].text.strip().replace(",", ""),cols[10].text.strip().replace(",", ""),cols[11].text.strip().replace(",", "")))
    df = pd.DataFrame(quotes)
    return df