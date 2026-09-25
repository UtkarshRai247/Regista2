"""
Task 15 -- Engine v2, Step 2 (option space) fused with Step 3 (shared
candidate features -- see features.py's docstring for why they're
computed in one per-match pass rather than two).

Option space (docs/specs/engine-v2-rebuild.md section 1): a fixed
global 4-yard grid covering the whole pitch (cell centers at
x=2,6,...,118 / y=2,6,...,78, all inside the pitch by construction),
restricted per pass to cells within 60 yards of the passer, PLUS every
visible teammate's exact position as its own candidate
(is_teammate_destination=1). The CHOSEN option is the grid cell
containing pass_end_location -- always included as a candidate even in
the rare case (~0.8% of passes, confirmed by direct sampling) its
distance from the passer exceeds 60 yards, since dropping the true
destination would reintroduce exactly the "chosen option missing"
problem this rebuild exists to fix; the count of such extensions is
reported (n_extended_beyond_60y).

Eligibility gate (unchanged from src/decision_engine/options.py, reused
as a definition only, not by import): Pass type, not in
EXCLUDED_PASS_TYPES, non-goalkeeper passer, a freeze frame with >=6
visible players, and a valid pass_end_location. No angle-matching, no
ambiguity rule -- every eligible pass gets a chosen candidate by
construction, so none are dropped for this reason.

Run: python src/engine_v2/grid.py
"""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

from geometry import PITCH_X, PITCH_Y, GRID_STEP, team_period_directions
from features import compute_candidate_features

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
EVENTS_DIR = DATA_DIR / "raw" / "events"
FRAMES_DIR = DATA_DIR / "raw" / "frames"
OUT_DIR = DATA_DIR / "processed" / "engine_v2" / "options_parts"
SUMMARY_PATH = DATA_DIR / "engine_v2_step2_options.json"

EXCLUDED_PASS_TYPES = {"Corner", "Free Kick", "Throw-in", "Kick Off", "Goal Kick"}
MAX_DIST_U = 60.0
V1_MATCHED_PASSES = 171618

_gx = np.arange(GRID_STEP / 2, PITCH_X, GRID_STEP)
_gy = np.arange(GRID_STEP / 2, PITCH_Y, GRID_STEP)
_GX, _GY = np.meshgrid(_gx, _gy)
GRID_CELLS = np.stack([_GX.ravel(), _GY.ravel()], axis=1)  # (600, 2), fixed for the whole module


def chosen_cell(end_loc: np.ndarray) -> np.ndarray:
    x = min(max(np.floor(end_loc[0] / GRID_STEP) * GRID_STEP + GRID_STEP / 2, GRID_STEP / 2), PITCH_X - GRID_STEP / 2)
    y = min(max(np.floor(end_loc[1] / GRID_STEP) * GRID_STEP + GRID_STEP / 2, GRID_STEP / 2), PITCH_Y - GRID_STEP / 2)
    return np.array([x, y])


def process_match(match_id: int) -> tuple:
    events = pd.read_parquet(EVENTS_DIR / f"{match_id}.parquet")
    frames = pd.read_parquet(FRAMES_DIR / f"{match_id}.parquet")
    events = events.sort_values("index").reset_index(drop=True)

    passes = events[(events["type"] == "Pass") & (~events["pass_type"].isin(EXCLUDED_PASS_TYPES))
                     & (events["position"] != "Goalkeeper")].copy()
    frames_by_event = {eid: g for eid, g in frames.groupby("id")}
    directions = team_period_directions(events)

    stats = {"eligible": 0, "no_frame": 0, "too_few_visible": 0, "no_end_loc": 0,
              "n_extended_beyond_60y": 0, "option_set_sizes": [], "displacements": []}
    rows = []

    for _, ev in passes.iterrows():
        eid = ev["id"]
        frame = frames_by_event.get(eid)
        if frame is None or len(frame) == 0:
            stats["no_frame"] += 1
            continue
        if len(frame) < 6:
            stats["too_few_visible"] += 1
            continue
        end_loc = ev.get("pass_end_location")
        if end_loc is None or (isinstance(end_loc, float) and pd.isna(end_loc)):
            stats["no_end_loc"] += 1
            continue

        stats["eligible"] += 1
        passer_raw = np.array(ev["location"], dtype=float)
        end_raw = np.array(end_loc, dtype=float)
        direction = directions.get((ev["team"], ev["period"]), 1)

        teammates = frame[(frame["teammate"] == True) & (frame["actor"] == False)]
        opponents = frame[frame["teammate"] == False]
        teammates_raw = np.array([list(l) for l in teammates["location"]], dtype=float) if len(teammates) else np.zeros((0, 2))
        opponents_raw = np.array([list(l) for l in opponents["location"]], dtype=float) if len(opponents) else np.zeros((0, 2))

        dist_to_grid = np.hypot(GRID_CELLS[:, 0] - passer_raw[0], GRID_CELLS[:, 1] - passer_raw[1])
        grid_cands = GRID_CELLS[dist_to_grid <= MAX_DIST_U]

        chosen_xy = chosen_cell(end_raw)
        displacement = float(np.hypot(chosen_xy[0] - end_raw[0], chosen_xy[1] - end_raw[1]))
        stats["displacements"].append(displacement)

        already_included = bool(np.any(np.all(np.isclose(grid_cands, chosen_xy, atol=1e-6), axis=1))) if len(grid_cands) else False
        if not already_included:
            grid_cands = np.vstack([grid_cands, chosen_xy]) if len(grid_cands) else chosen_xy[None, :]
            stats["n_extended_beyond_60y"] += 1

        n_grid, n_team = len(grid_cands), len(teammates_raw)
        candidates_raw = np.vstack([grid_cands, teammates_raw]) if n_team else grid_cands
        is_teammate_destination = np.concatenate([np.zeros(n_grid, dtype=int), np.ones(n_team, dtype=int)])
        stats["option_set_sizes"].append(len(candidates_raw))

        feats = compute_candidate_features(passer_raw, candidates_raw, is_teammate_destination,
                                            direction, opponents_raw, teammates_raw, len(frame))

        chosen_mask = ((is_teammate_destination == 0)
                       & np.isclose(candidates_raw[:, 0], chosen_xy[0], atol=1e-6)
                       & np.isclose(candidates_raw[:, 1], chosen_xy[1], atol=1e-6))

        df = pd.DataFrame(feats)
        df.insert(0, "match_id", match_id)
        df.insert(1, "event_id", eid)
        df["team"] = ev["team"]
        df["period"] = int(ev["period"])
        df["player_id"] = ev.get("player_id")
        df["passer_x"] = passer_raw[0]
        df["passer_y"] = passer_raw[1]
        df["candidate_x"] = candidates_raw[:, 0]
        df["candidate_y"] = candidates_raw[:, 1]
        df["chosen"] = chosen_mask
        df["pass_complete"] = bool(pd.isna(ev.get("pass_outcome")))
        df["pass_length"] = ev.get("pass_length")
        df["under_pressure"] = bool(ev["under_pressure"]) if pd.notna(ev.get("under_pressure")) else False
        rows.append(df)

    if rows:
        out = pd.concat(rows, ignore_index=True)
        for c in out.select_dtypes(include=["float64"]).columns:
            out[c] = out[c].astype("float32")
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        out.to_parquet(OUT_DIR / f"{match_id}.parquet")
        n_out = len(out)
    else:
        n_out = 0
    return stats, n_out


def main():
    match_ids = sorted(int(p.stem) for p in EVENTS_DIR.glob("*.parquet"))
    agg = {"eligible": 0, "no_frame": 0, "too_few_visible": 0, "no_end_loc": 0,
           "n_extended_beyond_60y": 0, "option_set_sizes": [], "displacements": [], "n_rows_total": 0}
    for i, mid in enumerate(match_ids):
        stats, n_out = process_match(mid)
        for k in ("eligible", "no_frame", "too_few_visible", "no_end_loc", "n_extended_beyond_60y"):
            agg[k] += stats[k]
        agg["option_set_sizes"].extend(stats["option_set_sizes"])
        agg["displacements"].extend(stats["displacements"])
        agg["n_rows_total"] += n_out
        if (i + 1) % 20 == 0:
            print(f"  {i + 1}/{len(match_ids)} matches, eligible so far={agg['eligible']}, rows so far={agg['n_rows_total']}")

    sizes = np.array(agg["option_set_sizes"])
    disp = np.array(agg["displacements"])
    summary = {
        "n_matches": len(match_ids),
        "eligible_passes": agg["eligible"],
        "no_frame": agg["no_frame"], "too_few_visible": agg["too_few_visible"], "no_end_loc": agg["no_end_loc"],
        "n_extended_beyond_60y": agg["n_extended_beyond_60y"],
        "v1_eligible_matched_passes": V1_MATCHED_PASSES,
        "options_per_pass_mean": float(sizes.mean()), "options_per_pass_median": float(np.median(sizes)),
        "options_per_pass_p90": float(np.percentile(sizes, 90)),
        "T1_median_displacement_u": float(np.median(disp)),
        "T1_pass_condition_le_2u": bool(np.median(disp) <= 2.0),
        "n_candidate_rows_total": agg["n_rows_total"],
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
    print(json.dumps(summary, indent=2, default=str))
    return summary


if __name__ == "__main__":
    main()
