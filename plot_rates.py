#!/usr/bin/env python3
"""
Plot daily mortgage/treasury series from data/mortgage_daily.csv.
"""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import plotly.graph_objects as go


DATA_PATH = Path("data/mortgage_daily.csv")
PLOT_PATH = Path("data/daily_rates.html")


def parse_float(value: str | None) -> Optional[float]:
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def load_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Missing data file: {path}")
    with path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plot daily mortgage/treasury rates.")
    parser.add_argument("--days", type=int, default=None, help="Only plot the last N days")
    parser.add_argument("--output", type=Path, default=PLOT_PATH, help="Output HTML path")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rows = load_rows(DATA_PATH)
    if not rows:
        raise RuntimeError("No rows found in data/mortgage_daily.csv")

    dates: list[datetime] = []
    finfam_min: list[Optional[float]] = []
    zillow_rate: list[Optional[float]] = []
    bankrate_rate: list[Optional[float]] = []
    fred_dgs10: list[Optional[float]] = []
    fred_mort30: list[Optional[float]] = []
    yahoo_tnx: list[Optional[float]] = []
    finfam_min_inst: list[str | None] = []

    for row in rows:
        run_date = row.get("run_date_utc", "")
        try:
            dates.append(datetime.strptime(run_date, "%Y-%m-%d"))
        except ValueError:
            continue

        finfam_min.append(parse_float(row.get("finfam_30y_min_apr")))
        zillow_rate.append(parse_float(row.get("zillow_or_30y_rate")))
        bankrate_rate.append(parse_float(row.get("bankrate_or_30y_rate")))
        fred_dgs10.append(parse_float(row.get("fred_DGS10_value")))
        fred_mort30.append(parse_float(row.get("fred_MORTGAGE30US_value")))
        yahoo_tnx.append(parse_float(row.get("yahoo_^TNX_close")))
        finfam_min_inst.append(row.get("finfam_30y_min_apr_institution") or None)

    if not dates:
        raise RuntimeError("No valid dates parsed from data")

    if args.days and args.days > 0:
        dates = dates[-args.days :]
        finfam_min = finfam_min[-args.days :]
        zillow_rate = zillow_rate[-args.days :]
        bankrate_rate = bankrate_rate[-args.days :]
        fred_dgs10 = fred_dgs10[-args.days :]
        fred_mort30 = fred_mort30[-args.days :]
        yahoo_tnx = yahoo_tnx[-args.days :]
        finfam_min_inst = finfam_min_inst[-args.days :]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=finfam_min,
            name="FinFam 30Y Min APR",
            mode="lines+markers",
            customdata=finfam_min_inst,
            hovertemplate=(
                "Date: %{x|%Y-%m-%d}<br>"
                "Rate: %{y:.3f}%<br>"
                "Institution: %{customdata}<extra></extra>"
            ),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=zillow_rate,
            name="Zillow OR 30Y Rate",
            mode="lines+markers",
            hovertemplate="Date: %{x|%Y-%m-%d}<br>Rate: %{y:.3f}%<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=bankrate_rate,
            name="Bankrate OR 30Y Rate",
            mode="lines+markers",
            hovertemplate="Date: %{x|%Y-%m-%d}<br>Rate: %{y:.3f}%<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=fred_dgs10,
            name="FRED DGS10",
            mode="lines+markers",
            hovertemplate="Date: %{x|%Y-%m-%d}<br>Rate: %{y:.3f}%<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=fred_mort30,
            name="FRED MORTGAGE30US",
            mode="lines+markers",
            hovertemplate="Date: %{x|%Y-%m-%d}<br>Rate: %{y:.3f}%<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=yahoo_tnx,
            name="Yahoo ^TNX",
            mode="lines+markers",
            hovertemplate="Date: %{x|%Y-%m-%d}<br>Rate: %{y:.3f}%<extra></extra>",
        )
    )

    fig.update_layout(
        title="Daily Mortgage & Treasury Rates",
        xaxis=dict(
            title="Date (UTC)",
            dtick=24 * 60 * 60 * 1000,
            tickformat="%Y-%m-%d",
        ),
        yaxis_title="Rate (%)",
        yaxis_ticksuffix="%",
        legend=dict(
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.02,
            bordercolor="rgba(0,0,0,0.1)",
            borderwidth=1,
        ),
        margin=dict(r=200),
        hovermode="x unified",
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(args.output, include_plotlyjs="cdn", full_html=True)
    print(f"Wrote: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
