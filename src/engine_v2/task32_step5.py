"""
Task 32, Step 5 (A1): does Decision predict matches it was not measured
in? Using cross-fitted per-pass Decision (pass_der_crossfit_v5.parquet,
292 matches), for every team-match unit:
(i) LINEUP: each pass's passer contributes his own mean Decision from
    his OTHER matches only (leave-this-match-out, pooled across all his
    other matches), requiring >= 50 passes in that complement. Unit
    score = pass-weighted mean over the match's covered passes. Units
    kept only if >= 70% of the team's passes in that match are covered.
(ii) TEAM: the team-context's (team x competition x season) mean
    Decision over its OTHER matches (leave-this-match-out), pass-
    weighted. No minimum-passes floor is stated for this version in the
    brief (unlike LINEUP's explicit >=50); none is imposed here --
    disclosed, not silently added.

Both standardised within their own kept-unit population, fit under
H-O1 (possession share, home, comp-season FE); LINEUP additionally
under PH-O2 (zone/pressure shares, team-context FE). All reused
unchanged from outcome_validation.py / outcome_validation_crossfit_v5.py:
build_team_match_units, add_possession_share, add_zone_pressure_shares,
add_xg, build_comp_season_dummies, build_team_context_dummies, fit_ols.

Run: python src/engine_v2/task32_step5.py
"""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

from validation_common import fit_ols, match_competition_lookup
from outcome_validation import (
    build_team_match_units, add_possession_share, add_zone_pressure_shares,
    add_xg, build_comp_season_dummies, build_team_context_dummies,
)

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
CROSSFIT_PATH = DATA_DIR / "processed" / "engine_v2" / "pass_der_crossfit_v5.parquet"
EV_DIR = DATA_DIR / "processed" / "engine_v2" / "options_ev"
SUMMARY_PATH = DATA_DIR / "engine_v2_task32_step5.json"

MIN_COMPLEMENT_PASSES_LINEUP = 50
LINEUP_COVERAGE_MIN = 0.70


def leave_one_match_out(per_pass: pd.DataFrame, group_col: str, min_complement: int = 0) -> pd.DataFrame:
    """For each (match_id, group_col) pair present in per_pass, the
    group's mean `decision` over every OTHER match, pass-weighted.
    NaN where the complement has fewer than min_complement passes."""
    totals = per_pass.groupby(group_col)["decision"].agg(["sum", "count"])
    by_match = per_pass.groupby(["match_id", group_col])["decision"].agg(["sum", "count"]).reset_index()
    by_match = by_match.merge(totals, on=group_col, suffixes=("_match", "_total"))
    by_match["complement_count"] = by_match["count_total"] - by_match["count_match"]
    complement_sum = by_match["sum_total"] - by_match["sum_match"]
    by_match["complement_mean"] = np.where(
        by_match["complement_count"] >= min_complement, complement_sum / by_match["complement_count"], np.nan)
    return by_match[["match_id", group_col, "complement_mean", "complement_count"]]


def build_lineup_units(crossfit: pd.DataFrame) -> pd.DataFrame:
    lineup_vals = leave_one_match_out(crossfit, "player_id", MIN_COMPLEMENT_PASSES_LINEUP)
    pp = crossfit.merge(lineup_vals, on=["match_id", "player_id"], how="left")
    agg = pp.groupby(["match_id", "team"]).agg(
        n_passes=("decision", "size"), n_covered=("complement_mean", "count"),
        mean_decision=("complement_mean", "mean")).reset_index()
    agg["coverage"] = agg["n_covered"] / agg["n_passes"]
    kept = agg[agg["coverage"] >= LINEUP_COVERAGE_MIN].copy()
    return kept, len(agg)


def build_team_units(crossfit: pd.DataFrame, comp_lookup: dict) -> pd.DataFrame:
    pp = crossfit.copy()
    pp["competition_id"] = pp["match_id"].map(lambda m: comp_lookup.get(m, (None, None))[0])
    pp["season_id"] = pp["match_id"].map(lambda m: comp_lookup.get(m, (None, None))[1])
    pp["context"] = pp["team"].astype(str) + "|" + pp["competition_id"].astype(str) + "|" + pp["season_id"].astype(str)
    team_vals = leave_one_match_out(pp, "context", min_complement=0)
    match_context = pp[["match_id", "team", "context"]].drop_duplicates()
    out = match_context.merge(team_vals, on=["match_id", "context"], how="left")
    out = out.rename(columns={"complement_mean": "mean_decision"})
    return out[["match_id", "team", "mean_decision", "complement_count"]]


def standardize_and_join(units: pd.DataFrame, scored: pd.DataFrame) -> pd.DataFrame:
    scored = scored.dropna(subset=["mean_decision"]).copy()
    scored["decision_z"] = (scored["mean_decision"] - scored["mean_decision"].mean()) / scored["mean_decision"].std(ddof=1)
    return units.merge(scored[["match_id", "team", "decision_z"]], on=["match_id", "team"], how="inner")


def fit_both(units: pd.DataFrame, label: str, extra_predictors: dict) -> dict:
    dummied, cs_cols = build_comp_season_dummies(units)
    dummied, tc_cols = build_team_context_dummies(dummied)
    units = units.merge(dummied[["match_id", "team", "comp_season", "team_context"] + cs_cols + tc_cols],
                          on=["match_id", "team"], how="left")
    results = {}
    ho1_predictors = ["decision_z", "possession_share", "is_home"] + cs_cols
    zone_share_cols = ["final_share", "defensive_share", "pressure_share"]
    pho2_predictors = ["decision_z", "possession_share", "is_home"] + zone_share_cols + tc_cols
    for outcome in ("xg", "goals"):
        res = fit_ols(units, outcome, ho1_predictors, "team_context")
        results[f"{outcome}_H-O1"] = res
        print(f"  [{label}] {outcome} H-O1: n={res['n']}, decision_z coef={res['coefficients']['decision_z']['coef']:.4f}, "
              f"p={res['coefficients']['decision_z']['p_value']:.4g}")
        if extra_predictors.get("pho2"):
            res2 = fit_ols(units, outcome, pho2_predictors, "team_context")
            results[f"{outcome}_PH-O2"] = res2
            print(f"  [{label}] {outcome} PH-O2: n={res2['n']}, decision_z coef={res2['coefficients']['decision_z']['coef']:.4f}, "
                  f"p={res2['coefficients']['decision_z']['p_value']:.4g}")
    return results


def main():
    print("Task 32 Step 5 (A1): out-of-match prediction ...")
    crossfit = pd.read_parquet(CROSSFIT_PATH, columns=["match_id", "team", "player_id", "decision"])
    print(f"  cross-fit corpus: {len(crossfit)} passes, {crossfit['match_id'].nunique()} matches")

    units, matches_meta = build_team_match_units()
    ev_match_ids = sorted(int(p.stem) for p in EV_DIR.glob("*.parquet"))
    units = add_possession_share(units, ev_match_ids)
    units = add_zone_pressure_shares(units, ev_match_ids)
    units = add_xg(units)

    print("  (i) LINEUP version ...")
    lineup_scored, n_total_units = build_lineup_units(crossfit)
    print(f"    units kept (>= {LINEUP_COVERAGE_MIN:.0%} coverage): {len(lineup_scored)}/{n_total_units}")
    lineup_units = standardize_and_join(units, lineup_scored)
    lineup_results = fit_both(lineup_units, "LINEUP", {"pho2": True})

    print("  (ii) TEAM version ...")
    comp_lookup = match_competition_lookup()
    team_scored = build_team_units(crossfit, comp_lookup)
    n_team_total = team_scored["mean_decision"].notna().sum() + team_scored["mean_decision"].isna().sum()
    n_team_kept = team_scored["mean_decision"].notna().sum()
    print(f"    units with a non-empty complement: {n_team_kept}/{n_team_total}")
    team_units = standardize_and_join(units, team_scored)
    team_results = fit_both(team_units, "TEAM", {"pho2": False})

    summary = {
        "n_crossfit_matches": int(crossfit["match_id"].nunique()),
        "lineup": {"n_team_match_units_total": n_total_units, "n_kept": len(lineup_scored),
                    "coverage_min": LINEUP_COVERAGE_MIN, "min_complement_passes": MIN_COMPLEMENT_PASSES_LINEUP,
                    "n_fit": len(lineup_units), "results": lineup_results},
        "team": {"n_team_match_units_total": int(n_team_total), "n_kept": int(n_team_kept),
                  "n_fit": len(team_units), "results": team_results},
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
    print(f"\nWrote {SUMMARY_PATH}")
    return summary


if __name__ == "__main__":
    main()
