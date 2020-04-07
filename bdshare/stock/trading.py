import os
import requests 
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
from dshare.util import vars


def get_current_trade_data():
    #file_name = (datetime.now().strftime('%Y%m%d%H%M%S')+".csv")
    r = requests.get(DSE_LSP_URL)
    soup = BeautifulSoup(r.text, 'html.parser')
    quotes=[] # a list to store quotes 
    table = soup.find('table') 
    for row in table.find_all('tr'):
        cols = row.find_all('td')
        quotes.append((cols[1].text.strip(), cols[2].text.strip(), cols[3].text.strip(), cols[4].text.strip(), cols[5].text.strip(), cols[6].text.strip(), cols[7].text.strip(), cols[8].text.strip(), cols[9].text.strip(),cols[10].text.strip()))
        #print (cols[1].text.strip(), cols[2].text.strip(), cols[3].text.strip(), cols[4].text.strip(), cols[5].text.strip(), cols[6].text.strip(), cols[7].text.strip(), cols[8].text.strip(), cols[9].text.strip(),cols[10].text.strip())
    df = pd.DataFrame(quotes)
    #df.to_csv(file_name, header=0, encoding='utf-8',index=False)
    return df


def get_hist_data(code='All Instrument', start=None, end=None,retry_count=3,pause=0.001):
    # data to be sent to api 
    data = {'DayEndSumDate1': start,
            'DayEndSumDate2': end,
            'Symbol': code,
            'ViewDayEndArchive': 'View Day End Archive'}

    r = requests.post(url = DSE_DEA_URL, data = data) 

    soup = BeautifulSoup(r.text, 'html.parser')

    quotes=[] # a list to store quotes 


    table = soup.find('table', attrs={'cellspacing' : '1'})

    for row in table.find_all('tr'):
        cols = row.find_all('td')
        quotes.append((cols[1].text.strip(), cols[2].text.strip(), cols[3].text.strip(), cols[4].text.strip(), cols[5].text.strip(), cols[6].text.strip(), cols[7].text.strip(), cols[8].text.strip(), cols[9].text.strip(),cols[10].text.strip(),cols[11].text.strip()))
        #print (cols[1].text.strip(), cols[2].text.strip(), cols[3].text.strip(), cols[4].text.strip(), cols[5].text.strip(), cols[6].text.strip(), cols[7].text.strip(), cols[8].text.strip(), cols[9].text.strip(),cols[10].text.strip(),cols[11].text.strip())
    df = pd.DataFrame(quotes)
    return df