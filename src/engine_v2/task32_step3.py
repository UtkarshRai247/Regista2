"""
Task 32, Step 3 (A4): rebuild Task 28's overall table and Task 29's
deep-midfield table from the CROSS-FITTED per-pass Decision
(pass_der_crossfit_v5.parquet, 292 matches), using the SAME methods
(Task 28's design-effect v_i + method-of-moments tau^2 for the overall
group; Task 29's within-group v_i + DerSimonian-Laird tau^2 for the
deep-midfield group), reusing both tasks' own functions unchanged.

Qualifying players are RE-SELECTED from the cross-fitted corpus's own
pooled pass counts (>=100), the identical threshold rule, rather than
reusing the full-corpus 537 IDs verbatim -- disclosed, since the
cross-fit corpus (292 matches) is missing 7 matches some players'
passes came from, so a small number of players may fall under 100
cross-fitted passes even though they cleared it on the full corpus.
The deep-midfield group membership itself (Task 27's is_deep_midfield
flag, defined by POSITION share, not pass count or Decision) is reused
unchanged.

(Decided in the brief, before this ran: cross-fitted tables become the
standard from here on, whatever this shows.)

Run: python src/engine_v2/task32_step3.py
"""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from task28_step1_2 import estimate_sigma2w_rho, empirical_bayes_shrink
from task29_step1_2 import dersimonian_laird, shrink as dl_shrink

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
CROSSFIT_PATH = DATA_DIR / "processed" / "engine_v2" / "pass_der_crossfit_v5.parquet"
PASS_DER_V8_PATH = DATA_DIR / "processed" / "engine_v2" / "pass_der_v8.parquet"
LEADERBOARD_V5C_PATH = DATA_DIR / "processed" / "leaderboard_v5c.parquet"
DM_SHRUNK_V5_PATH = DATA_DIR / "processed" / "engine_v2" / "task29_dm_shrunk.parquet"
SUMMARY_PATH = DATA_DIR / "engine_v2_task32_step3.json"

MIN_PASSES = 100


def build_group_stats(per_pass: pd.DataFrame) -> pd.DataFrame:
    m_i = per_pass.groupby("player_id")["decision_new"].mean().rename("m_i")
    n_i = per_pass.groupby("player_id").size().rename("n_i")
    g_i = per_pass.groupby("player_id")["match_id"].nunique().rename("G_i")
    stats = pd.concat([m_i, n_i, g_i], axis=1).reset_index()
    stats["mean_passes_per_match"] = stats["n_i"] / stats["G_i"]
    return stats


def main():
    print("Task 32 Step 3 (A4): in-sample vs cross-fitted player tables ...")
    crossfit = pd.read_parquet(CROSSFIT_PATH, columns=["match_id", "event_id", "player_id", "decision"])
    crossfit = crossfit.rename(columns={"decision": "decision_new"})
    print(f"  cross-fit corpus: {len(crossfit)} passes, {crossfit['player_id'].nunique()} players")

    n_i_all = crossfit.groupby("player_id").size()
    qualifying_ids_cf = set(n_i_all[n_i_all >= MIN_PASSES].index)
    print(f"  qualifying (>= {MIN_PASSES} cross-fitted passes): {len(qualifying_ids_cf)} "
          f"(full-corpus v5 had 537)")

    print("\n  overall table (Task 28's methods, cross-fitted Decision) ...")
    pp_overall = crossfit[crossfit["player_id"].isin(qualifying_ids_cf)]
    sigma2_w, rho, _ = estimate_sigma2w_rho(pp_overall)
    stats_o = build_group_stats(pp_overall)
    stats_o["v_i"] = sigma2_w * (1 + (stats_o["mean_passes_per_match"] - 1) * rho) / stats_o["n_i"]
    shrunk_o, mu_o, tau2_o = empirical_bayes_shrink(stats_o)
    shrunk_o["shrunken_i_per100"] = shrunk_o["shrunken_i"] * 100
    shrunk_o = shrunk_o.sort_values("shrunken_i", ascending=False).reset_index(drop=True)
    shrunk_o["rank_crossfit"] = shrunk_o.index + 1
    print(f"    sigma2_w={sigma2_w:.4e}, rho={rho:.6f}, mu={mu_o*100:.5f}, tau2={tau2_o*1e4:.4e}")

    old_overall = pd.read_parquet(LEADERBOARD_V5C_PATH, columns=["player_id", "player_name", "shrunken_i_per100", "rank_overall_v5c"])
    cmp_overall = shrunk_o.merge(old_overall, on="player_id", how="inner", suffixes=("_cf", "_v5"))
    print(f"    {len(cmp_overall)} players in both tables")

    per_pass_v8 = pd.read_parquet(PASS_DER_V8_PATH, columns=["match_id", "event_id", "decision_new"])
    per_pass_cf = pd.read_parquet(CROSSFIT_PATH, columns=["match_id", "event_id", "decision"])
    joined_pp = per_pass_v8.merge(per_pass_cf, on=["match_id", "event_id"], how="inner")
    r_per_pass = float(joined_pp["decision_new"].corr(joined_pp["decision"]))
    print(f"    per-pass correlation (in-sample vs cross-fitted decision): r={r_per_pass:.4f}, n={len(joined_pp)}")

    rho_overall_tables, p_overall_tables = spearmanr(cmp_overall["rank_crossfit"], cmp_overall["rank_overall_v5c"])
    print(f"    Spearman between overall tables (rank_crossfit vs rank_overall_v5): "
          f"rho={rho_overall_tables:.4f}, p={p_overall_tables:.4g}")

    top20_cf = set(shrunk_o.head(20)["player_id"])
    top20_v5 = set(old_overall.sort_values("rank_overall_v5c").head(20)["player_id"])
    overlap = len(top20_cf & top20_v5)
    print(f"    top-20 overlap: {overlap}/20")

    print("\n  deep-midfield table (Task 29's methods, cross-fitted Decision) ...")
    dm_ids = set(pd.read_parquet(LEADERBOARD_V5C_PATH, columns=["player_id", "is_deep_midfield"])
                 .loc[lambda d: d["is_deep_midfield"], "player_id"])
    pp_dm = crossfit[crossfit["player_id"].isin(dm_ids)]
    n_i_dm = pp_dm.groupby("player_id").size()
    print(f"    {int((n_i_dm > 0).sum())}/{len(dm_ids)} deep midfielders have any cross-fitted passes "
          f"(min={int(n_i_dm.min()) if len(n_i_dm) else 0})")
    sigma2_w_dm, rho_dm, _ = estimate_sigma2w_rho(pp_dm)
    stats_dm = build_group_stats(pp_dm)
    stats_dm["v_i_within_group"] = sigma2_w_dm * (1 + (stats_dm["mean_passes_per_match"] - 1) * rho_dm) / stats_dm["n_i"]
    dl = dersimonian_laird(stats_dm["m_i"].values, stats_dm["v_i_within_group"].values)
    shrunk_dm = dl_shrink(stats_dm, dl["mu_w"], dl["tau2"], "m_i", "v_i_within_group")
    shrunk_dm["shrunken_i_per100"] = shrunk_dm["shrunken_i"] * 100
    shrunk_dm["ci_low_90_per100"] = shrunk_dm["ci_low_90"] * 100
    shrunk_dm["ci_high_90_per100"] = shrunk_dm["ci_high_90"] * 100
    names = pd.read_parquet(LEADERBOARD_V5C_PATH, columns=["player_id", "player_name"])
    shrunk_dm = shrunk_dm.merge(names, on="player_id", how="left")
    shrunk_dm = shrunk_dm.sort_values("shrunken_i", ascending=False).reset_index(drop=True)
    shrunk_dm["rank_crossfit"] = shrunk_dm.index + 1
    mu_w_dm_per100 = dl["mu_w"] * 100
    print(f"    sigma2_w={sigma2_w_dm:.4e}, rho={rho_dm:.6f}, DL mu_w={mu_w_dm_per100:.5f}, "
          f"Q={dl['Q']:.2f}, p={dl['p_value']:.4f}, tau2={dl['tau2']:.4e}")

    old_dm = pd.read_parquet(DM_SHRUNK_V5_PATH, columns=["player_id", "player_name", "rank"])
    cmp_dm = shrunk_dm.merge(old_dm, on="player_id", how="inner", suffixes=("_cf", "_v5"))
    rho_dm_tables, p_dm_tables = spearmanr(cmp_dm["rank_crossfit"], cmp_dm["rank"])
    print(f"    Spearman between DM tables (rank_crossfit vs rank_v5): rho={rho_dm_tables:.4f}, p={p_dm_tables:.4g}, "
          f"n={len(cmp_dm)}")

    n_above = shrunk_dm[shrunk_dm["ci_low_90_per100"] > mu_w_dm_per100][["player_name", "n_i", "shrunken_i_per100"]]
    n_below = shrunk_dm[shrunk_dm["ci_high_90_per100"] < mu_w_dm_per100][["player_name", "n_i", "shrunken_i_per100"]]
    print(f"    intervals entirely ABOVE mu_w ({len(n_above)}): {n_above.to_dict('records')}")
    print(f"    intervals entirely BELOW mu_w ({len(n_below)}): {n_below.to_dict('records')}")

    summary = {
        "n_matches_crossfit": crossfit["match_id"].nunique() if "match_id" in crossfit.columns else None,
        "n_qualifying_crossfit": len(qualifying_ids_cf), "n_qualifying_v5_full_corpus": 537,
        "per_pass_correlation": {"r": r_per_pass, "n": len(joined_pp)},
        "overall": {
            "sigma2_w": sigma2_w, "rho": rho, "mu": mu_o, "tau2": tau2_o,
            "spearman_tables": {"rho": float(rho_overall_tables), "p": float(p_overall_tables), "n": len(cmp_overall)},
            "top20_overlap": overlap,
        },
        "deep_midfield": {
            "n_with_any_passes": int((n_i_dm > 0).sum()), "sigma2_w": sigma2_w_dm, "rho": rho_dm, "dl": dl,
            "spearman_tables": {"rho": float(rho_dm_tables), "p": float(p_dm_tables), "n": len(cmp_dm)},
            "n_above": len(n_above), "n_below": len(n_below),
            "above_names": n_above.to_dict("records"), "below_names": n_below.to_dict("records"),
        },
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
    print(f"\nWrote {SUMMARY_PATH}")
    return summary


if __name__ == "__main__":
    main()
