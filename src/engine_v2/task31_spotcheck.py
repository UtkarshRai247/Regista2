"""
Task 31, Step 4: spot-check the snapshot -- reload T6 reliability at 200
passes and the count of deep midfielders with 90% intervals entirely
above the group mean, FROM THE SNAPSHOT COPIES ONLY (data/benchmark_v5/),
never from the live originals. Both must equal BENCHMARK-v5.md's
recorded values (0.8191; 2).

T6 at 200 passes is not stored as a standalone number in any snapshotted
file -- it must be recomputed from the snapshotted Decision/Risk
per-pass output (pass_der_v8.parquet) using the same reliability_sweep
definition step8_regate.py used (100-split reliability, 100 repeats,
seed 42, Spearman-Brown). The deep-midfield above/below count IS already
a direct field in the snapshotted task29_step1_2 summary JSON's
per-player table (recomputed by counting from the snapshot's own
task29_dm_shrunk.parquet, not by trusting a stored count) -- both are
independently recomputed from the snapshot, not read off a cached
number, per the spirit of a spot-check.

Run: python src/engine_v2/task31_spotcheck.py
"""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

REPO_ROOT = Path(__file__).parent.parent.parent
SNAPSHOT_DIR = REPO_ROOT / "data" / "benchmark_v5"
PASS_DER_SNAPSHOT = SNAPSHOT_DIR / "processed" / "engine_v2" / "pass_der_v8.parquet"
DM_SHRUNK_SNAPSHOT = SNAPSHOT_DIR / "processed" / "engine_v2" / "task29_dm_shrunk.parquet"
SUMMARY_PATH = REPO_ROOT / "data" / "engine_v2_task31_spotcheck.json"

GATE_THRESHOLD = 200
N_REPEATS = 100
RNG_SEED = 42


def spearman_brown(r):
    if r is None or np.isnan(r) or r <= -1:
        return None
    return 2 * r / (1 + r)


def reliability_at_200(per_pass: pd.DataFrame) -> float:
    grouped = {key: g.reset_index(drop=True) for key, g in
               per_pass.dropna(subset=["decision_new"]).groupby(["player_id", "competition_id", "season_id"])}
    units = [key for key, g in grouped.items() if len(g) >= GATE_THRESHOLD]
    rng = np.random.default_rng(RNG_SEED)
    sb_vals = []
    for _ in range(N_REPEATS):
        h1_vals, h2_vals = [], []
        for key in units:
            g = grouped[key]
            idx = rng.permutation(len(g))
            half = len(g) // 2
            h1_vals.append(g.iloc[idx[:half]]["decision_new"].mean())
            h2_vals.append(g.iloc[idx[half:2 * half]]["decision_new"].mean())
        if len(h1_vals) >= 3:
            r = pd.Series(h1_vals).corr(pd.Series(h2_vals))
            sb = spearman_brown(r)
            if sb is not None:
                sb_vals.append(sb)
    return float(np.median(sb_vals)) if sb_vals else None


def main():
    print("Task 31 Step 4: spot-check from snapshot copies only ...")
    missing = []
    for p in (PASS_DER_SNAPSHOT, DM_SHRUNK_SNAPSHOT):
        if not p.exists():
            missing.append(str(p.relative_to(REPO_ROOT)))
    if missing:
        print(f"  CANNOT SPOT-CHECK -- missing from snapshot: {missing}")
        summary = {"status": "MISSING_INPUTS", "missing": missing}
        SUMMARY_PATH.write_text(json.dumps(summary, indent=2))
        return summary

    per_pass = pd.read_parquet(PASS_DER_SNAPSHOT, columns=["player_id", "competition_id", "season_id", "decision_new"])
    t6 = reliability_at_200(per_pass)
    print(f"  T6 reliability at 200 (recomputed from snapshot pass_der_v8.parquet): {t6}")

    dm = pd.read_parquet(DM_SHRUNK_SNAPSHOT)
    if "ci_low_90" in dm.columns and "v_i_within_group" in dm.columns:
        # Recompute mu_w directly as the precision-weighted mean of m_i using
        # v_i_within_group, matching task29_step1_2.py's own dersimonian_laird()
        # definition exactly -- not read off a cached column.
        w = 1.0 / dm["v_i_within_group"]
        mu_w = float((w * dm["m_i"]).sum() / w.sum())
        n_above = int((dm["ci_low_90"] > mu_w).sum())
        n_below = int((dm["ci_high_90"] < mu_w).sum())
    else:
        n_above = n_below = mu_w = None
    print(f"  mu_w (recomputed, precision-weighted mean): {mu_w}")
    print(f"  deep-midfield intervals entirely ABOVE mu_w (recomputed from snapshot): {n_above}")
    print(f"  deep-midfield intervals entirely BELOW mu_w (recomputed from snapshot): {n_below}")

    benchmark_t6 = 0.8191
    benchmark_n_above = 2
    t6_match = t6 is not None and round(t6, 4) == benchmark_t6
    n_above_match = n_above == benchmark_n_above

    print(f"\n  T6 matches BENCHMARK-v5.md (0.8191)? {t6_match} (got {round(t6, 4) if t6 else None})")
    print(f"  n_above matches BENCHMARK-v5.md (2)? {n_above_match} (got {n_above})")

    summary = {
        "status": "COMPLETE", "t6_recomputed": t6, "t6_benchmark": benchmark_t6, "t6_matches": t6_match,
        "mu_w_recomputed": mu_w, "n_above_recomputed": n_above, "n_below_recomputed": n_below,
        "n_above_benchmark": benchmark_n_above, "n_above_matches": n_above_match,
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
    print(f"\nWrote {SUMMARY_PATH}")
    return summary


if __name__ == "__main__":
    main()
