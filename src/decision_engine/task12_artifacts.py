"""
Task 12 — Total-effect spec (PH-O4), leaderboard, worked example
(Amendment v2-9). No new hypotheses; Steps 2-3 are descriptive artifacts.

Run: python src/decision_engine/task12_artifacts.py
"""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb

from decompose import DATA_DIR, EVENTS_DIR, PV_MODEL_PATH, build_per_pass_table, match_competition_lookup
from task04_situation_context import position_group
from task05_study_a_discovery import build_available_types_table, recover_raw_positions
from task06_study_a_confirmation import confirmation_match_ids, load_and_prepare
from task10_partB_outcome import fit_ols
from task11_outcome_diagnostics import build_diagnostics_frame

warnings.filterwarnings("ignore")

POLICY_PATH = DATA_DIR / "processed" / "options_policy.parquet"
PASSES_PATH = DATA_DIR / "processed" / "passes_situation.parquet"
TASK10_SUMMARY_PATH = DATA_DIR / "task10_partB_outcome.json"
TASK11_SUMMARY_PATH = DATA_DIR / "task11_outcome_diagnostics.json"
SUMMARY_PATH = DATA_DIR / "task12_artifacts.json"
WORKED_EXAMPLE_PATH = Path(__file__).parent.parent.parent / "data" / "processed" / "worked_example.csv"

RELIABILITY = 0.744
MIN_PASSES_LEADERBOARD = 200
TOP_BOTTOM_N = 20

COMP_NAMES = {
    (9, 281): "Bundesliga 2023/24", (43, 106): "FIFA World Cup 2022",
    (11, 90): "La Liga 2020/21", (7, 235): "Ligue 1 2022/23",
    (7, 108): "Ligue 1 2021/22", (44, 107): "MLS 2023",
    (55, 282): "UEFA Euro 2024", (55, 43): "UEFA Euro 2020",
}


# ---------- Step 1: PH-O4 ----------
def step1_pho4(units, cs_cols):
    predictors = ["decision_z", "is_home"] + cs_cols
    results = {}
    for outcome in ("xg", "goals"):
        results[f"{outcome}_PH-O4"] = fit_ols(units, outcome, predictors, "team_context")
    return results


# ---------- Step 2: Leaderboard ----------
def build_position_and_name_lookup() -> tuple:
    match_ids = sorted(int(p.stem) for p in EVENTS_DIR.glob("*.parquet"))
    pos_counts, name_counts = {}, {}
    for mid in match_ids:
        ev = pd.read_parquet(EVENTS_DIR / f"{mid}.parquet", columns=["player_id", "position", "player"])
        sub = ev.dropna(subset=["player_id", "position"])
        for pid, pos, name in zip(sub["player_id"], sub["position"], sub["player"]):
            pos_counts.setdefault(pid, {}).setdefault(pos, 0)
            pos_counts[pid][pos] += 1
            if pd.notna(name):
                name_counts.setdefault(pid, {}).setdefault(name, 0)
                name_counts[pid][name] += 1
    pos_lookup = {pid: max(counts, key=counts.get) for pid, counts in pos_counts.items()}
    name_lookup = {pid: max(counts, key=counts.get) for pid, counts in name_counts.items()}
    return pos_lookup, name_lookup


def step2_leaderboard(per_pass: pd.DataFrame) -> dict:
    comp_lookup = match_competition_lookup()
    per_pass = per_pass.copy()
    per_pass["competition_id"] = per_pass["match_id"].map(lambda m: comp_lookup.get(m, (None, None))[0])
    per_pass["season_id"] = per_pass["match_id"].map(lambda m: comp_lookup.get(m, (None, None))[1])

    pooled = per_pass.groupby("player_id").agg(
        n_eligible_passes=("decision", "count"), decision_per_100=("decision", lambda s: s.mean() * 100),
    ).reset_index()
    qualifying = pooled[pooled["n_eligible_passes"] >= MIN_PASSES_LEADERBOARD].copy()
    n_qualifying = len(qualifying)

    comps_per_player = per_pass[per_pass["player_id"].isin(qualifying["player_id"])].groupby(
        "player_id").apply(lambda g: sorted(set(
            COMP_NAMES.get((c, s), f"comp={c},season={s}")
            for c, s in zip(g["competition_id"], g["season_id"])))).rename("competitions").reset_index()
    qualifying = qualifying.merge(comps_per_player, on="player_id", how="left")

    pos_lookup, name_lookup = build_position_and_name_lookup()
    qualifying["position_group"] = qualifying["player_id"].map(lambda p: position_group(pos_lookup.get(p)))
    qualifying["player_name"] = qualifying["player_id"].map(lambda p: name_lookup.get(p, "?"))

    overall_mean_unweighted = float(qualifying["decision_per_100"].mean())
    overall_mean_weighted = float(
        (qualifying["decision_per_100"] * qualifying["n_eligible_passes"]).sum() / qualifying["n_eligible_passes"].sum()
    )
    qualifying["shrunken_decision_per_100"] = overall_mean_unweighted + RELIABILITY * (
        qualifying["decision_per_100"] - overall_mean_unweighted)

    cols = ["player_id", "player_name", "position_group", "competitions", "n_eligible_passes",
            "decision_per_100", "shrunken_decision_per_100"]
    top20 = qualifying.nlargest(TOP_BOTTOM_N, "shrunken_decision_per_100")[cols].to_dict("records")
    bottom20 = qualifying.nsmallest(TOP_BOTTOM_N, "shrunken_decision_per_100")[cols].to_dict("records")

    return {
        "n_qualifying_players": n_qualifying, "reliability": RELIABILITY,
        "overall_mean_unweighted": overall_mean_unweighted, "overall_mean_pass_weighted": overall_mean_weighted,
        "top20": top20, "bottom20": bottom20,
    }


# ---------- Step 3: Worked example ----------
def build_confirmation_avail():
    confirmation_ids = confirmation_match_ids()
    opt, passes, join_report = load_and_prepare(confirmation_ids)
    if join_report["match_rate"] != 1.0 or join_report["n_group_size_mismatches"]:
        raise RuntimeError(f"options_ev join failed: {join_report}")
    cell_info = passes[["match_id", "event_id", "zone", "under_pressure", "game_state", "team",
                         "competition_id", "season_id", "n_visible_players"]]
    avail = build_available_types_table(opt, cell_info[["match_id", "event_id", "zone",
                                                          "under_pressure", "game_state"]])
    return avail, opt, cell_info


def join_options_policy_full(typed: pd.DataFrame) -> pd.DataFrame:
    """Same match logic as task05_study_a_discovery.join_ev, but against
    options_policy.parquet (row-aligned superset of options_ev.parquet:
    same 1,237,611 rows/key columns, plus policy_raw_score/
    policy_probability) so one join carries p_success/ev/policy
    probability/angle/raw coordinates together instead of two."""
    # `typed` here is `opt` from load_and_prepare, which already carries
    # its own "_merge", "_rank", "ev", "distance", "pass_complete", "team"
    # and "candidate_x_raw"/"candidate_y_raw" columns from its EARLIER
    # join_ev(typed, ev) call (task05/06's own chain). Every policy column
    # that would collide with one of these is pulled under an explicit
    # "_pol" name instead of relying on pandas' silent _x/_y suffixing,
    # which previously left "ev" missing under the name this function
    # expected.
    typed = typed.drop(columns=["_merge", "_rank"], errors="ignore")
    typed = recover_raw_positions(typed)
    # Restrict to this pass's own (match_id, event_id) population BEFORE
    # any groupby -- reading the full options_policy.parquet and grouping
    # it whole hits the same "differently-shaped index" bug Task 09's
    # compute_g_p_l_ph2 hit (ValueError: Can only compare identically-
    # labeled Series objects), since a single pass's typed rows and the
    # full 1.2M-row policy table produce groupby indices that don't align.
    match_ids = typed["match_id"].unique().tolist()
    event_ids = typed["event_id"].unique().tolist()
    policy = pd.read_parquet(POLICY_PATH, columns=["match_id", "event_id", "candidate_x", "candidate_y",
                                                     "distance", "angle", "p_success", "ev", "policy_probability"],
                              filters=[("match_id", "in", match_ids), ("event_id", "in", event_ids)])
    policy = policy.rename(columns={"candidate_x": "candidate_x_pol", "candidate_y": "candidate_y_pol",
                                     "distance": "distance_pol", "ev": "ev_pol"})

    typed = typed.copy()
    typed["cx_r"] = typed["candidate_x_raw"].round(6)
    typed["cy_r"] = typed["candidate_y_raw"].round(6)
    policy["cx_r"] = policy["candidate_x_pol"].round(6)
    policy["cy_r"] = policy["candidate_y_pol"].round(6)

    key_cols = ["match_id", "event_id", "cx_r", "cy_r"]
    typed_group_sizes = typed.groupby(key_cols).size()
    policy_group_sizes = policy.groupby(key_cols).size()
    n_typed_collisions = int((typed_group_sizes > 1).sum())
    n_policy_collisions = int((policy_group_sizes > 1).sum())
    n_group_size_mismatches = int((typed_group_sizes.reindex(policy_group_sizes.index, fill_value=0)
                                    != policy_group_sizes.reindex(typed_group_sizes.index, fill_value=0)).sum())

    typed["_rank"] = typed.groupby(key_cols).cumcount()
    policy["_rank"] = policy.groupby(key_cols).cumcount()
    merged = typed.merge(
        policy[key_cols + ["_rank", "distance_pol", "angle", "p_success", "ev_pol", "policy_probability",
                            "candidate_x_pol", "candidate_y_pol"]],
        on=key_cols + ["_rank"], how="left", indicator=True)
    n_matched = int((merged["_merge"] == "both").sum())
    report = {"n_typed_rows": len(typed), "n_matched": n_matched,
              "match_rate": n_matched / len(typed) if len(typed) else None,
              "n_typed_key_collisions": n_typed_collisions, "n_policy_key_collisions": n_policy_collisions,
              "n_group_size_mismatches": n_group_size_mismatches}
    return merged, report


def next_two_events(match_id: int, event_id: str) -> list:
    ev = pd.read_parquet(EVENTS_DIR / f"{match_id}.parquet")
    ev = ev.sort_values("index").reset_index(drop=True)
    pos = ev.index[ev["id"] == event_id]
    if len(pos) == 0:
        return []
    i = pos[0]
    out = []
    for j in range(i + 1, min(i + 3, len(ev))):
        r = ev.iloc[j]
        out.append({"type": r["type"], "team": r["team"], "player": r.get("player")})
    return out


def step3_worked_example():
    avail, opt, cell_info = build_confirmation_avail()
    cell = avail[(avail["zone"] == "middle") & (avail["under_pressure"] == False)
                 & (avail["game_state"].isin(["level", "trailing"]))]
    lat_med = cell[cell["option_type"] == "lateral_medium"][
        ["match_id", "event_id", "ev_star"]].rename(columns={"ev_star": "ev_star_latmed"})
    chosen_rows = cell[cell["option_type"] == cell["j"]][
        ["match_id", "event_id", "j", "ev_star_j"]].drop_duplicates()
    qualifying = chosen_rows[chosen_rows["j"] != "lateral_medium"].merge(
        lat_med, on=["match_id", "event_id"], how="inner")
    qualifying["g"] = qualifying["ev_star_latmed"] - qualifying["ev_star_j"]
    n_qualifying = len(qualifying)

    qualifying = qualifying.sort_values(["g", "match_id", "event_id"]).reset_index(drop=True)
    median_idx = (n_qualifying - 1) // 2
    selected = qualifying.iloc[median_idx]
    mid, eid = int(selected["match_id"]), selected["event_id"]

    typed_pass = opt[(opt["match_id"] == mid) & (opt["event_id"] == eid)].copy()
    merged, join_report = join_options_policy_full(typed_pass)
    if join_report["match_rate"] != 1.0 or join_report["n_group_size_mismatches"]:
        raise RuntimeError(f"Worked-example options_policy join failed: {join_report}")

    # "Chosen option" = the specific candidate actually passed to (the
    # `chosen` flag), not the best-EV candidate of the chosen TYPE -- a
    # type bucket can hold more than one physical candidate, and the
    # player's actual choice need not be the highest-EV one within it.
    # "Best lateral_medium option" IS the max-EV candidate of that type,
    # matching ev_star's own definition (the counterfactual comparison).
    chosen_option = merged[merged["chosen"] == True].iloc[0]  # noqa: E712
    latmed_option = merged[merged["option_type"] == "lateral_medium"].sort_values("ev_pol", ascending=False).iloc[0]

    n_options_in_frame = int(len(merged))
    cell_row = cell_info[(cell_info["match_id"] == mid) & (cell_info["event_id"] == eid)].iloc[0]
    comp_lookup = match_competition_lookup()
    comp_id, season_id = comp_lookup.get(mid, (None, None))

    ev_full = pd.read_parquet(EVENTS_DIR / f"{mid}.parquet")
    pass_row = ev_full[ev_full["id"] == eid].iloc[0]
    passer_pos = position_group(pass_row.get("position"))
    minute = int(pass_row["minute"])

    def option_detail(row):
        return {"option_type": row["option_type"], "candidate_x": float(row["candidate_x_pol"]),
                "candidate_y": float(row["candidate_y_pol"]), "distance": float(row["distance_pol"]),
                "angle": float(row["angle"]), "p_success": float(row["p_success"]), "ev": float(row["ev_pol"]),
                "policy_probability": float(row["policy_probability"])}

    result = {
        "n_qualifying_passes": n_qualifying, "selected_index": median_idx, "g": float(selected["g"]),
        "match_id": mid, "competition": COMP_NAMES.get((comp_id, season_id), f"comp={comp_id},season={season_id}"),
        "minute": minute, "team": cell_row["team"], "passer_position_group": passer_pos,
        "chosen_option": option_detail(chosen_option), "lateral_medium_option": option_detail(latmed_option),
        "n_options_in_frame": n_options_in_frame, "n_visible_players": int(cell_row["n_visible_players"]),
        "pass_complete": bool(chosen_option["pass_complete"]) if "pass_complete" in merged.columns else None,
        "next_two_events": next_two_events(mid, eid),
        "join_report": join_report,
    }

    merged.to_csv(WORKED_EXAMPLE_PATH, index=False)
    return result


def main():
    print("Step 1: PH-O4 (total-effect spec, no possession share) ...")
    units, cs_cols, tc_cols = build_diagnostics_frame()
    step1_results = step1_pho4(units, cs_cols)
    for k, v in step1_results.items():
        print(f"{k}: n={v['n']}, R2={v['r_squared']:.4f}, decision_z={v['coefficients']['decision_z']}")

    print("\nStep 2: leaderboard ...")
    policy = pd.read_parquet(POLICY_PATH)
    pv_model = xgb.XGBClassifier()
    pv_model.load_model(PV_MODEL_PATH)
    per_pass = build_per_pass_table(policy, pv_model, verbose=True)
    step2_results = step2_leaderboard(per_pass)
    print(f"Qualifying players: {step2_results['n_qualifying_players']}, "
          f"overall_mean(unweighted)={step2_results['overall_mean_unweighted']:.4f}, "
          f"overall_mean(pass-weighted)={step2_results['overall_mean_pass_weighted']:.4f}")

    print("\nStep 3: worked example ...")
    step3_results = step3_worked_example()
    print(json.dumps(step3_results, indent=2, default=str))

    task10 = json.loads(TASK10_SUMMARY_PATH.read_text())
    task11 = json.loads(TASK11_SUMMARY_PATH.read_text())
    summary = {
        "status": "COMPLETE",
        "step1_pho4": step1_results,
        "step1_ho1_primary": task10["results"]["xg_H-O1"], "step1_ho1_goals_primary": task10["results"]["goals_H-O1"],
        "step1_pho1_primary": task11["step2_results"]["xg_PH-O1"],
        "step1_pho1_goals_primary": task11["step2_results"]["goals_PH-O1"],
        "step2_leaderboard": step2_results, "step3_worked_example": step3_results,
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
    print(f"\nWrote summary to {SUMMARY_PATH}")
    print(f"Wrote worked example option table to {WORKED_EXAMPLE_PATH}")


if __name__ == "__main__":
    main()
