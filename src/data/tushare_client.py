from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd
import requests
import re


_COMPONENT_TICKER_SUFFIX_MAP = {
    "SH": "sh",
    "SZ": "sz",
    "BJ": "bj",
}


def _normalize_component_ticker(ts_code: str) -> str:
    code, suffix = ts_code.split(".")
    return f"{_COMPONENT_TICKER_SUFFIX_MAP[suffix]}{code}"


@dataclass
class TushareClient:
    http_url: str
    token: str
    timeout: int = 30

    def _post(self, api_name: str, params: dict[str, Any], fields: list[str]) -> pd.DataFrame:
        response = requests.post(
            self.http_url,
            json={
                "api_name": api_name,
                "token": self.token,
                "params": params,
                "fields": ",".join(fields),
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("code") != 0:
            raise ValueError(payload.get("msg") or f"tushare api error: {payload.get('code')}")
        data = payload.get("data") or {}
        return pd.DataFrame(data.get("items", []), columns=data.get("fields", []))

    def get_daily(self, ts_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        fields = ["ts_code", "trade_date", "open", "high", "low", "close", "vol", "amount", "suspend_type"]
        return self._post(
            api_name="daily",
            params={"ts_code": ts_code, "start_date": start_date, "end_date": end_date},
            fields=fields,
        )

    def get_index_components(self, index_code: str) -> list[str]:
        fields = ["index_code", "con_code", "trade_date"]
        df = self._post(
            api_name="index_weight",
            params={"index_code": index_code},
            fields=fields,
        )
        if df.empty:
            return []
        return sorted(df["con_code"].dropna().astype(str).drop_duplicates().tolist())

    def get_stock_basic(self) -> pd.DataFrame:
        fields = ["ts_code", "name"]
        df = self._post(
            api_name="stock_basic",
            params={"list_status": "L", "market": "主板"},
            fields=fields,
        )
        if df.empty:
            return pd.DataFrame(columns=["ticker", "name"])
        renamed = df.rename(columns={"ts_code": "ticker"}).copy()
        renamed["ticker"] = renamed["ticker"].map(_normalize_component_ticker)
        return renamed[["ticker", "name"]].sort_values(by=["ticker"]).reset_index(drop=True)

    def filter_excluded_tickers(self, tickers: list[str], stock_basic: pd.DataFrame) -> list[str]:
        if stock_basic.empty:
            return tickers
        meta = stock_basic[stock_basic["ticker"].isin(tickers)].copy()
        meta["name"] = pd.Series(meta["name"], index=meta.index).fillna("").astype(str)
        meta = meta[~meta["name"].str.contains(r"(?:^\*?ST|ST)", regex=True)]
        keep = set(meta["ticker"].tolist())
        return [ticker for ticker in tickers if ticker in keep]

    def get_index_components_history(self, index_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        fields = ["index_code", "con_code", "trade_date", "weight"]
        df = self._post(
            api_name="index_weight",
            params={"index_code": index_code, "start_date": start_date, "end_date": end_date},
            fields=fields,
        )
        if df.empty:
            return pd.DataFrame(columns=["date", "index_code", "ticker", "weight"])
        renamed = df.rename(columns={"trade_date": "date", "con_code": "ticker"}).copy()
        renamed["date"] = pd.to_datetime(renamed["date"], format="%Y%m%d")
        renamed["ticker"] = renamed["ticker"].map(_normalize_component_ticker)
        renamed["weight"] = renamed["weight"].astype(float)
        return renamed[["date", "index_code", "ticker", "weight"]].sort_values(["date", "ticker"]).reset_index(drop=True)

    def get_suspend_history(self, start_date: str, end_date: str, ts_code: str | None = None) -> pd.DataFrame:
        fields = ["ts_code", "trade_date", "suspend_type", "suspend_timing"]
        params = {"start_date": start_date, "end_date": end_date}
        if ts_code is not None:
            params["ts_code"] = ts_code
        df = self._post(
            api_name="suspend_d",
            params=params,
            fields=fields,
        )
        if df.empty:
            return pd.DataFrame(columns=["date", "ticker", "suspend_type", "suspend_timing"])
        renamed = df.rename(columns={"trade_date": "date", "ts_code": "ticker"}).copy()
        renamed["date"] = pd.to_datetime(renamed["date"], format="%Y%m%d")
        renamed["ticker"] = renamed["ticker"].map(_normalize_component_ticker)
        return renamed[["date", "ticker", "suspend_type", "suspend_timing"]].sort_values(["date", "ticker"]).reset_index(drop=True)
