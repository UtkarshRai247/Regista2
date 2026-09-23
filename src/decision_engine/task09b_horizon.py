"""
Task 09b — Horizon sensitivity retry (Amendments v2-6.2, v2-7.2).

Resumes Task 09 Part 2, which stopped on diagnosed system memory
pressure, not a code fault. The first Task 09b attempt gated on swap
usage and correctly stopped -- but swap-used is the wrong signal: macOS
never reclaims written swap pages, so a high reading records PAST
pressure, not PRESENT headroom, and could block this retry forever even
once the system is healthy again. This version gates on LIVE memory
pressure instead: macOS's own `memory_pressure` free-percentage figure,
plus an "available memory" figure computed from `vm_stat` (free +
inactive + purgeable pages). Checked before starting and every 50
matches during the rebuild, around the same (frozen, unmodified)
row-building function Task 09 already validated.

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

PREFLIGHT_MIN_FREE_PCT = 40.0
PREFLIGHT_MIN_AVAILABLE_GB = 3.0
RUNTIME_MIN_FREE_PCT = 20.0
RUNTIME_MIN_AVAILABLE_GB = 1.5
MEMORY_CHECK_EVERY = 50
HORIZONS = [5, 15]
EV_PATH = DATA_DIR / "processed" / "options_ev.parquet"
TYPED_PATH = DATA_DIR / "processed" / "options_typed.parquet"
PASSES_PATH = DATA_DIR / "processed" / "passes_situation.parquet"
SUMMARY_PATH = DATA_DIR / "task09b_horizon.json"


def get_free_pct() -> float:
    out = subprocess.run(["memory_pressure"], capture_output=True, text=True).stdout
    m = re.search(r"System-wide memory free percentage:\s*(\d+)%", out)
    return float(m.group(1)) if m else float("nan")


def get_available_gb() -> float:
    out = subprocess.run(["vm_stat"], capture_output=True, text=True).stdout
    page_size_m = re.search(r"page size of (\d+) bytes", out)
    free_m = re.search(r"Pages free:\s*(\d+)\.", out)
    inactive_m = re.search(r"Pages inactive:\s*(\d+)\.", out)
    purgeable_m = re.search(r"Pages purgeable:\s*(\d+)\.", out)
    if not all([page_size_m, free_m, inactive_m, purgeable_m]):
        return float("nan")
    page_size = int(page_size_m.group(1))
    pages = int(free_m.group(1)) + int(inactive_m.group(1)) + int(purgeable_m.group(1))
    return pages * page_size / (1024 ** 3)


def check_memory() -> tuple:
    return get_free_pct(), get_available_gb()


def build_horizon_rows_gated(lookahead: int, match_ids: list) -> tuple:
    """Per-match parquet caching (resumable, skips already-cached
    matches) with a live memory-pressure re-check every
    MEMORY_CHECK_EVERY matches actually PROCESSED (not skipped).
    Returns (dataframe_or_None, stopped_bool, n_cached_total)."""
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
        if n_processed_this_run % MEMORY_CHECK_EVERY == 0:
            free_pct, available_gb = check_memory()
            n_cached = len(list(out_dir.glob("*.parquet")))
            print(f"    [horizon={lookahead}] processed {n_processed_this_run} this run, "
                  f"{n_cached}/{len(match_ids)} cached total, free={free_pct:.0f}%, available={available_gb:.2f}GB")
            if free_pct < RUNTIME_MIN_FREE_PCT or available_gb < RUNTIME_MIN_AVAILABLE_GB:
                print(f"    STOPPING horizon={lookahead}: free%={free_pct:.0f} (min {RUNTIME_MIN_FREE_PCT:.0f}) "
                      f"or available={available_gb:.2f}GB (min {RUNTIME_MIN_AVAILABLE_GB:.1f}GB) breached. "
                      f"{n_cached}/{len(match_ids)} matches cached; cache left as-is for a future resume.")
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
    print("Step 1: preflight machine check (live memory pressure, not swap) ...")
    free_pct, available_gb = check_memory()
    print(f"  System-wide memory free percentage: {free_pct:.0f}%")
    print(f"  Available memory (free+inactive+purgeable): {available_gb:.2f} GB")
    if free_pct < PREFLIGHT_MIN_FREE_PCT or available_gb < PREFLIGHT_MIN_AVAILABLE_GB:
        summary = {"status": "BLOCKED", "reason": "preflight memory-pressure check failed",
                   "free_pct": free_pct, "available_gb": available_gb,
                   "preflight_min_free_pct": PREFLIGHT_MIN_FREE_PCT,
                   "preflight_min_available_gb": PREFLIGHT_MIN_AVAILABLE_GB}
        SUMMARY_PATH.write_text(json.dumps(summary, indent=2))
        print(f"STOPPING: free%={free_pct:.0f} (need >= {PREFLIGHT_MIN_FREE_PCT:.0f}) or "
              f"available={available_gb:.2f}GB (need >= {PREFLIGHT_MIN_AVAILABLE_GB:.1f}GB) failed the "
              f"preflight gate. See {SUMMARY_PATH}")
        return

    print("Step 2: resuming/building horizon=5 and horizon=15 row caches, with a live memory-pressure gate ...")
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
            summary = {"status": "PARTIAL", "reason": "runtime memory-pressure check tripped",
                       "stopped_at_horizon": horizon, "n_cached": n_cached,
                       "n_total_matches": len(all_match_ids),
                       "runtime_min_free_pct": RUNTIME_MIN_FREE_PCT,
                       "runtime_min_available_gb": RUNTIME_MIN_AVAILABLE_GB}
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

    summary = {"status": "COMPLETE", "preflight_free_pct": free_pct, "preflight_available_gb": available_gb,
               "results_by_horizon": results_by_horizon, "verdicts": verdicts_df.to_dict("records")}
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
    print(f"\nWrote summary to {SUMMARY_PATH}")


if __name__ == "__main__":
    main()
