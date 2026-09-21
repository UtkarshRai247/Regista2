"""
Task 06 — Study A: confirmation, Gate D (Amendment v2-2), sensitivity
checks. Governed by docs/specs/analysis-plan-v2.md (plan section 3,
Amendments v2-1 and v2-2) and docs/specs/task-06-study-a-confirmation.md.

HARD RULE: only the 10 candidates in docs/results/05-study-a-candidates.csv
are ever aggregated into a G/P/s/L statistic on the confirmation half. No
other (cell, type) pair is computed. The confirmation-half parquet reads
below use the same pyarrow filter-pushdown pattern as Task 05.

Run: python src/decision_engine/task06_study_a_confirmation.py
"""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from statsmodels.stats.multitest import multipletests

from decompose import compute_realized_values
from task04_situation_context import DATA_DIR, INTL_COMPETITIONS
from task05_study_a_discovery import (
    BOOTSTRAP_SEED, EV_PATH, N_BOOTSTRAP, PASSES_PATH, STANDARD_SEASON_MATCHES,
    SPLIT_PATH, TYPED_PATH, build_available_types_table, join_ev, recover_raw_positions,
)

warnings.filterwarnings("ignore")

CANDIDATES_CSV = Path(__file__).parent.parent.parent / "docs" / "results" / "05-study-a-candidates.csv"
PV_MODEL_PATH = DATA_DIR / "processed" / "possession_value_model.json"

STEP1_OUT = DATA_DIR / "processed" / "study_a_confirmation_step1.parquet"
GATE_D_OUT = DATA_DIR / "processed" / "study_a_gate_d.parquet"
POOLED_OUT = DATA_DIR / "processed" / "study_a_pooled_diagnostic.parquet"
SENSITIVITY_OUT = DATA_DIR / "task06_sensitivity.json"
SUMMARY_PATH = DATA_DIR / "task06_study_a_confirmation.json"

HIGH_VISIBILITY_MIN = 18
COMP_SEASON_MIN_PASSES = 100
ALL_OPTION_TYPES = [f"{d}_{l}" for d in ("forward", "lateral", "backward") for l in ("short", "medium", "long")]


def confirmation_match_ids() -> list:
    split = pd.read_csv(SPLIT_PATH)
    return sorted(split.loc[split["half"] == "confirmation", "match_id"].tolist())


def parse_candidates() -> list:
    df = pd.read_csv(CANDIDATES_CSV)
    rows = []
    for _, r in df.iterrows():
        parts = dict(p.split("=") for p in r["cell"].split("|"))
        rows.append({"zone": parts["zone"], "under_pressure": parts["pressure"] == "yes",
                     "game_state": parts["state"], "option_type": r["type"],
                     "discovery_G": float(r["G"])})
    return rows


def load_and_prepare(match_ids: list):
    filt = [("match_id", "in", match_ids)]
    typed = pd.read_parquet(TYPED_PATH, filters=filt)
    passes = pd.read_parquet(PASSES_PATH, filters=filt)
    ev = pd.read_parquet(EV_PATH, columns=["match_id", "event_id", "team", "period",
                                            "candidate_x", "candidate_y", "chosen", "ev"],
                          filters=filt)
    typed = recover_raw_positions(typed)
    opt, join_report = join_ev(typed, ev)
    if join_report["match_rate"] != 1.0 or join_report["n_group_size_mismatches"]:
        raise RuntimeError(f"options_ev join failed on confirmation half: {join_report}")

    cell_info = passes[["match_id", "event_id", "zone", "under_pressure", "game_state",
                         "team", "competition_id", "season_id", "n_visible_players"]]
    opt = opt.drop(columns=["team"]).merge(cell_info[["match_id", "event_id", "team"]],
                                            on=["match_id", "event_id"])
    return opt, passes, join_report


def build_available_types_table_with_mean(opt: pd.DataFrame, cell_info: pd.DataFrame) -> pd.DataFrame:
    """Same as task05's build_available_types_table but also carries the
    MEAN ev per (pass, type) -- needed for sensitivity check 3.6a."""
    avail = build_available_types_table(opt, cell_info)
    means = opt.groupby(["match_id", "event_id", "option_type"])["ev"].mean().rename("ev_mean").reset_index()
    avail = avail.merge(means, on=["match_id", "event_id", "option_type"], how="left")
    j_means = avail[avail["option_type"] == avail["j"]][["match_id", "event_id", "ev_mean"]] \
        .rename(columns={"ev_mean": "ev_mean_j"})
    avail = avail.merge(j_means, on=["match_id", "event_id"], how="left")
    return avail


def bootstrap_g_stats(sub: pd.DataFrame, match_universe: list, seed: int = BOOTSTRAP_SEED,
                       n_boot: int = N_BOOTSTRAP) -> dict:
    n = len(match_universe)
    match_pos = {m: i for i, m in enumerate(match_universe)}
    rng = np.random.default_rng(seed)
    idx_matrix = rng.integers(0, n, size=(n_boot, n))

    n_passes = len(sub)
    if n_passes == 0:
        return {"G": None, "ci_low": None, "ci_high": None, "P": None, "L": None,
                "n_passes": 0, "n_matches": 0, "p_value": None}
    G = float(sub["g"].mean())
    P = float((sub["g"] > 0).mean())
    n_team_matches = sub[["team", "match_id"]].drop_duplicates().shape[0]
    n_matches_contrib = sub["match_id"].nunique()
    L = G * (n_passes / n_team_matches) * STANDARD_SEASON_MATCHES if n_team_matches else None

    per_match = sub.groupby("match_id")["g"].agg(["sum", "count"])
    sums = np.zeros(n)
    counts = np.zeros(n)
    for mid, r in per_match.iterrows():
        if mid in match_pos:
            sums[match_pos[mid]] = r["sum"]
            counts[match_pos[mid]] = r["count"]
    boot_sums = sums[idx_matrix].sum(axis=1)
    boot_counts = counts[idx_matrix].sum(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        boot_G = np.where(boot_counts > 0, boot_sums / boot_counts, np.nan)
    ci_low, ci_high = np.nanpercentile(boot_G, [2.5, 97.5])
    n_le_zero = int(np.nansum(boot_G <= 0))
    p_value = (1 + n_le_zero) / (n_boot + 1)
    return {"G": G, "ci_low": float(ci_low), "ci_high": float(ci_high), "P": P, "L": L,
            "n_passes": n_passes, "n_matches": int(n_matches_contrib), "p_value": p_value}


def s_for_pair(avail: pd.DataFrame, z, p, gs, k) -> float:
    cell = avail[(avail["zone"] == z) & (avail["under_pressure"] == p) & (avail["game_state"] == gs)]
    k_rows = cell[cell["option_type"] == k]
    if len(k_rows) == 0:
        return None
    return float((k_rows["j"] == k).mean())


def cand_mask(df: pd.DataFrame, cand: dict) -> pd.Series:
    return ((df["zone"] == cand["zone"]) & (df["under_pressure"] == cand["under_pressure"])
             & (df["game_state"] == cand["game_state"]) & (df["option_type"] == cand["option_type"]))


def step1_confirmation_stats(g_table, avail, candidates, confirmation_ids) -> pd.DataFrame:
    rows = []
    for cand in candidates:
        sub = g_table[cand_mask(g_table, cand)]
        stats = bootstrap_g_stats(sub, confirmation_ids)
        stats.update({"zone": cand["zone"], "under_pressure": cand["under_pressure"],
                       "game_state": cand["game_state"], "option_type": cand["option_type"],
                       "s": s_for_pair(avail, cand["zone"], cand["under_pressure"],
                                       cand["game_state"], cand["option_type"]),
                       "discovery_G": cand["discovery_G"]})
        rows.append(stats)
    df = pd.DataFrame(rows)
    reject, p_adj, _, _ = multipletests(df["p_value"].values, alpha=0.05, method="fdr_bh")
    df["bh_significant"] = reject
    df["p_adj"] = p_adj
    df["confirmed"] = df["bh_significant"] & (df["P"] > 0.5) & (df["L"] >= 0.5)
    cols = ["zone", "under_pressure", "game_state", "option_type", "discovery_G", "G", "ci_low",
            "ci_high", "p_value", "p_adj", "bh_significant", "P", "s", "L", "n_passes", "n_matches",
            "confirmed"]
    return df[cols]


def compute_confirmation_execution(confirmation_ids, opt, cell_info) -> pd.DataFrame:
    pv_model = xgb.XGBClassifier()
    pv_model.load_model(PV_MODEL_PATH)
    ev_full = pd.read_parquet(EV_PATH, columns=["match_id", "event_id", "chosen", "ev",
                                                 "p_success", "pass_complete"],
                               filters=[("match_id", "in", confirmation_ids)])
    chosen = ev_full[ev_full["chosen"]].copy()
    chosen_type = opt.loc[opt["chosen"], ["match_id", "event_id", "option_type"]] \
        .rename(columns={"option_type": "chosen_type"})
    chosen = chosen.merge(chosen_type, on=["match_id", "event_id"])

    realized_frames = [compute_realized_values(mid, pv_model) for mid in confirmation_ids]
    realized = pd.concat(realized_frames, ignore_index=True)
    df = chosen.merge(realized, on="event_id", how="left")
    df["execution"] = df["realized_value"] - df["ev"]
    df = df.merge(cell_info, on=["match_id", "event_id"])
    return df


def bootstrap_delta(k_df, ref_df, match_universe, seed=BOOTSTRAP_SEED, n_boot=N_BOOTSTRAP):
    n = len(match_universe)
    match_pos = {m: i for i, m in enumerate(match_universe)}
    rng = np.random.default_rng(seed)
    idx_matrix = rng.integers(0, n, size=(n_boot, n))

    def per_match(df):
        pm = df.groupby("match_id")["execution"].agg(["sum", "count"])
        sums = np.zeros(n)
        counts = np.zeros(n)
        for mid, r in pm.iterrows():
            if mid in match_pos:
                sums[match_pos[mid]] = r["sum"]
                counts[match_pos[mid]] = r["count"]
        return sums, counts

    sk, ck = per_match(k_df)
    sr, cr = per_match(ref_df)
    bk_num = sk[idx_matrix].sum(axis=1)
    bk_den = ck[idx_matrix].sum(axis=1)
    br_num = sr[idx_matrix].sum(axis=1)
    br_den = cr[idx_matrix].sum(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        bk = np.where(bk_den > 0, bk_num / bk_den, np.nan)
        br = np.where(br_den > 0, br_num / br_den, np.nan)
    delta_boot = br - bk
    return np.nanpercentile(delta_boot, [2.5, 97.5])


def gate_d(exec_df, step1_df, candidates, confirmation_ids) -> pd.DataFrame:
    rows = []
    for cand in candidates:
        z, p, gs, k = cand["zone"], cand["under_pressure"], cand["game_state"], cand["option_type"]
        cell_df = exec_df[(exec_df["zone"] == z) & (exec_df["under_pressure"] == p)
                           & (exec_df["game_state"] == gs)]
        k_df = cell_df[cell_df["chosen_type"] == k]
        ref_df = cell_df[cell_df["chosen_type"] != k]
        bias_k = float(k_df["execution"].mean())
        bias_ref = float(ref_df["execution"].mean())
        delta = bias_ref - bias_k
        ci_low, ci_high = bootstrap_delta(k_df, ref_df, confirmation_ids)

        comp_bias_k = float((k_df["pass_complete"].astype(float) - k_df["p_success"]).mean())
        comp_bias_ref = float((ref_df["pass_complete"].astype(float) - ref_df["p_success"]).mean())
        comp_relative_pp = (comp_bias_ref - comp_bias_k) * 100

        row_g = step1_df[cand_mask(step1_df, cand)].iloc[0]
        confirmation_G = row_g["G"]
        confirmed = bool(row_g["confirmed"])
        gate_d_pass = bool(ci_high < confirmation_G) if confirmation_G is not None else None

        rows.append({
            "zone": z, "under_pressure": p, "game_state": gs, "option_type": k,
            "confirmed_step1": confirmed, "confirmation_G": confirmation_G,
            "bias_k": bias_k, "bias_ref": bias_ref, "delta": delta,
            "delta_ci_low": float(ci_low), "delta_ci_high": float(ci_high),
            "gate_d_pass": gate_d_pass,
            "completion_calibration_relative_pp": comp_relative_pp,
            "n_k": len(k_df), "n_ref": len(ref_df),
        })
    return pd.DataFrame(rows)


def pooled_diagnostic(exec_df, confirmation_ids) -> pd.DataFrame:
    rows = []
    for k in ALL_OPTION_TYPES:
        k_df = exec_df[exec_df["chosen_type"] == k]
        ref_df = exec_df[exec_df["chosen_type"] != k]
        if len(k_df) == 0:
            rows.append({"option_type": k, "bias_k": None, "bias_ref": None, "delta": None,
                         "ci_low": None, "ci_high": None, "n_k": 0, "n_ref": len(ref_df)})
            continue
        bias_k = float(k_df["execution"].mean())
        bias_ref = float(ref_df["execution"].mean())
        delta = bias_ref - bias_k
        ci_low, ci_high = bootstrap_delta(k_df, ref_df, confirmation_ids)
        rows.append({"option_type": k, "bias_k": bias_k, "bias_ref": bias_ref, "delta": delta,
                     "ci_low": float(ci_low), "ci_high": float(ci_high),
                     "n_k": len(k_df), "n_ref": len(ref_df)})
    return pd.DataFrame(rows)


def sensitivity_checks(g_table, avail, confirmed_candidates, confirmation_ids, match_to_comp) -> dict:
    out = {}
    for cand in confirmed_candidates:
        key = f"{cand['zone']}|{'yes' if cand['under_pressure'] else 'no'}|{cand['game_state']}|{cand['option_type']}"
        sub = g_table[cand_mask(g_table, cand)]

        # a. mean EV instead of max
        avail_sub = avail[cand_mask(avail, cand)]
        g_mean = float((avail_sub["ev_mean"] - avail_sub["ev_mean_j"]).mean()) if len(avail_sub) else None
        avg_n_k = float(avail_sub["n_options"].mean()) if len(avail_sub) else None
        avg_n_j = float(avail_sub["n_options_j"].mean()) if len(avail_sub) else None
        check_a = {"G_mean_ev": g_mean, "avg_n_options_k": avg_n_k, "avg_n_options_j": avg_n_j}

        # b. high-visibility only (>=18 visible players)
        hv_sub = sub[sub["n_visible_players"] >= HIGH_VISIBILITY_MIN]
        check_b = bootstrap_g_stats(hv_sub, confirmation_ids)

        # c. per competition-season, sign/G/n where n_passes >= 100
        check_c = []
        for (comp_id, season_id), g in sub.groupby(["competition_id", "season_id"]):
            n = len(g)
            if n >= COMP_SEASON_MIN_PASSES:
                g_val = float(g["g"].mean())
                check_c.append({"competition_id": int(comp_id), "season_id": int(season_id),
                                 "G": g_val, "sign": "+" if g_val > 0 else ("-" if g_val < 0 else "0"),
                                 "n_passes": n})

        # d. tournaments only
        tourn_mask = [(c, s) in INTL_COMPETITIONS for c, s in zip(sub["competition_id"], sub["season_id"])]
        tourn_sub = sub[tourn_mask]
        tournament_match_ids = sorted(m for m, cs in match_to_comp.items() if cs in INTL_COMPETITIONS)
        check_d = bootstrap_g_stats(tourn_sub, tournament_match_ids)

        out[key] = {"a_mean_ev": check_a, "b_high_visibility": check_b,
                    "c_per_competition_season": check_c, "d_tournaments_only": check_d}
    return out


def main():
    confirmation_ids = confirmation_match_ids()
    print(f"Confirmation matches: {len(confirmation_ids)}")
    candidates = parse_candidates()
    print(f"Candidates (fixed, from Task 05): {len(candidates)}")

    print("Loading confirmation-only data and joining EV ...")
    opt, passes, join_report = load_and_prepare(confirmation_ids)
    print(json.dumps(join_report, indent=2))

    cell_info = passes[["match_id", "event_id", "zone", "under_pressure", "game_state",
                         "team", "competition_id", "season_id", "n_visible_players"]]
    match_to_comp = {int(m): (int(c), int(s)) for m, c, s in
                      passes[["match_id", "competition_id", "season_id"]].drop_duplicates().itertuples(index=False)}
    avail = build_available_types_table_with_mean(opt, cell_info)
    g_table = avail[avail["option_type"] != avail["j"]].copy()
    g_table["g"] = g_table["ev_star"] - g_table["ev_star_j"]

    print("Step 1: confirmation statistics for the 10 candidates ...")
    step1_df = step1_confirmation_stats(g_table, avail, candidates, confirmation_ids)
    step1_df.to_parquet(STEP1_OUT)
    print(step1_df[["zone", "under_pressure", "game_state", "option_type", "G", "p_value",
                     "p_adj", "confirmed"]].to_string())
    n_confirmed = int(step1_df["confirmed"].sum())
    print(f"CONFIRMED: {n_confirmed} / {len(candidates)}")

    print("Step 2: Gate D (Amendment v2-2) for all 10 candidates ...")
    exec_df = compute_confirmation_execution(confirmation_ids, opt, cell_info)
    gate_d_df = gate_d(exec_df, step1_df, candidates, confirmation_ids)
    gate_d_df.to_parquet(GATE_D_OUT)
    print(gate_d_df[["zone", "under_pressure", "game_state", "option_type", "confirmed_step1",
                      "delta", "gate_d_pass"]].to_string())

    print("Step 3: pooled type-level diagnostic (descriptive) ...")
    pooled_df = pooled_diagnostic(exec_df, confirmation_ids)
    pooled_df.to_parquet(POOLED_OUT)
    print(pooled_df.to_string())

    confirmed_candidates = [c for c, row in zip(candidates, step1_df.to_dict("records")) if row["confirmed"]]
    print(f"Step 4: sensitivity checks for {len(confirmed_candidates)} CONFIRMED candidate(s) ...")
    sensitivity = sensitivity_checks(g_table, avail, confirmed_candidates, confirmation_ids, match_to_comp)
    SENSITIVITY_OUT.write_text(json.dumps(sensitivity, indent=2, default=str))
    print(json.dumps(sensitivity, indent=2, default=str))

    summary = {
        "status": "COMPLETE",
        "n_confirmation_matches": len(confirmation_ids),
        "n_candidates": len(candidates),
        "join_report": join_report,
        "n_confirmed": n_confirmed,
        "confirmed_candidates": [
            {k: r[k] for k in ("zone", "under_pressure", "game_state", "option_type")}
            for r in step1_df.to_dict("records") if r["confirmed"]
        ],
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
    print(f"Wrote summary to {SUMMARY_PATH}")


if __name__ == "__main__":
    main()
