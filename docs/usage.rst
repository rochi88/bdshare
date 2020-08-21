========
Usage
========

Get DSE last or current trading data
====================================
.. code-block:: python
  from bdshare import get_current_trade_data

  df = get_current_trade_data()
  print(df.to_string())

.. code-block:: python
  from bdshare import get_current_trade_data

  df = get_current_trade_data('GP') # get specific instrument data
  print(df.to_string())


Get historical data
===================
.. code-block:: python
  from bdshare import get_hist_data

  df = get_hist_data('2020-03-01','2020-03-02') # get all instrument data
  print(df.to_string())


.. code-block:: python
  from bdshare import get_hist_data

  df = get_hist_data('2020-03-01','2020-03-02','ACI') # get specific instrument data
  print(df.to_string())


Get OHLCV historical data
=========================
.. code-block:: python
  from bdshare import get_basic_hist_data

  df = get_basic_hist_data('2020-03-01','2020-03-02') # get all instrument data
  print(df.to_string())


.. code-block:: python
  from bdshare import get_basic_hist_data

  df = get_basic_hist_data('2020-03-01','2020-03-02','GP') # get specific instrument data
  print(df.to_string())


Get DSE Index data
==================
.. code-block:: python
  from bdshare import get_market_inf_more_data

  df = get_market_inf_more_data('2020-03-01','2020-03-02') # get all instrument data
  print(df.to_string())


Get CSE last or current trading data
====================================
.. code-block:: python
  from bdshare import get_cse_current_trade_data

  df = get_cse_current_trade_data() # get all instrument data
  print(df.to_string())

.. code-block:: python
  from bdshare import get_cse_current_trade_data

  df = get_cse_current_trade_data('GP') # get specific instrument data
  print(df.to_string())


