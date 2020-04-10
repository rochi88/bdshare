========
Usage
========

#### Get last or current trading data
```python
from bdshare import get_current_trade_data

df = get_current_trade_data()
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
