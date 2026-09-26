"""
Task 19d, Step 3 (continued): recomputes the per-pass policy summary
(Decision, Risk) on the corrected EV corpus (options_ev_v2, built from
the retrained value models). The restriction (p_success>=0.05,
distance_u<=45, NOT offside_v2 under Task 19c's R4 rule) and the policy
model are UNCHANGED and reused as-is: CANDIDATE_FEATURES (what the
policy model scores) contains no value-model feature, so neither the
policy model nor its calibrated temperature (T=0.15716768602338257,
Task 19c's fitted value) are affected by today's fix -- refitting would
reproduce the identical value, since it depends only on policy raw
scores and chosen labels, neither of which changed. Reuses
`softmax_per_group`/`process_match` from policy_score_v5.py via
monkeypatched EV_DIR (input corpus), pointing at options_ev_v2.

Run: python src/engine_v2/policy_score_v6.py
"""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb

import policy_score_v5 as ps5
from policy_baseline_fix import POLICY_MODEL_PATH

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
STEP3_TASK19C_SUMMARY_PATH = DATA_DIR / "engine_v2_step3_policy_baseline_fix_v3.json"
OUT_PATH = DATA_DIR / "processed" / "engine_v2" / "pass_policy_summary_v6.parquet"
SUMMARY_PATH = DATA_DIR / "engine_v2_step3_recompute_v4.json"

ps5.EV_DIR = DATA_DIR / "processed" / "engine_v2" / "options_ev_v2"


def main():
    print("Step 3: recomputing policy summary on the corrected EV corpus (options_ev_v2) ...")
    model = xgb.XGBClassifier()
    model.load_model(str(POLICY_MODEL_PATH))
    task19c = json.loads(STEP3_TASK19C_SUMMARY_PATH.read_text())
    T = task19c["fitted_temperature"]
    fill_values = task19c["fill_values"]
    print(f"  reusing Task 19c's fitted temperature T={T:.4f} (unaffected by this task's fix)")

    match_ids = sorted(int(p.stem) for p in ps5.EV_DIR.glob("*.parquet"))
    all_rows, n_zero_total = [], 0
    for i, mid in enumerate(match_ids):
        rows, nz = ps5.process_match(mid, model, fill_values, T)
        all_rows.extend(rows)
        n_zero_total += nz
        if (i + 1) % 50 == 0:
            print(f"  {i + 1}/{len(match_ids)} matches, passes so far={len(all_rows)}")

    summary_df = pd.DataFrame(all_rows)
    summary_df.to_parquet(OUT_PATH)
    print(f"  {len(summary_df)} passes; {n_zero_total} passes had zero surviving restricted candidates "
          f"(Task 19c had 0)")

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
