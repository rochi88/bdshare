# from numpy import empty
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
        r = requests.get(vs.DSE_URL + vs.DSE_AGM_URL)
    except Exception as e:
        print(e)
    # soup = BeautifulSoup(r.text, 'html.parser')
    soup = BeautifulSoup(r.content, "html5lib")
    news = []  # a list to store quotes

    table = soup.find("table")

    for row in table.find_all("tr")[4:-6]:
        cols = row.find_all("td")
        news.append(
            {
                "company": cols[0].text.strip(),
                "yearEnd": cols[1].text.strip(),
                "dividend": cols[2].text.strip(),
                "agmData": cols[3].text.strip(),
                "recordDate": cols[4].text.strip(),
                "vanue": cols[5].text.strip(),
                "time": cols[6].text.strip(),
            }
        )
    df = pd.DataFrame(news)
    return df


def get_all_news(start=None, end=None, code=None):
    """
    get dse news.
    :param start: str, Start date e.g.: '2020-03-01'
    :param end: str, End date e.g.: '2020-03-02'
    :param code: str, Instrument symbol e.g.: 'ACI'
    :return: dataframe
    """
    # Handle backward compatibility - if only one parameter is provided, treat it as code
    if start is not None and end is None and code is None:
        # Backward compatibility: get_all_news(code) -> get_all_news(start=None, end=None, code=start)
        code = start
        start = None

    # data to be sent to post request
    data = {"inst": code, "criteria": 3, "archive": "news"}

    # Add date parameters if provided
    if start:
        data["startDate"] = start
    if end:
        data["endDate"] = end

    try:
        r = requests.post(url=vs.DSE_URL + vs.DSE_NEWS_URL, params=data)
        if r.status_code != 200:
            r = requests.post(url=vs.DSE_ALT_URL + vs.DSE_NEWS_URL, params=data)
    except Exception as e:
        print(e)
        return pd.DataFrame()

    # soup = BeautifulSoup(r.text, 'html.parser')
    soup = BeautifulSoup(r.content, "html5lib")

    # columns: Trading Code, News, Post Date
    news = []  # a list to store quotes

    table = soup.find("table", attrs={"class": "table-news"})

    if table is None:
        # Try alternative table selectors
        table = soup.find("table")
        if table is None:
            return pd.DataFrame()

    for row in table.find_all("tr"):
        heads = row.find_all("th")
        cols = row.find_all("td")
        if cols and heads:
            if len(heads) > 0 and heads[0].text.strip() == "News Title:":
                news.append({"News Title": cols[0].text.strip()})
            elif len(heads) > 0 and heads[0].text.strip() == "News:":
                news.append({"News": cols[0].text.strip()})
            elif len(heads) > 0 and heads[0].text.strip() == "Post Date:":
                news.append({"Post Date": cols[0].text.strip()})

    df = pd.DataFrame(news)
    return df
