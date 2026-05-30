from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.backtest.engine import BacktestEngine
from src.backtest.metrics import calc_metrics
from src.data.loader import load_components, load_factors
from src.reports.export import export_backtest_reports
from src.settings import load_settings
from src.strategy.rules import TopMomentumRule


class UniverseFilteredStrategy:
    def __init__(self, base_strategy: TopMomentumRule, universe_data: pd.DataFrame) -> None:
        self.base_strategy = base_strategy
        self.universe_data = universe_data

    def generate_signals(self, date: pd.Timestamp, factor_data: pd.DataFrame) -> dict[str, float]:
        return self.base_strategy.generate_signals(date, factor_data, self.universe_data)


def _component_root(settings: dict) -> Path:
    return settings["paths"]["raw_data"] / "tushare" / f"{settings['strategy']['universe']}_components"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--start-date", required=True)
    parser.add_argument("--end-date", required=True)
    parser.add_argument("--project-root", default=str(PROJECT_ROOT))
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    settings = load_settings(args.config, project_root=project_root)
    factor_root = settings["paths"]["processed_data"] / "factors" / "base"
    report_root = settings["paths"]["report_output"]
    component_index = settings["data_source"]["component_index"]
    component_root = _component_root(settings)

    factor_data = load_factors(factor_root, start_date=args.start_date, end_date=args.end_date, factor_set="base")
    universe_data = load_components(component_root, start_date=args.start_date, end_date=args.end_date, index_code=component_index)
    prices = factor_data[["date", "ticker", "close", "is_tradable"]].copy()
    unique_dates = sorted(pd.Timestamp(date) for date in factor_data["date"].unique())
    rebalance_dates = unique_dates[1:] if len(unique_dates) > 1 else []

    strategy = UniverseFilteredStrategy(TopMomentumRule(settings["strategy"]), universe_data)
    engine = BacktestEngine(
        initial_capital=float(settings["backtest"]["initial_capital"]),
        commission_bps=float(settings["backtest"]["commission_bps"]),
        slippage_bps=float(settings["backtest"]["slippage_bps"]),
    )
    result = engine.run(
        prices=prices,
        factor_data=factor_data,
        strategy=strategy,
        rebalance_dates=rebalance_dates,
    )
    summary = calc_metrics(result["equity_curve"], initial_capital=float(settings["backtest"]["initial_capital"]))
    export_backtest_reports(report_root, summary, result["equity_curve"], result["trades"], result["positions"])

    print(
        json.dumps(
            {
                "summary": summary,
                "report_root": str(report_root),
                "rebalance_count": len(rebalance_dates),
                "trade_count": int(len(result["trades"])),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
