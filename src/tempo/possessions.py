"""
Task 16 -- Tempo module: possession-sequence definition.

Reuses Task 11's own possession-sequence DEFINITION (open-play
possessions of >=3 eligible passes, stray opponent touches excluded via
team == possession_team) but is reimplemented directly against
passes_situation.parquet + raw events rather than by calling
task11_outcome_diagnostics.build_possessions() itself -- that function's
own first step computes the frozen (withdrawn, per D-015) per-pass
Decision table, which this module must not depend on. Same definition,
not the same code path (plan section 0).

Run standalone for a smoke check: python src/tempo/possessions.py
"""
import warnings
from pathlib import Path

import pandas as pd

from time_on_ball import parse_timestamp

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
EVENTS_DIR = DATA_DIR / "raw" / "events"
PASSES_PATH = DATA_DIR / "processed" / "passes_situation.parquet"
MIN_POSSESSION_PASSES = 3


def build_possession_sequences(verbose: bool = True) -> pd.DataFrame:
    """One row per open-play possession sequence (>=3 eligible passes):
    match_id, possession, team, n_passes, duration_s, pace
    (n_passes / duration_s, None if duration_s <= 0), passer_ids (the
    set of player_ids who made an eligible pass in this sequence)."""
    passes_elig = pd.read_parquet(PASSES_PATH, columns=["match_id", "event_id"])
    eligible_ids_by_match = passes_elig.groupby("match_id")["event_id"].apply(set).to_dict()
    match_ids = sorted(eligible_ids_by_match.keys())

    records = []
    n_zero_duration = 0
    for i, mid in enumerate(match_ids):
        ev = pd.read_parquet(EVENTS_DIR / f"{mid}.parquet")
        ev = ev.sort_values("index").reset_index(drop=True)
        ev["t"] = ev["timestamp"].apply(parse_timestamp)
        eligible_set = eligible_ids_by_match[mid]
        pp = ev[ev["id"].isin(eligible_set)].copy()
        pp = pp[pp["team"] == pp["possession_team"]]

        for poss_id, g in pp.groupby("possession"):
            if len(g) < MIN_POSSESSION_PASSES:
                continue
            g_sorted = g.sort_values("index")
            duration = float(g_sorted["t"].iloc[-1] - g_sorted["t"].iloc[0])
            pace = (len(g_sorted) / duration) if duration > 0 else None
            if duration <= 0:
                n_zero_duration += 1
            records.append({
                "match_id": mid, "possession": poss_id, "team": g_sorted["possession_team"].iloc[0],
                "n_passes": len(g_sorted), "duration_s": duration, "pace": pace,
                "passer_ids": frozenset(g_sorted["player_id"].tolist()),
            })
        if verbose and (i + 1) % 50 == 0:
            print(f"  possessions: {i + 1}/{len(match_ids)} matches")

    df = pd.DataFrame(records)
    if verbose:
        print(f"  {len(df)} possession sequences (>= {MIN_POSSESSION_PASSES} passes), "
              f"{n_zero_duration} with zero/negative duration (pace excluded, kept as None)")
    return df


if __name__ == "__main__":
    seq = build_possession_sequences()
    print(seq[["n_passes", "duration_s", "pace"]].describe())
