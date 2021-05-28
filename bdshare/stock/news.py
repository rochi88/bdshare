from numpy import empty
import requests 
from bs4 import BeautifulSoup
import pandas as pd
from bdshare.util import vars as vs

def get_agm_news():
    """
        get stock agm declarations.
        :return: dataframe
    """
    try:
        r = requests.get(vs.DSE_URL+vs.DSE_AGM_URL)
    except Exception as e:
        print(e)
    #soup = BeautifulSoup(r.text, 'html.parser')
    soup = BeautifulSoup(r.content, 'html5lib')
    news=[] # a list to store quotes 

    table = soup.find('table') 

    for row in table.find_all('tr')[4:-6]:
        cols = row.find_all('td')
        news.append({'company': cols[0].text.strip(), 
                    'yearEnd': cols[1].text.strip(),
                    'dividend': cols[2].text.strip(),
                    'agmData': cols[3].text.strip(),
                    'recordDate': cols[4].text.strip(),
                    'vanue': cols[5].text.strip(),
                    'time': cols[6].text.strip()
                        })
    df = pd.DataFrame(news)
    return df


def get_all_news(code=None):
    """
        get dse news.
        :param start: str, Start date e.g.: '2020-03-01'
        :param end: str, End date e.g.: '2020-03-02'
        :param code: str, Instrument symbol e.g.: 'ACI'
        :return: dataframe
    """
    # data to be sent to post request
    data = {'inst': code,
            'criteria': 3,
            'archive': 'news'}
    try:
        r = requests.post(url = vs.DSE_URL+vs.DSE_NEWS_URL, params=data) 
    except Exception as e:
        print(e)

    #soup = BeautifulSoup(r.text, 'html.parser')
    soup = BeautifulSoup(r.content, 'html5lib')

    # columns: Trading Code, News, Post Date
    news=[] # a list to store quotes 


    table = soup.find('table', attrs={'class' : 'table-news'})

    for row in table.find_all('tr'):
        heads = row.find_all('th')
        cols = row.find_all('td')
        if cols:
            if heads[0].text.strip() == "News Title:":
                news.append({"News Title": cols[0].text.strip()})
            elif heads[0].text.strip() == "News:":
                news.append({"News": cols[0].text.strip()})
            elif heads[0].text.strip() == "Post Date:":
                news.append({"Post Date": cols[0].text.strip()})
    df = pd.DataFrame(news)
    return df