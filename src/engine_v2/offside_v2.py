"""
Task 19c, Step 3: shared corpus-wide computation of the SELECTED
calibrated offside rule (Task 19c Step 2's winner: K>=10 visible
opponents, attacking-half-only, M=1 yard tolerance, using the
CORRECTED second-rearmost-opponent index), applied to every candidate
in a match's options_ev table -- not just chosen destinations, since the
restriction filter needs the flag on every candidate.

This is a corpus-wide re-derivation of the SAME rule already validated
against ground truth in offside_diagnostic_v2.py; it does not change
features.py again (already fixed, once) or any other engine component.

Run standalone for a smoke check: python src/engine_v2/offside_v2.py
"""
import warnings

import numpy as np
import pandas as pd

from geometry import team_period_directions, normalize_xy

warnings.filterwarnings("ignore")

SELECTED_K = 10
SELECTED_M = 1.0
SELECTED_ATTACKING_HALF_ONLY = True


def add_offside_v2_column(cand: pd.DataFrame, events: pd.DataFrame, frames: pd.DataFrame) -> pd.DataFrame:
    """cand: a match's full options_ev candidate rows (event_id, team,
    period, candidate_x, candidate_y, passer_x, passer_y, ...). Adds
    `offside_v2` (bool). events/frames: that match's raw event/frame
    tables (for direction inference and opponent positions)."""
    frames_by_event = {eid: g for eid, g in frames.groupby("id")}
    directions = team_period_directions(events)

    cand = cand.copy()
    cand["offside_v2"] = False
    for eid, g in cand.groupby("event_id", sort=False):
        team, period = g["team"].iloc[0], g["period"].iloc[0]
        direction = directions.get((team, period), 1)
        frame = frames_by_event.get(eid)
        if frame is None:
            continue
        opponents = frame[frame["teammate"] == False]
        n_opp = len(opponents)
        if n_opp < 2 or n_opp < SELECTED_K:
            continue
        opp_raw = np.array([list(l) for l in opponents["location"]], dtype=float)
        opp_nx = np.array([normalize_xy(x, y, direction)[0] for x, y in opp_raw])
        second_rearmost_nx = float(np.sort(opp_nx)[-2])

        passer_nx, _ = normalize_xy(g["passer_x"].iloc[0], g["passer_y"].iloc[0], direction)
        cand_nx = np.array([normalize_xy(x, y, direction)[0] for x, y in zip(g["candidate_x"], g["candidate_y"])])

        flag = (cand_nx > (second_rearmost_nx + SELECTED_M)) & (cand_nx > passer_nx)
        if SELECTED_ATTACKING_HALF_ONLY:
            flag = flag & (cand_nx >= 60.0)
        cand.loc[g.index, "offside_v2"] = flag
    return cand


if __name__ == "__main__":
    from pathlib import Path
    DATA_DIR = Path(__file__).parent.parent.parent / "data"
    mid = 3764440
    cand = pd.read_parquet(DATA_DIR / "processed" / "engine_v2" / "options_ev" / f"{mid}.parquet")
    events = pd.read_parquet(DATA_DIR / "raw" / "events" / f"{mid}.parquet").sort_values("index").reset_index(drop=True)
    frames = pd.read_parquet(DATA_DIR / "raw" / "frames" / f"{mid}.parquet")
    out = add_offside_v2_column(cand, events, frames)
    print(f"match {mid}: {out['offside_v2'].mean():.4f} share flagged offside_v2 (of {len(out)} candidates)")
    chosen = out[out["chosen"]]
    print(f"  chosen-row share flagged: {chosen['offside_v2'].mean():.4f} (of {len(chosen)} chosen)")
