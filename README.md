# FinFam Mortgage & Treasury Tracker

Daily mortgage and treasury rate tracking tool that collects data from multiple sources.

## Overview

This script pulls mortgage and treasury rate data from:
- **FinFam Credit Union** - 30-year fixed mortgage rates from multiple institutions
- **Zillow Oregon** - 30-year fixed mortgage rates
- **Bankrate Oregon** - 30-year fixed mortgage rates  
- **FRED** - DGS10 (10-year Treasury) and MORTGAGE30US (30-year mortgage rates)
- **Yahoo Finance** - ^TNX (CBOE 10-year Treasury yield index)

Data is appended daily to `data/mortgage_daily.csv`.

## Setup

1. Create a virtual environment with uv:
```bash
uv venv
source .venv/bin/activate
```

2. Install dependencies:
```bash
uv pip install -r requirements.txt
```

## Usage

Run the daily data collection:
```bash
python3 finfam.py
```

Or with uv:
```bash
uv run python3 finfam.py
```

## Plotting

Generate interactive plots from `data/mortgage_daily.csv`:
```bash
python3 plot_rates.py --output data/daily_rates.html
python3 plot_rates.py --days 7 --output data/last_7_days.html
python3 plot_rates.py --days 30 --output data/last_30_days.html
```

Open the HTML files in a browser to view interactive charts with hover details.

## Backfill (Historical Data)

To seed history (FinFam + FRED + Yahoo only), run:
```bash
python3 backfill_history.py --days 30
```

Optional range:
```bash
python3 backfill_history.py --start-date 2025-12-01 --end-date 2025-12-31
```

The daily run de-duplicates by `run_date_utc` and replaces same-day rows.

## GitHub Actions & Pages

The daily workflow updates the CSV and publishes plots to GitHub Pages:
- All-time: `all_time.html`
- Last 30 days: `last_30_days.html`
- Last 7 days: `last_7_days.html`

Enable GitHub Pages with **Settings → Pages → Source → GitHub Actions**.

## Output

The script writes data to `data/mortgage_daily.csv` with the following fields:
- Run date and metadata
- FinFam 30-year fixed rates (median, min, max, best APR excluding outliers)
- Zillow and Bankrate Oregon rates
- FRED treasury and mortgage data
- Yahoo Finance 10-year Treasury yield

## Requirements

- Python 3.12+
- requests library (see requirements.txt)
