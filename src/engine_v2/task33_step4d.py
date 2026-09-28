"""
Task 33, Step 4(d): player tables for Decision_v6. Task 28's method
(overall, method-of-moments) and Task 29's method (deep midfield,
DerSimonian-Laird within-group), reused UNCHANGED, applied to
Decision_v6 -- same pattern as Task 32 Step 3's crossfit-vs-in-sample
table rebuild. Qualifying players re-derived from Decision_v6's own
>=100-pass threshold (same disclosed convention as Task 32 Step 3).

Run: python src/engine_v2/task33_step4d.py
"""
import json
import warnings
from pathlib import Path

import pandas as pd
from scipy.stats import spearmanr

from task28_step1_2 import estimate_sigma2w_rho, empirical_bayes_shrink
from task29_step1_2 import dersimonian_laird, shrink as dl_shrink, FIXED_LIST
from task27_step1_deep_midfield import name_matches

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
DECISION_V6_PATH = DATA_DIR / "processed" / "engine_v2" / "decision_v6.parquet"
LEADERBOARD_V5C_PATH = DATA_DIR / "processed" / "leaderboard_v5c.parquet"
DM_SHRUNK_V5_PATH = DATA_DIR / "processed" / "engine_v2" / "task29_dm_shrunk.parquet"
SUMMARY_PATH = DATA_DIR / "engine_v2_task33_step4d.json"

MIN_PASSES = 100


def build_group_stats(per_pass: pd.DataFrame) -> pd.DataFrame:
    m_i = per_pass.groupby("player_id")["decision_new"].mean().rename("m_i")
    n_i = per_pass.groupby("player_id").size().rename("n_i")
    g_i = per_pass.groupby("player_id")["match_id"].nunique().rename("G_i")
    stats = pd.concat([m_i, n_i, g_i], axis=1).reset_index()
    stats["mean_passes_per_match"] = stats["n_i"] / stats["G_i"]
    return stats


def main():
    print("Task 33 Step 4(d): player tables for Decision_v6 ...")
    decision_v6 = pd.read_parquet(DECISION_V6_PATH, columns=["match_id", "player_id", "decision_v6", "excluded"])
    non_excluded = decision_v6[~decision_v6["excluded"]].rename(columns={"decision_v6": "decision_new"})
    print(f"  {len(non_excluded)} non-excluded passes")

    n_i_all = non_excluded.groupby("player_id").size()
    qualifying_ids = set(n_i_all[n_i_all >= MIN_PASSES].index)
    print(f"  qualifying (>= {MIN_PASSES} passes): {len(qualifying_ids)} (v5 had 537)")

    print("\n  overall table (Task 28's method) ...")
    pp_overall = non_excluded[non_excluded["player_id"].isin(qualifying_ids)]
    sigma2_w, rho, _ = estimate_sigma2w_rho(pp_overall)
    stats_o = build_group_stats(pp_overall)
    stats_o["v_i"] = sigma2_w * (1 + (stats_o["mean_passes_per_match"] - 1) * rho) / stats_o["n_i"]
    shrunk_o, mu_o, tau2_o = empirical_bayes_shrink(stats_o)
    shrunk_o = shrunk_o.sort_values("shrunken_i", ascending=False).reset_index(drop=True)
    shrunk_o["rank_v6"] = shrunk_o.index + 1
    print(f"    sigma2_w={sigma2_w:.4e}, rho={rho:.6f}, mu={mu_o*100:.5f}, tau2={tau2_o*1e4:.4e}")

    old_overall = pd.read_parquet(LEADERBOARD_V5C_PATH, columns=["player_id", "player_name", "rank_overall_v5c"])
    cmp_overall = shrunk_o.merge(old_overall, on="player_id", how="inner")
    rho_overall, p_overall = spearmanr(cmp_overall["rank_v6"], cmp_overall["rank_overall_v5c"])
    print(f"    Spearman vs v5 cross-fitted overall table: rho={rho_overall:.4f}, p={p_overall:.4g}, n={len(cmp_overall)}")

    print("\n  deep-midfield table (Task 29's method) ...")
    dm_ids = set(pd.read_parquet(LEADERBOARD_V5C_PATH, columns=["player_id", "is_deep_midfield"])
                 .loc[lambda d: d["is_deep_midfield"], "player_id"])
    pp_dm = non_excluded[non_excluded["player_id"].isin(dm_ids)]
    n_i_dm = pp_dm.groupby("player_id").size()
    print(f"    {int((n_i_dm > 0).sum())}/{len(dm_ids)} deep midfielders have any non-excluded v6 passes "
          f"(min={int(n_i_dm.min()) if len(n_i_dm) else 0})")

    sigma2_w_dm, rho_dm, _ = estimate_sigma2w_rho(pp_dm)
    stats_dm = build_group_stats(pp_dm)
    stats_dm["v_i_within_group"] = sigma2_w_dm * (1 + (stats_dm["mean_passes_per_match"] - 1) * rho_dm) / stats_dm["n_i"]
    dl = dersimonian_laird(stats_dm["m_i"].values, stats_dm["v_i_within_group"].values)
    shrunk_dm = dl_shrink(stats_dm, dl["mu_w"], dl["tau2"], "m_i", "v_i_within_group")
    shrunk_dm["shrunken_i_per100"] = shrunk_dm["shrunken_i"] * 100
    shrunk_dm["ci_low_90_per100"] = shrunk_dm["ci_low_90"] * 100
    shrunk_dm["ci_high_90_per100"] = shrunk_dm["ci_high_90"] * 100
    shrunk_dm["m_i_per100"] = shrunk_dm["m_i"] * 100

    names = pd.read_parquet(LEADERBOARD_V5C_PATH, columns=["player_id", "player_name"])
    shrunk_dm = shrunk_dm.merge(names, on="player_id", how="left")
    shrunk_dm = shrunk_dm.sort_values("shrunken_i", ascending=False).reset_index(drop=True)
    shrunk_dm["rank_v6"] = shrunk_dm.index + 1
    mu_w_dm_per100 = dl["mu_w"] * 100
    print(f"    sigma2_w={sigma2_w_dm:.4e}, rho={rho_dm:.6f}, DL mu_w={mu_w_dm_per100:.5f}, "
          f"Q={dl['Q']:.2f}, p={dl['p_value']:.4f}, tau2={dl['tau2']:.4e}")

    old_dm = pd.read_parquet(DM_SHRUNK_V5_PATH, columns=["player_id", "player_name", "rank"])
    cmp_dm = shrunk_dm.merge(old_dm, on="player_id", how="inner", suffixes=("_v6", "_v5"))
    rho_dm_tables, p_dm_tables = spearmanr(cmp_dm["rank_v6"], cmp_dm["rank"])
    print(f"    Spearman vs v5 cross-fitted DM table: rho={rho_dm_tables:.4f}, p={p_dm_tables:.4g}, n={len(cmp_dm)}")

    n_above = shrunk_dm[shrunk_dm["ci_low_90_per100"] > mu_w_dm_per100][["player_name", "n_i", "shrunken_i_per100"]]
    n_below = shrunk_dm[shrunk_dm["ci_high_90_per100"] < mu_w_dm_per100][["player_name", "n_i", "shrunken_i_per100"]]
    print(f"    intervals entirely ABOVE mu_w ({len(n_above)}): {n_above.to_dict('records')}")
    print(f"    intervals entirely BELOW mu_w ({len(n_below)}): {n_below.to_dict('records')}")

    print("\n  the six named deep midfielders (task29_step1_2.FIXED_LIST) ...")
    fixed_list_report = []
    for name in FIXED_LIST:
        hits = shrunk_dm[shrunk_dm["player_name"].apply(lambda n: name_matches(name, n))]
        if len(hits) != 1:
            fixed_list_report.append({"name": name, "note": f"{len(hits)} matches"})
            continue
        r = hits.iloc[0]
        entry = {"name": name, "player_name": r["player_name"], "n_i": int(r["n_i"]), "rank_v6": int(r["rank_v6"]),
                  "raw_per100": float(r["m_i_per100"]), "shrunken_per100": float(r["shrunken_i_per100"]),
                  "ci_90": [float(r["ci_low_90_per100"]), float(r["ci_high_90_per100"])]}
        fixed_list_report.append(entry)
        print(f"    {entry}")

    summary = {
        "n_qualifying_v6": len(qualifying_ids), "n_qualifying_v5": 537,
        "overall": {"sigma2_w": sigma2_w, "rho": rho, "mu": mu_o, "tau2": tau2_o,
                     "spearman_vs_v5": {"rho": float(rho_overall), "p": float(p_overall), "n": len(cmp_overall)}},
        "deep_midfield": {
            "n_with_any_passes": int((n_i_dm > 0).sum()), "sigma2_w": sigma2_w_dm, "rho": rho_dm, "dl": dl,
            "spearman_vs_v5": {"rho": float(rho_dm_tables), "p": float(p_dm_tables), "n": len(cmp_dm)},
            "n_above": len(n_above), "n_below": len(n_below),
            "above_names": n_above.to_dict("records"), "below_names": n_below.to_dict("records"),
            "fixed_list_report": fixed_list_report,
        },
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
    print(f"\nWrote {SUMMARY_PATH}")
    return summary


if __name__ == "__main__":
    main()
