"""
Task 17, Step 4: T6, the reliability gate (engine-v2-rebuild.md section
6's T6, deferred from Task 15's falsification battery since it needs
per-player Decision). Ported split-half Spearman-Brown pattern
(task01b_diagnostics.py's repeated_split_reliability shape, generalized
to sweep 7 thresholds exactly as src/tempo/reliability.py already did
for Task 16) -- RNG_SEED=42, N_REPEATS=100, unchanged.

Fixed pass condition (rebuild spec section 6): Decision reliability >=
0.60 at the 200-pass threshold. If it fails, STOP -- Step 5 does not run.

Also runs the separation check: Decision's correlation with completion
rate, progressive passes per 90, xA per 90 (player_season_metrics.parquet,
Task 01's frozen output, reused for its reference columns only) and the
two USABLE tempo metrics move_on_speed/hold_variation
(tempo_redesign_metrics.parquet, Task 16b).

Run: python src/engine_v2/reliability_t6.py
"""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

from validation_common import spearman_brown

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
PASS_DER_PATH = DATA_DIR / "processed" / "engine_v2" / "pass_der.parquet"
PLAYER_SEASON_REF_PATH = DATA_DIR / "processed" / "player_season_metrics.parquet"
TEMPO_PATH = DATA_DIR / "processed" / "tempo_redesign_metrics.parquet"
SUMMARY_PATH = DATA_DIR / "engine_v2_step4_reliability_t6.json"

THRESHOLDS = [100, 150, 200, 250, 300, 400, 500]
GATE_THRESHOLD = 200
N_REPEATS = 100
RNG_SEED = 42
USABLE_CUTOFF = 0.60


def reliability_sweep(per_pass: pd.DataFrame, metric_col: str, thresholds: list) -> dict:
    grouped = {key: g.reset_index(drop=True) for key, g in
               per_pass.dropna(subset=[metric_col]).groupby(["player_id", "competition_id", "season_id"])}
    n_by_unit = {key: len(g) for key, g in grouped.items()}
    results = {}
    for threshold in thresholds:
        units = [key for key, n in n_by_unit.items() if n >= threshold]
        rng = np.random.default_rng(RNG_SEED)
        sb_vals = []
        for _ in range(N_REPEATS):
            h1_vals, h2_vals = [], []
            for key in units:
                g = grouped[key]
                idx = rng.permutation(len(g))
                half = len(g) // 2
                h1_vals.append(g.iloc[idx[:half]][metric_col].mean())
                h2_vals.append(g.iloc[idx[half:2 * half]][metric_col].mean())
            if len(h1_vals) >= 3:
                r = pd.Series(h1_vals).corr(pd.Series(h2_vals))
                sb = spearman_brown(r)
                if sb is not None:
                    sb_vals.append(sb)
        arr = np.array(sb_vals)
        results[threshold] = {"n_units": len(units), "n_repeats_successful": len(sb_vals),
                               "median": float(np.median(arr)) if len(arr) else None,
                               "p5": float(np.percentile(arr, 5)) if len(arr) else None,
                               "p95": float(np.percentile(arr, 95)) if len(arr) else None}
    return results


def separation_check(pass_der: pd.DataFrame) -> dict:
    player_season = pass_der.groupby(["player_id", "competition_id", "season_id"]).agg(
        decision_per_100=("decision", lambda s: s.mean() * 100), n_passes=("decision", "count")).reset_index()
    qualifying = player_season[player_season["n_passes"] >= GATE_THRESHOLD]

    ref = pd.read_parquet(PLAYER_SEASON_REF_PATH, columns=["player_id", "competition_id", "season_id",
                                                             "completion_pct", "progressive_passes_per_90", "xa_per_90"])
    tempo = pd.read_parquet(TEMPO_PATH, columns=["player_id", "competition_id", "season_id",
                                                   "move_on_speed", "hold_variation"])
    joined = qualifying.merge(ref, on=["player_id", "competition_id", "season_id"], how="left")
    joined = joined.merge(tempo, on=["player_id", "competition_id", "season_id"], how="left")

    out = {}
    for col in ("completion_pct", "progressive_passes_per_90", "xa_per_90", "move_on_speed", "hold_variation"):
        sub = joined.dropna(subset=[col, "decision_per_100"])
        out[col] = {"n": int(len(sub)), "r": float(sub["decision_per_100"].corr(sub[col])) if len(sub) >= 3 else None}
    return out


def main():
    print("Step 4: T6 reliability gate ...")
    pass_der = pd.read_parquet(PASS_DER_PATH)
    print("  reliability sweep: decision ...")
    rel_decision = reliability_sweep(pass_der, "decision", THRESHOLDS)
    for th, r in rel_decision.items():
        print(f"    {th}: n_units={r['n_units']}, median={r['median']}")

    has_execution = "execution" in pass_der.columns
    rel_execution = None
    if has_execution:
        print("  reliability sweep: execution ...")
        rel_execution = reliability_sweep(pass_der, "execution", THRESHOLDS)
        for th, r in rel_execution.items():
            print(f"    {th}: n_units={r['n_units']}, median={r['median']}")

    decision_at_200 = rel_decision[GATE_THRESHOLD]["median"]
    t6_pass = decision_at_200 is not None and decision_at_200 >= USABLE_CUTOFF
    print(f"\n  T6: Decision reliability @200 = {decision_at_200} -> {'PASS' if t6_pass else 'FAIL'}")

    print("  separation check ...")
    sep = separation_check(pass_der)
    for col, r in sep.items():
        print(f"    {col}: n={r['n']}, r={r['r']}")

    summary = {
        "reliability_decision": rel_decision, "reliability_execution": rel_execution,
        "decision_reliability_at_200": decision_at_200, "T6_pass_condition": ">= 0.60 at 200-pass threshold",
        "T6_pass": t6_pass, "separation_check": sep,
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
    print(f"\nWrote {SUMMARY_PATH}")
    return summary


if __name__ == "__main__":
    main()
