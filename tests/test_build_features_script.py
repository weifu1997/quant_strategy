import json
import subprocess
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.data.loader import save_daily_partitions


class BuildFeaturesScriptTests(unittest.TestCase):
    def test_build_features_script_writes_base_factor_partitions(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            daily_root = project_root / "data" / "processed" / "daily"
            factor_root = project_root / "data" / "processed" / "factors" / "base"
            (project_root / "config").mkdir(parents=True, exist_ok=True)
            (project_root / "scripts").mkdir(parents=True, exist_ok=True)

            df = pd.DataFrame(
                [
                    {
                        "date": date,
                        "ticker": "sz000001",
                        "open": float(i),
                        "high": float(i) + 0.5,
                        "low": float(i) - 0.5,
                        "close": float(i),
                        "volume": float(1000 + i),
                        "amount": float(10000 + i * 10),
                        "is_tradable": True,
                    }
                    for i, date in enumerate(pd.date_range("2024-01-01", periods=25, freq="D"), start=1)
                ]
            )
            save_daily_partitions(df, daily_root)

            (project_root / "config" / "base.yaml").write_text(
                """
project:
  name: quant_strategy
paths:
  raw_data: data/raw
  processed_data: data/processed
  report_output: data/reports
""".strip()
                + "\n",
                encoding="utf-8",
            )
            (project_root / "config" / "server_ubuntu.yaml").write_text("{}\n", encoding="utf-8")

            script_path = Path("/root/project/quant_strategy/scripts/build_features.py")
            command = [
                "/root/project/quant_strategy/.venv/bin/python",
                str(script_path),
                "--config",
                str(project_root / "config" / "server_ubuntu.yaml"),
                "--start-date",
                "2024-01-01",
                "--end-date",
                "2024-01-31",
                "--project-root",
                str(project_root),
            ]
            completed = subprocess.run(command, capture_output=True, text=True, check=True)
            payload = json.loads(completed.stdout)

            self.assertEqual(payload["factor_set"], "base")
            self.assertEqual(payload["rows"], 25)
            self.assertEqual(payload["files_written"], 1)
            output_file = factor_root / "year=2024" / "factors.parquet"
            self.assertTrue(output_file.exists())

            written = pd.read_parquet(output_file)
            self.assertIn("ret_20", written.columns)
            self.assertIn("ma_20", written.columns)
            self.assertIn("close_above_ma20", written.columns)
            self.assertIn("amount_ma_20", written.columns)


if __name__ == "__main__":
    unittest.main()
