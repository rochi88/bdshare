# Bdshare
A utility for crawling historical and Real-time Quotes data of dse data

## Quickstart

### Install Dshare

```
$ pip install bdshare
```

### Using for data crawing from dse

```python
from bdshare.trading import get_current_trade_data

df = get_current_trade_data()
print(df.to_string())
```