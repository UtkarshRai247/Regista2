"""
Task 17, Step 1: T2 direction check (bounded, pre-specified, nothing
more). Task 15's single-location probe found M_for's partial dependence
on numerical_advantage_ahead inverted; this step tests it properly at
five locations, split by play pattern, against an empirical benchmark,
and applies the pre-specified reading fixed in
docs/specs/task-17-engine-v2-validation.md Step 1. No retraining, no
feature changes.

Run: python src/engine_v2/t2_direction_check.py
"""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb

from value_models import STATE_FEATURES, PATTERN_CODE, MODEL_FOR_PATH, OUT_PATH as VALUE_ROWS_PATH

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
SUMMARY_PATH = DATA_DIR / "engine_v2_step1_t2_direction_check.json"

LOCATIONS = [30.0, 50.0, 70.0, 90.0, 110.0]
Y_FIXED = 40.0
PERCENTILES = [10, 25, 50, 75, 90]
X_BANDS = [(0, 20, "0-20"), (20, 40, "20-40"), (40, 60, "40-60"), (60, 80, "60-80"),
           (80, 100, "80-100"), (100, 120, "100-120")]
# bands centered on the 5 test locations, per the task brief
BAND_FOR_LOCATION = {30.0: (20, 40), 50.0: (40, 60), 70.0: (60, 80), 90.0: (80, 100), 110.0: (100, 120)}
N_QUINTILES = 5


def partial_dependence(model, df: pd.DataFrame, ball_x: float, ball_y: float,
                        play_pattern_fixed: int = None) -> dict:
    baseline = df[STATE_FEATURES].median()
    pct_values = df["numerical_advantage_ahead"].quantile([p / 100 for p in PERCENTILES])
    out = {}
    rows = []
    for p in PERCENTILES:
        row = baseline.copy()
        row["ball_x"] = ball_x
        row["ball_y"] = ball_y
        row["numerical_advantage_ahead"] = pct_values.loc[p / 100]
        if play_pattern_fixed is not None:
            row["play_pattern_code"] = play_pattern_fixed
        rows.append(row)
    X = pd.DataFrame(rows)[STATE_FEATURES].astype(float)
    preds = model.predict_proba(X)[:, 1]
    for p, pred, adv in zip(PERCENTILES, preds, pct_values.values):
        out[str(p)] = {"numerical_advantage_ahead": float(adv), "p_for": float(pred)}
    return out


def empirical_benchmark(df: pd.DataFrame) -> dict:
    out = {}
    for lo, hi, label in X_BANDS:
        band = df[(df["ball_x"] >= lo) & (df["ball_x"] < hi)]
        if len(band) < N_QUINTILES * 20:
            out[label] = {"n": int(len(band)), "quintiles": None}
            continue
        band = band.copy()
        band["q"] = pd.qcut(band["numerical_advantage_ahead"], N_QUINTILES, duplicates="drop")
        rows = []
        for q, g in band.groupby("q", observed=True):
            rows.append({"bin": str(q), "n": int(len(g)),
                         "mean_numerical_advantage": float(g["numerical_advantage_ahead"].mean()),
                         "observed_rate": float(g["label_for"].mean())})
        out[label] = {"n": int(len(band)), "quintiles": rows}
    return out


def direction_agreement(pd_results: dict, emp_results: dict) -> list:
    comparisons = []
    for loc in LOCATIONS:
        lo, hi = BAND_FOR_LOCATION[loc]
        band_label = f"{lo}-{hi}"
        pd_at_loc = pd_results[str(loc)]
        model_dir = pd_at_loc["10"]["p_for"] < pd_at_loc["90"]["p_for"]  # True = increasing with advantage
        emp = emp_results.get(band_label, {}).get("quintiles")
        if emp and len(emp) >= 2:
            emp_dir = emp[0]["observed_rate"] < emp[-1]["observed_rate"]
            agrees = model_dir == emp_dir
        else:
            emp_dir, agrees = None, None
        comparisons.append({
            "location_x": loc, "band": band_label,
            "model_p_for_p10": pd_at_loc["10"]["p_for"], "model_p_for_p90": pd_at_loc["90"]["p_for"],
            "model_direction_increasing": model_dir,
            "empirical_direction_increasing": emp_dir, "agrees": agrees,
        })
    return comparisons


def main():
    print("Step 1: T2 direction check ...")
    df = pd.read_parquet(VALUE_ROWS_PATH)
    model_for = xgb.XGBClassifier()
    model_for.load_model(str(MODEL_FOR_PATH))

    print("  (a) partial dependence at 5 locations, baseline play pattern ...")
    pd_a = {str(loc): partial_dependence(model_for, df, loc, Y_FIXED) for loc in LOCATIONS}
    for loc, res in pd_a.items():
        print(f"    x={loc}: p10={res['10']['p_for']:.5f} -> p90={res['90']['p_for']:.5f}")

    print("  (b) partial dependence at 5 locations, Regular Play vs From Counter ...")
    pd_b_regular = {str(loc): partial_dependence(model_for, df, loc, Y_FIXED, PATTERN_CODE["Regular Play"]) for loc in LOCATIONS}
    pd_b_counter = {str(loc): partial_dependence(model_for, df, loc, Y_FIXED, PATTERN_CODE["From Counter"]) for loc in LOCATIONS}

    print("  (c) empirical benchmark ...")
    emp = empirical_benchmark(df)
    for label, res in emp.items():
        if res["quintiles"]:
            print(f"    band {label}: n={res['n']}, rate q1={res['quintiles'][0]['observed_rate']:.5f} "
                  f"-> q5={res['quintiles'][-1]['observed_rate']:.5f}")

    comparisons = direction_agreement(pd_a, emp)
    n_agree = sum(1 for c in comparisons if c["agrees"] is True)
    n_compared = sum(1 for c in comparisons if c["agrees"] is not None)
    print(f"\n  direction agreement: {n_agree}/{n_compared} locations")
    for c in comparisons:
        print(f"    x={c['location_x']}: model {'increasing' if c['model_direction_increasing'] else 'decreasing'}, "
              f"empirical {'increasing' if c['empirical_direction_increasing'] else 'decreasing'} -> "
              f"{'AGREE' if c['agrees'] else 'DISAGREE'}")

    systematic_inversion = n_compared > 0 and n_agree <= n_compared - n_agree and n_agree < n_compared
    verdict = "STOP -- systematic inversion, value model misbehaving" if (n_compared > 0 and n_agree < n_compared / 2) \
        else "PROCEED -- model tracks (or partially tracks) empirical rates; the model is right, the intuition may be wrong where it disagrees"

    summary = {
        "partial_dependence_baseline": pd_a,
        "partial_dependence_regular_play": pd_b_regular,
        "partial_dependence_from_counter": pd_b_counter,
        "empirical_benchmark": emp,
        "direction_comparisons": comparisons,
        "n_agree": n_agree, "n_compared": n_compared,
        "verdict": verdict,
        "stop": n_compared > 0 and n_agree < n_compared / 2,
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
    print(f"\n  VERDICT: {verdict}")
    print(f"\nWrote {SUMMARY_PATH}")
    return summary


if __name__ == "__main__":
    main()
