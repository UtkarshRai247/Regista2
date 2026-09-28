"""
Task 29, Steps 1-2: two independent fixes to Task 28's tau^2=0 null for
the 111 deep midfielders -- (1) sigma2_w/rho re-estimated WITHIN the
deep-midfield group only (not pooled across all 537 players, whose
forwards likely have more variable per-pass Decision), and (2) a
precision-weighted (DerSimonian-Laird) between-player variance instead
of Task 28's unweighted method-of-moments estimator (which let ~60
100-250-pass players dominate over the handful of 800-3,500-pass
players).

Run: python src/engine_v2/task29_step1_2.py
"""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import chi2
from scipy.optimize import minimize_scalar

from task28_step1_2 import estimate_sigma2w_rho

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
PASS_DER_V8_PATH = DATA_DIR / "processed" / "engine_v2" / "pass_der_v8.parquet"
LEADERBOARD_V5C_PATH = DATA_DIR / "processed" / "leaderboard_v5c.parquet"
TASK28_SUMMARY_PATH = DATA_DIR / "engine_v2_task28_step1_2.json"
SUMMARY_PATH = DATA_DIR / "engine_v2_task29_step1_2.json"

Z_90 = 1.645
FIXED_LIST = ["Kroos", "Verratti", "Busquets", "Xhaka", "Gundogan", "Grillitsch"]


def dersimonian_laird(m: np.ndarray, v: np.ndarray) -> dict:
    w = 1.0 / v
    mu_w = float(np.sum(w * m) / np.sum(w))
    Q = float(np.sum(w * (m - mu_w) ** 2))
    k = len(m)
    denom = np.sum(w) - np.sum(w ** 2) / np.sum(w)
    tau2 = max(0.0, (Q - (k - 1)) / denom)
    p_value = float(1 - chi2.cdf(Q, df=k - 1))
    return {"mu_w": mu_w, "Q": Q, "k": k, "df": k - 1, "p_value": p_value, "tau2": tau2}


def reml_tau2(m: np.ndarray, v: np.ndarray) -> dict:
    def neg2ll(tau2):
        w = 1.0 / (v + tau2)
        mu = np.sum(w * m) / np.sum(w)
        ll = -0.5 * (np.sum(np.log(v + tau2)) + np.log(np.sum(w)) + np.sum(w * (m - mu) ** 2))
        return -2 * ll

    res = minimize_scalar(neg2ll, bounds=(0, max(np.var(m, ddof=1) * 10, 1e-6)), method="bounded",
                           options={"xatol": 1e-12})
    tau2 = float(res.x)
    w = 1.0 / (v + tau2)
    mu = float(np.sum(w * m) / np.sum(w))
    return {"tau2": tau2, "mu_w": mu, "converged": bool(res.success)}


def shrink(table: pd.DataFrame, mu_w: float, tau2: float, m_col: str, v_col: str) -> pd.DataFrame:
    table = table.copy()
    table["shrinkage_factor"] = tau2 / (tau2 + table[v_col])
    table["shrunken_i"] = mu_w + table["shrinkage_factor"] * (table[m_col] - mu_w)
    table["posterior_sd_i"] = np.sqrt(tau2 * table[v_col] / (tau2 + table[v_col]))
    table["ci_low_90"] = table["shrunken_i"] - Z_90 * table["posterior_sd_i"]
    table["ci_high_90"] = table["shrunken_i"] + Z_90 * table["posterior_sd_i"]
    return table


def main():
    print("Task 29 Steps 1-2: within-group noise + precision-weighted tau^2 ...")
    leaderboard = pd.read_parquet(LEADERBOARD_V5C_PATH)
    dm_ids = set(leaderboard.loc[leaderboard["is_deep_midfield"], "player_id"])
    print(f"  {len(dm_ids)} deep midfielders")

    per_pass = pd.read_parquet(PASS_DER_V8_PATH, columns=["match_id", "player_id", "decision_new"])
    per_pass_dm = per_pass[per_pass["player_id"].isin(dm_ids)]
    print(f"  {len(per_pass_dm)} per-pass rows (deep midfielders only)")

    print("\n  Step 1: sigma2_w/rho within the deep-midfield group only ...")
    sigma2_w_dm, rho_dm, anova_dm = estimate_sigma2w_rho(per_pass_dm)
    print(f"    within-group: sigma2_w={sigma2_w_dm:.6e}, rho={rho_dm:.6f}")

    task28 = json.loads(TASK28_SUMMARY_PATH.read_text())
    sigma2_w_pooled, rho_pooled = task28["sigma2_w"], task28["rho"]
    print(f"    Task 28 pooled (537 players): sigma2_w={sigma2_w_pooled:.6e}, rho={rho_pooled:.6f}")

    m_i = per_pass_dm.groupby("player_id")["decision_new"].mean().rename("m_i")
    n_i = per_pass_dm.groupby("player_id").size().rename("n_i")
    g_i = per_pass_dm.groupby("player_id")["match_id"].nunique().rename("G_i")
    stats = pd.concat([m_i, n_i, g_i], axis=1).reset_index()
    stats["mean_passes_per_match"] = stats["n_i"] / stats["G_i"]
    stats["v_i_within_group"] = sigma2_w_dm * (1 + (stats["mean_passes_per_match"] - 1) * rho_dm) / stats["n_i"]
    stats["v_i_task28_pooled"] = sigma2_w_pooled * (1 + (stats["mean_passes_per_match"] - 1) * rho_pooled) / stats["n_i"]
    meta = leaderboard.loc[leaderboard["is_deep_midfield"], ["player_id", "player_name", "position_group", "competitions"]]
    stats = stats.merge(meta, on="player_id", how="left")

    print("\n  Step 2: DerSimonian-Laird tau^2 (PRIMARY), within-group v_i ...")
    dl_within = dersimonian_laird(stats["m_i"].values, stats["v_i_within_group"].values)
    print(f"    {dl_within}")

    print("  DerSimonian-Laird tau^2, Task 28's pooled v_i (comparison) ...")
    dl_pooled = dersimonian_laird(stats["m_i"].values, stats["v_i_task28_pooled"].values)
    print(f"    {dl_pooled}")

    print("  REML tau^2 (SECONDARY), within-group v_i ...")
    reml_within = reml_tau2(stats["m_i"].values, stats["v_i_within_group"].values)
    print(f"    {reml_within}")

    print("\n  Shrinking (PRIMARY: DL tau^2, within-group v_i) ...")
    shrunk_primary = shrink(stats, dl_within["mu_w"], dl_within["tau2"], "m_i", "v_i_within_group")
    shrunk_pooled_v = shrink(stats, dl_pooled["mu_w"], dl_pooled["tau2"], "m_i", "v_i_task28_pooled")

    def to_per100(df, suffix=""):
        df = df.copy()
        for c in ("m_i", "shrunken_i", "posterior_sd_i", "ci_low_90", "ci_high_90"):
            df[c + "_per100" + suffix] = df[c] * 100
        return df

    shrunk_primary = to_per100(shrunk_primary)
    shrunk_primary = shrunk_primary.sort_values("shrunken_i", ascending=False).reset_index(drop=True)
    shrunk_primary["rank"] = shrunk_primary.index + 1

    mu_w_per100 = dl_within["mu_w"] * 100
    n_above = int((shrunk_primary["ci_low_90_per100"] > mu_w_per100).sum())
    n_below = int((shrunk_primary["ci_high_90_per100"] < mu_w_per100).sum())
    print(f"\n  {n_above} intervals entirely ABOVE mu_w, {n_below} entirely BELOW (PRIMARY)")

    shrunk_pooled_v = to_per100(shrunk_pooled_v)
    shrunk_pooled_v = shrunk_pooled_v.sort_values("shrunken_i", ascending=False).reset_index(drop=True)

    print("\n  Fixed-list report (6 named players in the group) ...")
    import re, unicodedata
    def normalize_name(s):
        if s is None or (isinstance(s, float) and pd.isna(s)):
            return ""
        s = re.sub(r"'[^']*'", " ", str(s))
        s = unicodedata.normalize("NFKD", s)
        s = "".join(c for c in s if not unicodedata.combining(c))
        s = re.sub(r"[^a-zA-Z\s]", " ", s)
        return " ".join(s.lower().split())
    def name_matches(short_name, full_name):
        short_tokens = set(normalize_name(short_name).split())
        full_tokens = set(normalize_name(full_name).split())
        return len(short_tokens) > 0 and short_tokens <= full_tokens

    fixed_list_report = []
    for name in FIXED_LIST:
        hits = shrunk_primary[shrunk_primary["player_name"].apply(lambda n: name_matches(name, n))]
        if len(hits) != 1:
            fixed_list_report.append({"name": name, "note": f"{len(hits)} matches"})
            continue
        r = hits.iloc[0]
        entry = {"name": name, "player_name": r["player_name"], "n_i": int(r["n_i"]), "G_i": int(r["G_i"]),
                 "rank": int(r["rank"]), "raw_per100": float(r["m_i_per100"]),
                 "shrunken_per100": float(r["shrunken_i_per100"]),
                 "ci_90": [float(r["ci_low_90_per100"]), float(r["ci_high_90_per100"])]}
        fixed_list_report.append(entry)
        print(f"    {entry}")

    summary = {
        "n_deep_midfielders": len(dm_ids),
        "sigma2_w_within_group": sigma2_w_dm, "rho_within_group": rho_dm, "anova_within_group": anova_dm,
        "sigma2_w_task28_pooled": sigma2_w_pooled, "rho_task28_pooled": rho_pooled,
        "dl_primary_within_group": dl_within, "dl_comparison_pooled_v": dl_pooled, "reml_within_group": reml_within,
        "mu_w_per100": mu_w_per100, "n_intervals_above_muw": n_above, "n_intervals_below_muw": n_below,
        "table_primary": shrunk_primary.to_dict("records"),
        "table_pooled_v_comparison": shrunk_pooled_v[["player_id", "player_name", "n_i", "G_i", "m_i_per100",
                                                        "shrunken_i_per100", "ci_low_90_per100", "ci_high_90_per100"]].to_dict("records"),
        "fixed_list_report": fixed_list_report,
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))

    stats_out = DATA_DIR / "processed" / "engine_v2" / "task29_dm_shrunk.parquet"
    shrunk_primary.to_parquet(stats_out)
    print(f"\nWrote {SUMMARY_PATH} and {stats_out}")
    return summary


if __name__ == "__main__":
    main()
