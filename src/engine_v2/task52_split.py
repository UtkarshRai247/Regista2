"""
Task 52, Step 2: lock the development / replication split BEFORE any tempo
computation. docs/specs/task-52-tempo-development.md. Match-level metadata
only (no events, frames or derived rows are opened).

2015/16: DEVELOPMENT = Premier League (2, 27) and Bundesliga (9, 27);
         REPLICATION = La Liga (11, 27), Serie A (12, 27), Ligue 1 (7, 27).
         Match ids from data/raw_1516/matches/<comp>_<season>.parquet.
Study sample (292 = the options_ev_v4 match files; competition/season from
data/splits/cv_folds.csv): within each competition-season, sort match ids,
permute with numpy default_rng(20260929), first floor(n/2) = DEVELOPMENT,
rest = REPLICATION. One generator is created per competition-season, in
sorted (competition_id, season_id) order.

Writes docs/splits/tempo_split.csv (dataset, competition_id, season_id,
match_id, half). Also provides dev_ids() for later Task 52 code.

Run: python src/engine_v2/task52_split.py
"""
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).parent.parent.parent
DATA = REPO / "data"
SPLIT_PATH = REPO / "docs" / "splits" / "tempo_split.csv"
SEED = 20260929
DEV_1516 = {(2, 27), (9, 27)}
REP_1516 = {(11, 27), (12, 27), (7, 27)}


def build() -> pd.DataFrame:
    rows = []
    for c, s in sorted(DEV_1516 | REP_1516):
        mids = sorted(pd.read_parquet(DATA / "raw_1516" / "matches" / f"{c}_{s}.parquet", columns=["match_id"])["match_id"].astype(int))
        half = "DEVELOPMENT" if (c, s) in DEV_1516 else "REPLICATION"
        rows += [{"dataset": "2015/16", "competition_id": c, "season_id": s, "match_id": m, "half": half} for m in mids]
    ev_mids = {int(p.stem) for p in (DATA / "processed" / "engine_v2" / "options_ev_v4").glob("*.parquet")}
    folds = pd.read_csv(DATA / "splits" / "cv_folds.csv")
    folds = folds[folds["match_id"].isin(ev_mids)]
    assert len(folds) == len(ev_mids) == 292
    for (c, s), g in sorted(folds.groupby(["competition_id", "season_id"])):
        mids = np.array(sorted(g["match_id"].astype(int)))
        perm = np.random.default_rng(SEED).permutation(mids)
        k = len(mids) // 2
        rows += [{"dataset": "study", "competition_id": int(c), "season_id": int(s), "match_id": int(m),
                  "half": "DEVELOPMENT" if i < k else "REPLICATION"} for i, m in enumerate(perm)]
    return pd.DataFrame(rows)


def dev_ids(dataset: str) -> list:
    sp = pd.read_csv(SPLIT_PATH)
    return sorted(sp.loc[(sp["dataset"] == dataset) & (sp["half"] == "DEVELOPMENT"), "match_id"].astype(int))


def main():
    df = build()
    SPLIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(SPLIT_PATH, index=False)
    print(df.groupby(["dataset", "competition_id", "season_id", "half"]).size().to_string())
    print(f"Wrote {SPLIT_PATH} ({len(df)} rows)")


if __name__ == "__main__":
    main()
