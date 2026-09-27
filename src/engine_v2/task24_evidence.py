"""
Task 24, Step 1(a): reproduce the research lead's coordinate evidence
on ALL 299 matches (the brief's own check was on the first 40). No
model, feature, or code change happens in this script -- it only
measures the CURRENT (pre-fix) `team_period_directions` and the raw
StatsBomb coordinates.

(i) share of team-periods with mean shot x > 60 (evidence that events
    are already team-relative: a team's own shots cluster toward
    x=120 in ITS OWN events, regardless of which physical end of the
    pitch it actually defended).
(ii) opponent-goalkeeper x in shot freeze frames (median, share beyond
     x=100) -- the opponent's keeper, visible in the shooter's own
     frame, should sit near the defended goal if frames are
     self-consistent team-relative snapshots.
(iii) current (pre-fix) `team_period_directions` assignment counts --
      how many team-periods get +1 vs -1 today.

Run: python src/engine_v2/task24_evidence.py
"""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

from geometry import team_period_directions

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
EVENTS_DIR = DATA_DIR / "raw" / "events"
FRAMES_DIR = DATA_DIR / "raw" / "frames"
OUT_PATH = DATA_DIR / "engine_v2_task24_evidence.json"


def main():
    print("Task 24 Step 1(a): reproducing the coordinate evidence on all 299 matches ...")
    match_ids = sorted(int(p.stem) for p in EVENTS_DIR.glob("*.parquet"))

    team_period_shot_means = []  # (match_id, team, period, mean_shot_x, n_shots)
    direction_counts = {1: 0, -1: 0}
    keeper_xs = []

    for i, mid in enumerate(match_ids):
        events = pd.read_parquet(EVENTS_DIR / f"{mid}.parquet")
        events = events.sort_values("index").reset_index(drop=True)
        shots = events[events["type"] == "Shot"]
        teams = events["team"].dropna().unique().tolist()
        periods = sorted(events["period"].dropna().unique().tolist())

        for team in teams:
            for period in periods:
                tshots = shots[(shots["team"] == team) & (shots["period"] == period)]
                locs = [loc[0] for loc in tshots["location"] if loc is not None
                        and not (isinstance(loc, float) and pd.isna(loc))]
                if locs:
                    team_period_shot_means.append({
                        "match_id": mid, "team": team, "period": period,
                        "mean_shot_x": float(np.mean(locs)), "n_shots": len(locs),
                    })

        directions = team_period_directions(events)
        for d in directions.values():
            direction_counts[d] = direction_counts.get(d, 0) + 1

        frames = pd.read_parquet(FRAMES_DIR / f"{mid}.parquet")
        frames_by_event = {eid: g for eid, g in frames.groupby("id")}
        for _, srow in shots.iterrows():
            frame = frames_by_event.get(srow["id"])
            if frame is None or len(frame) == 0:
                continue
            keeper = frame[(frame["teammate"] == False) & (frame["keeper"] == True)]
            for loc in keeper["location"]:
                if loc is not None and not (isinstance(loc, float) and pd.isna(loc)):
                    keeper_xs.append(loc[0])

        if (i + 1) % 50 == 0:
            print(f"  {i + 1}/{len(match_ids)} matches processed")

    tp_df = pd.DataFrame(team_period_shot_means)
    share_mean_shot_x_gt_60 = float((tp_df["mean_shot_x"] > 60).mean())
    print(f"\n  team-periods with a shot: {len(tp_df)}")
    print(f"  share with mean shot x > 60: {share_mean_shot_x_gt_60:.4f} "
          f"(brief's first-40-match figure: 156/156 = 1.0000)")

    keeper_arr = np.array(keeper_xs)
    keeper_median = float(np.median(keeper_arr)) if len(keeper_arr) else None
    keeper_share_gt_100 = float((keeper_arr > 100).mean()) if len(keeper_arr) else None
    print(f"\n  opponent-keeper locations in shot frames: {len(keeper_arr)}")
    print(f"  median x: {keeper_median} (brief's figure: 117.4)")
    print(f"  share beyond x=100: {keeper_share_gt_100:.4f} (brief's figure: 0.999)" if keeper_share_gt_100 is not None else "")

    n_plus1, n_minus1 = direction_counts.get(1, 0), direction_counts.get(-1, 0)
    print(f"\n  current team_period_directions assignment counts (all 299 matches): "
          f"+1={n_plus1}, -1={n_minus1}, total={n_plus1 + n_minus1}")

    summary = {
        "n_matches": len(match_ids),
        "n_team_periods_with_shots": len(tp_df),
        "share_mean_shot_x_gt_60": share_mean_shot_x_gt_60,
        "n_keeper_locations_in_shot_frames": len(keeper_arr),
        "keeper_x_median": keeper_median,
        "keeper_x_share_gt_100": keeper_share_gt_100,
        "direction_assignment_counts": {"plus1": n_plus1, "minus1": n_minus1},
    }
    OUT_PATH.write_text(json.dumps(summary, indent=2, default=str))
    print(f"\nWrote {OUT_PATH}")
    return summary


if __name__ == "__main__":
    main()
