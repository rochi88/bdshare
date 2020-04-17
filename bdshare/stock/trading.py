import os
import requests 
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
from bdshare.util import vars as vs


def get_current_trade_data(symbol=None):
    """
        get last stock price.
        :param symbol: str, Instrument symbol e.g.: 'ACI' or 'aci'
        :return: dataframe
    """
    r = requests.get(vs.DSE_LSP_URL)
    soup = BeautifulSoup(r.text, 'html.parser')
    quotes=[] # a list to store quotes 
    table = soup.find('table') 
    for row in table.find_all('tr')[1:]:
        cols = row.find_all('td')
        quotes.append({'symbol' : cols[1].text.strip().replace(",", ""), 
                        'ltp' : cols[2].text.strip().replace(",", ""), 
                        'high' : cols[3].text.strip().replace(",", ""), 
                        'low' : cols[4].text.strip().replace(",", ""), 
                        'close' : cols[5].text.strip().replace(",", ""), 
                        'ycp' : cols[6].text.strip().replace(",", ""), 
                        'change' : cols[7].text.strip().replace("--", "0"), 
                        'trade' : cols[8].text.strip().replace(",", ""), 
                        'value' : cols[9].text.strip().replace(",", ""),
                        'volume' : cols[10].text.strip().replace(",", "")
                        })
    df = pd.DataFrame(quotes)
    if symbol:
        df = df.loc[df.symbol==symbol.upper()]
        return df
    else:
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
        quotes.append({'symbol' : cols[1].text.strip().replace(",", "")})
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

    for row in table.find_all('tr')[1:]:
        cols = row.find_all('td')
        quotes.append({'date' : cols[1].text.strip().replace(",", ""), 
                        'symbol' : cols[2].text.strip().replace(",", ""), 
                        'ltp' : cols[3].text.strip().replace(",", ""), 
                        'high' : cols[4].text.strip().replace(",", ""), 
                        'low' : cols[5].text.strip().replace(",", ""), 
                        'open' : cols[6].text.strip().replace(",", ""), 
                        'close' : cols[7].text.strip().replace(",", ""), 
                        'ycp' : cols[8].text.strip().replace(",", ""), 
                        'trade' : cols[9].text.strip().replace(",", ""),
                        'value' : cols[10].text.strip().replace(",", ""),
                        'volume' : cols[11].text.strip().replace(",", "")
                    })
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
    quotes=[] # a list to store quotes 


    table = soup.find('table', attrs={'cellspacing' : '1'})

    for row in table.find_all('tr')[1:]:
        cols = row.find_all('td')
        quotes.append({'date' : cols[1].text.strip().replace(",", ""), 
                        'open' : cols[6].text.strip().replace(",", ""), 
                        'high' : cols[4].text.strip().replace(",", ""), 
                        'close' : cols[7].text.strip().replace(",", ""), 
                        'low' : cols[5].text.strip().replace(",", ""), 
                        'volume' : cols[11].text.strip().replace(",", "")
                        })
    df = pd.DataFrame(quotes)
    return df

def get_close_price_data(start=None, end=None, code='All Instrument'):
    """
        get stock close price.
        :param start: str, Start date e.g.: '2020-03-01'
        :param end: str, End date e.g.: '2020-03-02'
        :param code: str, Instrument symbol e.g.: 'ACI'
        :return: dataframe
    """
    # data to be sent to post request
    data = {'ClosePDate': start,
            'ClosePDate1': end,
            'Symbol': code,
            'ViewClosePArchive': 'View Close Price'}

    r = requests.post(url = vs.DSE_CLOSE_PRICE_URL, data = data) 

    soup = BeautifulSoup(r.text, 'html.parser')

    # columns: date, open, high, close, low, volume
    quotes=[] # a list to store quotes 


    table = soup.find('table', attrs={'bgcolor' : '#808000'})

    for row in table.find_all('tr')[1:]:
        cols = row.find_all('td')
        quotes.append({'date' : cols[1].text.strip().replace(",", ""), 
                        'symbol' : cols[2].text.strip().replace(",", ""), 
                        'close' : cols[3].text.strip().replace(",", ""), 
                        'ycp' : cols[4].text.strip().replace(",", "")
                        })
    df = pd.DataFrame(quotes)
    return df