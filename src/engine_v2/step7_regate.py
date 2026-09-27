"""
Task 21, Step 2 (continued): recompute Execution corpus-wide with the v3
(possession-state) value models, assemble Decision/Risk/Execution,
re-run T6 and the separation check, report Task 19c/19d (old) vs this
task (new) side by side.

Run: python src/engine_v2/step7_regate.py
"""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb

from decision_execution_risk import compute_execution_for_match
from validation_common import spearman_brown

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
EV_DIR_V3 = DATA_DIR / "processed" / "engine_v2" / "options_ev_v3"
MODEL_FOR_PATH_V3 = DATA_DIR / "processed" / "engine_v2" / "value_model_for_v3.json"
MODEL_AGAINST_PATH_V3 = DATA_DIR / "processed" / "engine_v2" / "value_model_against_v3.json"
POLICY_SUMMARY_V7_PATH = DATA_DIR / "processed" / "engine_v2" / "pass_policy_summary_v7.parquet"
PASS_DER_V6_PATH = DATA_DIR / "processed" / "engine_v2" / "pass_der_v6.parquet"  # Task 19d's final table (player_id/comp/season lookup)
OUT_PATH = DATA_DIR / "processed" / "engine_v2" / "pass_der_v7.parquet"
PLAYER_SEASON_REF_PATH = DATA_DIR / "processed" / "player_season_metrics.parquet"
TEMPO_PATH = DATA_DIR / "processed" / "tempo_redesign_metrics.parquet"
STEP3_TASK19D_REGATE_PATH = DATA_DIR / "engine_v2_step3_regate_v4.json"
SUMMARY_PATH = DATA_DIR / "engine_v2_step3_regate_v5.json"

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
    print("Task 21 Step 2: recompute Execution (v3 models) + Decision/Risk (options_ev_v3), re-gate ...")
    model_for = xgb.XGBClassifier()
    model_for.load_model(str(MODEL_FOR_PATH_V3))
    model_against = xgb.XGBClassifier()
    model_against.load_model(str(MODEL_AGAINST_PATH_V3))

    match_ids = sorted(int(p.stem) for p in EV_DIR_V3.glob("*.parquet"))
    exec_rows = []
    n_total, n_out_of_bounds, n_no_loc_or_frame = 0, 0, 0
    for i, mid in enumerate(match_ids):
        chosen = pd.read_parquet(EV_DIR_V3 / f"{mid}.parquet", columns=["match_id", "event_id", "team", "player_id", "chosen", "EV"])
        chosen = chosen[chosen["chosen"]][["match_id", "event_id", "team", "player_id", "EV"]]
        rows, nt, noob, nnf = compute_execution_for_match(mid, chosen, model_for, model_against)
        exec_rows.extend(rows)
        n_total += nt
        n_out_of_bounds += noob
        n_no_loc_or_frame += nnf
        if (i + 1) % 50 == 0:
            print(f"  {i + 1}/{len(match_ids)} matches, valid Execution so far={len(exec_rows)}/{n_total}")

    execution_coverage = len(exec_rows) / n_total if n_total else 0.0
    print(f"  Execution coverage: {len(exec_rows)}/{n_total} = {execution_coverage:.4f} "
          f"(Task 15's original coverage was 0.8927)")
    exec_df = pd.DataFrame(exec_rows)

    new = pd.read_parquet(POLICY_SUMMARY_V7_PATH)
    new = new.dropna(subset=["ev_chosen", "policy_weighted_ev"]).copy()
    new["decision_new"] = new["ev_chosen"] - new["policy_weighted_ev"]
    new["risk_new"] = new["var_chosen"] - new["policy_weighted_var"]
    new = new.merge(exec_df[["match_id", "event_id", "execution"]], on=["match_id", "event_id"], how="left")
    new = new.rename(columns={"execution": "execution_new"})
    print(f"  new Decision/Risk/Execution computed for {len(new)} passes")

    old = pd.read_parquet(PASS_DER_V6_PATH, columns=["match_id", "event_id", "player_id", "competition_id", "season_id"])
    merged = old.merge(new[["match_id", "event_id", "decision_new", "risk_new", "execution_new"]],
                        on=["match_id", "event_id"], how="inner")
    merged.to_parquet(OUT_PATH)

    print("  reliability sweep: decision_new ...")
    rel_decision_new = reliability_sweep(merged, "decision_new", THRESHOLDS)
    for th, r in rel_decision_new.items():
        print(f"    {th}: n_units={r['n_units']}, median={r['median']}")
    print("  reliability sweep: execution_new ...")
    rel_execution_new = reliability_sweep(merged, "execution_new", THRESHOLDS)
    for th, r in rel_execution_new.items():
        print(f"    {th}: n_units={r['n_units']}, median={r['median']}")

    decision_new_at_200 = rel_decision_new[GATE_THRESHOLD]["median"]
    t6_pass = decision_new_at_200 is not None and decision_new_at_200 >= USABLE_CUTOFF
    print(f"\n  T6 (Task 21): Decision reliability @200 = {decision_new_at_200} -> {'PASS' if t6_pass else 'FAIL'}")

    task19d = json.loads(STEP3_TASK19D_REGATE_PATH.read_text())

    print("  separation check (Task 21) ...")
    sep_new, n_qualifying_new = separation_check(merged, "decision_new")
    for col, r in sep_new.items():
        print(f"    {col}: n={r['n']}, r={r['r']}")

    summary = {
        "n_passes_new": len(new),
        "execution_coverage_task21": execution_coverage, "n_execution_out_of_bounds": n_out_of_bounds,
        "n_execution_no_loc_or_frame": n_no_loc_or_frame,
        "reliability_decision_task19d": task19d["reliability_decision_task19d"],
        "reliability_decision_task21": rel_decision_new,
        "reliability_execution_task21": rel_execution_new,
        "decision_reliability_at_200_task17": task19d["decision_reliability_at_200_task17"],
        "decision_reliability_at_200_task18": task19d["decision_reliability_at_200_task18"],
        "decision_reliability_at_200_task19": task19d["decision_reliability_at_200_task19"],
        "decision_reliability_at_200_task19c": task19d["decision_reliability_at_200_task19c"],
        "decision_reliability_at_200_task19d": task19d["decision_reliability_at_200_task19d"],
        "decision_reliability_at_200_task21": decision_new_at_200,
        "T6_task21_pass": t6_pass,
        "n_qualifying_units_task21": n_qualifying_new,
        "separation_check_task17": task19d["separation_check_task17"],
        "separation_check_task18": task19d["separation_check_task18"],
        "separation_check_task19": task19d["separation_check_task19"],
        "separation_check_task19c": task19d["separation_check_task19c"],
        "separation_check_task19d": task19d["separation_check_task19d"],
        "separation_check_task21": sep_new,
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
    print(f"\nWrote {SUMMARY_PATH}")
    return summary


if __name__ == "__main__":
    main()
