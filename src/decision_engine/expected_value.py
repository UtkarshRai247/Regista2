"""
Task 01 — Step 4: expected value of each option.

EV = p_success * V(state after successful pass)
     + (1 - p_success) * V(state after turnover, valued negatively from
       the possessing team's perspective)

Stated assumption (flagged in the results page, not silently chosen):
"state after turnover, valued negatively from the possessing team's
perspective" = evaluate the SAME Step 3 value model on the post-turnover
state from the new possessor's (opponent's) perspective, then negate to
express it in the original team's frame — the only construction
consistent with a single, symmetric trained V. The post-turnover phase
is modeled as "From Counter" (the new possessor has just won the ball in
a transitional moment); the post-success phase is modeled as "Regular
Play" (continued open-play possession).

Run: python src/decision_engine/expected_value.py
"""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb

from pitch_direction import team_period_directions, normalize_xy
from possession_value import FEATURES as PV_FEATURES, PATTERN_CODE

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
EVENTS_DIR = DATA_DIR / "raw" / "events"
SCORED_PATH = DATA_DIR / "processed" / "options_scored.parquet"
PV_MODEL_PATH = DATA_DIR / "processed" / "possession_value_model.json"
OUT_PATH = DATA_DIR / "processed" / "options_ev.parquet"


def main():
    opts = pd.read_parquet(SCORED_PATH)
    pv_model = xgb.XGBClassifier()
    pv_model.load_model(PV_MODEL_PATH)

    # direction lookup per (match_id, team, period) — one pass over each match's events
    directions_by_match = {}
    for mid in opts["match_id"].unique():
        ev = pd.read_parquet(EVENTS_DIR / f"{mid}.parquet")
        dirs, _, _ = team_period_directions(ev)
        directions_by_match[mid] = dirs

    # time_remaining_period / score_diff aren't stored in options.parquet;
    # approximate at the option level using the event's own values, pulled
    # from the events table (joined by match_id + event_id).
    ev_context = {}
    for mid in opts["match_id"].unique():
        ev = pd.read_parquet(EVENTS_DIR / f"{mid}.parquet")
        ev = ev.sort_values("index").reset_index(drop=True)
        ev["t"] = ev["minute"] * 60 + ev["second"]
        period_end = ev.groupby("period")["t"].transform("max")
        ev["time_remaining_period"] = period_end - ev["t"]
        teams = ev["team"].dropna().unique().tolist()
        score = {t: 0 for t in teams}
        is_goal = ((ev["type"] == "Shot") & (ev["shot_outcome"] == "Goal")) | (ev["type"] == "Own Goal Against")
        score_diff_col = []
        for i in range(len(ev)):
            row = ev.iloc[i]
            opp = [t for t in teams if t != row["team"]]
            opp = opp[0] if opp else None
            score_diff_col.append(score.get(row["team"], 0) - score.get(opp, 0) if opp else 0)
            if is_goal.iloc[i]:
                scorer = row["team"]
                if row["type"] == "Own Goal Against":
                    scorer = opp
                if scorer in score:
                    score[scorer] += 1
        ev["score_diff"] = score_diff_col
        for _, r in ev.iterrows():
            ev_context[(mid, r["id"])] = (r["time_remaining_period"], r["score_diff"])

    rows_success, rows_turnover = [], []
    for _, r in opts.iterrows():
        mid, eid, team, period = r["match_id"], r["event_id"], r["team"], r["period"]
        direction = directions_by_match[mid].get((team, period), 1)
        time_remaining, score_diff = ev_context.get((mid, eid), (np.nan, 0))

        ax, ay = normalize_xy(r["candidate_x"], r["candidate_y"], direction)
        px, py = normalize_xy(r["passer_x"], r["passer_y"], direction)
        rows_success.append({
            "ball_x": ax, "ball_y": ay, "prev_x": px, "prev_y": py,
            "time_remaining_period": time_remaining, "score_diff": score_diff,
            "play_pattern_code": PATTERN_CODE["Regular Play"],
        })

        opp_direction = -direction
        tx, ty = normalize_xy(r["candidate_x"], r["candidate_y"], opp_direction)
        px, py = normalize_xy(r["passer_x"], r["passer_y"], opp_direction)
        rows_turnover.append({
            "ball_x": tx, "ball_y": ty, "prev_x": px, "prev_y": py,
            "time_remaining_period": time_remaining, "score_diff": -score_diff,
            "play_pattern_code": PATTERN_CODE["From Counter"],
        })

    X_success = pd.DataFrame(rows_success)[PV_FEATURES]
    X_turnover = pd.DataFrame(rows_turnover)[PV_FEATURES]

    v_success = pv_model.predict_proba(X_success)[:, 1]
    v_turnover_opponent = pv_model.predict_proba(X_turnover)[:, 1]
    v_turnover = -v_turnover_opponent  # negate to express in original team's frame

    opts["v_success"] = v_success
    opts["v_turnover"] = v_turnover
    opts["ev"] = opts["p_success"] * v_success + (1 - opts["p_success"]) * v_turnover

    opts.to_parquet(OUT_PATH)

    summary = {
        "ev_chosen": opts.loc[opts["chosen"], "ev"].describe().to_dict(),
        "ev_unchosen": opts.loc[~opts["chosen"], "ev"].describe().to_dict(),
    }
    print(json.dumps(summary, indent=2, default=float))
    (DATA_DIR / "expected_value_summary.json").write_text(json.dumps(summary, indent=2, default=float))


if __name__ == "__main__":
    main()
