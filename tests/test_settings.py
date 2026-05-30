import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.settings import load_settings


class SettingsTests(unittest.TestCase):
    def test_load_settings_merges_base_and_env_and_resolves_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            config_dir = project_root / "config"
            config_dir.mkdir(parents=True)
            (config_dir / "base.yaml").write_text(
                "\n".join(
                    [
                        "project:",
                        "  name: quant_strategy",
                        "data_source:",
                        "  token: ${TUSHARE_TOKEN}",
                        "paths:",
                        "  raw_data: data/raw",
                        "  processed_data: data/processed",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            env_config = config_dir / "server_ubuntu.yaml"
            env_config.write_text(
                "\n".join(
                    [
                        "runtime:",
                        "  env: server_ubuntu",
                        "paths:",
                        "  report_output: data/reports",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            with patch.dict(os.environ, {"TUSHARE_TOKEN": "secret-token"}, clear=False):
                settings = load_settings(env_config, project_root=project_root)

            self.assertEqual(settings["project"]["name"], "quant_strategy")
            self.assertEqual(settings["runtime"]["env"], "server_ubuntu")
            self.assertEqual(settings["data_source"]["token"], "secret-token")
            self.assertEqual(settings["paths"]["raw_data"], project_root / "data" / "raw")
            self.assertEqual(settings["paths"]["processed_data"], project_root / "data" / "processed")
            self.assertEqual(settings["paths"]["report_output"], project_root / "data" / "reports")

    def test_load_settings_raises_when_required_env_var_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            config_dir = project_root / "config"
            config_dir.mkdir(parents=True)
            (config_dir / "base.yaml").write_text(
                "data_source:\n  token: ${TUSHARE_TOKEN}\n",
                encoding="utf-8",
            )
            env_config = config_dir / "server_ubuntu.yaml"
            env_config.write_text("runtime:\n  env: server_ubuntu\n", encoding="utf-8")

            with patch.dict(os.environ, {}, clear=True):
                with self.assertRaises(ValueError):
                    load_settings(env_config, project_root=project_root)


if __name__ == "__main__":
    unittest.main()
