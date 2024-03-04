import time
import requests
from bs4 import BeautifulSoup
import pandas as pd
from bdshare.util import vars as vs


def get_current_trade_data(symbol=None, retry_count=1, pause=0.001):
    """
        get last stock price.
        :param symbol: str, Instrument symbol e.g.: 'ACI' or 'aci'
        :return: dataframecd 
    """

    for _ in range(retry_count):
        time.sleep(pause)
        try:
            r = requests.get(vs.DSE_URL+vs.DSE_LSP_URL)
            if r.status_code != 200:
                r = requests.get(vs.DSE_ALT_URL+vs.DSE_LSP_URL)
        except Exception as e:
            print(e)
        else:
            soup = BeautifulSoup(r.content, 'html5lib')
            quotes = []  # a list to store quotes
            table = soup.find('table', attrs={
                                'class': 'table table-bordered background-white shares-table fixedHeader'})

            # print(table)
            for row in table.find_all('tr')[1:]:
                cols = row.find_all('td')
                quotes.append({'symbol': cols[1].text.strip().replace(",", ""),
                       'ltp': cols[2].text.strip().replace(",", ""),
                       'high': cols[3].text.strip().replace(",", ""),
                       'low': cols[4].text.strip().replace(",", ""),
                       'close': cols[5].text.strip().replace(",", ""),
                       'ycp': cols[6].text.strip().replace(",", ""),
                       'change': cols[7].text.strip().replace("--", "0"),
                       'trade': cols[8].text.strip().replace(",", ""),
                       'value': cols[9].text.strip().replace(",", ""),
                       'volume': cols[10].text.strip().replace(",", "")
                       })
            df = pd.DataFrame(quotes)
            if symbol:
                df = df.loc[df.symbol == symbol.upper()]
                return df
            else:
                return df


def get_dsex_data(symbol=None, retry_count=1, pause=0.001):
    """
        get dseX share price.
        :param symbol: str, Instrument symbol e.g.: 'ACI' or 'aci'
        :return: dataframe
    """

    for _ in range(retry_count):
        time.sleep(pause)
        try:
            r = requests.get(vs.DSE_URL+vs.DSEX_INDEX_VALUE)
            if r.status_code != 200:
                r = requests.get(vs.DSE_ALT_URL+vs.DSEX_INDEX_VALUE)
        except Exception as e:
            print(e)
        else:
            soup = BeautifulSoup(r.content, 'html5lib')
            quotes = []  # a list to store quotes
            table = soup.find('table', attrs={
                                'class': 'table table-bordered background-white shares-table'})

            # print(table)
            for row in table.find_all('tr')[1:]:
                cols = row.find_all('td')
                quotes.append({'symbol': cols[1].text.strip().replace(",", ""),
                       'ltp': cols[2].text.strip().replace(",", ""),
                       'high': cols[3].text.strip().replace(",", ""),
                       'low': cols[4].text.strip().replace(",", ""),
                       'close': cols[5].text.strip().replace(",", ""),
                       'ycp': cols[6].text.strip().replace(",", ""),
                       'change': cols[7].text.strip().replace("--", "0"),
                       'trade': cols[8].text.strip().replace(",", ""),
                       'value': cols[9].text.strip().replace(",", ""),
                       'volume': cols[10].text.strip().replace(",", "")
                       })
            df = pd.DataFrame(quotes)
            if symbol:
                df = df.loc[df.symbol == symbol.upper()]
                return df
            else:
                return df


def get_current_trading_code():
    """
        get last stock codes.
        :return: dataframe
    """
    try:
        r = requests.get(vs.DSE_URL+vs.DSE_LSP_URL)
        if r.status_code != 200:
            r = requests.get(vs.DSE_ALT_URL+vs.DSE_LSP_URL)
    except Exception as e:
            print(e)
    #soup = BeautifulSoup(r.text, 'html.parser')
    soup = BeautifulSoup(r.content, 'html5lib')
    quotes = []  # a list to store quotes
    table = soup.find('table', attrs={
                                'class': 'table table-bordered background-white shares-table fixedHeader'})
    for row in table.find_all('tr')[1:]:
        cols = row.find_all('td')
        quotes.append({'symbol': cols[1].text.strip().replace(",", "")})
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
    data = {'startDate': start,
            'endDate': end,
            'inst': code,
            'archive': 'data'}
    try:
        r = requests.get(url=vs.DSE_URL+vs.DSE_DEA_URL, params=data)
        if r.status_code != 200:
            r = requests.get(url=vs.DSE_ALT_URL+vs.DSE_DEA_URL, params=data)
    except Exception as e:
            print(e)

    #soup = BeautifulSoup(r.text, 'html.parser')
    soup = BeautifulSoup(r.content, 'html5lib')

    quotes = []  # a list to store quotes

    table = soup.find('table', attrs={
                      'class': 'table table-bordered background-white shares-table fixedHeader'})
    for row in table.find_all('tr')[1:]:
        cols = row.find_all('td')
        quotes.append({'date': cols[1].text.strip().replace(",", ""),
                       'symbol': cols[2].text.strip().replace(",", ""),
                       'ltp': cols[3].text.strip().replace(",", ""),
                       'high': cols[4].text.strip().replace(",", ""),
                       'low': cols[5].text.strip().replace(",", ""),
                       'open': cols[6].text.strip().replace(",", ""),
                       'close': cols[7].text.strip().replace(",", ""),
                       'ycp': cols[8].text.strip().replace(",", ""),
                       'trade': cols[9].text.strip().replace(",", ""),
                       'value': cols[10].text.strip().replace(",", ""),
                       'volume': cols[11].text.strip().replace(",", "")
                       })
    df = pd.DataFrame(quotes)
    if 'date' in df.columns:
        df = df.set_index('date')
        df = df.sort_index(ascending=False)
    else:
        print('No data found')
    return df


def get_basic_hist_data(start=None, end=None, code='All Instrument', index=None, retry_count=1, pause=0.001):
    """
        get historical stock price.
        :param start: str, Start date e.g.: '2020-03-01'
        :param end: str, End date e.g.: '2020-03-02'
        :param code: str, Instrument symbol e.g.: 'ACI'
        :param retry_count : int, e.g.: 3
        :param pause : int, e.g.: 0
        :return: dataframe
    """
    # data to be sent to post request
    data = {'startDate': start,
            'endDate': end,
            'inst': code,
            'archive': 'data'}

    for _ in range(retry_count):
        time.sleep(pause)
        try:
            r = requests.get(url=vs.DSE_URL+vs.DSE_DEA_URL, params=data)
            if r.status_code != 200:
                r = requests.get(url=vs.DSE_ALT_URL+vs.DSE_DEA_URL, params=data)
        except Exception as e:
            print(e)
        else:
            #soup = BeautifulSoup(r.text, 'html.parser')
            soup = BeautifulSoup(r.content, 'html5lib')

            # columns: date, open, high, close, low, volume
            quotes = []  # a list to store quotes

            table = soup.find('table', attrs={
                              'class': 'table table-bordered background-white shares-table fixedHeader'})

            for row in table.find_all('tr')[1:]:
                cols = row.find_all('td')
                quotes.append({'date': cols[1].text.strip().replace(",", ""),
                               'open': float(cols[6].text.strip().replace(",", "")),
                               'high': float(cols[4].text.strip().replace(",", "")),
                               'low': float(cols[5].text.strip().replace(",", "")),
                               'close': float(cols[7].text.strip().replace(",", "")),
                               'volume': int(cols[11].text.strip().replace(",", ""))
                               })
            df = pd.DataFrame(quotes)
            if 'date' in df.columns:
                if (index == 'date'):
                    df = df.set_index('date')
                    df = df.sort_index(ascending=True)
                df = df.sort_index(ascending=True)
            else:
                print('No data found')
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
    data = {'startDate': start,
            'endDate': end,
            'inst': code,
            'archive': 'data'}
    try:
        r = requests.get(url=vs.DSE_URL+vs.DSE_CLOSE_PRICE_URL, params=data)
        if r.status_code != 200:
            r = requests.get(url=vs.DSE_ALT_URL+vs.DSE_CLOSE_PRICE_URL, params=data)
    except Exception as e:
        print(e)
    else:
        soup = BeautifulSoup(r.content, 'html5lib')

        # columns: date, open, high, close, low, volume
        quotes = []  # a list to store quotes

        table = soup.find(
            'table', attrs={'class': 'table table-bordered background-white'})

        for row in table.find_all('tr')[1:]:
            cols = row.find_all('td')
            quotes.append({'date': cols[1].text.strip().replace(",", ""),
                        'symbol': cols[2].text.strip().replace(",", ""),
                        'close': cols[3].text.strip().replace(",", ""),
                        'ycp': cols[4].text.strip().replace(",", "")
                        })
        df = pd.DataFrame(quotes)
        if 'date' in df.columns:
            df = df.set_index('date')
            df = df.sort_index(ascending=False)
        else:
            print('No data found')
        return df


def get_last_trade_price_data():
    df = pd.read_fwf('https://dsebd.org/datafile/quotes.txt', sep='\t', skiprows=4)
    return df