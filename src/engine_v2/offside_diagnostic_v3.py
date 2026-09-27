"""
Task 25, Step 2 (Task 24's Step 4): re-run Task 19c's exact offside
calibration procedure (same candidate rules, same 5% false-positive
bar, same selection criterion -- `evaluate_rule`/`breakdown_by`/
`select_best`/`K_VALUES`/`M_VALUES`/`MAX_FP_RATE`/`OPPONENT_BINS`,
all reused UNCHANGED from `offside_diagnostic.py`) against the same
StatsBomb "Pass Offside" ground truth, on THIS task's corrected
candidate corpus (`options_ev_v4`, built on the now-fixed geometry).
Only the corpus differs from `offside_diagnostic_v2.py`; the
calibration logic itself is identical.

Run: python src/engine_v2/offside_diagnostic_v3.py
"""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

from geometry import team_period_directions, normalize_xy
from offside_diagnostic import evaluate_rule, breakdown_by, select_best, K_VALUES, M_VALUES, MAX_FP_RATE, OPPONENT_BINS

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
EVENTS_DIR = DATA_DIR / "raw" / "events"
FRAMES_DIR = DATA_DIR / "raw" / "frames"
EV_DIR = DATA_DIR / "processed" / "engine_v2" / "options_ev_v4"
DIAGNOSTIC_TABLE_PATH = DATA_DIR / "processed" / "engine_v2" / "offside_diagnostic_table_v3.parquet"
SUMMARY_PATH = DATA_DIR / "engine_v2_step1_offside_diagnostic_v3.json"
STEP2_SUMMARY_PATH = DATA_DIR / "engine_v2_step2_offside_calibration_v3.json"
TASK19C_SUMMARY_PATH = DATA_DIR / "engine_v2_step1_offside_diagnostic_v2.json"


def build_diagnostic_table_v3() -> tuple:
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
                second_rearmost_nx = float(np.sort(opp_nx)[-2])
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


def main():
    print("Task 25 Step 2: re-running Task 19c's offside calibration on the corrected corpus ...")
    df, n_truly_offside_total = build_diagnostic_table_v3()
    df.to_parquet(DIAGNOSTIC_TABLE_PATH)
    print(f"  ground-truth 'Pass Offside' passes across 299 matches: {n_truly_offside_total}")
    print(f"  of those, {int(df['is_truly_offside'].sum())} fall within engine v2's eligible population")

    r0 = evaluate_rule(df)
    task19c = json.loads(TASK19C_SUMMARY_PATH.read_text())
    print(f"  R0 (this task, corrected geometry): FP rate={r0['false_positive_rate']:.4f}, recall={r0['recall']:.4f}")
    print(f"  R0 Task 19c (old geometry): FP rate={task19c['R0_corrected']['false_positive_rate']:.4f}, recall={task19c['R0_corrected']['recall']:.4f}")

    flag_r0 = df["second_rearmost_opp_nx"].notna() & (df["candidate_nx"] > df["second_rearmost_opp_nx"]) & (df["candidate_nx"] > df["passer_nx"])
    by_opponents = breakdown_by(df, flag_r0, OPPONENT_BINS, df["n_opponents_visible"], "n_opponents")
    by_half = breakdown_by(df, flag_r0, [(-1000, 60), (60, 1000)], df["candidate_nx"], "attacking_half")
    print(f"  R0 by n_opponents_visible: {by_opponents}")
    print(f"  R0 by attacking half: {by_half}")

    step1_summary = {
        "n_truly_offside_total_299_matches": n_truly_offside_total,
        "n_truly_offside_in_eligible_population": int(df["is_truly_offside"].sum()),
        "n_eligible_chosen_passes": len(df),
        "R0": r0, "R0_task19c": task19c["R0_corrected"],
        "R0_by_n_opponents_visible": by_opponents, "R0_by_attacking_half": by_half,
    }
    SUMMARY_PATH.write_text(json.dumps(step1_summary, indent=2, default=str))

    print("\nCalibrating candidate rules against ground truth only ...")
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

    winner = select_best(list(candidates.values()))
    winner_name = [k for k, v in candidates.items() if v is winner][0]
    meets_bar = winner["false_positive_rate"] < MAX_FP_RATE and winner["n_gated_population"] >= 100
    if meets_bar:
        outcome_note = f"selected {winner_name}: maximizes recall ({winner['recall']:.4f}) subject to FP<5%"
    else:
        outcome_note = (f"NO rule clears FP<5% (best candidate {winner_name} at "
                         f"FP={winner['false_positive_rate']:.4f}) -- offside filtering stays dropped")
    print(f"\n  FINAL SELECTION: {outcome_note}")

    step2_summary = {
        "best_K_from_R1": best_K, "all_candidates": candidates,
        "winner_name": winner_name, "winner": winner,
        "rule_clears_bar": meets_bar, "selection_note": outcome_note,
    }
    STEP2_SUMMARY_PATH.write_text(json.dumps(step2_summary, indent=2, default=str))
    print(f"\nWrote {SUMMARY_PATH} and {STEP2_SUMMARY_PATH}")
    return step1_summary, step2_summary


if __name__ == "__main__":
    main()
