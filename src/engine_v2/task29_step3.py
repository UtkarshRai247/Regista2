"""
Task 29, Step 3: an independent reliability check that does not use the
shrinkage model at all -- for deep midfielders with >=500 eligible
passes, split each player's own MATCHES (not passes) into two random
halves, take the mean Decision over each half's passes, correlate the
two half-means ACROSS PLAYERS, Spearman-Brown correct to full length.
Repeat over 100 splits; report the median and 5th-95th percentile of
the full-length reliability, and n (qualifying players).

Run: python src/engine_v2/task29_step3.py
"""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
PASS_DER_V8_PATH = DATA_DIR / "processed" / "engine_v2" / "pass_der_v8.parquet"
LEADERBOARD_V5C_PATH = DATA_DIR / "processed" / "leaderboard_v5c.parquet"
SUMMARY_PATH = DATA_DIR / "engine_v2_task29_step3.json"

MIN_PASSES = 500
N_SPLITS = 100
SEED = 20260928


def main():
    print("Task 29 Step 3: match-split reliability, deep midfielders with >=500 passes ...")
    leaderboard = pd.read_parquet(LEADERBOARD_V5C_PATH)
    dm_ids = set(leaderboard.loc[leaderboard["is_deep_midfield"], "player_id"])

    per_pass = pd.read_parquet(PASS_DER_V8_PATH, columns=["match_id", "player_id", "decision_new"])
    per_pass = per_pass[per_pass["player_id"].isin(dm_ids)]

    n_i = per_pass.groupby("player_id").size()
    qualifying = n_i[n_i >= MIN_PASSES].index
    print(f"  {len(qualifying)} deep midfielders with >= {MIN_PASSES} eligible passes")

    per_pass = per_pass[per_pass["player_id"].isin(qualifying)]
    matches_by_player = {pid: g["match_id"].unique() for pid, g in per_pass.groupby("player_id")}
    passes_by_player = {pid: g[["match_id", "decision_new"]].reset_index(drop=True) for pid, g in per_pass.groupby("player_id")}

    rng = np.random.default_rng(SEED)
    sb_values = []
    for split_i in range(N_SPLITS):
        h1_means, h2_means = [], []
        for pid in qualifying:
            matches = matches_by_player[pid]
            perm = rng.permutation(len(matches))
            half = len(matches) // 2
            h1_matches = set(matches[perm[:half]])
            h2_matches = set(matches[perm[half:]])
            df = passes_by_player[pid]
            h1_mean = df[df["match_id"].isin(h1_matches)]["decision_new"].mean()
            h2_mean = df[df["match_id"].isin(h2_matches)]["decision_new"].mean()
            h1_means.append(h1_mean)
            h2_means.append(h2_mean)
        r = np.corrcoef(h1_means, h2_means)[0, 1]
        sb = 2 * r / (1 + r) if not np.isnan(r) else np.nan
        sb_values.append(sb)

    sb_values = np.array(sb_values)
    valid = sb_values[~np.isnan(sb_values)]
    median_rel = float(np.median(valid))
    p5 = float(np.percentile(valid, 5))
    p95 = float(np.percentile(valid, 95))
    print(f"  n_splits_valid={len(valid)}/{N_SPLITS}")
    print(f"  median full-length reliability={median_rel:.4f}, [{p5:.4f}, {p95:.4f}] (5th-95th pct)")

    summary = {
        "min_passes": MIN_PASSES, "n_qualifying": len(qualifying), "n_splits": N_SPLITS,
        "n_splits_valid": int(len(valid)),
        "median_reliability": median_rel, "p5_reliability": p5, "p95_reliability": p95,
        "qualifying_player_ids": [int(p) for p in qualifying],
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
    print(f"\nWrote {SUMMARY_PATH}")
    return summary


if __name__ == "__main__":
    main()
