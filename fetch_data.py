"""
Refresh data.json for the inverse ETF volume dashboard.

Inverse share = inverse ETF dollar volume / (inverse + leveraged-long) dollar volume.
Dollar volume = unadjusted close x shares traded. The page computes the 1/3/5/7-day
readings from the raw daily sums stored here.

Run: python fetch_data.py
"""
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yfinance as yf

INVERSE = ["SH", "SDS", "SPXU", "SPXS", "PSQ", "QID", "SQQQ", "DOG", "DXD",
           "SDOW", "RWM", "TWM", "TZA", "SRTY", "SOXS", "FAZ"]
LEVERAGED = ["SSO", "UPRO", "SPXL", "QLD", "TQQQ", "DDM", "UDOW", "UWM",
             "TNA", "URTY", "SOXL", "FAS"]
START = "2010-01-01"
OUT = Path(__file__).parent / "data.json"
RETRIES = 3


def dollar_volume(tickers: list[str]) -> pd.DataFrame:
    """Daily close x volume per ticker. Parallel downloads sometimes drop a ticker
    (yfinance's cache reports 'database is locked'), so any ticker with no recent
    data is retried one at a time, without threads."""
    etf = yf.download(tickers, start=START, auto_adjust=False, progress=False, threads=True)
    dv = (etf["Close"] * etf["Volume"]).reindex(columns=tickers)
    for attempt in range(1, RETRIES + 1):
        missing = [t for t in tickers if dv[t].iloc[-30:].fillna(0).sum() == 0]
        if not missing:
            break
        print(f"retry {attempt}/{RETRIES}: {missing}", file=sys.stderr)
        time.sleep(3 * attempt)
        for t in missing:
            one = yf.download(t, start=START, auto_adjust=False, progress=False, threads=False)
            if one.empty:
                continue
            col = (one["Close"] * one["Volume"]).squeeze()
            dv = dv.reindex(dv.index.union(col.index))
            dv[t] = col
    return dv


def main() -> int:
    dv = dollar_volume(INVERSE + LEVERAGED)
    spx = yf.download("^GSPC", start=START, auto_adjust=True, progress=False)["Close"].squeeze()

    # A missing fund skews the share badly (no SOXL took it from ~40% to ~60%), so
    # publish nothing rather than a partial basket. Checks the last 30 days and the latest day.
    missing = [t for t in INVERSE + LEVERAGED
               if dv[t].iloc[-30:].fillna(0).sum() == 0 or pd.isna(dv[t].iloc[-1]) or dv[t].iloc[-1] == 0]
    if missing:
        print(f"no data for {missing} after {RETRIES} retries; keeping the existing data.json",
              file=sys.stderr)
        return 1
    dv = dv.fillna(0.0)
    inv = dv[[t for t in INVERSE if t in dv]].sum(axis=1)
    lev = dv[[t for t in LEVERAGED if t in dv]].sum(axis=1)

    df = pd.DataFrame({"inv": inv, "lev": lev}).join(spx.rename("spx"), how="inner")
    df = df[(df.inv + df.lev) > 0].dropna()
    if len(df) < 1000:
        print(f"only {len(df)} rows downloaded; keeping the existing data.json", file=sys.stderr)
        return 1

    payload = {
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "inverse": INVERSE,
        "leveraged": LEVERAGED,
        "missing_recent": missing,
        "date": [d.strftime("%Y-%m-%d") for d in df.index],
        "inv": (df.inv / 1e6).round(2).tolist(),   # $ millions
        "lev": (df.lev / 1e6).round(2).tolist(),   # $ millions
        "spx": df.spx.round(2).tolist(),
    }
    OUT.write_text(json.dumps(payload, separators=(",", ":")))
    last = df.iloc[-1]
    print(f"{df.index[-1].date()}: daily inverse share {last.inv / (last.inv + last.lev):.1%}, "
          f"{len(df)} rows -> {OUT.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
