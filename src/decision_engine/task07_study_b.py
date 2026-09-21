"""
Task 07 — PART 2: Study B (plan section 4). Does decision quality
travel between player and team context?

Steps B1-B5 per docs/specs/task-07-study-b.md. Uses reml_crossed.py for
the hand-built sparse REML estimator (Amendment v2-3.2). Per that
amendment and the user's explicit instruction, Step B3's parameter
recovery test on the REAL design must pass all three scenarios before
Step B4 fits the real data -- if any scenario fails, this script stops
and reports BLOCKED for B4/B5 without fitting the real data.

Run: python src/decision_engine/task07_study_b.py
"""
import json
import warnings

import numpy as np
import pandas as pd

from decompose import match_competition_lookup
from reml_crossed import fit_reml, simulate_units
from task04_situation_context import CLUB_COMPETITIONS, DATA_DIR, EVENTS_DIR, INTL_COMPETITIONS, position_group

warnings.filterwarnings("ignore")

POLICY_PATH = DATA_DIR / "processed" / "options_policy.parquet"
PASSES_PATH = DATA_DIR / "processed" / "passes_situation.parquet"
METRICS_PATH = DATA_DIR / "processed" / "player_season_metrics.parquet"

UNITS_OUT = DATA_DIR / "processed" / "study_b_units.parquet"
RECOVERY_OUT = DATA_DIR / "task07_study_b_recovery.json"
SUMMARY_PATH = DATA_DIR / "task07_study_b.json"

STAGE1_MIN_PASSES = 20
SEED = 20260920
N_BOOTSTRAP = 1000
N_RECOVERY_SIMS = 100
ZERO_BOUNDARY_FRAC = 0.01
X_COLS = ["share_defensive", "share_final", "share_pressure"]


def compute_decision_per_pass(policy: pd.DataFrame) -> pd.DataFrame:
    """Decision = EV(chosen) - sum(policy_probability * EV) per pass.
    Same arithmetic as decompose.build_per_pass_table's 'decision' column
    (single source of truth for this formula); reimplemented here without
    the possession-value model dependency since Study B needs only
    Decision, not Execution/realized value."""
    policy = policy.copy()
    policy["ev_x_prob"] = policy["ev"] * policy["policy_probability"]
    grp = policy.groupby("event_id")
    per_pass = grp.agg(
        match_id=("match_id", "first"), team=("team", "first"), player_id=("player_id", "first"),
        ev_chosen=("ev", lambda s: s[policy.loc[s.index, "chosen"]].iloc[0]),
        policy_weighted_ev=("ev_x_prob", "sum"),
    ).reset_index()
    per_pass["decision"] = per_pass["ev_chosen"] - per_pass["policy_weighted_ev"]
    return per_pass


def step_b1():
    print("Step B1: per-pass Decision and reproduction check ...")
    policy = pd.read_parquet(POLICY_PATH)
    per_pass = compute_decision_per_pass(policy)
    comp_lookup = match_competition_lookup()
    per_pass["competition_id"] = per_pass["match_id"].map(lambda m: comp_lookup.get(m, (None, None))[0])
    per_pass["season_id"] = per_pass["match_id"].map(lambda m: comp_lookup.get(m, (None, None))[1])

    agg = per_pass.groupby(["player_id", "competition_id", "season_id"]).agg(
        n_eligible_passes=("decision", "count"), decision_per_100=("decision", lambda s: s.mean() * 100),
    ).reset_index()

    metrics = pd.read_parquet(METRICS_PATH)[["player_id", "competition_id", "season_id",
                                              "n_eligible_passes", "decision_per_100"]]
    check = agg.merge(metrics, on=["player_id", "competition_id", "season_id"], suffixes=("_recomputed", "_frozen"))
    n_row_mismatch = len(agg) != len(metrics) or len(check) != len(metrics)
    max_diff = float((check["decision_per_100_recomputed"] - check["decision_per_100_frozen"]).abs().max())
    n_count_mismatch = int((check["n_eligible_passes_recomputed"] != check["n_eligible_passes_frozen"]).sum())
    reproduced = (not n_row_mismatch) and max_diff < 1e-6 and n_count_mismatch == 0
    report = {"n_agg_rows": len(agg), "n_metrics_rows": len(metrics), "n_matched_rows": len(check),
              "row_count_mismatch": n_row_mismatch, "max_abs_diff_decision_per_100": max_diff,
              "n_count_mismatches": n_count_mismatch, "reproduced": reproduced}
    print(json.dumps(report, indent=2))
    if not reproduced:
        return None, None, report

    print("Building position lookup from raw events (full 299-match sample) ...")
    pos_frames = []
    for f in sorted(EVENTS_DIR.glob("*.parquet")):
        mid = int(f.stem)
        ev = pd.read_parquet(f, columns=["id", "position"])
        ev["match_id"] = mid
        pos_frames.append(ev.rename(columns={"id": "event_id"}))
    position_lookup = pd.concat(pos_frames, ignore_index=True)

    passes = pd.read_parquet(PASSES_PATH)
    base = passes.merge(per_pass[["match_id", "event_id", "decision"]], on=["match_id", "event_id"])
    base = base.merge(position_lookup, on=["match_id", "event_id"], how="left")

    grouped = base.groupby(["player_id", "team", "competition_id", "season_id"])
    units = grouped.agg(
        n_passes=("decision", "count"), mean_decision=("decision", "mean"), sd_decision=("decision", "std"),
        share_defensive=("zone", lambda s: (s == "defensive").mean()),
        share_middle=("zone", lambda s: (s == "middle").mean()),
        share_final=("zone", lambda s: (s == "final").mean()),
        share_pressure=("under_pressure", "mean"),
        position_mode=("position", lambda s: s.mode().iloc[0] if not s.mode().empty else None),
    ).reset_index()
    units = units[units["n_passes"] >= STAGE1_MIN_PASSES].copy()
    units["se"] = units["sd_decision"] / np.sqrt(units["n_passes"])
    units["position_group"] = units["position_mode"].map(position_group)
    units = units.drop(columns=["position_mode", "sd_decision"])
    print(f"Stage-1 units (>= {STAGE1_MIN_PASSES} passes): {len(units)}")
    return units, report, report


def step_b2(units: pd.DataFrame) -> dict:
    print("Step B2: Gate E counts ...")
    per_player = units.groupby("player_id")
    n_players_2plus = int((per_player.size() >= 2).sum())

    movers = {}
    for pid, g in per_player:
        club = g[g.apply(lambda r: (r["competition_id"], r["season_id"]) in CLUB_COMPETITIONS, axis=1)]
        intl = g[g.apply(lambda r: (r["competition_id"], r["season_id"]) in INTL_COMPETITIONS, axis=1)]
        if len(club) and len(intl):
            movers[pid] = {"club": club, "intl": intl}
    n_movers = len(movers)
    n_movers_same_group = 0
    mover_position_match = {}
    for pid, v in movers.items():
        club_groups = set(v["club"]["position_group"].dropna())
        intl_groups = set(v["intl"]["position_group"].dropna())
        match = bool(club_groups & intl_groups)
        mover_position_match[pid] = match
        if match:
            n_movers_same_group += 1

    report = {"n_units": len(units), "n_players": units["player_id"].nunique(),
              "n_team_contexts": units.groupby(["team", "competition_id", "season_id"]).ngroups,
              "n_players_2plus_units": n_players_2plus, "n_club_intl_movers": n_movers,
              "n_movers_same_position_group": n_movers_same_group}
    print(json.dumps(report, indent=2))
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


def step_b3(units: pd.DataFrame) -> dict:
    print("Step B3: REML parameter recovery test on the REAL design ...")
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
            "mean_S_hat": float(np.mean(s_hats)), "mean_abs_error_S": float(np.mean(np.abs(s_hats - (0.5 if kind == "a" else (1.0 if kind == "b" else 0.0))))),
            "n_sims": N_RECOVERY_SIMS, "passed": passed, "detail": detail,
        }
        print(f"  scenario {kind}: {json.dumps(results[kind], indent=2)}")
    report = {"observed_stage1_variance": observed_var, "magnitude_used": magnitude,
              "scenarios": results, "all_passed": all_pass}
    RECOVERY_OUT.write_text(json.dumps(report, indent=2, default=str))
    return report


def bootstrap_by_player(units: pd.DataFrame, n_boot: int, seed: int, x_cols: list):
    rng = np.random.default_rng(seed)
    players = units["player_id"].unique()
    P = len(players)
    groups = units.groupby("player_id").indices
    s_hats = []
    for _ in range(n_boot):
        drawn = rng.choice(players, size=P, replace=True)
        idx = np.concatenate([groups[p] for p in drawn])
        rep = units.iloc[idx]
        fit = fit_reml(rep, x_cols=x_cols)
        s_hats.append(fit["S"])
    return np.array(s_hats)


def step_b4(units: pd.DataFrame, gate_e_counts: dict) -> dict:
    print("Step B4: fitting the real 1,701-unit design ...")
    fit = fit_reml(units, x_cols=X_COLS)
    print(json.dumps(fit, indent=2))
    print("Bootstrapping S's 95% CI (1,000 draws, resampling players) ...")
    s_boot = bootstrap_by_player(units, N_BOOTSTRAP, SEED, X_COLS)
    ci_low, ci_high = float(np.percentile(s_boot, 2.5)), float(np.percentile(s_boot, 97.5))

    gate_fail_n = gate_e_counts["n_players_2plus_units"] < 100
    gate_fail_zero = fit["var_team"] < ZERO_BOUNDARY_FRAC * fit["var_player"]
    gate_fail_span = (ci_high - ci_low) > 0.6
    gate_e_pass = not (gate_fail_n or gate_fail_zero or gate_fail_span)

    report = {
        "fit": fit, "S_ci_low": ci_low, "S_ci_high": ci_high,
        "gate_e": {
            "fail_fewer_than_100_2plus_players": bool(gate_fail_n),
            "fail_var_team_at_zero_boundary": bool(gate_fail_zero),
            "zero_boundary_threshold_frac": ZERO_BOUNDARY_FRAC,
            "fail_S_interval_spans_over_0.6": bool(gate_fail_span),
            "verdict": "PASS" if gate_e_pass else "DESCRIPTIVE ONLY",
        },
    }
    print(json.dumps(report, indent=2))
    return report


def step_b5(units: pd.DataFrame, movers: dict, mover_position_match: dict) -> dict:
    print("Step B5a: refit on position-matched movers + all non-movers ...")
    mismatched_players = {pid for pid, ok in mover_position_match.items() if not ok}
    restricted = units[~units["player_id"].isin(mismatched_players)].copy()
    fit_a = fit_reml(restricted, x_cols=X_COLS)
    s_boot_a = bootstrap_by_player(restricted, N_BOOTSTRAP, SEED, X_COLS)
    ci_a = (float(np.percentile(s_boot_a, 2.5)), float(np.percentile(s_boot_a, 97.5)))
    report_a = {"n_units_excluded": len(units) - len(restricted), "fit": fit_a, "S_ci_low": ci_a[0], "S_ci_high": ci_a[1]}
    print(json.dumps(report_a, indent=2))

    print("Step B5b: club-vs-international correlation for movers ...")
    rows = []
    for pid, v in movers.items():
        club_mean = float(np.average(v["club"]["mean_decision"], weights=v["club"]["n_passes"]))
        intl_mean = float(np.average(v["intl"]["mean_decision"], weights=v["intl"]["n_passes"]))
        rows.append({"player_id": pid, "club_mean": club_mean, "intl_mean": intl_mean})
    mover_df = pd.DataFrame(rows)
    r = float(mover_df["club_mean"].corr(mover_df["intl_mean"]))
    rng = np.random.default_rng(SEED)
    n_movers = len(mover_df)
    r_boot = []
    for _ in range(N_BOOTSTRAP):
        idx = rng.integers(0, n_movers, size=n_movers)
        sample = mover_df.iloc[idx]
        r_boot.append(sample["club_mean"].corr(sample["intl_mean"]))
    r_boot = np.array(r_boot, dtype=float)
    r_boot = r_boot[~np.isnan(r_boot)]
    report_b = {"r": r, "n_movers": n_movers, "ci_low": float(np.percentile(r_boot, 2.5)),
                "ci_high": float(np.percentile(r_boot, 97.5)), "n_bootstrap_valid": len(r_boot)}
    print(json.dumps(report_b, indent=2))
    return {"b5a": report_a, "b5b": report_b}


def main():
    units, b1_data_report, reproduction_report = step_b1()
    if units is None:
        summary = {"status": "BLOCKED", "reason": "Step B1 reproduction check failed", "report": reproduction_report}
        SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
        print("STOPPING: Step B1 reproduction check failed. See", SUMMARY_PATH)
        return

    UNITS_OUT.parent.mkdir(parents=True, exist_ok=True)
    units.to_parquet(UNITS_OUT)

    gate_e_counts, movers, mover_position_match = step_b2(units)
    recovery_report = step_b3(units)

    summary = {
        "status": "PARTIAL" if not recovery_report["all_passed"] else "COMPLETE",
        "step_b1": reproduction_report, "step_b2": gate_e_counts, "step_b3": recovery_report,
    }

    if not recovery_report["all_passed"]:
        summary["step_b4"] = "NOT RUN -- recovery test failed, per hard rule"
        summary["step_b5"] = "NOT RUN -- recovery test failed, per hard rule"
        SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
        print("STOPPING before Step B4: recovery test failed at least one scenario. See", RECOVERY_OUT)
        return

    step_b4_report = step_b4(units, gate_e_counts)
    summary["step_b4"] = step_b4_report
    step_b5_report = step_b5(units, movers, mover_position_match)
    summary["step_b5"] = step_b5_report

    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
    print(f"\nWrote summary to {SUMMARY_PATH}")


if __name__ == "__main__":
    main()
