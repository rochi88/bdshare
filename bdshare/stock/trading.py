import os
import requests 
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
from bdshare.util import vars as vs


def get_current_trade_data():
    """
        get last stock price.
        :return: dataframe
    """
    r = requests.get(vs.DSE_LSP_URL)
    soup = BeautifulSoup(r.text, 'html.parser')
    quotes=[] # a list to store quotes 
    table = soup.find('table') 
    for row in table.find_all('tr'):
        cols = row.find_all('td')
        quotes.append((cols[1].text.strip().replace(",", ""), cols[2].text.strip().replace(",", ""), cols[3].text.strip().replace(",", ""), cols[4].text.strip().replace(",", ""), cols[5].text.strip().replace(",", ""), cols[6].text.strip().replace(",", ""), cols[7].text.strip().replace("--", "0"), cols[8].text.strip().replace(",", ""), cols[9].text.strip().replace(",", ""),cols[10].text.strip().replace(",", "")))
    df = pd.DataFrame(quotes)
    return df

def get_current_trading_code():
    """
        get last stock codes.
        :return: dataframe
    """
    r = requests.get(vs.DSE_LSP_URL)
    soup = BeautifulSoup(r.text, 'html.parser')
    quotes=[] # a list to store quotes 
    table = soup.find('table') 
    for row in table.find_all('tr')[1:]:
        cols = row.find_all('td')
        quotes.append((cols[1].text.strip().replace(",", "")))
    df = pd.DataFrame(quotes)
    return df


def get_hist_data(start=None, end=None, code='All Instrument'):
    """
        get historical stock price.
        :param start: str, Start date e.g.: '2020-03-01'
        :param end: str, End date e.g.: '2020-03-02'
        :param code: str, Instrument symbol e.g.: 'ACI'
        :return: dataframe
    """
    # data to be sent to post request
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


def get_basic_hist_data(start=None, end=None, code='All Instrument'):
    """
        get historical stock price.
        :param start: str, Start date e.g.: '2020-03-01'
        :param end: str, End date e.g.: '2020-03-02'
        :param code: str, Instrument symbol e.g.: 'ACI'
        :return: dataframe
    """
    # data to be sent to post request
    data = {'DayEndSumDate1': start,
            'DayEndSumDate2': end,
            'Symbol': code,
            'ViewDayEndArchive': 'View Day End Archive'}

    r = requests.post(url = vs.DSE_DEA_URL, data = data) 

    soup = BeautifulSoup(r.text, 'html.parser')

    # columns: date, open, high, close, low, volume
    quotes=['date', 'open', 'high', 'close', 'low', 'volume'] # a list to store quotes 


    table = soup.find('table', attrs={'cellspacing' : '1'})

    for row in table.find_all('tr'):
        cols = row.find_all('td')
        quotes.append((cols[1].text.strip().replace(",", ""), cols[5].text.strip().replace(",", ""), cols[3].text.strip().replace(",", ""), cols[6].text.strip().replace(",", ""), cols[4].text.strip().replace(",", ""), cols[10].text.strip().replace(",", "")))
    df = pd.DataFrame(quotes)
    return df