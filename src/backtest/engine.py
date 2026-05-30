from __future__ import annotations

import math
from collections.abc import Sequence

import pandas as pd

from .ledger import Ledger


class BacktestEngine:
    def __init__(self, initial_capital: float, commission_bps: float, slippage_bps: float) -> None:
        self.initial_capital = float(initial_capital)
        self.commission_rate = float(commission_bps) / 10000.0
        self.slippage_rate = float(slippage_bps) / 10000.0

    def run(
        self,
        prices: pd.DataFrame,
        factor_data: pd.DataFrame,
        strategy,
        rebalance_dates: Sequence[pd.Timestamp],
    ) -> dict[str, pd.DataFrame]:
        ledger = Ledger(cash=self.initial_capital)
        rebalance_set = {pd.Timestamp(d) for d in rebalance_dates}
        ordered = prices.copy()
        ordered["date"] = pd.to_datetime(ordered["date"])
        ordered = ordered.sort_values(["date", "ticker"]).reset_index(drop=True)
        trading_dates = [pd.Timestamp(d) for d in ordered["date"].drop_duplicates().tolist()]
        previous_date_map = {trading_dates[idx]: trading_dates[idx - 1] for idx in range(1, len(trading_dates))}

        for date, daily_prices in ordered.groupby("date", sort=True):
            date = pd.Timestamp(date)
            if date in rebalance_set and date in previous_date_map:
                signal_date = previous_date_map[date]
                self._rebalance(signal_date, date, daily_prices, factor_data, strategy, ledger)
            equity = self._mark_to_market(daily_prices, ledger)
            ledger.record_equity(date, equity=equity, cash=ledger.cash)
            for _, row in daily_prices.iterrows():
                ticker = row["ticker"]
                shares = ledger.positions.get(ticker, 0)
                if shares > 0:
                    ledger.record_position(date, ticker=ticker, shares=shares, close=float(row["close"]))
        return ledger.to_frames()

    def _rebalance(
        self,
        signal_date: pd.Timestamp,
        execution_date: pd.Timestamp,
        daily_prices: pd.DataFrame,
        factor_data: pd.DataFrame,
        strategy,
        ledger: Ledger,
    ) -> None:
        target_weights = strategy.generate_signals(signal_date, factor_data)
        price_map = {row["ticker"]: float(row["close"]) for _, row in daily_prices.iterrows()}
        tradable_map = {
            row["ticker"]: bool(row["is_tradable"]) if "is_tradable" in daily_prices.columns and not pd.isna(row.get("is_tradable")) else True
            for _, row in daily_prices.iterrows()
        }
        portfolio_value = self._mark_to_market(daily_prices, ledger)

        target_shares: dict[str, int] = {}
        for ticker, weight in target_weights.items():
            price = price_map.get(ticker)
            if price is None or price <= 0 or not tradable_map.get(ticker, True):
                continue
            gross_unit_price = price * (1.0 + self.slippage_rate)
            board_lot_price = gross_unit_price * 100.0
            lots = int((portfolio_value * float(weight)) // board_lot_price)
            shares = lots * 100
            if shares > 0:
                target_shares[ticker] = shares

        current_tickers = {ticker for ticker, shares in ledger.positions.items() if shares > 0}
        all_tickers = sorted(current_tickers | set(target_shares.keys()))

        sell_orders: list[tuple[str, int, float, float]] = []
        for ticker in all_tickers:
            current_shares = ledger.positions.get(ticker, 0)
            desired_shares = target_shares.get(ticker, 0)
            shares_to_sell = max(current_shares - desired_shares, 0)
            price = price_map.get(ticker)
            if price is None or shares_to_sell <= 0 or not tradable_map.get(ticker, True):
                continue
            notional = shares_to_sell * price
            trading_cost = notional * (self.commission_rate + self.slippage_rate)
            sell_orders.append((ticker, shares_to_sell, price, trading_cost))

        for ticker, shares, price, trading_cost in sell_orders:
            notional = shares * price
            ledger.cash += notional - trading_cost
            ledger.positions[ticker] = ledger.positions.get(ticker, 0) - shares
            ledger.record_trade(execution_date, ticker=ticker, shares=shares, price=price, side="sell", cost=trading_cost)

        buy_orders: list[tuple[str, int, float, float]] = []
        buy_notional_total = 0.0
        for ticker in sorted(target_shares.keys()):
            desired_shares = target_shares[ticker]
            current_shares = ledger.positions.get(ticker, 0)
            shares_to_buy = max(desired_shares - current_shares, 0)
            price = price_map.get(ticker)
            if price is None or shares_to_buy <= 0:
                continue
            notional = shares_to_buy * price
            trading_cost = notional * (self.commission_rate + self.slippage_rate)
            buy_orders.append((ticker, shares_to_buy, price, trading_cost))
            buy_notional_total += notional + trading_cost

        if buy_notional_total > ledger.cash and buy_notional_total > 0:
            scale = ledger.cash / buy_notional_total
            scaled_orders: list[tuple[str, int, float, float]] = []
            for ticker, shares, price, _ in buy_orders:
                scaled_shares = int(math.floor((shares * scale) / 100.0)) * 100
                if scaled_shares <= 0:
                    continue
                notional = scaled_shares * price
                trading_cost = notional * (self.commission_rate + self.slippage_rate)
                scaled_orders.append((ticker, scaled_shares, price, trading_cost))
            buy_orders = scaled_orders

        for ticker, shares, price, trading_cost in buy_orders:
            notional = shares * price
            ledger.cash -= notional + trading_cost
            ledger.positions[ticker] = ledger.positions.get(ticker, 0) + shares
            ledger.record_trade(execution_date, ticker=ticker, shares=shares, price=price, side="buy", cost=trading_cost)

        for ticker, shares in list(ledger.positions.items()):
            if shares <= 0:
                ledger.positions.pop(ticker, None)

    def _mark_to_market(self, daily_prices: pd.DataFrame, ledger: Ledger) -> float:
        price_map = {row["ticker"]: float(row["close"]) for _, row in daily_prices.iterrows()}
        position_value = 0.0
        for ticker, shares in ledger.positions.items():
            if ticker in price_map:
                position_value += shares * price_map[ticker]
        return ledger.cash + position_value
