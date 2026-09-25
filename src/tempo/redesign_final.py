"""
Task 16b -- Tempo redesign, Step 4: final tempo table (T-2.5).

Every metric at USABLE or PROVISIONAL -- the three from Task 16
(median_time_on_ball, one_touch_share, pressure_delta) plus whichever
of MOVE_ON_SPEED/HOLD_VARIATION cleared the Step 3 gate -- reported per
player-season as both a raw value and a within-position-group z-score
(T-2.5: presentation, not a new metric). pressure_delta is included and
described per T-2.6 (a restatement of baseline hold time), not fixed or
excluded. The 200-involvement floor is the single gate already
established in Task 16 (each player-season's own time-on-ball
observation count), applied uniformly, per reliability.py's own
convention. Decision/Execution/Risk are never read.

Run: python src/tempo/redesign_final.py
"""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

from relationships import position_group, build_position_and_name_lookup, METRICS_PATH as TASK16_METRICS_PATH
from redesign_metrics import OUT_PATH as REDESIGN_METRICS_PATH

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
REFERENCE_PATH = DATA_DIR / "processed" / "player_season_metrics.parquet"
RELIABILITY_16_PATH = DATA_DIR / "tempo_step3_reliability.json"
RELIABILITY_16B_PATH = DATA_DIR / "tempo_step3b_reliability.json"
SUMMARY_PATH = DATA_DIR / "tempo_step4b_final.json"

GATE_THRESHOLD = 200
TOP_BOTTOM_N = 20

RAW_COL = {
    "median_time_on_ball": "median_time_on_ball", "one_touch_share": "one_touch_share",
    "pressure_delta": "pressure_delta", "move_on_speed": "move_on_speed", "hold_variation": "hold_variation",
}


def main():
    print("Step 4b: final tempo table (survivors of both gates) ...")
    v16 = json.loads(RELIABILITY_16_PATH.read_text())["verdicts"]
    v16b = json.loads(RELIABILITY_16B_PATH.read_text())["verdicts"]
    survivors = [m for m, v in v16.items() if v["verdict"] in ("USABLE", "PROVISIONAL")]
    survivors += [m for m, v in v16b.items() if v["verdict"] in ("USABLE", "PROVISIONAL")]
    dropped = [m for m, v in v16.items() if v["verdict"] == "NOT MEASURABLE"]
    print(f"  survivors: {survivors}")
    print(f"  dropped (Task 16, not rebuilt per T-2.2/T-2.3): {dropped}")

    task16 = pd.read_parquet(TASK16_METRICS_PATH)
    involvements = task16[["player_id", "competition_id", "season_id", "n_involvements"]].drop_duplicates()
    qualifying_units = involvements[involvements["n_involvements"] >= GATE_THRESHOLD]

    redesign = pd.read_parquet(REDESIGN_METRICS_PATH)
    merged = qualifying_units.merge(
        task16[["player_id", "competition_id", "season_id", "median_time_on_ball", "one_touch_share", "pressure_delta"]],
        on=["player_id", "competition_id", "season_id"], how="left")
    merged = merged.merge(
        redesign[["player_id", "competition_id", "season_id", "move_on_speed", "hold_variation"]],
        on=["player_id", "competition_id", "season_id"], how="left")
    print(f"  units meeting the {GATE_THRESHOLD}-involvement floor: {len(merged)}")

    pos_lookup, name_lookup = build_position_and_name_lookup()
    merged["position_group"] = merged["player_id"].map(lambda p: position_group(pos_lookup.get(p)))
    merged["player_name"] = merged["player_id"].map(lambda p: name_lookup.get(p, "?"))

    for m in survivors:
        col = RAW_COL[m]
        grp = merged.groupby("position_group")[col]
        merged[f"{m}_z"] = (merged[col] - grp.transform("mean")) / grp.transform("std")

    cols = [RAW_COL[m] for m in survivors]
    corr_matrix = merged[cols].corr().to_dict()
    print(f"  correlation matrix:\n{merged[cols].corr().to_string()}")

    ref = pd.read_parquet(REFERENCE_PATH, columns=["player_id", "competition_id", "season_id",
                                                     "completion_pct", "progressive_passes_per_90", "xa_per_90"])
    joined = merged.merge(ref, on=["player_id", "competition_id", "season_id"], how="left")
    public_cols = ["completion_pct", "progressive_passes_per_90", "xa_per_90"]
    corr_public = joined[cols + public_cols].corr().loc[cols, public_cols].to_dict()
    print(f"  correlation with public metrics:\n{joined[cols + public_cols].corr().loc[cols, public_cols].to_string()}")

    leaderboards = {}
    for m in survivors:
        col, zcol = RAW_COL[m], f"{m}_z"
        sub = merged.dropna(subset=[zcol])
        display_cols = ["player_id", "player_name", "position_group", col, zcol]
        top20 = sub.nlargest(TOP_BOTTOM_N, zcol)[display_cols].to_dict("records")
        bottom20 = sub.nsmallest(TOP_BOTTOM_N, zcol)[display_cols].to_dict("records")
        leaderboards[m] = {"n_qualifying": len(sub), "top20": top20, "bottom20": bottom20}
        print(f"  {m}: {len(sub)} qualifying units")

    summary = {
        "survivors": survivors, "dropped_from_task16_not_rebuilt": dropped,
        "n_units_at_200": len(merged), "correlation_matrix": corr_matrix,
        "correlation_with_public_metrics": corr_public, "leaderboards": leaderboards,
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
    print(f"\nWrote {SUMMARY_PATH}")
    return summary


if __name__ == "__main__":
    main()
