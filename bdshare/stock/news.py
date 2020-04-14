import os
import requests 
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
from bdshare.util import vars as vs

def get_agm_news():
    """
        get stock agm declarations.
        :return: dataframe
    """
    r = requests.get(vs.DSE_AGM_URL)
    soup = BeautifulSoup(r.text, 'html.parser')
    quotes=[] # a list to store quotes 
    table = soup.find('table') 
    for row in table.find_all('tr'):
        cols = row.find_all('td')
        quotes.append((cols[1].text.strip().replace(",", ""), cols[2].text.strip().replace(",", ""), cols[3].text.strip().replace(",", ""), cols[4].text.strip().replace(",", ""), cols[5].text.strip().replace(",", ""), cols[6].text.strip().replace(",", ""), cols[7].text.strip().replace("--", "0"), cols[8].text.strip().replace(",", ""), cols[9].text.strip().replace(",", ""),cols[10].text.strip().replace(",", "")))
    df = pd.DataFrame(quotes)
    return df


def get_latest_pe_news():
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
        quotes.append((cols[1].text.strip().replace(",", ""), cols[2].text.strip().replace(",", ""), cols[3].text.strip().replace(",", ""), cols[4].text.strip().replace(",", ""), cols[5].text.strip().replace(",", ""), cols[6].text.strip().replace(",", ""), cols[7].text.strip().replace("--", "0"), cols[8].text.strip().replace(",", ""), cols[9].text.strip().replace(",", ""),cols[10].text.strip().replace(",", "")))
    df = pd.DataFrame(quotes)
    return df


def get_all_news(start=None, end=None, code=None):
    """
        get dse news.
        :param start: str, Start date e.g.: '2020-03-01'
        :param end: str, End date e.g.: '2020-03-02'
        :param code: str, Instrument symbol e.g.: 'ACI'
        :return: dataframe
    """
    # data to be sent to post request
    data = {'NewsDate1': start,
            'NewsDate2': end,
            'Symbol': code,
            'ViewNews': 'View News'}

    r = requests.post(url = vs.DSE_NEWS_URL, data = data) 

    soup = BeautifulSoup(r.text, 'html.parser')

    # columns: Trading Code, News, Post Date
    news=[] # a list to store quotes 


    table = soup.find('table', attrs={'bgcolor' : '#E0E0E0'})

    for row in table.find_all('tr'):
        cols = row.find_all('td')
        news.append({'date' : cols[1].text.strip().replace(",", ""), 'open' : cols[6].text.strip().replace(",", ""), 'high' : cols[4].text.strip().replace(",", ""), 'close' : cols[7].text.strip().replace(",", ""), 'low' : cols[5].text.strip().replace(",", ""), 'volume' : cols[11].text.strip().replace(",", "")})
    df = pd.DataFrame(news)
    return df