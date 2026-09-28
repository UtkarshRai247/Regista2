"""
Task 26, Step 1(b): build the candidate option space + CANDIDATE_FEATURES
on the untouched holdout matches (data/raw_holdout/), reusing
`grid.process_match` UNCHANGED (the geometry fix is already baked into
`geometry.py`, applied automatically) -- the geometry/feature logic is
not duplicated. No retraining anywhere in this step; this is pure
candidate-geometry construction, not a model.

One holdout match (3845506) has an events file but no frames file
(Task 23's own recorded 360-data parse failure); `grid.process_match`
reads the frames file unconditionally, so this driver skips that one
match rather than calling `grid.main()` directly (which would crash on
it) -- disclosed, not a change to `grid.py` itself.

Run: python src/engine_v2/grid_holdout.py
"""
import json
import warnings
from pathlib import Path

import numpy as np

import grid

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
grid.EVENTS_DIR = DATA_DIR / "raw_holdout" / "events"
grid.FRAMES_DIR = DATA_DIR / "raw_holdout" / "frames"
grid.OUT_DIR = DATA_DIR / "processed" / "engine_v2" / "options_parts_holdout"
SUMMARY_PATH = DATA_DIR / "engine_v2_task26_step1b_options_holdout.json"


def main():
    print("Task 26 Step 1(b): building candidate option space on the holdout ...")
    match_ids = sorted(int(p.stem) for p in grid.EVENTS_DIR.glob("*.parquet"))
    agg = {"eligible": 0, "no_frame": 0, "too_few_visible": 0, "no_end_loc": 0,
           "n_extended_beyond_60y": 0, "option_set_sizes": [], "displacements": [], "n_rows_total": 0}
    n_skipped_no_frames_file = 0
    for i, mid in enumerate(match_ids):
        if not (grid.FRAMES_DIR / f"{mid}.parquet").exists():
            n_skipped_no_frames_file += 1
            continue
        stats, n_out = grid.process_match(mid)
        for k in ("eligible", "no_frame", "too_few_visible", "no_end_loc", "n_extended_beyond_60y"):
            agg[k] += stats[k]
        agg["option_set_sizes"].extend(stats["option_set_sizes"])
        agg["displacements"].extend(stats["displacements"])
        agg["n_rows_total"] += n_out
        if (i + 1) % 20 == 0:
            print(f"  {i + 1}/{len(match_ids)} matches, eligible so far={agg['eligible']}, rows so far={agg['n_rows_total']}")

    sizes = np.array(agg["option_set_sizes"])
    disp = np.array(agg["displacements"])
    summary = {
        "n_matches": len(match_ids), "n_skipped_no_frames_file": n_skipped_no_frames_file,
        "eligible_passes": agg["eligible"],
        "no_frame": agg["no_frame"], "too_few_visible": agg["too_few_visible"], "no_end_loc": agg["no_end_loc"],
        "n_extended_beyond_60y": agg["n_extended_beyond_60y"],
        "options_per_pass_mean": float(sizes.mean()) if len(sizes) else None,
        "options_per_pass_median": float(np.median(sizes)) if len(sizes) else None,
        "T1_median_displacement_u": float(np.median(disp)) if len(disp) else None,
        "T1_pass_condition_le_2u": bool(np.median(disp) <= 2.0) if len(disp) else None,
        "n_candidate_rows_total": agg["n_rows_total"],
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
    print(json.dumps(summary, indent=2, default=str))
    return summary


if __name__ == "__main__":
    main()
