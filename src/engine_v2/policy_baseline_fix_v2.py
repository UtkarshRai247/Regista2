"""
Task 19, Step 3: recompute the policy baseline with offside filtering
DROPPED ENTIRELY, per Step 2's calibration verdict (no candidate rule --
R0 through R4, all K/M/attacking-half variants -- reliably detects
offside from these freeze frames at a false-positive rate below 5%; the
best functioning rule, R4 with K=10 and M=3, still has FP=10.74%).
Restriction is now p_success>=0.05 AND distance_u<=45 only. Same
temperature procedure as Task 18 Step 1, refit fresh on this new
restricted population -- reuses load_scored_match/fit_temperature/
policy_metrics/softmax_per_group from policy_baseline_fix.py unchanged.

Run: python src/engine_v2/policy_baseline_fix_v2.py
"""
import json
import warnings
from pathlib import Path

import pandas as pd

from common import match_disjoint_split, CANDIDATE_FEATURES
from policy_baseline_fix import (
    load_scored_match, fit_temperature, policy_metrics, POLICY_MODEL_PATH,
    RESTRICT_MIN_P_SUCCESS, RESTRICT_MAX_DISTANCE_U, RNG_SEED, TEST_SIZE,
)
import xgboost as xgb
import numpy as np

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
EV_DIR = DATA_DIR / "processed" / "engine_v2" / "options_ev"
STEP1_TASK18_SUMMARY_PATH = DATA_DIR / "engine_v2_step1_policy_baseline_fix.json"
SUMMARY_PATH = DATA_DIR / "engine_v2_step3_policy_baseline_fix_v2.json"


def restrict_no_offside(df: pd.DataFrame) -> pd.DataFrame:
    return df[(df["p_success"] >= RESTRICT_MIN_P_SUCCESS) & (df["distance_u"] <= RESTRICT_MAX_DISTANCE_U)]


def main():
    print("Step 3: recompute the policy baseline with offside filtering dropped ...")
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
    print(f"  match-disjoint split: {len(train_ids)} train, {len(test_ids)} test matches (same seed as Task 18 Step 1)")

    print("  scoring train matches ...")
    train_df = pd.concat([load_scored_match(mid, model, fill_values) for mid in sorted(train_ids)], ignore_index=True)
    print("  scoring test matches ...")
    test_df = pd.concat([load_scored_match(mid, model, fill_values) for mid in sorted(test_ids)], ignore_index=True)

    old = json.loads(STEP1_TASK18_SUMMARY_PATH.read_text())
    print("  BEFORE (Task 18's calibrated policy: restricted incl. offside, T=0.1579) -- reusing its recorded numbers")

    print("  restricting candidate set WITHOUT offside (p_success>=0.05, distance_u<=45) ...")
    train_restricted = restrict_no_offside(train_df)
    test_restricted = restrict_no_offside(test_df)
    per_pass_counts = test_restricted.groupby("event_id").size()
    print(f"    restricted candidates/pass (test): mean={per_pass_counts.mean():.1f}, "
          f"median={per_pass_counts.median():.1f}, p90={per_pass_counts.quantile(0.9):.1f}")

    print("  fitting temperature on training matches' restricted candidates ...")
    T_fitted = fit_temperature(train_restricted)
    print(f"    fitted temperature: {T_fitted:.4f} (Task 18's was {old['fitted_temperature']:.4f})")

    print("  AFTER (restricted candidate set without offside, calibrated temperature) ...")
    after = policy_metrics(test_restricted, T=T_fitted, restricted=True)
    print(f"    {after}")

    behavioral = after["median_effective_options"] < 100 and after["corr_policy_weighted_vs_unweighted_mean_ev"] < 0.95
    print(f"\n  PRE-SPECIFIED READING (Task 18's, reapplied): baseline is "
          f"{'BEHAVIORAL' if behavioral else 'STILL NOT BEHAVIORAL'} "
          f"(median effective options {after['median_effective_options']:.1f}, "
          f"corr {after['corr_policy_weighted_vs_unweighted_mean_ev']:.4f})")

    summary = {
        "n_train_matches": len(train_ids), "n_test_matches": len(test_ids),
        "restricted_candidates_per_pass_test": {
            "mean": float(per_pass_counts.mean()), "median": float(per_pass_counts.median()),
            "p90": float(per_pass_counts.quantile(0.9))},
        "fitted_temperature": T_fitted,
        "task18_before": old["before"], "task18_after_with_offside": old["after"],
        "task19_after_no_offside": after,
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
