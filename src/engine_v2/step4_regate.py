"""
Task 19, Step 3 (continued): recompute Decision/Risk with the
offside-free calibrated policy (Execution is unchanged -- it does not
depend on the policy), re-run T6 and the separation check, and report
Task 18 vs Task 19 side by side. Mirrors step2_regate.py exactly.

Run: python src/engine_v2/step4_regate.py
"""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

from validation_common import spearman_brown

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
POLICY_SUMMARY_V4_PATH = DATA_DIR / "processed" / "engine_v2" / "pass_policy_summary_v4.parquet"
PASS_DER_PATH = DATA_DIR / "processed" / "engine_v2" / "pass_der.parquet"
OUT_PATH = DATA_DIR / "processed" / "engine_v2" / "pass_der_v4.parquet"
PLAYER_SEASON_REF_PATH = DATA_DIR / "processed" / "player_season_metrics.parquet"
TEMPO_PATH = DATA_DIR / "processed" / "tempo_redesign_metrics.parquet"
STEP2B_TASK18_PATH = DATA_DIR / "engine_v2_step2b_regate.json"
SUMMARY_PATH = DATA_DIR / "engine_v2_step3_regate.json"

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


def separation_check(pass_der: pd.DataFrame, decision_col: str) -> tuple:
    player_season = pass_der.groupby(["player_id", "competition_id", "season_id"]).agg(
        decision_per_100=(decision_col, lambda s: s.mean() * 100), n_passes=(decision_col, "count")).reset_index()
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
    return out, len(qualifying)


def main():
    print("Step 3: re-gate with the offside-free calibrated policy ...")
    new = pd.read_parquet(POLICY_SUMMARY_V4_PATH)
    new = new.dropna(subset=["ev_chosen", "policy_weighted_ev"]).copy()
    new["decision_new"] = new["ev_chosen"] - new["policy_weighted_ev"]
    new["risk_new"] = new["var_chosen"] - new["policy_weighted_var"]
    print(f"  new Decision/Risk computed for {len(new)} passes (of 250,850)")

    old = pd.read_parquet(PASS_DER_PATH, columns=["match_id", "event_id", "player_id", "competition_id",
                                                    "season_id", "decision", "risk", "execution"])
    merged = old.merge(new[["match_id", "event_id", "decision_new", "risk_new"]], on=["match_id", "event_id"], how="inner")
    merged.to_parquet(OUT_PATH)

    print("  reliability sweep: decision_new ...")
    rel_new = reliability_sweep(merged, "decision_new", THRESHOLDS)
    for th, r in rel_new.items():
        print(f"    {th}: n_units={r['n_units']}, median={r['median']}")

    decision_new_at_200 = rel_new[GATE_THRESHOLD]["median"]
    t6_pass = decision_new_at_200 is not None and decision_new_at_200 >= USABLE_CUTOFF
    print(f"\n  T6 (Task 19): Decision reliability @200 = {decision_new_at_200} -> {'PASS' if t6_pass else 'FAIL'}")

    task18 = json.loads(STEP2B_TASK18_PATH.read_text())

    print("  separation check (Task 19) ...")
    sep_new, n_qualifying_new = separation_check(merged, "decision_new")
    for col, r in sep_new.items():
        print(f"    {col}: n={r['n']}, r={r['r']}")

    summary = {
        "n_passes_new": len(new),
        "reliability_decision_task18": task18["reliability_decision_new"],
        "reliability_decision_task19": rel_new,
        "decision_reliability_at_200_task17": task18["decision_reliability_at_200_old"],
        "decision_reliability_at_200_task18": task18["decision_reliability_at_200_new"],
        "decision_reliability_at_200_task19": decision_new_at_200,
        "T6_task19_pass": t6_pass,
        "n_qualifying_units_task19": n_qualifying_new,
        "separation_check_task17": task18["separation_check_old"],
        "separation_check_task18": task18["separation_check_new"],
        "separation_check_task19": sep_new,
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
    print(f"\nWrote {SUMMARY_PATH}")
    return summary


if __name__ == "__main__":
    main()
