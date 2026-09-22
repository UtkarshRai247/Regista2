"""
Task 08 — PART 3: Reliability audit (plan 6a, descriptive).

Per-pass progressive/xA flags aren't materialized anywhere as a file,
but the logic to compute them already exists in decompose.
compute_reference_metrics (per pass, before it aggregates to match-level
sums) -- so the brief's STOP condition ("if flags do not exist") does not
apply; this script extracts the per-pass values instead of the
aggregate, reusing the exact same formula and PROGRESSIVE_THRESHOLD_M
constant rather than inventing a new one.

All 5 metrics (completion, progressive, xA, Decision, Execution) are
computed on the SAME population -- eligible passes (the 171,618-pass
population) -- for internal consistency: Decision/Execution only exist
on that population, and the unit definition's pass-count thresholds
(100-500) are naturally "eligible passes" throughout this project.

Run: python src/decision_engine/task08_reliability_audit.py
"""
import json
import warnings

import numpy as np
import pandas as pd
import xgboost as xgb

from decompose import DATA_DIR, EVENTS_DIR, PROGRESSIVE_THRESHOLD_M, PV_MODEL_PATH, \
    build_per_pass_table, match_competition_lookup
from pitch_direction import normalize_xy, team_period_directions

warnings.filterwarnings("ignore")

POLICY_PATH = DATA_DIR / "processed" / "options_policy.parquet"
PASSES_PATH = DATA_DIR / "processed" / "passes_situation.parquet"
SUMMARY_PATH = DATA_DIR / "task08_reliability_audit.json"

SEED = 20260920
N_SPLITS = 100
THRESHOLDS = [100, 150, 200, 250, 300, 400, 500]
METRICS = ["complete", "progressive", "xa", "decision", "execution"]
RELIABILITY_TARGET = 0.70


def per_pass_reference_flags(match_id: int) -> pd.DataFrame:
    """Per-pass completion/progressive/xA -- mirrors decompose.
    compute_reference_metrics's per-pass logic exactly (same formula,
    same PROGRESSIVE_THRESHOLD_M), returning per-pass rows instead of
    match-aggregated sums."""
    ev = pd.read_parquet(EVENTS_DIR / f"{match_id}.parquet")
    ev = ev.sort_values("index").reset_index(drop=True)
    directions, _, _ = team_period_directions(ev)
    passes = ev[ev["type"] == "Pass"].copy()
    xa_by_shot = ev[ev["type"] == "Shot"].set_index("id")["shot_statsbomb_xg"]

    records = []
    for _, r in passes.iterrows():
        if pd.isna(r["player_id"]):
            continue
        loc, end_loc = r["location"], r["pass_end_location"]
        progressive = False
        if (loc is not None and end_loc is not None
                and not (isinstance(loc, float) and pd.isna(loc))
                and not (isinstance(end_loc, float) and pd.isna(end_loc))
                and pd.isna(r.get("pass_outcome"))):
            direction = directions.get((r["team"], r["period"]), 1)
            sx, _ = normalize_xy(loc[0], loc[1], direction)
            ex, _ = normalize_xy(end_loc[0], end_loc[1], direction)
            progressive = (120.0 - sx) - (120.0 - ex) >= PROGRESSIVE_THRESHOLD_M

        xa = 0.0
        if r.get("pass_shot_assist") and pd.notna(r.get("pass_assisted_shot_id")):
            raw_xa = xa_by_shot.get(r["pass_assisted_shot_id"], 0.0)
            xa = float(raw_xa) if pd.notna(raw_xa) else 0.0

        records.append({
            "match_id": match_id, "event_id": r["id"], "player_id": r["player_id"],
            "complete": bool(pd.isna(r.get("pass_outcome"))),
            "progressive": bool(progressive), "xa": xa,
        })
    return pd.DataFrame(records)


def build_master_table() -> pd.DataFrame:
    print("Building per-pass Decision/Execution (decompose.build_per_pass_table) ...")
    policy = pd.read_parquet(POLICY_PATH)
    pv_model = xgb.XGBClassifier()
    pv_model.load_model(PV_MODEL_PATH)
    per_pass_de = build_per_pass_table(policy, pv_model, verbose=True)

    print("Extracting per-pass completion/progressive/xA flags (all 299 matches) ...")
    passes = pd.read_parquet(PASSES_PATH, columns=["match_id", "event_id"])
    eligible_keys = set(zip(passes["match_id"], passes["event_id"]))
    match_ids = sorted(int(p.stem) for p in EVENTS_DIR.glob("*.parquet"))
    frames = []
    for i, mid in enumerate(match_ids):
        flags = per_pass_reference_flags(mid)
        flags = flags[flags.apply(lambda r: (r["match_id"], r["event_id"]) in eligible_keys, axis=1)]
        frames.append(flags)
        if (i + 1) % 50 == 0:
            print(f"  {i + 1}/{len(match_ids)} matches processed")
    flags_df = pd.concat(frames, ignore_index=True)
    print(f"Eligible passes with reference flags: {len(flags_df)} (expected 171,618)")

    comp_lookup = match_competition_lookup()
    flags_df["competition_id"] = flags_df["match_id"].map(lambda m: comp_lookup.get(m, (None, None))[0])
    flags_df["season_id"] = flags_df["match_id"].map(lambda m: comp_lookup.get(m, (None, None))[1])

    master = flags_df.merge(per_pass_de[["match_id", "event_id", "decision", "execution"]],
                             on=["match_id", "event_id"], how="inner")
    print(f"Master per-pass table: {len(master)} rows")
    return master


def run_audit(master: pd.DataFrame) -> dict:
    all_groups = {}
    for key, g in master.groupby(["player_id", "competition_id", "season_id"]):
        all_groups[key] = {m: g[m].values.astype(float) for m in METRICS}

    results = {}
    for threshold in THRESHOLDS:
        qualifying_keys = [k for k, v in all_groups.items() if len(v[METRICS[0]]) >= threshold]
        n_units = len(qualifying_keys)
        print(f"Threshold {threshold}: {n_units} qualifying units")
        if n_units < 2:
            results[threshold] = {"n_units": n_units, **{m: {"median": None, "p5": None, "p95": None} for m in METRICS}}
            continue

        rng = np.random.default_rng(SEED + threshold)
        r_sb = {m: [] for m in METRICS}
        for _ in range(N_SPLITS):
            h1 = {m: [] for m in METRICS}
            h2 = {m: [] for m in METRICS}
            for key in qualifying_keys:
                vals = all_groups[key]
                n = len(vals[METRICS[0]])
                perm = rng.permutation(n)
                half = n // 2
                idx1, idx2 = perm[:half], perm[half:]
                for m in METRICS:
                    arr = vals[m]
                    h1[m].append(arr[idx1].mean())
                    h2[m].append(arr[idx2].mean())
            for m in METRICS:
                r = np.corrcoef(h1[m], h2[m])[0, 1]
                r_sb[m].append(2 * r / (1 + r) if not np.isnan(r) else np.nan)

        threshold_result = {"n_units": n_units}
        for m in METRICS:
            arr = np.array(r_sb[m])
            threshold_result[m] = {"median": float(np.nanmedian(arr)), "p5": float(np.nanpercentile(arr, 5)),
                                    "p95": float(np.nanpercentile(arr, 95))}
        results[threshold] = threshold_result
        print(json.dumps(threshold_result, indent=2))

    return results


def main():
    master = build_master_table()
    results = run_audit(master)

    lowest_threshold_070 = {}
    for m in METRICS:
        found = None
        for t in THRESHOLDS:
            med = results[t][m]["median"]
            if med is not None and med >= RELIABILITY_TARGET:
                found = t
                break
        lowest_threshold_070[m] = found if found is not None else "not reached"
    print(json.dumps(lowest_threshold_070, indent=2, default=str))

    summary = {"status": "COMPLETE", "thresholds": THRESHOLDS, "n_splits": N_SPLITS,
               "results_by_threshold": {str(t): v for t, v in results.items()},
               "lowest_threshold_reaching_0.70": lowest_threshold_070}
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
    print(f"\nWrote summary to {SUMMARY_PATH}")


if __name__ == "__main__":
    main()
