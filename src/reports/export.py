from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


def export_backtest_reports(report_root: str | Path, summary: dict, equity_curve: pd.DataFrame, trades: pd.DataFrame, positions: pd.DataFrame) -> None:
    report_root = Path(report_root)
    report_root.mkdir(parents=True, exist_ok=True)
    (report_root / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    equity_curve.to_csv(report_root / "equity_curve.csv", index=False)
    trades.to_csv(report_root / "trades.csv", index=False)
    positions.to_csv(report_root / "positions.csv", index=False)
