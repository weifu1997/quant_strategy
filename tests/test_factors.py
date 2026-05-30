import unittest

import pandas as pd
from pandas.testing import assert_series_equal

from src.factors.momentum import calc_ret
from src.factors.trend import calc_ma, close_above_ma
from src.factors.liquidity import calc_amount_ma


class FactorFunctionTests(unittest.TestCase):
    def make_sample(self) -> pd.DataFrame:
        dates = pd.date_range("2024-01-01", periods=25, freq="D")
        rows = []
        for i, date in enumerate(dates, start=1):
            rows.append(
                {
                    "date": date,
                    "ticker": "sz000001",
                    "open": float(i),
                    "high": float(i) + 0.5,
                    "low": float(i) - 0.5,
                    "close": float(i),
                    "volume": float(1000 + i),
                    "amount": float(10000 + i * 10),
                }
            )
            rows.append(
                {
                    "date": date,
                    "ticker": "sh600000",
                    "open": float(i * 10),
                    "high": float(i * 10) + 0.5,
                    "low": float(i * 10) - 0.5,
                    "close": float(i * 10),
                    "volume": float(2000 + i),
                    "amount": float(50000 + i * 100),
                }
            )
        return pd.DataFrame(rows)

    def test_calc_ret_adds_grouped_ret_20_column(self) -> None:
        df = self.make_sample()
        df.loc[(df["ticker"] == "sh600000") & (df["date"] == pd.Timestamp("2024-01-21")), "close"] = 999.0

        result = calc_ret(df, period=20)

        self.assertIn("ret_20", result.columns)

        ticker_a = result[result["ticker"] == "sz000001"].sort_values("date")
        ticker_b = result[result["ticker"] == "sh600000"].sort_values("date")

        self.assertTrue(pd.isna(ticker_a.iloc[19]["ret_20"]))
        self.assertAlmostEqual(ticker_a.iloc[20]["ret_20"], 20.0)
        self.assertAlmostEqual(ticker_b.iloc[20]["ret_20"], 98.9)

    def test_calc_ma_adds_grouped_ma_20_column(self) -> None:
        df = self.make_sample()

        result = calc_ma(df, period=20)

        self.assertIn("ma_20", result.columns)

        ticker_a = result[result["ticker"] == "sz000001"].sort_values("date")
        self.assertTrue(pd.isna(ticker_a.iloc[18]["ma_20"]))
        self.assertAlmostEqual(ticker_a.iloc[19]["ma_20"], 10.5)
        self.assertAlmostEqual(ticker_a.iloc[20]["ma_20"], 11.5)

    def test_close_above_ma_adds_boolean_column(self) -> None:
        df = self.make_sample()
        df = calc_ma(df, period=20)

        result = close_above_ma(df, period=20)

        self.assertIn("close_above_ma20", result.columns)
        ticker_a = result[result["ticker"] == "sz000001"].sort_values("date")
        self.assertTrue(pd.isna(ticker_a.iloc[18]["close_above_ma20"]))
        self.assertTrue(ticker_a.iloc[19]["close_above_ma20"])

    def test_calc_amount_ma_adds_grouped_amount_ma_20_column(self) -> None:
        df = self.make_sample()

        result = calc_amount_ma(df, period=20)

        self.assertIn("amount_ma_20", result.columns)

        ticker_a = result[result["ticker"] == "sz000001"].sort_values("date")
        expected = pd.Series([10000 + i * 10 for i in range(1, 21)], dtype=float).mean()
        self.assertTrue(pd.isna(ticker_a.iloc[18]["amount_ma_20"]))
        self.assertAlmostEqual(ticker_a.iloc[19]["amount_ma_20"], expected)


if __name__ == "__main__":
    unittest.main()
