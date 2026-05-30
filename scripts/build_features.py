from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.data.loader import load_daily, save_factor_partitions
from src.factors.liquidity import calc_amount_ma
from src.factors.momentum import calc_ret
from src.factors.trend import calc_ma, close_above_ma
from src.settings import load_settings


def build_base_factors(daily_df):
    result = calc_ret(daily_df, period=20)
    result = calc_ma(result, period=20)
    result = close_above_ma(result, period=20)
    result = calc_amount_ma(result, period=20)
    if "is_tradable" not in result.columns:
        result["is_tradable"] = True
    return result[["date", "ticker", "close", "ret_20", "ma_20", "close_above_ma20", "amount_ma_20", "is_tradable"]].copy()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--start-date", required=True)
    parser.add_argument("--end-date", required=True)
    parser.add_argument("--project-root", default=str(PROJECT_ROOT))
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    settings = load_settings(args.config, project_root=project_root)
    processed_root = settings["paths"]["processed_data"]
    daily_root = processed_root / "daily"
    factor_root = processed_root / "factors" / "base"

    daily_df = load_daily(daily_root, start_date=args.start_date, end_date=args.end_date)
    factor_df = build_base_factors(daily_df)
    written = save_factor_partitions(factor_df, factor_root)

    print(
        json.dumps(
            {
                "factor_set": "base",
                "rows": int(len(factor_df)),
                "files_written": len(written),
                "written_paths": [str(path) for path in written],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
