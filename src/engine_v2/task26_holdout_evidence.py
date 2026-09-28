"""
Task 26, Step 1(a): reproduce task24_evidence.py's coordinate checks
(share of team-periods with mean shot x>60, opponent-keeper x in shot
frames, direction-assignment counts) on the untouched holdout matches
(data/raw_holdout/), to confirm the same team-relative coordinate
convention holds there before scoring it with the frozen engine v5.

Adapted (not a pure monkeypatched reuse of task24_evidence.main()):
one holdout match (3845506) has an events file but no frames file
(Task 23's own recorded 360-data parse failure) -- task24_evidence.py's
loop assumes every match has both, which never failed on the study
sample. This version skips a match's frame-dependent checks (keeper x)
when its frames file is absent, and reports the count skipped; the
shot-mean-x check (events only) and direction-assignment count are
unaffected and cover all 126 matches.

Run: python src/engine_v2/task26_holdout_evidence.py
"""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

from geometry import team_period_directions

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
EVENTS_DIR = DATA_DIR / "raw_holdout" / "events"
FRAMES_DIR = DATA_DIR / "raw_holdout" / "frames"
OUT_PATH = DATA_DIR / "engine_v2_task26_holdout_evidence.json"


def main():
    print("Task 26 Step 1(a): coordinate evidence on the holdout (126 matches) ...")
    match_ids = sorted(int(p.stem) for p in EVENTS_DIR.glob("*.parquet"))

    team_period_shot_means = []
    direction_counts = {1: 0, -1: 0}
    keeper_xs = []
    n_matches_no_frames = 0

    for mid in match_ids:
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

        frames_path = FRAMES_DIR / f"{mid}.parquet"
        if not frames_path.exists():
            n_matches_no_frames += 1
            continue
        frames = pd.read_parquet(frames_path)
        frames_by_event = {eid: g for eid, g in frames.groupby("id")}
        for _, srow in shots.iterrows():
            frame = frames_by_event.get(srow["id"])
            if frame is None or len(frame) == 0:
                continue
            keeper = frame[(frame["teammate"] == False) & (frame["keeper"] == True)]
            for loc in keeper["location"]:
                if loc is not None and not (isinstance(loc, float) and pd.isna(loc)):
                    keeper_xs.append(loc[0])

    tp_df = pd.DataFrame(team_period_shot_means)
    share_mean_shot_x_gt_60 = float((tp_df["mean_shot_x"] > 60).mean())
    print(f"\n  team-periods with a shot: {len(tp_df)}")
    print(f"  share with mean shot x > 60: {share_mean_shot_x_gt_60:.4f}")
    print(f"  matches skipped for the keeper check (no frames file): {n_matches_no_frames}")

    keeper_arr = np.array(keeper_xs)
    keeper_median = float(np.median(keeper_arr)) if len(keeper_arr) else None
    keeper_share_gt_100 = float((keeper_arr > 100).mean()) if len(keeper_arr) else None
    print(f"\n  opponent-keeper locations in shot frames: {len(keeper_arr)}")
    print(f"  median x: {keeper_median}")
    print(f"  share beyond x=100: {keeper_share_gt_100}")

    n_plus1, n_minus1 = direction_counts.get(1, 0), direction_counts.get(-1, 0)
    print(f"\n  team_period_directions assignment counts (post-Task-24-fix, all should be +1): "
          f"+1={n_plus1}, -1={n_minus1}")

    summary = {
        "n_matches": len(match_ids), "n_matches_no_frames": n_matches_no_frames,
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
