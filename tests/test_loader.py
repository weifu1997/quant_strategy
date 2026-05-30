import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.data.loader import (
    load_components,
    load_daily,
    load_factors,
    load_suspends,
    save_component_partitions,
    save_daily_partitions,
    save_factor_partitions,
    save_suspend_partitions,
)


class LoaderTests(unittest.TestCase):
    def test_save_daily_partitions_and_load_daily(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            df = pd.DataFrame(
                [
                    {"date": pd.Timestamp("2023-12-29"), "ticker": "sh600000", "open": 8, "high": 9, "low": 7.5, "close": 8.4, "volume": 700, "amount": 1400, "is_tradable": True},
                    {"date": pd.Timestamp("2024-01-02"), "ticker": "sz000001", "open": 10, "high": 11, "low": 9, "close": 10.5, "volume": 900, "amount": 1800, "is_tradable": False},
                ]
            )

            written = save_daily_partitions(df, root)
            self.assertEqual(len(written), 2)
            self.assertTrue((root / "year=2023" / "daily.parquet").exists())
            self.assertTrue((root / "year=2024" / "daily.parquet").exists())

            loaded = load_daily(root, start_date="2024-01-01", end_date="2024-01-31")
            self.assertEqual(len(loaded), 1)
            self.assertEqual(loaded.iloc[0]["ticker"], "sz000001")

    def test_save_factor_partitions_and_load_factors(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            df = pd.DataFrame(
                [
                    {
                        "date": pd.Timestamp("2024-01-02"),
                        "ticker": "sz000001",
                        "close": 10.5,
                        "ret_20": 0.10,
                        "ma_20": 9.9,
                        "close_above_ma20": True,
                        "amount_ma_20": 2000.0,
                    },
                    {
                        "date": pd.Timestamp("2024-01-03"),
                        "ticker": "sh600000",
                        "close": 8.4,
                        "ret_20": 0.05,
                        "ma_20": 8.1,
                        "close_above_ma20": True,
                        "amount_ma_20": 1500.0,
                    },
                ]
            )

            written = save_factor_partitions(df, root)
            self.assertEqual(len(written), 1)
            self.assertTrue((root / "year=2024" / "factors.parquet").exists())

            loaded = load_factors(root, start_date="2024-01-01", end_date="2024-01-31")
            self.assertEqual(len(loaded), 2)
            self.assertEqual(
                loaded.columns.tolist(),
                ["date", "ticker", "close", "ret_20", "ma_20", "close_above_ma20", "amount_ma_20", "is_tradable"],
            )

    def test_save_component_partitions_and_load_components(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            df = pd.DataFrame(
                [
                    {"date": pd.Timestamp("2024-01-31"), "index_code": "000300.SH", "ticker": "sz000001", "weight": 0.12},
                    {"date": pd.Timestamp("2024-02-29"), "index_code": "000300.SH", "ticker": "sh600000", "weight": 0.08},
                ]
            )

            written = save_component_partitions(df, root)
            self.assertEqual(len(written), 1)
            self.assertTrue((root / "year=2024" / "components.parquet").exists())

            loaded = load_components(root, start_date="2024-01-01", end_date="2024-01-31", index_code="000300.SH")
            self.assertEqual(len(loaded), 1)
            self.assertEqual(loaded.iloc[0]["ticker"], "sz000001")

    def test_save_suspend_partitions_and_load_suspends(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            df = pd.DataFrame(
                [
                    {"date": pd.Timestamp("2024-01-02"), "ticker": "sz000001", "suspend_type": "S", "suspend_timing": pd.NA},
                    {"date": pd.Timestamp("2024-02-01"), "ticker": "sh600000", "suspend_type": "R", "suspend_timing": pd.NA},
                ]
            )

            written = save_suspend_partitions(df, root)
            self.assertEqual(len(written), 1)
            self.assertTrue((root / "year=2024" / "suspend.parquet").exists())

            loaded = load_suspends(root, start_date="2024-01-01", end_date="2024-01-31")
            self.assertEqual(len(loaded), 1)
            self.assertEqual(loaded.iloc[0]["ticker"], "sz000001")


if __name__ == "__main__":
    unittest.main()
