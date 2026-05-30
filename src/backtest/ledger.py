from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd


@dataclass
class Ledger:
    cash: float
    positions: dict[str, int] = field(default_factory=dict)
    position_rows: list[dict] = field(default_factory=list)
    trade_rows: list[dict] = field(default_factory=list)
    equity_rows: list[dict] = field(default_factory=list)

    def record_position(self, date: pd.Timestamp, ticker: str, shares: int, close: float) -> None:
        self.position_rows.append(
            {
                "date": pd.Timestamp(date),
                "ticker": ticker,
                "shares": int(shares),
                "close": float(close),
            }
        )

    def record_trade(self, date: pd.Timestamp, ticker: str, shares: int, price: float, side: str, cost: float) -> None:
        self.trade_rows.append(
            {
                "date": pd.Timestamp(date),
                "ticker": ticker,
                "shares": int(shares),
                "price": float(price),
                "side": side,
                "cost": float(cost),
            }
        )

    def record_equity(self, date: pd.Timestamp, equity: float, cash: float) -> None:
        self.equity_rows.append(
            {
                "date": pd.Timestamp(date),
                "equity": float(equity),
                "cash": float(cash),
            }
        )

    def to_frames(self) -> dict[str, pd.DataFrame]:
        return {
            "positions": pd.DataFrame(self.position_rows),
            "trades": pd.DataFrame(self.trade_rows),
            "equity_curve": pd.DataFrame(self.equity_rows),
        }
