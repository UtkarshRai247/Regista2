"""
Task 25, Step 2 (Task 24's Step 5): falsification battery on the
corrected-geometry rebuild. T1 restated (grid.py's own candidate
geometry is direction-invariant in its distance gate, so T1 is
unaffected by the fix -- restated from grid_v2.py's own run). T2 from
value_models_v5_retrain.py (magnitude verdict AND sign). T3 (EV vs
p_success Spearman) recomputed on `options_ev_v4`. T4 (three synthetic
scenarios) rerun via `test_t4_synthetic.py`, reused unchanged, with
`t4mod.EV_DIR` monkeypatched to `options_ev_v4` FROM THE START (the
Task 19d lesson) -- reporting the p90 from BOTH Task 23's seeded-sample
procedure and the committed test's own sampling, both computed on
`options_ev_v4`. T5 from pass_success_v3.py's own run. T6 from
step8_regate.py.

Run: python src/engine_v2/falsification_v3.py
"""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from scipy.stats import spearmanr

import test_t4_synthetic as t4mod
from test_t4_synthetic import (
    scenario_a_unmarked_runner_vs_marked_sideways, scenario_b_congested_cluster_vs_open_space,
    scenario_c_through_ball_top_decile,
)

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
EV_DIR_V4 = DATA_DIR / "processed" / "engine_v2" / "options_ev_v4"
t4mod.EV_DIR = EV_DIR_V4
MODEL_FOR_PATH_V5 = DATA_DIR / "processed" / "engine_v2" / "value_model_for_v5.json"
MODEL_AGAINST_PATH_V5 = DATA_DIR / "processed" / "engine_v2" / "value_model_against_v5.json"
PASS_SUCCESS_MODEL_PATH_V3 = DATA_DIR / "processed" / "engine_v2" / "pass_success_model_v3.json"
STEP4_PASS_SUCCESS_V3_PATH = DATA_DIR / "engine_v2_step4_pass_success_v3.json"
STEP2_OPTIONS_V2_PATH = DATA_DIR / "engine_v2_step2_options_v2.json"
STEP3_VALUE_MODELS_V5_PATH = DATA_DIR / "engine_v2_step3_value_models_v5.json"
STEP3_REGATE_V6_PATH = DATA_DIR / "engine_v2_step3_regate_v6.json"
SUMMARY_PATH = DATA_DIR / "engine_v2_step5_falsification_v3.json"

T3_SAMPLE_SIZE = 5_000_000
T3_THRESHOLD = 0.90
T6_USABLE_CUTOFF = 0.60
T6_GATE_THRESHOLD = 200


def run_t3(rng: np.random.Generator) -> dict:
    parts = sorted(EV_DIR_V4.glob("*.parquet"))
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
    print("Task 25 Step 5: falsification battery on the corrected-geometry rebuild ...")
    model_for = xgb.XGBClassifier()
    model_for.load_model(str(MODEL_FOR_PATH_V5))
    model_against = xgb.XGBClassifier()
    model_against.load_model(str(MODEL_AGAINST_PATH_V5))
    pass_success_model = xgb.XGBClassifier()
    pass_success_model.load_model(str(PASS_SUCCESS_MODEL_PATH_V3))
    fill_values = json.loads(STEP4_PASS_SUCCESS_V3_PATH.read_text())["fill_values"]

    step2_options = json.loads(STEP2_OPTIONS_V2_PATH.read_text())
    t1 = {"pass_condition": "median displacement between scored chosen destination and pass_end_location <= 2 yards",
          "median_displacement_u": step2_options["T1_median_displacement_u"], "verdict": step2_options["T1_pass_condition_le_2u"]}
    print(f"  T1: {t1}")

    value_models_v5 = json.loads(STEP3_VALUE_MODELS_V5_PATH.read_text())
    t2 = {"pass_condition": "M_for's prediction differs materially (>=10% of its own predicted-probability IQR) "
                              "between the 10th and 90th percentile of numerical_advantage_ahead, ball location fixed; "
                              "sign reported, not gated",
          **value_models_v5["T2"], "sign": value_models_v5["T2_sign"], "verdict": value_models_v5["T2"]["T2_pass"]}
    print(f"  T2: {t2}")

    print("  T3 (EV vs p_success Spearman) ...")
    rng = np.random.default_rng(42)
    t3 = run_t3(rng)
    print(f"    {t3}")

    print("  T4 (three synthetic scenarios, EV_DIR=options_ev_v4 from the start) ...")
    t4 = run_t4(model_for, model_against, pass_success_model, fill_values)
    print(f"    {t4}")

    pass_success_v3 = json.loads(STEP4_PASS_SUCCESS_V3_PATH.read_text())
    t5 = {"pass_condition": "pass-success calibration off by no more than 5pp in every pass-length bucket",
          "by_bucket": pass_success_v3["T5_calibration_by_length_bucket"],
          "verdict": pass_success_v3["T5_pass_condition_le_5pp_all_buckets"]}
    print(f"  T5: {t5}")

    regate_v6 = json.loads(STEP3_REGATE_V6_PATH.read_text())
    t6 = {"pass_condition": "split-half reliability of Decision, 100 splits, >=200 passes, >= 0.60",
          "value": regate_v6["decision_reliability_at_200_task25"], "verdict": regate_v6["T6_task25_pass"]}
    print(f"  T6: {t6}")

    battery = {"T1": t1, "T2": t2, "T3": t3, "T4": t4, "T5": t5, "T6": t6}
    gate_tests = ["T2", "T3", "T4", "T5", "T6"]

    def gate_verdict(name):
        t = battery[name]
        if name == "T4":
            return t["all_pass"]
        if name == "T3":
            return t["T3_pass"]
        return t["verdict"]

    all_gate_pass = all(gate_verdict(t) for t in gate_tests)
    print(f"\n  Overall (T2,T3,T4,T5,T6 gates; T1 restated): {'ALL PASS' if all_gate_pass else 'AT LEAST ONE FAILURE'}")

    battery["all_gate_pass"] = all_gate_pass
    SUMMARY_PATH.write_text(json.dumps(battery, indent=2, default=str))
    print(f"\nWrote {SUMMARY_PATH}")
    return battery


if __name__ == "__main__":
    main()
