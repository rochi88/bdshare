#Bdshare                                                             
---


[![Documentation Status](https://readthedocs.org/projects/bdshare/badge/?version=latest)](https://bdshare.readthedocs.io/en/latest/?badge=latest)
![PyPI](https://img.shields.io/pypi/v/bdshare)
![StyleCI](https://github.styleci.io/repos/253465924/shield?branch=master)


A utility for crawling historical and Real-time data from stock exchanges of Bangladesh. At present this utility can collect data from Dhaka stock exchange.

### <a name="contents"></a>Contents
- [Installation](#install)
- [Example Use](#usage)
- [List of functions](#functions)
- [Todo's and Road Map:](#roadmap)


## Quickstart

### <a name="install"></a>[Installation](#contents)

```sh
$ pip install bdshare
```
or upgrade
```sh
$ pip install -U bdshare
```

### <a name="usage"></a>[Example Use](#contents)

#### Get DSE last or current trading data
```python
from bdshare import get_current_trade_data

df = get_current_trade_data()
print(df.to_string())
```
```python
from bdshare import get_current_trade_data

df = get_current_trade_data('GP') # get specific instrument data
print(df.to_string())
```

#### Get historical data
```python
from bdshare import get_hist_data

df = get_hist_data('2022-03-01','2022-03-02') # get all instrument data
print(df.to_string())
```
or
```python
from bdshare import get_hist_data

df = get_hist_data('2022-03-01','2022-03-02','ACI') # get specific instrument data
print(df.to_string())
```

#### Get OHLCV historical data
```python
from bdshare import get_basic_hist_data

df = get_basic_hist_data('2022-03-01','2022-03-02') # get all instrument data
print(df.to_string())
```
or
```python
from bdshare import get_basic_hist_data

df = get_basic_hist_data('2022-03-01','2022-03-02','GP') # get specific instrument data
print(df.to_string())
```

#### Get DSE Index data
```python
from bdshare import get_market_inf

df = get_market_inf() # get last 30 days market data
print(df.to_string())
```

```python
from bdshare import get_market_inf_more_data

df = get_market_inf_more_data('2022-03-01','2022-03-02') # get historical market data
print(df.to_string())
```

#### Get DSE Market Depth data
```python
from bdshare import get_market_depth_data

df = get_market_depth_data('ACI') # get current buy and sell data
print(df.to_string())
```

#### Save data to csv file
```python
from bdshare import get_basic_hist_data, Store

df = get_basic_hist_data('2022-03-01','2022-03-02') # get all instrument data
Store(df).save()
```

### <a name="functions"></a> [List of functions](#contents)

#### Trading data
|Function|Params|Description|
|---|---|---|
|get_current_trade_data()|symbol:str|get last stock price|
|get_dsex_data()|symbol:str|get dseX share price|
|get_current_trading_code()||get last stock codes|
|get_hist_data()|start:str, end:str|get historical stock price|
|get_basic_hist_data()|start:str, end:str, code:str|get historical stock price|
|get_close_price_data()|start:str, end:str, code:str|get stock close price|
|get_last_trade_price_data()|||

#### Trading news
|Function|Params|Description|
|---|---|---|
|get_agm_news()||get stock agm declarations|
|get_all_news()|start:str, end:str, code:str|get dse news|

#### Market data
|Function|Params|Description|
|---|---|---|
|get_market_inf()||get stock market information|
|get_latest_pe()||get last stock P/E|
|get_market_inf_more_data()|start:str, end:str|get historical stock price|
|get_market_depth_data()|index:str|get_market_depth_data('ACI')|

### <a name="roadmap"></a> [TODO's and Road Map:](#contents)
 - [x] refine logic for parameters 
 - [x] Demo example;
 - [x] DSE daily data and historical data crawling
 - [x] DSE news,p/e crawling
 - [x] Add DSEX Index data support
 - [x] Create tests
 - [x] Store dat to csv
 - [x] DSE market depth data
 - [x] Add docker support in demo example


### Documentation

Complete documentation can be found at [Readthedocs](http://bdshare.readthedocs.io/en/latest/ "bdshare's readthedocs") .


## Contributing to this project

Anyone and everyone is welcome to contribute. Please take a moment to
review the [guidelines for contributing](CONTRIBUTING.md).

* [Bug reports](CONTRIBUTING.md#bugs)
* [Feature requests](CONTRIBUTING.md#features)
* [Pull requests](CONTRIBUTING.md#pull-requests)
