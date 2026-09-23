"""
Task 10 — PART B: Outcome validation (Amendment v2-6.3). First test in
this project of whether Decision predicts a real match outcome.

Unit: team-match (299 matches x 2 teams = 598). Predictor: that team's
mean Decision in that match, from the FROZEN (non-cross-fitted) per-pass
table. Outcomes: team xG (primary), team goals (secondary).

Run: python src/decision_engine/task10_partB_outcome.py
"""
import json
import warnings

import numpy as np
import pandas as pd
import statsmodels.api as sm
import xgboost as xgb

from decompose import DATA_DIR, EVENTS_DIR, PV_MODEL_PATH, build_per_pass_table
from task04_situation_context import load_matches_meta
from task08_reliability_audit import per_pass_reference_flags

warnings.filterwarnings("ignore")

POLICY_PATH = DATA_DIR / "processed" / "options_policy.parquet"
PASSES_PATH = DATA_DIR / "processed" / "passes_situation.parquet"
SUMMARY_PATH = DATA_DIR / "task10_partB_outcome.json"


def build_team_match_units() -> pd.DataFrame:
    matches_meta = load_matches_meta()
    print(f"Matches: {len(matches_meta)}")

    rows = []
    for mid, m in matches_meta.items():
        rows.append({"match_id": mid, "team": m["home_team"], "is_home": 1,
                     "goals": m["home_score"], "competition_id": m["competition_id"], "season_id": m["season_id"]})
        rows.append({"match_id": mid, "team": m["away_team"], "is_home": 0,
                     "goals": m["away_score"], "competition_id": m["competition_id"], "season_id": m["season_id"]})
    units = pd.DataFrame(rows)
    print(f"Team-match units: {len(units)} (expected 598)")
    return units, matches_meta


def add_decision(units: pd.DataFrame) -> pd.DataFrame:
    print("Computing frozen per-pass Decision (decompose.build_per_pass_table) ...")
    policy = pd.read_parquet(POLICY_PATH)
    pv_model = xgb.XGBClassifier()
    pv_model.load_model(PV_MODEL_PATH)
    per_pass = build_per_pass_table(policy, pv_model, verbose=True)
    dec = per_pass.groupby(["match_id", "team"])["decision"].mean().reset_index().rename(
        columns={"decision": "mean_decision"})
    out = units.merge(dec, on=["match_id", "team"], how="left")
    print(f"  Decision missing for {out['mean_decision'].isna().sum()} team-match rows.")
    return out


def add_possession_share(units: pd.DataFrame) -> pd.DataFrame:
    passes = pd.read_parquet(PASSES_PATH, columns=["match_id", "team"])
    counts = passes.groupby(["match_id", "team"]).size().reset_index(name="n_eligible_passes")
    out = units.merge(counts, on=["match_id", "team"], how="left")
    out["n_eligible_passes"] = out["n_eligible_passes"].fillna(0)
    total_per_match = out.groupby("match_id")["n_eligible_passes"].transform("sum")
    out["possession_share"] = out["n_eligible_passes"] / total_per_match
    return out


def add_reference_rates(units: pd.DataFrame) -> pd.DataFrame:
    print("Extracting per-pass completion/progressive/xA (reusing task08_reliability_audit's exact formulas) ...")
    passes_team = pd.read_parquet(PASSES_PATH, columns=["match_id", "event_id", "team"])
    match_ids = sorted(int(p.stem) for p in EVENTS_DIR.glob("*.parquet"))
    frames = []
    for i, mid in enumerate(match_ids):
        flags = per_pass_reference_flags(mid)
        frames.append(flags)
        if (i + 1) % 50 == 0:
            print(f"  {i + 1}/{len(match_ids)} matches")
    flags_df = pd.concat(frames, ignore_index=True)
    flags_df = flags_df.merge(passes_team, on=["match_id", "event_id"], how="inner")
    agg = flags_df.groupby(["match_id", "team"]).agg(
        completion_rate=("complete", "mean"), progressive_rate=("progressive", "mean"),
        xa_per_pass=("xa", "mean"), n_reference_passes=("complete", "count"),
    ).reset_index()
    out = units.merge(agg, on=["match_id", "team"], how="left")
    return out


def add_xg(units: pd.DataFrame) -> pd.DataFrame:
    match_ids = sorted(int(p.stem) for p in EVENTS_DIR.glob("*.parquet"))
    rows = []
    n_missing_xg_shots = 0
    n_matches_with_any_shot = 0
    for mid in match_ids:
        ev = pd.read_parquet(EVENTS_DIR / f"{mid}.parquet", columns=["type", "team", "shot_statsbomb_xg"])
        shots = ev[ev["type"] == "Shot"]
        if len(shots):
            n_matches_with_any_shot += 1
        n_missing_xg_shots += int(shots["shot_statsbomb_xg"].isna().sum())
        xg_by_team = shots.groupby("team")["shot_statsbomb_xg"].sum()
        for team, xg in xg_by_team.items():
            rows.append({"match_id": mid, "team": team, "xg": float(xg)})
    xg_df = pd.DataFrame(rows)
    out = units.merge(xg_df, on=["match_id", "team"], how="left")
    out["xg"] = out["xg"].fillna(0.0)
    print(f"Matches with at least one shot: {n_matches_with_any_shot}/{len(match_ids)}; "
          f"shots missing shot_statsbomb_xg: {n_missing_xg_shots}")
    return out


def fit_ols(df: pd.DataFrame, y_col: str, predictors: list, cluster_col: str) -> dict:
    sub = df.dropna(subset=[y_col] + predictors + [cluster_col]).copy()
    X = sm.add_constant(sub[predictors])
    y = sub[y_col]
    model = sm.OLS(y, X.astype(float)).fit(cov_type="cluster", cov_kwds={"groups": sub[cluster_col]})
    result = {
        "n": int(len(sub)), "r_squared": float(model.rsquared),
        "coefficients": {},
    }
    for name in predictors:
        result["coefficients"][name] = {
            "coef": float(model.params[name]), "se": float(model.bse[name]),
            "ci_low": float(model.conf_int().loc[name, 0]), "ci_high": float(model.conf_int().loc[name, 1]),
            "p_value": float(model.pvalues[name]),
        }
    return result


def main():
    units, matches_meta = build_team_match_units()
    units = add_decision(units)
    units = add_possession_share(units)
    units = add_reference_rates(units)
    units = add_xg(units)

    units["team_context"] = (units["team"].astype(str) + "|" + units["competition_id"].astype(str)
                              + "|" + units["season_id"].astype(str))
    units["comp_season"] = units["competition_id"].astype(str) + "_" + units["season_id"].astype(str)
    dummies = pd.get_dummies(units["comp_season"], prefix="cs", drop_first=True).astype(float)
    units = pd.concat([units, dummies], axis=1)
    comp_season_cols = list(dummies.columns)

    decision_mean = units["mean_decision"].mean()
    decision_sd = units["mean_decision"].std(ddof=1)
    units["decision_z"] = (units["mean_decision"] - decision_mean) / decision_sd
    print(f"\nDecision (team-match mean): mean={decision_mean}, sd={decision_sd}")

    ho1_predictors = ["decision_z", "possession_share", "is_home"] + comp_season_cols
    ho2_predictors = ho1_predictors + ["completion_rate", "progressive_rate", "xa_per_pass"]

    results = {}
    for outcome in ("xg", "goals"):
        print(f"\n=== Outcome: {outcome} ===")
        for label, predictors in (("H-O1", ho1_predictors), ("H-O2", ho2_predictors)):
            res = fit_ols(units, outcome, predictors, "team_context")
            print(f"{label}: n={res['n']}, R2={res['r_squared']:.4f}, "
                  f"decision_z coef={res['coefficients']['decision_z']}")
            results[f"{outcome}_{label}"] = res

    summary = {
        "status": "COMPLETE", "n_team_matches": len(units),
        "n_matches_with_shot": int((units.groupby("match_id")["xg"].transform("sum") >= 0).sum() // 2),
        "decision_mean": float(decision_mean), "decision_sd": float(decision_sd),
        "comp_season_reference": units["comp_season"].astype("category").cat.categories[0]
        if len(dummies) else None,
        "results": results,
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
    print(f"\nWrote summary to {SUMMARY_PATH}")


if __name__ == "__main__":
    main()
