"""
Task 02 — Step 4: build controls for the primary model.

- Age at competition-season end, from transfermarkt date_of_birth.
- Position group: StatsBomb's ~20 granular labels collapsed to
  Defender/Midfielder/Forward (goalkeepers are already excluded by
  construction — Step 1 of the decision engine never generates eligible
  passes for a goalkeeper passer). The exact grouping isn't specified in
  the brief; stated here, not silently assumed.
- Minutes/completion%/progressive-passes-per-90 already in
  player_season_metrics.parquet. Goals+assists/90 computed fresh here
  from the raw event data (not previously computed).
- Tournament-vs-league indicator: direct lookup over the 8 known
  competition-seasons.
- Club strength: median market value of team-mates at the valuation
  date, excluding the player. No dedicated "squad as of date" table
  exists in transfermarkt-datasets (confirmed in planning research) —
  approximated via the `appearances` table: team-mates are players with
  an appearance for the same club within +/-90 days of the valuation
  date, and their own valuation is the nearest one within +/-180 days.
  Flagged plainly as an approximation, per the spec's own request to
  note this control shares its source with the outcome.
- Contract expiry: reported directly from `players.contract_expiration_date`.

Run: python src/market_join/controls.py
"""
import argparse
import json
import warnings
from pathlib import Path

import duckdb
import pandas as pd

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
EVENTS_DIR = DATA_DIR / "raw" / "events"
MATCHES_DIR = DATA_DIR / "raw" / "matches"
UNITS_PATH = DATA_DIR / "processed" / "units_with_valuations.parquet"
DUCKDB_PATH = DATA_DIR / "transfermarkt-datasets.duckdb"
OUT_PATH = DATA_DIR / "processed" / "market_join_analysis_sample.parquet"
DEFAULT_UNITS_PATH = UNITS_PATH
DEFAULT_OUT_PATH = OUT_PATH

TOURNAMENTS = {(43, 106), (55, 282), (55, 43)}  # WC2022, Euro2024, Euro2020

POSITION_GROUP = {
    "Goalkeeper": "Goalkeeper",
    "Center Back": "Defender", "Left Center Back": "Defender", "Right Center Back": "Defender",
    "Left Back": "Defender", "Right Back": "Defender",
    "Left Wing Back": "Defender", "Right Wing Back": "Defender",
    "Center Defensive Midfield": "Midfielder", "Left Defensive Midfield": "Midfielder",
    "Right Defensive Midfield": "Midfielder", "Center Midfield": "Midfielder",
    "Left Center Midfield": "Midfielder", "Right Center Midfield": "Midfielder",
    "Center Attacking Midfield": "Midfielder", "Left Attacking Midfield": "Midfielder",
    "Right Attacking Midfield": "Midfielder",
    "Left Wing": "Forward", "Right Wing": "Forward", "Center Forward": "Forward",
    "Left Center Forward": "Forward", "Right Center Forward": "Forward",
    "Secondary Striker": "Forward",
}


def mode_positions() -> dict:
    pos_counts = {}
    for f in EVENTS_DIR.glob("*.parquet"):
        ev = pd.read_parquet(f, columns=["player_id", "position"])
        sub = ev.dropna(subset=["player_id", "position"])
        for pid, pos in zip(sub["player_id"], sub["position"]):
            pos_counts.setdefault(pid, {}).setdefault(pos, 0)
            pos_counts[pid][pos] += 1
    return {pid: max(counts, key=counts.get) for pid, counts in pos_counts.items()}


def goals_assists_per_season() -> pd.DataFrame:
    # StatsBomb's per-match parquet only includes columns that appear at
    # least once in that match (e.g. no pass_goal_assist column at all if
    # no assisted goal happened) — read full files, access defensively.
    rows = []
    for f in EVENTS_DIR.glob("*.parquet"):
        mid = int(f.stem)
        ev = pd.read_parquet(f)
        goals = ev[(ev["type"] == "Shot") & (ev["shot_outcome"] == "Goal")]
        assists = ev[ev["pass_goal_assist"] == True] if "pass_goal_assist" in ev.columns \
            else ev.iloc[0:0]
        for pid, n in goals["player_id"].value_counts().items():
            rows.append({"match_id": mid, "player_id": pid, "goals": n, "assists": 0})
        for pid, n in assists["player_id"].value_counts().items():
            rows.append({"match_id": mid, "player_id": pid, "goals": 0, "assists": n})
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    return df.groupby(["match_id", "player_id"]).sum().reset_index()


def club_strength(con, tm_player_id: int, val_date, exclude_player=True):
    club_row = con.execute(
        "SELECT player_club_id FROM appearances WHERE player_id = ? "
        "ORDER BY ABS(date_diff('day', date, ?)) ASC LIMIT 1",
        [tm_player_id, val_date],
    ).fetchone()
    if not club_row or club_row[0] is None:
        return None, None
    club_id = club_row[0]

    teammates = con.execute(
        "SELECT DISTINCT player_id FROM appearances "
        "WHERE player_club_id = ? AND ABS(date_diff('day', date, ?)) <= 90",
        [club_id, val_date],
    ).fetchdf()["player_id"].tolist()
    if exclude_player and tm_player_id in teammates:
        teammates.remove(tm_player_id)
    if not teammates:
        return None, club_id

    vals = []
    for pid in teammates:
        v = con.execute(
            "SELECT market_value_in_eur FROM player_valuations WHERE player_id = ? "
            "AND ABS(date_diff('day', date, ?)) <= 180 "
            "ORDER BY ABS(date_diff('day', date, ?)) ASC LIMIT 1",
            [pid, val_date, val_date],
        ).fetchone()
        if v and v[0] is not None:
            vals.append(v[0])
    if not vals:
        return None, club_id
    return float(pd.Series(vals).median()), club_id


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--units", type=str, default=str(DEFAULT_UNITS_PATH))
    ap.add_argument("--out", type=str, default=str(DEFAULT_OUT_PATH))
    args = ap.parse_args()
    units_path, out_path = Path(args.units), Path(args.out)

    units = pd.read_parquet(units_path)
    con = duckdb.connect(str(DUCKDB_PATH), read_only=True)
    players = con.execute(
        "SELECT player_id, date_of_birth, contract_expiration_date FROM players"
    ).fetchdf()

    pos_map = mode_positions()
    ga = goals_assists_per_season()

    match_comp = {}
    for f in MATCHES_DIR.glob("*.parquet"):
        comp_id, season_id = (int(x) for x in f.stem.split("_"))
        for mid in pd.read_parquet(f, columns=["match_id"])["match_id"]:
            match_comp[int(mid)] = (comp_id, season_id)
    ga["competition_id"] = ga["match_id"].map(lambda m: match_comp.get(m, (None, None))[0])
    ga["season_id"] = ga["match_id"].map(lambda m: match_comp.get(m, (None, None))[1])
    ga_agg = ga.groupby(["player_id", "competition_id", "season_id"]).agg(
        goals=("goals", "sum"), assists=("assists", "sum")
    ).reset_index()

    units["position"] = units["player_id"].map(pos_map)
    units["position_group"] = units["position"].map(POSITION_GROUP)
    units["is_tournament"] = units.apply(
        lambda r: (int(r["competition_id"]), int(r["season_id"])) in TOURNAMENTS, axis=1)

    units = units.merge(ga_agg, on=["player_id", "competition_id", "season_id"], how="left")
    units["goals"] = units["goals"].fillna(0)
    units["assists"] = units["assists"].fillna(0)
    units["goals_assists_per_90"] = (units["goals"] + units["assists"]) / (units["minutes_played"] / 90)

    units = units.merge(players, left_on="tm_player_id", right_on="player_id",
                         suffixes=("", "_tm"), how="left")
    units["date_of_birth"] = pd.to_datetime(units["date_of_birth"])
    units["age_at_season_end"] = (
        (pd.to_datetime(units["season_end_date"]) - units["date_of_birth"]).dt.days / 365.25
    )
    units["has_contract_expiry"] = units["contract_expiration_date"].notna()

    club_strengths, club_ids = [], []
    for _, u in units.iterrows():
        cs, cid = club_strength(con, int(u["tm_player_id"]), u["valuation_date"])
        club_strengths.append(cs)
        club_ids.append(cid)
    units["club_strength_eur"] = club_strengths
    units["club_id_at_valuation"] = club_ids

    n_no_club_strength = units["club_strength_eur"].isna().sum()
    n_missing_age = units["age_at_season_end"].isna().sum()

    final = units[units["club_strength_eur"].notna() & units["age_at_season_end"].notna()].copy()
    final.to_parquet(out_path)

    summary = {
        "units_with_valuation": len(units),
        "no_club_strength": int(n_no_club_strength),
        "missing_age": int(n_missing_age),
        "final_unit_count": len(final),
        "distinct_players": int(final["player_id"].nunique()),
        "contract_expiry_populated_rate": float(final["has_contract_expiry"].mean()),
    }
    print(json.dumps(summary, indent=2, default=str))
    (DATA_DIR / f"controls_summary_{out_path.stem}.json").write_text(
        json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
