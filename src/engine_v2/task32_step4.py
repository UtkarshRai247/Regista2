"""
Task 32, Step 4 (A5): is Decision stable WITHIN a role?

Role assignment reuses Task 27 Step 1's exact per-pass-position technique
(per-pass StatsBomb `position`, not modal), extended from a single
DM-vs-not split to the brief's 6-way group list, >=50% of a qualifying
player's eligible passes (full corpus, 292 matches, same population as
every other Task 32 step).

(a) reuses step8_regate.py's own reliability_sweep(), unchanged, run
    WITHIN each role's player set.
(b) weighted one-way ANOVA of player-level mean Decision on role,
    weight = each player's eligible-pass count (disclosed operationalization
    of "one-way, weighted by passes" -- see the results page).
(c) reuses Task 26 Step 6's Study B units (study_b_units_v5.parquet,
    already built, not rebuilt) and its PH-B1 fit/interval machinery
    (fit_reml, method_ii_parametric_bootstrap -- the already-selected
    PRIMARY interval method from Task 26, not a fresh coverage-selection
    run), replacing the position_group dummies with role dummies.
    45-minute wall-clock budget; skip and disclose if exceeded.

Run: python src/engine_v2/task32_step4.py
"""
import json
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent / "decision_engine"))
from reml_crossed import fit_reml  # noqa: E402
from step8_regate import reliability_sweep  # noqa: E402
from task26_step6_study_b import method_ii_parametric_bootstrap, X_COLS  # noqa: E402

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
EVENTS_DIR = DATA_DIR / "raw" / "events"
PASS_DER_V8_PATH = DATA_DIR / "processed" / "engine_v2" / "pass_der_v8.parquet"
LEADERBOARD_V5C_PATH = DATA_DIR / "processed" / "leaderboard_v5c.parquet"
STUDY_B_UNITS_PATH = DATA_DIR / "processed" / "engine_v2" / "study_b_units_v5.parquet"
SUMMARY_PATH = DATA_DIR / "engine_v2_task32_step4.json"

TIME_BUDGET_SECONDS = 45 * 60
ROLE_SHARE_THRESHOLD = 0.50
SEED = 20260928

ROLE_POSITIONS = {
    "CB": {"Center Back", "Left Center Back", "Right Center Back"},
    "FB": {"Left Back", "Right Back", "Left Wing Back", "Right Wing Back"},
    "DM": {"Center Defensive Midfield", "Left Defensive Midfield", "Right Defensive Midfield"},
    "CM": {"Center Midfield", "Left Center Midfield", "Right Center Midfield"},
    "AM/W": {"Center Attacking Midfield", "Left Attacking Midfield", "Right Attacking Midfield",
              "Left Midfield", "Right Midfield", "Left Wing", "Right Wing"},
    "FW": {"Center Forward", "Left Center Forward", "Right Center Forward", "Secondary Striker"},
}


def assign_roles(qualifying_ids: set) -> pd.DataFrame:
    per_pass = pd.read_parquet(PASS_DER_V8_PATH, columns=["match_id", "event_id", "player_id"])
    per_pass = per_pass[per_pass["player_id"].isin(qualifying_ids)]
    match_ids = sorted(per_pass["match_id"].unique())
    pos_frames = []
    for mid in match_ids:
        ev = pd.read_parquet(EVENTS_DIR / f"{mid}.parquet", columns=["id", "position"])
        ev = ev.rename(columns={"id": "event_id"})
        ev["match_id"] = mid
        pos_frames.append(ev)
    positions = pd.concat(pos_frames, ignore_index=True)
    per_pass = per_pass.merge(positions, on=["match_id", "event_id"], how="left")

    for role, pos_set in ROLE_POSITIONS.items():
        per_pass[f"is_{role}"] = per_pass["position"].isin(pos_set)

    agg = per_pass.groupby("player_id").agg(
        n_eligible_passes=("position", "size"),
        **{f"n_{role}": (f"is_{role}", "sum") for role in ROLE_POSITIONS},
    ).reset_index()
    for role in ROLE_POSITIONS:
        agg[f"share_{role}"] = agg[f"n_{role}"] / agg["n_eligible_passes"]

    def pick_role(row):
        for role in ROLE_POSITIONS:
            if row[f"share_{role}"] >= ROLE_SHARE_THRESHOLD:
                return role
        return "MIXED"
    agg["role"] = agg.apply(pick_role, axis=1)
    return agg[["player_id", "n_eligible_passes", "role"] + [f"share_{r}" for r in ROLE_POSITIONS]]


def main():
    t_start = time.time()
    print("Task 32 Step 4 (A5): role-based reliability ...")
    leaderboard = pd.read_parquet(LEADERBOARD_V5C_PATH, columns=["player_id", "player_name"])
    qualifying_ids = set(leaderboard["player_id"])
    print(f"  qualifying players: {len(qualifying_ids)}")

    roles = assign_roles(qualifying_ids)
    role_counts = roles["role"].value_counts().to_dict()
    print(f"  role counts: {role_counts}")

    per_pass_der = pd.read_parquet(PASS_DER_V8_PATH,
                                    columns=["player_id", "competition_id", "season_id", "decision_new"])
    role_by_player = roles.set_index("player_id")["role"].to_dict()
    per_pass_der["role"] = per_pass_der["player_id"].map(role_by_player)
    per_pass_der = per_pass_der[per_pass_der["player_id"].isin(qualifying_ids)]

    thresholds = [100, 200, 300, 500]
    print("  (a) reliability_sweep WITHIN each role ...")
    within_role_reliability = {}
    for role in list(ROLE_POSITIONS) + ["MIXED"]:
        sub = per_pass_der[per_pass_der["role"] == role]
        n_players_role = sub["player_id"].nunique()
        if n_players_role < 3:
            within_role_reliability[role] = {"n_players": n_players_role, "note": "too few players to sweep"}
            continue
        sweep = reliability_sweep(sub, "decision_new", thresholds)
        within_role_reliability[role] = {"n_players": n_players_role, "sweep": sweep}
        print(f"    {role} (n_players={n_players_role}): "
              f"{ {t: sweep[t]['median'] for t in thresholds} }")

    print("  (b) weighted one-way ANOVA of player-level mean Decision on role ...")
    player_stats = per_pass_der.groupby(["player_id", "role"]).agg(
        n_i=("decision_new", "size"), m_i=("decision_new", "mean")).reset_index()
    grand_mean = np.average(player_stats["m_i"], weights=player_stats["n_i"])
    ss_total = float(np.sum(player_stats["n_i"] * (player_stats["m_i"] - grand_mean) ** 2))
    ss_between = 0.0
    for role, g in player_stats.groupby("role"):
        role_mean = np.average(g["m_i"], weights=g["n_i"])
        ss_between += float(np.sum(g["n_i"]) * (role_mean - grand_mean) ** 2)
    variance_share_role = ss_between / ss_total
    print(f"    weighted eta^2 (share of variance explained by role): {variance_share_role:.4f}")

    print("  (c) PH-B1 refit with roles (Study B, engine v5) ...")
    c_result = {"skipped": False}
    if not STUDY_B_UNITS_PATH.exists():
        c_result = {"skipped": True, "reason": f"{STUDY_B_UNITS_PATH} not found (Task 26 Step 6 must have run)"}
    else:
        units = pd.read_parquet(STUDY_B_UNITS_PATH)
        units["role"] = units["player_id"].map(role_by_player)
        units_role = units.dropna(subset=["role"]).copy()
        group_counts = units_role["role"].value_counts()
        dummy_roles = [r for r in ROLE_POSITIONS if group_counts.get(r, 0) > 0]  # MIXED = reference
        for r in dummy_roles:
            units_role[f"is_{r}"] = (units_role["role"] == r).astype(float)
        x_cols_role = X_COLS + [f"is_{r}" for r in dummy_roles]
        t_c_start = time.time()
        phb1_role_fit = fit_reml(units_role, x_cols=x_cols_role)
        elapsed_after_fit = time.time() - t_c_start
        if elapsed_after_fit > TIME_BUDGET_SECONDS:
            c_result = {"skipped": True, "reason": "REML fit alone exceeded the 45-minute budget",
                        "phb1_role_fit": phb1_role_fit}
        else:
            phb1_role_ci = method_ii_parametric_bootstrap(units_role, phb1_role_fit, x_cols_role, SEED)
            elapsed_total = time.time() - t_c_start
            if elapsed_total > TIME_BUDGET_SECONDS:
                c_result = {"skipped": True, "reason": "finished but exceeded the 45-minute budget; reporting anyway",
                            "phb1_role_fit": phb1_role_fit, "phb1_role_ci": phb1_role_ci,
                            "wall_clock_seconds": elapsed_total, "dummy_roles": dummy_roles,
                            "n_units": len(units_role)}
            else:
                c_result = {"skipped": False, "phb1_role_fit": phb1_role_fit, "phb1_role_ci": phb1_role_ci,
                            "wall_clock_seconds": elapsed_total, "dummy_roles": dummy_roles,
                            "n_units": len(units_role), "reference_category": "MIXED"}
        print(f"    PH-B1 (role fixed effects): S={c_result.get('phb1_role_fit', {}).get('S')}, "
              f"CI={c_result.get('phb1_role_ci')}, wall_clock={c_result.get('wall_clock_seconds')}")

    summary = {
        "n_qualifying": len(qualifying_ids), "role_counts": role_counts,
        "a_within_role_reliability": within_role_reliability,
        "b_variance_share_explained_by_role": variance_share_role,
        "c_phb1_role_refit": c_result,
        "total_wall_clock_seconds": time.time() - t_start,
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
    print(f"\nWrote {SUMMARY_PATH}")
    return summary


if __name__ == "__main__":
    main()
