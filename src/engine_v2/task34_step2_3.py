"""
Task 34, Steps 2-3: tests of reception quality (RQ_rel) and the deep-
midfield table. docs/specs/task-34-reception-quality.md.

Reuses unchanged: task32_step4.assign_roles (role rule),
step8_regate.reliability_sweep (R1), task26_step6_study_b.split_half_reliability
+ the PH-B2 disattenuation/bootstrap recipe (R2, sides = a player's two
largest team-contexts with >= 50 receptions -- the brief does not say which
two; disclosed), task32_step5.leave_one_match_out/standardize_and_join/fit_both
+ outcome_validation unit builders (R3, over receptions, column RQ as the
brief writes it), task26_step5_correlations' player-level pooling of
move_on_speed / median_time_on_ball / completion_pct (R4),
task28_step1_2.estimate_sigma2w_rho + task29_step1_2.dersimonian_laird/shrink (Step 3).

Run: python src/engine_v2/task34_step2_3.py
"""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

from step8_regate import reliability_sweep
from task32_step4 import assign_roles, ROLE_POSITIONS
from task26_step6_study_b import split_half_reliability
from task32_step5 import leave_one_match_out, standardize_and_join, fit_both
from outcome_validation import build_team_match_units, add_possession_share, add_zone_pressure_shares, add_xg
from task26_step5_correlations import (weighted_avg, MOVE_RESID_V2_PATH, TIME_ON_BALL_PATH,
                                       PLAYER_SEASON_METRICS_PATH)
from task28_step1_2 import estimate_sigma2w_rho
from task29_step1_2 import dersimonian_laird, shrink, FIXED_LIST
from task27_step1_deep_midfield import name_matches

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
EVENTS_DIR = DATA_DIR / "raw" / "events"
REC_PATH = DATA_DIR / "processed" / "engine_v2" / "task34_receptions.parquet"
LEADERBOARD_V5C_PATH = DATA_DIR / "processed" / "leaderboard_v5c.parquet"
CROSSFIT_V5_PATH = DATA_DIR / "processed" / "engine_v2" / "pass_der_crossfit_v5.parquet"
EV_DIR_V1 = DATA_DIR / "processed" / "engine_v2" / "options_ev"  # same match-id source task32_step5 uses
SUMMARY_PATH = DATA_DIR / "engine_v2_task34_step2_3.json"
TABLE_PATH = DATA_DIR / "processed" / "engine_v2" / "task34_dm_shrunk.parquet"

R1_THRESHOLDS = [100, 200, 300]
R2_MIN_RECEPTIONS = 50
R2_SEED = 20260920
R2_N_BOOT = 1000
R2_N_SPLITS = 100
R2_N_SPLITS_BOOT = 20
R3_MIN_COMPLEMENT = 50
R3_COVERAGE_MIN = 0.70


def fisher_ci(r: float, n: int) -> list:
    if n < 4 or r is None or np.isnan(r):
        return [None, None]
    z, se = np.arctanh(r), 1 / np.sqrt(n - 3)
    return [float(np.tanh(z - 1.96 * se)), float(np.tanh(z + 1.96 * se))]


def r1(rec, roles, dm_ids):
    out = {}
    groups = {"deep_midfield_111": rec[rec["player_id"].isin(dm_ids)]}
    for role in list(ROLE_POSITIONS) + ["MIXED"]:
        groups[f"role_{role}"] = rec[rec["role"] == role]
    groups["all_537_with_role"] = rec[rec["role"].notna()]
    groups["all_receivers"] = rec
    for name, sub in groups.items():
        sweep = reliability_sweep(sub, "rq_rel", R1_THRESHOLDS)
        out[name] = {"n_players": int(sub["player_id"].nunique()), "n_receptions": len(sub), "sweep": sweep}
        print(f"    {name}: " + ", ".join(f"{t}: n_units={sweep[t]['n_units']} med={sweep[t]['median']}"
                                          for t in R1_THRESHOLDS))
    return out


def r2(rec, pids_filter=None):
    cnt = rec.groupby(["player_id", "team_context"]).size().rename("n").reset_index()
    cnt = cnt[cnt["n"] >= R2_MIN_RECEPTIONS]
    if pids_filter is not None:
        cnt = cnt[cnt["player_id"].isin(pids_filter)]
    side_a, side_b = {}, {}
    for pid, g in cnt.groupby("player_id"):
        if len(g) < 2:
            continue
        top = g.sort_values(["n", "team_context"], ascending=[False, True]).iloc[:2]["team_context"].tolist()
        sub = rec[rec["player_id"] == pid]
        side_a[pid] = sub.loc[sub["team_context"] == top[0], "rq_rel"].values
        side_b[pid] = sub.loc[sub["team_context"] == top[1], "rq_rel"].values
    pids = sorted(side_a)
    res = {"n_players": len(pids), "n_players_with_3plus_contexts": int((cnt.groupby("player_id").size() >= 3).sum())}
    if len(pids) < 4:
        res["note"] = "too few players"
        return res
    means = pd.DataFrame({"a": [side_a[p].mean() for p in pids], "b": [side_b[p].mean() for p in pids]}, index=pids)
    rel_a = split_half_reliability([side_a[p] for p in pids], R2_N_SPLITS, R2_SEED)
    rel_b = split_half_reliability([side_b[p] for p in pids], R2_N_SPLITS, R2_SEED + 1)
    r_obs = float(means["a"].corr(means["b"]))
    res.update({"rel_a": rel_a, "rel_b": rel_b, "r_obs": r_obs, "r_obs_fisher_95": fisher_ci(r_obs, len(pids))})
    if rel_a < 0.10 or rel_b < 0.10:
        res.update({"unmeasurable": True, "r_true": None, "r_true_ci": None})
        return res
    res["unmeasurable"] = False
    res["r_true_uncapped"] = float(r_obs / np.sqrt(rel_a * rel_b))
    res["r_true"] = float(np.clip(res["r_true_uncapped"], -1, 1))
    rng = np.random.default_rng(R2_SEED)
    arr = np.array(pids)
    boot = np.empty(R2_N_BOOT)
    for b in range(R2_N_BOOT):
        drawn = rng.choice(arr, size=len(arr), replace=True)
        r_b = np.corrcoef(means.loc[drawn, "a"], means.loc[drawn, "b"])[0, 1]
        ra = split_half_reliability([side_a[p] for p in drawn], R2_N_SPLITS_BOOT, R2_SEED + 1000 + b)
        rb = split_half_reliability([side_b[p] for p in drawn], R2_N_SPLITS_BOOT, R2_SEED + 2000 + b)
        boot[b] = np.clip(r_b / np.sqrt(max(ra, 1e-8) * max(rb, 1e-8)), -1, 1)
    res["r_true_ci"] = [float(np.nanpercentile(boot, 2.5)), float(np.nanpercentile(boot, 97.5))]
    res["n_boot_nan"] = int(np.isnan(boot).sum())
    res["share_boot_capped"] = float((np.abs(boot) >= 1).mean())
    return res


def r3(rec):
    pp = rec[["match_id", "team", "player_id", "rq"]].rename(columns={"rq": "decision"})
    vals = leave_one_match_out(pp, "player_id", R3_MIN_COMPLEMENT)
    pp = pp.merge(vals, on=["match_id", "player_id"], how="left")
    agg = pp.groupby(["match_id", "team"]).agg(n_rec=("decision", "size"), n_cov=("complement_mean", "count"),
                                                mean_decision=("complement_mean", "mean")).reset_index()
    agg["coverage"] = agg["n_cov"] / agg["n_rec"]
    kept = agg[agg["coverage"] >= R3_COVERAGE_MIN]
    print(f"    units kept (>= {R3_COVERAGE_MIN:.0%} coverage): {len(kept)}/{len(agg)}")
    units, _ = build_team_match_units()
    mids = sorted(int(p.stem) for p in EV_DIR_V1.glob("*.parquet"))
    units = add_possession_share(units, mids)
    units = add_zone_pressure_shares(units, mids)
    units = add_xg(units)
    joined = standardize_and_join(units, kept)
    results = fit_both(joined, "RQ LINEUP", {"pho2": True})
    return {"n_units_total": len(agg), "n_kept": len(kept), "n_fit": len(joined),
            "coverage_quantiles": agg["coverage"].quantile([0.1, 0.25, 0.5, 0.75]).to_dict(), "results": results}


def receptions_per_team_pass(rec, pids):
    rec_n = rec[rec["player_id"].isin(pids)].groupby("player_id").size()
    team_passes = {}
    for mid in sorted(rec["match_id"].unique()):
        ev = pd.read_parquet(EVENTS_DIR / f"{mid}.parquet", columns=["index", "player_id", "team", "type"])
        passes = ev[ev["type"] == "Pass"]
        for (pid, team), g in ev[ev["player_id"].isin(pids)].groupby(["player_id", "team"]):
            lo, hi = g["index"].min(), g["index"].max()
            n = int(((passes["team"] == team) & passes["index"].between(lo, hi)).sum())
            team_passes[pid] = team_passes.get(pid, 0) + n
    tp = pd.Series(team_passes)
    return (rec_n / tp.reindex(rec_n.index)).rename("receptions_per_team_pass")


def r4(rec, dm_ids):
    pl = rec[rec["player_id"].isin(dm_ids)].groupby("player_id")["rq_rel"].agg(["mean", "size"])
    pl.columns = ["rq_rel_mean", "n_receptions"]
    dec = pd.read_parquet(CROSSFIT_V5_PATH, columns=["player_id", "decision"])
    dec = dec[dec["player_id"].isin(dm_ids)].groupby("player_id")["decision"].mean().rename("decision_v5_crossfit")
    mv = pd.read_parquet(MOVE_RESID_V2_PATH, columns=["player_id", "residual"])
    mv = mv[mv["player_id"].isin(dm_ids)].groupby("player_id")["residual"].mean().rename("move_on_speed")
    tob = pd.read_parquet(TIME_ON_BALL_PATH, columns=["player_id", "time_on_ball", "resolved"])
    tob = tob[tob["resolved"] & tob["player_id"].isin(dm_ids)].groupby("player_id")["time_on_ball"].median() \
        .rename("median_time_on_ball")
    psm = pd.read_parquet(PLAYER_SEASON_METRICS_PATH, columns=["player_id", "n_eligible_passes", "completion_pct"])
    psm = psm[psm["player_id"].isin(dm_ids)]
    comp = psm.groupby("player_id").apply(lambda g: weighted_avg(g, "completion_pct", "n_eligible_passes")) \
        .rename("completion_pct")
    rptp = receptions_per_team_pass(rec, dm_ids)
    table = pl.join([dec, mv, tob, comp, rptp], how="left")
    out = {}
    for col in ("decision_v5_crossfit", "move_on_speed", "median_time_on_ball", "completion_pct",
                "receptions_per_team_pass"):
        sub = table.dropna(subset=["rq_rel_mean", col])
        r = float(sub["rq_rel_mean"].corr(sub[col])) if len(sub) >= 3 else None
        out[col] = {"n": len(sub), "r": r, "fisher_95": fisher_ci(r, len(sub))}
        print(f"    RQ_rel vs {col}: n={len(sub)}, r={r}")
    return out


def step3(rec, dm_meta):
    pp = rec[rec["player_id"].isin(set(dm_meta["player_id"]))][["player_id", "match_id", "rq_rel"]] \
        .rename(columns={"rq_rel": "decision_new"})
    sigma2_w, rho, anova = estimate_sigma2w_rho(pp)
    g = pp.groupby("player_id")
    stats = pd.DataFrame({"m_i": g["decision_new"].mean(), "n_i": g.size(), "G_i": g["match_id"].nunique()}).reset_index()
    stats["mean_rec_per_match"] = stats["n_i"] / stats["G_i"]
    stats["v_i"] = sigma2_w * (1 + (stats["mean_rec_per_match"] - 1) * rho) / stats["n_i"]
    stats = stats.merge(dm_meta, on="player_id", how="left")
    dl = dersimonian_laird(stats["m_i"].values, stats["v_i"].values)
    t = shrink(stats, dl["mu_w"], dl["tau2"], "m_i", "v_i").sort_values("shrunken_i", ascending=False).reset_index(drop=True)
    t["rank"] = t.index + 1
    above = t[t["ci_low_90"] > dl["mu_w"]]
    below = t[t["ci_high_90"] < dl["mu_w"]]
    fixed = []
    for name in FIXED_LIST:
        hits = t[t["player_name"].apply(lambda n: name_matches(name, n))]
        if len(hits) != 1:
            fixed.append({"name": name, "note": f"{len(hits)} matches"})
            continue
        r = hits.iloc[0]
        fixed.append({"name": name, "player_name": r["player_name"], "n_i": int(r["n_i"]), "rank": int(r["rank"]),
                      "raw": float(r["m_i"]), "shrunken": float(r["shrunken_i"]),
                      "ci_90": [float(r["ci_low_90"]), float(r["ci_high_90"])]})
    t.to_parquet(TABLE_PATH)
    print(f"    Q={dl['Q']:.2f} df={dl['df']} p={dl['p_value']:.4g} tau2={dl['tau2']:.4g}; "
          f"above={len(above)} below={len(below)}")
    return {"sigma2_w": sigma2_w, "rho": rho, "anova": anova, "dl": dl,
            "n_above": len(above), "names_above": above["player_name"].tolist(),
            "n_below": len(below), "names_below": below["player_name"].tolist(),
            "fixed_list": fixed,
            "table": t[["rank", "player_id", "player_name", "n_i", "G_i", "m_i", "shrinkage_factor",
                        "shrunken_i", "ci_low_90", "ci_high_90"]].to_dict("records")}


def main():
    print("Task 34 Steps 2-3 ...")
    rec = pd.read_parquet(REC_PATH, columns=["match_id", "team", "player_id", "team_context",
                                             "competition_id", "season_id", "rq", "rq_rel"])
    lb = pd.read_parquet(LEADERBOARD_V5C_PATH, columns=["player_id", "player_name", "is_deep_midfield"])
    dm_meta = lb.loc[lb["is_deep_midfield"], ["player_id", "player_name"]]
    dm_ids = set(dm_meta["player_id"])
    assert len(dm_ids) == 111, len(dm_ids)
    roles = assign_roles(set(lb["player_id"]))
    role_counts = roles["role"].value_counts().to_dict()
    task32 = json.loads((DATA_DIR / "engine_v2_task32_step4.json").read_text())["role_counts"]
    assert role_counts == task32, (role_counts, task32)
    rec["role"] = rec["player_id"].map(roles.set_index("player_id")["role"])
    dm_rec = rec[rec["player_id"].isin(dm_ids)]
    print(f"  {len(rec)} receptions; deep midfielders with receptions: {dm_rec['player_id'].nunique()}/111 "
          f"({len(dm_rec)} receptions)")

    print("  R1 ...")
    res_r1 = r1(rec, roles, dm_ids)
    dm200 = res_r1["deep_midfield_111"]["sweep"][200]["median"]
    r1_pass = dm200 is not None and dm200 >= 0.60
    print(f"  R1 deep midfield @200 = {dm200} -> {'PASS' if r1_pass else 'FAIL'}")

    print("  R2 (all players) ...")
    res_r2 = r2(rec)
    print(f"    {res_r2}")
    print("  R2 (deep midfielders) ...")
    res_r2_dm = r2(rec, dm_ids)
    print(f"    {res_r2_dm}")
    r2_pass = bool(res_r2.get("r_true_ci") and res_r2["r_true_ci"][0] > 0)

    print("  R3 ...")
    res_r3 = r3(rec)
    xg = res_r3["results"]["xg_H-O1"]["coefficients"]["decision_z"]
    r3_pass = xg["coef"] > 0 and xg["p_value"] < 0.05
    print(f"  R3 -> {'PASS' if r3_pass else 'FAIL'}")

    print("  R4 ...")
    res_r4 = r4(rec, dm_ids)

    print("  Step 3 ...")
    res_s3 = step3(rec, dm_meta)

    summary = {"n_receptions": len(rec), "n_dm_with_receptions": int(dm_rec["player_id"].nunique()),
               "n_dm_receptions": len(dm_rec), "role_counts": role_counts,
               "r1": res_r1, "r1_dm_at_200": dm200, "r1_pass": r1_pass,
               "r2_all": res_r2, "r2_dm": res_r2_dm, "r2_pass_all": r2_pass,
               "r3": res_r3, "r3_pass": r3_pass, "r4": res_r4, "step3": res_s3}
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
    print(f"Wrote {SUMMARY_PATH}, {TABLE_PATH}")


if __name__ == "__main__":
    main()
