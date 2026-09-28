"""
Task 32, Step 1 (A2): is the "typical choice" baseline unbiased?
Using the cross-fitted per-pass values (pass_der_crossfit_v5.parquet,
292 matches -- see the results page for why 292, not 299).

(a) Mean Decision overall, share of the 537 qualifying players (Task
    28's set) with a positive mean.
(b) Mean Decision/ev_chosen/policy_weighted_ev by passer zone
    (0-40/40-80/80-120), pass length (0-10/10-20/20-30/30+), pass
    outcome (complete/incomplete).
(c) Calibration: decile of policy_weighted_ev -> mean policy_weighted_ev
    vs mean ev_chosen.
(d) Share of chosen options outside the policy's restricted candidate
    set (p_success>=0.05, distance_u<=45, NOT offside_v4); mean
    Decision inside vs outside.
(e) Policy top-1/top-3 accuracy on v5, cited from the crossfit summary.

Run: python src/engine_v2/task32_step1.py
"""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

from validation_common import zone_of
from policy_baseline_fix import RESTRICT_MIN_P_SUCCESS, RESTRICT_MAX_DISTANCE_U
from offside_v4 import add_offside_v4_column

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
EVENTS_DIR = DATA_DIR / "raw" / "events"
FRAMES_DIR = DATA_DIR / "raw" / "frames"
EV_DIR = DATA_DIR / "processed" / "engine_v2" / "options_ev_v4"
CROSSFIT_PATH = DATA_DIR / "processed" / "engine_v2" / "pass_der_crossfit_v5.parquet"
LEADERBOARD_V5C_PATH = DATA_DIR / "processed" / "leaderboard_v5c.parquet"
CROSSFIT_SUMMARY_PATH = DATA_DIR / "engine_v2_step6_crossfit_v5.json"
SUMMARY_PATH = DATA_DIR / "engine_v2_task32_step1.json"

LENGTH_BUCKETS = [(0, 10), (10, 20), (20, 30), (30, 1000)]
LENGTH_LABELS = ["0-10", "10-20", "20-30", "30+"]


def length_bucket(x):
    for (lo, hi), label in zip(LENGTH_BUCKETS, LENGTH_LABELS):
        if lo <= x < hi:
            return label
    return None


def main():
    print("Task 32 Step 1 (A2): typical-choice baseline diagnostics ...")
    crossfit = pd.read_parquet(CROSSFIT_PATH)
    match_ids = sorted(crossfit["match_id"].unique())
    print(f"  cross-fit corpus: {len(crossfit)} passes, {len(match_ids)} matches")

    print("  joining chosen-candidate metadata (passer_x, pass_length, pass_complete, "
          "p_success, distance_u) + offside_v4 per match ...")
    meta_frames = []
    for i, mid in enumerate(match_ids):
        df = pd.read_parquet(EV_DIR / f"{mid}.parquet",
                              columns=["match_id", "event_id", "team", "period", "chosen", "passer_x", "passer_y",
                                       "candidate_x", "candidate_y", "pass_length", "pass_complete", "p_success",
                                       "distance_u", "EV"])
        chosen = df[df["chosen"]].copy()
        events = pd.read_parquet(EVENTS_DIR / f"{mid}.parquet").sort_values("index").reset_index(drop=True)
        frames = pd.read_parquet(FRAMES_DIR / f"{mid}.parquet")
        df_off = add_offside_v4_column(df, events, frames)
        chosen_off = df_off[df_off["chosen"]][["match_id", "event_id", "offside_v4"]]
        chosen = chosen.merge(chosen_off, on=["match_id", "event_id"], how="left")

        # (c)/mean-of-all-candidates not needed here (Step 6 needs it), but grab
        # mean EV over ALL candidates per pass now while the file is open, for reuse.
        all_mean_ev = df.groupby("event_id")["EV"].mean().rename("mean_ev_all_candidates").reset_index()
        chosen = chosen.merge(all_mean_ev, on="event_id", how="left")
        meta_frames.append(chosen)
        if (i + 1) % 50 == 0:
            print(f"    {i + 1}/{len(match_ids)} matches")

    meta = pd.concat(meta_frames, ignore_index=True)
    joined = crossfit.merge(meta, on=["match_id", "event_id"], how="inner", suffixes=("", "_meta"))
    print(f"  joined: {len(joined)} passes")

    joined["zone"] = joined["passer_x"].apply(zone_of)
    joined["length_bucket"] = joined["pass_length"].apply(length_bucket)
    joined["outcome"] = np.where(joined["pass_complete"], "complete", "incomplete")
    joined["restricted_ok"] = (joined["p_success"] >= RESTRICT_MIN_P_SUCCESS) & \
        (joined["distance_u"] <= RESTRICT_MAX_DISTANCE_U) & (~joined["offside_v4"].fillna(False))

    # (a)
    leaderboard = pd.read_parquet(LEADERBOARD_V5C_PATH, columns=["player_id"])
    qualifying_ids = set(leaderboard["player_id"])
    joined_qual = joined[joined["player_id"].isin(qualifying_ids)]
    per_player_mean = joined_qual.groupby("player_id")["decision"].mean()
    a = {
        "mean_decision_overall_crossfit": float(joined["decision"].mean()),
        "n_passes_overall_crossfit": len(joined),
        "n_qualifying_players_with_crossfit_passes": int(per_player_mean.notna().sum()),
        "share_qualifying_players_positive_mean": float((per_player_mean > 0).mean()),
    }
    print(f"\n  (a) {a}")

    # (b)
    def by_group(col):
        g = joined.groupby(col).agg(
            n=("decision", "size"), mean_decision=("decision", "mean"),
            mean_ev_chosen=("ev_chosen", "mean"), mean_policy_weighted_ev=("policy_weighted_ev", "mean"),
        ).reset_index()
        return g.to_dict("records")

    b_zone = by_group("zone")
    b_length = by_group("length_bucket")
    b_outcome = by_group("outcome")
    print(f"  (b) by zone: {b_zone}")
    print(f"  (b) by length: {b_length}")
    print(f"  (b) by outcome: {b_outcome}")

    # (c)
    joined_c = joined.dropna(subset=["policy_weighted_ev"]).copy()
    joined_c["decile"] = pd.qcut(joined_c["policy_weighted_ev"], 10, labels=False, duplicates="drop")
    c = joined_c.groupby("decile").agg(
        n=("decision", "size"), mean_policy_weighted_ev=("policy_weighted_ev", "mean"),
        mean_ev_chosen=("ev_chosen", "mean"),
    ).reset_index().to_dict("records")
    n_deciles_ev_chosen_exceeds = sum(1 for r in c if r["mean_ev_chosen"] > r["mean_policy_weighted_ev"])
    print(f"  (c) calibration by decile: {c}")
    print(f"  (c) n deciles where mean ev_chosen > mean policy_weighted_ev: {n_deciles_ev_chosen_exceeds}/{len(c)}")

    # (d)
    outside = joined[~joined["restricted_ok"]]
    inside = joined[joined["restricted_ok"]]
    d = {
        "n_total": len(joined), "n_outside_restriction": len(outside),
        "share_outside_restriction": float(len(outside) / len(joined)),
        "mean_decision_outside": float(outside["decision"].mean()) if len(outside) else None,
        "mean_decision_inside": float(inside["decision"].mean()) if len(inside) else None,
    }
    print(f"  (d) {d}")

    # (e)
    crossfit_summary = json.loads(CROSSFIT_SUMMARY_PATH.read_text())
    e = crossfit_summary["oof_policy"]
    print(f"  (e) policy top1/top3 (from crossfit summary): {e}")

    summary = {
        "n_matches_crossfit": len(match_ids), "n_passes_joined": len(joined),
        "a": a, "b_by_zone": b_zone, "b_by_length": b_length, "b_by_outcome": b_outcome,
        "c_calibration_by_decile": c, "c_n_deciles_ev_chosen_exceeds": n_deciles_ev_chosen_exceeds,
        "c_n_deciles_total": len(c), "d": d, "e_policy_accuracy": e,
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
    print(f"\nWrote {SUMMARY_PATH}")
    return summary


if __name__ == "__main__":
    main()
