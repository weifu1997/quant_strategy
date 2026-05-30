import pandas as pd


def calc_ret(df: pd.DataFrame, period: int) -> pd.DataFrame:
    result = df.copy()
    column = f"ret_{period}"
    result[column] = (
        result.sort_values(["ticker", "date"])
        .groupby("ticker", sort=False)["close"]
        .pct_change(periods=period)
    )
    return result
