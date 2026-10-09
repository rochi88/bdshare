# _*_ coding:utf-8 _*_
'''
Tests for scraping either DSE site: the legacy old.dsebd.org HTML pages and
the current dsebd.org JSON API, plus the automatic fallback between them.

The offline tests mock HTTP. The live tests hit both sites and are skipped
with BDSHARE_SKIP_LIVE=1.
'''
import os
import unittest
import warnings
from unittest import mock

import pandas as pd

import bdshare
from bdshare.util import vars as vs
from bdshare.util import helper
from bdshare.util.helper import BDShareError, _safe_num, _with_fallback
from bdshare.stock import market, news, trading


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


class TestFetchJsonPages(unittest.TestCase):

    @staticmethod
    def _fake(total, size=2):
        rows = list(range(total))
        def fake(path, params=None, retries=3, pause=0.2):
            page = params.get("page", 1)
            return {"rows": rows[(page - 1) * size:page * size],
                    "total": total, "page": page, "pageSize": size}
        return fake

    def test_fetches_every_page_in_order(self):
        with mock.patch.object(helper, "_fetch_json", side_effect=self._fake(7)) as fetch:
            self.assertEqual(helper._fetch_json_pages("p", {"x": 1}), list(range(7)))
        self.assertEqual(fetch.call_count, 4)
        self.assertEqual(sorted(c.args[1].get("page", 1) for c in fetch.call_args_list),
                         [1, 2, 3, 4])
        self.assertTrue(all(c.args[1]["x"] == 1 for c in fetch.call_args_list))

    def test_single_page_makes_one_request(self):
        with mock.patch.object(helper, "_fetch_json", side_effect=self._fake(2)) as fetch:
            self.assertEqual(helper._fetch_json_pages("p"), [0, 1])
        fetch.assert_called_once()

    def test_empty_result(self):
        with mock.patch.object(helper, "_fetch_json",
                               return_value={"rows": [], "total": 0, "pageSize": 500}) as fetch:
            self.assertEqual(helper._fetch_json_pages("p"), [])
        fetch.assert_called_once()


class TestDayEndRows(unittest.TestCase):

    def test_passes_range_and_instrument(self):
        with mock.patch.object(trading, "_fetch_json_pages", return_value=[1]) as pages:
            trading._day_end_rows_new("2026-01-01", "2026-01-31", "GP", 3, 0)
            trading._day_end_rows_new("2026-01-01", "2026-01-31", None, 3, 0)
        self.assertEqual(pages.call_args_list[0].args[1],
                         {"from": "2026-01-01", "to": "2026-01-31", "inst": "GP"})
        self.assertEqual(pages.call_args_list[1].args[1],
                         {"from": "2026-01-01", "to": "2026-01-31"})


class TestParseQuotes(unittest.TestCase):

    def test_skips_title_and_header(self):
        text = ("Price & Index for the Date:09-10-2026        Time: 10:45:01\n\n"
                "Instr. Code        Last Trade/Close Price\n\n"
                "1JANATAMF \t 3.4\nAMCL(PRAN) \t 217.5\nACI \t\t 1,187.6\n")
        self.assertEqual(trading._parse_quotes(text),
                         [("1JANATAMF", 3.4), ("AMCL(PRAN)", 217.5), ("ACI", 1187.6)])


class TestLegacyNewsQueries(_SourceMixin, unittest.TestCase):
    source = "legacy"

    def _params(self, *args, **kwargs):
        with mock.patch.object(news, "_legacy_news_rows", return_value=[]) as rows:
            bdshare.get_all_news(*args, **kwargs)
        return rows.call_args.args[0]

    def test_no_arguments_uses_latest_feed(self):
        self.assertEqual(self._params(), {"archive": "news", "criteria": 2})

    def test_date_range_sends_both_dates(self):
        self.assertEqual(self._params("2026-09-01", "2026-09-30"),
                         {"archive": "news", "criteria": 4,
                          "startDate": "2026-09-01", "endDate": "2026-09-30"})

    def test_code_filters_dates_locally(self):
        items = [{"symbol": "GP", "date": d} for d in ("2026-01-05", "2026-02-05", "2026-03-05")]
        with mock.patch.object(news, "_legacy_news_rows", return_value=items) as rows:
            df = bdshare.get_all_news("2026-02-01", "2026-02-28", "GP")
        self.assertEqual(rows.call_args.args[0], {"archive": "news", "criteria": 3, "inst": "GP"})
        self.assertEqual(df["date"].tolist(), ["2026-02-05"])

    def test_price_sensitive_news_is_new_site_only(self):
        with self.assertRaisesRegex(BDShareError, "only available from dsebd.org"):
            bdshare.get_price_sensitive_news()


def _rsc_page(payload: str) -> str:
    """A minimal Next.js page carrying ``payload`` as RSC push scripts, split mid-row."""
    import json
    half = len(payload) // 2
    return "".join(
        f'<script>self.__next_f.push([1,{json.dumps(part)}])</script>'
        for part in (payload[:half], payload[half:])
    )


class TestRscPayload(unittest.TestCase):

    def test_rows_and_length_prefixed_text(self):
        text = "Dhaka ৳ text"  # multi-byte: the T length counts bytes
        payload = (f'1:I["chunk.js"]\n'
                   f'2:T{len(text.encode()):x},{text}'
                   f'3:{{"a":"$2","b":"$undefined","c":"$$x","d":"$1"}}\n')
        rows = helper._rsc_rows(_rsc_page(payload))
        self.assertEqual(rows["2"], text)
        self.assertEqual(rows["1"], 'I["chunk.js"]')
        self.assertEqual(helper._rsc_resolve(rows["3"], rows),
                         {"a": text, "b": None, "c": "$x", "d": 'I["chunk.js"]'})

    def test_path_through_react_element(self):
        rows = {"5": ["$", "div", None, {"children": ["$", "p", None, {"x": 1}]}]}
        self.assertEqual(helper._rsc_resolve("$5:props:children:props:x", rows), 1)

    def test_reference_cycle_raises(self):
        with self.assertRaisesRegex(BDShareError, "cycle"):
            helper._rsc_resolve("$1", {"1": "$2", "2": "$1"})

    def test_path_reference(self):
        rows = {"5": {"props": {"t": {"dates": ["01 Oct", "04 Oct"]}}}}
        self.assertEqual(helper._rsc_resolve("$5:props:t:dates", rows), ["01 Oct", "04 Oct"])


class TestCompanyDetails(unittest.TestCase):

    PAYLOAD = (
        '7:T5,hello'
        '5:["$","div",null,{"company":{"code":"GP","name":"Grameenphone Ltd.",'
        '"authorizedCapital":40000,"description":"$7","creditRating":"$undefined",'
        '"loanStatus":{"shortTerm":7000},'
        '"sharePattern":[{"date":"Sep 30, 2026","pattern":{"sponsor":90,"public":3}}],'
        '"dividendHistory":[],'
        '"peTable":{"dates":["01 Oct","04 Oct"],"basic":[11.0,11.1]},'
        '"disclosuresNextCursor":"123"}}]\n'
    )

    def _details(self, symbol, payload=PAYLOAD):
        page = mock.Mock(text=_rsc_page(payload))
        with mock.patch.object(market, "safe_get", return_value=page) as get:
            return market.get_company_details(symbol), get.call_args.args[0]

    def test_fields_and_tables(self):
        d, url = self._details("gp")
        self.assertTrue(url.endswith("company/GP"))
        self.assertEqual(d["name"], "Grameenphone Ltd.")
        self.assertEqual(d["description"], "hello")
        self.assertIsNone(d["creditRating"])
        self.assertEqual(d["loanStatus"], {"shortTerm": 7000})
        self.assertNotIn("disclosuresNextCursor", d)
        self.assertEqual(list(d["sharePattern"].columns),
                         ["date", "pattern_sponsor", "pattern_public"])
        self.assertTrue(d["dividendHistory"].empty)
        self.assertEqual(d["peTable"]["basic"].tolist(), [11.0, 11.1])

    def test_symbol_is_url_encoded(self):
        payload = self.PAYLOAD.replace('"code":"GP"', '"code":"AMCL(PRAN)"')
        d, url = self._details("amcl(pran)", payload)
        self.assertTrue(url.endswith("company/AMCL%28PRAN%29"))
        self.assertEqual(d["code"], "AMCL(PRAN)")

    def test_unknown_symbol(self):
        with self.assertRaisesRegex(BDShareError, "Company not found"):
            self._details("NOSUCHCO")


class TestLastTradePriceNew(_SourceMixin, unittest.TestCase):
    source = "new"

    def test_close_then_ltp_main_board_only_sorted(self):
        data = {"cols": ["code", "board", "ltp", "close"],
                "rows": [["GP", "PUBLIC", 242.5, 242.0],
                         ["ACI", "PUBLIC", 187.6, None],   # in session: no close yet
                         ["XBOND", "DEBT", 100.0, 100.0]]}
        with mock.patch.object(trading, "_fetch_json", return_value=data):
            df = bdshare.get_last_trade_price_data()
        self.assertEqual(df.values.tolist(), [["ACI", 187.6], ["GP", 242.0]])


class TestDividendDeclarations(unittest.TestCase):

    @staticmethod
    def _item(code, summary, body, id_, type_="Dividend", filed="2026-10-05"):
        return {"id": id_, "code": code, "name": f"{code} Ltd.", "type": type_,
                "summary": f"{code}: {summary}", "body": body, "filedAt": filed}

    def test_parses_multi_part_declaration(self):
        rows = [
            self._item("APEX", "Dividend Declaration",
                       "(Cont. News of APEX): The Company has also reported EPS of Tk. 3.38. (end)", "2"),
            self._item("APEX", "Dividend Declaration",
                       "The Board of Directors has recommended 20% Cash Dividend for the year ended "
                       "June 30, 2026. Date of AGM: 26.11.2026, Time: 10:00 AM, Venue/Mode: Digital "
                       "Platform. Record Date: 27.10.2026. (cont.)", "1"),
        ]
        self.assertEqual(news._parse_dividend_declarations(rows), [{
            "symbol": "APEX", "company": "APEX Ltd.", "date": "2026-10-05",
            "yearEnd": "June 30, 2026", "dividend": "20% Cash Dividend",
            "agmDate": "26.11.2026", "recordDate": "27.10.2026",
            "venue": "Digital Platform", "time": "10:00 AM",
        }])

    def test_interim_and_alternate_wording(self):
        rows = [
            self._item("GP", "Declaration of Interim Dividend and Audited Q2 Financials",
                       "The Board has declared Interim Cash Dividend for the year 2026 at the rate "
                       "of 105% of the paid-up capital for the six-month period ended on 30 June "
                       "2026. Record date for entitlement of Interim Cash Dividend is August 12, 2026.", "1"),
            self._item("ENVOY", "Dividend Declaration",
                       "The Board of Directors has recommended 32.50% Cash Dividend for the year "
                       "ended June 30, 2026. Date of AGM: 05 December 2026 at 11:00 AM, Venue: "
                       "Gulshan Club, Dhaka. Record Date: 26 October 2026.", "2"),
        ]
        gp, envoy = news._parse_dividend_declarations(rows)
        self.assertEqual(gp["dividend"], "105% Interim Cash Dividend")
        self.assertEqual(gp["recordDate"], "August 12, 2026")
        self.assertIsNone(gp["agmDate"])
        self.assertEqual((envoy["agmDate"], envoy["time"], envoy["recordDate"]),
                         ("05 December 2026", "11:00 AM", "26 October 2026"))

    def test_skips_other_news_and_orphan_continuations(self):
        rows = [
            self._item("X", "Dividend Disbursement", "The Company has disbursed...", "1"),
            self._item("Y", "Dividend Declaration", "recommended 10% Cash Dividend for the year "
                       "ended June 30, 2026.", "2", type_="Price sensitive"),
            self._item("Z", "Dividend Declaration",
                       "(Continuation news of W): Stock Dividend is not recommended...", "3"),
            self._item("V", "No BSEC Approval Required for Stock Dividend Declaration", "...", "4"),
        ]
        self.assertEqual(news._parse_dividend_declarations(rows), [])

    def test_default_range_and_code(self):
        with mock.patch.object(news, "_fetch_json_range", return_value=[]) as fetch, \
                mock.patch.object(news, "_date_range", return_value=("2026-10-09", "2026-10-09")):
            df = bdshare.get_dividend_declarations(code="GP")
        self.assertEqual(fetch.call_args.args[1:4], ("2026-04-12", "2026-10-09", {"code": "GP"}))
        self.assertEqual(list(df.columns), news._DIVIDEND_COLUMNS)


class TestDeprecations(unittest.TestCase):

    @staticmethod
    def _deprecations(fn, *args):
        """DeprecationWarning messages raised by ``fn(*args)``.

        The fake pages below hold no real data, so a BDShareError from parsing
        them is expected and ignored.
        """
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            try:
                fn(*args)
            except BDShareError:
                pass
        return [str(w.message) for w in caught if issubclass(w.category, DeprecationWarning)]

    def test_legacy_only_functions_warn_once_and_name_replacement(self):
        page = mock.Mock(content=b"<html></html>")
        table = helper._parse_html(b"<table><tr><td>x</td></tr></table>").xpath("//table")[0]
        cases = [
            ("get_company_info", bdshare.get_company_info, "get_company_details"),
            ("get_company_inf", bdshare.get_company_inf, "get_company_details"),
            ("BDShare.get_company_profile",
             bdshare.BDShare(cache_enabled=False).get_company_profile, "get_company_details"),
            ("get_agm_news", lambda _: bdshare.get_agm_news(), "get_dividend_declarations"),
            ("get_news('agm')", lambda _: bdshare.get_news("agm"), "news_type='dividend'"),
        ]
        with mock.patch.object(market, "safe_get", return_value=page), \
                mock.patch.object(news, "_fetch_table", return_value=table):
            for name, fn, replacement in cases:
                with self.subTest(name):
                    msgs = self._deprecations(fn, "GP")
                    self.assertEqual(len(msgs), 1, msgs)
                    self.assertIn(replacement, msgs[0])

    def test_replacements_do_not_warn(self):
        with mock.patch.object(news, "_fetch_json_range", return_value=[]):
            self.assertEqual(self._deprecations(bdshare.get_dividend_declarations), [])
            self.assertEqual(self._deprecations(bdshare.get_news, "dividend"), [])


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


@unittest.skipIf(os.environ.get("BDSHARE_SKIP_LIVE"), "live network tests disabled")
class TestLiveCompanyDetails(unittest.TestCase):

    def test_company_details(self):
        d = bdshare.get_company_details("GP")
        self.assertEqual(d["code"], "GP")
        self.assertIn("name", d)
        self.assertIsInstance(d["dividendHistory"], pd.DataFrame)

    def test_unknown_company(self):
        with self.assertRaises(BDShareError):
            bdshare.get_company_details("NOSUCHCO")
