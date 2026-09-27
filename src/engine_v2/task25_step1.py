"""
Task 25, Step 1: is Task 24's G1 residual (2.30% of band 0-40
in-possession rows flagged "beyond the defensive line") visibility, or
a remaining coordinate error? No engine code is changed here -- this
only measures, using `value_model_rows_diagnostic_v5.parquet` (Task
24's rebuilt rows) plus a direct re-read of each affected event's own
360 frame to count VISIBLE OPPONENTS (not stored as its own column in
the diagnostic file; `n_visible_players` there is teammates+opponents+
actor combined).

(a) G1 share (beyond line) by visible-opponent-count bin: 0-3, 4-6,
    7-9, 10-11, restricted to band 0-40, in-possession rows.
(b) G1 share restricted to frames with >=10 visible opponents (R4's
    own K).
(c) For the residual beyond-line rows: median defensive_line_x, and
    the share with fewer than 10 visible opponents.
(d) Per team-period, the share of its band-0-40 rows that are
    beyond-line; the 10 highest (n>=1), plus which of those have
    n>=50 rows (the brief's own minimum for the decision rule).

DECISION (fixed by the brief, not chosen here): residual attributed to
visibility, continue to Step 2, if (b) < 1% AND no team-period with
n>=50 rows in (d) exceeds 20% beyond-line share.

Run: python src/engine_v2/task25_step1.py
"""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
EVENTS_DIR = DATA_DIR / "raw" / "events"
FRAMES_DIR = DATA_DIR / "raw" / "frames"
DIAGNOSTIC_PATH = DATA_DIR / "processed" / "engine_v2" / "value_model_rows_diagnostic_v5.parquet"
OUT_PATH = DATA_DIR / "engine_v2_task25_step1.json"

OPP_BINS = [(0, 3), (4, 6), (7, 9), (10, 11)]


def count_visible_opponents_and_period(band040: pd.DataFrame) -> tuple:
    """For every (match_id, event_id) in band040, count opponents
    (teammate==False) in that event's own 360 frame, and look up its
    `period` (not a column in the diagnostic file)."""
    n_opp = pd.Series(index=band040.index, dtype="float64")
    period = pd.Series(index=band040.index, dtype="float64")
    for mid, g in band040.groupby("match_id"):
        frames = pd.read_parquet(FRAMES_DIR / f"{mid}.parquet")
        opp_counts = frames[frames["teammate"] == False].groupby("id").size()
        n_opp.loc[g.index] = g["event_id"].map(opp_counts).values
        events = pd.read_parquet(EVENTS_DIR / f"{mid}.parquet", columns=["id", "period"])
        period_lookup = events.set_index("id")["period"]
        period.loc[g.index] = g["event_id"].map(period_lookup).values
    return n_opp.fillna(0).astype(int), period.astype(int)


def bin_of(n: int) -> str:
    for lo, hi in OPP_BINS:
        if lo <= n <= hi:
            return f"{lo}-{hi}"
    return "12+"


def main():
    print("Task 25 Step 1: visibility vs remaining coordinate error, band 0-40 ...")
    diag = pd.read_parquet(DIAGNOSTIC_PATH)
    in_poss = diag[diag["in_possession"]].copy()
    band040 = in_poss[(in_poss["ball_x"] >= 0) & (in_poss["ball_x"] < 40)].copy()
    band040["ball_beyond_defensive_line"] = band040["ball_beyond_defensive_line"].fillna(False).astype(bool)
    print(f"  band 0-40, in-possession rows: {len(band040)}")

    print("  counting visible opponents per event (re-reading 360 frames) and looking up period ...")
    band040["n_visible_opponents"], band040["period"] = count_visible_opponents_and_period(band040)
    band040["opp_bin"] = band040["n_visible_opponents"].apply(bin_of)

    print("\n  (a) G1 share by visible-opponent-count bin ...")
    a_rows = []
    for lo, hi in OPP_BINS:
        label = f"{lo}-{hi}"
        sub = band040[band040["opp_bin"] == label]
        n = len(sub)
        n_beyond = int(sub["ball_beyond_defensive_line"].sum())
        share = n_beyond / n if n else None
        a_rows.append({"opp_bin": label, "n": n, "n_beyond_line": n_beyond, "share_beyond_line": share})
        print(f"    {a_rows[-1]}")
    sub_12plus = band040[band040["opp_bin"] == "12+"]
    if len(sub_12plus):
        n = len(sub_12plus)
        n_beyond = int(sub_12plus["ball_beyond_defensive_line"].sum())
        a_rows.append({"opp_bin": "12+", "n": n, "n_beyond_line": n_beyond, "share_beyond_line": n_beyond / n})
        print(f"    {a_rows[-1]} (unexpected -- more than 11 opponents visible; reported for completeness)")

    print("\n  (b) G1 share restricted to frames with >=10 visible opponents ...")
    ge10 = band040[band040["n_visible_opponents"] >= 10]
    n_ge10 = len(ge10)
    n_beyond_ge10 = int(ge10["ball_beyond_defensive_line"].sum())
    share_ge10 = n_beyond_ge10 / n_ge10 if n_ge10 else None
    b_result = {"n_rows_ge10_visible_opponents": n_ge10, "n_beyond_line": n_beyond_ge10, "share_beyond_line": share_ge10}
    print(f"    {b_result}")

    print("\n  (c) residual beyond-line rows: median defensive_line_x, share with <10 visible opponents ...")
    residual = band040[band040["ball_beyond_defensive_line"]]
    c_result = {
        "n_residual_rows": len(residual),
        "median_defensive_line_x": float(residual["defensive_line_x"].median()) if len(residual) else None,
        "share_lt_10_visible_opponents": float((residual["n_visible_opponents"] < 10).mean()) if len(residual) else None,
    }
    print(f"    {c_result}")

    print("\n  (d) per team-period, share of band-0-40 rows beyond-line, top 10 ...")
    tp = band040.groupby(["team", "period"]).agg(
        n=("ball_beyond_defensive_line", "size"), n_beyond=("ball_beyond_defensive_line", "sum")).reset_index()
    tp["share_beyond_line"] = tp["n_beyond"] / tp["n"]
    tp_top10 = tp.sort_values("share_beyond_line", ascending=False).head(10)
    d_rows = tp_top10.to_dict("records")
    for r in d_rows:
        print(f"    {r}")

    tp_n50 = tp[tp["n"] >= 50]
    max_share_n50 = float(tp_n50["share_beyond_line"].max()) if len(tp_n50) else None
    print(f"\n  team-periods with n>=50 band-0-40 rows: {len(tp_n50)}, max share_beyond_line among them: {max_share_n50}")

    decision_b_pass = share_ge10 is not None and share_ge10 < 0.01
    decision_d_pass = max_share_n50 is None or max_share_n50 <= 0.20
    decision = decision_b_pass and decision_d_pass
    print(f"\n  DECISION: (b)<1% -> {decision_b_pass} (share={share_ge10}); "
          f"no n>=50 team-period exceeds 20% -> {decision_d_pass} (max={max_share_n50})")
    print(f"  {'VISIBILITY -- continue to Step 2' if decision else 'REMAINING COORDINATE ERROR -- STOP after Step 1'}")

    summary = {
        "n_band040_in_possession": len(band040),
        "a_by_opponent_bin": a_rows,
        "b_ge10_visible_opponents": b_result,
        "c_residual_rows": c_result,
        "d_top10_team_periods": d_rows,
        "n_team_periods_ge50_rows": len(tp_n50),
        "max_share_beyond_line_among_n_ge50": max_share_n50,
        "decision_b_lt_1pct": decision_b_pass,
        "decision_d_no_tp_over_20pct": decision_d_pass,
        "decision_visibility_continue_to_step2": decision,
    }
    OUT_PATH.write_text(json.dumps(summary, indent=2, default=str))
    print(f"\nWrote {OUT_PATH}")
    return summary


if __name__ == "__main__":
    main()
