"""
Task 19, Steps 1-2: quantify the offside heuristic's defect against
StatsBomb's own ground truth ("Pass Offside" outcome labels), then
calibrate a replacement rule -- judged ONLY on those labels, never on a
Decision value, coefficient, or player.

R0 (the current rule, unchanged elsewhere in the engine) is: destination
beyond the second-rearmost visible opponent and beyond the ball. All
candidate rules here are variants of that same geometric test, gated by
extra conditions (minimum visible-opponent count K, attacking-half-only,
a tolerance margin M) -- never a different geometric idea.

Ground truth: passes with pass_outcome == "Pass Offside", across all 299
raw match event files (independent of engine v2's own eligibility gate).
False-positive rate and recall are computed on engine v2's existing
250,850-pass eligible population (same gate as grid.py: open-play Pass,
non-goalkeeper, frame with >=6 visible players, valid pass_end_location)
since that is the population every downstream engine-v2 number is built
on; passes outside that population (e.g. offside free-kicks, excluded by
EXCLUDED_PASS_TYPES) cannot contribute to recall as measured here, and
the count excluded is reported.

Run: python src/engine_v2/offside_diagnostic.py
"""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

from geometry import team_period_directions, normalize_xy

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
EVENTS_DIR = DATA_DIR / "raw" / "events"
FRAMES_DIR = DATA_DIR / "raw" / "frames"
EV_DIR = DATA_DIR / "processed" / "engine_v2" / "options_ev"
DIAGNOSTIC_TABLE_PATH = DATA_DIR / "processed" / "engine_v2" / "offside_diagnostic_table.parquet"
SUMMARY_PATH = DATA_DIR / "engine_v2_step1_offside_diagnostic.json"
STEP2_SUMMARY_PATH = DATA_DIR / "engine_v2_step2_offside_calibration.json"

EXCLUDED_PASS_TYPES = {"Corner", "Free Kick", "Throw-in", "Kick Off", "Goal Kick"}
K_VALUES = [6, 8, 10, 12]
M_VALUES = [0, 1, 2, 3]
MAX_FP_RATE = 0.05
OPPONENT_BINS = [(0, 6), (6, 8), (8, 10), (10, 12), (12, 100)]


def build_diagnostic_table() -> pd.DataFrame:
    match_ids = sorted(int(p.stem) for p in EVENTS_DIR.glob("*.parquet"))
    rows = []
    n_truly_offside_total = 0
    for i, mid in enumerate(match_ids):
        events = pd.read_parquet(EVENTS_DIR / f"{mid}.parquet")
        events = events.sort_values("index").reset_index(drop=True)
        n_truly_offside_total += int((events["pass_outcome"] == "Pass Offside").sum())

        ev_path = EV_DIR / f"{mid}.parquet"
        if not ev_path.exists():
            continue
        cand = pd.read_parquet(ev_path, columns=["event_id", "team", "period", "player_id", "chosen",
                                                    "pass_complete", "candidate_x", "candidate_y",
                                                    "passer_x", "passer_y"])
        chosen = cand[cand["chosen"]].copy()
        if len(chosen) == 0:
            continue

        frames = pd.read_parquet(FRAMES_DIR / f"{mid}.parquet")
        frames_by_event = {eid: g for eid, g in frames.groupby("id")}
        directions = team_period_directions(events)
        outcome_by_id = events.set_index("id")["pass_outcome"]

        for _, r in chosen.iterrows():
            eid = r["event_id"]
            direction = directions.get((r["team"], r["period"]), 1)
            frame = frames_by_event.get(eid)
            if frame is None:
                continue
            opponents = frame[frame["teammate"] == False]
            n_opp = len(opponents)
            if n_opp >= 2:
                opp_raw = np.array([list(l) for l in opponents["location"]], dtype=float)
                opp_nx = np.array([normalize_xy(x, y, direction)[0] for x, y in opp_raw])
                second_rearmost_nx = float(np.sort(opp_nx)[1])
            else:
                second_rearmost_nx = np.nan

            cand_nx, _ = normalize_xy(r["candidate_x"], r["candidate_y"], direction)
            passer_nx, _ = normalize_xy(r["passer_x"], r["passer_y"], direction)
            outcome = outcome_by_id.get(eid)
            rows.append({
                "match_id": mid, "event_id": eid,
                "pass_complete": bool(r["pass_complete"]),
                "is_truly_offside": bool(outcome == "Pass Offside"),
                "n_opponents_visible": n_opp,
                "candidate_nx": float(cand_nx), "passer_nx": float(passer_nx),
                "second_rearmost_opp_nx": second_rearmost_nx,
            })
        if (i + 1) % 50 == 0:
            print(f"  {i + 1}/{len(match_ids)} matches, rows so far={len(rows)}")

    df = pd.DataFrame(rows)
    return df, n_truly_offside_total


MIN_GATED_POPULATION = 100  # below this, a K-gate's own operating population is too small to trust its FP/recall


def evaluate_rule(df: pd.DataFrame, K: int = None, M: float = 0.0, attacking_half_only: bool = False) -> dict:
    has_second = df["second_rearmost_opp_nx"].notna()
    flag = has_second & (df["candidate_nx"] > (df["second_rearmost_opp_nx"] + M)) & (df["candidate_nx"] > df["passer_nx"])
    if K is not None:
        flag = flag & (df["n_opponents_visible"] >= K)
    if attacking_half_only:
        flag = flag & (df["candidate_nx"] >= 60.0)

    n_gated_population = int((df["n_opponents_visible"] >= K).sum()) if K is not None else len(df)
    completed = df["pass_complete"]
    offside_true = df["is_truly_offside"]
    fp_rate = float(flag[completed].mean())
    recall = float(flag[offside_true].mean()) if offside_true.sum() else None
    return {"K": K, "M": M, "attacking_half_only": attacking_half_only,
            "n_completed": int(completed.sum()), "n_flagged_of_completed": int(flag[completed].sum()),
            "false_positive_rate": fp_rate, "n_gated_population": n_gated_population,
            "n_truly_offside_in_population": int(offside_true.sum()),
            "n_truly_offside_flagged": int(flag[offside_true].sum()) if offside_true.sum() else 0,
            "recall": recall}


def breakdown_by(df: pd.DataFrame, flag: pd.Series, group_col_values: list, group_col: pd.Series, label: str) -> list:
    out = []
    for lo, hi in group_col_values:
        mask = (group_col >= lo) & (group_col < hi)
        sub_completed = df["pass_complete"] & mask
        sub_offside = df["is_truly_offside"] & mask
        out.append({
            f"{label}_range": f"{lo}-{hi}",
            "n_completed": int(sub_completed.sum()),
            "false_positive_rate": float(flag[sub_completed].mean()) if sub_completed.sum() else None,
            "n_truly_offside": int(sub_offside.sum()),
            "recall": float(flag[sub_offside].mean()) if sub_offside.sum() else None,
        })
    return out


def select_best(candidates: list) -> dict:
    """A K-gate whose own operating population is tiny (e.g. K=12: only
    0.0012% of rows ever have >=12 visible opponents, since a team fields
    at most 11) can trivially satisfy FP<5% by construction (it almost
    never fires) without being a real detector -- confirmed directly:
    K=12's single flagged completed pass (of 214,513) still yields
    FP=0.0005%, recall=0%, statistically meaningless from n=3. Candidates
    whose gated population is below MIN_GATED_POPULATION=100 are excluded
    from BOTH the primary (max-recall-subject-to-FP<5%) and fallback
    (lowest-FP) selection, since including them would let a structurally
    tiny operating point masquerade as "meeting the constraint." This is
    the plainly-intended reading of "meets that constraint" (a rule that
    actually operates on a real population), not a new criterion --
    disclosed here and in the results page."""
    non_degenerate = [c for c in candidates if c["n_gated_population"] >= MIN_GATED_POPULATION]
    feasible = [c for c in non_degenerate if c["false_positive_rate"] is not None and c["false_positive_rate"] < MAX_FP_RATE
                and c["recall"] is not None]
    if feasible:
        return max(feasible, key=lambda c: c["recall"])
    valid = [c for c in non_degenerate if c["false_positive_rate"] is not None] or candidates
    return min(valid, key=lambda c: c["false_positive_rate"])


def main():
    print("Step 1: building the ground-truth diagnostic table ...")
    df, n_truly_offside_total = build_diagnostic_table()
    df.to_parquet(DIAGNOSTIC_TABLE_PATH)
    print(f"  ground-truth 'Pass Offside' passes across 299 matches: {n_truly_offside_total}")
    print(f"  of those, {int(df['is_truly_offside'].sum())} fall within engine v2's eligible population "
          f"({n_truly_offside_total - int(df['is_truly_offside'].sum())} excluded, e.g. set-piece pass types)")

    r0 = evaluate_rule(df)  # K=None, M=0, attacking_half_only=False -- matches the CURRENT engine v2 rule exactly
    print(f"  R0 (current rule): FP rate={r0['false_positive_rate']:.4f}, recall={r0['recall']}")

    flag_r0 = df["second_rearmost_opp_nx"].notna() & (df["candidate_nx"] > df["second_rearmost_opp_nx"]) & (df["candidate_nx"] > df["passer_nx"])
    by_opponents = breakdown_by(df, flag_r0, OPPONENT_BINS, df["n_opponents_visible"], "n_opponents")
    by_half = breakdown_by(df, flag_r0, [(-1000, 60), (60, 1000)], df["candidate_nx"], "attacking_half")
    print(f"  R0 by n_opponents_visible: {by_opponents}")
    print(f"  R0 by attacking half (first row=own half, second=attacking half): {by_half}")

    step1_summary = {
        "n_truly_offside_total_299_matches": n_truly_offside_total,
        "n_truly_offside_in_eligible_population": int(df["is_truly_offside"].sum()),
        "n_eligible_chosen_passes": len(df),
        "R0": r0, "R0_by_n_opponents_visible": by_opponents, "R0_by_attacking_half": by_half,
    }
    SUMMARY_PATH.write_text(json.dumps(step1_summary, indent=2, default=str))

    print("\nStep 2: calibrating candidate rules against ground truth only ...")
    candidates = {"R0": r0}
    r1_variants = {}
    for K in K_VALUES:
        r = evaluate_rule(df, K=K)
        r1_variants[f"R1_K{K}"] = r
        candidates[f"R1_K{K}"] = r
        print(f"  R1_K{K}: FP={r['false_positive_rate']:.4f}, recall={r['recall']}")
    best_r1 = select_best(list(r1_variants.values()))
    best_K = best_r1["K"]
    print(f"  best K from R1: {best_K}")

    r2 = evaluate_rule(df, attacking_half_only=True)
    candidates["R2"] = r2
    print(f"  R2: FP={r2['false_positive_rate']:.4f}, recall={r2['recall']}")

    r3 = evaluate_rule(df, K=best_K, attacking_half_only=True)
    candidates["R3"] = r3
    print(f"  R3 (K={best_K} + attacking half): FP={r3['false_positive_rate']:.4f}, recall={r3['recall']}")

    r4_variants = {}
    for M in M_VALUES:
        r = evaluate_rule(df, K=best_K, M=M, attacking_half_only=True)
        r4_variants[f"R4_M{M}"] = r
        candidates[f"R4_M{M}"] = r
        print(f"  R4_M{M}: FP={r['false_positive_rate']:.4f}, recall={r['recall']}")

    all_candidates = list(candidates.values())
    non_degenerate = [c for c in all_candidates if c["n_gated_population"] >= MIN_GATED_POPULATION]
    feasible = [c for c in non_degenerate if c["false_positive_rate"] < MAX_FP_RATE and c["recall"] is not None]
    if feasible:
        winner = max(feasible, key=lambda c: c["recall"])
        winner_name = [k for k, v in candidates.items() if v is winner][0]
        outcome_note = f"selected {winner_name}: maximizes recall ({winner['recall']:.4f}) subject to FP<5%"
        drop_offside = False
    else:
        fallback_pool = non_degenerate or all_candidates
        winner = min(fallback_pool, key=lambda c: c["false_positive_rate"])
        winner_name = [k for k, v in candidates.items() if v is winner][0]
        outcome_note = (f"NO functioning rule met FP<5% (candidates gated by K=12 mechanically show FP=0/recall=0 "
                         f"but never fire -- max visible opponents is realistically <=11, so K=12 is a "
                         f"structurally impossible threshold, not a real operating point, and is excluded from "
                         f"selection; among rules that actually fire, the lowest FP was {winner_name} at "
                         f"{winner['false_positive_rate']:.4f}, still far above 5%) -- offside cannot be reliably "
                         f"detected from freeze frames at an acceptable false-positive cost; the engine STOPS "
                         f"excluding offside destinations altogether")
        drop_offside = True

    print(f"\n  FINAL SELECTION: {outcome_note}")

    step2_summary = {
        "best_K_from_R1": best_K, "all_candidates": candidates,
        "winner_name": winner_name, "winner": winner,
        "drop_offside_filtering": drop_offside, "selection_note": outcome_note,
    }
    STEP2_SUMMARY_PATH.write_text(json.dumps(step2_summary, indent=2, default=str))
    print(f"\nWrote {SUMMARY_PATH} and {STEP2_SUMMARY_PATH}")
    return step1_summary, step2_summary


if __name__ == "__main__":
    main()
