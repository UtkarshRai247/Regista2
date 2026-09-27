"""
Task 23, Step 3 (D3): what is in the top decile of EV, corpus-wide? No
model, feature, or threshold changes -- this only measures, reusing the
EXACT seeded sample built by task23_d1.py (30 of 292 options_ev_v2
matches, seed=20260927, 50,000 rows/match, saved to
task23_d1_sample.parquet) and its own EV p90.

Describes the options with EV >= p90: distribution of destination band
(normalized x, direction-corrected per event), channel (CENTRAL =
|normalized y - 40| <= 10, WIDE = otherwise), pass distance
(distance_u), p_success, and the share that are exact teammate
positions (is_teammate_destination). Compared against the full sample.
No interpretation -- description only.

Run: python src/engine_v2/task23_d1.py  (writes the sample this reads)
     python src/engine_v2/task23_d3.py
"""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

from geometry import team_period_directions
from features import normalize_xy_arr

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
EVENTS_DIR = DATA_DIR / "raw" / "events"
SAMPLE_PATH = DATA_DIR / "processed" / "engine_v2" / "task23_d1_sample.parquet"
OUT_PATH = DATA_DIR / "engine_v2_task23_d3.json"

BANDS = [(0, 40), (40, 60), (60, 80), (80, 100), (100, 120)]


def band_of(x: float):
    for lo, hi in BANDS:
        if lo <= x < hi:
            return f"{lo}-{hi}"
    return None


def add_normalized_destination(sample: pd.DataFrame) -> pd.DataFrame:
    sample = sample.copy()
    dest_x = np.full(len(sample), np.nan)
    dest_y = np.full(len(sample), np.nan)
    for mid, g in sample.groupby("match_id"):
        events = pd.read_parquet(EVENTS_DIR / f"{mid}.parquet")
        directions = team_period_directions(events)
        for (team, period), gg in g.groupby(["team", "period"]):
            direction = directions.get((team, period), 1)
            xy = gg[["candidate_x", "candidate_y"]].values.astype(float)
            n_xy = normalize_xy_arr(xy, direction)
            dest_x[gg.index] = n_xy[:, 0]
            dest_y[gg.index] = n_xy[:, 1]
    sample["dest_x_norm"] = dest_x
    sample["dest_y_norm"] = dest_y
    sample["band"] = sample["dest_x_norm"].apply(band_of)
    sample["channel"] = np.where((sample["dest_y_norm"] - 40).abs() <= 10, "CENTRAL", "WIDE")
    return sample


def describe_group(df: pd.DataFrame) -> dict:
    return {
        "n": len(df),
        "band_distribution": df["band"].value_counts(normalize=True).to_dict(),
        "channel_distribution": df["channel"].value_counts(normalize=True).to_dict(),
        "distance_u": {"mean": float(df["distance_u"].mean()), "median": float(df["distance_u"].median()),
                        "p10": float(df["distance_u"].quantile(0.10)), "p90": float(df["distance_u"].quantile(0.90))},
        "p_success": {"mean": float(df["p_success"].mean()), "median": float(df["p_success"].median()),
                       "p10": float(df["p_success"].quantile(0.10)), "p90": float(df["p_success"].quantile(0.90))},
        "share_is_teammate_destination": float(df["is_teammate_destination"].mean()),
    }


def main():
    print("Task 23 Step 3 (D3): describing the top EV decile vs the full seeded sample ...")
    sample = pd.read_parquet(SAMPLE_PATH)
    print(f"  loaded seeded sample: {len(sample)} rows")
    sample = add_normalized_destination(sample)

    p90 = float(sample["EV"].quantile(0.90))
    top_decile = sample[sample["EV"] >= p90]
    print(f"  EV p90={p90:.5f}, top-decile rows={len(top_decile)} ({len(top_decile) / len(sample):.4f} of sample)")

    full_desc = describe_group(sample)
    top_desc = describe_group(top_decile)
    print("\n  full sample:")
    print(f"    {json.dumps(full_desc, indent=4, default=str)}")
    print("\n  top decile (EV >= p90):")
    print(f"    {json.dumps(top_desc, indent=4, default=str)}")

    summary = {"EV_p90": p90, "full_sample": full_desc, "top_decile": top_desc}
    OUT_PATH.write_text(json.dumps(summary, indent=2, default=str))
    print(f"\nWrote {OUT_PATH}")
    return summary


if __name__ == "__main__":
    main()
