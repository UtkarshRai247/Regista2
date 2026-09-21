"""
Task 01 — GATE A: Reliability. STOP AND REPORT.

Randomly splits each player's eligible passes into two halves, computes
Decision/Execution/Risk on each half, and reports the Spearman-Brown
corrected split-half correlation with a bootstrap CI — overall and split
by >500 vs <500 total eligible passes. Per the spec: report exactly as
it comes out, do not proceed past this gate without an instruction from
the research lead, whatever the number is.

Run: python src/decision_engine/gate_a_reliability.py
"""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb

from decompose import build_per_pass_table

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
POLICY_PATH = DATA_DIR / "processed" / "options_policy.parquet"
PV_MODEL_PATH = DATA_DIR / "processed" / "possession_value_model.json"
RNG_SEED = 42
N_BOOTSTRAP = 1000


def spearman_brown(r: float) -> float:
    if r >= 1:
        return 1.0
    return (2 * r) / (1 + r)


def split_half_reliability(per_pass: pd.DataFrame, metric: str, rng: np.random.Generator) -> dict:
    rows = []
    for pid, g in per_pass.groupby("player_id"):
        idx = rng.permutation(len(g))
        half = len(g) // 2
        if half < 5:  # too few passes to split meaningfully
            continue
        h1 = g.iloc[idx[:half]][metric].mean()
        h2 = g.iloc[idx[half:2 * half]][metric].mean()
        rows.append({"player_id": pid, "h1": h1, "h2": h2, "n": len(g)})
    df = pd.DataFrame(rows)
    if len(df) < 3:
        return {"n_players": len(df), "r": None, "spearman_brown": None}

    r = df["h1"].corr(df["h2"])
    sb_r = spearman_brown(r)

    boot = []
    n = len(df)
    for _ in range(N_BOOTSTRAP):
        sample = df.sample(n=n, replace=True, random_state=None)
        rr = sample["h1"].corr(sample["h2"])
        if pd.notna(rr):
            boot.append(spearman_brown(rr))
    ci_lo, ci_hi = (float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))) if boot else (None, None)

    return {
        "n_players": int(n), "raw_r": float(r), "spearman_brown": float(sb_r),
        "bootstrap_ci_95": [ci_lo, ci_hi],
    }


def main():
    policy = pd.read_parquet(POLICY_PATH)
    pv_model = xgb.XGBClassifier()
    pv_model.load_model(PV_MODEL_PATH)

    per_pass = build_per_pass_table(policy, pv_model)
    n_by_player = per_pass.groupby("player_id").size()

    rng = np.random.default_rng(RNG_SEED)
    results = {}
    for metric in ["decision", "execution", "risk"]:
        overall = split_half_reliability(per_pass, metric, rng)
        high = split_half_reliability(
            per_pass[per_pass["player_id"].isin(n_by_player[n_by_player > 500].index)], metric, rng)
        low = split_half_reliability(
            per_pass[per_pass["player_id"].isin(n_by_player[n_by_player <= 500].index)], metric, rng)
        results[metric] = {"overall": overall, "above_500_passes": high, "at_or_below_500_passes": low}

    print(json.dumps(results, indent=2))
    (DATA_DIR / "gate_a_reliability.json").write_text(json.dumps(results, indent=2))
    print("\n*** GATE A: reported above. STOP — do not proceed without research-lead instruction. ***")


if __name__ == "__main__":
    main()
