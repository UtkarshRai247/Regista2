"""
Task 26, Step 1(c): outcome-validation battery on the holdout
team-matches, specifications UNCHANGED, reusing every builder from
`outcome_validation.py` (`build_team_match_units`, `add_decision`,
`add_possession_share`, `add_zone_pressure_shares`, `add_reference_rates`,
`add_xg`, `build_comp_season_dummies`, `build_team_context_dummies`) and
`validation_common.py` (`fit_ols`, `load_matches_meta`,
`per_pass_reference_flags`) via monkeypatched I/O paths on BOTH modules
(they hold separate copies of `EVENTS_DIR`/`MATCHES_DIR`).
`decision_z` is standardized WITHIN the holdout's own 246 team-match
units (mean/SD computed on the holdout alone, not reusing the study
sample's), per the brief's explicit instruction.

Team-context dummies are NOT built here: the holdout has only 3
competition-seasons and no repeated team-context beyond a handful of
matches per team, so PH-O2 (team-context fixed effects) and the
possession-level PH-O3 (team_context clustering) either would be
singular or degenerate on this population -- reported as NOT COMPUTED
with the reason, per the brief's explicit "report every specification
that can be computed and say which cannot (and why)."

Run: python src/engine_v2/outcome_validation_holdout.py
"""
import json
import warnings
from pathlib import Path

import outcome_validation as ov
import validation_common as vc

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"

ov.EVENTS_DIR = DATA_DIR / "raw_holdout" / "events"
ov.EV_DIR = DATA_DIR / "processed" / "engine_v2" / "options_ev_holdout"
ov.PASS_DER_PATH = DATA_DIR / "processed" / "engine_v2" / "pass_der_holdout.parquet"
vc.EVENTS_DIR = DATA_DIR / "raw_holdout" / "events"
vc.MATCHES_DIR = DATA_DIR / "raw_holdout" / "matches"

SUMMARY_PATH = DATA_DIR / "engine_v2_task26_step1c_outcome_validation_holdout.json"


def main():
    print("Task 26 Step 1(c): outcome validation on holdout team-matches ...")
    units, matches_meta = ov.build_team_match_units()
    ev_match_ids = sorted(int(p.stem) for p in ov.EV_DIR.glob("*.parquet"))
    print(f"  {len(units)} team-match rows from {len(matches_meta)} holdout matches")

    units = ov.add_decision(units)
    n_missing = int(units["mean_decision"].isna().sum())
    print(f"  Decision missing for {n_missing} team-match rows")

    units = ov.add_possession_share(units, ev_match_ids)
    units = ov.add_zone_pressure_shares(units, ev_match_ids)
    print("  reference rates ...")
    units = ov.add_reference_rates(units, ev_match_ids)
    units = ov.add_xg(units)

    has_decision = units["mean_decision"].notna()
    scored = units[has_decision].copy()
    scored["decision_mean"] = scored["mean_decision"].mean()
    scored["decision_sd"] = scored["mean_decision"].std(ddof=1)
    scored["decision_z"] = (scored["mean_decision"] - scored["decision_mean"]) / scored["decision_sd"]
    print(f"  decision_z standardized within the holdout's own {len(scored)} scored team-match units "
          f"(mean={scored['decision_mean'].iloc[0]:.5f}, sd={scored['decision_sd'].iloc[0]:.5f})")

    dummied, cs_cols = ov.build_comp_season_dummies(scored)
    print(f"  comp-season dummies: {len(cs_cols)} levels (3 holdout competition-seasons -> up to 2 dummies)")

    ho1_predictors = ["decision_z", "possession_share", "is_home"] + cs_cols
    ho2_predictors = ho1_predictors + ["completion_rate", "progressive_rate", "xa_per_pass"]
    zone_share_cols = ["final_share", "defensive_share", "pressure_share"]
    pho1_predictors = ["decision_z", "possession_share", "is_home"] + cs_cols + zone_share_cols
    pho4_predictors = ["decision_z", "is_home"] + cs_cols

    team_match_results = {}
    not_computed = {}
    for outcome in ("xg", "goals"):
        for label, predictors in (("H-O1", ho1_predictors), ("H-O2", ho2_predictors),
                                    ("PH-O1", pho1_predictors), ("PH-O4", pho4_predictors)):
            try:
                res = vc.fit_ols(dummied, outcome, predictors, "team")
                team_match_results[f"{outcome}_{label}"] = res
                coef = res["coefficients"]["decision_z"]
                print(f"  {outcome} {label}: n={res['n']}, decision_z coef={coef['coef']:.4f}, p={coef['p_value']:.4g}")
            except Exception as e:
                not_computed[f"{outcome}_{label}"] = f"could not fit: {e}"
                print(f"  {outcome} {label}: NOT COMPUTED -- {e}")

    not_computed["PH-O2"] = ("not computed: requires team-context (team x competition-season) fixed effects; "
                              "the holdout has only 3 competition-seasons and most teams appear in only 1-2 "
                              "matches, so team-context dummies would be at or near the row count (singular design)")
    not_computed["PH-O3"] = ("not computed: the possession-level specification clusters by team-context; "
                              "the same near-singular-design concern as PH-O2 applies, and the holdout's "
                              "possession count at this task's minimum-pass floor is small")
    print(f"  PH-O2: NOT COMPUTED -- {not_computed['PH-O2']}")
    print(f"  PH-O3: NOT COMPUTED -- {not_computed['PH-O3']}")

    xg_ho1 = team_match_results.get("xg_H-O1")
    gate_pass = False
    if xg_ho1 is not None:
        coef = xg_ho1["coefficients"]["decision_z"]
        gate_pass = bool(coef["coef"] > 0 and coef["p_value"] < 0.05)
    print(f"\n  GATE (xg H-O1 decision_z positive, p<0.05): {'PASS' if gate_pass else 'FAIL'}")

    summary = {
        "n_holdout_matches": len(matches_meta), "n_team_match_units": len(units),
        "n_scored_team_match_units": len(scored), "n_missing_decision": n_missing,
        "n_comp_season_levels": len(cs_cols) + 1,
        "team_match_results": team_match_results, "not_computed": not_computed,
        "gate_xg_HO1_positive_p_lt_05": gate_pass,
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
    print(f"\nWrote {SUMMARY_PATH}")
    return summary


if __name__ == "__main__":
    main()
