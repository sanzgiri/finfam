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
