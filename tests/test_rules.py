import unittest

import pandas as pd

from src.strategy.portfolio import equal_weight
from src.strategy.rules import TopMomentumRule


class StrategyRuleTests(unittest.TestCase):
    def make_factor_data(self) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {
                    "date": pd.Timestamp("2024-01-31"),
                    "ticker": "sz000001",
                    "close": 10.0,
                    "ret_20": 0.30,
                    "ma_20": 9.5,
                    "close_above_ma20": True,
                    "amount_ma_20": 100_000_000.0,
                },
                {
                    "date": pd.Timestamp("2024-01-31"),
                    "ticker": "sh600000",
                    "close": 9.0,
                    "ret_20": 0.20,
                    "ma_20": 8.8,
                    "close_above_ma20": True,
                    "amount_ma_20": 80_000_000.0,
                },
                {
                    "date": pd.Timestamp("2024-01-31"),
                    "ticker": "sz000002",
                    "close": 8.0,
                    "ret_20": 0.40,
                    "ma_20": 8.2,
                    "close_above_ma20": False,
                    "amount_ma_20": 90_000_000.0,
                },
                {
                    "date": pd.Timestamp("2024-01-31"),
                    "ticker": "sh600001",
                    "close": 7.0,
                    "ret_20": 0.50,
                    "ma_20": 6.5,
                    "close_above_ma20": True,
                    "amount_ma_20": 10_000_000.0,
                },
            ]
        )

    def test_equal_weight_returns_uniform_weights(self) -> None:
        weights = equal_weight(["a", "b", "c"])
        self.assertEqual(weights, {"a": 1 / 3, "b": 1 / 3, "c": 1 / 3})

    def test_equal_weight_returns_empty_dict_for_empty_input(self) -> None:
        self.assertEqual(equal_weight([]), {})

    def test_generate_signals_applies_filters_and_topk(self) -> None:
        config = {
            "topk": 2,
            "min_amount_ma20": 50_000_000,
            "require_close_above_ma20": True,
        }
        rule = TopMomentumRule(config)

        weights = rule.generate_signals(pd.Timestamp("2024-01-31"), self.make_factor_data())

        self.assertEqual(weights, {"sz000001": 0.5, "sh600000": 0.5})

    def test_generate_signals_returns_empty_when_no_rows_pass_filters(self) -> None:
        config = {
            "topk": 2,
            "min_amount_ma20": 200_000_000,
            "require_close_above_ma20": True,
        }
        rule = TopMomentumRule(config)

        weights = rule.generate_signals(pd.Timestamp("2024-01-31"), self.make_factor_data())

        self.assertEqual(weights, {})

    def test_generate_signals_filters_by_universe_membership_for_date(self) -> None:
        config = {
            "topk": 2,
            "min_amount_ma20": 50_000_000,
            "require_close_above_ma20": True,
        }
        rule = TopMomentumRule(config)
        universe = pd.DataFrame(
            [
                {"date": pd.Timestamp("2024-01-31"), "ticker": "sh600000"},
            ]
        )

        weights = rule.generate_signals(pd.Timestamp("2024-01-31"), self.make_factor_data(), universe)

        self.assertEqual(weights, {"sh600000": 1.0})


if __name__ == "__main__":
    unittest.main()
