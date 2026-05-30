from __future__ import annotations


def equal_weight(tickers: list[str]) -> dict[str, float]:
    if not tickers:
        return {}
    weight = 1.0 / len(tickers)
    return {ticker: weight for ticker in tickers}
