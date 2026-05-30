import unittest

import pandas as pd

from src.data.normalize import normalize_ohlcv


class NormalizeTests(unittest.TestCase):
    def test_normalize_ohlcv_renames_and_sorts(self) -> None:
        raw = pd.DataFrame(
            [
                {"ts_code": "000001.SZ", "trade_date": "20240103", "open": 11, "high": 12, "low": 10, "close": 11.5, "vol": 1000, "amount": 2000, "suspend_type": "S"},
                {"ts_code": "000001.SZ", "trade_date": "20240102", "open": 10, "high": 11, "low": 9, "close": 10.5, "vol": 900, "amount": 1800, "suspend_type": None},
                {"ts_code": "600000.SH", "trade_date": "20240102", "open": 8, "high": 9, "low": 7.5, "close": 8.4, "vol": 700, "amount": 1400, "suspend_type": ""},
            ]
        )

        df = normalize_ohlcv(raw)

        self.assertEqual(list(df.columns), ["date", "ticker", "open", "high", "low", "close", "volume", "amount", "is_tradable"])
        self.assertEqual(df.iloc[0]["ticker"], "sh600000")
        self.assertEqual(df.iloc[1]["ticker"], "sz000001")
        self.assertEqual(df.iloc[1]["date"].strftime("%Y-%m-%d"), "2024-01-02")
        self.assertEqual(df.iloc[2]["date"].strftime("%Y-%m-%d"), "2024-01-03")
        self.assertTrue(df.iloc[0]["is_tradable"])
        self.assertTrue(df.iloc[1]["is_tradable"])
        self.assertFalse(df.iloc[2]["is_tradable"])

    def test_normalize_ohlcv_uses_suspend_table_when_field_missing(self) -> None:
        raw = pd.DataFrame(
            [
                {"ts_code": "000001.SZ", "trade_date": "20240102", "open": 10, "high": 11, "low": 9, "close": 10.5, "vol": 900, "amount": 1800},
                {"ts_code": "600000.SH", "trade_date": "20240102", "open": 8, "high": 9, "low": 7.5, "close": 8.4, "vol": 700, "amount": 1400},
            ]
        )
        suspends = pd.DataFrame(
            [
                {"date": pd.Timestamp("2024-01-02"), "ticker": "sz000001", "suspend_type": "S", "suspend_timing": pd.NA},
            ]
        )

        df = normalize_ohlcv(raw, suspends)

        self.assertFalse(df.loc[df["ticker"] == "sz000001", "is_tradable"].iloc[0])
        self.assertTrue(df.loc[df["ticker"] == "sh600000", "is_tradable"].iloc[0])

    def test_normalize_ohlcv_returns_empty_contract_for_empty_input(self) -> None:
        df = normalize_ohlcv(pd.DataFrame())
        self.assertEqual(list(df.columns), ["date", "ticker", "open", "high", "low", "close", "volume", "amount", "is_tradable"])
        self.assertEqual(len(df), 0)


if __name__ == "__main__":
    unittest.main()
