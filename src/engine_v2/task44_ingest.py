"""
Task 44, Step 1: ingest StatsBomb's 2015/16 big-five open data from the
author's local copy (brief's operational note: the open-data ZIP unzipped
into data/raw_1516/open-data-master/). No analysis.

Match lists: data/matches/<competition_id>/27.json for competitions 2, 7,
9, 11, 12; events: data/events/<match_id>.json. Each event file is
flattened with statsbombpy's OWN functions (entities.events +
helpers.filter_and_group_events, then concat with sort=True) -- exactly
what sb.events() does after fetching -- and written to
data/raw_1516/events/<match_id>.parquet (never data/raw/ or
data/raw_holdout/). Match metadata -> data/raw_1516/matches/<comp>_27.parquet.

Coordinate check: task24_evidence.py's part (i) only -- share of
team-periods whose mean shot x > 60 (its parts (ii)/(iii) need 360
frames, which 2015/16 does not have).

Run: python src/engine_v2/task44_ingest.py
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from statsbombpy import entities, helpers

DATA_DIR = Path(__file__).parent.parent.parent / "data"
SRC = DATA_DIR / "raw_1516" / "open-data-master" / "data"
OUT_EVENTS = DATA_DIR / "raw_1516" / "events"
OUT_MATCHES = DATA_DIR / "raw_1516" / "matches"
SUMMARY_PATH = DATA_DIR / "engine_v2_task44_step1.json"
COMPETITIONS = (2, 7, 9, 11, 12)
SEASON = 27


def flatten(match_id: int) -> tuple:
    raw = json.loads((SRC / "events" / f"{match_id}.json").read_text())
    grouped = helpers.filter_and_group_events(entities.events(raw, match_id), {}, "dataframe", True)
    df = pd.concat([pd.DataFrame(v) for v in grouped.values()], axis=0, ignore_index=True, sort=True)
    return df, len(raw)


def main():
    OUT_EVENTS.mkdir(parents=True, exist_ok=True)
    OUT_MATCHES.mkdir(parents=True, exist_ok=True)
    per_league, problems, tp_rows = {}, [], []
    for comp in COMPETITIONS:
        matches = json.loads((SRC / "matches" / str(comp) / f"{SEASON}.json").read_text())
        mdf = pd.DataFrame([{"match_id": m["match_id"], "match_date": m["match_date"],
                             "home_team": m["home_team"]["home_team_name"], "away_team": m["away_team"]["away_team_name"],
                             "home_score": m["home_score"], "away_score": m["away_score"],
                             "competition_id": comp, "season_id": SEASON,
                             "competition_name": m["competition"]["competition_name"]} for m in matches])
        mdf.to_parquet(OUT_MATCHES / f"{comp}_{SEASON}.parquet")
        n_ok, n_events = 0, 0
        for mid in mdf["match_id"]:
            path = SRC / "events" / f"{mid}.json"
            if not path.exists():
                problems.append({"match_id": int(mid), "problem": "missing events file"})
                continue
            df, n_raw = flatten(int(mid))
            if len(df) != n_raw or not {"type", "team", "location", "index", "possession"} <= set(df.columns):
                problems.append({"match_id": int(mid), "problem": f"rows {len(df)} vs json {n_raw} / columns"})
            df.to_parquet(OUT_EVENTS / f"{mid}.parquet")
            n_ok += 1
            n_events += len(df)
            shots = df[df["type"] == "Shot"]
            for (team, period), g in shots.groupby(["team", "period"]):
                xs = [l[0] for l in g["location"] if isinstance(l, (list, np.ndarray))]
                if xs:
                    tp_rows.append({"match_id": int(mid), "team": team, "period": int(period), "mean_shot_x": float(np.mean(xs))})
        per_league[str(comp)] = {"name": mdf["competition_name"].iloc[0], "n_matches_listed": len(mdf),
                                 "n_ingested": n_ok, "n_events": n_events}
        print(f"  {comp} {mdf['competition_name'].iloc[0]}: {n_ok}/{len(mdf)} matches, {n_events} events")
    tp = pd.DataFrame(tp_rows)
    share = float((tp["mean_shot_x"] > 60).mean())
    print(f"  team-periods with shots: {len(tp)}; share with mean shot x > 60: {share:.4f}")
    SUMMARY_PATH.write_text(json.dumps({"per_league": per_league, "problems": problems,
                                        "n_team_periods_with_shots": len(tp), "share_mean_shot_x_gt_60": share},
                                       indent=2))
    print(f"  problems: {problems if problems else 'none'}")


if __name__ == "__main__":
    main()
