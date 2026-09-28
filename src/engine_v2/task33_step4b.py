"""
Task 33, Step 4(b): same-match battery (H-O1, H-O2, PH-O1, PH-O2, PH-O4;
xG and goals) for Decision_v6, beside v5. Reuses every general-purpose
builder from outcome_validation.py UNCHANGED (build_team_match_units,
add_possession_share, add_zone_pressure_shares, add_reference_rates,
add_xg, build_comp_season_dummies, build_team_context_dummies, fit_ols)
-- exactly as outcome_validation_crossfit_v5.py does for v5. Only the
Decision SOURCE differs (decision_v6.parquet's `decision_v6` column
instead of pass_der_crossfit_v5.parquet's `decision`), so a thin 4-line
`add_decision_v6` replaces `add_decision_crossfit` (whose column name is
hard-coded to "decision" and can't be monkeypatched around a renamed
column) -- everything else is identical. PH-O3 (possession-level) is
not requested by Step 4(b) and is not run.

Also fits one extra spec: H-O1 with BOTH f(state) and Decision_v6 as
joint standardised predictors.

Run: python src/engine_v2/task33_step4b.py
"""
import json
import warnings
from pathlib import Path

import pandas as pd

from outcome_validation import (
    build_team_match_units, add_possession_share, add_zone_pressure_shares,
    add_xg, build_comp_season_dummies, build_team_context_dummies,
)
from validation_common import fit_ols

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
EV_DIR = DATA_DIR / "processed" / "engine_v2" / "options_ev"
DECISION_V6_PATH = DATA_DIR / "processed" / "engine_v2" / "decision_v6.parquet"
SUMMARY_PATH = DATA_DIR / "engine_v2_task33_step4b.json"


def add_decision_v6(units: pd.DataFrame) -> pd.DataFrame:
    pass_der = pd.read_parquet(DECISION_V6_PATH, columns=["match_id", "team", "decision_v6"])
    dec = pass_der.groupby(["match_id", "team"])["decision_v6"].mean().reset_index().rename(columns={"decision_v6": "mean_decision"})
    return units.merge(dec, on=["match_id", "team"], how="left")


def add_f_state(units: pd.DataFrame) -> pd.DataFrame:
    pass_der = pd.read_parquet(DECISION_V6_PATH, columns=["match_id", "team", "f_oof"])
    dec = pass_der.groupby(["match_id", "team"])["f_oof"].mean().reset_index().rename(columns={"f_oof": "mean_f_oof"})
    return units.merge(dec, on=["match_id", "team"], how="left")


def main():
    print("Task 33 Step 4(b): same-match battery for Decision_v6 ...")
    units, matches_meta = build_team_match_units()
    ev_match_ids = sorted(int(p.stem) for p in EV_DIR.glob("*.parquet"))

    units = add_decision_v6(units)
    units = add_f_state(units)
    n_missing = int(units["mean_decision"].isna().sum())
    print(f"  Decision_v6 missing for {n_missing} team-match rows")

    units = add_possession_share(units, ev_match_ids)
    units = add_zone_pressure_shares(units, ev_match_ids)
    units = add_xg(units)

    units["decision_z"] = (units["mean_decision"] - units["mean_decision"].mean()) / units["mean_decision"].std(ddof=1)
    units["f_oof_z"] = (units["mean_f_oof"] - units["mean_f_oof"].mean()) / units["mean_f_oof"].std(ddof=1)

    has_decision = units["mean_decision"].notna()
    dummied, cs_cols = build_comp_season_dummies(units[has_decision])
    dummied, tc_cols = build_team_context_dummies(dummied)
    keep_cols = ["match_id", "team", "comp_season", "team_context"] + cs_cols + tc_cols
    units = units.merge(dummied[keep_cols], on=["match_id", "team"], how="left")

    ho1_predictors = ["decision_z", "possession_share", "is_home"] + cs_cols
    zone_share_cols = ["final_share", "defensive_share", "pressure_share"]
    pho1_predictors = ["decision_z", "possession_share", "is_home"] + cs_cols + zone_share_cols
    pho2_predictors = ["decision_z", "possession_share", "is_home"] + zone_share_cols + tc_cols
    pho4_predictors = ["decision_z", "is_home"] + cs_cols
    joint_predictors = ["decision_z", "f_oof_z", "possession_share", "is_home"] + cs_cols

    team_match_results = {}
    for outcome in ("xg", "goals"):
        for label, predictors in (("H-O1", ho1_predictors), ("PH-O1", pho1_predictors),
                                    ("PH-O2", pho2_predictors), ("PH-O4", pho4_predictors)):
            res = fit_ols(units, outcome, predictors, "team_context")
            team_match_results[f"{outcome}_{label}"] = res
            print(f"  {outcome} {label}: n={res['n']}, decision_z coef={res['coefficients']['decision_z']['coef']:.4f}, "
                  f"p={res['coefficients']['decision_z']['p_value']:.4g}")
        res_joint = fit_ols(units, outcome, joint_predictors, "team_context")
        team_match_results[f"{outcome}_H-O1_plus_f_state"] = res_joint
        print(f"  {outcome} H-O1+f(state): decision_z coef={res_joint['coefficients']['decision_z']['coef']:.4f} "
              f"(p={res_joint['coefficients']['decision_z']['p_value']:.4g}), "
              f"f_oof_z coef={res_joint['coefficients']['f_oof_z']['coef']:.4f} "
              f"(p={res_joint['coefficients']['f_oof_z']['p_value']:.4g})")

    print("  H-O2 requires completion_rate/progressive_rate/xa_per_pass (add_reference_rates) -- "
          "reused unchanged from outcome_validation.py")
    from outcome_validation import add_reference_rates
    units = add_reference_rates(units, ev_match_ids)
    ho2_predictors = ho1_predictors + ["completion_rate", "progressive_rate", "xa_per_pass"]
    for outcome in ("xg", "goals"):
        res = fit_ols(units, outcome, ho2_predictors, "team_context")
        team_match_results[f"{outcome}_H-O2"] = res
        print(f"  {outcome} H-O2: n={res['n']}, decision_z coef={res['coefficients']['decision_z']['coef']:.4f}, "
              f"p={res['coefficients']['decision_z']['p_value']:.4g}")

    summary = {"n_team_match_units": len(units), "n_missing_decision": n_missing,
                "team_match_results": team_match_results}
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
    print(f"\nWrote {SUMMARY_PATH}")
    return summary


if __name__ == "__main__":
    main()
