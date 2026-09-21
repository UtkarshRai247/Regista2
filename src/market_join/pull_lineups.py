"""
Task 02 — Step 2 prerequisite: pull StatsBomb lineups for all 299 sample
matches. Not fetched in Task 01 — needed here for each player's
StatsBomb-reported `country`, used as the crosswalk's secondary key.
Run: python src/market_join/pull_lineups.py
"""
import sys
import time
import warnings
from pathlib import Path

import pandas as pd
import requests
from statsbombpy import sb
import requests_cache

requests_cache.uninstall_cache()
_orig_get = requests.get


def _get_with_timeout(*args, **kwargs):
    kwargs.setdefault("timeout", 30)
    return _orig_get(*args, **kwargs)


requests.get = _get_with_timeout
warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
EVENTS_DIR = DATA_DIR / "raw" / "events"
LINEUPS_DIR = DATA_DIR / "raw" / "lineups"


def main():
    LINEUPS_DIR.mkdir(parents=True, exist_ok=True)
    match_ids = sorted(int(p.stem) for p in EVENTS_DIR.glob("*.parquet"))
    print(f"{len(match_ids)} matches to pull lineups for", file=sys.stderr)

    n_pulled = n_skipped = n_failed = 0
    for i, mid in enumerate(match_ids):
        out_path = LINEUPS_DIR / f"{mid}.parquet"
        if out_path.exists():
            n_skipped += 1
            continue
        for attempt in range(2):
            try:
                lineups = sb.lineups(match_id=mid)
                rows = []
                for team, df in lineups.items():
                    df = df.copy()
                    df["team"] = team
                    rows.append(df[["player_id", "player_name", "player_nickname", "country", "team"]])
                pd.concat(rows, ignore_index=True).to_parquet(out_path)
                n_pulled += 1
                break
            except Exception as e:
                if attempt == 1:
                    print(f"  FAILED match {mid}: {e}", file=sys.stderr)
                    n_failed += 1
                else:
                    time.sleep(1)
        if (i + 1) % 50 == 0:
            print(f"  {i + 1}/{len(match_ids)} processed "
                  f"(pulled={n_pulled}, skipped={n_skipped}, failed={n_failed})", file=sys.stderr)

    print(f"Done. pulled={n_pulled} skipped={n_skipped} failed={n_failed} total={len(match_ids)}")


if __name__ == "__main__":
    main()
