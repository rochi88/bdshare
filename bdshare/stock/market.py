import time
import requests
from bs4 import BeautifulSoup
import pandas as pd
from bdshare.util import vars as vs


def get_market_inf():
    """
        get stock market information.
        :return: dataframe
    """
    r = requests.get(vs.DSE_URL+vs.DSE_MARKET_INF_URL)
    soup = BeautifulSoup(r.text, 'html.parser')
    quotes = []  # a list to store quotes

    table = soup.find('table', attrs={'class': 'table table-bordered background-white text-center', '_id': 'data-table'})

    for row in table.find_all('tr')[1:]:
        cols = row.find_all('td')
        quotes.append({'Date': cols[0].text.strip().replace(",", ""),
                       'Total Trade': cols[1].text.strip().replace(",", ""),
                       'Total Volume': cols[2].text.strip().replace(",", ""),
                       'Total Value (mn)': cols[3].text.strip().replace(",", ""),
                       'Total Market Cap. (mn)': cols[4].text.strip().replace(",", ""),
                       'DSEX Index': cols[5].text.strip().replace(",", ""),
                       'DSES Index': cols[6].text.strip().replace(",", ""),
                       'DS30 Index': cols[7].text.strip().replace(",", ""),
                       'DGEN Index': cols[8].text.strip().replace(",", "")
        })
    df = pd.DataFrame(quotes)
    return df


def get_latest_pe():
    """
        get last stock P/E.
        :return: dataframe
    """
    r = requests.get(vs.DSE_URL+vs.DSE_LPE_URL)
    # soup = BeautifulSoup(r.text, 'html.parser')
    soup = BeautifulSoup(r.content, 'html5lib')

    quotes = []  # a list to store quotes
    table = soup.find('table', attrs={'class': 'table table-bordered background-white shares-table fixedHeader'})
    for row in table.find_all('tr')[1:]:
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


def get_market_inf_more_data(start=None, end=None, index=None, retry_count=3, pause=0.001):
    """
        get historical stock price.
        :param start: str, Start date e.g.: '2020-03-01'
        :param end: str, End date e.g.: '2020-03-02'
        :param retry_count : int, e.g.: 3
        :param pause : int, e.g.: 0
        :return: dataframe
    """
    # data to be sent to post request
    data = {'startDate': start,
            'endDate': end,
            'searchRecentMarket': 'Search Recent Market'}

    for _ in range(retry_count):
        time.sleep(pause)
        try:
            r = requests.post(
                url=vs.DSE_URL+vs.DSE_MARKET_INF_MORE_URL, data=data)
        except Exception as e:
            print(e)
        else:
            #soup = BeautifulSoup(r.text, 'html.parser')
            soup = BeautifulSoup(r.content, 'html5lib')

            quotes = []  # a list to store quotes

            table = soup.find('table', attrs={
                              'class': 'table table-bordered background-white text-center'})

            for row in table.find_all('tr')[1:]:
                cols = row.find_all('td')
                quotes.append({'Date': cols[0].text.strip().replace(",", ""),
                               'Total Trade': int(cols[1].text.strip().replace(",", "")),
                               'Total Volume': int(cols[2].text.strip().replace(",", "")),
                               'Total Value in Taka(mn)': float(cols[3].text.strip().replace(",", "")),
                               'Total Market Cap. in Taka(mn)': float(cols[4].text.strip().replace(",", "")),
                               'DSEX Index': float(cols[5].text.strip().replace(",", "")),
                               'DSES Index': float(cols[6].text.strip().replace(",", "")),
                               'DS30 Index': float(cols[7].text.strip().replace(",", "")),
                               'DGEN Index': float(cols[8].text.strip().replace("-", "0"))
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


def get_market_depth_data(index, retry_count=3, pause=0.001):
    """
        get market depth data.
        :param index: str, e.g.: 'ACI'
        :param retry_count : int, e.g.: 3
        :param pause : int, e.g.: 0
        :return: dataframe
    """
    # data to be sent to post request
    data = {'inst': index}

    for _ in range(retry_count):
        time.sleep(pause)
        session  = requests.Session()
        session.head(vs.DSE_URL+vs.DSE_MARKET_DEPTH_REFERER_URL)
        headers = {'X-Requested-With':'XMLHttpRequest'}
        session.headers.update(headers)
        try:
            r = session.post(
                url=vs.DSE_URL+vs.DSE_MARKET_DEPTH_URL, data=data)
        except Exception as e:
            print(e)
        else:
            soup = BeautifulSoup(r.content, 'html5lib')

            result = [] 

            matrix = ['buy_price', 'buy_volume', 'sell_price', 'sell_volume']

            table = soup.find('table', attrs={
                              'class': 'table table-stripped'})

            for row in table.find_all('tr')[:1]:
                cols = row.find_all('td', valign="top")
                index = 0

                for mainrow in cols:
                    for row in mainrow.find_all('tr')[2:]:
                        newcols = row.find_all('td')
                        result.append({matrix[index]:float(newcols[0].text.strip()),
                                    matrix[index+1]:int(newcols[1].text.strip())})
                    index = index+2

            df = pd.DataFrame(result)
            return df