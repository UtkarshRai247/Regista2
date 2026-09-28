"""
Task 40, Step 4: spot-check from the BENCHMARK v6 snapshot copies only
(data/benchmark_v6/), never the live originals. Both numbers are
recomputed, not read off a stored value:
- Task 35 study v5-Decision P-test coefficient (+0.000747 per pass):
  task35_ptest.add_s + fe_fit on the snapshot's task35_ptest_inputs.
- Task 38 deep-midfield count above / below the group mean (12 / 14):
  Task 29's method (estimate_sigma2w_rho, DerSimonian-Laird, shrink, 90%
  intervals) on the snapshot's availability_moments, for the DM players
  listed in the snapshot's availability_dm_table.

Run: python src/engine_v2/task40_spotcheck.py
"""
import json
from pathlib import Path

import pandas as pd

from task35_ptest import add_s, fe_fit
from task28_step1_2 import estimate_sigma2w_rho
from task29_step1_2 import dersimonian_laird, shrink

REPO_ROOT = Path(__file__).parent.parent.parent
SNAP = REPO_ROOT / "data" / "benchmark_v6"
SUMMARY_PATH = REPO_ROOT / "data" / "engine_v2_task40_spotcheck.json"
EXPECTED = {"task35_coef_per_pass": 0.000747, "task38_above": 12, "task38_below": 14}


def main():
    inputs = pd.read_parquet(SNAP / "processed" / "engine_v2" / "task35_ptest_inputs.parquet")
    d = add_s(inputs, "decision")
    d["role"] = d["player_id"].map(inputs.drop_duplicates("player_id").set_index("player_id")["role"])
    coef = fe_fit(d, "y_net_xg", "g_xg")["coef_per_sd"]

    mom = pd.read_parquet(SNAP / "processed" / "pff" / "availability_moments.parquet",
                          columns=["pff_player_id", "pff_game_id", "av"])
    dm_ids = set(pd.read_parquet(SNAP / "processed" / "pff" / "availability_dm_table.parquet")["player_id"])
    pp = mom[mom["pff_player_id"].isin(dm_ids)].rename(
        columns={"pff_player_id": "player_id", "pff_game_id": "match_id", "av": "decision_new"})
    s2, rho, _ = estimate_sigma2w_rho(pp)
    g = pp.groupby("player_id")
    st = pd.DataFrame({"m_i": g["decision_new"].mean(), "n_i": g.size(), "G_i": g["match_id"].nunique()}).reset_index()
    st["v_i"] = s2 * (1 + (st["n_i"] / st["G_i"] - 1) * rho) / st["n_i"]
    dl = dersimonian_laird(st["m_i"].values, st["v_i"].values)
    t = shrink(st, dl["mu_w"], dl["tau2"], "m_i", "v_i")
    above, below = int((t["ci_low_90"] > dl["mu_w"]).sum()), int((t["ci_high_90"] < dl["mu_w"]).sum())

    got = {"task35_coef_per_pass": coef, "task38_n_dm": len(dm_ids), "task38_above": above, "task38_below": below}
    match = {"task35": round(coef, 6) == EXPECTED["task35_coef_per_pass"],
             "task38": (above, below) == (EXPECTED["task38_above"], EXPECTED["task38_below"])}
    print(f"Task 35 v5 Decision P-test coefficient (per pass, from snapshot): {coef:+.10f} "
          f"-> rounds to {coef:+.6f}; BENCHMARK-v6: +0.000747 -> {'MATCH' if match['task35'] else 'MISMATCH'}")
    print(f"Task 38 DM ({len(dm_ids)} players) above / below group mean (from snapshot): {above} / {below}; "
          f"BENCHMARK-v6: 12 / 14 -> {'MATCH' if match['task38'] else 'MISMATCH'}")
    SUMMARY_PATH.write_text(json.dumps({"expected": EXPECTED, "recomputed": got, "match": match}, indent=2))


if __name__ == "__main__":
    main()
