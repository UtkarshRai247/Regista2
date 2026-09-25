"""
Task 16b -- Tempo redesign, Step 2: MOVE_ON_SPEED and HOLD_VARIATION
(Amendment T-2.3). One attempt, pre-specified construction; pace_delta
and tempo_variation are not patched, they are replaced.

Both metrics are built from tempo_time_on_ball.parquet's existing
population (ALL open-play passes with a resolvable receipt chain,
209,775 rows -- never passes_situation.parquet's matched subset).

Direction inference + zone classification (defensive/middle/final
thirds, thresholds nx<40/<80 on a 120-length pitch) reuse the project's
existing convention (task04_situation_context.py / pitch_direction.py)
but are reimplemented locally -- pure geometry, ported faithfully --
so src/tempo/ keeps zero import-time dependency on src/decision_engine/,
consistent with Task 16's own convention for position_group,
match_competition_lookup and spearman_brown.

Fixed effects for (match_id, team) are absorbed by exact group-mean
demeaning (the Frisch-Waugh-Lovell "within" transformation) rather than
~600 dummy columns -- identical residuals, much cheaper.

Run: python src/tempo/redesign_metrics.py
"""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

from time_on_ball import is_open_play_pass, parse_timestamp, OUT_PATH as TIME_ON_BALL_PATH

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
EVENTS_DIR = DATA_DIR / "raw" / "events"
OUT_PATH = DATA_DIR / "processed" / "tempo_redesign_metrics.parquet"
MOVE_RESID_PATH = DATA_DIR / "processed" / "tempo_redesign_move_residuals.parquet"
HOLD_RESID_PATH = DATA_DIR / "processed" / "tempo_redesign_hold_residuals.parquet"
SUMMARY_PATH = DATA_DIR / "tempo_step2b_redesign.json"

PITCH_X, PITCH_Y = 120.0, 80.0
ZONE_CATEGORIES = ["defensive", "middle", "final"]


def team_period_directions(events: pd.DataFrame) -> dict:
    """Ported from src/decision_engine/pitch_direction.py (pure shot-
    location geometry, no option/value-model dependency), reimplemented
    locally rather than imported, per this module's independence goal."""
    teams = [t for t in events["team"].dropna().unique().tolist()]
    periods = sorted(events["period"].dropna().unique().tolist())
    shots = events[events["type"] == "Shot"]
    directions = {}
    period1_dir = None
    for period in periods:
        pshots = shots[shots["period"] == period]
        means = {}
        for t in teams:
            tshots = pshots[pshots["team"] == t]
            locs = [loc[0] for loc in tshots["location"] if loc is not None
                    and not (isinstance(loc, float) and pd.isna(loc))]
            if locs:
                means[t] = sum(locs) / len(locs)
        if len(means) >= 2:
            ordered = sorted(means, key=means.get)
            directions[(ordered[0], period)] = -1
            directions[(ordered[1], period)] = 1
        elif len(means) == 1:
            known_team = next(iter(means))
            other = [t for t in teams if t != known_team]
            directions[(known_team, period)] = 1 if means[known_team] > PITCH_X / 2 else -1
            if other:
                directions[(other[0], period)] = -directions[(known_team, period)]
        else:
            if period1_dir is not None and len(teams) == 2:
                flip = -1 if period % 2 == 0 else 1
                directions[(teams[0], period)] = period1_dir[teams[0]] * flip
                directions[(teams[1], period)] = period1_dir[teams[1]] * flip
            else:
                directions[(teams[0], period)] = 1
                if len(teams) > 1:
                    directions[(teams[1], period)] = -1
        if period == 1:
            period1_dir = {t: directions.get((t, 1), 1) for t in teams}
    return directions


def zone_of(nx: float) -> str:
    return "defensive" if nx < 40 else ("middle" if nx < 80 else "final")


def build_match_frame(mid: int) -> pd.DataFrame:
    """One row per open-play pass in the match, with the interval to
    the team's next open-play pass in the same possession (index-
    ordered), zone, and pass_length."""
    ev = pd.read_parquet(EVENTS_DIR / f"{mid}.parquet")
    ev = ev.sort_values("index").reset_index(drop=True)
    ev["t"] = ev["timestamp"].apply(parse_timestamp)
    op = ev[is_open_play_pass(ev)].copy()
    if op.empty:
        return pd.DataFrame()

    directions = team_period_directions(ev)
    loc = op["location"].tolist()
    op["loc_x"] = [l[0] if isinstance(l, (list, np.ndarray)) else np.nan for l in loc]
    op["loc_y"] = [l[1] if isinstance(l, (list, np.ndarray)) else np.nan for l in loc]
    op["direction"] = [directions.get((t, p), 1) for t, p in zip(op["team"], op["period"])]
    op["nx"] = np.where(op["direction"] == 1, op["loc_x"], PITCH_X - op["loc_x"])
    op["zone"] = op["nx"].apply(lambda nx: zone_of(nx) if pd.notna(nx) else None)

    op = op.sort_values("index")
    grp = list(zip(op["possession"], op["team"]))
    op["grp"] = grp
    next_t = op.groupby("grp")["t"].shift(-1)
    op["interval"] = next_t - op["t"]
    op["is_last_in_group"] = next_t.isna()

    op["match_id"] = mid
    op["event_id"] = op["id"]
    return op[["match_id", "event_id", "team", "zone", "pass_length",
               "interval", "is_last_in_group"]]


def demeaned_residuals(df: pd.DataFrame, y_col: str, x_cols: list, group_cols: list) -> np.ndarray:
    """Exact within-group (Frisch-Waugh-Lovell) residuals for
    y ~ x_cols, absorbing group_cols as fixed effects via group-mean
    demeaning instead of dummy columns."""
    g = df.groupby(group_cols)
    y_dm = df[y_col] - g[y_col].transform("mean")
    X_dm = df[x_cols].copy()
    for c in x_cols:
        X_dm[c] = df[c] - g[c].transform("mean")
    model = sm.OLS(y_dm.astype(float), X_dm.astype(float)).fit()
    return model.resid.values, model.rsquared


def main():
    print("Step 2b: building MOVE_ON_SPEED / HOLD_VARIATION (T-2.3) ...")
    tob = pd.read_parquet(TIME_ON_BALL_PATH)
    match_ids = sorted(tob["match_id"].unique())

    frames = []
    for i, mid in enumerate(match_ids):
        frames.append(build_match_frame(mid))
        if (i + 1) % 50 == 0:
            print(f"  {i + 1}/{len(match_ids)} matches")
    op_all = pd.concat(frames, ignore_index=True)

    n_last = int(op_all["is_last_in_group"].sum())
    joined = tob.merge(op_all, on=["match_id", "event_id", "team"], how="inner", suffixes=("", "_op"))
    print(f"  resolved population joined to open-play stream: {len(joined)}/{len(tob)} rows")

    n_dropped_last = int(joined["is_last_in_group"].sum())
    move_df = joined[~joined["is_last_in_group"]].copy()
    n_nonpositive = int((move_df["interval"] <= 0).sum())
    move_df = move_df[move_df["interval"] > 0]
    move_df = move_df.dropna(subset=["zone", "pass_length"])
    move_df["log_interval"] = np.log(move_df["interval"])
    print(f"  MOVE_ON_SPEED: dropped {n_dropped_last} last-of-group passes (of {len(joined)}), "
          f"{n_nonpositive} non-positive intervals; {len(move_df)} remain")

    zone_dummies = pd.get_dummies(pd.Categorical(move_df["zone"], categories=ZONE_CATEGORIES),
                                   drop_first=True).astype(float)
    zone_dummies.columns = [f"zone_{c}" for c in zone_dummies.columns]
    move_df = pd.concat([move_df.reset_index(drop=True), zone_dummies.reset_index(drop=True)], axis=1)
    move_df["under_pressure_f"] = move_df["under_pressure"].astype(float)
    x_cols = list(zone_dummies.columns) + ["under_pressure_f", "pass_length"]
    move_resid, move_r2 = demeaned_residuals(move_df, "log_interval", x_cols, ["match_id", "team"])
    move_df["residual"] = move_resid
    print(f"  MOVE_ON_SPEED regression: n={len(move_df)}, within R^2={move_r2:.4f}")

    hold_df = joined.dropna(subset=["zone", "pass_length"]).copy()
    zone_dummies_h = pd.get_dummies(pd.Categorical(hold_df["zone"], categories=ZONE_CATEGORIES),
                                     drop_first=True).astype(float)
    zone_dummies_h.columns = [f"zone_{c}" for c in zone_dummies_h.columns]
    hold_df = pd.concat([hold_df.reset_index(drop=True), zone_dummies_h.reset_index(drop=True)], axis=1)
    hold_df["under_pressure_f"] = hold_df["under_pressure"].astype(float)
    x_cols_h = list(zone_dummies_h.columns) + ["under_pressure_f", "pass_length"]
    hold_resid, hold_r2 = demeaned_residuals(hold_df, "time_on_ball", x_cols_h, ["match_id", "team"])
    hold_df["residual"] = hold_resid
    print(f"  HOLD_VARIATION regression: n={len(hold_df)}, within R^2={hold_r2:.4f}")

    # competition/season are looked up the same way Step 2/3 of Task 16 did, via match_competition_lookup
    from metrics import match_competition_lookup
    comp_lookup = match_competition_lookup()
    for d in (move_df, hold_df):
        d["competition_id"] = d["match_id"].map(lambda m: comp_lookup.get(m, (None, None))[0])
        d["season_id"] = d["match_id"].map(lambda m: comp_lookup.get(m, (None, None))[1])

    move_by_player = move_df.groupby(["player_id", "competition_id", "season_id"])["residual"]
    move_summary = move_by_player.agg(["mean", "count"]).rename(columns={"mean": "move_on_speed", "count": "n_move_on_speed"})

    hold_by_player = hold_df.groupby(["player_id", "competition_id", "season_id"])["residual"]
    hold_summary = hold_by_player.agg(lambda s: float(s.std(ddof=1)) if len(s) > 1 else None).rename("hold_variation")
    hold_n = hold_by_player.size().rename("n_hold_variation")

    per_player = move_summary.join(hold_summary, how="outer").join(hold_n, how="outer").reset_index()
    per_player.to_parquet(OUT_PATH)
    move_df[["player_id", "competition_id", "season_id", "residual"]].to_parquet(MOVE_RESID_PATH)
    hold_df[["player_id", "competition_id", "season_id", "residual"]].to_parquet(HOLD_RESID_PATH)

    def pct(s):
        return {str(p): float(np.percentile(s.dropna(), p)) for p in (5, 25, 50, 75, 95)}

    n_per_player_move = move_by_player.size()
    n_per_player_hold = hold_by_player.size()

    summary = {
        "n_open_play_pass_rows_built": int(len(op_all)),
        "n_resolved_joined_to_stream": int(len(joined)),
        "n_dropped_last_of_group": n_dropped_last,
        "n_dropped_nonpositive_interval": n_nonpositive,
        "move_on_speed": {
            "n_obs": int(len(move_df)), "within_r_squared": float(move_r2),
            "n_players": int(per_player["move_on_speed"].notna().sum()),
            "n_obs_per_player": pct(pd.Series(n_per_player_move.values)),
            "residual_distribution": pct(move_df["residual"]),
        },
        "hold_variation": {
            "n_obs": int(len(hold_df)), "within_r_squared": float(hold_r2),
            "n_players": int(per_player["hold_variation"].notna().sum()),
            "n_obs_per_player": pct(pd.Series(n_per_player_hold.values)),
            "player_sd_distribution": pct(per_player["hold_variation"].dropna()),
        },
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
    print(json.dumps(summary, indent=2, default=str))
    print(f"\nWrote {OUT_PATH} and {SUMMARY_PATH}")
    return per_player, move_df, hold_df, summary


if __name__ == "__main__":
    main()
