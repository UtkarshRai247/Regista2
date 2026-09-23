"""
Task 09b — Horizon sensitivity retry (Amendments v2-6.2, v2-7.2).

Resumes Task 09 Part 2, which stopped on diagnosed system memory
pressure, not a code fault. This script adds explicit machine-health
gates around the same (frozen, unmodified) row-building function Task 09
already validated: check swap before starting (stop if > 1.0GB), and
re-check every 50 matches during the rebuild (stop if > 2.0GB), instead
of discovering the problem mid-run again.

Run: python src/decision_engine/task09b_horizon.py
"""
import json
import re
import subprocess
import time
import warnings

import pandas as pd
import xgboost as xgb
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split

from decompose import DATA_DIR, EVENTS_DIR
from possession_value import FEATURES as PV_FEATURES
from task09_horizon import (
    FROZEN_HORIZON, ROBUST_CANDIDATES, build_ev_context_for_matches, build_match_rows_horizon,
    compute_g_p_l_ph2, recompute_ev_at_horizon,
)
from task06_study_a_confirmation import cand_mask, confirmation_match_ids

warnings.filterwarnings("ignore")

PREFLIGHT_SWAP_LIMIT_MB = 1024.0
RUNTIME_SWAP_LIMIT_MB = 2048.0
SWAP_CHECK_EVERY = 50
HORIZONS = [5, 15]
EV_PATH = DATA_DIR / "processed" / "options_ev.parquet"
TYPED_PATH = DATA_DIR / "processed" / "options_typed.parquet"
PASSES_PATH = DATA_DIR / "processed" / "passes_situation.parquet"
SUMMARY_PATH = DATA_DIR / "task09b_horizon.json"


def get_swap_mb() -> float:
    out = subprocess.run(["sysctl", "vm.swapusage"], capture_output=True, text=True).stdout
    m = re.search(r"used\s*=\s*([\d.]+)M", out)
    return float(m.group(1)) if m else float("nan")


def get_free_pages_mb() -> float:
    out = subprocess.run(["vm_stat"], capture_output=True, text=True).stdout
    page_size_m = re.search(r"page size of (\d+) bytes", out)
    free_m = re.search(r"Pages free:\s*(\d+)\.", out)
    if not page_size_m or not free_m:
        return float("nan")
    page_size = int(page_size_m.group(1))
    free_pages = int(free_m.group(1))
    return free_pages * page_size / (1024 * 1024)


def build_horizon_rows_gated(lookahead: int, match_ids: list) -> tuple:
    """Per-match parquet caching (resumable, skips already-cached
    matches) with a live swap re-check every SWAP_CHECK_EVERY matches
    actually PROCESSED (not skipped). Returns (dataframe_or_None,
    stopped_bool, n_cached_total)."""
    out_dir = DATA_DIR / "processed" / f"possession_value_parts_h{lookahead}"
    out_dir.mkdir(parents=True, exist_ok=True)
    n_processed_this_run = 0
    for mid in match_ids:
        out_path = out_dir / f"{mid}.parquet"
        if out_path.exists():
            continue
        rows = build_match_rows_horizon(mid, lookahead)
        if rows:
            pd.DataFrame(rows).to_parquet(out_path)
        n_processed_this_run += 1
        if n_processed_this_run % SWAP_CHECK_EVERY == 0:
            swap_mb = get_swap_mb()
            n_cached = len(list(out_dir.glob("*.parquet")))
            print(f"    [horizon={lookahead}] processed {n_processed_this_run} this run, "
                  f"{n_cached}/{len(match_ids)} cached total, swap={swap_mb:.0f}MB")
            if swap_mb > RUNTIME_SWAP_LIMIT_MB:
                print(f"    STOPPING horizon={lookahead}: swap {swap_mb:.0f}MB > "
                      f"{RUNTIME_SWAP_LIMIT_MB:.0f}MB limit. {n_cached}/{len(match_ids)} matches cached; "
                      "cache left as-is for a future resume.")
                return None, True, n_cached
    n_cached = len(list(out_dir.glob("*.parquet")))
    parts = list(out_dir.glob("*.parquet"))
    df = pd.concat((pd.read_parquet(p) for p in parts), ignore_index=True)
    return df, False, n_cached


def fit_horizon_model(df: pd.DataFrame):
    X, y = df[PV_FEATURES], df["label"]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    model = xgb.XGBClassifier(n_estimators=300, max_depth=5, learning_rate=0.05,
                               subsample=0.8, colsample_bytree=0.8, random_state=42, eval_metric="logloss")
    model.fit(X_train, y_train)
    auc = float(roc_auc_score(y_test, model.predict_proba(X_test)[:, 1]))
    return model, auc


def main():
    print("Step 1: preflight machine check ...")
    swap_mb = get_swap_mb()
    free_mb = get_free_pages_mb()
    print(f"  swap used: {swap_mb:.2f} MB, free physical pages: {free_mb:.2f} MB")
    if swap_mb > PREFLIGHT_SWAP_LIMIT_MB:
        summary = {"status": "BLOCKED", "reason": "preflight swap check failed",
                   "swap_used_mb": swap_mb, "free_pages_mb": free_mb,
                   "preflight_limit_mb": PREFLIGHT_SWAP_LIMIT_MB}
        SUMMARY_PATH.write_text(json.dumps(summary, indent=2))
        print(f"STOPPING: swap used ({swap_mb:.2f}MB) exceeds the {PREFLIGHT_SWAP_LIMIT_MB:.0f}MB preflight "
              "limit. The user needs to close other applications before this retry can run. "
              f"See {SUMMARY_PATH}")
        return

    print("Step 2: resuming/building horizon=5 and horizon=15 row caches, with a live swap gate ...")
    all_match_ids = sorted(int(p.stem) for p in EVENTS_DIR.glob("*.parquet"))
    horizon_dfs = {}
    stopped = False
    for horizon in HORIZONS:
        t0 = time.time()
        df, this_stopped, n_cached = build_horizon_rows_gated(horizon, all_match_ids)
        print(f"  horizon={horizon}: {'STOPPED' if this_stopped else 'complete'}, "
              f"{n_cached}/{len(all_match_ids)} cached, {time.time() - t0:.1f}s")
        if this_stopped:
            stopped = True
            summary = {"status": "PARTIAL", "reason": "runtime swap check tripped",
                       "stopped_at_horizon": horizon, "n_cached": n_cached,
                       "n_total_matches": len(all_match_ids), "swap_limit_mb": RUNTIME_SWAP_LIMIT_MB}
            SUMMARY_PATH.write_text(json.dumps(summary, indent=2))
            print(f"STOPPING before completing horizon={horizon}. See {SUMMARY_PATH}")
            break
        horizon_dfs[horizon] = df

    if stopped:
        return

    print("\nStep 3: fitting models and recomputing G/CI/P/L/PH-2 for the 3 ROBUST candidates ...")
    confirmation_ids = confirmation_match_ids()
    results_by_horizon = {}
    for horizon in HORIZONS:
        print(f"  horizon={horizon}: fitting ...")
        model, auc = fit_horizon_model(horizon_dfs[horizon])
        print(f"  horizon={horizon} held-out AUC: {auc:.4f}")

        scored = pd.read_parquet(DATA_DIR / "processed" / "options_scored.parquet",
                                  filters=[("match_id", "in", confirmation_ids)])
        passes_cells = pd.read_parquet(PASSES_PATH, filters=[("match_id", "in", confirmation_ids)],
                                        columns=["match_id", "event_id", "zone", "under_pressure", "game_state"])
        target_cells = {(c["zone"], c["under_pressure"], c["game_state"]) for c in ROBUST_CANDIDATES}
        relevant_passes = passes_cells[passes_cells.apply(
            lambda r: (r["zone"], r["under_pressure"], r["game_state"]) in target_cells, axis=1)]
        relevant_keys = set(zip(relevant_passes["match_id"], relevant_passes["event_id"]))
        scored_subset = scored[scored.apply(lambda r: (r["match_id"], r["event_id"]) in relevant_keys, axis=1)].copy()
        relevant_matches = sorted(scored_subset["match_id"].unique())

        directions_by_match, ev_context = build_ev_context_for_matches(relevant_matches)
        ev_table = recompute_ev_at_horizon(scored_subset, directions_by_match, ev_context, model)
        stats_df, join_report = compute_g_p_l_ph2(ev_table, confirmation_ids, ROBUST_CANDIDATES)
        print(stats_df.to_string())
        results_by_horizon[horizon] = {"held_out_auc": auc, "join_report": join_report,
                                        "stats": stats_df.to_dict("records")}

    print(f"\n  horizon={FROZEN_HORIZON} (frozen, for comparison) ...")
    frozen_ev_full = pd.read_parquet(EV_PATH, filters=[("match_id", "in", confirmation_ids)])
    stats_frozen, _ = compute_g_p_l_ph2(
        frozen_ev_full[["match_id", "event_id", "team", "period", "candidate_x", "candidate_y", "chosen", "ev"]],
        confirmation_ids, ROBUST_CANDIDATES)
    print(stats_frozen.to_string())
    results_by_horizon[FROZEN_HORIZON] = {"stats": stats_frozen.to_dict("records")}

    print("\nApplying v2-6.2's interpretation rule ...")
    verdicts = []
    for cand in ROBUST_CANDIDATES:
        def ok(h):
            row = pd.DataFrame(results_by_horizon[h]["stats"])
            r = row[cand_mask(row, cand)].iloc[0]
            return (r["G"] is not None) and (r["G"] > 0) and (r["ci_low"] is not None) and (r["ci_low"] > 0)
        ok5, ok15 = ok(5), ok(15)
        if ok5 and ok15:
            verdict = "horizon-robust"
        elif ok5 or ok15:
            verdict = "holds at one horizon only"
        else:
            verdict = "artefact of the 10-action horizon"
        verdicts.append({**cand, "positive_excl_zero_at_5": ok5, "positive_excl_zero_at_15": ok15, "verdict": verdict})
    verdicts_df = pd.DataFrame(verdicts)
    print(verdicts_df.to_string())

    summary = {"status": "COMPLETE", "preflight_swap_mb": swap_mb, "preflight_free_pages_mb": free_mb,
               "results_by_horizon": results_by_horizon, "verdicts": verdicts_df.to_dict("records")}
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
    print(f"\nWrote summary to {SUMMARY_PATH}")


if __name__ == "__main__":
    main()
