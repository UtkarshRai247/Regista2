"""
Task 15 -- Engine v2, shared infra used by more than one model-training
step: calibration reporting (ported from
src/decision_engine/possession_value.py's calibration_table, already
the de facto project standard, reused unchanged by task13_objectives.py
too) and match-disjoint splitting (ported from the identical pattern
duplicated in src/decision_engine/pass_success.py and policy.py).
Pure/file-agnostic; no engine_v2-specific logic lives here.
"""
import warnings

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupShuffleSplit

warnings.filterwarnings("ignore")

DATA_DIR_NAME = "data"

CANDIDATE_FEATURES = [
    "distance_u", "forward_progress_u", "lateral_shift_u", "relative_bearing_deg",
    "opponents_within_3u", "opponents_within_5u", "opponents_within_10u",
    "distance_to_nearest_opponent_u", "teammates_within_5u",
    "n_opponents_in_corridor", "min_perp_distance_to_lane",
    "opponents_between_ball_and_destination", "passer_pressure_3u", "passer_pressure_5u",
    "is_teammate_destination", "n_visible_players",
]

LENGTH_BUCKETS = [(0, 20), (20, 30), (30, 50), (50, np.inf)]


def length_bucket_label(length: float) -> str:
    for lo, hi in LENGTH_BUCKETS:
        if lo <= length < hi:
            return f"{lo}-{hi if np.isfinite(hi) else '50+'}"
    return "unknown"


def calibration_table(y_true, y_pred, n_bins: int = 10) -> list:
    df = pd.DataFrame({"y": y_true, "p": y_pred})
    try:
        df["bin"] = pd.qcut(df["p"], n_bins, duplicates="drop")
    except ValueError:
        df["bin"] = pd.cut(df["p"], n_bins)
    out = []
    for b, g in df.groupby("bin", observed=True):
        out.append({"bin": str(b), "n": int(len(g)), "mean_predicted": float(g["p"].mean()),
                    "mean_actual": float(g["y"].mean())})
    return out


def match_disjoint_split(df: pd.DataFrame, group_col: str = "match_id", test_size: float = 0.2, seed: int = 42):
    splitter = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=seed)
    train_idx, test_idx = next(splitter.split(df, groups=df[group_col]))
    train, test = df.iloc[train_idx].copy(), df.iloc[test_idx].copy()
    assert set(train[group_col]) & set(test[group_col]) == set(), "match leakage across train/test split"
    return train, test


def prep_X(df: pd.DataFrame, features: list, fill_values: dict = None) -> tuple:
    """Impute missing values (distance_to_nearest_opponent_u,
    min_perp_distance_to_lane can be NaN when zero opponents are
    visible) with each feature's TRAIN-set max, anchored explicitly
    (fill_values passed through from the train call) rather than
    recomputed per-frame -- v1's pass_success.py recomputed the fill
    value from whatever frame it was called on, an inconsistency noted
    in research and corrected here."""
    X = df[features].astype(float).copy()
    if fill_values is None:
        fill_values = {c: float(X[c].max()) for c in features}
    for c in features:
        X[c] = X[c].fillna(fill_values[c])
    return X, fill_values
