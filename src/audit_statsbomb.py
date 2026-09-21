"""
Task 00 data audit — Section B.
Enumerates every StatsBomb open-data competition-season via statsbombpy
(zero-auth, no signup) and reports match counts and 360 coverage.
Run: python src/audit_statsbomb.py
"""
import json
import sys
import time
from pathlib import Path

from statsbombpy import sb

OUT_PATH = Path(__file__).parent.parent / "data" / "_statsbomb_audit_cache.json"


def main():
    comps = sb.competitions()
    rows = []
    for _, comp in comps.iterrows():
        comp_id = int(comp["competition_id"])
        season_id = int(comp["season_id"])
        label = f"{comp['competition_name']} {comp['season_name']}"
        try:
            matches = sb.matches(competition_id=comp_id, season_id=season_id)
        except Exception as e:
            rows.append({
                "competition": label, "competition_id": comp_id,
                "season_id": season_id, "error": str(e),
            })
            continue

        n_matches = len(matches)
        n_360 = int((matches["match_status_360"] == "available").sum()) \
            if "match_status_360" in matches.columns else 0

        rows.append({
            "competition": label,
            "competition_id": comp_id,
            "season_id": season_id,
            "match_count": n_matches,
            "matches_with_360": n_360,
        })
        print(f"{label}: {n_matches} matches, {n_360} with 360 available", file=sys.stderr)
        time.sleep(0.05)  # be polite to the open-data host

    OUT_PATH.parent.mkdir(exist_ok=True)
    OUT_PATH.write_text(json.dumps(rows, indent=2))
    print(f"\nWrote {len(rows)} competition-seasons to {OUT_PATH}")

    wc2022 = [r for r in rows if "World Cup" in r["competition"] and "2022" in r["competition"]]
    print("\nWorld Cup 2022 rows:", json.dumps(wc2022, indent=2))


if __name__ == "__main__":
    main()
