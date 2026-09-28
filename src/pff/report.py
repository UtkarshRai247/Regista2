"""
Task 36: summary tables for the results page from the outputs of
align.py and frames.py (no new computation on the data itself beyond
distributions and the 1.5 x IQR outlier rule for the Step 2 audit).

Run: python src/pff/report.py   (after align.py --stage clock)
"""
import json
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).parent.parent.parent / "data"
OUT_DIR = DATA_DIR / "processed" / "pff"

AUDIT_COLS = ["n_frames", "fps_implied_min", "ball_present_share", "visible_share", "estimated_share",
              "conf_HIGH", "conf_MEDIUM", "conf_LOW", "x_min", "x_max", "y_min", "y_max",
              "n_duplicate_video_time", "rows_out", "mb_out"]


def main():
    audit = json.loads((DATA_DIR / "pff_task36_audit.json").read_text())
    a = pd.DataFrame(audit.values())
    a["fps_implied_min"] = a["fps_implied_by_period"].map(lambda d: min(d.values()))
    for k in ("HIGH", "MEDIUM", "LOW"):
        a[f"conf_{k}"] = a["confidence_shares"].map(lambda d: d.get(k, 0.0))
    a["mb_out"] = a["bytes_out"] / 1e6
    print("## Step 2 audit distribution (64 matches)")
    print(a[AUDIT_COLS].describe(percentiles=[0.25, 0.5, 0.75]).T[["min", "25%", "50%", "75%", "max"]]
          .round(4).to_string())
    print("\nfps (metadata):", a["fps_meta"].value_counts().to_dict())
    print("periods:", a["periods"].map(tuple).value_counts().to_dict())
    print("frames in periods outside 1-4 (total):", int(a["n_frames_other_period"].sum()),
          "| null-clock frames:", int(a["n_frames_null_clock"].sum()))
    print("max clock deviation vs metadata startPeriod (s):", a["max_clock_dev_vs_meta_s"].max(),
          "| matches with startPeriod:", int(a["max_clock_dev_vs_meta_s"].notna().sum()))
    print("PFF shots with no tracking frame within 0.5 s:", int(a["n_pff_shots_without_frame"].sum()))
    print("rows with unmapped player:", int(a["rows_unmapped_player"].sum()))
    print(f"TOTAL rows {int(a['rows_out'].sum())}, frames {int(a['frames_out'].sum())}, "
          f"size {a['bytes_out'].sum() / 1e9:.3f} GB")

    print("\n## Outliers (outside [Q1 - 1.5 IQR, Q3 + 1.5 IQR])")
    for c in AUDIT_COLS:
        q1, q3 = a[c].quantile(0.25), a[c].quantile(0.75)
        lo, hi = q1 - 1.5 * (q3 - q1), q3 + 1.5 * (q3 - q1)
        out = a[(a[c] < lo) | (a[c] > hi)]
        if len(out):
            print(f"- {c}: " + ", ".join(f"{int(r.pff_game_id)} ({r[c]:.4g})" for _, r in out.iterrows()))

    clock = json.loads((DATA_DIR / "pff_task36_clock.json").read_text())
    cw = pd.read_csv(OUT_DIR / "crosswalk.csv").set_index("pff_game_id")
    rows = []
    for gid, c in clock["clock"].items():
        g = int(gid)
        used = clock["offsets_used"][gid]
        rows.append({"pff": g, "sb": int(cw.loc[g, "statsbomb_match_id"]),
                     "match": f"{cw.loc[g, 'pff_home']} v {cw.loc[g, 'pff_away']}",
                     "pff_shots": c["n_pff_shots"], "sb_shots": c["n_sb_shots"], "paired": c["n_paired"],
                     "median_s": c.get("median"), "iqr_s": c.get("iqr"), "spread_s": c.get("spread"),
                     "slope_s_per_min": c.get("slope_s_per_min"), "flag_gt2s": c.get("flag_spread_gt_2s"),
                     "periods_on_match_median": ",".join(p for p, v in used.items() if v["source"] != "period")})
    ct = pd.DataFrame(rows).sort_values("pff")
    print("\n## Step 3(b) clock per match")
    print(ct.round(3).to_string(index=False))
    print("\nsummary:", {"matches": len(ct), "paired_total": int(ct["paired"].sum()),
                         "pff_shots_total": int(ct["pff_shots"].sum()), "sb_shots_total": int(ct["sb_shots"].sum()),
                         "median_of_medians": float(ct["median_s"].median()),
                         "median_range": [float(ct["median_s"].min()), float(ct["median_s"].max())],
                         "n_flag_gt2s": int(ct["flag_gt2s"].sum()),
                         "slope_range": [float(ct["slope_s_per_min"].min()), float(ct["slope_s_per_min"].max())],
                         "slope_median": float(ct["slope_s_per_min"].median())})

    coord = pd.read_parquet(OUT_DIR / "shot_coordinate_check.parquet")
    print("\n## Step 3(d)", json.dumps(clock["coord_check"], indent=1))
    print("by ball visibility (median d_ball, n):",
          coord.groupby("ball_visibility")["d_ball"].agg(["median", "size"]).round(3).to_dict("index"))
    print("by shooter visibility (median d_shooter, n):",
          coord.groupby("shooter_visibility")["d_shooter"].agg(["median", "size"]).round(3).to_dict("index"))
    per_match = coord.groupby("pff_game_id")["d_ball"].median()
    print("per-match median d_ball: min/median/max", round(per_match.min(), 3), round(per_match.median(), 3),
          round(per_match.max(), 3), "| matches with median d_ball > 10:", per_match[per_match > 10].round(2).to_dict())


if __name__ == "__main__":
    main()
