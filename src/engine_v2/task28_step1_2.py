"""
Task 28: fix the sampling variance in the player shrinkage. Task 27's
v_i was a match-clustered variance that collapses to exactly zero for
a player seen in only one match (the within-player residuals sum to
zero by construction), giving that player NO shrinkage and an
artificially narrow interval -- the reported symptom (Bentancur n=137
narrower than Busquets n=2,994).

FIX (Step 1): a design-effect variance, estimated ONCE by pooling all
537 qualifying players via a one-way random-effects ANOVA with matches
nested in players (a player's own passes, already demeaned by that
player's own mean, form the "deviations"; matches are the nested
groups within that already-demeaned space):
  N = total passes, k = total (player, match) groups.
  For each group g (one player's passes in one match): n_g passes,
  mean deviation e_g. Grand mean of deviations = 0 exactly (guaranteed
  by per-player demeaning).
  SSB = sum_g n_g * e_g^2, df_B = k-1, MSB = SSB/df_B.
  SSW = sum_g sum_{pass in g} (e_pass - e_g)^2, df_W = N-k, MSW = SSW/df_W.
  n0 = (N - sum_g(n_g^2)/N) / (k-1)          [unbalanced-design adjustment]
  sigma2_u_hat = max(0, (MSB - MSW) / n0)     [between-match variance]
  sigma2_eps_hat = MSW                        [within-match/pass variance]
  sigma2_w = sigma2_u_hat + sigma2_eps_hat
  rho = sigma2_u_hat / sigma2_w if sigma2_w>0 else 0   [floored at 0 by construction]
Then per player i: m_i = n_i/G_i (mean passes per match), v_i =
sigma2_w * (1 + (m_i-1)*rho) / n_i -- the standard cluster-sampling
design-effect variance of a mean.

Everything else (group-specific mu/tau^2 by method of moments, shrinkage
factor, posterior SD, 90% interval) is UNCHANGED from Task 27 Step 2 --
only v_i's formula changes, per the hard rule.

Run: python src/engine_v2/task28_step1_2.py
"""
import json
import re
import unicodedata
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
PASS_DER_V8_PATH = DATA_DIR / "processed" / "engine_v2" / "pass_der_v8.parquet"
LEADERBOARD_V5B_PATH = DATA_DIR / "processed" / "leaderboard_v5b.parquet"  # Task 27's overall table (full 537)
TASK27_SUMMARY_PATH = DATA_DIR / "engine_v2_task27_step2_4_tables.json"    # has Task 27's full DM table + fixed list
DM_SHARE_PATH = DATA_DIR / "processed" / "engine_v2" / "task27_dm_share.parquet"
OUT_PARQUET = DATA_DIR / "processed" / "leaderboard_v5c.parquet"
SUMMARY_PATH = DATA_DIR / "engine_v2_task28_step1_2.json"

Z_90 = 1.645
FIXED_LIST = ["Kroos", "Modric", "Verratti", "Busquets", "De Bruyne", "Xhaka", "de Jong",
              "Kimmich", "Rodri", "Pedri", "Gundogan", "Grillitsch", "Shaparenko"]
NICKNAME_ALIASES = {"pedri": "pedro gonzalez lopez", "rodri": "rodrigo hernandez cascante"}


def normalize_name(s):
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return ""
    s = re.sub(r"'[^']*'", " ", str(s))
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-zA-Z\s]", " ", s)
    return " ".join(s.lower().split())


def name_matches(short_name, full_name):
    norm_short = normalize_name(short_name)
    norm_short = NICKNAME_ALIASES.get(norm_short, norm_short)
    short_tokens = set(norm_short.split())
    full_tokens = set(normalize_name(full_name).split())
    return len(short_tokens) > 0 and short_tokens <= full_tokens


def estimate_sigma2w_rho(per_pass: pd.DataFrame) -> tuple:
    """per_pass: player_id, match_id, decision_new. Pools ALL 537
    players' per-player-demeaned deviations into one one-way random-
    effects ANOVA with (player, match) as the nested group."""
    per_pass = per_pass.copy()
    m_i_map = per_pass.groupby("player_id")["decision_new"].mean()
    per_pass["dev"] = per_pass["decision_new"] - per_pass["player_id"].map(m_i_map)

    grp = per_pass.groupby(["player_id", "match_id"])["dev"]
    n_g = grp.size()
    e_g = grp.mean()
    N = len(per_pass)
    k = len(n_g)

    ssb = float((n_g * e_g ** 2).sum())
    df_b = k - 1
    msb = ssb / df_b

    dev_indexed = per_pass.set_index(["player_id", "match_id"])["dev"]
    e_g_full = dev_indexed.index.map(e_g)
    ssw = float(((dev_indexed.values - e_g_full.values) ** 2).sum())
    df_w = N - k
    msw = ssw / df_w

    n0 = (N - float((n_g ** 2).sum()) / N) / df_b

    sigma2_eps = msw
    sigma2_u = max(0.0, (msb - msw) / n0)
    sigma2_w = sigma2_u + sigma2_eps
    rho = max(0.0, sigma2_u / sigma2_w) if sigma2_w > 0 else 0.0

    return sigma2_w, rho, {"N": N, "k": k, "ssb": ssb, "ssw": ssw, "msb": msb, "msw": msw,
                            "n0": n0, "sigma2_u": sigma2_u, "sigma2_eps": sigma2_eps}


def empirical_bayes_shrink(table: pd.DataFrame) -> tuple:
    mu = float(table["m_i"].mean())
    tau2 = max(0.0, float(table["m_i"].var(ddof=1)) - float(table["v_i"].mean()))
    table = table.copy()
    table["shrinkage_factor"] = tau2 / (tau2 + table["v_i"])
    table["shrunken_i"] = mu + table["shrinkage_factor"] * (table["m_i"] - mu)
    table["posterior_sd_i"] = np.sqrt(tau2 * table["v_i"] / (tau2 + table["v_i"]))
    table["ci_low_90"] = table["shrunken_i"] - Z_90 * table["posterior_sd_i"]
    table["ci_high_90"] = table["shrunken_i"] + Z_90 * table["posterior_sd_i"]
    return table, mu, tau2


def to_per100(df):
    df = df.copy()
    for c in ("m_i", "shrunken_i", "posterior_sd_i", "ci_low_90", "ci_high_90"):
        df[c + "_per100"] = df[c] * 100
    return df


def main():
    print("Task 28: fixing the shrinkage sampling variance ...")
    leaderboard = pd.read_parquet(LEADERBOARD_V5B_PATH, columns=["player_id", "player_name", "position_group",
                                                                   "competitions", "is_deep_midfield", "rank_overall"])
    qualifying_ids = set(leaderboard["player_id"])

    per_pass = pd.read_parquet(PASS_DER_V8_PATH, columns=["match_id", "player_id", "decision_new"])
    per_pass = per_pass[per_pass["player_id"].isin(qualifying_ids)]
    print(f"  {len(per_pass)} per-pass rows, {per_pass['player_id'].nunique()} players")

    print("  Step 1: estimating sigma2_w and rho (one-way ANOVA, matches nested in players, pooled) ...")
    sigma2_w, rho, anova_detail = estimate_sigma2w_rho(per_pass)
    print(f"    sigma2_w={sigma2_w:.6e}, rho={rho:.6f}")
    print(f"    ANOVA detail: {json.dumps(anova_detail, indent=2, default=str)}")

    m_i_series = per_pass.groupby("player_id")["decision_new"].mean().rename("m_i")
    n_i_series = per_pass.groupby("player_id").size().rename("n_i")
    g_i_series = per_pass.groupby("player_id")["match_id"].nunique().rename("G_i")
    stats = pd.concat([m_i_series, n_i_series, g_i_series], axis=1).reset_index()
    stats["mean_passes_per_match"] = stats["n_i"] / stats["G_i"]
    stats["v_i"] = sigma2_w * (1 + (stats["mean_passes_per_match"] - 1) * rho) / stats["n_i"]
    stats = stats.merge(leaderboard[["player_id", "player_name", "position_group", "competitions", "is_deep_midfield"]],
                         on="player_id", how="left")

    print("\n  (a) overall group (n=537) shrinkage with fixed v_i ...")
    overall, mu_overall, tau2_overall = empirical_bayes_shrink(stats)
    print(f"    mu={mu_overall*100:.5f}, tau^2={tau2_overall*1e4:.6e}, "
          f"shrinkage factor range=[{overall['shrinkage_factor'].min():.4f}, {overall['shrinkage_factor'].max():.4f}]")

    dm_group = stats[stats["is_deep_midfield"]].copy()
    print(f"  (b) deep-midfield group (n={len(dm_group)}) shrinkage with fixed v_i ...")
    dm_shrunk, mu_dm, tau2_dm = empirical_bayes_shrink(dm_group)
    print(f"    mu={mu_dm*100:.5f}, tau^2={tau2_dm*1e4:.6e}, "
          f"shrinkage factor range=[{dm_shrunk['shrinkage_factor'].min():.4f}, {dm_shrunk['shrinkage_factor'].max():.4f}]")

    overall = to_per100(overall).sort_values("shrunken_i", ascending=False).reset_index(drop=True)
    overall["rank_overall_v5c"] = overall.index + 1

    dm_shrunk = to_per100(dm_shrunk).sort_values("shrunken_i", ascending=False).reset_index(drop=True)
    dm_shrunk["rank_deep_midfield_v5c"] = dm_shrunk.index + 1
    dm_std = dm_shrunk["shrunken_i_per100"].std(ddof=1)
    dm_shrunk["z_within_dm"] = (dm_shrunk["shrunken_i_per100"] - dm_shrunk["shrunken_i_per100"].mean()) / dm_std

    dm_mean = mu_dm * 100
    n_above = int((dm_shrunk["ci_low_90_per100"] > dm_mean).sum())
    n_below = int((dm_shrunk["ci_high_90_per100"] < dm_mean).sum())
    print(f"\n  DM group: {n_above} intervals entirely ABOVE the group mean, {n_below} entirely BELOW")

    # Symptom check: Bentancur, Busquets, Mings interval widths
    for name in ["Bentancur", "Busquets", "Mings"]:
        hits = overall[overall["player_name"].apply(lambda n: name_matches(name, n))]
        for _, r in hits.iterrows():
            width = r["ci_high_90_per100"] - r["ci_low_90_per100"]
            print(f"    {r['player_name']}: n={r['n_i']}, G={r['G_i']}, 90% width={width:.4f} "
                  f"(+/-{width/2:.4f})")

    print("\n  Spearman correlation with Task 27's ranking ...")
    overall_task27 = pd.read_parquet(LEADERBOARD_V5B_PATH, columns=["player_id", "rank_overall"])
    overall_cmp = overall.merge(overall_task27, on="player_id", how="left", suffixes=("", "_task27"))
    rho_overall, p_overall = spearmanr(overall_cmp["rank_overall_v5c"], overall_cmp["rank_overall"])
    print(f"    overall table: spearman rho={rho_overall:.4f} (p={p_overall:.4g})")

    task27_summary = json.loads(TASK27_SUMMARY_PATH.read_text())
    task27_dm = pd.DataFrame(task27_summary["deep_midfield_table"])[["player_id", "rank_deep_midfield"]]
    dm_cmp = dm_shrunk.merge(task27_dm, on="player_id", how="left")
    rho_dm, p_dm = spearmanr(dm_cmp["rank_deep_midfield_v5c"], dm_cmp["rank_deep_midfield"])
    print(f"    deep-midfield table: spearman rho={rho_dm:.4f} (p={p_dm:.4g})")

    top20 = overall.head(20)
    bottom20 = overall.tail(20).sort_values("rank_overall_v5c")

    print("\n  Top 5 overall (fixed v_i):")
    for _, r in top20.head(5).iterrows():
        print(f"    {r['rank_overall_v5c']} {r['player_name']} n={r['n_i']} G={r['G_i']} "
              f"raw={r['m_i_per100']:.4f} shrunk={r['shrunken_i_per100']:.4f} "
              f"[{r['ci_low_90_per100']:.4f}, {r['ci_high_90_per100']:.4f}]")

    print("\n  (c) fixed-list report ...")
    fixed_list_report = []
    for short_name in FIXED_LIST:
        hits = overall[overall["player_name"].apply(lambda n: name_matches(short_name, n))]
        if len(hits) != 1:
            fixed_list_report.append({"name": short_name, "note": f"{len(hits)} matches"})
            continue
        r = hits.iloc[0]
        pid = r["player_id"]
        dm_row = dm_shrunk[dm_shrunk["player_id"] == pid]
        entry = {
            "name": short_name, "player_name": r["player_name"], "n_i": int(r["n_i"]), "G_i": int(r["G_i"]),
            "overall_rank": int(r["rank_overall_v5c"]), "shrunken_per100": float(r["shrunken_i_per100"]),
            "ci_90": [float(r["ci_low_90_per100"]), float(r["ci_high_90_per100"])],
            "is_deep_midfield": bool(r["is_deep_midfield"]),
        }
        entry["deep_midfield_rank"] = int(dm_row.iloc[0]["rank_deep_midfield_v5c"]) if len(dm_row) else "not in group"
        fixed_list_report.append(entry)
        print(f"    {entry}")

    overall.to_parquet(OUT_PARQUET)
    print(f"\nWrote {OUT_PARQUET}")

    def records(df, cols):
        return df[cols].to_dict("records")

    top_bottom_cols = ["player_id", "player_name", "position_group", "competitions", "n_i", "G_i",
                        "m_i_per100", "shrunken_i_per100", "ci_low_90_per100", "ci_high_90_per100", "rank_overall_v5c"]
    dm_cols = ["player_id", "player_name", "n_i", "G_i", "m_i_per100", "shrunken_i_per100",
               "ci_low_90_per100", "ci_high_90_per100", "z_within_dm", "rank_deep_midfield_v5c"]

    summary = {
        "sigma2_w": sigma2_w, "rho": rho, "anova_detail": anova_detail,
        "n_overall": len(overall), "mu_overall_per100": mu_overall * 100, "tau2_overall_per100sq": tau2_overall * 1e4,
        "shrinkage_factor_range_overall": [float(overall["shrinkage_factor"].min()), float(overall["shrinkage_factor"].max())],
        "n_deep_midfield": len(dm_shrunk), "mu_dm_per100": mu_dm * 100, "tau2_dm_per100sq": tau2_dm * 1e4,
        "shrinkage_factor_range_dm": [float(dm_shrunk["shrinkage_factor"].min()), float(dm_shrunk["shrinkage_factor"].max())],
        "n_dm_intervals_above_group_mean": n_above, "n_dm_intervals_below_group_mean": n_below,
        "spearman_overall_vs_task27": {"rho": float(rho_overall), "p": float(p_overall)},
        "spearman_dm_vs_task27": {"rho": float(rho_dm), "p": float(p_dm)},
        "top20": records(top20, top_bottom_cols), "bottom20": records(bottom20, top_bottom_cols),
        "deep_midfield_table": records(dm_shrunk, dm_cols),
        "fixed_list_report": fixed_list_report,
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
    print(f"\nWrote {SUMMARY_PATH}")
    return summary


if __name__ == "__main__":
    main()
