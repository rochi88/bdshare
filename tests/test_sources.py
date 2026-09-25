# _*_ coding:utf-8 _*_
'''
Tests for scraping either DSE site: the legacy old.dsebd.org HTML pages and
the current dsebd.org JSON API, plus the automatic fallback between them.

The offline tests mock HTTP. The live tests hit both sites and are skipped
with BDSHARE_SKIP_LIVE=1.
'''
import os
import unittest
from unittest import mock

import pandas as pd

import bdshare
from bdshare.util import vars as vs
from bdshare.util import helper
from bdshare.util.helper import BDShareError, _safe_num, _with_fallback
from bdshare.stock import trading


class _SourceMixin:
    """Force vs.DSE_SOURCE for the duration of a test."""
    source = "auto"

    def setUp(self):
        self._saved_source = vs.DSE_SOURCE
        vs.DSE_SOURCE = self.source

    def tearDown(self):
        vs.DSE_SOURCE = self._saved_source


class TestSafeNum(unittest.TestCase):

    def test_keeps_negative_sign(self):
        self.assertEqual(_safe_num("-1.20", float), -1.2)
        self.assertEqual(_safe_num("-1,234", int), -1234)

    def test_dash_placeholders_are_none(self):
        for placeholder in ("-", "--", " -- ", "", "n/a", "NaN"):
            self.assertIsNone(_safe_num(placeholder, float), placeholder)


class TestWithFallback(_SourceMixin, unittest.TestCase):

    def test_auto_uses_new_site_when_it_works(self):
        legacy = mock.Mock()
        self.assertEqual(_with_fallback(legacy, lambda: "new", "x"), "new")
        legacy.assert_not_called()

    def test_auto_falls_back_on_new_site_failure(self):
        def new():
            raise BDShareError("404")
        self.assertEqual(_with_fallback(lambda: "legacy", new, "x"), "legacy")

    def test_auto_falls_back_on_new_site_parse_error(self):
        def new():
            return {}["rows"]  # KeyError, as from a changed API response
        self.assertEqual(_with_fallback(lambda: "legacy", new, "x"), "legacy")

    def test_auto_reports_both_failures(self):
        def fail(msg):
            def f():
                raise BDShareError(msg)
            return f
        with self.assertRaises(BDShareError) as ctx:
            _with_fallback(fail("legacy down"), fail("new down"), "Thing")
        self.assertIn("legacy down", str(ctx.exception))
        self.assertIn("new down", str(ctx.exception))

    def test_forced_sources(self):
        legacy, new = mock.Mock(return_value=1), mock.Mock(return_value=2)
        vs.DSE_SOURCE = "legacy"
        self.assertEqual(_with_fallback(legacy, new, "x"), 1)
        vs.DSE_SOURCE = "new"
        self.assertEqual(_with_fallback(legacy, new, "x"), 2)

    def test_invalid_source(self):
        vs.DSE_SOURCE = "bogus"
        with self.assertRaises(ValueError):
            _with_fallback(lambda: 1, lambda: 2, "x")


class TestFetchJsonRange(unittest.TestCase):

    def test_splits_truncated_range_newest_first(self):
        def fake(path, params=None, retries=3, pause=0.2):
            if params["from"] == params["to"]:
                return {"rows": [params["from"]]}
            return {"rows": ["partial"], "truncated": True}

        with mock.patch.object(helper, "_fetch_json", side_effect=fake):
            rows = helper._fetch_json_range("p", "2026-01-01", "2026-01-04")
        self.assertEqual(rows, ["2026-01-04", "2026-01-03", "2026-01-02", "2026-01-01"])

    def test_single_day_is_not_split(self):
        with mock.patch.object(helper, "_fetch_json",
                               return_value={"rows": [1, 2], "total": 5}) as fetch:
            self.assertEqual(helper._fetch_json_range("p", "2026-01-01", "2026-01-01"), [1, 2])
        fetch.assert_called_once()


class TestDayEndCap(unittest.TestCase):

    def test_fills_instruments_cut_off_by_the_row_cap(self):
        def row(code):
            return {"date": "2026-01-01", "tradingCode": code}

        capped_day = [row(f"A{i:03d}") for i in range(trading._DAY_END_CAP)]

        def fake_range(path, start, end, params=None, retries=3, pause=0.2, max_rows=None):
            if params and params.get("inst"):
                return [row(params["inst"])]
            return list(capped_day)

        instruments = {"instruments": [r["tradingCode"] for r in capped_day] + ["ZZZ", "ZZY"]}
        with mock.patch.object(trading, "_fetch_json_range", side_effect=fake_range), \
                mock.patch.object(trading, "_fetch_json", return_value=instruments):
            rows = trading._day_end_rows_new("2026-01-01", "2026-01-01", None, 3, 0)

        codes = [r["tradingCode"] for r in rows]
        self.assertEqual(len(codes), trading._DAY_END_CAP + 2)
        self.assertIn("ZZZ", codes)
        self.assertIn("ZZY", codes)


@unittest.skipIf(os.environ.get("BDSHARE_SKIP_LIVE"), "live network tests disabled")
class _LiveBothSites(_SourceMixin):
    """Live checks run once per site; subclasses set ``source``."""

    TRADE_COLUMNS = ["symbol", "ltp", "high", "low", "close", "ycp",
                     "change", "trade", "value", "volume"]

    def test_current_trade_data(self):
        df = bdshare.get_current_trade_data()
        self.assertEqual(list(df.columns), self.TRADE_COLUMNS)
        self.assertGreater(len(df), 100)

    def test_dsex_data(self):
        df = bdshare.get_dsex_data()
        self.assertEqual(list(df.columns), self.TRADE_COLUMNS)
        self.assertFalse(df.empty)

    def test_historical_data(self):
        df = bdshare.get_historical_data("2026-09-01", "2026-09-24", "ACI")
        self.assertEqual(list(df.columns), ["symbol", "ltp", "high", "low", "open",
                                            "close", "ycp", "trade", "value", "volume"])
        self.assertTrue((df["symbol"] == "ACI").all())
        self.assertFalse(df.empty)

    def test_close_price_data(self):
        df = bdshare.get_close_price_data("2026-09-20", "2026-09-24", "ACI")
        self.assertEqual(list(df.columns), ["symbol", "close", "ycp"])
        self.assertFalse(df.empty)

    def test_market_info(self):
        df = bdshare.get_market_info()
        self.assertEqual(len(df), 30)
        self.assertEqual(df.columns[0], "Date")

    def test_market_info_more_data(self):
        df = bdshare.get_market_info_more_data("2026-09-01", "2026-09-24")
        self.assertFalse(df.empty)
        self.assertIn("DSEX Index", df.columns)

    def test_latest_pe(self):
        df = bdshare.get_latest_pe()
        self.assertEqual(df.shape[1], 9)
        self.assertGreater(len(df), 100)

    def test_top_gainers(self):
        df = bdshare.get_top_ten_gainers_losers()
        self.assertEqual(list(df.columns), ["symbol", "close", "high", "low", "ycp", "change"])
        self.assertEqual(len(df), 10)

    def test_top_twenty_shares(self):
        df = bdshare.get_top_twenty_shares()
        self.assertEqual(list(df.columns),
                         ["symbol", "ltp", "high", "low", "ycp", "trade", "volume"])
        self.assertEqual(len(df), 20)
        self.assertTrue(pd.api.types.is_integer_dtype(df["trade"]))

    def test_market_status(self):
        self.assertIsInstance(bdshare.get_market_status(), str)

    def test_all_news(self):
        df = bdshare.get_all_news(code="ACI")
        self.assertEqual(list(df.columns), ["symbol", "title", "news", "date"])
        self.assertFalse(df.empty)


class TestLiveLegacySite(_LiveBothSites, unittest.TestCase):
    source = "legacy"


class TestLiveCurrentSite(_LiveBothSites, unittest.TestCase):
    source = "new"


if __name__ == "__main__":
    unittest.main()
