"""
Task 23, Step 4 — pull StatsBomb events + 360 frames for the 360-covered
competition-seasons NOT in the study sample (Women's Euro 2022, Women's
World Cup 2023, Women's Euro 2025; per docs/results/00-data-audit.md's
360-coverage enumeration), into a SEPARATE directory (data/raw_holdout/),
never data/raw/. Download and ingest only -- no model, feature, or
outcome code is run on this data in this task.

Mirrors src/decision_engine/pull_data.py's exact pull logic (resumable,
one match at a time, requests_cache disabled, timeout patched) with only
the output directory and competition-season list changed.

Competition/season IDs looked up live via sb.competitions():
  Women's Euro 2022:      competition_id=53, season_id=106
  Women's World Cup 2023: competition_id=72, season_id=107
  Women's Euro 2025:      competition_id=53, season_id=315

Run: python src/decision_engine/pull_holdout_data.py
"""
import sys
import time
import warnings
from pathlib import Path

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
EVENTS_DIR = DATA_DIR / "raw_holdout" / "events"
FRAMES_DIR = DATA_DIR / "raw_holdout" / "frames"
MATCHES_DIR = DATA_DIR / "raw_holdout" / "matches"

HOLDOUT_COMPETITIONS = [
    {"name": "Women's Euro 2022", "competition_id": 53, "season_id": 106},
    {"name": "Women's World Cup 2023", "competition_id": 72, "season_id": 107},
    {"name": "Women's Euro 2025", "competition_id": 53, "season_id": 315},
]


def main():
    for d in (EVENTS_DIR, FRAMES_DIR, MATCHES_DIR):
        d.mkdir(parents=True, exist_ok=True)

    match_ids = []
    per_comp_counts = {}
    for comp in HOLDOUT_COMPETITIONS:
        matches = sb.matches(competition_id=comp["competition_id"], season_id=comp["season_id"])
        mpath = MATCHES_DIR / f"{comp['competition_id']}_{comp['season_id']}.parquet"
        if not mpath.exists():
            matches.to_parquet(mpath)
        n_360 = int((matches["match_status_360"] == "available").sum()) if "match_status_360" in matches.columns else None
        per_comp_counts[comp["name"]] = {"n_matches": len(matches), "n_360_available": n_360}
        match_ids.extend(matches["match_id"].tolist())
        print(f"  {comp['name']}: {len(matches)} matches, 360 available={n_360}", file=sys.stderr)

    print(f"{len(match_ids)} matches to pull", file=sys.stderr)
    n_pulled = n_skipped = n_failed = 0
    n_frame_coverage_yes, n_frame_coverage_no = 0, 0
    failed_ids = []
    for i, mid in enumerate(match_ids):
        epath = EVENTS_DIR / f"{mid}.parquet"
        fpath = FRAMES_DIR / f"{mid}.parquet"
        if epath.exists() and fpath.exists():
            n_skipped += 1
            continue
        for attempt in range(2):
            try:
                if not epath.exists():
                    events = sb.events(match_id=mid)
                    events.to_parquet(epath)
                if not fpath.exists():
                    frames = sb.frames(match_id=mid)
                    frames.to_parquet(fpath)
                n_pulled += 1
                break
            except Exception as e:
                if attempt == 1:
                    print(f"  FAILED match {mid}: {e}", file=sys.stderr)
                    n_failed += 1
                    failed_ids.append(mid)
                else:
                    time.sleep(1)
        if (i + 1) % 20 == 0:
            print(f"  {i + 1}/{len(match_ids)} processed "
                  f"(pulled={n_pulled}, skipped={n_skipped}, failed={n_failed})", file=sys.stderr)
        time.sleep(0.05)

    for mid in match_ids:
        fpath = FRAMES_DIR / f"{mid}.parquet"
        if fpath.exists():
            try:
                import pandas as pd
                frames = pd.read_parquet(fpath)
                if len(frames) > 0:
                    n_frame_coverage_yes += 1
                else:
                    n_frame_coverage_no += 1
            except Exception:
                n_frame_coverage_no += 1
        else:
            n_frame_coverage_no += 1

    print(f"\nDone. pulled={n_pulled} skipped={n_skipped} failed={n_failed} total={len(match_ids)}")
    print(f"Per-competition match counts: {per_comp_counts}")
    print(f"Frame coverage (non-empty frames file present): {n_frame_coverage_yes}/{len(match_ids)}")
    if failed_ids:
        print(f"Failed match ids: {failed_ids}")
    return {"per_comp_counts": per_comp_counts, "n_pulled": n_pulled, "n_skipped": n_skipped,
            "n_failed": n_failed, "n_total": len(match_ids), "failed_ids": failed_ids,
            "n_frame_coverage_yes": n_frame_coverage_yes, "n_frame_coverage_no": n_frame_coverage_no}


if __name__ == "__main__":
    main()
