# dshare
A utility for crawling historical and Real-time Quotes data of dse data

## Quickstart

### Install Dshare

```
$ pip install dshare
```

### Using for data crawing from dse

```python
from dshare.trading import get_current_trade_data

df = get_current_trade_data()
print(df.to_string())
```