#!/usr/bin/env python3
"""
Daily mortgage/treasury tracker.

Pulls:
A) FinFam CU mortgage rates (30-year fixed) from assets.finfam.app JSON
B) Zillow Oregon 30-year fixed rate
C) Bankrate Oregon 30-year fixed rate
+ DGS10 (FRED), MORTGAGE30US (FRED, weekly), and Yahoo quotes for ^TNX + "10Y" (US10Y=X)

Writes/append to: data/mortgage_daily.csv
"""

from __future__ import annotations

import csv
import datetime as dt
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import requests


# -----------------------------
# Config
# -----------------------------
FINFAM_BASE = "https://assets.finfam.app/cumort"
ZILLOW_OR_URL = "https://www.zillow.com/homeloans/mortgage-rates/oregon/"
BANKRATE_OR_URL = "https://www.bankrate.com/mortgages/mortgage-rates/oregon/"

# FRED "fredgraph.csv" endpoints (no API key needed)
FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"

# Yahoo chart endpoint
YAHOO_CHART = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=10d&interval=1d"


OUTDIR = Path("data")
OUTCSV = OUTDIR / "mortgage_daily.csv"


DEFAULT_HEADERS = {
    # A mildly “browser-ish” UA helps avoid some basic blocks.
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X) AppleWebKit/537.36 (KHTML, like Gecko) Chrome Safari",
    "Accept": "text/html,application/json;q=0.9,*/*;q=0.8",
}


# -----------------------------
# Helpers
# -----------------------------
def http_get(url: str, timeout: int = 30) -> requests.Response:
    r = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
    r.raise_for_status()
    return r


def try_finfam_latest(max_lookback_days: int = 10) -> tuple[str, dict[str, Any]]:
    """
    FinFam publishes daily files like:
      rates_2025-12-30.json
    We'll try today in UTC and back off N days until we find one.
    """
    # Use UTC date because FinFam metadata timestamps are UTC.
    today = dt.datetime.now(dt.timezone.utc).date()

    last_err: Optional[Exception] = None
    for i in range(max_lookback_days + 1):
        d = today - dt.timedelta(days=i)
        url = f"{FINFAM_BASE}/rates_{d.isoformat()}.json"
        try:
            data = http_get(url).json()
            return url, data
        except Exception as e:
            last_err = e

    raise RuntimeError(f"Could not fetch any FinFam rates file in last {max_lookback_days} days") from last_err


def parse_finfam_30y(data: dict[str, Any]) -> dict[str, Any]:
    """
    Extract 30-year fixed summary metrics, and compute best APR across institutions (excluding outliers).
    """
    obs_date = data.get("metadata", {}).get("observation_date")
    last_updated = data.get("metadata", {}).get("last_updated")

    pt = (data.get("product_types") or {}).get("30-year-fixed") or {}
    finfam_median_apr = pt.get("median_apr")
    finfam_min_apr = pt.get("min_apr")
    finfam_max_apr = pt.get("max_apr")
    finfam_count = pt.get("count")

    # Compute "best APR" across institutions, skipping outliers
    best_apr = None
    best_inst = None

    for inst in data.get("institutions", []) or []:
        name = inst.get("name")
        for rate in inst.get("rates", []) or []:
            if rate.get("normalized_product_type") != "30-year-fixed":
                continue
            if (rate.get("outlier_reason") or "").strip():
                continue
            apr = rate.get("apr")
            if apr is None:
                continue
            if best_apr is None or apr < best_apr:
                best_apr = apr
                best_inst = name

    return {
        "finfam_observation_date": obs_date,
        "finfam_last_updated": last_updated,
        "finfam_30y_median_apr": finfam_median_apr,
        "finfam_30y_min_apr": finfam_min_apr,
        "finfam_30y_max_apr": finfam_max_apr,
        "finfam_30y_count": finfam_count,
        "finfam_30y_best_apr_ex_outliers": best_apr,
        "finfam_30y_best_apr_institution": best_inst,
    }


def extract_first_float(patterns: list[str], text: str) -> Optional[float]:
    for pat in patterns:
        m = re.search(pat, text, flags=re.IGNORECASE | re.MULTILINE)
        if m:
            try:
                return float(m.group(1))
            except Exception:
                pass
    return None


def fetch_zillow_or_30y() -> dict[str, Any]:
    html = http_get(ZILLOW_OR_URL).text
    # Example (currently): "current 30-year fixed mortgage rates in Oregon are 5.99%"
    rate = extract_first_float(
        [
            r"30-year fixed mortgage rates in oregon are\s*([0-9.]+)\s*%",
            r"30-Year Fixed.*?\bRate\s*([0-9.]+)\s*%",  # fallback
        ],
        html,
    )
    apr = extract_first_float([r"30-Year Fixed.*?\bAPR\s*([0-9.]+)\s*%"], html)
    return {"zillow_or_30y_rate": rate, "zillow_or_30y_apr": apr}


def fetch_bankrate_or_30y() -> dict[str, Any]:
    html = http_get(BANKRATE_OR_URL).text
    # Example (currently): "current interest rates in Oregon are 6.17 percent for a 30-year fixed mortgage"
    rate = extract_first_float(
        [
            r"current interest rates in oregon are\s*([0-9.]+)\s*percent\s*for a\s*30-year fixed",
            r"\b30-Year Fixed Rate\b.*?\b([0-9.]+)\s*%",  # fallback
        ],
        html,
    )
    return {"bankrate_or_30y_rate": rate}


def fetch_fred_latest(series_id: str) -> dict[str, Any]:
    """
    Pull the last non-missing value from fredgraph.csv.
    """
    url = FRED_CSV.format(series_id=series_id)
    text = http_get(url).text.strip().splitlines()
    # header: DATE,<SERIES>
    last_date = None
    last_val = None

    for line in text[1:]:
        parts = line.split(",")
        if len(parts) < 2:
            continue
        d, v = parts[0].strip(), parts[1].strip()
        if v == "." or v == "":
            continue
        last_date, last_val = d, float(v)

    return {
        f"fred_{series_id}_date": last_date,
        f"fred_{series_id}_value": last_val,
        f"fred_{series_id}_source": url,
    }


def fetch_yahoo_latest(symbol: str) -> dict[str, Any]:
    """
    Uses Yahoo's chart JSON to get the latest close.
    Returns None values if symbol not found or request fails.
    """
    try:
        url = YAHOO_CHART.format(symbol=requests.utils.quote(symbol, safe=""))
        j = http_get(url).json()

        result = (j.get("chart", {}) or {}).get("result")
        if not result:
            return {f"yahoo_{symbol}_date": None, f"yahoo_{symbol}_close": None}

        r0 = result[0]
        ts = r0.get("timestamp") or []
        closes = (((r0.get("indicators") or {}).get("quote") or [{}])[0]).get("close") or []

        # Walk from the end to find last non-null close
        last_close = None
        last_ts = None
        for t, c in zip(reversed(ts), reversed(closes)):
            if c is None:
                continue
            last_close = float(c)
            last_ts = int(t)
            break

        last_date = dt.datetime.fromtimestamp(last_ts, tz=dt.timezone.utc).date().isoformat() if last_ts else None
        return {f"yahoo_{symbol}_date": last_date, f"yahoo_{symbol}_close": last_close}
    except Exception as e:
        print(f"Warning: Could not fetch Yahoo data for {symbol}: {e}", file=sys.stderr)
        return {f"yahoo_{symbol}_date": None, f"yahoo_{symbol}_close": None}


@dataclass
class DailyRow:
    run_date_utc: str
    finfam_url: str
    payload: dict[str, Any]


def write_row_csv(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    file_exists = path.exists()

    # Stable column order: keep existing headers if file exists
    if file_exists:
        with path.open("r", newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            existing_headers = next(reader, [])
        headers = existing_headers
        # Add any new keys to the end
        for k in row.keys():
            if k not in headers:
                headers.append(k)
    else:
        headers = list(row.keys())

    # Write
    if not file_exists:
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=headers)
            w.writeheader()
            w.writerow(row)
    else:
        # If headers expanded, rewrite file with new header + prior rows
        with path.open("r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            prior = list(reader)

        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=headers)
            w.writeheader()
            for r in prior:
                w.writerow(r)
            w.writerow(row)


def main() -> int:
    run_date_utc = dt.datetime.now(dt.timezone.utc).date().isoformat()

    finfam_url, finfam_data = try_finfam_latest()
    finfam_30y = parse_finfam_30y(finfam_data)

    zillow = fetch_zillow_or_30y()
    bankrate = fetch_bankrate_or_30y()

    dgs10 = fetch_fred_latest("DGS10")           # daily 10Y constant maturity
    mort30 = fetch_fred_latest("MORTGAGE30US")   # weekly Freddie Mac PMMS

    # Yahoo quote for 10Y Treasury - CBOE 10Y yield index
    tnx = fetch_yahoo_latest("^TNX")

    row: dict[str, Any] = {
        "run_date_utc": run_date_utc,
        "finfam_url": finfam_url,
        **finfam_30y,
        **zillow,
        **bankrate,
        **dgs10,
        **mort30,
        **tnx,
    }

    write_row_csv(OUTCSV, row)
    print(f"Wrote: {OUTCSV.resolve()}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        raise