"""
Task 17 -- shared, ported infra for the outcome-validation battery
(Steps 3-5). Ported (not cross-imported) from src/decision_engine/,
same independence convention as the rest of src/engine_v2/:
  - spearman_brown: task01b_diagnostics.py's 3-line formula.
  - fit_ols: task10_partB_outcome.py's cluster-robust OLS helper,
    unchanged.
  - per_pass_reference_flags: task08_reliability_audit.py's per-pass
    completion/progressive/xA extraction, unchanged formula and
    PROGRESSIVE_THRESHOLD_M=10.0 (ported from decompose.py).
  - load_matches_meta: task04_situation_context.py's pure match-
    metadata join (home/away team+score+competition+season) -- named
    as surviving "data pipeline" infra in docs/ENGINE_AUDIT.md.
  - zone_of: the project's standing defensive/middle/final-thirds
    convention (nx<40/<80), reused verbatim.
"""
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

from geometry import team_period_directions, normalize_xy

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
EVENTS_DIR = DATA_DIR / "raw" / "events"
MATCHES_DIR = DATA_DIR / "raw" / "matches"

PROGRESSIVE_THRESHOLD_M = 10.0


def spearman_brown(r):
    if r is None or pd.isna(r):
        return None
    if r >= 1:
        return 1.0
    return (2 * r) / (1 + r)


def fit_ols(df: pd.DataFrame, y_col: str, predictors: list, cluster_col: str) -> dict:
    sub = df.dropna(subset=[y_col] + predictors + [cluster_col]).copy()
    X = sm.add_constant(sub[predictors])
    y = sub[y_col]
    model = sm.OLS(y, X.astype(float)).fit(cov_type="cluster", cov_kwds={"groups": sub[cluster_col]})
    result = {"n": int(len(sub)), "r_squared": float(model.rsquared), "coefficients": {}}
    for name in predictors:
        result["coefficients"][name] = {
            "coef": float(model.params[name]), "se": float(model.bse[name]),
            "ci_low": float(model.conf_int().loc[name, 0]), "ci_high": float(model.conf_int().loc[name, 1]),
            "p_value": float(model.pvalues[name]),
        }
    return result


def load_matches_meta() -> dict:
    meta = {}
    for f in sorted(MATCHES_DIR.glob("*.parquet")):
        comp_id, season_id = (int(x) for x in f.stem.split("_"))
        df = pd.read_parquet(f, columns=["match_id", "home_team", "away_team", "home_score", "away_score"])
        for _, r in df.iterrows():
            meta[int(r["match_id"])] = {
                "competition_id": comp_id, "season_id": season_id,
                "home_team": r["home_team"], "away_team": r["away_team"],
                "home_score": int(r["home_score"]), "away_score": int(r["away_score"]),
            }
    return meta


def zone_of(nx: float) -> str:
    return "defensive" if nx < 40 else ("middle" if nx < 80 else "final")


def match_competition_lookup() -> dict:
    """{match_id: (competition_id, season_id)}, ported from the same
    pure metadata join used throughout src/decision_engine/ and
    src/tempo/ (data/raw/matches/{comp}_{season}.parquet filenames)."""
    lookup = {}
    for f in MATCHES_DIR.glob("*.parquet"):
        comp_id, season_id = f.stem.split("_")
        matches = pd.read_parquet(f, columns=["match_id"])
        for mid in matches["match_id"]:
            lookup[int(mid)] = (int(comp_id), int(season_id))
    return lookup


def per_pass_reference_flags(match_id: int) -> pd.DataFrame:
    """Per-pass completion/progressive/xA over ALL of a match's Pass
    events (not restricted to the eligible/candidate population) --
    the caller inner-joins to whichever eligible-pass population it
    needs, exactly as v1's task10_partB_outcome.add_reference_rates
    does against passes_situation.parquet."""
    ev = pd.read_parquet(EVENTS_DIR / f"{match_id}.parquet")
    ev = ev.sort_values("index").reset_index(drop=True)
    directions = team_period_directions(ev)
    passes = ev[ev["type"] == "Pass"].copy()
    xa_by_shot = ev[ev["type"] == "Shot"].set_index("id")["shot_statsbomb_xg"]

    records = []
    for _, r in passes.iterrows():
        if pd.isna(r["player_id"]):
            continue
        loc, end_loc = r["location"], r["pass_end_location"]
        progressive = False
        if (loc is not None and end_loc is not None
                and not (isinstance(loc, float) and pd.isna(loc))
                and not (isinstance(end_loc, float) and pd.isna(end_loc))
                and pd.isna(r.get("pass_outcome"))):
            direction = directions.get((r["team"], r["period"]), 1)
            sx, _ = normalize_xy(loc[0], loc[1], direction)
            ex, _ = normalize_xy(end_loc[0], end_loc[1], direction)
            progressive = (ex - sx) >= PROGRESSIVE_THRESHOLD_M

        xa = 0.0
        if r.get("pass_shot_assist") and pd.notna(r.get("pass_assisted_shot_id")):
            raw_xa = xa_by_shot.get(r["pass_assisted_shot_id"], 0.0)
            xa = float(raw_xa) if pd.notna(raw_xa) else 0.0

        records.append({
            "match_id": match_id, "event_id": r["id"], "team": r["team"], "player_id": r["player_id"],
            "complete": bool(pd.isna(r.get("pass_outcome"))),
            "progressive": bool(progressive), "xa": xa,
        })
    return pd.DataFrame(records)
