from __future__ import annotations

import math

import pandas as pd


def calc_metrics(equity_curve: pd.DataFrame, initial_capital: float) -> dict[str, float]:
    if equity_curve.empty:
        return {"final_equity": float(initial_capital), "total_return": 0.0, "max_drawdown": 0.0}
    curve = equity_curve.copy().sort_values("date")
    curve["running_max"] = curve["equity"].cummax()
    curve["drawdown"] = curve["equity"] / curve["running_max"] - 1.0
    final_equity = float(curve.iloc[-1]["equity"])
    total_return = final_equity / float(initial_capital) - 1.0
    max_drawdown = float(curve["drawdown"].min())
    return {
        "final_equity": final_equity,
        "total_return": float(total_return),
        "max_drawdown": max_drawdown,
    }
