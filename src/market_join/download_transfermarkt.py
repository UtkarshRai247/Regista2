"""
Task 02 — Step 1: acquire market data.
Downloads the single DuckDB file published by dcaribou/transfermarkt-datasets
(CC0), containing all 12 tables. No Kaggle account needed.
Run: python src/market_join/download_transfermarkt.py
"""
import sys
from pathlib import Path

import requests

URL = "https://pub-e682421888d945d684bcae8890b0ec20.r2.dev/data/transfermarkt-datasets.duckdb"
DATA_DIR = Path(__file__).parent.parent.parent / "data"
OUT_PATH = DATA_DIR / "transfermarkt-datasets.duckdb"


def main():
    if OUT_PATH.exists():
        print(f"Already present: {OUT_PATH} ({OUT_PATH.stat().st_size / 1e6:.1f} MB)")
        return
    print(f"Downloading {URL} ...", file=sys.stderr)
    r = requests.get(URL, timeout=120, stream=True)
    r.raise_for_status()
    with open(OUT_PATH, "wb") as f:
        for chunk in r.iter_content(chunk_size=1 << 20):
            f.write(chunk)
    print(f"Saved {OUT_PATH} ({OUT_PATH.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
