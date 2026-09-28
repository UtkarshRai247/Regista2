"""
Task 26, Step 6: Study B rebuilt on engine v5 -- does decision quality
travel between team contexts? As plan v2 section 4 and Amendments v2-5,
v2-6.1 specify, ported from `task07_study_b.py`/
`task08_studyb_corrections.py`/`task10_partA_interval.py` (Study A/B's
own REML machinery, `reml_crossed.py`, and the coverage-validated
interval-selection procedure are REUSED UNCHANGED -- this task adapts
only the DATA source, not the statistics).

Coordinate routing (the brief's own explicit requirement): the original
Study B built its `zone` covariate from `passes_situation.parquet`
(withdrawn engine v1 infrastructure, built via `decision_engine`'s OLD
`pitch_direction.py`). Engine v5's own per-pass covariates come
directly from `options_ev_v4`'s chosen rows (`passer_x`, already the
corrected-coordinate value since `engine_v2.geometry.team_period_directions`
is now +1 everywhere -- no normalization step is needed at all) joined
to `pass_der_v8.parquet`'s `decision_new`. This IS the coordinate-
routing fix the brief asks for; disclosed here and in the results page,
not silently substituted.

Run: python src/engine_v2/task26_step6_study_b.py
"""
import json
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "decision_engine"))
from reml_crossed import bootstrap_by_player, fit_reml, profile_likelihood_ci_S, simulate_units  # noqa: E402
from task04_situation_context import CLUB_COMPETITIONS, INTL_COMPETITIONS, position_group  # noqa: E402

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
EVENTS_DIR = DATA_DIR / "raw" / "events"
EV_DIR = DATA_DIR / "processed" / "engine_v2" / "options_ev_v4"
PASS_DER_V8_PATH = DATA_DIR / "processed" / "engine_v2" / "pass_der_v8.parquet"
UNITS_OUT = DATA_DIR / "processed" / "engine_v2" / "study_b_units_v5.parquet"
RECOVERY_OUT = DATA_DIR / "engine_v2_task26_step6_recovery.json"
SUMMARY_PATH = DATA_DIR / "engine_v2_task26_step6_study_b.json"

STAGE1_MIN_PASSES = 20
SEED = 20260920
N_BOOTSTRAP = 1000
N_RECOVERY_SIMS = 100
ZERO_BOUNDARY_FRAC = 0.01
X_COLS = ["share_defensive", "share_final", "share_pressure"]

N_SIM_TARGET = 100
N_SIM_MIN_FALLBACK = 50
B_BOOTSTRAP = 200
TIME_BUDGET_SECONDS = 2 * 3600
CHECKPOINT_AT = 25

N_SPLITS_PH_B2 = 100
N_SPLITS_PH_B2_BOOT = 20
POSITION_DUMMY_GROUPS = ["GK", "Defender", "Forward"]


def zone_of(nx: float) -> str:
    return "defensive" if nx < 40 else ("middle" if nx < 80 else "final")


def build_position_lookup() -> dict:
    match_ids = sorted(int(p.stem) for p in EVENTS_DIR.glob("*.parquet"))
    pos_counts = {}
    for mid in match_ids:
        ev = pd.read_parquet(EVENTS_DIR / f"{mid}.parquet", columns=["player_id", "position"])
        sub = ev.dropna(subset=["player_id", "position"])
        for pid, pos in zip(sub["player_id"], sub["position"]):
            pos_counts.setdefault(pid, {}).setdefault(pos, 0)
            pos_counts[pid][pos] += 1
    return {pid: max(counts, key=counts.get) for pid, counts in pos_counts.items()}


def build_per_pass_table() -> pd.DataFrame:
    """Engine v5's per-pass covariates: team/passer_x/under_pressure from
    options_ev_v4's chosen rows (already corrected-coordinate, direction
    always +1), decision_new/competition_id/season_id from pass_der_v8."""
    match_ids = sorted(int(p.stem) for p in EV_DIR.glob("*.parquet"))
    frames = []
    for mid in match_ids:
        df = pd.read_parquet(EV_DIR / f"{mid}.parquet",
                              columns=["match_id", "event_id", "team", "player_id", "passer_x", "under_pressure", "chosen"])
        frames.append(df[df["chosen"]].drop(columns=["chosen"]))
    chosen = pd.concat(frames, ignore_index=True)
    der = pd.read_parquet(PASS_DER_V8_PATH, columns=["match_id", "event_id", "competition_id", "season_id", "decision_new"])
    per_pass = chosen.merge(der, on=["match_id", "event_id"], how="inner")
    per_pass["zone"] = per_pass["passer_x"].apply(zone_of)
    return per_pass


def build_stage1_units(per_pass: pd.DataFrame, pos_lookup: dict) -> pd.DataFrame:
    grouped = per_pass.groupby(["player_id", "team", "competition_id", "season_id"])
    units = grouped.agg(
        n_passes=("decision_new", "count"), mean_decision=("decision_new", "mean"), sd_decision=("decision_new", "std"),
        share_defensive=("zone", lambda s: (s == "defensive").mean()),
        share_middle=("zone", lambda s: (s == "middle").mean()),
        share_final=("zone", lambda s: (s == "final").mean()),
        share_pressure=("under_pressure", "mean"),
    ).reset_index()
    units = units[units["n_passes"] >= STAGE1_MIN_PASSES].copy()
    units["se"] = units["sd_decision"] / np.sqrt(units["n_passes"])
    units["position_group"] = units["player_id"].map(lambda p: position_group(pos_lookup.get(p)))
    units = units.drop(columns=["sd_decision"])
    return units


def gate_e(units: pd.DataFrame) -> tuple:
    per_player = units.groupby("player_id")
    n_players_2plus = int((per_player.size() >= 2).sum())
    movers, mover_position_match = {}, {}
    for pid, g in per_player:
        club = g[g.apply(lambda r: (r["competition_id"], r["season_id"]) in CLUB_COMPETITIONS, axis=1)]
        intl = g[g.apply(lambda r: (r["competition_id"], r["season_id"]) in INTL_COMPETITIONS, axis=1)]
        if len(club) and len(intl):
            movers[pid] = {"club": club, "intl": intl}
            club_groups = set(club["position_group"].dropna())
            intl_groups = set(intl["position_group"].dropna())
            mover_position_match[pid] = bool(club_groups & intl_groups)
    n_movers_same_group = sum(mover_position_match.values())
    report = {"n_units": len(units), "n_players": units["player_id"].nunique(),
              "n_team_contexts": units.groupby(["team", "competition_id", "season_id"]).ngroups,
              "n_players_2plus_units": n_players_2plus, "n_club_intl_movers": len(movers),
              "n_movers_same_position_group": n_movers_same_group}
    return report, movers, mover_position_match


def _scenario_pass(kind, var_p_hat, var_t_hat, s_hat, true_var_p, true_var_t):
    if kind == "a":
        ok_p = abs(np.mean(var_p_hat) - true_var_p) <= 0.10 * true_var_p
        ok_t = abs(np.mean(var_t_hat) - true_var_t) <= 0.10 * true_var_t
        ok_s = float(np.mean(np.abs(s_hat - 0.5))) < 0.05
        return bool(ok_p and ok_t and ok_s), {"ok_var_player": bool(ok_p), "ok_var_team": bool(ok_t), "ok_S": bool(ok_s)}
    if kind == "b":
        ok_zero = float(np.mean(var_t_hat)) < 0.05 * float(np.mean(var_p_hat))
        ok_s = abs(float(np.mean(s_hat)) - 1.0) < 0.05
        return bool(ok_zero and ok_s), {"ok_zero_var_team": bool(ok_zero), "ok_S": bool(ok_s)}
    ok_zero = float(np.mean(var_p_hat)) < 0.05 * float(np.mean(var_t_hat))
    ok_s = abs(float(np.mean(s_hat)) - 0.0) < 0.05
    return bool(ok_zero and ok_s), {"ok_zero_var_player": bool(ok_zero), "ok_S": bool(ok_s)}


def recovery_test(units: pd.DataFrame) -> dict:
    observed_var = float(np.var(units["mean_decision"].values, ddof=1))
    magnitude = observed_var / 3.0
    scenarios = {"a": (magnitude, magnitude), "b": (magnitude, 0.0), "c": (0.0, magnitude)}
    scenario_seed_offset = {"a": 0, "b": 1000, "c": 2000}
    results = {}
    all_pass = True
    for kind, (true_vp, true_vt) in scenarios.items():
        var_p_hats, var_t_hats, s_hats = [], [], []
        for i in range(N_RECOVERY_SIMS):
            sim = simulate_units(units, true_vp, true_vt, seed=SEED + scenario_seed_offset[kind] + i)
            fit = fit_reml(sim, x_cols=X_COLS)
            var_p_hats.append(fit["var_player"]); var_t_hats.append(fit["var_team"]); s_hats.append(fit["S"])
        var_p_hats, var_t_hats, s_hats = np.array(var_p_hats), np.array(var_t_hats), np.array(s_hats)
        passed, detail = _scenario_pass(kind, var_p_hats, var_t_hats, s_hats, true_vp, true_vt)
        all_pass = all_pass and passed
        results[kind] = {
            "true_var_player": true_vp, "true_var_team": true_vt,
            "mean_var_player_hat": float(np.mean(var_p_hats)), "mean_var_team_hat": float(np.mean(var_t_hats)),
            "mean_S_hat": float(np.mean(s_hats)), "n_sims": N_RECOVERY_SIMS, "passed": passed, "detail": detail,
        }
    report = {"observed_stage1_variance": observed_var, "magnitude_used": magnitude,
              "scenarios": results, "all_passed": all_pass}
    RECOVERY_OUT.write_text(json.dumps(report, indent=2, default=str))
    return report


def method_i_cluster_bootstrap(units, x_cols, seed):
    s_boot = bootstrap_by_player(units, x_cols, B_BOOTSTRAP, seed)
    return float(np.percentile(s_boot, 2.5)), float(np.percentile(s_boot, 97.5))


def method_ii_parametric_bootstrap(units, fit, x_cols, seed):
    s_boot = np.empty(B_BOOTSTRAP)
    for b in range(B_BOOTSTRAP):
        sim = simulate_units(units, fit["var_player"], fit["var_team"], seed=seed + b)
        s_boot[b] = fit_reml(sim, x_cols=x_cols)["S"]
    return float(np.percentile(s_boot, 2.5)), float(np.percentile(s_boot, 97.5))


def method_iii_profile_likelihood(units, x_cols):
    pl = profile_likelihood_ci_S(units, x_cols=x_cols)
    return pl["ci_low"], pl["ci_high"]


def build_all_three_intervals(units, x_cols, seed):
    fit = fit_reml(units, x_cols=x_cols)
    ci_i = method_i_cluster_bootstrap(units, x_cols, seed)
    ci_ii = method_ii_parametric_bootstrap(units, fit, x_cols, seed + 100000)
    ci_iii = method_iii_profile_likelihood(units, x_cols)
    return {"fit": fit, "i": ci_i, "ii": ci_ii, "iii": ci_iii}


def coverage_test(units: pd.DataFrame, fit_real: dict) -> dict:
    true_var_player, true_var_team = fit_real["var_player"], fit_real["var_team"]
    true_S = true_var_player / (true_var_player + true_var_team)
    print(f"Coverage test: target {N_SIM_TARGET} sims at true var_player={true_var_player:.6g}, "
          f"var_team={true_var_team:.6g}, true S={true_S:.6f} ...")
    contains = {"i": [], "ii": [], "iii": []}
    widths = {"i": [], "ii": [], "iii": []}
    t_start = time.time()
    n_target = N_SIM_TARGET
    sim_idx = 0
    while sim_idx < n_target:
        sim_units = simulate_units(units, true_var_player, true_var_team, seed=SEED + sim_idx)
        result = build_all_three_intervals(sim_units, X_COLS, seed=SEED + 1000 * (sim_idx + 1))
        for m in ("i", "ii", "iii"):
            lo, hi = result[m]
            contains[m].append(lo <= true_S <= hi)
            widths[m].append(hi - lo)
        sim_idx += 1
        if sim_idx % 5 == 0:
            print(f"  sim {sim_idx}/{n_target}: {time.time() - t_start:.0f}s total")
        if sim_idx == CHECKPOINT_AT:
            elapsed = time.time() - t_start
            projected = elapsed / sim_idx * N_SIM_TARGET
            print(f"  Checkpoint at {sim_idx}: elapsed {elapsed:.0f}s, projected {projected:.0f}s ({projected/3600:.2f}h)")
            if projected > TIME_BUDGET_SECONDS:
                n_target = N_SIM_MIN_FALLBACK
                print(f"  Projected runtime exceeds the 2-hour budget -- cutting to {N_SIM_MIN_FALLBACK} sims total.")

    n_completed = sim_idx
    report = {"n_simulations": n_completed, "cut_to_fallback": n_completed < N_SIM_TARGET,
              "true_var_player": true_var_player, "true_var_team": true_var_team, "true_S": true_S}
    for m in ("i", "ii", "iii"):
        report[m] = {"coverage": float(np.mean(contains[m])), "mean_width": float(np.mean(widths[m]))}
    return report


def select_primary(coverage_report: dict):
    candidates = {m: coverage_report[m]["coverage"] for m in ("i", "ii", "iii") if coverage_report[m]["coverage"] >= 0.90}
    if not candidates:
        return None
    return min(candidates, key=lambda m: abs(candidates[m] - 0.95))


def interval_by_method(u, method, x_cols, seed):
    if method == "i":
        return method_i_cluster_bootstrap(u, x_cols, seed)
    if method == "ii":
        fit = fit_reml(u, x_cols=x_cols)
        return method_ii_parametric_bootstrap(u, fit, x_cols, seed)
    return method_iii_profile_likelihood(u, x_cols)


def build_side_pass_arrays(per_pass: pd.DataFrame, movers: dict):
    per_pass = per_pass.copy()
    per_pass["ctx_key"] = (per_pass["team"].astype(str) + "|" + per_pass["competition_id"].astype(str)
                            + "|" + per_pass["season_id"].astype(str))
    mover_pids = set(movers.keys())
    per_pass_mv = per_pass[per_pass["player_id"].isin(mover_pids)]
    club_passes, intl_passes = {}, {}
    for pid, v in movers.items():
        club_keys = set(v["club"]["team"].astype(str) + "|" + v["club"]["competition_id"].astype(str)
                         + "|" + v["club"]["season_id"].astype(str))
        intl_keys = set(v["intl"]["team"].astype(str) + "|" + v["intl"]["competition_id"].astype(str)
                         + "|" + v["intl"]["season_id"].astype(str))
        sub = per_pass_mv[per_pass_mv["player_id"] == pid]
        club_passes[pid] = sub[sub["ctx_key"].isin(club_keys)]["decision_new"].values
        intl_passes[pid] = sub[sub["ctx_key"].isin(intl_keys)]["decision_new"].values
    return club_passes, intl_passes


def split_half_reliability(arrays: list, n_splits: int, seed: int) -> float:
    rng = np.random.default_rng(seed)
    r_sb_list = []
    for _ in range(n_splits):
        h1_means, h2_means = [], []
        for arr in arrays:
            n = len(arr)
            perm = rng.permutation(n)
            half = n // 2
            h1_means.append(arr[perm[:half]].mean())
            h2_means.append(arr[perm[half:]].mean())
        r = np.corrcoef(h1_means, h2_means)[0, 1]
        r_sb_list.append(2 * r / (1 + r) if not np.isnan(r) else np.nan)
    return float(np.nanmedian(r_sb_list))


def weighted_side_means(movers: dict) -> pd.DataFrame:
    rows = []
    for pid, v in movers.items():
        club_mean = float(np.average(v["club"]["mean_decision"], weights=v["club"]["n_passes"]))
        intl_mean = float(np.average(v["intl"]["mean_decision"], weights=v["intl"]["n_passes"]))
        rows.append({"player_id": pid, "club_mean": club_mean, "intl_mean": intl_mean})
    return pd.DataFrame(rows)


def ph_b2(units: pd.DataFrame, per_pass: pd.DataFrame, movers: dict) -> dict:
    club_passes, intl_passes = build_side_pass_arrays(per_pass, movers)
    mean_intl_passes = float(np.mean([len(a) for a in intl_passes.values()])) if intl_passes else 0.0
    pids_sorted = sorted(movers.keys())
    rel_club = split_half_reliability([club_passes[p] for p in pids_sorted], N_SPLITS_PH_B2, SEED)
    rel_intl = split_half_reliability([intl_passes[p] for p in pids_sorted], N_SPLITS_PH_B2, SEED + 1)
    mover_df = weighted_side_means(movers).set_index("player_id")
    r_obs = float(mover_df.loc[pids_sorted, "club_mean"].corr(mover_df.loc[pids_sorted, "intl_mean"]))
    result = {"rel_club": rel_club, "rel_intl": rel_intl, "r_obs": r_obs, "n_movers": len(movers),
              "mean_intl_passes_per_mover": mean_intl_passes}
    if rel_club < 0.10 or rel_intl < 0.10:
        result.update({"unmeasurable": True, "r_true": None, "r_true_ci": None})
        return result
    result["unmeasurable"] = False
    r_true_raw = r_obs / np.sqrt(rel_club * rel_intl)
    result["r_true"] = float(np.clip(r_true_raw, -1.0, 1.0))
    rng = np.random.default_rng(SEED)
    pids_arr = np.array(pids_sorted)
    n_movers = len(pids_arr)
    r_true_boot = np.empty(N_BOOTSTRAP)
    for b in range(N_BOOTSTRAP):
        drawn = rng.choice(pids_arr, size=n_movers, replace=True)
        club_means_b = mover_df.loc[drawn, "club_mean"].values
        intl_means_b = mover_df.loc[drawn, "intl_mean"].values
        r_obs_b = np.corrcoef(club_means_b, intl_means_b)[0, 1]
        rel_club_b = split_half_reliability([club_passes[p] for p in drawn], N_SPLITS_PH_B2_BOOT, SEED + 1000 + b)
        rel_intl_b = split_half_reliability([intl_passes[p] for p in drawn], N_SPLITS_PH_B2_BOOT, SEED + 2000 + b)
        denom = np.sqrt(max(rel_club_b, 1e-8) * max(rel_intl_b, 1e-8))
        r_true_boot[b] = np.clip(r_obs_b / denom, -1.0, 1.0)
    result["r_true_ci"] = (float(np.percentile(r_true_boot, 2.5)), float(np.percentile(r_true_boot, 97.5)))
    return result


def design_calculation(rel_club, rel_intl, mean_intl_passes) -> dict:
    z_a2 = norm.ppf(1 - 0.05 / 2)
    z_b = norm.ppf(0.80)
    power = {}
    for true_r in (0.3, 0.5):
        r_eff = true_r * np.sqrt(rel_club * rel_intl)
        n_req = ((z_a2 + z_b) / np.arctanh(r_eff)) ** 2 + 3
        power[str(true_r)] = {"r_effective": float(r_eff), "n_movers_required": float(np.ceil(n_req))}
    sb = {}
    for target in (0.5, 0.7):
        k = target * (1 - rel_intl) / (rel_intl * (1 - target))
        n_new = k * mean_intl_passes
        sb[str(target)] = {"k": float(k), "intl_passes_per_mover_required": float(np.ceil(n_new))}
    return {"power_for_true_r": power, "spearman_brown_projection": sb,
            "rel_club_used": rel_club, "rel_intl_used": rel_intl, "mean_intl_passes_per_mover_used": mean_intl_passes}


def apply_claim_rules(b4_ci, phb1_ci, phb2, phb3_ci) -> dict:
    tier1 = (b4_ci[0] > 0.5) and (phb1_ci[0] > 0.5)
    if phb2.get("unmeasurable") or phb2.get("r_true_ci") is None:
        phb2_ok = False
    else:
        phb2_ok = (phb2["r_true"] > 0) and (phb2["r_true_ci"][0] > 0)
    tier2 = tier1 and phb2_ok and (phb3_ci[0] > 0.5)
    return {"tier1_allowed": bool(tier1), "tier2_allowed": bool(tier2),
            "tier1_conditions": {"b4_ci_low_gt_0.5": b4_ci[0] > 0.5, "phb1_ci_low_gt_0.5": phb1_ci[0] > 0.5},
            "tier2_conditions": {"tier1": bool(tier1), "phb2_positive_excl_zero": bool(phb2_ok),
                                  "phb3_ci_low_gt_0.5": phb3_ci[0] > 0.5}}


def main():
    t_start = time.time()
    print("Task 26 Step 6: Study B rebuilt on engine v5 ...")
    print("  building per-pass covariates from options_ev_v4 + pass_der_v8 ...")
    per_pass = build_per_pass_table()
    print(f"  {len(per_pass)} per-pass rows")

    print("  building position lookup ...")
    pos_lookup = build_position_lookup()

    units = build_stage1_units(per_pass, pos_lookup)
    units.to_parquet(UNITS_OUT)
    print(f"  stage-1 units (>= {STAGE1_MIN_PASSES} passes): {len(units)}")

    gate_e_report, movers, mover_position_match = gate_e(units)
    print(f"  Gate E: {json.dumps(gate_e_report, indent=2)}")

    print("  parameter recovery test (100 sims x 3 scenarios) ...")
    recovery = recovery_test(units)
    print(f"  recovery all_passed={recovery['all_passed']}")

    summary = {"n_per_pass_rows": len(per_pass), "gate_e": gate_e_report, "recovery": recovery}

    if not recovery["all_passed"]:
        summary["status"] = "BLOCKED_AT_RECOVERY"
        SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
        print("STOPPING before B4: recovery test failed at least one scenario.")
        return summary

    print("  B4: primary REML fit ...")
    fit_b4 = fit_reml(units, x_cols=X_COLS)
    print(f"  {json.dumps(fit_b4, indent=2, default=str)}")

    print("  coverage test (interval-method selection, Amendment v2-6.1) ...")
    coverage_report = coverage_test(units, fit_b4)
    primary = select_primary(coverage_report)
    print(f"  coverage: {json.dumps(coverage_report, indent=2)}")
    print(f"  PRIMARY method: {primary}")

    print("  building all three intervals for B4 on the real data ...")
    real_result = build_all_three_intervals(units, X_COLS, seed=SEED)

    summary.update({
        "status": "COMPLETE", "n_units": len(units), "n_movers": len(movers),
        "n_movers_position_matched": sum(mover_position_match.values()),
        "b4_fit": fit_b4, "coverage_report": coverage_report, "primary_method": primary,
        "b4_intervals_all_methods": {k: real_result[k] for k in ("i", "ii", "iii")},
    })

    if primary is None:
        summary["note"] = "No interval method reached >=0.90 coverage; Study B reports the point estimate only, descriptive."
        SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
        print(f"\nWrote {SUMMARY_PATH}")
        return summary

    print("  PH-B1: position-group fixed effects ...")
    u_phb1 = units.copy()
    group_counts = units["position_group"].value_counts()
    dummy_groups = [g for g in POSITION_DUMMY_GROUPS if group_counts.get(g, 0) > 0]
    dropped_zero = [g for g in POSITION_DUMMY_GROUPS if group_counts.get(g, 0) == 0]
    for g in dummy_groups:
        u_phb1[f"is_{g}"] = (u_phb1["position_group"] == g).astype(float)
    x_cols_phb1 = X_COLS + [f"is_{g}" for g in dummy_groups]
    phb1_fit = fit_reml(u_phb1, x_cols=x_cols_phb1)
    phb1_ci = interval_by_method(u_phb1, primary, x_cols_phb1, SEED + 2)
    print(f"  PH-B1: fit S={phb1_fit['S']:.4f}, CI={phb1_ci}")

    print("  PH-B2: disattenuated mover correlation ...")
    phb2 = ph_b2(units, per_pass, movers)
    print(f"  PH-B2: {json.dumps(phb2, indent=2, default=str)}")

    print("  PH-B3: 2+-unit players only ...")
    counts = units.groupby("player_id").size()
    multi_players = counts[counts >= 2].index
    u_phb3 = units[units["player_id"].isin(multi_players)].copy()
    phb3_fit = fit_reml(u_phb3, x_cols=X_COLS)
    phb3_ci = interval_by_method(u_phb3, primary, X_COLS, SEED + 3)
    print(f"  PH-B3: fit S={phb3_fit['S']:.4f}, CI={phb3_ci}, n_units={len(u_phb3)}")

    tiers = apply_claim_rules(real_result[primary], phb1_ci, phb2, phb3_ci)
    print(f"  tier rules: {json.dumps(tiers, indent=2)}")

    design_calc = None
    if not tiers["tier2_allowed"]:
        design_calc = design_calculation(phb2["rel_club"], phb2["rel_intl"], phb2["mean_intl_passes_per_mover"])

    summary.update({
        "dropped_zero_count_position_groups": dropped_zero,
        "phb1": {"fit": phb1_fit, "ci": phb1_ci, "x_cols": x_cols_phb1},
        "phb2": phb2, "phb3": {"fit": phb3_fit, "ci": phb3_ci, "n_units": len(u_phb3)},
        "tier_rules": tiers, "design_calculation": design_calc,
        "wall_clock_seconds": time.time() - t_start,
    })
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
    print(f"\nWrote {SUMMARY_PATH}")
    return summary


if __name__ == "__main__":
    main()
