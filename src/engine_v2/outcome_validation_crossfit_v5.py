"""
Task 25, Step 2 (Task 24's Step 6, continued): re-runs the full
outcome-validation battery on this task's cross-fitted Decision
(corrected geometry, this task's newly selected offside rule),
reusing every function from `outcome_validation_crossfit.py` unchanged
-- only the Decision source path is swapped (monkeypatched module
attribute), same pattern as every prior crossfit outcome-validation
task.

Run: python src/engine_v2/outcome_validation_crossfit_v5.py
"""
import json
import warnings
from pathlib import Path

import outcome_validation_crossfit as ovc
from outcome_validation import MIN_POSSESSION_PASSES

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
EV_DIR = DATA_DIR / "processed" / "engine_v2" / "options_ev"  # Task 15's original corpus, used only for the auxiliary
                                                                # team-match features (possession/zone/pressure shares),
                                                                # which are independent of the value-model/geometry fix
                                                                # -- same convention as every prior crossfit task.
SUMMARY_PATH = DATA_DIR / "engine_v2_step6_outcome_validation_crossfit_v5.json"

ovc.PASS_DER_CROSSFIT_PATH = DATA_DIR / "processed" / "engine_v2" / "pass_der_crossfit_v5.parquet"


def main():
    print("Task 25 Step 2: outcome validation on this task's cross-fitted Decision (corrected geometry) ...")
    units, matches_meta = ovc.build_team_match_units()
    ev_match_ids = sorted(int(p.stem) for p in EV_DIR.glob("*.parquet"))

    units = ovc.add_decision_crossfit(units)
    n_missing = int(units["mean_decision"].isna().sum())
    print(f"  Decision missing for {n_missing} team-match rows")

    units = ovc.add_possession_share(units, ev_match_ids)
    units = ovc.add_zone_pressure_shares(units, ev_match_ids)
    print("  reference rates ...")
    units = ovc.add_reference_rates(units, ev_match_ids)
    units = ovc.add_xg(units)

    units["decision_mean"] = units["mean_decision"].mean()
    units["decision_sd"] = units["mean_decision"].std(ddof=1)
    units["decision_z"] = (units["mean_decision"] - units["decision_mean"]) / units["decision_sd"]

    has_decision = units["mean_decision"].notna()
    dummied, cs_cols = ovc.build_comp_season_dummies(units[has_decision])
    dummied, tc_cols = ovc.build_team_context_dummies(dummied)
    keep_cols = ["match_id", "team", "comp_season", "team_context"] + cs_cols + tc_cols
    units = units.merge(dummied[keep_cols], on=["match_id", "team"], how="left")

    ho1_predictors = ["decision_z", "possession_share", "is_home"] + cs_cols
    ho2_predictors = ho1_predictors + ["completion_rate", "progressive_rate", "xa_per_pass"]
    zone_share_cols = ["final_share", "defensive_share", "pressure_share"]
    pho1_predictors = ["decision_z", "possession_share", "is_home"] + cs_cols + zone_share_cols
    pho2_predictors = ["decision_z", "possession_share", "is_home"] + zone_share_cols + tc_cols
    pho4_predictors = ["decision_z", "is_home"] + cs_cols

    team_match_results = {}
    for outcome in ("xg", "goals"):
        for label, predictors in (("H-O1", ho1_predictors), ("H-O2", ho2_predictors),
                                    ("PH-O1", pho1_predictors), ("PH-O2", pho2_predictors), ("PH-O4", pho4_predictors)):
            res = ovc.fit_ols(units, outcome, predictors, "team_context")
            team_match_results[f"{outcome}_{label}"] = res
            print(f"  {outcome} {label}: n={res['n']}, decision_z coef={res['coefficients']['decision_z']['coef']:.4f}, "
                  f"p={res['coefficients']['decision_z']['p_value']:.4g}")

    print("  building possessions (PH-O3) on this task's cross-fitted Decision ...")
    poss, n_team_mismatch = ovc.build_possessions_crossfit(ev_match_ids)
    print(f"  possessions (>= {MIN_POSSESSION_PASSES} passes): {len(poss)}")
    pho3 = ovc.fit_pho3(poss)
    print(f"  PH-O3(a) ends_in_shot margfx: {pho3['ends_in_shot_logit']['decision_z_margfx']}")
    print(f"  PH-O3(b) possession_xg coef: {pho3['possession_xg_ols']['decision_z_coef']}")

    summary = {
        "n_team_match_units": len(units), "n_missing_decision": n_missing,
        "team_match_results": team_match_results,
        "n_possessions": len(poss), "n_team_mismatch_passes": n_team_mismatch,
        "possession_level_results": pho3,
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
    print(f"\nWrote {SUMMARY_PATH}")
    return summary


if __name__ == "__main__":
    main()
