"""
Task 19d, Step 4: re-run the falsification battery affected by this
task's fixes -- T2 (already run inside value_models_v2.py's retrain),
T3 (EV vs p_success Spearman, on the corrected corpus), T4 (the three
committed synthetic scenarios, rerun against the retrained models,
functions reused unchanged from test_t4_synthetic.py). T5 (pass-success
calibration) is unaffected -- the pass-success model and its scoring
were never touched by this task's fixes, so it is reported as identical
to Task 15's published figures, not recomputed. T6 and the separation
check were already run in step6_regate.py.

Run: python src/engine_v2/falsification_v2.py
"""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from scipy.stats import spearmanr

from pass_success_v2 import MODEL_PATH as PASS_SUCCESS_MODEL_PATH
import test_t4_synthetic as t4mod
from test_t4_synthetic import (
    scenario_a_unmarked_runner_vs_marked_sideways, scenario_b_congested_cluster_vs_open_space,
    scenario_c_through_ball_top_decile,
)

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
EV_DIR_V2 = DATA_DIR / "processed" / "engine_v2" / "options_ev_v2"
t4mod.EV_DIR = EV_DIR_V2  # scenario_c's corpus-percentile threshold must use the corrected corpus, not Task 15's original
MODEL_FOR_PATH_V2 = DATA_DIR / "processed" / "engine_v2" / "value_model_for_v2.json"
MODEL_AGAINST_PATH_V2 = DATA_DIR / "processed" / "engine_v2" / "value_model_against_v2.json"
STEP4_TASK15_SUMMARY_PATH = DATA_DIR / "engine_v2_step4_pass_success.json"
SUMMARY_PATH = DATA_DIR / "engine_v2_step4_falsification_v2.json"

T3_SAMPLE_SIZE = 5_000_000
T3_THRESHOLD = 0.90


def run_t3(rng: np.random.Generator) -> dict:
    parts = sorted(EV_DIR_V2.glob("*.parquet"))
    samples = []
    remaining = T3_SAMPLE_SIZE
    for p in parts:
        df = pd.read_parquet(p, columns=["EV", "p_success"])
        n_take = min(len(df), max(1, remaining // max(1, len(parts))))
        if len(df) > 0:
            samples.append(df.sample(n=min(n_take, len(df)), random_state=rng.integers(0, 2**31 - 1)))
    sample = pd.concat(samples, ignore_index=True)
    if len(sample) > T3_SAMPLE_SIZE:
        sample = sample.sample(n=T3_SAMPLE_SIZE, random_state=42)
    rho, pval = spearmanr(sample["EV"], sample["p_success"])
    return {"n_sample": int(len(sample)), "spearman_rho": float(rho), "p_value": float(pval),
            "T3_pass": bool(rho < T3_THRESHOLD)}


def run_t4(model_for, model_against, pass_success_model, fill_values) -> dict:
    results = {}
    try:
        scenario_a_unmarked_runner_vs_marked_sideways(model_for, model_against)
        results["scenario_a"] = "PASS"
    except AssertionError as e:
        results["scenario_a"] = f"FAIL: {e}"
    try:
        scenario_b_congested_cluster_vs_open_space(model_for, model_against, pass_success_model, fill_values)
        results["scenario_b"] = "PASS"
    except AssertionError as e:
        results["scenario_b"] = f"FAIL: {e}"
    try:
        scenario_c_through_ball_top_decile(model_for, model_against, pass_success_model, fill_values)
        results["scenario_c"] = "PASS"
    except AssertionError as e:
        results["scenario_c"] = f"FAIL: {e}"
    results["all_pass"] = all(v == "PASS" for k, v in results.items() if k != "all_pass")
    return results


def main():
    print("Step 4: T3, T4 on the corrected corpus / retrained models ...")
    model_for = xgb.XGBClassifier()
    model_for.load_model(str(MODEL_FOR_PATH_V2))
    model_against = xgb.XGBClassifier()
    model_against.load_model(str(MODEL_AGAINST_PATH_V2))
    pass_success_model = xgb.XGBClassifier()
    pass_success_model.load_model(str(PASS_SUCCESS_MODEL_PATH))
    fill_values = json.loads(STEP4_TASK15_SUMMARY_PATH.read_text())["fill_values"]

    print("  T3 (EV vs p_success Spearman) ...")
    rng = np.random.default_rng(42)
    t3 = run_t3(rng)
    print(f"    {t3}")

    print("  T4 (three synthetic scenarios, retrained models) ...")
    t4 = run_t4(model_for, model_against, pass_success_model, fill_values)
    print(f"    {t4}")

    t5_task15 = STEP4_TASK15_SUMMARY_PATH  # pass-success unaffected; cite Task 15's figures directly
    t5_summary = json.loads(t5_task15.read_text())["T5_calibration_by_length_bucket"]

    summary = {"T3": t3, "T4": t4, "T5_unaffected_task15_figures": t5_summary}
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
    print(f"\nWrote {SUMMARY_PATH}")
    return summary


if __name__ == "__main__":
    main()
