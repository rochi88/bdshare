=====
Usage
=====

This page covers all available functions in **bdshare** with complete examples.
For installation instructions, see :doc:`installation`.
For the full API specification, see :doc:`api`.

.. contents:: On This Page
   :local:
   :depth: 2

----

Dhaka Stock Exchange (DSE)
==========================

Live Trading Data
-----------------

Get current prices for all instruments or a specific symbol.

.. code-block:: python

    from bdshare import get_current_trade_data

    # All instruments
    df = get_current_trade_data()
    print(df.to_string())

.. code-block:: python

    from bdshare import get_current_trade_data

    # Single instrument (case-insensitive)
    df = get_current_trade_data('GP')
    print(df.to_string())

**Returned columns:**

+----------+-------+-------------------------------------------------+
| Column   | Type  | Description                                     |
+==========+=======+=================================================+
| symbol   | str   | Trading symbol                                  |
+----------+-------+-------------------------------------------------+
| ltp      | float | Last trade price                                |
+----------+-------+-------------------------------------------------+
| high     | float | Day high                                        |
+----------+-------+-------------------------------------------------+
| low      | float | Day low                                         |
+----------+-------+-------------------------------------------------+
| close    | float | Closing price                                   |
+----------+-------+-------------------------------------------------+
| ycp      | float | Yesterday's closing price                       |
+----------+-------+-------------------------------------------------+
| change   | float | Price change from ycp                           |
+----------+-------+-------------------------------------------------+
| trade    | int   | Number of trades                                |
+----------+-------+-------------------------------------------------+
| value    | float | Total traded value                              |
+----------+-------+-------------------------------------------------+
| volume   | int   | Total traded volume                             |
+----------+-------+-------------------------------------------------+


DSEX Index Data
---------------

Get live DSEX index entries.

.. code-block:: python

    from bdshare import get_dsex_data

    # All DSEX entries
    df = get_dsex_data()
    print(df.to_string())

.. code-block:: python

    from bdshare import get_dsex_data

    # Filter by symbol
    df = get_dsex_data('DSEX')
    print(df.to_string())


Trading Codes
-------------

Get the full list of currently tradeable symbols.

.. code-block:: python

    from bdshare import get_current_trading_code

    df = get_current_trading_code()
    print(df['symbol'].tolist())


Historical Data
---------------

Get full OHLCV and metadata for a date range.
Results are indexed by date, sorted newest-first.

.. code-block:: python

    from bdshare import get_hist_data

    # All instruments for a date range
    df = get_hist_data('2024-01-01', '2024-03-31')
    print(df.to_string())

.. code-block:: python

    from bdshare import get_hist_data

    # Specific instrument
    df = get_hist_data('2024-01-01', '2024-03-31', 'ACI')
    print(df.to_string())

**Returned columns:**

+----------+-------+-------------------------------------------------+
| Column   | Type  | Description                                     |
+==========+=======+=================================================+
| date     | str   | Index — trading date                            |
+----------+-------+-------------------------------------------------+
| symbol   | str   | Trading symbol                                  |
+----------+-------+-------------------------------------------------+
| ltp      | float | Last trade price                                |
+----------+-------+-------------------------------------------------+
| high     | float | Day high                                        |
+----------+-------+-------------------------------------------------+
| low      | float | Day low                                         |
+----------+-------+-------------------------------------------------+
| open     | float | Opening price                                   |
+----------+-------+-------------------------------------------------+
| close    | float | Closing price                                   |
+----------+-------+-------------------------------------------------+
| ycp      | float | Yesterday's closing price                       |
+----------+-------+-------------------------------------------------+
| trade    | int   | Number of trades                                |
+----------+-------+-------------------------------------------------+
| value    | float | Total traded value                              |
+----------+-------+-------------------------------------------------+
| volume   | int   | Total traded volume                             |
+----------+-------+-------------------------------------------------+

.. note::

   Deprecated alias: ``get_historical_data()`` still works but emits a
   ``DeprecationWarning``. Migrate to ``get_hist_data()``.


Simplified OHLCV Historical Data
---------------------------------

Returns only open, high, low, close, volume — sorted oldest-first.
This format is directly compatible with TA libraries such as ``ta``,
``pandas-ta``, and ``backtrader``.

.. code-block:: python

    from bdshare import get_basic_hist_data

    # All instruments
    df = get_basic_hist_data('2024-01-01', '2024-03-31')
    print(df.to_string())

.. code-block:: python

    from bdshare import get_basic_hist_data

    # Specific instrument
    df = get_basic_hist_data('2024-01-01', '2024-03-31', 'GP')
    print(df.to_string())

.. code-block:: python

    from bdshare import get_basic_hist_data
    import datetime as dt

    # Rolling 2-year window with date set as the DataFrame index
    end   = dt.date.today()
    start = end - dt.timedelta(days=2 * 365)
    df    = get_basic_hist_data(str(start), str(end), 'GP', index='date')
    print(df.to_string())

.. note::

   Deprecated alias: ``get_basic_historical_data()`` still works but emits a
   ``DeprecationWarning``. Migrate to ``get_basic_hist_data()``.


Close Price Data
----------------

Returns only closing price and prior close (ycp), indexed by date.

.. code-block:: python

    from bdshare import get_close_price_data

    df = get_close_price_data('2024-01-01', '2024-03-31', 'ACI')
    print(df.to_string())


Last Trade Price (Text File)
-----------------------------

Fetches the DSE fixed-width text file for the most recent session.

.. code-block:: python

    from bdshare import get_last_trade_price_data

    df = get_last_trade_price_data()
    print(df.to_string())


----

Market & Index Summary
=======================

Current Market Summary
-----------------------

Returns the last 30 days of overall market data including all DSE indices,
total volumes, and market capitalisation.

.. code-block:: python

    from bdshare import get_market_info

    df = get_market_info()
    print(df.to_string())

**Returned columns:** Date, Total Trade, Total Volume, Total Value (mn),
Total Market Cap. (mn), DSEX Index, DSES Index, DS30 Index, DGEN Index.


Historical Market Summary
--------------------------

Fetch extended market statistics between two dates via the DSE search form.

.. code-block:: python

    from bdshare import get_market_info_more_data

    df = get_market_info_more_data('2024-01-01', '2024-03-31')
    print(df.to_string())

.. code-block:: python

    from bdshare import get_market_info_more_data

    # Set date as the DataFrame index, sorted ascending
    df = get_market_info_more_data('2024-01-01', '2024-03-31', index='date')
    print(df.to_string())


Market Depth (Order Book)
--------------------------

Returns the live buy and sell order book for a symbol.

.. code-block:: python

    from bdshare import get_market_depth_data

    df = get_market_depth_data('ACI')
    print(df.to_string())

**Returned columns:** buy_price, buy_volume, sell_price, sell_volume.


P/E Ratios
----------

Get the latest price-to-earnings ratios for all listed companies.

.. code-block:: python

    from bdshare import get_latest_pe

    df = get_latest_pe()
    print(df.to_string())


Company Profile
---------------

Returns a list of DataFrames containing detailed company information
(financials, directors, shareholding, etc.).

.. code-block:: python

    from bdshare import get_company_info

    tables = get_company_info('GP')
    for t in tables:
        print(t.to_string())
        print()


Sector Performance
------------------

Get sector-wise performance across the market.

.. code-block:: python

    from bdshare import get_sector_performance

    df = get_sector_performance()
    print(df.to_string())


Top Gainers & Losers
---------------------

.. code-block:: python

    from bdshare import get_top_gainers_losers

    # Default: top 10
    df = get_top_gainers_losers()
    print(df.to_string())

.. code-block:: python

    from bdshare import get_top_gainers_losers

    # Custom limit
    df = get_top_gainers_losers(limit=20)
    print(df.to_string())


----

News & Announcements
====================

Unified News Dispatcher
------------------------

``get_news()`` is the recommended entry point. Use ``news_type`` to select
the category and ``code`` to filter by symbol.

+---------------+--------------------------------------+
| news_type     | Description                          |
+===============+======================================+
| ``'all'``     | All DSE news items (default)         |
+---------------+--------------------------------------+
| ``'agm'``     | AGM / dividend declarations          |
+---------------+--------------------------------------+
| ``'corporate'`` | Corporate announcements            |
+---------------+--------------------------------------+
| ``'psn'``     | Price-sensitive news                 |
+---------------+--------------------------------------+

.. code-block:: python

    from bdshare import get_news

    # All news
    df = get_news(news_type='all')
    print(df.to_string())

.. code-block:: python

    from bdshare import get_news

    # AGM declarations
    df = get_news(news_type='agm')
    print(df.to_string())

.. code-block:: python

    from bdshare import get_news

    # Corporate announcements for a specific symbol
    df = get_news(news_type='corporate', code='GP')
    print(df.to_string())

.. code-block:: python

    from bdshare import get_news

    # Price-sensitive news
    df = get_news(news_type='psn', code='ACI')
    print(df.to_string())


AGM News
--------

.. code-block:: python

    from bdshare import get_agm_news

    df = get_agm_news()
    print(df.to_string())

**Returned columns:** company, yearEnd, dividend, agmDate, recordDate, venue, time.


All News
--------

.. code-block:: python

    from bdshare import get_all_news

    # All news (no filter)
    df = get_all_news()
    print(df.to_string())

.. code-block:: python

    from bdshare import get_all_news

    # Filter by symbol
    df = get_all_news(code='BEXIMCO')
    print(df.to_string())

.. code-block:: python

    from bdshare import get_all_news

    # Filter by date range and symbol
    df = get_all_news('2024-01-01', '2024-03-31', 'GP')
    print(df.to_string())


Corporate Announcements
------------------------

.. code-block:: python

    from bdshare import get_corporate_announcements

    df = get_corporate_announcements()
    print(df.to_string())

.. code-block:: python

    from bdshare import get_corporate_announcements

    df = get_corporate_announcements(code='GP')
    print(df.to_string())


Price-Sensitive News
---------------------

.. code-block:: python

    from bdshare import get_price_sensitive_news

    df = get_price_sensitive_news()
    print(df.to_string())

.. code-block:: python

    from bdshare import get_price_sensitive_news

    df = get_price_sensitive_news(code='ACI')
    print(df.to_string())


----

Saving Data
===========

Save any DataFrame to CSV using the built-in ``Store`` helper.

.. code-block:: python

    from bdshare import get_basic_hist_data, Store
    import datetime as dt

    end   = dt.date.today()
    start = end - dt.timedelta(days=365)

    df = get_basic_hist_data(str(start), str(end), 'GP')
    Store(df).save()  # saved to current directory as CSV


----

OOP Client
==========

The ``BDShare`` class wraps all functions with automatic caching and
rate limiting (5 calls/second sliding window).

Initialisation
--------------

.. code-block:: python

    from bdshare import BDShare

    bd = BDShare()                     # caching on by default
    bd = BDShare(cache_enabled=False)  # disable caching
    bd = BDShare(api_key='your-key')   # premium API key (future use)

Context Manager
---------------

Use as a context manager to ensure the session and cache are cleaned up
automatically on exit:

.. code-block:: python

    from bdshare import BDShare

    with BDShare() as bd:
        df = bd.get_current_trades('GP')
        print(df.to_string())

Method Reference
----------------

All methods accept a ``use_cache`` keyword argument (default ``True``).
The table below shows each method with its cache TTL.

**Market methods**

.. code-block:: python

    bd.get_market_summary()            # DSEX/DSES/DS30 indices    — 1-min  TTL
    bd.get_company_profile('ACI')      # Company profile           — 1-hr   TTL
    bd.get_latest_pe_ratios()          # All P/E ratios            — 1-hr   TTL
    bd.get_top_movers(limit=10)        # Top gainers/losers        — 5-min  TTL
    bd.get_sector_performance()        # Sector breakdown          — 5-min  TTL

**Trading methods**

.. code-block:: python

    bd.get_current_trades()            # All live prices           — 30-sec TTL
    bd.get_current_trades('GP')        # Single symbol
    bd.get_dsex_index()                # DSEX index entries        — 1-min  TTL
    bd.get_trading_codes()             # All tradeable symbols     — 24-hr  TTL
    bd.get_historical_data(            # Historical OHLCV          — no TTL (opt-in)
        'GP',
        '2024-01-01',
        '2024-03-31',
        use_cache=True,
    )

**News methods**

.. code-block:: python

    bd.get_news(news_type='all')                      # All news   — 5-min TTL
    bd.get_news(news_type='corporate', code='GP')
    bd.get_news(news_type='psn')

**Utility methods**

.. code-block:: python

    bd.clear_cache()                   # Flush all cached responses
    bd.configure(proxy_url='http://proxy:8080')
    print(bd.version)                  # e.g. "2.0.0"


----

Error Handling
==============

All failures raise ``BDShareError``. Catch it specifically rather than
bare ``Exception`` so unexpected bugs are never silently swallowed.

.. code-block:: python

    from bdshare import get_hist_data, BDShareError

    try:
        df = get_hist_data('2024-01-01', '2024-03-31', 'INVALID')
    except BDShareError as e:
        print(f"DSE error: {e}")

Common causes of ``BDShareError``:

- Symbol not present in the response table
- DSE site returned a non-200 status after all retries
- Network timeout (default: 10 seconds per request)
- Page structure changed on the DSE website — please open an issue

.. warning::

   The library retries up to **3 times** with exponential back-off
   (0.2 s → 0.4 s → 0.8 s) before raising ``BDShareError``. Short-lived
   DSE outages are handled automatically.


----

Chittagong Stock Exchange (CSE)
================================

.. note::

   CSE support is currently in development. The functions below are
   **placeholders** — they will raise ``NotImplementedError`` until the
   CSE module is released. Track progress on
   `GitHub <https://github.com/rochi88/bdshare/issues>`_.

.. code-block:: python

    from bdshare import get_cse_current_trade_data

    # All CSE instruments
    df = get_cse_current_trade_data()
    print(df.to_string())

.. code-block:: python

    from bdshare import get_cse_current_trade_data

    # Specific CSE instrument
    df = get_cse_current_trade_data('GP')
    print(df.to_string())


----

Proxy Support
=============

Route all requests through a proxy server (useful in restricted networks):

.. code-block:: python

    from bdshare import BDShare

    with BDShare() as bd:
        bd.configure(proxy_url='http://your-proxy-server:8080')
        df = bd.get_current_trades()
        print(df.to_string())


----

Complete Example: Stock Screener
==================================

The following example fetches live data for all instruments and screens
for stocks with a positive change greater than 3 % and volume above
a threshold.

.. code-block:: python

    from bdshare import get_current_trade_data, BDShareError

    try:
        df = get_current_trade_data()
    except BDShareError as e:
        print(f"Failed to fetch data: {e}")
        raise SystemExit(1)

    # Numeric columns were already cast — no conversion needed
    screened = df[
        (df['change'] > 3.0) &
        (df['volume'] > 100_000)
    ].sort_values('change', ascending=False)

    print(screened[['symbol', 'ltp', 'change', 'volume']].to_string())


Complete Example: Portfolio P&L
================================

.. code-block:: python

    from bdshare import BDShare, BDShareError

    PORTFOLIO = {
        'GP':      {'qty': 100, 'cost': 450.50},
        'ACI':     {'qty':  50, 'cost': 225.75},
        'BEXIMCO': {'qty': 200, 'cost': 125.25},
    }

    with BDShare() as bd:
        total_cost = total_value = 0.0

        for symbol, pos in PORTFOLIO.items():
            try:
                row   = bd.get_current_trades(symbol).iloc[0]
                price = row['ltp']
                mv    = pos['qty'] * price
                cost  = pos['qty'] * pos['cost']
                pnl   = mv - cost

                print(f"{symbol:10s}  ltp={price:8.2f}  P&L={pnl:+10.2f}")
                total_cost  += cost
                total_value += mv

            except BDShareError as e:
                print(f"{symbol}: {e}")

        pct = (total_value / total_cost - 1) * 100
        print(f"\nTotal P&L: {total_value - total_cost:+.2f}  ({pct:+.2f}%)")