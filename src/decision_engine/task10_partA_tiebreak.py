"""
Task 10 — PART A addendum: tie-break disclosure.

The coverage test (task10_partA_interval.py) found methods (ii) parametric
bootstrap and (iii) profile-likelihood tied at 0.93 coverage, both exactly
0.02 from the target 0.95. Amendment v2-6.1 / the task-10 brief specify
"PRIMARY = coverage closest to 0.95 among methods with coverage >= 0.90"
but do not specify a tie-break rule. task10_partA_interval.select_primary()
resolves the tie via Python's min() over an ("i","ii","iii")-ordered dict,
which returns the FIRST method encountered on an exact tie -- an
implementation-order artifact, not a specified or considered decision.
This is disclosed as a question for the research lead in the results page,
not resolved here.

This script computes PH-B1/PH-B3 CIs and the resulting v2-5.4 tier verdict
under the untied alternate, method (iii), reusing the already-fitted real
data and the same PH-B1/PH-B3 unit subsets task10_partA_interval.py used
for method (ii) -- so the research lead has both candidates' full downstream
consequences without re-running the ~2-hour coverage test. PH-B2 is
unaffected by method choice (Task 08's disattenuated correlation, unrelated
to S's interval construction) and is not recomputed here.

Run: python src/decision_engine/task10_partA_tiebreak.py
"""
import json

import pandas as pd

from reml_crossed import profile_likelihood_ci_S
from task04_situation_context import DATA_DIR
from task10_partA_interval import X_COLS, apply_tier_rules

UNITS_PATH = DATA_DIR / "processed" / "study_b_units.parquet"
PARTA_SUMMARY_PATH = DATA_DIR / "task10_partA_interval.json"
OUT_PATH = DATA_DIR / "task10_partA_tiebreak.json"


def main():
    units = pd.read_parquet(UNITS_PATH)
    parta = json.loads(PARTA_SUMMARY_PATH.read_text())
    real_ci_iii = tuple(parta["real_data_all_methods"]["iii"])
    phb2 = parta["phb2"]

    x_cols_phb1 = X_COLS + ["is_Defender", "is_Forward"]
    u_phb1 = units.copy()
    for g in ["Defender", "Forward"]:
        u_phb1[f"is_{g}"] = (u_phb1["position_group"] == g).astype(float)
    phb1 = profile_likelihood_ci_S(u_phb1, x_cols=x_cols_phb1)
    phb1_ci_iii = (phb1["ci_low"], phb1["ci_high"])

    counts = units.groupby("player_id").size()
    multi_players = counts[counts >= 2].index
    u_phb3 = units[units["player_id"].isin(multi_players)].copy()
    phb3 = profile_likelihood_ci_S(u_phb3, x_cols=X_COLS)
    phb3_ci_iii = (phb3["ci_low"], phb3["ci_high"])

    tiers_iii = apply_tier_rules(real_ci_iii, phb1_ci_iii, phb2, phb3_ci_iii)

    print(f"PH-B1 (iii): CI={phb1_ci_iii}")
    print(f"PH-B3 (iii): CI={phb3_ci_iii}")
    print("Tier verdict under (iii) as primary:")
    print(json.dumps(tiers_iii, indent=2))

    out = {
        "note": "Alternate tier verdict if the coverage tie (ii vs iii, both 0.93) had been "
                "broken toward (iii) instead of (ii). See docs/results/10-validation.md Section 6.",
        "real_ci_iii": real_ci_iii, "phb1_ci_iii": phb1_ci_iii, "phb3_ci_iii": phb3_ci_iii,
        "tier_rules_under_iii": tiers_iii,
    }
    OUT_PATH.write_text(json.dumps(out, indent=2, default=str))
    print(f"\nWrote {OUT_PATH}")


if __name__ == "__main__":
    main()
