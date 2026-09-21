"""
Task 01 — post-hoc diagnostic (NOT part of the spec, NOT a gate).
Requested directly: a reliability-by-pass-threshold curve, and a
player-pooled-across-seasons comparison. Does not change Gate A, Gate B,
the analysis plan, or any metric definition — reuses the exact same
split-half / Spearman-Brown machinery, just re-sliced.

Two distinct groupings, reported separately because they answer
different questions:
  (a) per player-SEASON: unit = (player_id, competition_id, season_id).
      A player appearing in 2 competitions is 2 independent units.
      This matches the study's declared unit of analysis
      (analysis-plan-pillar4.md: "one row per player per
      competition-season").
  (b) per PLAYER, pooled across all their competition-seasons in this
      sample: unit = player_id alone. NOTE: this is what the original
      Gate A script (gate_a_reliability.py) already does — it groups
      the per-pass table by player_id only, with no competition_id/
      season_id in it at all. So (b) is not a new alternative being
      introduced here; it's what Gate A's reported numbers actually are.

Run: python src/decision_engine/gate_a_threshold_diagnostic.py
"""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb

from decompose import build_per_pass_table, match_competition_lookup

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
POLICY_PATH = DATA_DIR / "processed" / "options_policy.parquet"
PV_MODEL_PATH = DATA_DIR / "processed" / "possession_value_model.json"
RNG_SEED = 42
N_BOOTSTRAP = 1000

THRESHOLDS_FULL = [200, 250, 300, 350, 400, 450, 500]
THRESHOLDS_POOLED = [200, 350, 500]


def spearman_brown(r: float) -> float:
    if r >= 1:
        return 1.0
    return (2 * r) / (1 + r)


def split_half_reliability_by_group(df: pd.DataFrame, group_cols: list, metric: str,
                                     min_passes: int, rng: np.random.Generator) -> dict:
    rows = []
    for key, g in df.groupby(group_cols):
        if len(g) < min_passes:
            continue
        idx = rng.permutation(len(g))
        half = len(g) // 2
        h1 = g.iloc[idx[:half]][metric].mean()
        h2 = g.iloc[idx[half:2 * half]][metric].mean()
        rows.append({"key": key, "h1": h1, "h2": h2, "n": len(g)})
    sub = pd.DataFrame(rows)
    if len(sub) < 3:
        return {"n_units": len(sub), "spearman_brown": None}

    r = sub["h1"].corr(sub["h2"])
    sb_r = spearman_brown(r)

    boot = []
    n = len(sub)
    for _ in range(N_BOOTSTRAP):
        sample = sub.sample(n=n, replace=True)
        rr = sample["h1"].corr(sample["h2"])
        if pd.notna(rr):
            boot.append(spearman_brown(rr))
    ci = [float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))] if boot else [None, None]

    return {"n_units": int(n), "raw_r": float(r), "spearman_brown": float(sb_r),
            "bootstrap_ci_95": ci}


def main():
    policy = pd.read_parquet(POLICY_PATH)
    pv_model = xgb.XGBClassifier()
    pv_model.load_model(PV_MODEL_PATH)
    per_pass = build_per_pass_table(policy, pv_model, verbose=False)

    comp_lookup = match_competition_lookup()
    per_pass["competition_id"] = per_pass["match_id"].map(lambda m: comp_lookup.get(m, (None, None))[0])
    per_pass["season_id"] = per_pass["match_id"].map(lambda m: comp_lookup.get(m, (None, None))[1])

    rng = np.random.default_rng(RNG_SEED)

    # --- (4) per player-season, threshold curve ---
    curve = []
    for t in THRESHOLDS_FULL:
        dec = split_half_reliability_by_group(
            per_pass, ["player_id", "competition_id", "season_id"], "decision", t, rng)
        exe = split_half_reliability_by_group(
            per_pass, ["player_id", "competition_id", "season_id"], "execution", t, rng)
        curve.append({
            "min_passes": t,
            "n_units_surviving": dec["n_units"],
            "decision_spearman_brown": dec.get("spearman_brown"),
            "decision_ci_95": dec.get("bootstrap_ci_95"),
            "execution_spearman_brown": exe.get("spearman_brown"),
            "execution_ci_95": exe.get("bootstrap_ci_95"),
        })

    # --- (5) per player, pooled across all competition-seasons ---
    pooled = []
    for t in THRESHOLDS_POOLED:
        dec = split_half_reliability_by_group(per_pass, ["player_id"], "decision", t, rng)
        pooled.append({
            "min_passes": t,
            "n_players_surviving": dec["n_units"],
            "decision_spearman_brown": dec.get("spearman_brown"),
            "decision_ci_95": dec.get("bootstrap_ci_95"),
        })

    result = {"per_player_season_curve": curve, "per_player_pooled": pooled}
    print(json.dumps(result, indent=2))
    (DATA_DIR / "gate_a_threshold_diagnostic.json").write_text(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
