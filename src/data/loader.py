from __future__ import annotations

from pathlib import Path

import pandas as pd


DAILY_FILE_NAME = "daily.parquet"
FACTOR_FILE_NAME = "factors.parquet"
COMPONENT_FILE_NAME = "components.parquet"
SUSPEND_FILE_NAME = "suspend.parquet"
DAILY_COLUMNS = ["date", "ticker", "open", "high", "low", "close", "volume", "amount", "is_tradable"]
BASE_FACTOR_COLUMNS = ["date", "ticker", "close", "ret_20", "ma_20", "close_above_ma20", "amount_ma_20", "is_tradable"]
COMPONENT_COLUMNS = ["date", "index_code", "ticker", "weight"]
SUSPEND_COLUMNS = ["date", "ticker", "suspend_type", "suspend_timing"]
OPTIONAL_BOOL_COLUMNS = ["is_tradable"]


def _save_partitioned(df: pd.DataFrame, output_root: str | Path, file_name: str) -> list[Path]:
    output_root = Path(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    frame = df.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    frame["year"] = frame["date"].dt.year
    for year, part in frame.groupby("year"):
        target_dir = output_root / f"year={year}"
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / file_name
        part.drop(columns=["year"]).to_parquet(target_path, index=False)
        written.append(target_path)
    return sorted(written)


def _load_partitioned(
    data_root: str | Path,
    file_name: str,
    start_date: str,
    end_date: str,
    columns: list[str],
    universe: list[str] | None = None,
) -> pd.DataFrame:
    data_root = Path(data_root)
    parquet_files = sorted(data_root.glob(f"year=*/{file_name}"))
    if not parquet_files:
        return pd.DataFrame(columns=columns)
    frames = [pd.read_parquet(path) for path in parquet_files]
    df = pd.concat(frames, ignore_index=True)
    for column in columns:
        if column not in df.columns:
            if column in OPTIONAL_BOOL_COLUMNS:
                df[column] = True
            else:
                df[column] = pd.NA
    df = df[columns].copy()
    df["date"] = pd.to_datetime(df["date"])
    start = pd.Timestamp(start_date)
    end = pd.Timestamp(end_date)
    mask = (df["date"] >= start) & (df["date"] <= end)
    if universe is not None:
        mask &= df["ticker"].isin(universe)
    return df.loc[mask].sort_values(["ticker", "date"]).reset_index(drop=True)


def save_daily_partitions(df: pd.DataFrame, output_root: str | Path) -> list[Path]:
    return _save_partitioned(df, output_root, DAILY_FILE_NAME)


def save_factor_partitions(df: pd.DataFrame, output_root: str | Path) -> list[Path]:
    return _save_partitioned(df, output_root, FACTOR_FILE_NAME)


def save_component_partitions(df: pd.DataFrame, output_root: str | Path) -> list[Path]:
    return _save_partitioned(df, output_root, COMPONENT_FILE_NAME)


def save_suspend_partitions(df: pd.DataFrame, output_root: str | Path) -> list[Path]:
    return _save_partitioned(df, output_root, SUSPEND_FILE_NAME)


def load_daily(data_root: str | Path, start_date: str, end_date: str, universe: list[str] | None = None) -> pd.DataFrame:
    return _load_partitioned(data_root, DAILY_FILE_NAME, start_date, end_date, DAILY_COLUMNS, universe)


def load_components(data_root: str | Path, start_date: str, end_date: str, index_code: str | None = None) -> pd.DataFrame:
    df = _load_partitioned(data_root, COMPONENT_FILE_NAME, start_date, end_date, COMPONENT_COLUMNS)
    if index_code is not None and not df.empty:
        df = df[df["index_code"] == index_code].copy()
    return df.sort_values(["date", "ticker"]).reset_index(drop=True)


def load_suspends(data_root: str | Path, start_date: str, end_date: str) -> pd.DataFrame:
    return _load_partitioned(data_root, SUSPEND_FILE_NAME, start_date, end_date, SUSPEND_COLUMNS)


def load_factors(
    data_root: str | Path,
    start_date: str,
    end_date: str,
    factor_set: str = "base",
    universe: list[str] | None = None,
) -> pd.DataFrame:
    if factor_set != "base":
        raise ValueError(f"Unsupported factor_set: {factor_set}")
    return _load_partitioned(data_root, FACTOR_FILE_NAME, start_date, end_date, BASE_FACTOR_COLUMNS, universe)
