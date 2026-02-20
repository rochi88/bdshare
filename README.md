# bdshare

![StyleCI](https://github.styleci.io/repos/253465924/shield?branch=main)
[![Documentation Status](https://readthedocs.org/projects/bdshare/badge/?version=latest)](https://bdshare.readthedocs.io/en/latest/?badge=latest)
![PyPI](https://img.shields.io/pypi/v/bdshare)
![Python](https://img.shields.io/pypi/pyversions/bdshare)
![License](https://img.shields.io/github/license/rochi88/bdshare)

**bdshare** is a Python library for fetching live and historical market data from the Dhaka Stock Exchange (DSE). It handles scraping, retries, caching, and rate limiting so you can focus on your analysis.

---

## Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Core Concepts](#core-concepts)
- [Usage Guide](#usage-guide)
  - [Live Trading Data](#live-trading-data)
  - [Historical Data](#historical-data)
  - [Market & Index Data](#market--index-data)
  - [News & Announcements](#news--announcements)
  - [Saving to CSV](#saving-to-csv)
- [OOP Client (BDShare)](#oop-client-bdshare)
- [Error Handling](#error-handling)
- [API Reference](#api-reference)
- [Examples](#examples)
- [Contributing](#contributing)
- [Roadmap](#roadmap)
- [Disclaimer](#disclaimer)

---

## Installation

**Requirements:** Python 3.7+

```bash
pip install bdshare
```

Install from source (latest development version):

```bash
pip install -U git+https://github.com/rochi88/bdshare.git
```

Dependencies installed automatically: `pandas`, `requests`, `beautifulsoup4`, `lxml`

---

## Quick Start

```python
from bdshare import get_current_trade_data, get_hist_data

# Live prices for all instruments
df = get_current_trade_data()
print(df.head())

# Historical data for a specific symbol
df = get_hist_data('2024-01-01', '2024-01-31', 'GP')
print(df.head())
```

Or use the object-oriented client:

```python
from bdshare import BDShare

with BDShare() as bd:
    print(bd.get_market_summary())
    print(bd.get_current_trades('ACI'))
```

---

## Core Concepts

| Concept | Details |
|---|---|
| **Retries** | All network calls retry up to 3 times with exponential back-off |
| **Fallback URL** | Every request has a primary and an alternate DSE endpoint |
| **Caching** | The `BDShare` client caches responses automatically (configurable TTL) |
| **Rate limiting** | Built-in sliding-window limiter (5 calls/second) prevents being blocked |
| **Errors** | All failures raise `BDShareError` — never silent |

---

## Usage Guide

### Live Trading Data

```python
from bdshare import get_current_trade_data, get_dsex_data, get_current_trading_code

# All instruments — returns columns: symbol, ltp, high, low, close, ycp, change, trade, value, volume
df = get_current_trade_data()

# Single instrument (case-insensitive)
df = get_current_trade_data('GP')

# DSEX index entries
df = get_dsex_data()

# Just the list of tradeable symbols
codes = get_current_trading_code()
print(codes['symbol'].tolist())
```

### Historical Data

```python
from bdshare import get_hist_data, get_basic_hist_data, get_close_price_data
import datetime as dt

start = '2024-01-01'
end   = '2024-03-31'

# Full historical data (ltp, open, high, low, close, volume, trade, value…)
# Indexed by date, sorted newest-first
df = get_hist_data(start, end, 'ACI')

# Simplified OHLCV — sorted oldest-first, ready for TA libraries
df = get_basic_hist_data(start, end, 'ACI')

# Set date as index explicitly
df = get_basic_hist_data(start, end, 'ACI', index='date')

# Rolling 2-year window
end   = dt.date.today()
start = end - dt.timedelta(days=2 * 365)
df    = get_basic_hist_data(str(start), str(end), 'GP')

# Close prices only
df = get_close_price_data(start, end, 'ACI')
```

> **Column order note:** `get_basic_hist_data` intentionally returns OHLCV in standard order
> (`open`, `high`, `low`, `close`, `volume`) to be compatible with libraries like `ta`, `pandas-ta`, and `backtrader`.

### Market & Index Data

```python
from bdshare import (
    get_market_info,
    get_market_info_more_data,
    get_market_depth_data,
    get_latest_pe,
    get_sector_performance,
    get_top_gainers_losers,
    get_company_info,
)

# Last 30 days of market summary (DSEX, DSES, DS30, DGEN, volumes, market cap)
df = get_market_info()

# Historical market summary between two dates
df = get_market_info_more_data('2024-01-01', '2024-03-31')

# Order book (buy/sell depth) for a symbol
df = get_market_depth_data('ACI')

# P/E ratios for all listed companies
df = get_latest_pe()

# Sector-wise performance
df = get_sector_performance()

# Top 10 gainers and losers (adjust limit as needed)
df = get_top_gainers_losers(limit=10)

# Detailed company profile
tables = get_company_info('GP')
```

### News & Announcements

```python
from bdshare import get_news, get_agm_news, get_all_news

# Unified dispatcher — news_type: 'all' | 'agm' | 'corporate' | 'psn'
df = get_news(news_type='all')
df = get_news(news_type='agm')
df = get_news(news_type='corporate', code='GP')
df = get_news(news_type='psn', code='ACI')   # price-sensitive news

# Direct function calls
df = get_agm_news()                          # AGM / dividend declarations
df = get_all_news(code='BEXIMCO')            # All news for one symbol
df = get_all_news('2024-01-01', '2024-03-31', 'GP')  # Filtered by date + symbol
```

### Saving to CSV

```python
from bdshare import get_basic_hist_data, Store
import datetime as dt

end   = dt.date.today()
start = end - dt.timedelta(days=365)

df = get_basic_hist_data(str(start), str(end), 'GP')
Store(df).save()   # saves to current directory as a CSV
```

---

## OOP Client (BDShare)

The `BDShare` class wraps all functions with automatic caching and rate limiting.

```python
from bdshare import BDShare

bd = BDShare(cache_enabled=True)   # cache_enabled=True is the default
```

### Context manager (auto-cleans cache and session)

```python
with BDShare() as bd:
    data = bd.get_current_trades('GP')
```

### Market methods

```python
bd.get_market_summary()                    # DSEX/DSES/DS30 indices + stats  (1-min TTL)
bd.get_company_profile('ACI')             # Company profile                  (1-hr TTL)
bd.get_latest_pe_ratios()                 # All P/E ratios                   (1-hr TTL)
bd.get_top_movers(limit=10)               # Top gainers/losers               (5-min TTL)
bd.get_sector_performance()               # Sector breakdown                 (5-min TTL)
```

### Trading methods

```python
bd.get_current_trades()                   # All live prices                  (30-sec TTL)
bd.get_current_trades('GP')               # Single symbol
bd.get_dsex_index()                       # DSEX index entries               (1-min TTL)
bd.get_trading_codes()                    # All tradeable symbols            (24-hr TTL)
bd.get_historical_data('GP', '2024-01-01', '2024-03-31')    # OHLCV history
```

### News methods

```python
bd.get_news(news_type='all')              # All news                         (5-min TTL)
bd.get_news(news_type='corporate', code='GP')
bd.get_news(news_type='psn')             # Price-sensitive news
```

### Utility methods

```python
bd.clear_cache()                          # Flush all cached data
bd.configure(proxy_url='http://proxy:8080')
print(bd.version)                         # Package version string
```

---

## Error Handling

All failures raise `BDShareError`. Never catch bare `Exception` — you'll miss bugs.

```python
from bdshare import BDShare, BDShareError

bd = BDShare()

try:
    df = bd.get_historical_data('INVALID', '2024-01-01', '2024-01-31')
except BDShareError as e:
    print(f"DSE error: {e}")
    # safe fallback logic here
```

Common causes of `BDShareError`:
- Symbol not found in the response table
- DSE site returned a non-200 status after all retries
- Table structure changed on the DSE page (report as a bug)
- Network timeout

---

## API Reference

### Trading Functions

| Function | Parameters | Returns | Description |
|---|---|---|---|
| `get_current_trade_data(symbol?)` | `symbol: str` | DataFrame | Live prices (all or one symbol) |
| `get_dsex_data(symbol?)` | `symbol: str` | DataFrame | DSEX index entries |
| `get_current_trading_code()` | — | DataFrame | All tradeable symbols |
| `get_hist_data(start, end, code?)` | `str, str, str` | DataFrame | Full historical OHLCV |
| `get_basic_hist_data(start, end, code?, index?)` | `str, str, str, str` | DataFrame | Simplified OHLCV (TA-ready) |
| `get_close_price_data(start, end, code?)` | `str, str, str` | DataFrame | Close + prior close |
| `get_last_trade_price_data()` | — | DataFrame | Last trade from DSE text file |

### Market Functions

| Function | Parameters | Returns | Description |
|---|---|---|---|
| `get_market_info()` | — | DataFrame | 30-day market summary |
| `get_market_info_more_data(start, end)` | `str, str` | DataFrame | Historical market summary |
| `get_market_depth_data(symbol)` | `str` | DataFrame | Order book (buy/sell depth) |
| `get_latest_pe()` | — | DataFrame | P/E ratios for all companies |
| `get_company_info(symbol)` | `str` | list[DataFrame] | Detailed company tables |
| `get_sector_performance()` | — | DataFrame | Sector-wise performance |
| `get_top_gainers_losers(limit?)` | `int` (default 10) | DataFrame | Top movers |

### News Functions

| Function | Parameters | Returns | Description |
|---|---|---|---|
| `get_news(news_type?, code?)` | `str, str` | DataFrame | Unified news dispatcher |
| `get_agm_news()` | — | DataFrame | AGM / dividend declarations |
| `get_all_news(start?, end?, code?)` | `str, str, str` | DataFrame | All DSE news |
| `get_corporate_announcements(code?)` | `str` | DataFrame | Corporate actions |
| `get_price_sensitive_news(code?)` | `str` | DataFrame | Price-sensitive news |

### `get_news` `news_type` values

| Value | Equivalent direct function |
|---|---|
| `'all'` | `get_all_news()` |
| `'agm'` | `get_agm_news()` |
| `'corporate'` | `get_corporate_announcements()` |
| `'psn'` | `get_price_sensitive_news()` |

---

## Examples

### Stock performance summary

```python
import datetime as dt
from bdshare import BDShare, BDShareError

def summarize(symbol: str, days: int = 30) -> dict:
    end   = dt.date.today()
    start = end - dt.timedelta(days=days)

    with BDShare() as bd:
        try:
            df = bd.get_historical_data(symbol, str(start), str(end))
        except BDShareError as e:
            print(f"Could not fetch data: {e}")
            return {}

    return {
        'symbol':       symbol,
        'current':      df['close'].iloc[0],
        'period_high':  df['high'].max(),
        'period_low':   df['low'].min(),
        'avg_volume':   df['volume'].mean(),
        'change_pct':   (df['close'].iloc[0] - df['close'].iloc[-1])
                        / df['close'].iloc[-1] * 100,
    }

result = summarize('GP', days=30)
print(f"{result['symbol']}: {result['change_pct']:.2f}% over 30 days")
```

### Simple portfolio tracker

```python
from bdshare import BDShare, BDShareError

PORTFOLIO = {
    'GP':      {'qty': 100, 'cost': 450.50},
    'ACI':     {'qty':  50, 'cost': 225.75},
    'BEXIMCO': {'qty': 200, 'cost': 125.25},
}

with BDShare() as bd:
    total_cost = total_value = 0

    for symbol, pos in PORTFOLIO.items():
        try:
            row = bd.get_current_trades(symbol).iloc[0]
            price        = row['ltp']
            market_value = pos['qty'] * price
            cost         = pos['qty'] * pos['cost']
            pnl          = market_value - cost

            print(f"{symbol:10s}  price={price:8.2f}  P&L={pnl:+10.2f}")
            total_cost  += cost
            total_value += market_value

        except BDShareError as e:
            print(f"{symbol}: fetch error — {e}")

    print(f"\nPortfolio P&L: {total_value - total_cost:+.2f} "
          f"({(total_value/total_cost - 1)*100:+.2f}%)")
```

### Fetch and screen top gainers above 5 %

```python
from bdshare import get_top_gainers_losers

df = get_top_gainers_losers(limit=20)
big_movers = df[df['change'] > 5]
print(big_movers[['symbol', 'ltp', 'change']])
```

---

## Contributing

Contributions are welcome! To get started:

```bash
git clone https://github.com/rochi88/bdshare.git
cd bdshare
pip install -e ".[dev]"
pytest
```

Please open an issue before submitting a pull request for significant changes. See [CONTRIBUTING.md](CONTRIBUTING.md) for the full guide.

---

## Roadmap

- [ ] Chittagong Stock Exchange (CSE) support
- [ ] WebSocket streaming for real-time ticks
- [ ] Built-in technical indicators (`ta` integration)
- [ ] Portfolio management helpers
- [ ] Docker demo examples
- [x] Shared session with exponential back-off
- [x] `lxml`-based fast parsing
- [x] `BDShareError` for clean error handling
- [x] Unified `get_news()` dispatcher
- [x] Rate limiter and response caching

---

## Support

- **Docs:** [bdshare.readthedocs.io](https://bdshare.readthedocs.io/)
- **Bugs / Features:** [GitHub Issues](https://github.com/rochi88/bdshare/issues)
- **Discussion:** [GitHub Discussions](https://github.com/rochi88/bdshare/discussions)

---

## License

MIT — see [LICENSE](LICENSE) for details.

## Disclaimer

bdshare is intended for educational and research use. Always respect DSE's terms of service. The authors are not responsible for financial decisions made using this library.