"""
Task 10 — PART A: Study B interval method, selected by simulated
coverage (Amendment v2-6.1). Task 08's cluster-bootstrap-with-fresh-ids
interval and Task 08's own predecessor were both shown invalid (the 95%
CI didn't contain the point estimate) -- this replaces the method by
testing which of three candidates actually achieves ~95% coverage on
simulated data with the REAL design, rather than by preference.

Run: python src/decision_engine/task10_partA_interval.py
"""
import json
import time
import warnings

import numpy as np
import pandas as pd

from reml_crossed import bootstrap_by_player, fit_reml, profile_likelihood_ci_S, simulate_units
from task04_situation_context import DATA_DIR
from task08_studyb_corrections import build_movers

warnings.filterwarnings("ignore")

UNITS_PATH = DATA_DIR / "processed" / "study_b_units.parquet"
SUMMARY_PATH = DATA_DIR / "task10_partA_interval.json"

X_COLS = ["share_defensive", "share_final", "share_pressure"]
TRUE_VAR_PLAYER = 4.9024e-7
TRUE_VAR_TEAM = 2.5967e-7
TRUE_S = TRUE_VAR_PLAYER / (TRUE_VAR_PLAYER + TRUE_VAR_TEAM)
N_SIM_TARGET = 100
N_SIM_MIN_FALLBACK = 50
B_BOOTSTRAP = 200
SEED = 20260920
TIME_BUDGET_SECONDS = 2 * 3600
CHECKPOINT_AT = 25


def method_i_cluster_bootstrap(units: pd.DataFrame, seed: int) -> tuple:
    s_boot = bootstrap_by_player(units, X_COLS, B_BOOTSTRAP, seed)
    return float(np.percentile(s_boot, 2.5)), float(np.percentile(s_boot, 97.5))


def method_ii_parametric_bootstrap(units: pd.DataFrame, fit: dict, seed: int) -> tuple:
    s_boot = np.empty(B_BOOTSTRAP)
    for b in range(B_BOOTSTRAP):
        sim = simulate_units(units, fit["var_player"], fit["var_team"], seed=seed + b)
        s_boot[b] = fit_reml(sim, x_cols=X_COLS)["S"]
    return float(np.percentile(s_boot, 2.5)), float(np.percentile(s_boot, 97.5))


def method_iii_profile_likelihood(units: pd.DataFrame) -> tuple:
    pl = profile_likelihood_ci_S(units, x_cols=X_COLS)
    return pl["ci_low"], pl["ci_high"]


def build_all_three_intervals(units: pd.DataFrame, seed: int) -> dict:
    fit = fit_reml(units, x_cols=X_COLS)
    ci_i = method_i_cluster_bootstrap(units, seed)
    ci_ii = method_ii_parametric_bootstrap(units, fit, seed + 100000)
    ci_iii = method_iii_profile_likelihood(units)
    return {"fit": fit, "i": ci_i, "ii": ci_ii, "iii": ci_iii}


def coverage_test(units: pd.DataFrame) -> dict:
    print(f"Running coverage test: target {N_SIM_TARGET} simulations at true var_player={TRUE_VAR_PLAYER}, "
          f"var_team={TRUE_VAR_TEAM}, true S={TRUE_S:.6f} ...")
    contains = {"i": [], "ii": [], "iii": []}
    widths = {"i": [], "ii": [], "iii": []}
    t_start = time.time()
    n_target = N_SIM_TARGET
    for sim_idx in range(n_target):
        t0 = time.time()
        sim_units = simulate_units(units, TRUE_VAR_PLAYER, TRUE_VAR_TEAM, seed=SEED + sim_idx)
        result = build_all_three_intervals(sim_units, seed=SEED + 1000 * (sim_idx + 1))
        for m in ("i", "ii", "iii"):
            lo, hi = result[m]
            contains[m].append(lo <= TRUE_S <= hi)
            widths[m].append(hi - lo)
        elapsed = time.time() - t_start
        if (sim_idx + 1) % 5 == 0:
            print(f"  sim {sim_idx + 1}/{n_target}: {time.time() - t0:.1f}s this sim, {elapsed:.0f}s total")
        if (sim_idx + 1) == CHECKPOINT_AT:
            projected = elapsed / (sim_idx + 1) * N_SIM_TARGET
            print(f"  Checkpoint at {sim_idx + 1} sims: elapsed {elapsed:.0f}s, "
                  f"projected total for {N_SIM_TARGET} sims: {projected:.0f}s ({projected / 3600:.2f}h)")
            if projected > TIME_BUDGET_SECONDS:
                n_target = N_SIM_MIN_FALLBACK
                print(f"  Projected runtime exceeds the 2-hour budget -- cutting to "
                      f"{N_SIM_MIN_FALLBACK} simulations total, per the brief's contingency. Disclosed here.")

    n_completed = len(contains["i"])
    report = {"n_simulations": n_completed, "cut_to_fallback": n_completed < N_SIM_TARGET,
              "true_var_player": TRUE_VAR_PLAYER, "true_var_team": TRUE_VAR_TEAM, "true_S": TRUE_S}
    for m in ("i", "ii", "iii"):
        report[m] = {"coverage": float(np.mean(contains[m])), "mean_width": float(np.mean(widths[m]))}
    return report


def select_primary(coverage_report: dict) -> str:
    candidates = {m: coverage_report[m]["coverage"] for m in ("i", "ii", "iii") if coverage_report[m]["coverage"] >= 0.90}
    if not candidates:
        return None
    return min(candidates, key=lambda m: abs(candidates[m] - 0.95))


def apply_tier_rules(primary_ci_b4: tuple, phb1_ci: tuple, phb2: dict, phb3_ci: tuple) -> dict:
    tier1 = (primary_ci_b4[0] > 0.5) and (phb1_ci[0] > 0.5)
    if phb2.get("unmeasurable") or phb2.get("r_true_ci") is None:
        phb2_ok = False
    else:
        phb2_ok = (phb2["r_true"] > 0) and (phb2["r_true_ci"][0] > 0)
    tier2 = tier1 and phb2_ok and (phb3_ci[0] > 0.5)
    return {"tier1_allowed": bool(tier1), "tier2_allowed": bool(tier2),
            "tier1_conditions": {"b4_ci_low_gt_0.5": primary_ci_b4[0] > 0.5, "phb1_ci_low_gt_0.5": phb1_ci[0] > 0.5},
            "tier2_conditions": {"tier1": bool(tier1), "phb2_positive_excl_zero": bool(phb2_ok),
                                  "phb3_ci_low_gt_0.5": phb3_ci[0] > 0.5}}


def main():
    units = pd.read_parquet(UNITS_PATH)
    print(f"Loaded {len(units)} stage-1 units.")

    coverage_report = coverage_test(units)
    print(json.dumps(coverage_report, indent=2))

    primary = select_primary(coverage_report)
    print(f"\nPRIMARY method: {primary if primary else 'NONE -- Study B reports point estimate only, descriptive'}")

    print("\nBuilding all three intervals on the REAL data (study_b_units.parquet, primary fit) ...")
    real_result = build_all_three_intervals(units, seed=SEED)
    print(json.dumps({"fit": real_result["fit"], "i": real_result["i"], "ii": real_result["ii"],
                       "iii": real_result["iii"]}, indent=2, default=str))

    # PH-B1/PH-B2/PH-B3 on the real data, with the PRIMARY interval method
    # (reusing Task 08's exact ph_b1/ph_b2/ph_b3 machinery/logic, but
    # swapping in whichever bootstrap/interval approach is primary for
    # the CI construction on B4/PH-B1/PH-B3; PH-B2's own CI construction,
    # a simple correlation bootstrap, is untouched -- v2-6.1 only
    # concerns Study B's crossed-random-effects S interval, not PH-B2's
    # unrelated mover-correlation bootstrap).
    movers, mover_position_match = build_movers(units)
    print(f"\nMovers: {len(movers)}, position-matched: {sum(mover_position_match.values())}")

    if primary is None:
        summary = {
            "status": "COMPLETE", "coverage_report": coverage_report, "primary_method": None,
            "real_data_all_methods": {k: real_result[k] for k in ("i", "ii", "iii")},
            "real_data_fit": real_result["fit"],
            "note": "No method reached >=0.90 coverage; Study B reports the point estimate only, descriptive.",
        }
        SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
        print(f"\nWrote summary to {SUMMARY_PATH}")
        return

    x_cols_phb1 = X_COLS + ["is_Defender", "is_Forward"]

    def interval_by_method_xcols(u, method, seed, x_cols):
        if method == "i":
            s_boot = bootstrap_by_player(u, x_cols, B_BOOTSTRAP, seed)
            return float(np.percentile(s_boot, 2.5)), float(np.percentile(s_boot, 97.5))
        if method == "ii":
            fit = fit_reml(u, x_cols=x_cols)
            s_boot = np.empty(B_BOOTSTRAP)
            for b in range(B_BOOTSTRAP):
                sim = simulate_units(u, fit["var_player"], fit["var_team"], seed=seed + 100000 + b)
                s_boot[b] = fit_reml(sim, x_cols=x_cols)["S"]
            return float(np.percentile(s_boot, 2.5)), float(np.percentile(s_boot, 97.5))
        pl = profile_likelihood_ci_S(u, x_cols=x_cols)
        return pl["ci_low"], pl["ci_high"]

    u_phb1 = units.copy()
    for g in ["Defender", "Forward"]:
        u_phb1[f"is_{g}"] = (u_phb1["position_group"] == g).astype(float)
    phb1_ci = interval_by_method_xcols(u_phb1, primary, SEED + 2, x_cols_phb1)
    phb1_fit = fit_reml(u_phb1, x_cols=x_cols_phb1)
    print(f"PH-B1 ({primary}): fit S={phb1_fit['S']:.4f}, CI={phb1_ci}")

    counts = units.groupby("player_id").size()
    multi_players = counts[counts >= 2].index
    u_phb3 = units[units["player_id"].isin(multi_players)].copy()
    phb3_ci = interval_by_method_xcols(u_phb3, primary, SEED + 3, X_COLS)
    phb3_fit = fit_reml(u_phb3, x_cols=X_COLS)
    print(f"PH-B3 ({primary}): fit S={phb3_fit['S']:.4f}, CI={phb3_ci}, n_units={len(u_phb3)}")

    # PH-B2: reuse Task 08's exact disattenuated-correlation computation
    # (unaffected by v2-6.1 -- that amendment concerns only S's interval).
    from task08_studyb_corrections import build_pass_level_decision, build_side_pass_arrays, \
        split_half_reliability, weighted_side_means, N_SPLITS_PH_B2, N_SPLITS_PH_B2_BOOT, N_BOOTSTRAP as N_BOOT_PHB2
    per_pass = build_pass_level_decision()
    club_passes, intl_passes = build_side_pass_arrays(per_pass, movers)
    pids_sorted = sorted(movers.keys())
    rel_club = split_half_reliability([club_passes[p] for p in pids_sorted], N_SPLITS_PH_B2, SEED)
    rel_intl = split_half_reliability([intl_passes[p] for p in pids_sorted], N_SPLITS_PH_B2, SEED + 1)
    mover_df = weighted_side_means(units, movers).set_index("player_id")
    r_obs = float(mover_df.loc[pids_sorted, "club_mean"].corr(mover_df.loc[pids_sorted, "intl_mean"]))
    phb2 = {"rel_club": rel_club, "rel_intl": rel_intl, "r_obs": r_obs}
    if rel_club < 0.10 or rel_intl < 0.10:
        phb2["unmeasurable"] = True
        phb2["r_true"] = None
        phb2["r_true_ci"] = None
    else:
        phb2["unmeasurable"] = False
        r_true_raw = r_obs / np.sqrt(rel_club * rel_intl)
        phb2["r_true"] = float(np.clip(r_true_raw, -1.0, 1.0))
        rng = np.random.default_rng(SEED)
        pids_arr = np.array(pids_sorted)
        n_movers = len(pids_arr)
        r_true_boot = np.empty(N_BOOT_PHB2)
        for b in range(N_BOOT_PHB2):
            drawn = rng.choice(pids_arr, size=n_movers, replace=True)
            club_means_b = mover_df.loc[drawn, "club_mean"].values
            intl_means_b = mover_df.loc[drawn, "intl_mean"].values
            r_obs_b = np.corrcoef(club_means_b, intl_means_b)[0, 1]
            rel_club_b = split_half_reliability([club_passes[p] for p in drawn], N_SPLITS_PH_B2_BOOT, SEED + 1000 + b)
            rel_intl_b = split_half_reliability([intl_passes[p] for p in drawn], N_SPLITS_PH_B2_BOOT, SEED + 2000 + b)
            denom = np.sqrt(max(rel_club_b, 1e-8) * max(rel_intl_b, 1e-8))
            r_true_boot[b] = np.clip(r_obs_b / denom, -1.0, 1.0)
        phb2["r_true_ci"] = (float(np.percentile(r_true_boot, 2.5)), float(np.percentile(r_true_boot, 97.5)))
    print(f"PH-B2: {json.dumps(phb2, indent=2, default=str)}")

    print(f"\nApplying v2-5.4 tier rules using the PRIMARY interval method ({primary}) ...")
    tiers = apply_tier_rules(real_result[primary], phb1_ci, phb2, phb3_ci)
    print(json.dumps(tiers, indent=2))

    summary = {
        "status": "COMPLETE", "coverage_report": coverage_report, "primary_method": primary,
        "real_data_all_methods": {k: real_result[k] for k in ("i", "ii", "iii")},
        "real_data_fit": real_result["fit"],
        "phb1": {"fit": phb1_fit, "ci": phb1_ci}, "phb2": phb2, "phb3": {"fit": phb3_fit, "ci": phb3_ci},
        "tier_rules": tiers,
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
    print(f"\nWrote summary to {SUMMARY_PATH}")


if __name__ == "__main__":
    main()
