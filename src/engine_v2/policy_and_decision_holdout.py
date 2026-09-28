"""
Task 26, Step 1(b): score the holdout policy with the FROZEN engine v5
policy model, offside rule (R1_K10, `offside_v4`), and softmax
temperature (0.1562, from `policy_baseline_fix_v5.py`'s own summary) --
no refitting, no recalibration. Then computes Decision/Risk per pass
(ev_chosen - policy_weighted_ev / var_chosen - policy_weighted_var).
No reliability sweep or separation check here -- the holdout is not
part of the player-level pool, only the outcome-validation gate (Step
1(c), a separate script).

Reuses `policy_score_v8.py`'s `process_match`/`softmax_per_group`
UNCHANGED via monkeypatched I/O directories.

Run: python src/engine_v2/policy_and_decision_holdout.py
"""
import json
import warnings
from pathlib import Path

import pandas as pd
import xgboost as xgb

import policy_score_v8 as ps8
from policy_baseline_fix import POLICY_MODEL_PATH

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
STEP3_POLICY_V5_PATH = DATA_DIR / "engine_v2_step3_policy_baseline_fix_v5.json"

ps8.EVENTS_DIR = DATA_DIR / "raw_holdout" / "events"
ps8.FRAMES_DIR = DATA_DIR / "raw_holdout" / "frames"
ps8.EV_DIR = DATA_DIR / "processed" / "engine_v2" / "options_ev_holdout"
ps8.OUT_PATH = DATA_DIR / "processed" / "engine_v2" / "pass_policy_summary_holdout.parquet"
ps8.SUMMARY_PATH = DATA_DIR / "engine_v2_task26_step1b_policy_holdout.json"

PASS_DER_HOLDOUT_PATH = DATA_DIR / "processed" / "engine_v2" / "pass_der_holdout.parquet"


def main():
    print("Task 26 Step 1(b): scoring holdout policy with frozen model/offside_v4/T=0.1562 ...")
    model = xgb.XGBClassifier()
    model.load_model(str(POLICY_MODEL_PATH))
    step3 = json.loads(STEP3_POLICY_V5_PATH.read_text())
    T = step3["fitted_temperature"]
    fill_values = step3["fill_values"]
    print(f"  using frozen temperature T={T:.4f} (engine v5's own value, no refit)")

    match_ids = sorted(int(p.stem) for p in ps8.EV_DIR.glob("*.parquet"))
    all_rows, n_zero_total = [], 0
    for i, mid in enumerate(match_ids):
        rows, nz = ps8.process_match(mid, model, fill_values, T)
        all_rows.extend(rows)
        n_zero_total += nz
        if (i + 1) % 20 == 0:
            print(f"  {i + 1}/{len(match_ids)} matches, passes so far={len(all_rows)}")

    summary_df = pd.DataFrame(all_rows)
    summary_df.to_parquet(ps8.OUT_PATH)
    print(f"  {len(summary_df)} passes; {n_zero_total} passes had zero surviving restricted candidates")

    decision_df = summary_df.dropna(subset=["ev_chosen", "policy_weighted_ev"]).copy()
    decision_df["decision"] = decision_df["ev_chosen"] - decision_df["policy_weighted_ev"]
    decision_df["risk"] = decision_df["var_chosen"] - decision_df["policy_weighted_var"]
    decision_df[["match_id", "event_id", "team", "decision", "risk"]].to_parquet(PASS_DER_HOLDOUT_PATH)
    print(f"  wrote {len(decision_df)} passes' Decision/Risk to {PASS_DER_HOLDOUT_PATH}")

    report = {
        "temperature_used": T, "n_passes": len(summary_df),
        "n_passes_zero_restricted_candidates": n_zero_total,
        "n_passes_with_decision": len(decision_df),
    }
    ps8.SUMMARY_PATH.write_text(json.dumps(report, indent=2, default=str))
    print(json.dumps(report, indent=2, default=str))
    print(f"\nWrote {ps8.SUMMARY_PATH}")
    return report


if __name__ == "__main__":
    main()
