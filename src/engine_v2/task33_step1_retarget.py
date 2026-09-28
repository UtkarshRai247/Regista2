"""
Task 33, Step 1 (fix A3): score incomplete passes by where they were
aimed. For every INCOMPLETE eligible pass, among visible teammates
(teammate=True, not the passer) in its freeze frame: keep those within
15 degrees of the pass direction (passer -> end location) AND within 10
units of the pass end location; the intended target is the one closest
to the end location among those. If a target exists: status=retargeted,
target = that teammate's raw freeze-frame location (which, by
construction in grid.py, IS an existing is_teammate_destination==1
candidate row's (candidate_x, candidate_y) -- matching that row to an
actual scored candidate is done in crossfit_v6.py, where the match's
candidate rows are already loaded, not duplicated here). If no target
exists: status=excluded (kept in the data, flagged). Completed passes:
status=unchanged.

Eligibility mirrors grid.py's own gate exactly (same EXCLUDED_PASS_TYPES
import, same frame>=6/end-location checks) so this script's population
matches options_ev_v4's 292-match, 250,850-pass corpus exactly.

Run: python src/engine_v2/task33_step1_retarget.py
"""
import json
import math
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

from grid import EXCLUDED_PASS_TYPES

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
EVENTS_DIR = DATA_DIR / "raw" / "events"
FRAMES_DIR = DATA_DIR / "raw" / "frames"
EV_DIR = DATA_DIR / "processed" / "engine_v2" / "options_ev_v4"
OUT_PATH = DATA_DIR / "processed" / "engine_v2" / "incomplete_retarget_v6.parquet"
SUMMARY_PATH = DATA_DIR / "engine_v2_task33_step1.json"

MAX_ANGLE_DEG = 15.0
MAX_DIST_TO_END_U = 10.0


def find_intended_target(passer_raw, end_raw, teammates_raw):
    if len(teammates_raw) == 0:
        return None
    line_vec = end_raw - passer_raw
    line_len = np.hypot(*line_vec)
    if line_len < 1e-6:
        return None
    line_angle = math.degrees(math.atan2(line_vec[1], line_vec[0]))
    to_team = teammates_raw - passer_raw
    team_angle = np.degrees(np.arctan2(to_team[:, 1], to_team[:, 0]))
    ang_diff = np.abs((team_angle - line_angle + 180) % 360 - 180)
    dist_to_end = np.hypot(teammates_raw[:, 0] - end_raw[0], teammates_raw[:, 1] - end_raw[1])
    mask = (ang_diff <= MAX_ANGLE_DEG) & (dist_to_end <= MAX_DIST_TO_END_U)
    if not mask.any():
        return None
    masked_dist = np.where(mask, dist_to_end, np.inf)
    idx = int(np.argmin(masked_dist))
    return teammates_raw[idx]


def process_match(match_id: int) -> list:
    events = pd.read_parquet(EVENTS_DIR / f"{match_id}.parquet").sort_values("index").reset_index(drop=True)
    frames = pd.read_parquet(FRAMES_DIR / f"{match_id}.parquet")
    frames_by_event = {eid: g for eid, g in frames.groupby("id")}

    passes = events[(events["type"] == "Pass") & (~events["pass_type"].isin(EXCLUDED_PASS_TYPES))
                     & (events["position"] != "Goalkeeper")]
    rows = []
    for _, ev in passes.iterrows():
        eid = ev["id"]
        frame = frames_by_event.get(eid)
        if frame is None or len(frame) < 6:
            continue
        end_loc = ev.get("pass_end_location")
        if end_loc is None or (isinstance(end_loc, float) and pd.isna(end_loc)):
            continue

        pass_complete = bool(pd.isna(ev.get("pass_outcome")))
        if pass_complete:
            rows.append({"match_id": match_id, "event_id": eid, "status": "unchanged",
                         "target_x": None, "target_y": None, "distance_moved": None})
            continue

        passer_raw = np.array(ev["location"], dtype=float)
        end_raw = np.array(end_loc, dtype=float)
        teammates = frame[(frame["teammate"] == True) & (frame["actor"] == False)]
        teammates_raw = np.array([list(l) for l in teammates["location"]], dtype=float) if len(teammates) else np.zeros((0, 2))

        target = find_intended_target(passer_raw, end_raw, teammates_raw)
        if target is None:
            rows.append({"match_id": match_id, "event_id": eid, "status": "excluded",
                         "target_x": None, "target_y": None, "distance_moved": None})
        else:
            dist_moved = float(np.hypot(target[0] - end_raw[0], target[1] - end_raw[1]))
            rows.append({"match_id": match_id, "event_id": eid, "status": "retargeted",
                         "target_x": float(target[0]), "target_y": float(target[1]),
                         "distance_moved": dist_moved})
    return rows


def main():
    print("Task 33 Step 1 (A3): retargeting incomplete passes ...")
    match_ids = sorted(int(p.stem) for p in EV_DIR.glob("*.parquet"))
    print(f"  {len(match_ids)} matches")

    all_rows = []
    for i, mid in enumerate(match_ids):
        all_rows.extend(process_match(mid))
        if (i + 1) % 50 == 0:
            print(f"    {i + 1}/{len(match_ids)} matches, rows so far={len(all_rows)}")

    df = pd.DataFrame(all_rows)
    df.to_parquet(OUT_PATH)
    print(f"\n  total eligible passes: {len(df)}")

    counts = df["status"].value_counts().to_dict()
    print(f"  counts: {counts}")

    retargeted = df[df["status"] == "retargeted"]
    median_dist_moved = float(retargeted["distance_moved"].median()) if len(retargeted) else None
    print(f"  median distance moved by retargeted passes: {median_dist_moved}")

    summary = {
        "n_eligible_total": len(df), "counts": counts,
        "n_retargeted": int(counts.get("retargeted", 0)), "n_excluded": int(counts.get("excluded", 0)),
        "n_unchanged": int(counts.get("unchanged", 0)),
        "median_distance_moved_retargeted": median_dist_moved,
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
    print(f"\nWrote {SUMMARY_PATH} and {OUT_PATH}")
    return summary


if __name__ == "__main__":
    main()
