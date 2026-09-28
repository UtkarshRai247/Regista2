"""
Task 26, Step 3: player-level threshold by reliability (fixed rule).
Reuses `step8_regate.py`'s own `reliability_sweep` function unchanged on
`pass_der_v8.parquet`'s `decision_new` (engine v5's Decision), at
thresholds 100/150/200/250/300/400/500.

RULE (fixed by the brief, not chosen by looking at any ranking): the
threshold is the LOWEST at which median reliability reaches 0.70. If
none does, use 200 and mark every player-level result PROVISIONAL with
its reliability inline.

Run: python src/engine_v2/task26_step3_threshold.py
"""
import json
import warnings
from pathlib import Path

import pandas as pd

from step8_regate import reliability_sweep, THRESHOLDS, GATE_THRESHOLD

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
PASS_DER_V8_PATH = DATA_DIR / "processed" / "engine_v2" / "pass_der_v8.parquet"
SUMMARY_PATH = DATA_DIR / "engine_v2_task26_step3_threshold.json"

USABLE_BAR = 0.70


def main():
    print("Task 26 Step 3: player-level threshold by reliability ...")
    per_pass = pd.read_parquet(PASS_DER_V8_PATH, columns=["player_id", "competition_id", "season_id", "decision_new"])
    rel = reliability_sweep(per_pass, "decision_new", THRESHOLDS)
    for th, r in rel.items():
        print(f"  {th}: n_units={r['n_units']}, median={r['median']}")

    chosen_threshold = None
    for th in THRESHOLDS:
        if rel[th]["median"] is not None and rel[th]["median"] >= USABLE_BAR:
            chosen_threshold = th
            break

    if chosen_threshold is not None:
        provisional = False
        print(f"\n  Lowest threshold with median reliability >= {USABLE_BAR}: {chosen_threshold} "
              f"(median={rel[chosen_threshold]['median']:.4f})")
    else:
        chosen_threshold = GATE_THRESHOLD
        provisional = True
        print(f"\n  No threshold reaches {USABLE_BAR} -- using {chosen_threshold} (PROVISIONAL), "
              f"median reliability={rel[chosen_threshold]['median']}")

    summary = {
        "reliability_by_threshold": rel, "usable_bar": USABLE_BAR,
        "chosen_threshold": chosen_threshold, "chosen_threshold_reliability": rel[chosen_threshold]["median"],
        "provisional": provisional,
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
    print(f"\nWrote {SUMMARY_PATH}")
    return summary


if __name__ == "__main__":
    main()
