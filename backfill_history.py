#!/usr/bin/env python3
"""
Backfill historical FinFam + FRED + Yahoo data into data/mortgage_daily.csv.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import sys
from bisect import bisect_right
from pathlib import Path
from typing import Any, Optional

import requests

from finfam import (
    FINFAM_BASE,
    OUTCSV,
    fetch_fred_latest,
    http_get,
    parse_finfam_30y,
    write_row_csv,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill historical rate data.")
    parser.add_argument("--days", type=int, default=30, help="Number of days to backfill")
    parser.add_argument("--start-date", type=str, default=None, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", type=str, default=None, help="End date (YYYY-MM-DD)")
    return parser.parse_args()


def load_existing_dates(path: Path) -> set[str]:
    if not path.exists():
        return set()
    with path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return {row.get("run_date_utc", "") for row in reader if row.get("run_date_utc")}


def parse_date(value: str) -> dt.date:
    return dt.datetime.strptime(value, "%Y-%m-%d").date()


def date_range(start: dt.date, end: dt.date) -> list[dt.date]:
    days = (end - start).days
    return [start + dt.timedelta(days=i) for i in range(days + 1)]


def fetch_finfam_for_date(date: dt.date) -> tuple[str, dict[str, Any]]:
    url = f"{FINFAM_BASE}/rates_{date.isoformat()}.json"
    data = http_get(url).json()
    return url, data


def fetch_fred_series(series_id: str) -> tuple[list[dt.date], list[float], str]:
    result = fetch_fred_latest(series_id)
    source = result.get(f"fred_{series_id}_source")
    if not source:
        source = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
    text = http_get(source).text.strip().splitlines()
    dates: list[dt.date] = []
    values: list[float] = []
    for line in text[1:]:
        parts = line.split(",")
        if len(parts) < 2:
            continue
        d, v = parts[0].strip(), parts[1].strip()
        if v == "." or v == "":
            continue
        try:
            dates.append(parse_date(d))
            values.append(float(v))
        except ValueError:
            continue
    return dates, values, source


def fetch_yahoo_series(symbol: str, range_str: str = "2y") -> tuple[list[dt.date], list[float]]:
    url = (
        "https://query1.finance.yahoo.com/v8/finance/chart/"
        f"{requests.utils.quote(symbol, safe='')}?range={range_str}&interval=1d"
    )
    data = http_get(url).json()
    result = (data.get("chart", {}) or {}).get("result")
    if not result:
        return [], []
    r0 = result[0]
    timestamps = r0.get("timestamp") or []
    closes = (((r0.get("indicators") or {}).get("quote") or [{}])[0]).get("close") or []
    dates: list[dt.date] = []
    values: list[float] = []
    for t, c in zip(timestamps, closes):
        if c is None:
            continue
        d = dt.datetime.fromtimestamp(int(t), tz=dt.timezone.utc).date()
        dates.append(d)
        values.append(float(c))
    return dates, values


def value_on_or_before(
    dates: list[dt.date], values: list[float], target: dt.date
) -> tuple[Optional[dt.date], Optional[float]]:
    if not dates:
        return None, None
    idx = bisect_right(dates, target) - 1
    if idx < 0:
        return None, None
    return dates[idx], values[idx]


def main() -> int:
    args = parse_args()
    today = dt.datetime.now(dt.timezone.utc).date()

    if args.start_date and args.end_date:
        start_date = parse_date(args.start_date)
        end_date = parse_date(args.end_date)
    else:
        days = max(args.days, 1)
        end_date = today
        start_date = today - dt.timedelta(days=days - 1)

    existing_dates = load_existing_dates(OUTCSV)
    fred_dgs10_dates, fred_dgs10_values, fred_dgs10_source = fetch_fred_series("DGS10")
    fred_mort30_dates, fred_mort30_values, fred_mort30_source = fetch_fred_series("MORTGAGE30US")
    yahoo_dates, yahoo_values = fetch_yahoo_series("^TNX", range_str="2y")

    for date in date_range(start_date, end_date):
        if date.isoformat() in existing_dates:
            continue
        try:
            finfam_url, finfam_data = fetch_finfam_for_date(date)
        except Exception as exc:
            print(f"Skipping {date.isoformat()}: FinFam fetch failed ({exc})", file=sys.stderr)
            continue

        finfam_30y = parse_finfam_30y(finfam_data)
        dgs10_date, dgs10_value = value_on_or_before(fred_dgs10_dates, fred_dgs10_values, date)
        mort30_date, mort30_value = value_on_or_before(fred_mort30_dates, fred_mort30_values, date)
        tnx_date, tnx_value = value_on_or_before(yahoo_dates, yahoo_values, date)

        row: dict[str, Any] = {
            "run_date_utc": date.isoformat(),
            "finfam_url": finfam_url,
            **finfam_30y,
            "zillow_or_30y_rate": None,
            "zillow_or_30y_apr": None,
            "bankrate_or_30y_rate": None,
            "fred_DGS10_date": dgs10_date.isoformat() if dgs10_date else None,
            "fred_DGS10_value": dgs10_value,
            "fred_DGS10_source": fred_dgs10_source,
            "fred_MORTGAGE30US_date": mort30_date.isoformat() if mort30_date else None,
            "fred_MORTGAGE30US_value": mort30_value,
            "fred_MORTGAGE30US_source": fred_mort30_source,
            "yahoo_^TNX_date": tnx_date.isoformat() if tnx_date else None,
            "yahoo_^TNX_close": tnx_value,
        }

        write_row_csv(OUTCSV, row)
        print(f"Backfilled {date.isoformat()}")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
