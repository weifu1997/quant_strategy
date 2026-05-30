from __future__ import annotations

import pandas as pd

from .portfolio import equal_weight


class TopMomentumRule:
    def __init__(self, config: dict) -> None:
        self.topk = int(config["topk"])
        self.min_amount = float(config["min_amount_ma20"])
        self.require_above_ma = bool(config["require_close_above_ma20"])

    def generate_signals(
        self,
        date: pd.Timestamp,
        factor_data: pd.DataFrame,
        universe_data: pd.DataFrame | None = None,
    ) -> dict[str, float]:
        df = factor_data[factor_data["date"] == pd.Timestamp(date)].copy()
        if universe_data is not None and not universe_data.empty:
            allowed = universe_data[universe_data["date"] == pd.Timestamp(date)]["ticker"].tolist()
            df = df[df["ticker"].isin(allowed)]
        if self.require_above_ma:
            df = df[df["close_above_ma20"] == True]
        df = df[df["amount_ma_20"] >= self.min_amount]
        df = df.sort_values("ret_20", ascending=False)
        selected = df.head(self.topk)["ticker"].tolist()
        return equal_weight(selected)
