# Change log

All notable changes to **bdshare** are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.1.6] - 2026-02-20

### Changed
- Updated `readthedocs` structure

## [1.1.5] - 2026-02-20

### Changed
- Renamed `get_hist_data()` → `get_historical_data()` (improved readability)
- Renamed `get_basic_hist_data()` → `get_basic_historical_data()` (improved readability)
- Renamed `get_market_inf()` → `get_market_info()` (improved readability)
- Renamed `get_market_inf_more_data()` → `get_market_info_more_data()` (improved readability)
- Renamed `get_company_inf()` → `get_company_info()` (improved readability)

### Deprecated
- `get_hist_data()` — still callable but emits `DeprecationWarning`; will be removed in 2.0.0
- `get_basic_hist_data()` — still callable but emits `DeprecationWarning`; will be removed in 2.0.0
- `get_market_inf()` — still callable but emits `DeprecationWarning`; will be removed in 2.0.0
- `get_market_inf_more_data()` — still callable but emits `DeprecationWarning`; will be removed in 2.0.0
- `get_company_inf()` — still callable but emits `DeprecationWarning`; will be removed in 2.0.0

### Added
- `BDShareError` custom exception — all network and scraping failures now raise this instead of silently printing and returning `None`
- Shared `requests.Session` (`_session`) across all modules — reuses TCP connections for significantly faster repeated calls
- Exponential back-off retry logic in `safe_get()` — pauses 0.2 s → 0.4 s → 0.8 s between attempts before raising `BDShareError`
- Fallback URL support in `safe_get()` — primary and alternate DSE endpoints tried within the same retry attempt
- `lxml`-based HTML parsing in `_fetch_table()` with `html.parser` fallback — replaces `html5lib` (~10× faster)
- `_safe_num()` helper — all scraped values now returned as typed numerics (`float`/`int`) instead of raw strings
- `_parse_trade_rows()` and `_filter_symbol()` internal helpers in `trading.py` — eliminate duplicated parsing logic between `get_current_trade_data()` and `get_dsex_data()`
- `get_news()` unified dispatcher — accepts `news_type` of `'all'`, `'agm'`, `'corporate'`, or `'psn'`
- `get_corporate_announcements()` and `get_price_sensitive_news()` — previously missing functions now fully implemented
- Column count guards (`len(cols) < N`) across all table parsers — malformed rows are skipped rather than raising `IndexError`
- Backward-compatibility aliases for all renamed functions with `DeprecationWarning`
- Type hints throughout all public functions
- Comprehensive docstrings with parameter and return documentation

### Fixed
- `get_agm_news()`: corrected field name typo `agmData` → `agmDate`
- `get_agm_news()`: corrected field name typo `vanue` → `venue`
- `get_market_depth_data()`: no longer creates a new `requests.Session` on every retry iteration
- `get_basic_hist_data()`: redundant double `sort_index()` call removed
- `get_hist_data()` and `get_close_price_data()`: no longer silently return `None` on empty results
- `RateLimiter` in `__init__.py`: switched from `time.time()` to `time.monotonic()` for reliable elapsed-time measurement

### Removed
- `html5lib` as the default parser — replaced by `lxml` with `html.parser` fallback
- Silent `print(e)` error handling — all error paths now raise `BDShareError`
- Dead `timeout` parameter from `BDShare.configure()` — it had no effect

## [1.1.4] - 2025-09-16

### Added

- Enhanced error handling and robustness across all functions
- Improved parameter handling for news functions
- Better file path resolution for utility functions
- Comprehensive fallback mechanisms for network issues

### Changed

- Fixed get_all_news() function to support date range parameters as documented
- Enhanced market info functions with better error handling
- Improved Store utility with proper file saving mechanism
- Fixed Tickers utility with correct file path resolution

### Fixed

- All major function issues identified in testing (18/18 functions now working)
- Parameter signature mismatches in news functions
- HTML parsing errors in market data functions
- File saving issues in Store utility
- Missing tickers.json file dependency

## [1.1.2] - 2024-12-31

### Added

- n/a

### Changed

- update tests

### Fixed

- n/a

## [1.1.1] - 2024-12-31

### Added

- n/a

### Changed

- update runner

### Fixed

- n/a

## [1.1.0] - 2024-12-31

### Added

- new function for getting company info

### Changed

- n/a

### Fixed

- n/a

## [1.0.4] - 2024-12-30

### Added

- n/a

### Changed

- changed lint

### Fixed

- fixed typo

## [1.0.3] - 2024-07-29

### Added

- n/a

### Changed

- n/a

### Fixed

- check fix for latest P/E url [#6]

## [1.0.2] - 2024-07-29

### Added

- n/a

### Changed

- n/a

### Fixed

- fixed latest P/E url [#6]

## [1.0.0] - 2024-03-04

### Added

- Updated docs

### Changed

- n/a

## [0.7.2] - 2024-03-04

### Added

- Updated docs

### Changed

- n/a

## [0.7.1] - 2024-03-04

### Added

- n/a

### Changed

- fixed market depth data api

## [0.7.0] - 2024-03-04

### Added

- n/a

### Changed

- n/a

## [0.6.0] - 2024-03-03

### Added

- n/a

### Changed

- n/a

## [0.5.1] - 2024-02-29

### Added

- n/a

### Changed

- n/a

## [0.5.0] - 2024-02-29

### Added

- fixed store datafrave to csv file method

### Changed

- n/a

## [0.4.0] - 2023-03-12

### Added

- n/a

### Changed

- changed package manager

## [0.3.2] - 2022-10-10

### Added

- n/a

### Changed

- n/a

## [0.3.1] - 2022-06-15

### Added

- n/a

### Changed

- n/a

## [0.2.1] - 2021-08-01

### Added

-

### Changed

- `get_current_trading_code()`

## [0.2.0] - 2021-06-01

### Added

- added get_market_depth_data
- added get_dsex_data
- added 'dse.com.bd' as redundant

### Changed

- Changed documentation
- changed get_agm_news
- changed get_all_news

## [0.1.4] - 2020-08-22

### Added

- added get_market_inf_more_data

### Changed

- Changed documentation

## [0.1.3] - 2020-08-20

### Added

- html5lib
- added get params

### Changed

- post request to get

## [0.1.2] - 2020-05-21

### Added

- modified index declaration

## [0.1.1] - 2020-05-20

### Added

- modified index declaration

## [0.1.0] - 2020-04-08

### Added

- added git tag
- `VERSION.txt`

### Changed

- `setup.py`
- `HISTORY.md` to `CHANGELOG.md`

## [0.0.1] - 2020-04-06

### Added

- `get_hist_data(), get_current_trade_data()`
- `HISTORY.md`
