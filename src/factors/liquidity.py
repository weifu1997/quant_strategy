import pandas as pd


def calc_amount_ma(df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
    result = df.copy()
    column = f"amount_ma_{period}"
    ordered = result.sort_values(["ticker", "date"]).copy()
    ordered[column] = (
        ordered.groupby("ticker", sort=False)["amount"]
        .transform(lambda s: s.rolling(window=period, min_periods=period).mean())
    )
    return ordered
