from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.data.loader import load_components, load_factors
from src.settings import load_settings
from src.strategy.rules import TopMomentumRule


def _component_root(settings: dict) -> Path:
    return settings["paths"]["raw_data"] / "tushare" / f"{settings['strategy']['universe']}_components"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--date", required=True)
    parser.add_argument("--project-root", default=str(PROJECT_ROOT))
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    settings = load_settings(args.config, project_root=project_root)
    factor_root = settings["paths"]["processed_data"] / "factors" / "base"
    component_index = settings["data_source"]["component_index"]
    component_root = _component_root(settings)
    factor_data = load_factors(factor_root, start_date=args.date, end_date=args.date, factor_set="base")
    universe_data = load_components(component_root, start_date=args.date, end_date=args.date, index_code=component_index)

    rule = TopMomentumRule(settings["strategy"])
    weights = rule.generate_signals(args.date, factor_data, universe_data)
    selected_tickers = list(weights.keys())
    selected_rows = []
    if selected_tickers:
        selected = factor_data[(factor_data["date"] == args.date) & (factor_data["ticker"].isin(selected_tickers))].copy()
        selected = selected.sort_values("ret_20", ascending=False)
        selected_rows = json.loads(selected.to_json(orient="records", date_format="iso"))

    print(
        json.dumps(
            {
                "date": args.date,
                "weights": weights,
                "selected_tickers": selected_tickers,
                "selected_rows": selected_rows,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
