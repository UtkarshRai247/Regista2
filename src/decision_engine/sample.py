"""
Task 01 — Step 0: sample confirmation.
Derives the men's, 360-covered competition-season sample directly from
StatsBomb's live competitions() data (via the real `competition_gender`
field, not name-guessing), joined against Task 00's 360-coverage cache.
Excludes AFCON 2023 (spec: 1/52 coverage, too partial) and all women's
competitions.
Run: python src/decision_engine/sample.py
"""
import json
import warnings
from pathlib import Path

from statsbombpy import sb

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
AUDIT_CACHE = DATA_DIR / "_statsbomb_audit_cache.json"
OUT_PATH = DATA_DIR / "sample_competitions.json"


def get_sample() -> list[dict]:
    audit = json.loads(AUDIT_CACHE.read_text())
    has_360 = {(r["competition_id"], r["season_id"]): r["matches_with_360"]
               for r in audit if r.get("matches_with_360", 0) > 0}

    comps = sb.competitions()
    rows = []
    for _, c in comps.iterrows():
        key = (int(c["competition_id"]), int(c["season_id"]))
        if key not in has_360:
            continue
        if c["competition_gender"] != "male":
            continue
        n_360 = has_360[key]
        # exclude partial coverage (AFCON 2023: 1/52)
        matches = sb.matches(competition_id=key[0], season_id=key[1])
        n_matches = len(matches)
        if n_360 < n_matches:
            continue
        rows.append({
            "competition": f"{c['competition_name']} {c['season_name']}",
            "competition_id": key[0],
            "season_id": key[1],
            "matches": n_matches,
        })
    return rows


def main():
    rows = get_sample()
    total = sum(r["matches"] for r in rows)
    print(f"Sample: {len(rows)} competition-seasons, {total} matches\n")
    for r in rows:
        print(f"  {r['competition']:30s} comp={r['competition_id']:3d} "
              f"season={r['season_id']:4d}  {r['matches']:3d} matches")
    OUT_PATH.write_text(json.dumps(rows, indent=2))
    print(f"\nWrote {OUT_PATH}")


if __name__ == "__main__":
    main()
