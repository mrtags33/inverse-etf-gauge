# Inverse ETF Gauge

Daily share of leveraged-plus-inverse ETF dollar volume that goes into inverse funds,
shown as 1, 3, 5 and 7-day readings with Warren Pies's public 40/50/60% bottom levels.
Built independently from public data; not affiliated with 3Fourteen Research.

- `fetch_data.py` downloads daily data from Yahoo Finance and writes `data.json`.
- `.github/workflows/update.yml` runs it every weekday at 22:30 UTC and commits the result.
- `index.html` reads `data.json` and is served by GitHub Pages.

Run locally:

    pip install -r requirements.txt
    python fetch_data.py
    python -m http.server 8765
