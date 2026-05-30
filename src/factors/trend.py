import pandas as pd


def calc_ma(df: pd.DataFrame, period: int) -> pd.DataFrame:
    result = df.copy()
    column = f"ma_{period}"
    ordered = result.sort_values(["ticker", "date"]).copy()
    ordered[column] = (
        ordered.groupby("ticker", sort=False)["close"]
        .transform(lambda s: s.rolling(window=period, min_periods=period).mean())
    )
    return ordered


def close_above_ma(df: pd.DataFrame, period: int) -> pd.DataFrame:
    result = df.copy()
    ma_column = f"ma_{period}"
    output_column = f"close_above_ma{period}"
    result[output_column] = pd.Series(pd.NA, index=result.index, dtype="boolean")
    mask = result[ma_column].notna()
    result.loc[mask, output_column] = result.loc[mask, "close"] > result.loc[mask, ma_column]
    return result
