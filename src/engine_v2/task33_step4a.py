"""
Task 33, Step 4(a)+4(e): the GATE. Out-of-match LINEUP test (Task 32
Step 5 code reused UNCHANGED via import) for Decision_v6 (the GATE),
ev_chosen (v6, report only), f(state) alone (report only), and
Decision_policy_v6 (Step 4(e), report only).

task32_step5.py's leave_one_match_out/build_lineup_units hard-code the
per-pass value column name as "decision" -- reused unchanged by
renaming whichever v6 column is under test to "decision" before calling
them (a zero-cost adapter, not a modification of the imported
functions).

GATE: Decision_v6 PASSES iff LINEUP H-O1 xG coefficient is positive
with p<0.05.

Run: python src/engine_v2/task33_step4a.py
"""
import json
import warnings
from pathlib import Path

import pandas as pd

from task32_step5 import build_lineup_units, standardize_and_join, fit_both
from outcome_validation import build_team_match_units, add_possession_share, add_zone_pressure_shares, add_xg

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
EV_DIR = DATA_DIR / "processed" / "engine_v2" / "options_ev"
DECISION_V6_PATH = DATA_DIR / "processed" / "engine_v2" / "decision_v6.parquet"
SUMMARY_PATH = DATA_DIR / "engine_v2_task33_step4a.json"

VERSIONS = [
    ("decision_v6", "decision_v6", True),
    ("ev_chosen_v6", "ev_chosen", False),
    ("f_state_alone", "f_oof", False),
    ("decision_policy_v6", "decision_policy_v6", False),
]


def main():
    print("Task 33 Step 4(a)+4(e): out-of-match LINEUP GATE test ...")
    decision_v6 = pd.read_parquet(DECISION_V6_PATH)
    non_excluded = decision_v6[~decision_v6["excluded"]]
    print(f"  v6 corpus: {len(decision_v6)} passes, {len(non_excluded)} non-excluded (used for all 4 versions, "
          f"for apples-to-apples comparison)")

    units, _ = build_team_match_units()
    ev_match_ids = sorted(int(p.stem) for p in EV_DIR.glob("*.parquet"))
    units = add_possession_share(units, ev_match_ids)
    units = add_zone_pressure_shares(units, ev_match_ids)
    units = add_xg(units)

    results = {}
    gate_pass = None
    for label, col, is_gate in VERSIONS:
        print(f"\n  [{label}] (column={col}) ...")
        per_pass = non_excluded[["match_id", "team", "player_id", col]].dropna(subset=[col]).rename(columns={col: "decision"})
        lineup_scored, n_total_units = build_lineup_units(per_pass)
        print(f"    units kept: {len(lineup_scored)}/{n_total_units}")
        lineup_units = standardize_and_join(units, lineup_scored)
        res = fit_both(lineup_units, label, {"pho2": True})
        results[label] = {"n_total_units": n_total_units, "n_kept": len(lineup_scored),
                            "n_fit": len(lineup_units), "results": res}
        if is_gate:
            xg_ho1 = res["xg_H-O1"]["coefficients"]["decision_z"]
            gate_pass = bool(xg_ho1["coef"] > 0 and xg_ho1["p_value"] < 0.05)
            print(f"    GATE: xg H-O1 decision_z coef={xg_ho1['coef']:.4f}, p={xg_ho1['p_value']:.4g} "
                  f"-> GATE {'PASS' if gate_pass else 'FAIL'}")

    print(f"\n{'='*60}\nGATE VERDICT: {'PASS' if gate_pass else 'FAIL'}\n{'='*60}")

    summary = {"n_v6_total": len(decision_v6), "n_non_excluded": len(non_excluded),
                "versions": results, "gate_pass": gate_pass}
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
    print(f"\nWrote {SUMMARY_PATH}")
    return summary


if __name__ == "__main__":
    main()
