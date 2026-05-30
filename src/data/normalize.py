from __future__ import annotations

import pandas as pd


_TICKER_SUFFIX_MAP = {
    "SH": "sh",
    "SZ": "sz",
    "BJ": "bj",
}


def _normalize_ticker(ts_code: str) -> str:
    code, suffix = ts_code.split(".")
    return f"{_TICKER_SUFFIX_MAP[suffix]}{code}"


def normalize_ohlcv(df: pd.DataFrame, suspends: pd.DataFrame | None = None) -> pd.DataFrame:
    renamed = df.rename(columns={"ts_code": "ticker", "trade_date": "date", "vol": "volume"}).copy()
    if renamed.empty:
        return pd.DataFrame(columns=["date", "ticker", "open", "high", "low", "close", "volume", "amount", "is_tradable"])
    renamed["ticker"] = renamed["ticker"].map(_normalize_ticker)
    renamed["date"] = pd.to_datetime(renamed["date"], format="%Y%m%d")
    if "suspend_type" in renamed.columns:
        suspend_type = renamed["suspend_type"]
        renamed["is_tradable"] = suspend_type.isna() | (suspend_type == "")
    elif suspends is not None and not suspends.empty:
        suspend_keys = set(
            zip(pd.to_datetime(suspends["date"]).tolist(), suspends["ticker"].astype(str).tolist())
        )
        renamed["is_tradable"] = [
            (date, ticker) not in suspend_keys
            for date, ticker in zip(renamed["date"].tolist(), renamed["ticker"].astype(str).tolist())
        ]
    else:
        # This proxy currently does not reliably return a tradability field.
        # Treat missing suspend metadata as unknown, and keep the contract explicit upstream.
        renamed["is_tradable"] = True
    columns = ["date", "ticker", "open", "high", "low", "close", "volume", "amount", "is_tradable"]
    renamed = renamed[columns]
    return renamed.sort_values(["ticker", "date"]).reset_index(drop=True)
