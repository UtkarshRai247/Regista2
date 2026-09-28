"""
Task 33, Step 4(c): reliability for Decision_v6. T6 (step8_regate's own
reliability_sweep, UNCHANGED) at 200 passes on the FULL non-excluded v6
corpus (all roles, unrestricted -- exactly how T6=0.8191 was computed
for v5: no qualifying-player restriction, only step8_regate's own
per-unit threshold). Then Task 32 Step 4's within-role reliability and
role-share-of-variance, reusing its `assign_roles`/`ROLE_POSITIONS`
UNCHANGED (role depends only on position share, not on which Decision
column is used) restricted to the 537 qualifying players, matching Task
32 Step 4's own convention exactly.

Run: python src/engine_v2/task33_step4c.py
"""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

from validation_common import match_competition_lookup
from step8_regate import reliability_sweep
from task32_step4 import assign_roles, ROLE_POSITIONS

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
DECISION_V6_PATH = DATA_DIR / "processed" / "engine_v2" / "decision_v6.parquet"
LEADERBOARD_V5C_PATH = DATA_DIR / "processed" / "leaderboard_v5c.parquet"
SUMMARY_PATH = DATA_DIR / "engine_v2_task33_step4c.json"

THRESHOLDS_WITHIN_ROLE = [100, 200, 300, 500]
GATE_THRESHOLD = 200


def main():
    print("Task 33 Step 4(c): reliability for Decision_v6 ...")
    decision_v6 = pd.read_parquet(DECISION_V6_PATH, columns=["match_id", "event_id", "player_id", "decision_v6", "excluded"])
    non_excluded = decision_v6[~decision_v6["excluded"]].copy()
    comp_lookup = match_competition_lookup()
    non_excluded["competition_id"] = non_excluded["match_id"].map(lambda m: comp_lookup.get(m, (None, None))[0])
    non_excluded["season_id"] = non_excluded["match_id"].map(lambda m: comp_lookup.get(m, (None, None))[1])
    print(f"  {len(non_excluded)} non-excluded passes")

    print(f"\n  T6 (all roles, unrestricted, threshold={GATE_THRESHOLD}) ...")
    t6_all = reliability_sweep(non_excluded, "decision_v6", [GATE_THRESHOLD])
    t6 = t6_all[GATE_THRESHOLD]
    print(f"    n_units={t6['n_units']}, median={t6['median']} (v5 BENCHMARK: 0.8191)")

    print("\n  role assignment (Task 32 Step 4's assign_roles, unchanged) ...")
    leaderboard = pd.read_parquet(LEADERBOARD_V5C_PATH, columns=["player_id"])
    qualifying_ids = set(leaderboard["player_id"])
    roles = assign_roles(qualifying_ids)
    role_counts = roles["role"].value_counts().to_dict()
    print(f"  role counts: {role_counts}")
    role_by_player = roles.set_index("player_id")["role"].to_dict()

    pp_qual = non_excluded[non_excluded["player_id"].isin(qualifying_ids)].copy()
    pp_qual["role"] = pp_qual["player_id"].map(role_by_player)
    print(f"  qualifying-player non-excluded passes: {len(pp_qual)}")

    within_role_reliability = {}
    for role in list(ROLE_POSITIONS) + ["MIXED"]:
        sub = pp_qual[pp_qual["role"] == role]
        n_players_role = sub["player_id"].nunique()
        if n_players_role < 3:
            within_role_reliability[role] = {"n_players": n_players_role, "note": "too few players to sweep"}
            continue
        sweep = reliability_sweep(sub, "decision_v6", THRESHOLDS_WITHIN_ROLE)
        within_role_reliability[role] = {"n_players": n_players_role, "sweep": sweep}
        print(f"    {role} (n_players={n_players_role}): "
              f"{ {t: sweep[t]['median'] for t in THRESHOLDS_WITHIN_ROLE} }")

    print("\n  weighted one-way ANOVA of player-level mean Decision_v6 on role ...")
    player_stats = pp_qual.groupby(["player_id", "role"]).agg(
        n_i=("decision_v6", "size"), m_i=("decision_v6", "mean")).reset_index()
    grand_mean = np.average(player_stats["m_i"], weights=player_stats["n_i"])
    ss_total = float(np.sum(player_stats["n_i"] * (player_stats["m_i"] - grand_mean) ** 2))
    ss_between = 0.0
    for role, g in player_stats.groupby("role"):
        role_mean = np.average(g["m_i"], weights=g["n_i"])
        ss_between += float(np.sum(g["n_i"]) * (role_mean - grand_mean) ** 2)
    variance_share_role = ss_between / ss_total
    print(f"    weighted eta^2 (share of variance explained by role): {variance_share_role:.4f} "
          f"(v5 comparison, Task 32 Step 4: 0.6387)")

    summary = {
        "t6_all_roles_at_200": t6, "t6_v5_benchmark": 0.8191,
        "n_qualifying": len(qualifying_ids), "role_counts": role_counts,
        "within_role_reliability": within_role_reliability,
        "variance_share_explained_by_role": variance_share_role,
        "variance_share_v5_task32": 0.6386733447137616,
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
    print(f"\nWrote {SUMMARY_PATH}")
    return summary


if __name__ == "__main__":
    main()
