import unittest

import pandas as pd

from src.backtest.engine import BacktestEngine


class StubStrategy:
    def __init__(self, weights_by_date: dict[pd.Timestamp, dict[str, float]]) -> None:
        self.weights_by_date = weights_by_date
        self.called_dates: list[pd.Timestamp] = []

    def generate_signals(self, date: pd.Timestamp, factor_data: pd.DataFrame) -> dict[str, float]:
        ts = pd.Timestamp(date)
        self.called_dates.append(ts)
        return self.weights_by_date.get(ts, {})


class BacktestEngineTests(unittest.TestCase):
    def make_prices(self) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {"date": pd.Timestamp("2024-01-30"), "ticker": "sz000001", "close": 9.5},
                {"date": pd.Timestamp("2024-01-30"), "ticker": "sh600000", "close": 19.5},
                {"date": pd.Timestamp("2024-01-31"), "ticker": "sz000001", "close": 10.0},
                {"date": pd.Timestamp("2024-01-31"), "ticker": "sh600000", "close": 20.0},
                {"date": pd.Timestamp("2024-02-01"), "ticker": "sz000001", "close": 11.0},
                {"date": pd.Timestamp("2024-02-01"), "ticker": "sh600000", "close": 21.0},
                {"date": pd.Timestamp("2024-02-02"), "ticker": "sz000001", "close": 12.0},
                {"date": pd.Timestamp("2024-02-02"), "ticker": "sh600000", "close": 22.0},
            ]
        )

    def test_engine_uses_t_minus_1_signal_on_rebalance_date(self) -> None:
        prices = self.make_prices()
        factor_data = pd.DataFrame([{"date": pd.Timestamp("2024-01-30"), "ticker": "sz000001"}])
        strategy = StubStrategy({pd.Timestamp("2024-01-30"): {"sz000001": 1.0}})
        engine = BacktestEngine(initial_capital=100000, commission_bps=0, slippage_bps=0)

        result = engine.run(
            prices=prices,
            factor_data=factor_data,
            strategy=strategy,
            rebalance_dates=[pd.Timestamp("2024-01-31")],
        )

        self.assertEqual(strategy.called_dates, [pd.Timestamp("2024-01-30")])
        self.assertEqual(result["positions"].iloc[0]["ticker"], "sz000001")
        self.assertGreater(result["positions"].iloc[0]["shares"], 0)

    def test_engine_buys_in_round_lots_of_100_shares(self) -> None:
        prices = self.make_prices()
        factor_data = pd.DataFrame([{"date": pd.Timestamp("2024-01-30"), "ticker": "sz000001"}])
        strategy = StubStrategy({pd.Timestamp("2024-01-30"): {"sz000001": 1.0}})
        engine = BacktestEngine(initial_capital=100000, commission_bps=0, slippage_bps=0)

        result = engine.run(
            prices=prices,
            factor_data=factor_data,
            strategy=strategy,
            rebalance_dates=[pd.Timestamp("2024-01-31")],
        )

        first_position = result["positions"].iloc[0]
        self.assertEqual(int(first_position["shares"]) % 100, 0)

    def test_engine_marks_equity_to_market_on_non_rebalance_days(self) -> None:
        prices = self.make_prices()
        factor_data = pd.DataFrame([{"date": pd.Timestamp("2024-01-30"), "ticker": "sz000001"}])
        strategy = StubStrategy({pd.Timestamp("2024-01-30"): {"sz000001": 1.0}})
        engine = BacktestEngine(initial_capital=100000, commission_bps=0, slippage_bps=0)

        result = engine.run(
            prices=prices,
            factor_data=factor_data,
            strategy=strategy,
            rebalance_dates=[pd.Timestamp("2024-01-31")],
        )

        equity = result["equity_curve"]
        self.assertEqual(len(equity), 4)
        self.assertLess(equity.iloc[1]["equity"], equity.iloc[2]["equity"])
        self.assertLess(equity.iloc[2]["equity"], equity.iloc[3]["equity"])

    def test_engine_applies_trading_costs(self) -> None:
        prices = self.make_prices()
        factor_data = pd.DataFrame([{"date": pd.Timestamp("2024-01-30"), "ticker": "sz000001"}])
        strategy = StubStrategy({pd.Timestamp("2024-01-30"): {"sz000001": 1.0}})
        engine_without_cost = BacktestEngine(initial_capital=100000, commission_bps=0, slippage_bps=0)
        engine_with_cost = BacktestEngine(initial_capital=100000, commission_bps=10, slippage_bps=5)

        result_without_cost = engine_without_cost.run(
            prices=prices,
            factor_data=factor_data,
            strategy=strategy,
            rebalance_dates=[pd.Timestamp("2024-01-31")],
        )
        result_with_cost = engine_with_cost.run(
            prices=prices,
            factor_data=factor_data,
            strategy=strategy,
            rebalance_dates=[pd.Timestamp("2024-01-31")],
        )

        no_cost_equity = result_without_cost["equity_curve"].iloc[-1]["equity"]
        with_cost_equity = result_with_cost["equity_curve"].iloc[-1]["equity"]
        self.assertLess(with_cost_equity, no_cost_equity)

    def test_engine_replaces_old_positions_on_next_rebalance(self) -> None:
        prices = self.make_prices()
        factor_data = pd.DataFrame(
            [
                {"date": pd.Timestamp("2024-01-30"), "ticker": "sz000001"},
                {"date": pd.Timestamp("2024-01-31"), "ticker": "sh600000"},
            ]
        )
        strategy = StubStrategy(
            {
                pd.Timestamp("2024-01-30"): {"sz000001": 1.0},
                pd.Timestamp("2024-01-31"): {"sh600000": 1.0},
            }
        )
        engine = BacktestEngine(initial_capital=100000, commission_bps=0, slippage_bps=0)

        result = engine.run(
            prices=prices,
            factor_data=factor_data,
            strategy=strategy,
            rebalance_dates=[pd.Timestamp("2024-01-31"), pd.Timestamp("2024-02-01")],
        )

        last_positions = result["positions"][result["positions"]["date"] == pd.Timestamp("2024-02-02")]
        self.assertEqual(last_positions["ticker"].tolist(), ["sh600000"])

    def test_engine_sells_before_buys_on_rebalance(self) -> None:
        prices = self.make_prices()
        factor_data = pd.DataFrame(
            [
                {"date": pd.Timestamp("2024-01-30"), "ticker": "sz000001"},
                {"date": pd.Timestamp("2024-01-31"), "ticker": "sh600000"},
            ]
        )
        strategy = StubStrategy(
            {
                pd.Timestamp("2024-01-30"): {"sz000001": 1.0},
                pd.Timestamp("2024-01-31"): {"sh600000": 1.0},
            }
        )
        engine = BacktestEngine(initial_capital=100000, commission_bps=0, slippage_bps=0)

        result = engine.run(
            prices=prices,
            factor_data=factor_data,
            strategy=strategy,
            rebalance_dates=[pd.Timestamp("2024-01-31"), pd.Timestamp("2024-02-01")],
        )

        trades = result["trades"]
        second_rebalance = trades[trades["date"] == pd.Timestamp("2024-02-01")].reset_index(drop=True)
        self.assertEqual(second_rebalance.iloc[0]["side"], "sell")
        self.assertEqual(second_rebalance.iloc[1]["side"], "buy")

    def test_engine_rebalances_existing_holdings_to_target_weights(self) -> None:
        prices = self.make_prices()
        factor_data = pd.DataFrame(
            [
                {"date": pd.Timestamp("2024-01-30"), "ticker": "sz000001"},
                {"date": pd.Timestamp("2024-01-30"), "ticker": "sh600000"},
                {"date": pd.Timestamp("2024-01-31"), "ticker": "sz000001"},
                {"date": pd.Timestamp("2024-01-31"), "ticker": "sh600000"},
            ]
        )
        strategy = StubStrategy(
            {
                pd.Timestamp("2024-01-30"): {"sz000001": 1.0},
                pd.Timestamp("2024-01-31"): {"sz000001": 0.5, "sh600000": 0.5},
            }
        )
        engine = BacktestEngine(initial_capital=100000, commission_bps=0, slippage_bps=0)

        result = engine.run(
            prices=prices,
            factor_data=factor_data,
            strategy=strategy,
            rebalance_dates=[pd.Timestamp("2024-01-31"), pd.Timestamp("2024-02-01")],
        )

        positions = result["positions"]
        last_positions = positions[positions["date"] == pd.Timestamp("2024-02-02")].sort_values("ticker").reset_index(drop=True)
        self.assertEqual(last_positions["ticker"].tolist(), ["sh600000", "sz000001"])
        self.assertLess(int(last_positions[last_positions["ticker"] == "sz000001"].iloc[0]["shares"]), 10000)
        buy_trades = result["trades"][(result["trades"]["date"] == pd.Timestamp("2024-02-01")) & (result["trades"]["side"] == "buy")]
        self.assertIn("sh600000", buy_trades["ticker"].tolist())

    def test_engine_does_not_buy_untradable_target(self) -> None:
        prices = self.make_prices()
        prices.loc[
            (prices["date"] == pd.Timestamp("2024-01-31")) & (prices["ticker"] == "sh600000"),
            "is_tradable",
        ] = False
        factor_data = pd.DataFrame([{"date": pd.Timestamp("2024-01-30"), "ticker": "sh600000"}])
        strategy = StubStrategy({pd.Timestamp("2024-01-30"): {"sh600000": 1.0}})
        engine = BacktestEngine(initial_capital=100000, commission_bps=0, slippage_bps=0)

        result = engine.run(
            prices=prices,
            factor_data=factor_data,
            strategy=strategy,
            rebalance_dates=[pd.Timestamp("2024-01-31")],
        )

        self.assertTrue(result["trades"].empty)
        self.assertTrue(result["positions"].empty)

    def test_engine_does_not_sell_untradable_existing_holding(self) -> None:
        prices = self.make_prices()
        prices.loc[
            (prices["date"] == pd.Timestamp("2024-02-01")) & (prices["ticker"] == "sz000001"),
            "is_tradable",
        ] = False
        factor_data = pd.DataFrame(
            [
                {"date": pd.Timestamp("2024-01-30"), "ticker": "sz000001"},
                {"date": pd.Timestamp("2024-01-31"), "ticker": "sh600000"},
            ]
        )
        strategy = StubStrategy(
            {
                pd.Timestamp("2024-01-30"): {"sz000001": 1.0},
                pd.Timestamp("2024-01-31"): {"sh600000": 1.0},
            }
        )
        engine = BacktestEngine(initial_capital=100000, commission_bps=0, slippage_bps=0)

        result = engine.run(
            prices=prices,
            factor_data=factor_data,
            strategy=strategy,
            rebalance_dates=[pd.Timestamp("2024-01-31"), pd.Timestamp("2024-02-01")],
        )

        second_rebalance_trades = result["trades"][result["trades"]["date"] == pd.Timestamp("2024-02-01")]
        self.assertTrue((second_rebalance_trades["side"] != "sell").all())
        last_positions = result["positions"][result["positions"]["date"] == pd.Timestamp("2024-02-02")]
        self.assertIn("sz000001", last_positions["ticker"].tolist())


if __name__ == "__main__":
    unittest.main()
