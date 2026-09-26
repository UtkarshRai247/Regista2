"""
Task 19c, Step 3 (continued): recomputes the per-pass policy summary
(Decision, Risk) using the corrected+calibrated offside rule + its own
refit temperature, applied to the full 106,141,669-row corpus.

Run: python src/engine_v2/policy_score_v5.py
"""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb

from common import CANDIDATE_FEATURES, prep_X
from policy_baseline_fix import RESTRICT_MIN_P_SUCCESS, RESTRICT_MAX_DISTANCE_U, POLICY_MODEL_PATH
from offside_v2 import add_offside_v2_column

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
EVENTS_DIR = DATA_DIR / "raw" / "events"
FRAMES_DIR = DATA_DIR / "raw" / "frames"
EV_DIR = DATA_DIR / "processed" / "engine_v2" / "options_ev"
STEP3_SUMMARY_PATH = DATA_DIR / "engine_v2_step3_policy_baseline_fix_v3.json"
OUT_PATH = DATA_DIR / "processed" / "engine_v2" / "pass_policy_summary_v5.parquet"
SUMMARY_PATH = DATA_DIR / "engine_v2_step3_recompute_v3.json"


def softmax_per_group(scores: np.ndarray, groups: np.ndarray) -> np.ndarray:
    df = pd.DataFrame({"score": scores, "group": groups})
    out = np.empty(len(df))
    for _, g in df.groupby("group"):
        s = g["score"].values
        e = np.exp(s - s.max())
        out[g.index] = e / e.sum()
    return out


def process_match(match_id: int, model, fill_values: dict, T: float) -> list:
    df = pd.read_parquet(EV_DIR / f"{match_id}.parquet")
    events = pd.read_parquet(EVENTS_DIR / f"{match_id}.parquet").sort_values("index").reset_index(drop=True)
    frames = pd.read_parquet(FRAMES_DIR / f"{match_id}.parquet")
    df = add_offside_v2_column(df, events, frames)

    restricted = df[(df["p_success"] >= RESTRICT_MIN_P_SUCCESS) & (df["distance_u"] <= RESTRICT_MAX_DISTANCE_U)
                     & (~df["offside_v2"])].copy()

    X, _ = prep_X(restricted, CANDIDATE_FEATURES, fill_values)
    raw_score = model.predict_proba(X)[:, 1]
    restricted["policy_probability"] = softmax_per_group(raw_score / T, restricted["event_id"].values)
    restricted["var_option"] = restricted["p_success"] * (1 - restricted["p_success"]) * \
        (restricted["V_net_success"] - restricted["V_net_turnover"]) ** 2
    restricted["ev_x_prob"] = restricted["EV"] * restricted["policy_probability"]
    restricted["var_x_prob"] = restricted["var_option"] * restricted["policy_probability"]

    all_chosen = df[df["chosen"]].set_index("event_id")
    all_var_chosen = all_chosen["p_success"] * (1 - all_chosen["p_success"]) * \
        (all_chosen["V_net_success"] - all_chosen["V_net_turnover"]) ** 2

    rows = []
    n_zero_survivors = 0
    all_event_ids = df["event_id"].unique()
    grouped = {eid: g for eid, g in restricted.groupby("event_id", sort=False)}
    for eid in all_event_ids:
        g = grouped.get(eid)
        chosen_row = all_chosen.loc[eid] if eid in all_chosen.index else None
        if g is None or len(g) == 0:
            n_zero_survivors += 1
            policy_weighted_ev, policy_weighted_var = None, None
        else:
            policy_weighted_ev = float(g["ev_x_prob"].sum())
            policy_weighted_var = float(g["var_x_prob"].sum())
        rows.append({
            "match_id": match_id, "event_id": eid,
            "team": chosen_row["team"] if chosen_row is not None else None,
            "ev_chosen": float(chosen_row["EV"]) if chosen_row is not None else None,
            "var_chosen": float(all_var_chosen.loc[eid]) if chosen_row is not None else None,
            "policy_weighted_ev": policy_weighted_ev, "policy_weighted_var": policy_weighted_var,
            "n_restricted_candidates": int(len(g)) if g is not None else 0,
        })
    return rows, n_zero_survivors


def main():
    print("Step 3: recomputing policy summary with the corrected+calibrated offside rule (full corpus) ...")
    model = xgb.XGBClassifier()
    model.load_model(str(POLICY_MODEL_PATH))
    step3 = json.loads(STEP3_SUMMARY_PATH.read_text())
    T = step3["fitted_temperature"]
    fill_values = step3["fill_values"]
    print(f"  using fitted temperature T={T:.4f}")

    match_ids = sorted(int(p.stem) for p in EV_DIR.glob("*.parquet"))
    all_rows, n_zero_total = [], 0
    for i, mid in enumerate(match_ids):
        rows, nz = process_match(mid, model, fill_values, T)
        all_rows.extend(rows)
        n_zero_total += nz
        if (i + 1) % 50 == 0:
            print(f"  {i + 1}/{len(match_ids)} matches, passes so far={len(all_rows)}")

    summary_df = pd.DataFrame(all_rows)
    summary_df.to_parquet(OUT_PATH)
    print(f"  {len(summary_df)} passes; {n_zero_total} passes had zero surviving restricted candidates")

    report = {
        "temperature_used": T, "n_passes": len(summary_df),
        "n_passes_zero_restricted_candidates": n_zero_total,
        "n_restricted_candidates_distribution": {
            str(p): float(np.percentile(summary_df["n_restricted_candidates"], p)) for p in (5, 25, 50, 75, 95)},
    }
    SUMMARY_PATH.write_text(json.dumps(report, indent=2, default=str))
    print(json.dumps(report, indent=2, default=str))
    print(f"\nWrote {SUMMARY_PATH}")
    return report


if __name__ == "__main__":
    main()
