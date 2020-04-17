# Bdshare

[![Documentation Status](https://readthedocs.org/projects/bdshare/badge/?version=latest)](https://bdshare.readthedocs.io/en/latest/?badge=latest)

A utility for crawling historical and Real-time data from stock exchanges of Bangladesh. At preesent this utility can collect data from dhaka stock exchange only.

### <a name="contents"></a>Contents
- [Installation](#install)
- [Example Use](#usage)
- [TODO's and Road Map:](#roadmap)


## Quickstart

### <a name="install"></a>[Installation](#contents)

```sh
$ pip install bdshare
```

### <a name="usage"></a>[Example Use](#contents)

#### Get last or current trading data
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

df = get_hist_data('2020-03-01','2020-03-02') # get all instrument data
print(df.to_string())
```
or
```python
from bdshare import get_hist_data

df = get_hist_data('2020-03-01','2020-03-02','ACI') # get specific instrument data
print(df.to_string())
```

### <a name="roadmap"></a> [TODO's and Road Map:](#contents)
 - [x] refine logic for parameters 
 - [x] examples;
 - [x] DSE daily data and historical data crawling
 - [x] DSE news,p/e crawling
 - [ ] Add CSE support


### Documentation

Complete documentation can be found at [Readthedocs](http://bdshare.readthedocs.io/en/latest/ "bdshare's readthedocs") .


## Contributing to this project

Anyone and everyone is welcome to contribute. Please take a moment to
review the [guidelines for contributing](CONTRIBUTING.md).

* [Bug reports](CONTRIBUTING.md#bugs)
* [Feature requests](CONTRIBUTING.md#features)
* [Pull requests](CONTRIBUTING.md#pull-requests)