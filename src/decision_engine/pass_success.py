"""
Task 01 — Step 2: pass success model.

Trains a gradient-boosted classifier predicting whether a pass completes,
using only features that exist for both chosen and unchosen options (the
declared Step 1 feature set: distance, angle, lane_crosses_opponent,
opponents_within_5m, distance_to_nearest_opponent, candidate location).
Trained on CHOSEN (matched, actually-attempted) rows only, since ground
truth completion is only known for the pass actually made — then applied
to every candidate (chosen and unchosen) to estimate p_success for
counterfactual options.

Held out by MATCH, not by row, to avoid leakage (same match's passes are
not independent).

Run: python src/decision_engine/pass_success.py
"""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupShuffleSplit

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
OPTIONS_DIR = DATA_DIR / "processed" / "options_parts"
MODEL_PATH = DATA_DIR / "processed" / "pass_success_model.json"
SCORED_PATH = DATA_DIR / "processed" / "options_scored.parquet"

FEATURES = [
    "distance", "angle", "lane_crosses_opponent",
    "opponents_within_5m", "distance_to_nearest_opponent",
    "candidate_x", "candidate_y",
]


def load_options() -> pd.DataFrame:
    parts = list(OPTIONS_DIR.glob("*.parquet"))
    return pd.concat((pd.read_parquet(p) for p in parts), ignore_index=True)


def prep_X(df: pd.DataFrame) -> pd.DataFrame:
    X = df[FEATURES].copy()
    X["lane_crosses_opponent"] = X["lane_crosses_opponent"].astype(int)
    X["distance_to_nearest_opponent"] = X["distance_to_nearest_opponent"].fillna(
        X["distance_to_nearest_opponent"].max()
    )
    return X


def calibration_table(y_true, y_pred, n_bins=10) -> list[dict]:
    df = pd.DataFrame({"y": y_true, "p": y_pred})
    df["bin"] = pd.qcut(df["p"], n_bins, duplicates="drop")
    return [
        {"bin": str(b), "n": int(len(g)), "mean_predicted": float(g["p"].mean()),
         "mean_actual": float(g["y"].mean())}
        for b, g in df.groupby("bin", observed=True)
    ]


def main():
    opts = load_options()
    chosen = opts[opts["chosen"]].copy()
    print(f"Total options rows: {len(opts):,}, chosen (matched) rows: {len(chosen):,}")

    gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
    train_idx, test_idx = next(gss.split(chosen, groups=chosen["match_id"]))
    train, test = chosen.iloc[train_idx], chosen.iloc[test_idx]
    assert set(train["match_id"]) & set(test["match_id"]) == set(), "match leakage!"

    X_train, y_train = prep_X(train), train["pass_complete"].astype(int)
    X_test, y_test = prep_X(test), test["pass_complete"].astype(int)

    model = xgb.XGBClassifier(
        n_estimators=200, max_depth=4, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.8, random_state=42,
        eval_metric="logloss",
    )
    model.fit(X_train, y_train)
    model.save_model(MODEL_PATH)

    p_test = model.predict_proba(X_test)[:, 1]
    auc = roc_auc_score(y_test, p_test)
    calib = calibration_table(y_test.values, p_test)

    # extrapolation check: unchosen options outside training feature range
    ranges = {f: (X_train[f].min(), X_train[f].max()) for f in FEATURES}
    unchosen = opts[~opts["chosen"]].copy()
    X_unchosen = prep_X(unchosen)
    outside = np.zeros(len(X_unchosen), dtype=bool)
    for f, (lo, hi) in ranges.items():
        outside |= (X_unchosen[f] < lo) | (X_unchosen[f] > hi)
    extrapolation_rate = float(outside.mean())

    # score every candidate (chosen + unchosen) for downstream EV calc
    X_all = prep_X(opts)
    opts["p_success"] = model.predict_proba(X_all)[:, 1]
    opts.to_parquet(SCORED_PATH)

    summary = {
        "n_train_matches": int(train["match_id"].nunique()),
        "n_test_matches": int(test["match_id"].nunique()),
        "n_train_rows": len(train), "n_test_rows": len(test),
        "auc": float(auc),
        "calibration": calib,
        "feature_ranges_train": {f: [float(lo), float(hi)] for f, (lo, hi) in ranges.items()},
        "unchosen_extrapolation_rate": extrapolation_rate,
    }
    print(json.dumps(summary, indent=2))
    (DATA_DIR / "pass_success_summary.json").write_text(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
