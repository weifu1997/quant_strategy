import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from scripts.fetch_data import main


class FetchDataScriptTests(unittest.TestCase):
    def test_fetch_data_script_writes_partitioned_dataset(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            config_dir = project_root / "config"
            config_dir.mkdir(parents=True)
            (config_dir / "base.yaml").write_text(
                "\n".join(
                    [
                        "data_source:",
                        "  provider: tushare_http",
                        "  http_url: http://example.com",
                        "  token: secret",
                        "  component_index: 000300.SH",
                        "  start_date: '2024-01-01'",
                        "  end_date: '2024-01-31'",
                        "strategy:",
                        "  universe: csi300",
                        "paths:",
                        "  raw_data: data/raw",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            config_path = config_dir / "server_ubuntu.yaml"
            config_path.write_text("runtime:\n  env: test\n", encoding="utf-8")

            sample = pd.DataFrame(
                [{"ts_code": "000001.SZ", "trade_date": "20240102", "open": 10, "high": 11, "low": 9, "close": 10.5, "vol": 900, "amount": 1800}]
            )

            stdout = io.StringIO()
            with patch("scripts.fetch_data.PROJECT_ROOT", project_root):
                with patch("scripts.fetch_data.TushareClient") as client_cls:
                    client = client_cls.return_value
                    client.get_daily.return_value = sample
                    client.get_suspend_history.return_value = pd.DataFrame(
                        [
                            {"date": pd.Timestamp("2024-01-02"), "ticker": "sz000001", "suspend_type": "S", "suspend_timing": pd.NA},
                        ]
                    )
                    with patch("sys.argv", ["fetch_data.py", "--config", str(config_path), "--ts-code", "000001.SZ"]):
                        with redirect_stdout(stdout):
                            exit_code = main()

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["rows"], 1)
            self.assertTrue((project_root / "data" / "raw" / "year=2024" / "daily.parquet").exists())
            self.assertTrue((project_root / "data" / "raw" / "tushare" / "suspends" / "year=2024" / "suspend.parquet").exists())
            written = pd.read_parquet(project_root / "data" / "raw" / "year=2024" / "daily.parquet")
            self.assertFalse(written.iloc[0]["is_tradable"])

    def test_fetch_data_script_fetches_component_index_batch(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            config_dir = project_root / "config"
            config_dir.mkdir(parents=True)
            (config_dir / "base.yaml").write_text(
                "\n".join(
                    [
                        "data_source:",
                        "  provider: tushare_http",
                        "  http_url: http://example.com",
                        "  token: secret",
                        "  component_index: 000300.SH",
                        "  start_date: '2024-01-01'",
                        "  end_date: '2024-01-31'",
                        "strategy:",
                        "  universe: csi300",
                        "paths:",
                        "  raw_data: data/raw",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            config_path = config_dir / "server_ubuntu.yaml"
            config_path.write_text("runtime:\n  env: test\n", encoding="utf-8")

            sample_a = pd.DataFrame(
                [{"ts_code": "000001.SZ", "trade_date": "20240102", "open": 10, "high": 11, "low": 9, "close": 10.5, "vol": 900, "amount": 1800, "suspend_type": None}]
            )
            sample_b = pd.DataFrame(
                [{"ts_code": "600000.SH", "trade_date": "20240102", "open": 8, "high": 9, "low": 7.5, "close": 8.4, "vol": 700, "amount": 1400, "suspend_type": "S"}]
            )

            stdout = io.StringIO()
            with patch("scripts.fetch_data.PROJECT_ROOT", project_root):
                with patch("scripts.fetch_data.TushareClient") as client_cls:
                    client = client_cls.return_value
                    client.get_index_components.return_value = ["000001.SZ", "300001.SZ", "688001.SH", "430001.BJ", "600145.SH"]
                    client.get_stock_basic.return_value = pd.DataFrame(
                        [
                            {"ticker": "sz000001", "name": "平安银行"},
                            {"ticker": "sz300001", "name": "特锐德"},
                            {"ticker": "sh688001", "name": "华兴源创"},
                            {"ticker": "bj430001", "name": "北交样本"},
                            {"ticker": "sh600145", "name": "*ST新亿"},
                        ]
                    )
                    client.filter_excluded_tickers.return_value = ["sz000001"]
                    client.get_index_components_history.return_value = pd.DataFrame(
                        [
                            {"date": pd.Timestamp("2024-01-31"), "index_code": "000300.SH", "ticker": "sz000001", "weight": 0.12},
                        ]
                    )
                    client.get_suspend_history.return_value = pd.DataFrame(
                        [
                            {"date": pd.Timestamp("2024-01-02"), "ticker": "sh600000", "suspend_type": "S", "suspend_timing": pd.NA},
                        ]
                    )
                    client.get_daily.side_effect = [sample_a]
                    with patch("sys.argv", ["fetch_data.py", "--config", str(config_path), "--component-index", "000300.SH"]):
                        with redirect_stdout(stdout):
                            exit_code = main()

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["rows"], 1)
            self.assertEqual(payload["tickers"], ["000001.SZ"])
            written = pd.read_parquet(project_root / "data" / "raw" / "year=2024" / "daily.parquet")
            self.assertEqual(sorted(written["ticker"].tolist()), ["sz000001"])
            components = pd.read_parquet(project_root / "data" / "raw" / "tushare" / "csi300_components" / "year=2024" / "components.parquet")
            self.assertEqual(sorted(components["ticker"].tolist()), ["sz000001"])
            self.assertEqual(client.get_daily.call_count, 1)


if __name__ == "__main__":
    unittest.main()
