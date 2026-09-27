"""
Task 25, Step 2 (Task 24's Step 4): refit the softmax temperature on
`options_ev_v4` (corrected geometry). Restriction: p_success>=0.05 AND
distance_u<=45 (Task 18's own thresholds, kept unchanged and disclosed
as originally set on the old, half-flipped coordinates) AND NOT
offside_v4 (THIS task's newly selected offside rule from
offside_diagnostic_v3.py -- R1_K10, not Task 19c's R4, since
recalibrating on the corrected geometry selects a different rule).

Run: python src/engine_v2/policy_baseline_fix_v5.py
"""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb

from common import match_disjoint_split, CANDIDATE_FEATURES, prep_X
from offside_v4 import add_offside_v4_column
from policy_baseline_fix import (
    fit_temperature, policy_metrics, POLICY_MODEL_PATH,
    RESTRICT_MIN_P_SUCCESS, RESTRICT_MAX_DISTANCE_U, RNG_SEED, TEST_SIZE,
)

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
EVENTS_DIR = DATA_DIR / "raw" / "events"
FRAMES_DIR = DATA_DIR / "raw" / "frames"
EV_DIR = DATA_DIR / "processed" / "engine_v2" / "options_ev_v4"
TASK19C_SUMMARY_PATH = DATA_DIR / "engine_v2_step3_policy_baseline_fix_v3.json"
SUMMARY_PATH = DATA_DIR / "engine_v2_step3_policy_baseline_fix_v5.json"


def load_scored_match_with_offside_v4(mid: int, model, fill_values: dict) -> pd.DataFrame:
    cols = CANDIDATE_FEATURES + ["match_id", "event_id", "team", "period", "chosen", "p_success",
                                   "candidate_x", "candidate_y", "passer_x", "passer_y", "EV"]
    df = pd.read_parquet(EV_DIR / f"{mid}.parquet", columns=cols)
    X, _ = prep_X(df, CANDIDATE_FEATURES, fill_values)
    df["raw_score"] = model.predict_proba(X)[:, 1]

    events = pd.read_parquet(EVENTS_DIR / f"{mid}.parquet").sort_values("index").reset_index(drop=True)
    frames = pd.read_parquet(FRAMES_DIR / f"{mid}.parquet")
    df = add_offside_v4_column(df, events, frames)
    return df


def restrict_with_offside_v4(df: pd.DataFrame) -> pd.DataFrame:
    return df[(df["p_success"] >= RESTRICT_MIN_P_SUCCESS) & (df["distance_u"] <= RESTRICT_MAX_DISTANCE_U)
              & (~df["offside_v4"])]


def main():
    print("Task 25 Step 2: refitting temperature on options_ev_v4, offside_v4 (R1_K10) restriction ...")
    model = xgb.XGBClassifier()
    model.load_model(str(POLICY_MODEL_PATH))

    match_ids = sorted(int(p.stem) for p in EV_DIR.glob("*.parquet"))
    fill_values = {c: -np.inf for c in CANDIDATE_FEATURES}
    for mid in match_ids:
        df = pd.read_parquet(EV_DIR / f"{mid}.parquet", columns=CANDIDATE_FEATURES)
        for c in CANDIDATE_FEATURES:
            m = df[c].max()
            if pd.notna(m) and m > fill_values[c]:
                fill_values[c] = float(m)

    match_df = pd.DataFrame({"match_id": match_ids})
    train_matches, test_matches = match_disjoint_split(match_df, "match_id", TEST_SIZE, RNG_SEED)
    train_ids, test_ids = set(train_matches["match_id"]), set(test_matches["match_id"])
    print(f"  match-disjoint split: {len(train_ids)} train, {len(test_ids)} test matches (same seed as every prior task)")

    print("  scoring + computing offside_v4 for train matches ...")
    train_df = pd.concat([load_scored_match_with_offside_v4(mid, model, fill_values) for mid in sorted(train_ids)], ignore_index=True)
    print("  scoring + computing offside_v4 for test matches ...")
    test_df = pd.concat([load_scored_match_with_offside_v4(mid, model, fill_values) for mid in sorted(test_ids)], ignore_index=True)

    task19c = json.loads(TASK19C_SUMMARY_PATH.read_text())

    print("  restricting candidate set (p_success>=0.05, distance_u<=45, NOT offside_v4) ...")
    train_restricted = restrict_with_offside_v4(train_df)
    test_restricted = restrict_with_offside_v4(test_df)
    per_pass_counts = test_restricted.groupby("event_id").size()
    print(f"    restricted candidates/pass (test): mean={per_pass_counts.mean():.1f}, "
          f"median={per_pass_counts.median():.1f}, p90={per_pass_counts.quantile(0.9):.1f}")

    print("  fitting temperature on training matches' restricted candidates ...")
    T_fitted = fit_temperature(train_restricted)
    print(f"    fitted temperature: {T_fitted:.4f} (Task 19c's value was {task19c['fitted_temperature']:.4f})")

    print("  AFTER (restricted candidate set, options_ev_v4, offside_v4, refit temperature) ...")
    after = policy_metrics(test_restricted, T=T_fitted, restricted=True)
    print(f"    {after}")

    behavioral = after["median_effective_options"] < 100 and after["corr_policy_weighted_vs_unweighted_mean_ev"] < 0.95
    print(f"\n  PRE-SPECIFIED READING: baseline is {'BEHAVIORAL' if behavioral else 'STILL NOT BEHAVIORAL'} "
          f"(median effective options {after['median_effective_options']:.1f}, "
          f"corr {after['corr_policy_weighted_vs_unweighted_mean_ev']:.4f})")

    summary = {
        "n_train_matches": len(train_ids), "n_test_matches": len(test_ids),
        "restricted_candidates_per_pass_test": {
            "mean": float(per_pass_counts.mean()), "median": float(per_pass_counts.median()),
            "p90": float(per_pass_counts.quantile(0.9))},
        "fitted_temperature": T_fitted,
        "task19c_temperature": task19c["fitted_temperature"],
        "task19c_after": task19c["task19c_after_corrected_offside"] if "task19c_after_corrected_offside" in task19c else task19c.get("after"),
        "after": after,
        "pre_specified_reading": {"median_effective_options_lt_100": after["median_effective_options"] < 100,
                                    "correlation_lt_0.95": after["corr_policy_weighted_vs_unweighted_mean_ev"] < 0.95,
                                    "behavioral": behavioral},
        "fill_values": fill_values,
        "train_match_ids": sorted(train_ids), "test_match_ids": sorted(test_ids),
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
    print(f"\nWrote {SUMMARY_PATH}")
    return summary


if __name__ == "__main__":
    main()
