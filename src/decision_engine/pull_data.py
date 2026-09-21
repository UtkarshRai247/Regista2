"""
Task 01 — data pull. Fetches events + 360 frames for every match in the
sample (data/sample_competitions.json), one match at a time, writing raw
parquet immediately so a crash mid-pull just resumes (skips matches
already on disk).
Run: python src/decision_engine/pull_data.py
"""
import json
import sys
import time
import warnings
from pathlib import Path

import requests
from statsbombpy import sb
import requests_cache

# statsbombpy installs a growing sqlite requests_cache at import time. On a
# long single-pass pull (each match fetched exactly once, no repeat lookups
# needed) that cache only grows and, on this machine's tight memory, causes
# severe progressive slowdown (observed: sub-second fetches degrading to
# 30-50s/call after ~30 matches). Disable it — plain requests underneath.
requests_cache.uninstall_cache()

# statsbombpy's own requests.get() calls carry no timeout. socket.setdefault
# timeout() does NOT fix this — urllib3 (which requests sits on) manages its
# own per-connection timeout and ignores the process-wide socket default
# when the caller passes none, so a stalled connection (observed: a
# "between bytes" 503, then a plain silent hang on a later match) blocks
# forever. Patching requests.get itself to default a timeout is the only
# fix that actually reaches statsbombpy's calls.
_orig_get = requests.get


def _get_with_timeout(*args, **kwargs):
    kwargs.setdefault("timeout", 30)
    return _orig_get(*args, **kwargs)


requests.get = _get_with_timeout

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
EVENTS_DIR = DATA_DIR / "raw" / "events"
FRAMES_DIR = DATA_DIR / "raw" / "frames"
MATCHES_DIR = DATA_DIR / "raw" / "matches"


def main():
    sample = json.loads((DATA_DIR / "sample_competitions.json").read_text())
    for d in (EVENTS_DIR, FRAMES_DIR, MATCHES_DIR):
        d.mkdir(parents=True, exist_ok=True)

    match_ids = []
    for comp in sample:
        matches = sb.matches(competition_id=comp["competition_id"],
                              season_id=comp["season_id"])
        mpath = MATCHES_DIR / f"{comp['competition_id']}_{comp['season_id']}.parquet"
        if not mpath.exists():
            matches.to_parquet(mpath)
        match_ids.extend(matches["match_id"].tolist())

    print(f"{len(match_ids)} matches to pull", file=sys.stderr)
    n_pulled = n_skipped = n_failed = 0
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
                else:
                    time.sleep(1)
        if (i + 1) % 20 == 0:
            print(f"  {i + 1}/{len(match_ids)} processed "
                  f"(pulled={n_pulled}, skipped={n_skipped}, failed={n_failed})",
                  file=sys.stderr)
        time.sleep(0.05)

    print(f"\nDone. pulled={n_pulled} skipped={n_skipped} failed={n_failed} "
          f"total={len(match_ids)}")


if __name__ == "__main__":
    main()
