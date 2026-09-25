"""
Task 16b -- Tempo redesign, Step 3: the gate (T-2.4), unchanged.

Reuses reliability.reliability_sweep_pass_level (generic over a
dataframe of per-observation rows and a metric_fn) exactly as shipped
in Task 16 -- MOVE_ON_SPEED and HOLD_VARIATION are both pass-level
quantities, so the existing pass-level split machinery applies
unmodified. reliability.py itself is not changed.

Run: python src/tempo/redesign_reliability.py
"""
import json
import warnings
from pathlib import Path

import pandas as pd

from reliability import reliability_sweep_pass_level, classify, THRESHOLDS, GATE_THRESHOLD
from redesign_metrics import MOVE_RESID_PATH, HOLD_RESID_PATH

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
SUMMARY_PATH = DATA_DIR / "tempo_step3b_reliability.json"


def metric_move_on_speed(g: pd.DataFrame):
    return float(g["residual"].mean()) if len(g) else None


def metric_hold_variation(g: pd.DataFrame):
    return float(g["residual"].std(ddof=1)) if len(g) > 1 else None


def main():
    print("Step 3b: THE GATE for MOVE_ON_SPEED / HOLD_VARIATION ...")
    move_df = pd.read_parquet(MOVE_RESID_PATH)
    hold_df = pd.read_parquet(HOLD_RESID_PATH)

    print("  move_on_speed ...")
    rel_move = reliability_sweep_pass_level(move_df, metric_move_on_speed, THRESHOLDS)
    print("  hold_variation ...")
    rel_hold = reliability_sweep_pass_level(hold_df, metric_hold_variation, THRESHOLDS)

    all_results = {"move_on_speed": rel_move, "hold_variation": rel_hold}
    verdicts = {}
    for metric, results in all_results.items():
        median_at_200 = results[GATE_THRESHOLD]["median"]
        verdicts[metric] = {"median_reliability_at_200": median_at_200, "verdict": classify(median_at_200)}
        print(f"  {metric}: median reliability @200 = {median_at_200} -> {verdicts[metric]['verdict']}")

    summary = {"thresholds": THRESHOLDS, "results": all_results, "verdicts": verdicts}
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
    print(f"\nWrote {SUMMARY_PATH}")
    return summary


if __name__ == "__main__":
    main()
