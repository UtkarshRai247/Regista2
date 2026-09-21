"""
Task 02/03 — attach valuations. Parameterized (Task 03) so the same
logic serves the 90-day (Task 02 / robustness variant a), 180-day
(Amendment 2 primary), and any pass-threshold variant without
duplicating code.

For each unit: the valuation record dated within +window_days of the
competition-season end date (earliest if several), plus the record
closest to +12 months after that date for the H3 secondary analysis.

Run: python src/market_join/valuations.py [--window-days N]
    [--min-passes N] [--crosswalk PATH] [--out PATH]
"""
import argparse
import json
import warnings
from pathlib import Path

import duckdb
import pandas as pd

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
MATCHES_DIR = DATA_DIR / "raw" / "matches"
METRICS_PATH = DATA_DIR / "processed" / "player_season_metrics.parquet"
DUCKDB_PATH = DATA_DIR / "transfermarkt-datasets.duckdb"

COMP_NAMES = {
    (9, 281): "Bundesliga 23/24", (43, 106): "WC2022", (11, 90): "La Liga 20/21",
    (7, 235): "Ligue1 22/23", (7, 108): "Ligue1 21/22", (44, 107): "MLS 2023",
    (55, 282): "Euro2024", (55, 43): "Euro2020",
}


def competition_season_end_dates() -> dict:
    out = {}
    for f in MATCHES_DIR.glob("*.parquet"):
        comp_id, season_id = (int(x) for x in f.stem.split("_"))
        m = pd.read_parquet(f)
        out[(comp_id, season_id)] = pd.to_datetime(m["match_date"]).max()
    return out


def run(window_days: int, min_passes: int, crosswalk_path: Path, out_path: Path) -> dict:
    metrics = pd.read_parquet(METRICS_PATH)
    units = metrics[metrics["n_eligible_passes"] >= min_passes].copy()
    crosswalk = pd.read_csv(crosswalk_path)

    end_dates = competition_season_end_dates()
    units["season_end_date"] = units.apply(
        lambda r: end_dates.get((int(r["competition_id"]), int(r["season_id"]))), axis=1)

    units = units.merge(
        crosswalk[["player_id", "tm_player_id", "match_method"]], on="player_id", how="left")

    matched = units[units["tm_player_id"].notna()].copy()
    n_crosswalk_failed = len(units) - len(matched)

    con = duckdb.connect(str(DUCKDB_PATH), read_only=True)
    valuations = con.execute(
        "SELECT player_id, date, market_value_in_eur FROM player_valuations"
    ).fetchdf()
    valuations["date"] = pd.to_datetime(valuations["date"])

    rows = []
    n_no_valuation = 0
    for _, u in matched.iterrows():
        tmid = int(u["tm_player_id"])
        end = u["season_end_date"]
        pv = valuations[valuations["player_id"] == tmid].sort_values("date")

        window = pv[(pv["date"] >= end) & (pv["date"] <= end + pd.Timedelta(days=window_days))]
        if window.empty:
            n_no_valuation += 1
            continue
        primary = window.iloc[0]  # earliest within window

        target_12mo = end + pd.Timedelta(days=365)
        pv["gap_12mo"] = (pv["date"] - target_12mo).abs()
        h3 = pv.loc[pv["gap_12mo"].idxmin()] if not pv.empty else None

        row = u.to_dict()
        row["valuation_date"] = primary["date"]
        row["valuation_eur"] = primary["market_value_in_eur"]
        row["valuation_gap_days"] = (primary["date"] - end).days
        row["days_to_valuation"] = (primary["date"] - end).days
        if h3 is not None:
            row["valuation_12mo_date"] = h3["date"]
            row["valuation_12mo_eur"] = h3["market_value_in_eur"]
            row["valuation_12mo_gap_days"] = (h3["date"] - target_12mo).days
        rows.append(row)

    result = pd.DataFrame(rows)
    result.to_parquet(out_path)

    matched_ids = set(zip(result["player_id"], result["competition_id"], result["season_id"])) \
        if not result.empty else set()
    missing = matched[~matched.apply(
        lambda r: (r["player_id"], r["competition_id"], r["season_id"]) in matched_ids, axis=1)]
    missing_by_comp = missing.apply(
        lambda r: COMP_NAMES.get((int(r["competition_id"]), int(r["season_id"]))), axis=1
    ).value_counts().to_dict() if not missing.empty else {}

    return {
        "window_days": window_days, "min_passes": min_passes,
        "units_after_threshold": len(units),
        "crosswalk_failed": n_crosswalk_failed,
        f"no_valuation_in_{window_days}day_window": n_no_valuation,
        "no_valuation_by_competition": missing_by_comp,
        "units_with_valuation": len(result),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--window-days", type=int, default=90)
    ap.add_argument("--min-passes", type=int, default=200)
    ap.add_argument("--crosswalk", type=str,
                     default=str(DATA_DIR / "processed" / "player_crosswalk.csv"))
    ap.add_argument("--out", type=str,
                     default=str(DATA_DIR / "processed" / "units_with_valuations.parquet"))
    args = ap.parse_args()

    summary = run(args.window_days, args.min_passes, Path(args.crosswalk), Path(args.out))
    print(json.dumps(summary, indent=2, default=str))
    (DATA_DIR / f"valuations_summary_{args.window_days}d_{args.min_passes}p.json").write_text(
        json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
