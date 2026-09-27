"""
Task 25, Step 2 (Task 24's Step 4): shared corpus-wide application of
THIS task's newly selected offside rule (offside_diagnostic_v3.py's
winner: R1_K10 -- K>=10 visible opponents, NO M tolerance, NOT
attacking-half-restricted -- different in composition from Task 19c's
R4, since recalibrating on the corrected geometry selects a different
rule). Mirrors `offside_v2.py`'s structure exactly, parameters changed
to this task's own selection.

Run standalone for a smoke check: python src/engine_v2/offside_v4.py
"""
import warnings

import numpy as np
import pandas as pd

from geometry import team_period_directions, normalize_xy

warnings.filterwarnings("ignore")

SELECTED_K = 10
SELECTED_M = 0.0
SELECTED_ATTACKING_HALF_ONLY = False


def add_offside_v4_column(cand: pd.DataFrame, events: pd.DataFrame, frames: pd.DataFrame) -> pd.DataFrame:
    frames_by_event = {eid: g for eid, g in frames.groupby("id")}
    directions = team_period_directions(events)

    cand = cand.copy()
    cand["offside_v4"] = False
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
        cand.loc[g.index, "offside_v4"] = flag
    return cand
