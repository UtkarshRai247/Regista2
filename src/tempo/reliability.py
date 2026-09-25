"""
Task 16 -- Tempo module, Step 3: THE GATE.

Governing document: docs/specs/analysis-plan-tempo.md section 5,
executed via docs/specs/task-16-tempo.md Step 3. Reuses the repeated-
split-half reliability PATTERN already established in
task01b_diagnostics.py's repeated_split_reliability (100 random splits,
Spearman-Brown corrected, median + 5th/95th percentiles), generalized
to sweep 7 thresholds for five tempo metrics instead of one fixed
threshold for two engine-v1 metrics. spearman_brown is redefined here
(a 3-line pure formula) rather than imported, per plan section 0.

Split unit: median_time_on_ball / one_touch_share / pressure_delta are
split at the PASS level (each player's own time_on_ball rows, matching
task01b's own per-observation convention). pace_delta / tempo_variation
are split at the MATCH level (each player's own contributing matches),
consistent with how their point estimates are already bootstrapped
"clustered by match" in Step 2 -- a genuine construction choice where
the brief doesn't specify split granularity for the rhythm metrics,
disclosed here and in the results page.

The single "involvement count" threshold gate (100/150/.../500) is
applied uniformly across all five metrics using each player-season's
own time-on-ball observation count, per plan section 1's "eligible
on-ball involvements" (a single named unit, not five separate ones).

Run: python src/tempo/reliability.py
"""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

from metrics import match_competition_lookup
from possessions import build_possession_sequences
from time_on_ball import OUT_PATH as TIME_ON_BALL_PATH

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
SUMMARY_PATH = DATA_DIR / "tempo_step3_reliability.json"

THRESHOLDS = [100, 150, 200, 250, 300, 400, 500]
GATE_THRESHOLD = 200
N_REPEATS = 100
RNG_SEED = 42
ONE_TOUCH_S = 0.4
USABLE_CUTOFF = 0.70
PROVISIONAL_CUTOFF = 0.50


def spearman_brown(r):
    if r is None or pd.isna(r):
        return None
    if r >= 1:
        return 1.0
    return (2 * r) / (1 + r)


def metric_median_tob(g: pd.DataFrame):
    return float(g["time_on_ball"].median()) if len(g) else None


def metric_one_touch(g: pd.DataFrame):
    return float((g["time_on_ball"] < ONE_TOUCH_S).mean()) if len(g) else None


def metric_pressure_delta(g: pd.DataFrame):
    a = g.loc[g["under_pressure"], "time_on_ball"]
    b = g.loc[~g["under_pressure"], "time_on_ball"]
    if len(a) == 0 or len(b) == 0:
        return None
    return float(a.median() - b.median())


def summarize(vals: list, n_units: int) -> dict:
    if vals:
        arr = np.array(vals)
        return {"n_units": n_units, "n_repeats_successful": len(vals),
                "median": float(np.median(arr)), "p5": float(np.percentile(arr, 5)),
                "p95": float(np.percentile(arr, 95))}
    return {"n_units": n_units, "n_repeats_successful": 0, "median": None, "p5": None, "p95": None}


def reliability_sweep_pass_level(tob: pd.DataFrame, metric_fn, thresholds: list,
                                  n_repeats: int = N_REPEATS, seed: int = RNG_SEED) -> dict:
    grouped = {key: g.reset_index(drop=True) for key, g in tob.groupby(["player_id", "competition_id", "season_id"])}
    n_by_unit = {key: len(g) for key, g in grouped.items()}

    results = {}
    for threshold in thresholds:
        units = [key for key, n in n_by_unit.items() if n >= threshold]
        rng = np.random.default_rng(seed)
        sb_vals = []
        for _ in range(n_repeats):
            h1_vals, h2_vals = [], []
            for key in units:
                g = grouped[key]
                idx = rng.permutation(len(g))
                half = len(g) // 2
                v1 = metric_fn(g.iloc[idx[:half]])
                v2 = metric_fn(g.iloc[idx[half:2 * half]])
                if v1 is not None and v2 is not None:
                    h1_vals.append(v1)
                    h2_vals.append(v2)
            if len(h1_vals) >= 3:
                r = pd.Series(h1_vals).corr(pd.Series(h2_vals))
                sb = spearman_brown(r)
                if sb is not None:
                    sb_vals.append(sb)
        results[threshold] = summarize(sb_vals, len(units))
    return results


def reliability_sweep_match_level(seq: pd.DataFrame, involvement_counts: dict, thresholds: list,
                                   n_repeats: int = N_REPEATS, seed: int = RNG_SEED) -> tuple:
    seq_valid = seq[seq["pace"].notna()]
    by_match_team = {k: list(v[["pace", "passer_ids"]].itertuples(index=False, name=None))
                      for k, v in seq_valid.groupby(["match_id", "team"])}
    player_match_team = {}
    for _, r in seq_valid.iterrows():
        for pid in r["passer_ids"]:
            player_match_team.setdefault((pid, r["competition_id"], r["season_id"]), set()).add((r["match_id"], r["team"]))

    def pace_and_var(pid, match_teams):
        withs, withouts = [], []
        for (mid, team) in match_teams:
            for pace, passers in by_match_team.get((mid, team), []):
                (withs if pid in passers else withouts).append(pace)
        if not withs or not withouts:
            return None, None
        pace_delta = float(np.mean(withs) - np.mean(withouts))
        variation = float(np.std(withs, ddof=1)) if len(withs) > 1 else None
        return pace_delta, variation

    results_pace, results_var = {}, {}
    for threshold in thresholds:
        units = [key for key in player_match_team if involvement_counts.get(key, 0) >= threshold]
        rng = np.random.default_rng(seed)
        sb_pace, sb_var = [], []
        for _ in range(n_repeats):
            h1_pace, h2_pace, h1_var, h2_var = [], [], [], []
            for key in units:
                match_teams = list(player_match_team[key])
                if len(match_teams) < 2:
                    continue
                idx = rng.permutation(len(match_teams))
                half = len(match_teams) // 2
                g1 = [match_teams[k] for k in idx[:half]]
                g2 = [match_teams[k] for k in idx[half:2 * half]]
                p1, v1 = pace_and_var(key[0], g1)
                p2, v2 = pace_and_var(key[0], g2)
                if p1 is not None and p2 is not None:
                    h1_pace.append(p1)
                    h2_pace.append(p2)
                if v1 is not None and v2 is not None:
                    h1_var.append(v1)
                    h2_var.append(v2)
            if len(h1_pace) >= 3:
                sb = spearman_brown(pd.Series(h1_pace).corr(pd.Series(h2_pace)))
                if sb is not None:
                    sb_pace.append(sb)
            if len(h1_var) >= 3:
                sb = spearman_brown(pd.Series(h1_var).corr(pd.Series(h2_var)))
                if sb is not None:
                    sb_var.append(sb)
        results_pace[threshold] = summarize(sb_pace, len(units))
        results_var[threshold] = summarize(sb_var, len(units))
    return results_pace, results_var


def classify(median_at_200) -> str:
    if median_at_200 is None:
        return "NOT MEASURABLE"
    if median_at_200 >= USABLE_CUTOFF:
        return "USABLE"
    if median_at_200 >= PROVISIONAL_CUTOFF:
        return "PROVISIONAL"
    return "NOT MEASURABLE"


def main():
    print("Step 3: THE GATE -- 100-split reliability at 7 thresholds for 5 metrics ...")
    tob = pd.read_parquet(TIME_ON_BALL_PATH)
    comp_lookup = match_competition_lookup()
    tob = tob.copy()
    tob["competition_id"] = tob["match_id"].map(lambda m: comp_lookup.get(m, (None, None))[0])
    tob["season_id"] = tob["match_id"].map(lambda m: comp_lookup.get(m, (None, None))[1])
    involvement_counts = tob.groupby(["player_id", "competition_id", "season_id"]).size().to_dict()

    print("  median_time_on_ball ...")
    rel_median = reliability_sweep_pass_level(tob, metric_median_tob, THRESHOLDS)
    print("  one_touch_share ...")
    rel_one_touch = reliability_sweep_pass_level(tob, metric_one_touch, THRESHOLDS)
    print("  pressure_delta ...")
    rel_pressure = reliability_sweep_pass_level(tob, metric_pressure_delta, THRESHOLDS)

    print("  building possession sequences for pace_delta/tempo_variation reliability ...")
    seq = build_possession_sequences()
    comp_lookup2 = comp_lookup
    seq["competition_id"] = seq["match_id"].map(lambda m: comp_lookup2.get(m, (None, None))[0])
    seq["season_id"] = seq["match_id"].map(lambda m: comp_lookup2.get(m, (None, None))[1])
    print("  pace_delta / tempo_variation ...")
    rel_pace, rel_var = reliability_sweep_match_level(seq, involvement_counts, THRESHOLDS)

    all_results = {
        "median_time_on_ball": rel_median, "one_touch_share": rel_one_touch,
        "pressure_delta": rel_pressure, "pace_delta": rel_pace, "tempo_variation": rel_var,
    }
    verdicts = {}
    for metric, results in all_results.items():
        median_at_200 = results[GATE_THRESHOLD]["median"]
        verdicts[metric] = {"median_reliability_at_200": median_at_200, "verdict": classify(median_at_200)}
        print(f"  {metric}: median reliability @200 = {median_at_200} -> {verdicts[metric]['verdict']}")

    summary = {"thresholds": THRESHOLDS, "results": all_results, "verdicts": verdicts}
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
    print(f"\nWrote {SUMMARY_PATH}")
    return summary


if __name__ == "__main__":
    main()
