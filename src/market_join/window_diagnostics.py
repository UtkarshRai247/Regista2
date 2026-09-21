"""
Task 02 follow-up diagnostic — valuation window sensitivity. Pure data-
quality check on the transfermarkt join; does not touch Decision, does
not fit anything, does not examine Decision-vs-value.

4. For units currently lost to the 90-day window: distribution of days
   from season end to the NEAREST SUBSEQUENT valuation record (strictly
   on/after season end), tournament vs league, 30-day buckets to 365.
5. Recovery counts at 120/180/270/365-day windows, tournament vs league.
6. For units that already have a 90-day valuation: how many also have a
   distinct later record within 180/365 days, and the median absolute
   change in log value between the 90-day record and the nearest
   strictly-later record within 180 days.

Run: python src/market_join/window_diagnostics.py
"""
import json
import warnings
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
MATCHES_DIR = DATA_DIR / "raw" / "matches"
METRICS_PATH = DATA_DIR / "processed" / "player_season_metrics.parquet"
CROSSWALK_PATH = DATA_DIR / "processed" / "player_crosswalk.csv"
UNITS_PATH = DATA_DIR / "processed" / "units_with_valuations.parquet"
DUCKDB_PATH = DATA_DIR / "transfermarkt-datasets.duckdb"

TOURNAMENTS = {(43, 106), (55, 282), (55, 43)}
BUCKET_EDGES = list(range(0, 366, 30)) + [10_000]


def competition_season_end_dates() -> dict:
    out = {}
    for f in MATCHES_DIR.glob("*.parquet"):
        comp_id, season_id = (int(x) for x in f.stem.split("_"))
        m = pd.read_parquet(f)
        out[(comp_id, season_id)] = pd.to_datetime(m["match_date"]).max()
    return out


def main():
    metrics = pd.read_parquet(METRICS_PATH)
    units = metrics[metrics["n_eligible_passes"] >= 200].copy()
    crosswalk = pd.read_csv(CROSSWALK_PATH)
    end_dates = competition_season_end_dates()
    units["season_end_date"] = units.apply(
        lambda r: end_dates.get((int(r["competition_id"]), int(r["season_id"]))), axis=1)
    units = units.merge(crosswalk[["player_id", "tm_player_id"]], on="player_id", how="left")
    units["is_tournament"] = units.apply(
        lambda r: (int(r["competition_id"]), int(r["season_id"])) in TOURNAMENTS, axis=1)
    matched = units[units["tm_player_id"].notna()].copy()

    con = duckdb.connect(str(DUCKDB_PATH), read_only=True)
    val = con.execute("SELECT player_id, date, market_value_in_eur FROM player_valuations").fetchdf()
    val["date"] = pd.to_datetime(val["date"])

    with_90 = pd.read_parquet(UNITS_PATH)
    with_90_keys = set(zip(with_90["player_id"], with_90["competition_id"], with_90["season_id"]))

    # ---- Section 4 & 5: units currently lost to the 90-day window ----
    lost_rows = []
    for _, u in matched.iterrows():
        key = (u["player_id"], u["competition_id"], u["season_id"])
        if key in with_90_keys:
            continue  # already has a 90-day valuation
        tmid = int(u["tm_player_id"])
        end = u["season_end_date"]
        pv = val[(val["player_id"] == tmid) & (val["date"] >= end)].sort_values("date")
        gap = int((pv.iloc[0]["date"] - end).days) if not pv.empty else None
        lost_rows.append({"is_tournament": u["is_tournament"], "gap_days": gap})

    lost_df = pd.DataFrame(lost_rows)
    print(f"Units currently lost to the 90-day window: {len(lost_df)}")
    print(f"  of which with NO subsequent valuation at all (any horizon): "
          f"{lost_df['gap_days'].isna().sum()}")

    def histogram(df, label):
        d = df.dropna(subset=["gap_days"])
        counts, _ = np.histogram(d["gap_days"], bins=BUCKET_EDGES)
        print(f"\n  {label} (n={len(d)} with a subsequent record; "
              f"{len(df) - len(d)} with none):")
        for i in range(len(BUCKET_EDGES) - 2):
            lo, hi = BUCKET_EDGES[i], BUCKET_EDGES[i + 1]
            print(f"    {lo:3d}-{hi:3d} days: {counts[i]}")
        beyond = int((d["gap_days"] >= 365).sum())
        print(f"    >365 days: {beyond}")

    print("\n=== Section 4: histogram of days-to-nearest-subsequent-valuation ===")
    histogram(lost_df[lost_df["is_tournament"]], "Tournament")
    histogram(lost_df[~lost_df["is_tournament"]], "League")

    print("\n=== Section 5: recovery counts at wider windows ===")
    recovery = {}
    for window in (120, 180, 270, 365):
        for is_t, label in ((True, "tournament"), (False, "league")):
            sub = lost_df[lost_df["is_tournament"] == is_t]
            recovered = int((sub["gap_days"] <= window).sum())
            recovery.setdefault(window, {})[label] = recovered
        print(f"  {window}-day window: tournament +{recovery[window]['tournament']}, "
              f"league +{recovery[window]['league']} "
              f"(total recovered: {recovery[window]['tournament'] + recovery[window]['league']} / {len(lost_df)})")

    # ---- Section 6: for units WITH a 90-day valuation, cost of widening ----
    has_180 = has_365 = 0
    log_changes = []
    for _, u in with_90.iterrows():
        tmid = int(u["tm_player_id"])
        end = u["season_end_date"]
        v90_date, v90_val = u["valuation_date"], u["valuation_eur"]
        pv = val[(val["player_id"] == tmid) & (val["date"] >= end)].sort_values("date")

        within_180 = pv[pv["date"] <= end + pd.Timedelta(days=180)]
        within_365 = pv[pv["date"] <= end + pd.Timedelta(days=365)]
        if len(within_180) > 0:
            has_180 += 1
        if len(within_365) > 0:
            has_365 += 1

        later = pv[pv["date"] > pd.Timestamp(v90_date)]
        later_180 = later[later["date"] <= end + pd.Timedelta(days=180)]
        if not later_180.empty:
            v180_val = later_180.iloc[0]["market_value_in_eur"]
            log_changes.append(abs(np.log(v180_val) - np.log(v90_val)))

    print(f"\n=== Section 6: cost of widening, for the {len(with_90)} units with a 90-day valuation ===")
    print(f"  Also have >=1 record within 180 days: {has_180}/{len(with_90)}")
    print(f"  Also have >=1 record within 365 days: {has_365}/{len(with_90)}")
    print(f"  Units with a DISTINCT later record appearing in the 90-180 day range: {len(log_changes)}")
    if log_changes:
        print(f"  Median |log(v180) - log(v90)| for those units: {np.median(log_changes):.4f}")
        print(f"  (as a ratio: median value change factor = {np.exp(np.median(log_changes)):.3f}x)")

    (DATA_DIR / "window_diagnostics.json").write_text(json.dumps({
        "n_lost_to_90day": len(lost_df),
        "n_lost_no_subsequent_ever": int(lost_df["gap_days"].isna().sum()),
        "recovery_by_window": recovery,
        "has_180_of_90": [has_180, len(with_90)],
        "has_365_of_90": [has_365, len(with_90)],
        "n_with_distinct_180_record": len(log_changes),
        "median_abs_log_change_90_to_180": float(np.median(log_changes)) if log_changes else None,
    }, indent=2))


if __name__ == "__main__":
    main()
