import time
import requests
from bs4 import BeautifulSoup
import pandas as pd
from bdshare.util import vars as vs


def get_market_inf(retry_count=3, pause=0.001):
    """
    get company information.
    :return: dataframe
    """
    for _ in range(retry_count):
        time.sleep(pause)
        try:
            r = requests.get(vs.DSE_URL + vs.DSE_MARKET_INF_URL)
            if r.status_code != 200:
                r = requests.get(vs.DSE_ALT_URL + vs.DSE_MARKET_INF_URL)
        except Exception as e:
            print(e)
            continue
        else:
            soup = BeautifulSoup(r.text, "html.parser")
            quotes = []  # a list to store quotes

            table = soup.find(
                "table",
                attrs={
                    "class": "table table-bordered background-white text-center",
                    "_id": "data-table",
                },
            )

            if table is None:
                # Try alternative selectors
                table = soup.find(
                    "table",
                    attrs={
                        "class": "table table-bordered background-white text-center"
                    },
                )
                if table is None:
                    table = soup.find("table")

            if table is None:
                print("No table found on market info page")
                return pd.DataFrame()

            rows = table.find_all("tr")
            for row in rows[1:]:  # Skip header row
                cols = row.find_all("td")
                if len(cols) >= 9:  # Ensure we have enough columns
                    try:
                        quotes.append(
                            {
                                "Date": cols[0].text.strip().replace(",", ""),
                                "Total Trade": cols[1].text.strip().replace(",", ""),
                                "Total Volume": cols[2].text.strip().replace(",", ""),
                                "Total Value (mn)": cols[3]
                                .text.strip()
                                .replace(",", ""),
                                "Total Market Cap. (mn)": cols[4]
                                .text.strip()
                                .replace(",", ""),
                                "DSEX Index": cols[5].text.strip().replace(",", ""),
                                "DSES Index": cols[6].text.strip().replace(",", ""),
                                "DS30 Index": cols[7].text.strip().replace(",", ""),
                                "DGEN Index": cols[8].text.strip().replace(",", ""),
                            }
                        )
                    except (IndexError, AttributeError) as e:
                        print(f"Error parsing row: {e}")
                        continue

            if quotes:
                df = pd.DataFrame(quotes)
                return df

    return pd.DataFrame()


def get_company_inf(symbol=None, retry_count=3, pause=0.001):
    """
    get stock market information.
    :param symbol: str, Instrument symbol e.g.: 'ACI' or 'aci'
    :return: dataframe
    """
    data = {"name": symbol}

    for _ in range(retry_count):
        time.sleep(pause)
        try:
            r = requests.get(vs.DSE_URL + vs.DSE_COMPANY_INF_URL, params=data)
            if r.status_code != 200:
                r = requests.get(vs.DSE_ALT_URL + vs.DSE_COMPANY_INF_URL, params=data)
        except Exception as e:
            print(e)
        else:
            tables = pd.read_html(r.content)
            return tables[400:]


def get_latest_pe(retry_count=3, pause=0.001):
    """
    get last stock P/E.
    :return: dataframe
    """
    for _ in range(retry_count):
        time.sleep(pause)
        try:
            r = requests.get(vs.DSE_URL + vs.DSE_LPE_URL)
            if r.status_code != 200:
                r = requests.get(vs.DSE_ALT_URL + vs.DSE_LPE_URL)
        except Exception as e:
            print(e)
            continue
        else:
            if r.status_code == 502:
                print(
                    "DSE server returned 502 Bad Gateway - server issue, not code issue"
                )
                return pd.DataFrame()

            soup = BeautifulSoup(r.content, "html5lib")

            quotes = []  # a list to store quotes
            table = soup.find(
                "table",
                attrs={
                    "class": "table table-bordered background-white shares-table fixedHeader"
                },
            )

            if table is None:
                # Try alternative selectors
                table = soup.find(
                    "table",
                    attrs={
                        "class": "table table-bordered background-white shares-table"
                    },
                )
                if table is None:
                    table = soup.find("table")

            if table is None:
                print("No table found on P/E page")
                return pd.DataFrame()

            rows = table.find_all("tr")
            for row in rows[1:]:  # Skip header row
                cols = row.find_all("td")
                if len(cols) >= 10:  # Ensure we have enough columns
                    try:
                        quotes.append(
                            (
                                cols[1].text.strip().replace(",", ""),
                                cols[2].text.strip().replace(",", ""),
                                cols[3].text.strip().replace(",", ""),
                                cols[4].text.strip().replace(",", ""),
                                cols[5].text.strip().replace(",", ""),
                                cols[6].text.strip().replace(",", ""),
                                cols[7].text.strip().replace(",", ""),
                                cols[8].text.strip().replace(",", ""),
                                cols[9].text.strip().replace(",", ""),
                            )
                        )
                    except (IndexError, AttributeError) as e:
                        print(f"Error parsing P/E row: {e}")
                        continue

            if quotes:
                df = pd.DataFrame(quotes)
                return df

    return pd.DataFrame()


def get_market_inf_more_data(
    start=None, end=None, index=None, retry_count=3, pause=0.001
):
    """
    get historical stock price.
    :param start: str, Start date e.g.: '2020-03-01'
    :param end: str, End date e.g.: '2020-03-02'
    :param retry_count : int, e.g.: 3
    :param pause : int, e.g.: 0
    :return: dataframe
    """
    # data to be sent to post request
    data = {
        "startDate": start,
        "endDate": end,
        "searchRecentMarket": "Search Recent Market",
    }

    for _ in range(retry_count):
        time.sleep(pause)
        try:
            r = requests.post(url=vs.DSE_URL + vs.DSE_MARKET_INF_MORE_URL, data=data)
            if r.status_code != 200:
                r = requests.post(
                    url=vs.DSE_ALT_URL + vs.DSE_MARKET_INF_MORE_URL, data=data
                )
        except Exception as e:
            print(e)
            continue
        else:
            # soup = BeautifulSoup(r.text, 'html.parser')
            soup = BeautifulSoup(r.content, "html5lib")

            quotes = []  # a list to store quotes

            table = soup.find(
                "table",
                attrs={"class": "table table-bordered background-white text-center"},
            )

            if table is None:
                # Try alternative selectors
                table = soup.find(
                    "table", attrs={"class": "table table-bordered background-white"}
                )
                if table is None:
                    table = soup.find("table")

            if table is None:
                print("No table found on market info more data page")
                return pd.DataFrame()

            rows = table.find_all("tr")
            for row in rows[1:]:  # Skip header row
                cols = row.find_all("td")
                if len(cols) >= 9:  # Ensure we have enough columns
                    try:
                        quotes.append(
                            {
                                "Date": cols[0].text.strip().replace(",", ""),
                                "Total Trade": int(
                                    cols[1].text.strip().replace(",", "")
                                ),
                                "Total Volume": int(
                                    cols[2].text.strip().replace(",", "")
                                ),
                                "Total Value in Taka(mn)": float(
                                    cols[3].text.strip().replace(",", "")
                                ),
                                "Total Market Cap. in Taka(mn)": float(
                                    cols[4].text.strip().replace(",", "")
                                ),
                                "DSEX Index": float(
                                    cols[5].text.strip().replace(",", "")
                                ),
                                "DSES Index": float(
                                    cols[6].text.strip().replace(",", "")
                                ),
                                "DS30 Index": float(
                                    cols[7].text.strip().replace(",", "")
                                ),
                                "DGEN Index": float(
                                    cols[8].text.strip().replace("-", "0")
                                ),
                            }
                        )
                    except (IndexError, ValueError, AttributeError) as e:
                        print(f"Error parsing market data row: {e}")
                        continue

            if quotes:
                df = pd.DataFrame(quotes)
                if "Date" in df.columns:
                    if index == "date":
                        df = df.set_index("Date")
                        df = df.sort_index(ascending=True)
                    df = df.sort_index(ascending=True)
                return df
            else:
                print("No data found")
                return pd.DataFrame()

    return pd.DataFrame()


def get_market_depth_data(index, retry_count=3, pause=0.001):
    """
    get market depth data.
    :param index: str, e.g.: 'ACI'
    :param retry_count : int, e.g.: 3
    :param pause : int, e.g.: 0
    :return: dataframe
    """
    # data to be sent to post request
    data = {"inst": index}

    for _ in range(retry_count):
        time.sleep(pause)
        session = requests.Session()
        session.head(vs.DSE_URL + vs.DSE_MARKET_DEPTH_REFERER_URL)
        headers = {"X-Requested-With": "XMLHttpRequest"}
        session.headers.update(headers)
        try:
            r = session.post(url=vs.DSE_URL + vs.DSE_MARKET_DEPTH_URL, data=data)
        except Exception as e:
            print(e)
        else:
            soup = BeautifulSoup(r.content, "html5lib")

            result = []

            matrix = ["buy_price", "buy_volume", "sell_price", "sell_volume"]

            table = soup.find("table", attrs={"class": "table table-stripped"})

            for row in table.find_all("tr")[:1]:
                cols = row.find_all("td", valign="top")
                index = 0

                for mainrow in cols:
                    for row in mainrow.find_all("tr")[2:]:
                        newcols = row.find_all("td")
                        result.append(
                            {
                                matrix[index]: float(newcols[0].text.strip()),
                                matrix[index + 1]: int(newcols[1].text.strip()),
                            }
                        )
                    index = index + 2

            df = pd.DataFrame(result)
            return df
