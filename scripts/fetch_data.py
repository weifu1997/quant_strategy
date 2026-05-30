from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.data.loader import save_component_partitions, save_daily_partitions, save_suspend_partitions
from src.data.normalize import normalize_ohlcv
from src.data.tushare_client import TushareClient, _normalize_component_ticker
from src.settings import load_settings


def _resolve_tickers(args: argparse.Namespace, source: dict, client: TushareClient) -> list[str]:
    if args.ts_code:
        return [args.ts_code]
    component_index = args.component_index or source.get("component_index")
    if component_index is None:
        raise ValueError("component_index is required when --ts-code is not provided")
    tickers = client.get_index_components(component_index)
    stock_basic = client.get_stock_basic()
    filtered_tickers = client.filter_excluded_tickers([_normalize_component_ticker(ts_code) for ts_code in tickers], stock_basic)
    normalized_to_ts = {_normalize_component_ticker(ts_code): ts_code for ts_code in tickers}
    return [normalized_to_ts[ticker] for ticker in filtered_tickers]


def _component_dir_name(settings: dict) -> str:
    return f"{settings.get('strategy', {}).get('universe', 'components')}_components"


def _component_output_root(raw_data_root: Path, settings: dict) -> Path:
    return raw_data_root / "tushare" / _component_dir_name(settings)


def _suspend_output_root(raw_data_root: Path) -> Path:
    return raw_data_root / "tushare" / "suspends"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--ts-code")
    parser.add_argument("--component-index")
    args = parser.parse_args()

    if bool(args.ts_code) == bool(args.component_index):
        parser.error("exactly one of --ts-code or --component-index is required")

    settings = load_settings(args.config, project_root=PROJECT_ROOT)
    source = settings["data_source"]
    client = TushareClient(http_url=source["http_url"], token=source["token"])
    tickers = _resolve_tickers(args, source, client)
    start_date = str(source["start_date"]).replace("-", "")
    end_date = str(source["end_date"]).replace("-", "") if source.get("end_date") else "20991231"
    frames: list[pd.DataFrame] = []
    for ts_code in tickers:
        frames.append(
            client.get_daily(
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date,
            )
        )
    suspend_history = client.get_suspend_history(start_date, end_date, None if not args.ts_code else tickers[0])
    raw = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    normalized = normalize_ohlcv(raw, suspend_history)
    output_root = settings["paths"]["raw_data"]
    written = save_daily_partitions(normalized, output_root)
    suspend_paths = save_suspend_partitions(suspend_history, _suspend_output_root(output_root))
    component_written: list[str] = []
    if not args.ts_code:
        component_index = args.component_index or source["component_index"]
        component_history = client.get_index_components_history(component_index, start_date, end_date)
        filtered_component_history = component_history[component_history["ticker"].isin([_normalize_component_ticker(ts_code) for ts_code in tickers])].copy()
        component_paths = save_component_partitions(filtered_component_history, _component_output_root(output_root, settings))
        component_written = [str(path) for path in component_paths]
    print(
        json.dumps(
            {
                "rows": int(len(normalized)),
                "tickers": tickers,
                "written_paths": [str(p) for p in written],
                "suspend_written_paths": [str(path) for path in suspend_paths],
                "component_written_paths": component_written,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
