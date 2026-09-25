"""
Task 15 -- Engine v2, Step 4: pass-success model.

Same model family as v1 (gradient boosting, same hyperparameters as
src/decision_engine/pass_success.py: n_estimators=200, max_depth=4,
learning_rate=0.05, subsample=0.8, colsample_bytree=0.8, random_state=42
-- v1's convention for this smaller, non-freeze-frame-context candidate
feature set), trained on CHOSEN destinations only (label=pass_complete),
held out by MATCH (not by row) to avoid leakage, per v1's own explicit
convention. Produces T5 (calibration by pass-length bucket) and T7
(off-policy / convex-hull support), then scores every candidate (chosen
and unchosen) for Steps 5-6 to consume.

Run: python src/engine_v2/pass_success_v2.py
"""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from scipy.spatial import Delaunay
from sklearn.metrics import roc_auc_score

from common import CANDIDATE_FEATURES, LENGTH_BUCKETS, length_bucket_label, calibration_table, match_disjoint_split, prep_X

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
PARTS_DIR = DATA_DIR / "processed" / "engine_v2" / "options_parts"
SCORED_DIR = DATA_DIR / "processed" / "engine_v2" / "options_scored"
MODEL_PATH = DATA_DIR / "processed" / "engine_v2" / "pass_success_model.json"
SUMMARY_PATH = DATA_DIR / "engine_v2_step4_pass_success.json"

XGB_KWARGS = dict(n_estimators=200, max_depth=4, learning_rate=0.05,
                   subsample=0.8, colsample_bytree=0.8, random_state=42, eval_metric="logloss")
T5_MAX_ABS_DIFF_PP = 5.0


def load_chosen_rows() -> pd.DataFrame:
    parts = sorted(PARTS_DIR.glob("*.parquet"))
    frames = []
    cols = CANDIDATE_FEATURES + ["match_id", "event_id", "pass_complete", "pass_length", "candidate_x", "candidate_y", "chosen"]
    for p in parts:
        df = pd.read_parquet(p, columns=cols)
        frames.append(df[df["chosen"]])
    return pd.concat(frames, ignore_index=True)


def t5_calibration_by_bucket(test: pd.DataFrame, p_test: np.ndarray) -> dict:
    test = test.copy()
    test["p_success"] = p_test
    test["bucket"] = test["pass_length"].apply(length_bucket_label)
    out = {}
    for lo, hi in LENGTH_BUCKETS:
        label = length_bucket_label(lo)
        g = test[test["bucket"] == label]
        if len(g) == 0:
            out[label] = {"n": 0, "mean_predicted": None, "mean_actual": None, "abs_diff_pp": None, "pass": None}
            continue
        mp, ma = float(g["p_success"].mean()), float(g["pass_complete"].mean())
        diff_pp = abs(mp - ma) * 100
        out[label] = {"n": int(len(g)), "mean_predicted": mp, "mean_actual": ma,
                      "abs_diff_pp": diff_pp, "pass": bool(diff_pp <= T5_MAX_ABS_DIFF_PP)}
    return out


def t7_offpolicy_support(train: pd.DataFrame, test: pd.DataFrame) -> dict:
    train = train.copy()
    test = test.copy()
    train["bucket"] = train["pass_length"].apply(length_bucket_label)
    test["bucket"] = test["pass_length"].apply(length_bucket_label)
    out = {}
    for lo, hi in LENGTH_BUCKETS:
        label = length_bucket_label(lo)
        tr = train[train["bucket"] == label][["candidate_x", "candidate_y"]].values
        te = test[test["bucket"] == label][["candidate_x", "candidate_y"]].values
        if len(tr) < 4 or len(te) == 0:
            out[label] = {"n_test": int(len(te)), "share_outside_hull": None}
            continue
        try:
            hull = Delaunay(tr)
            outside = hull.find_simplex(te) < 0
            out[label] = {"n_test": int(len(te)), "share_outside_hull": float(outside.mean())}
        except Exception as e:
            out[label] = {"n_test": int(len(te)), "share_outside_hull": None, "error": str(e)}
    return out


def score_all_candidates(model: xgb.XGBClassifier, fill_values: dict):
    SCORED_DIR.mkdir(parents=True, exist_ok=True)
    parts = sorted(PARTS_DIR.glob("*.parquet"))
    for i, p in enumerate(parts):
        df = pd.read_parquet(p)
        X, _ = prep_X(df, CANDIDATE_FEATURES, fill_values)
        df["p_success"] = model.predict_proba(X)[:, 1].astype("float32")
        df.to_parquet(SCORED_DIR / p.name)
        if (i + 1) % 50 == 0:
            print(f"  scored {i + 1}/{len(parts)} matches")


def main():
    print("Step 4: pass-success model ...")
    chosen = load_chosen_rows()
    print(f"  chosen rows (training population): {len(chosen)}")

    train, test = match_disjoint_split(chosen, "match_id", 0.2, 42)
    X_train, fill_values = prep_X(train, CANDIDATE_FEATURES)
    X_test, _ = prep_X(test, CANDIDATE_FEATURES, fill_values)
    y_train, y_test = train["pass_complete"].astype(int), test["pass_complete"].astype(int)

    model = xgb.XGBClassifier(**XGB_KWARGS)
    model.fit(X_train, y_train)
    p_test = model.predict_proba(X_test)[:, 1]
    auc = float(roc_auc_score(y_test, p_test))
    print(f"  n_train={len(train)}, n_test={len(test)}, held-out AUC={auc:.4f}")

    calib_overall = calibration_table(y_test.values, p_test, n_bins=10)
    t5 = t5_calibration_by_bucket(test, p_test)
    print(f"  T5 calibration by length bucket: {t5}")
    t5_pass = all(v["pass"] for v in t5.values() if v["pass"] is not None)

    t7 = t7_offpolicy_support(train, test)
    print(f"  T7 off-policy support by length bucket: {t7}")

    model.save_model(str(MODEL_PATH))
    print("  scoring all candidates (chosen + unchosen) ...")
    score_all_candidates(model, fill_values)

    summary = {
        "n_chosen_rows": int(len(chosen)), "n_train": int(len(train)), "n_test": int(len(test)),
        "held_out_auc": auc, "calibration_overall": calib_overall,
        "T5_calibration_by_length_bucket": t5, "T5_pass_condition_le_5pp_all_buckets": t5_pass,
        "T7_offpolicy_support_by_length_bucket": t7,
        "fill_values": fill_values,
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
    print(f"\nWrote {SUMMARY_PATH}")
    return summary


if __name__ == "__main__":
    main()
