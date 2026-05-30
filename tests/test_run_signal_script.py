import json
import subprocess
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.data.loader import save_component_partitions, save_factor_partitions


class RunSignalScriptTests(unittest.TestCase):
    def test_run_signal_script_outputs_target_weights(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            factor_root = project_root / "data" / "processed" / "factors" / "base"
            (project_root / "config").mkdir(parents=True, exist_ok=True)

            factors = pd.DataFrame(
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
                ]
            )
            save_factor_partitions(factors, factor_root)
            component_root = project_root / "data" / "raw" / "tushare" / "csi300_components"
            components = pd.DataFrame(
                [
                    {"date": pd.Timestamp("2024-01-31"), "index_code": "000300.SH", "ticker": "sh600000", "weight": 0.08},
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
paths:
  raw_data: data/raw
  processed_data: data/processed
  report_output: data/reports
""".strip()
                + "\n",
                encoding="utf-8",
            )
            (project_root / "config" / "server_ubuntu.yaml").write_text("{}\n", encoding="utf-8")

            script_path = Path("/root/project/quant_strategy/scripts/run_signal.py")
            command = [
                "/root/project/quant_strategy/.venv/bin/python",
                str(script_path),
                "--config",
                str(project_root / "config" / "server_ubuntu.yaml"),
                "--date",
                "2024-01-31",
                "--project-root",
                str(project_root),
            ]
            completed = subprocess.run(command, capture_output=True, text=True, check=True)
            payload = json.loads(completed.stdout)

            self.assertEqual(payload["date"], "2024-01-31")
            self.assertEqual(payload["weights"], {"sh600000": 1.0})
            self.assertEqual(payload["selected_tickers"], ["sh600000"])
            self.assertEqual(len(payload["selected_rows"]), 1)
            self.assertEqual(payload["selected_rows"][0]["ticker"], "sh600000")


if __name__ == "__main__":
    unittest.main()
