import json
import subprocess
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.data.loader import save_component_partitions, save_factor_partitions


class RunBacktestScriptTests(unittest.TestCase):
    def test_run_backtest_script_outputs_summary_and_reports(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            factor_root = project_root / "data" / "processed" / "factors" / "base"
            report_root = project_root / "data" / "reports"
            (project_root / "config").mkdir(parents=True, exist_ok=True)

            factors = pd.DataFrame(
                [
                    {
                        "date": pd.Timestamp("2024-01-30"),
                        "ticker": "sz000001",
                        "close": 9.5,
                        "ret_20": 0.31,
                        "ma_20": 9.4,
                        "close_above_ma20": True,
                        "amount_ma_20": 95_000_000.0,
                    },
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
                        "date": pd.Timestamp("2024-02-01"),
                        "ticker": "sz000001",
                        "close": 11.0,
                        "ret_20": 0.25,
                        "ma_20": 9.7,
                        "close_above_ma20": True,
                        "amount_ma_20": 110_000_000.0,
                    },
                    {
                        "date": pd.Timestamp("2024-02-02"),
                        "ticker": "sz000001",
                        "close": 12.0,
                        "ret_20": 0.22,
                        "ma_20": 10.0,
                        "close_above_ma20": True,
                        "amount_ma_20": 120_000_000.0,
                    },
                ]
            )
            save_factor_partitions(factors, factor_root)
            component_root = project_root / "data" / "raw" / "tushare" / "csi300_components"
            components = pd.DataFrame(
                [
                    {"date": pd.Timestamp("2024-01-31"), "index_code": "000300.SH", "ticker": "sz000001", "weight": 0.12},
                    {"date": pd.Timestamp("2024-02-01"), "index_code": "000300.SH", "ticker": "sz000001", "weight": 0.10},
                ]
            )
            save_component_partitions(components, component_root)

            (project_root / "config" / "base.yaml").write_text(
                """
project:
  name: quant_strategy
data_source:
  component_index: 000300.SH
strategy:
  universe: csi300
  topk: 20
  min_amount_ma20: 50000000
  require_close_above_ma20: true
backtest:
  initial_capital: 100000
  commission_bps: 0
  slippage_bps: 0
paths:
  raw_data: data/raw
  processed_data: data/processed
  report_output: data/reports
""".strip()
                + "\n",
                encoding="utf-8",
            )
            (project_root / "config" / "server_ubuntu.yaml").write_text("{}\n", encoding="utf-8")

            script_path = Path("/root/project/quant_strategy/scripts/run_backtest.py")
            command = [
                "/root/project/quant_strategy/.venv/bin/python",
                str(script_path),
                "--config",
                str(project_root / "config" / "server_ubuntu.yaml"),
                "--start-date",
                "2024-01-31",
                "--end-date",
                "2024-02-02",
                "--project-root",
                str(project_root),
            ]
            completed = subprocess.run(command, capture_output=True, text=True, check=True)
            payload = json.loads(completed.stdout)

            self.assertGreater(payload["summary"]["final_equity"], 100000)
            self.assertEqual(payload["rebalance_count"], 2)
            self.assertGreaterEqual(payload["trade_count"], 1)
            summary = json.loads((report_root / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["final_equity"], payload["summary"]["final_equity"])
            trades = pd.read_csv(report_root / "trades.csv")
            self.assertEqual(sorted(trades["ticker"].unique().tolist()), ["sz000001"])
            self.assertTrue((report_root / "summary.json").exists())
            self.assertTrue((report_root / "equity_curve.csv").exists())
            self.assertTrue((report_root / "trades.csv").exists())
            self.assertTrue((report_root / "positions.csv").exists())


if __name__ == "__main__":
    unittest.main()
