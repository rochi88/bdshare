# _*_ coding:utf-8 _*_
'''
Tests for bdshare.portfolio (position tracking and live P&L valuation).
'''
import unittest
import pandas as pd

from bdshare.portfolio import Portfolio, Position


class TestPosition(unittest.TestCase):

    def test_cost_basis(self):
        p = Position("GP", quantity=100, avg_cost=450.5)
        self.assertEqual(p.cost_basis, 45050.0)


class TestPortfolioHoldings(unittest.TestCase):
    """No-network tests: cost-basis bookkeeping only."""

    def test_empty_portfolio_holdings(self):
        pf = Portfolio()
        df = pf.holdings()
        self.assertIsInstance(df, pd.DataFrame)
        self.assertTrue(df.empty)
        self.assertEqual(list(df.columns), ["symbol", "quantity", "avg_cost", "cost_basis"])

    def test_add_position(self):
        pf = Portfolio()
        pf.add_position("gp", quantity=100, avg_cost=450.5)
        self.assertIn("GP", pf.positions)
        self.assertEqual(pf.positions["GP"].quantity, 100)

    def test_add_position_blends_cost(self):
        pf = Portfolio()
        pf.add_position("GP", quantity=100, avg_cost=450.0)
        pf.add_position("GP", quantity=50, avg_cost=480.0)
        pos = pf.positions["GP"]
        self.assertEqual(pos.quantity, 150)
        self.assertAlmostEqual(pos.avg_cost, (100 * 450.0 + 50 * 480.0) / 150)

    def test_add_position_netting_to_zero_removes_it(self):
        pf = Portfolio()
        pf.add_position("GP", quantity=100, avg_cost=450.0)
        pf.add_position("GP", quantity=-100, avg_cost=0)
        self.assertNotIn("GP", pf.positions)

    def test_remove_position(self):
        pf = Portfolio()
        pf.add_position("GP", quantity=100, avg_cost=450.0)
        pf.remove_position("gp")
        self.assertNotIn("GP", pf.positions)
        # Removing something not held is a no-op, not an error.
        pf.remove_position("NOT_HELD")

    def test_holdings_dataframe(self):
        pf = Portfolio()
        pf.add_position("GP", quantity=100, avg_cost=450.5)
        pf.add_position("ACI", quantity=50, avg_cost=225.75)
        df = pf.holdings()
        self.assertEqual(len(df), 2)
        self.assertEqual(set(df["symbol"]), {"GP", "ACI"})
        gp_row = df[df["symbol"] == "GP"].iloc[0]
        self.assertEqual(gp_row["cost_basis"], 45050.0)


class TestPortfolioValuation(unittest.TestCase):
    """Live tests: valuation() and summary() hit the real DSE feed."""

    def test_empty_portfolio_valuation_and_summary(self):
        pf = Portfolio()
        df = pf.valuation()
        self.assertIsInstance(df, pd.DataFrame)
        self.assertTrue(df.empty)
        summary = pf.summary()
        self.assertEqual(summary["positions"], 0)
        self.assertEqual(summary["total_cost"], 0.0)

    def test_valuation_known_symbols(self):
        pf = Portfolio()
        pf.add_position("GP", quantity=100, avg_cost=450.5)
        pf.add_position("ACI", quantity=50, avg_cost=225.75)
        df = pf.valuation()
        self.assertEqual(len(df), 2)
        for col in ("ltp", "market_value", "pnl", "pnl_pct"):
            self.assertIn(col, df.columns)
        self.assertTrue(df["ltp"].notna().all())

    def test_valuation_unknown_symbol_is_nan_not_error(self):
        pf = Portfolio()
        pf.add_position("NOT_A_REAL_SYMBOL_XYZ", quantity=10, avg_cost=1.0)
        df = pf.valuation()
        self.assertEqual(len(df), 1)
        self.assertTrue(pd.isna(df.iloc[0]["ltp"]))
        self.assertTrue(pd.isna(df.iloc[0]["market_value"]))

    def test_summary_totals(self):
        pf = Portfolio()
        pf.add_position("GP", quantity=100, avg_cost=450.5)
        summary = pf.summary()
        self.assertEqual(summary["positions"], 1)
        self.assertAlmostEqual(summary["total_cost"], 45050.0)
        self.assertIsInstance(summary["total_value"], float)
        self.assertAlmostEqual(
            summary["total_pnl"], summary["total_value"] - summary["total_cost"]
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
