import unittest
from decimal import Decimal as D

from app import calculations as c


class Formulas(unittest.TestCase):
    def test_core_formulas(self):
        self.assertEqual(c.shortfall(1000, 800), D(200))
        self.assertEqual(c.positive_shortfall(1000, 800), D(200))
        self.assertEqual(c.achievement_pct(1000, 800), D(80))
        self.assertEqual(c.loss_pct(1000, 800), D(20))
        self.assertEqual(c.revenue(800, "70.5"), D("56400.0"))
        self.assertEqual(c.revenue_loss(1000, 800, 70), D(14000))
        self.assertEqual(c.operating_profit(D(56400), 6400), D(50000))

    def test_overproduction_is_negative_shortfall_but_zero_loss(self):
        self.assertEqual(c.shortfall(1000, 1200), D(-200))
        self.assertEqual(c.positive_shortfall(1000, 1200), D(0))
        self.assertEqual(c.loss_pct(1000, 1200), D(0))
        self.assertEqual(c.revenue_loss(1000, 1200, 70), D(0))
        self.assertEqual(c.achievement_pct(1000, 1200), D(120))

    def test_zero_planned_is_safe(self):
        self.assertIsNone(c.achievement_pct(0, 50))
        self.assertIsNone(c.loss_pct(0, 0))
        self.assertEqual(c.positive_shortfall(0, 50), D(0))

    def test_invalid_input_rejected(self):
        for bad in (-1, "abc", None, True, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                c.achievement_pct(100, bad)
        with self.assertRaises(ValueError):
            c.revenue(10, -5)

    def test_decimal_precision_kept(self):
        self.assertEqual(c.revenue("0.1", "0.2"), D("0.02"))

    def test_totals_do_not_let_overproduction_hide_losses(self):
        rows = [dict(planned_oil=1000, actual_oil=800, oil_price=70, operating_cost=100, downtime_hours=2),
                dict(planned_oil=1000, actual_oil=1200, oil_price=70, operating_cost=100, downtime_hours=0)]
        t = c.totals(rows)
        self.assertEqual(t["net_shortfall"], D(0))
        self.assertEqual(t["positive_shortfall"], D(200))
        self.assertEqual(t["revenue_loss"], D(14000))
        self.assertEqual(t["achievement_pct"], D(100))
        self.assertEqual(t["loss_pct"], D(10))
        self.assertEqual(t["operating_profit"], D(2000 * 70 - 200))

    def test_totals_empty(self):
        t = c.totals([])
        self.assertIsNone(t["achievement_pct"])
        self.assertEqual(t["record_count"], 0)

    def test_target_status(self):
        self.assertEqual(c.target_status(D(1000), 1000), "MET")
        self.assertEqual(c.target_status(D(950), 1000, 90), "AT_RISK")
        self.assertEqual(c.target_status(D(950), 1000, 90, period_ended=True), "MISSED")
        self.assertEqual(c.target_status(D(500), 1000), "MISSED")
        self.assertEqual(c.target_status(None, 1000), "NO_DATA")
        with self.assertRaises(ValueError):
            c.target_status(D(1), 0)


if __name__ == "__main__":
    unittest.main()
