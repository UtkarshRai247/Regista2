"""
Task 48, Data: ingest the 64 RESERVED competition-seasons (listed in
docs/results/46-movers-and-spatial-physical.md; ids saved in
data/engine_v2_task46_part_a.json) -- the single use of this data.
docs/specs/task-48-confirmation-reserved.md.

Events are flattened with Task 44's `flatten` (statsbombpy's own
functions) into data/raw_reserved/events/<match_id>.parquet; matches into
data/raw_reserved/matches/<comp>_<season>.parquet. Club vs national team
from competitions.json's `competition_international`. Coordinate check:
task24_evidence.py part (i) (share of team-periods with mean shot x > 60).

Run: python src/engine_v2/task48_ingest.py
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

from task44_ingest import flatten, SRC

DATA_DIR = Path(__file__).parent.parent.parent / "data"
OUT_EVENTS = DATA_DIR / "raw_reserved" / "events"
OUT_MATCHES = DATA_DIR / "raw_reserved" / "matches"
SUMMARY_PATH = DATA_DIR / "engine_v2_task48_ingest.json"


def main():
    reserved = [tuple(x) for x in json.loads((DATA_DIR / "engine_v2_task46_part_a.json").read_text())["reserved_not_opened"]]
    assert len(reserved) == 64
    comps = {(c["competition_id"], c["season_id"]): c for c in json.loads((SRC / "competitions.json").read_text())}
    OUT_EVENTS.mkdir(parents=True, exist_ok=True)
    OUT_MATCHES.mkdir(parents=True, exist_ok=True)
    rows, problems, tp_rows, seen = [], [], [], set()
    for comp, season in reserved:
        meta = comps.get((comp, season), {})
        matches = json.loads((SRC / "matches" / str(comp) / f"{season}.json").read_text())
        mdf = pd.DataFrame([{"match_id": m["match_id"], "match_date": m["match_date"],
                             "home_team": m["home_team"]["home_team_name"], "away_team": m["away_team"]["away_team_name"],
                             "competition_id": comp, "season_id": season} for m in matches])
        mdf.to_parquet(OUT_MATCHES / f"{comp}_{season}.parquet")
        n_ok, n_ev = 0, 0
        for mid in mdf["match_id"]:
            if mid in seen:
                problems.append({"match_id": int(mid), "problem": "listed in more than one reserved competition-season"})
                continue
            seen.add(mid)
            if not (SRC / "events" / f"{mid}.json").exists():
                problems.append({"match_id": int(mid), "competition": [comp, season], "problem": "missing events file"})
                continue
            df, n_raw = flatten(int(mid))
            if len(df) != n_raw:
                problems.append({"match_id": int(mid), "problem": f"rows {len(df)} vs json {n_raw}"})
            df.to_parquet(OUT_EVENTS / f"{mid}.parquet")
            n_ok += 1
            n_ev += len(df)
            for (team, period), g in df[df["type"] == "Shot"].groupby(["team", "period"]):
                xs = [l[0] for l in g["location"] if isinstance(l, (list, np.ndarray))]
                if xs:
                    tp_rows.append(float(np.mean(xs)))
        rows.append({"competition_id": comp, "season_id": season, "competition": meta.get("competition_name"),
                     "season": meta.get("season_name"), "gender": meta.get("competition_gender"),
                     "international": bool(meta.get("competition_international")), "n_matches": len(mdf),
                     "n_ingested": n_ok, "n_events": n_ev})
        print(f"  {comp}/{season} {meta.get('competition_name')} {meta.get('season_name')}: {n_ok}/{len(mdf)} matches")
    share = float((np.array(tp_rows) > 60).mean())
    SUMMARY_PATH.write_text(json.dumps({"per_competition_season": rows, "problems": problems,
                                        "n_team_periods_with_shots": len(tp_rows), "share_mean_shot_x_gt_60": share}, indent=2))
    print(f"  total matches {sum(r['n_ingested'] for r in rows)}; team-periods {len(tp_rows)}; share > 60: {share:.4f}; "
          f"problems: {len(problems)}")


if __name__ == "__main__":
    main()
