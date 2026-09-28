"""
Task 27, Steps 2+4: fix the shrinkage (empirical Bayes, per player,
match-clustered sampling variance) and rebuild the leaderboard tables
on the corrected DEEP MIDFIELD group (Step 1).

Step 2 formula, exactly as specified:
  m_i = player's mean Decision per pass; n_i = eligible passes.
  v_i = (1/n_i^2) * sum over matches of (sum over that match's passes
        of (d - m_i))^2                          [match-clustered var]
  Within the group being ranked: mu = mean(m_i); tau^2 = max(0,
  var(m_i) - mean(v_i)).
  shrunken_i = mu + tau^2/(tau^2+v_i) * (m_i - mu)
  posterior_SD_i = sqrt(tau^2 * v_i / (tau^2+v_i))
  90% interval = shrunken_i +/- 1.645 * SD_i
Reported per 100 passes (m_i, shrunken_i, SD_i, interval bounds all
scaled by 100 for reporting -- consistent since Var scales by 100^2).

Run: python src/engine_v2/task27_step2_4_tables.py
"""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
PASS_DER_V8_PATH = DATA_DIR / "processed" / "engine_v2" / "pass_der_v8.parquet"
LEADERBOARD_V5_PATH = DATA_DIR / "processed" / "leaderboard_v5.parquet"
DM_SHARE_PATH = DATA_DIR / "processed" / "engine_v2" / "task27_dm_share.parquet"
CORR_V5_PATH = DATA_DIR / "engine_v2_task26_step5_correlations.json"
MOVE_RESID_V2_PATH = DATA_DIR / "processed" / "tempo_redesign_move_residuals_v2.parquet"
HOLD_RESID_V2_PATH = DATA_DIR / "processed" / "tempo_redesign_hold_residuals_v2.parquet"
TIME_ON_BALL_PATH = DATA_DIR / "processed" / "tempo_time_on_ball.parquet"
PLAYER_SEASON_METRICS_PATH = DATA_DIR / "processed" / "player_season_metrics.parquet"
OUT_PARQUET = DATA_DIR / "processed" / "leaderboard_v5b.parquet"
SUMMARY_PATH = DATA_DIR / "engine_v2_task27_step2_4_tables.json"

TOP_BOTTOM_N = 20
Z_90 = 1.645
FIXED_LIST = ["Kroos", "Modric", "Verratti", "Busquets", "De Bruyne", "Xhaka", "de Jong",
              "Kimmich", "Rodri", "Pedri", "Gundogan", "Grillitsch", "Shaparenko"]


def compute_match_clustered_variance(per_pass: pd.DataFrame) -> pd.DataFrame:
    """per_pass: columns player_id, match_id, decision_new. Returns one
    row per player_id: m_i, n_i, v_i."""
    m_i = per_pass.groupby("player_id")["decision_new"].mean().rename("m_i")
    per_pass = per_pass.merge(m_i, on="player_id", how="left")
    per_pass["resid"] = per_pass["decision_new"] - per_pass["m_i"]
    match_sums = per_pass.groupby(["player_id", "match_id"])["resid"].sum()
    v_i = (match_sums ** 2).groupby("player_id").sum()
    n_i = per_pass.groupby("player_id").size()
    out = pd.DataFrame({"m_i": m_i, "n_i": n_i, "sum_sq_match_sums": v_i})
    out["v_i"] = out["sum_sq_match_sums"] / (out["n_i"] ** 2)
    return out.drop(columns=["sum_sq_match_sums"]).reset_index()


def empirical_bayes_shrink(table: pd.DataFrame) -> tuple:
    """table: player_id, m_i, n_i, v_i, for one group. Returns table
    with shrunken_i, posterior_sd_i, ci_low_90, ci_high_90 added (all in
    RAW per-pass units, not yet x100), plus (mu, tau2)."""
    mu = float(table["m_i"].mean())
    tau2 = max(0.0, float(table["m_i"].var(ddof=1)) - float(table["v_i"].mean()))
    table = table.copy()
    table["shrinkage_factor"] = tau2 / (tau2 + table["v_i"])
    table["shrunken_i"] = mu + table["shrinkage_factor"] * (table["m_i"] - mu)
    table["posterior_sd_i"] = np.sqrt(tau2 * table["v_i"] / (tau2 + table["v_i"]))
    table["ci_low_90"] = table["shrunken_i"] - Z_90 * table["posterior_sd_i"]
    table["ci_high_90"] = table["shrunken_i"] + Z_90 * table["posterior_sd_i"]
    return table, mu, tau2


def main():
    print("Task 27 Steps 2+4: empirical Bayes shrinkage + rebuilt tables ...")
    leaderboard = pd.read_parquet(LEADERBOARD_V5_PATH, columns=["player_id", "player_name", "position_group", "competitions"])
    dm = pd.read_parquet(DM_SHARE_PATH, columns=["player_id", "dm_share", "is_deep_midfield"])
    qualifying_ids = set(leaderboard["player_id"])

    per_pass = pd.read_parquet(PASS_DER_V8_PATH, columns=["match_id", "player_id", "decision_new"])
    per_pass = per_pass[per_pass["player_id"].isin(qualifying_ids)]
    print(f"  {len(per_pass)} per-pass rows, {per_pass['player_id'].nunique()} players")

    print("  computing match-clustered variance v_i per player ...")
    stats = compute_match_clustered_variance(per_pass)
    stats = stats.merge(leaderboard, on="player_id", how="left").merge(dm, on="player_id", how="left")

    print("  (a) overall group (n=537) empirical Bayes shrinkage ...")
    overall, mu_overall, tau2_overall = empirical_bayes_shrink(stats)
    print(f"    mu={mu_overall*100:.5f}, tau^2={tau2_overall*1e4:.6e} (x100^2 units), "
          f"shrinkage factor range=[{overall['shrinkage_factor'].min():.4f}, {overall['shrinkage_factor'].max():.4f}]")

    dm_group = stats[stats["is_deep_midfield"]].copy()
    print(f"  (b) deep-midfield group (n={len(dm_group)}) empirical Bayes shrinkage, WITHIN group ...")
    dm_shrunk, mu_dm, tau2_dm = empirical_bayes_shrink(dm_group)
    print(f"    mu={mu_dm*100:.5f}, tau^2={tau2_dm*1e4:.6e} (x100^2 units), "
          f"shrinkage factor range=[{dm_shrunk['shrinkage_factor'].min():.4f}, {dm_shrunk['shrinkage_factor'].max():.4f}]")

    def to_per100(df):
        df = df.copy()
        for c in ("m_i", "shrunken_i", "posterior_sd_i", "ci_low_90", "ci_high_90"):
            df[c + "_per100"] = df[c] * 100
        return df

    overall = to_per100(overall).sort_values("shrunken_i", ascending=False).reset_index(drop=True)
    overall["rank_overall"] = overall.index + 1
    overall["group_mean_overall"] = mu_overall * 100
    overall["group_std"] = overall["shrunken_i_per100"].std(ddof=1)
    overall["z_overall"] = (overall["shrunken_i_per100"] - overall["shrunken_i_per100"].mean()) / overall["group_std"]

    dm_shrunk = to_per100(dm_shrunk).sort_values("shrunken_i", ascending=False).reset_index(drop=True)
    dm_shrunk["rank_deep_midfield"] = dm_shrunk.index + 1
    dm_std = dm_shrunk["shrunken_i_per100"].std(ddof=1)
    dm_shrunk["z_within_dm"] = (dm_shrunk["shrunken_i_per100"] - dm_shrunk["shrunken_i_per100"].mean()) / dm_std

    dm_mean = mu_dm * 100
    n_above = int((dm_shrunk["ci_low_90_per100"] > dm_mean).sum())
    n_below = int((dm_shrunk["ci_high_90_per100"] < dm_mean).sum())
    print(f"  DM group: {n_above} players' 90% intervals lie entirely ABOVE the group mean, "
          f"{n_below} entirely BELOW")

    top20 = overall.head(TOP_BOTTOM_N)
    bottom20 = overall.tail(TOP_BOTTOM_N).sort_values("rank_overall")

    print("\n  Top 5 overall (Step 2 shrinkage):")
    for _, r in top20.head(5).iterrows():
        print(f"    {r['rank_overall']} {r['player_name']} n={r['n_i']} raw={r['m_i_per100']:.4f} "
              f"shrunk={r['shrunken_i_per100']:.4f} [{r['ci_low_90_per100']:.4f}, {r['ci_high_90_per100']:.4f}]")

    print("\n  (c) fixed-list report ...")
    overall_rank_lookup = overall.set_index("player_id")["rank_overall"].to_dict()
    dm_rank_lookup = dm_shrunk.set_index("player_id")["rank_deep_midfield"].to_dict()
    dm_share_lookup = dm.set_index("player_id")["dm_share"].to_dict()
    is_dm_lookup = dm.set_index("player_id")["is_deep_midfield"].to_dict()
    overall_row_lookup = overall.set_index("player_id")

    import re, unicodedata
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

    fixed_list_report = []
    for short_name in FIXED_LIST:
        hits = overall[overall["player_name"].apply(lambda n: name_matches(short_name, n))]
        if len(hits) != 1:
            fixed_list_report.append({"name": short_name, "note": f"{len(hits)} matches"})
            continue
        r = hits.iloc[0]
        pid = r["player_id"]
        entry = {
            "name": short_name, "player_name": r["player_name"],
            "overall_rank": int(r["rank_overall"]), "n_eligible_passes": int(r["n_i"]),
            "shrunken_per100": float(r["shrunken_i_per100"]),
            "ci_90": [float(r["ci_low_90_per100"]), float(r["ci_high_90_per100"])],
            "dm_share": float(dm_share_lookup.get(pid, 0.0)),
            "is_deep_midfield": bool(is_dm_lookup.get(pid, False)),
        }
        if is_dm_lookup.get(pid, False):
            entry["deep_midfield_rank"] = int(dm_rank_lookup[pid])
        else:
            entry["deep_midfield_rank"] = "not in group"
        fixed_list_report.append(entry)
        print(f"    {entry}")

    print("\n  (d) correlation matrix within the deep-midfield group ...")
    dm_ids = set(dm_shrunk["player_id"])
    move_resid = pd.read_parquet(MOVE_RESID_V2_PATH, columns=["player_id", "residual"])
    move = move_resid[move_resid["player_id"].isin(dm_ids)].groupby("player_id")["residual"].mean().rename("move_on_speed")
    hold_resid = pd.read_parquet(HOLD_RESID_V2_PATH, columns=["player_id", "residual"])
    hold = hold_resid[hold_resid["player_id"].isin(dm_ids)].groupby("player_id")["residual"].agg(
        lambda s: float(s.std(ddof=1)) if len(s) > 1 else None).rename("hold_variation")
    tob = pd.read_parquet(TIME_ON_BALL_PATH, columns=["player_id", "time_on_ball", "resolved"])
    tob = tob[tob["resolved"] & tob["player_id"].isin(dm_ids)]
    tob_med = tob.groupby("player_id")["time_on_ball"].median().rename("median_time_on_ball")
    psm = pd.read_parquet(PLAYER_SEASON_METRICS_PATH,
                           columns=["player_id", "n_eligible_passes", "completion_pct", "progressive_passes_per_90", "xa_per_90"])
    psm = psm[psm["player_id"].isin(dm_ids)]
    ref_rows = []
    for pid, g in psm.groupby("player_id"):
        w = g["n_eligible_passes"]
        ref_rows.append({"player_id": pid,
                          "completion_pct": float(np.average(g["completion_pct"].dropna(), weights=w.loc[g["completion_pct"].dropna().index])) if g["completion_pct"].notna().any() else np.nan,
                          "progressive_passes_per_90": float(np.average(g["progressive_passes_per_90"].dropna(), weights=w.loc[g["progressive_passes_per_90"].dropna().index])) if g["progressive_passes_per_90"].notna().any() else np.nan,
                          "xa_per_90": float(np.average(g["xa_per_90"].dropna(), weights=w.loc[g["xa_per_90"].dropna().index])) if g["xa_per_90"].notna().any() else np.nan})
    ref = pd.DataFrame(ref_rows)

    dm_corr_table = dm_shrunk[["player_id", "shrunken_i_per100"]].rename(columns={"shrunken_i_per100": "decision_per_100"})
    # risk isn't part of Step 2's shrinkage; reuse raw risk_per_100 pooled mean for the correlation matrix, unshrunk (same as Task 26 Step 5)
    der = pd.read_parquet(PASS_DER_V8_PATH, columns=["player_id", "risk_new"])
    der = der[der["player_id"].isin(dm_ids)]
    risk = der.groupby("player_id")["risk_new"].mean().mul(100).rename("risk_per_100").reset_index()
    dm_corr_table = dm_corr_table.merge(risk, on="player_id", how="left").merge(move, on="player_id", how="left") \
        .merge(hold, on="player_id", how="left").merge(tob_med, on="player_id", how="left").merge(ref, on="player_id", how="left")

    metric_cols = ["decision_per_100", "risk_per_100", "move_on_speed", "hold_variation", "median_time_on_ball",
                   "completion_pct", "progressive_passes_per_90", "xa_per_90"]
    corr_dm = dm_corr_table[metric_cols].corr()
    pairs_beyond = []
    for i, a in enumerate(metric_cols):
        for c in metric_cols[i + 1:]:
            r = corr_dm.loc[a, c]
            if pd.notna(r) and abs(r) > 0.7:
                pairs_beyond.append({"pair": [a, c], "r": float(r)})
    print(f"    n={len(dm_corr_table)}, pairs |r|>0.7: {pairs_beyond}")
    print(f"    Decision vs xA per 90 (within deep-midfield): r={corr_dm.loc['decision_per_100', 'xa_per_90']:.4f}")

    overall.to_parquet(OUT_PARQUET)
    print(f"\nWrote {OUT_PARQUET}")

    def records(df, cols):
        return df[cols].to_dict("records")

    top_bottom_cols = ["player_id", "player_name", "position_group", "competitions", "n_i",
                        "m_i_per100", "shrunken_i_per100", "ci_low_90_per100", "ci_high_90_per100", "rank_overall"]
    dm_cols = ["player_id", "player_name", "n_i", "m_i_per100", "shrunken_i_per100",
               "ci_low_90_per100", "ci_high_90_per100", "z_within_dm", "rank_deep_midfield"]

    summary = {
        "n_overall": len(overall), "mu_overall_per100": mu_overall * 100, "tau2_overall_per100sq": tau2_overall * 1e4,
        "shrinkage_factor_range_overall": [float(overall["shrinkage_factor"].min()), float(overall["shrinkage_factor"].max())],
        "n_deep_midfield": len(dm_shrunk), "mu_dm_per100": mu_dm * 100, "tau2_dm_per100sq": tau2_dm * 1e4,
        "shrinkage_factor_range_dm": [float(dm_shrunk["shrinkage_factor"].min()), float(dm_shrunk["shrinkage_factor"].max())],
        "n_dm_intervals_above_group_mean": n_above, "n_dm_intervals_below_group_mean": n_below,
        "top20": records(top20, top_bottom_cols), "bottom20": records(bottom20, top_bottom_cols),
        "deep_midfield_table": records(dm_shrunk, dm_cols),
        "fixed_list_report": fixed_list_report,
        "dm_correlation_matrix": corr_dm.to_dict(), "dm_correlation_n": len(dm_corr_table),
        "dm_pairs_beyond_0.7": pairs_beyond,
        "dm_decision_vs_xa_per_90": float(corr_dm.loc["decision_per_100", "xa_per_90"]),
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
    print(f"\nWrote {SUMMARY_PATH}")
    return summary


if __name__ == "__main__":
    main()
