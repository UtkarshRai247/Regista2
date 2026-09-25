"""
Task 16 -- Tempo module, Step 4: relationships (USABLE/PROVISIONAL
metrics only).

Governing document: docs/specs/analysis-plan-tempo.md section 6,
executed via docs/specs/task-16-tempo.md Step 4. Reads
player_season_metrics.parquet ONLY for its completion_pct/
progressive_passes_per_90/xa_per_90 columns -- decision_per_100/
execution_per_100/risk_per_100 are never touched, per D-015 and the
task's hard rule. position_group/name lookup are tiny, independent
reimplementations (pure string mapping / raw-event player_id-position-
name counting) so this module has no import-time dependency on
src/decision_engine/.

Run: python src/tempo/relationships.py
"""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

from metrics import OUT_PATH as METRICS_PATH

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
EVENTS_DIR = DATA_DIR / "raw" / "events"
REFERENCE_PATH = DATA_DIR / "processed" / "player_season_metrics.parquet"
RELIABILITY_PATH = DATA_DIR / "tempo_step3_reliability.json"
SUMMARY_PATH = DATA_DIR / "tempo_step4_relationships.json"

GATE_THRESHOLD = 200
TOP_BOTTOM_N = 20
COMP_NAMES = {
    (9, 281): "Bundesliga 2023/24", (43, 106): "FIFA World Cup 2022",
    (11, 90): "La Liga 2020/21", (7, 235): "Ligue 1 2022/23",
    (7, 108): "Ligue 1 2021/22", (44, 107): "MLS 2023",
    (55, 282): "UEFA Euro 2024", (55, 43): "UEFA Euro 2020",
}
METRIC_COLS = {
    "median_time_on_ball": "median_time_on_ball", "one_touch_share": "one_touch_share",
    "pressure_delta": "pressure_delta", "pace_delta": "pace_delta", "tempo_variation": "tempo_variation",
}


def position_group(pos) -> str:
    """Same mapping as task04_situation_context.position_group, reimplemented
    locally (pure string logic, no engine dependency)."""
    if pos is None or (isinstance(pos, float) and pd.isna(pos)):
        return None
    if pos == "Goalkeeper":
        return "GK"
    if "Back" in pos:
        return "Defender"
    if "Midfield" in pos:
        return "Midfielder"
    return "Forward"


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


def main():
    print("Step 4: relationships for USABLE/PROVISIONAL metrics only ...")
    verdicts = json.loads(RELIABILITY_PATH.read_text())["verdicts"]
    qualifying_metrics = [m for m, v in verdicts.items() if v["verdict"] in ("USABLE", "PROVISIONAL")]
    dropped_metrics = [m for m, v in verdicts.items() if v["verdict"] == "NOT MEASURABLE"]
    print(f"  qualifying (USABLE/PROVISIONAL): {qualifying_metrics}")
    print(f"  dropped (NOT MEASURABLE): {dropped_metrics}")

    if not qualifying_metrics:
        summary = {"status": "COMPLETE", "note": "all five metrics NOT MEASURABLE; no relationships computed",
                   "verdicts": verdicts}
        SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
        print("  No metric passed the gate -- Step 4 has nothing to compute, per T-1.3.")
        return summary

    metrics = pd.read_parquet(METRICS_PATH)
    involvements = metrics[["player_id", "competition_id", "season_id", "n_involvements"]].drop_duplicates()
    qualifying_units = involvements[involvements["n_involvements"] >= GATE_THRESHOLD]
    metrics = metrics.merge(
        qualifying_units[["player_id", "competition_id", "season_id"]], on=["player_id", "competition_id", "season_id"])
    print(f"  units meeting the {GATE_THRESHOLD}-involvement floor: {len(metrics)}")

    cols = [METRIC_COLS[m] for m in qualifying_metrics]
    corr_matrix = metrics[cols].corr().to_dict()
    print(f"  correlation matrix among qualifying metrics:\n{metrics[cols].corr().to_string()}")

    ref = pd.read_parquet(REFERENCE_PATH, columns=["player_id", "competition_id", "season_id",
                                                     "completion_pct", "progressive_passes_per_90", "xa_per_90"])
    joined = metrics.merge(ref, on=["player_id", "competition_id", "season_id"], how="left")
    public_cols = ["completion_pct", "progressive_passes_per_90", "xa_per_90"]
    corr_public = joined[cols + public_cols].corr().loc[cols, public_cols].to_dict()
    print(f"  correlation with public metrics:\n{joined[cols + public_cols].corr().loc[cols, public_cols].to_string()}")

    pos_lookup, name_lookup = build_position_and_name_lookup()
    metrics["position_group"] = metrics["player_id"].map(lambda p: position_group(pos_lookup.get(p)))
    metrics["player_name"] = metrics["player_id"].map(lambda p: name_lookup.get(p, "?"))

    comps_per_unit = metrics.groupby("player_id").apply(
        lambda g: sorted(set(COMP_NAMES.get((c, s), f"comp={c},season={s}")
                              for c, s in zip(g["competition_id"], g["season_id"])))).rename("competitions")
    metrics = metrics.merge(comps_per_unit, on="player_id", how="left")

    leaderboards = {}
    for m in qualifying_metrics:
        col = METRIC_COLS[m]
        sub = metrics.dropna(subset=[col])
        display_cols = ["player_id", "player_name", "position_group", "competitions",
                         "n_involvements", col]
        top20 = sub.nlargest(TOP_BOTTOM_N, col)[display_cols].to_dict("records")
        bottom20 = sub.nsmallest(TOP_BOTTOM_N, col)[display_cols].to_dict("records")
        leaderboards[m] = {"n_qualifying": len(sub), "top20": top20, "bottom20": bottom20}
        print(f"  {m}: {len(sub)} qualifying units")

    summary = {
        "status": "COMPLETE", "verdicts": verdicts, "qualifying_metrics": qualifying_metrics,
        "dropped_metrics": dropped_metrics, "n_units_at_200": len(metrics),
        "correlation_matrix": corr_matrix, "correlation_with_public_metrics": corr_public,
        "leaderboards": leaderboards,
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
    print(f"\nWrote {SUMMARY_PATH}")
    return summary


if __name__ == "__main__":
    main()
