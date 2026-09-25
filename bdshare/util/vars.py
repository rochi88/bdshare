# -*- coding:utf-8 -*-
import os

# Current DSE site: a Next.js front-end backed by a JSON API. The legacy .php
# pages return 404 here, so it is scraped through the API endpoints below.
# Tried first.
DSE_URL = "https://dsebd.org/"
DSE_ALT_URL = "https://dse.com.bd/"

# Legacy DSE site: server-rendered HTML tables. Used as a fallback whenever
# dsebd.org fails.
DSE_LEGACY_URL = "https://old.dsebd.org/"
DSE_LEGACY_ALT_URL = "https://old.dse.com.bd/"

# Which site to scrape: "auto" (dsebd.org first, then legacy), "new" or "legacy".
# Read at call time, so it can also be changed at runtime via this module.
DSE_SOURCE = os.environ.get("BDSHARE_SOURCE", "auto").strip().lower()

DSE_LSP_URL = "latest_share_price_scroll_l.php"
DSE_DEA_URL = "day_end_archive.php"
DSE_AGM_URL = "Company_AGM.htm"
DSE_LPE_URL = "latest_PE.php"
DSE_NEWS_URL = "old_news.php"
DSE_CLOSE_PRICE_URL = "dse_close_price_archive.php"
DSE_COMPANY_LIST_URL = "company_listing.php"
DSE_COMPANY_INFO_URL = "displayCompany.php"

DSE_MARKET_INFO_URL = "recent_market_information.php"
DSE_MARKET_INFO_MORE_URL = "recent_market_information_more.php"
DSE_MARKET_DEPTH_URL = "ajax/load-instrument.php"
DSE_MARKET_DEPTH_REFERER_URL = "mkt_depth_3.php"
DSE_MARKET_SUMMARY_URL = "market_summary.php"

DSEX_INDEX_VALUE = "dseX_share.php"

DSE_TOP_TEN_GAINERS_URL = "top_ten_gainer.php"
DSE_TOP_TWENTY_SHARES_URL = "top_20_share.php"

# dsebd.org JSON API endpoints (relative to DSE_URL)
DSE_API_PRICES = "api/live/prices"
DSE_API_MARKET = "api/live/market"
DSE_API_DEPTH = "api/live/depth"
DSE_API_INDEX_CONSTITUENTS = "api/live/index-constituents"
DSE_API_DAY_END = "api/live/data-archive/day-end"
DSE_API_DAY_END_INSTRUMENTS = "api/live/data-archive/instruments"
DSE_API_RECENT_MARKET_INFO = "api/live/recent-market-info"
DSE_API_NEWS = "api/live/news"
DSE_NEW_PE_URL = "pe"
