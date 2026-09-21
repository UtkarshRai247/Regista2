"""
Task 01 — Step 6: Decision / Execution / Risk decomposition.

Per pass (grouped by event_id):
  Decision  = EV(chosen) - sum_options[ policy_probability(option) * EV(option) ]
  Execution = realized_value(actual outcome) - EV(chosen)
  Risk      = Var(chosen) - sum_options[ policy_probability(option) * Var(option) ]
    where Var(option) = p_success*(1-p_success)*(v_success - v_turnover)^2,
    the variance of that option's two-point (success/turnover) outcome —
    mirrors Decision's exact "chosen minus policy-weighted-average"
    structure, applied to variance instead of EV. Stated plainly as this
    script's construction, since the spec doesn't spell out the options'
    variance formula explicitly.

Execution uses the TRUE pass_end_location and TRUE outcome (this is the
one place pass_end_location is used beyond the Step 1 matching step, per
D-011) — not the candidate's freeze-frame location, since Execution asks
"how did the REAL outcome compare to what was expected," not "how did
this hypothetical option compare."

Aggregates to per-player-per-competition-season: Decision/Execution/Risk
as a mean per 100 eligible passes, plus reference metrics computed over
the player's FULL event activity that competition-season (not restricted
to the frames-eligible subset, since these are meant to be the ordinary,
standard versions of these metrics for Gate B's separation check):
progressive passes/90, xA/90, pass completion %, minutes played.

Run: python src/decision_engine/decompose.py
"""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb

from pitch_direction import team_period_directions, normalize_xy
from possession_value import FEATURES as PV_FEATURES, PATTERN_CODE

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
EVENTS_DIR = DATA_DIR / "raw" / "events"
MATCHES_DIR = DATA_DIR / "raw" / "matches"
POLICY_PATH = DATA_DIR / "processed" / "options_policy.parquet"
PV_MODEL_PATH = DATA_DIR / "processed" / "possession_value_model.json"
OUT_PATH = DATA_DIR / "processed" / "player_season_metrics.parquet"

PROGRESSIVE_THRESHOLD_M = 10.0  # stated simplification: a completed pass counts as
                                  # "progressive" if it moves the ball >= 10m closer
                                  # to the center of the opponent's goal (attack-x
                                  # distance-to-goal reduced by >= 10m).


def match_competition_lookup() -> dict:
    lookup = {}
    for f in MATCHES_DIR.glob("*.parquet"):
        comp_id, season_id = f.stem.split("_")
        matches = pd.read_parquet(f)
        for mid in matches["match_id"]:
            lookup[int(mid)] = (int(comp_id), int(season_id))
    return lookup


def compute_realized_values(match_id: int, pv_model) -> pd.DataFrame:
    """Realized value of each pass's ACTUAL outcome, using the true
    pass_end_location (direction-normalized) and the true completion
    result — not the candidate's freeze-frame location. This is the one
    place beyond Step 1's matching where pass_end_location is used."""
    ev = pd.read_parquet(EVENTS_DIR / f"{match_id}.parquet")
    ev = ev.sort_values("index").reset_index(drop=True)
    ev["t"] = ev["minute"] * 60 + ev["second"]
    period_end = ev.groupby("period")["t"].transform("max")
    directions, _, _ = team_period_directions(ev)

    teams = ev["team"].dropna().unique().tolist()
    score = {t: 0 for t in teams}
    is_goal = ((ev["type"] == "Shot") & (ev["shot_outcome"] == "Goal")) | (ev["type"] == "Own Goal Against")
    score_diff_at = {}
    for i in range(len(ev)):
        row = ev.iloc[i]
        opp = [t for t in teams if t != row["team"]]
        opp = opp[0] if opp else None
        score_diff_at[row["id"]] = score.get(row["team"], 0) - score.get(opp, 0) if opp else 0
        if is_goal.iloc[i]:
            scorer = row["team"]
            if row["type"] == "Own Goal Against":
                scorer = opp
            if scorer in score:
                score[scorer] += 1

    def has_loc(v):
        return v is not None and not (isinstance(v, float) and pd.isna(v))

    passes = ev[(ev["type"] == "Pass")
                & ev["location"].apply(has_loc)
                & ev["pass_end_location"].apply(has_loc)].copy()

    rows_success, rows_turnover, meta = [], [], []
    for _, r in passes.iterrows():
        loc, end_loc = r["location"], r["pass_end_location"]
        direction = directions.get((r["team"], r["period"]), 1)
        time_remaining = float(period_end.loc[r.name] - r["t"])
        score_diff = score_diff_at[r["id"]]
        complete = pd.isna(r.get("pass_outcome"))

        sx, sy = normalize_xy(end_loc[0], end_loc[1], direction)
        px, py = normalize_xy(loc[0], loc[1], direction)
        rows_success.append({
            "ball_x": sx, "ball_y": sy, "prev_x": px, "prev_y": py,
            "time_remaining_period": time_remaining, "score_diff": score_diff,
            "play_pattern_code": PATTERN_CODE["Regular Play"],
        })

        opp_direction = -direction
        tx, ty = normalize_xy(end_loc[0], end_loc[1], opp_direction)
        opx, opy = normalize_xy(loc[0], loc[1], opp_direction)
        rows_turnover.append({
            "ball_x": tx, "ball_y": ty, "prev_x": opx, "prev_y": opy,
            "time_remaining_period": time_remaining, "score_diff": -score_diff,
            "play_pattern_code": PATTERN_CODE["From Counter"],
        })
        meta.append({"event_id": r["id"], "complete": complete})

    if not meta:
        return pd.DataFrame(columns=["event_id", "realized_value"])

    meta_df = pd.DataFrame(meta)
    v_success = pv_model.predict_proba(pd.DataFrame(rows_success)[PV_FEATURES])[:, 1]
    v_turnover_opp = pv_model.predict_proba(pd.DataFrame(rows_turnover)[PV_FEATURES])[:, 1]
    v_turnover = -v_turnover_opp

    meta_df["realized_value"] = np.where(meta_df["complete"].values, v_success, v_turnover)
    return meta_df[["event_id", "realized_value"]]


def compute_reference_metrics(match_id: int) -> pd.DataFrame:
    """Progressive passes, xA, completion %, minutes — over ALL of a
    player's activity in the match, not just the frames-eligible subset."""
    ev = pd.read_parquet(EVENTS_DIR / f"{match_id}.parquet")
    ev = ev.sort_values("index").reset_index(drop=True)
    directions, _, _ = team_period_directions(ev)

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
            goal_x = 120.0
            dist_before = goal_x - sx
            dist_after = goal_x - ex
            progressive = (dist_before - dist_after) >= PROGRESSIVE_THRESHOLD_M

        xa = 0.0
        if r.get("pass_shot_assist") and pd.notna(r.get("pass_assisted_shot_id")):
            raw_xa = xa_by_shot.get(r["pass_assisted_shot_id"], 0.0)
            xa = float(raw_xa) if pd.notna(raw_xa) else 0.0

        records.append({
            "player_id": r["player_id"], "team": r["team"],
            "complete": pd.isna(r.get("pass_outcome")),
            "progressive": progressive, "xa": xa,
        })

    df = pd.DataFrame(records)
    if df.empty:
        return pd.DataFrame(columns=["player_id", "n_passes", "n_complete", "n_progressive", "xa_sum"])
    agg = df.groupby("player_id").agg(
        n_passes=("complete", "count"),
        n_complete=("complete", "sum"),
        n_progressive=("progressive", "sum"),
        xa_sum=("xa", "sum"),
    ).reset_index()
    agg["match_id"] = match_id
    return agg


def compute_minutes(match_id: int) -> pd.DataFrame:
    ev = pd.read_parquet(EVENTS_DIR / f"{match_id}.parquet")
    ev = ev.sort_values("index").reset_index(drop=True)
    ev["t"] = ev["minute"] * 60 + ev["second"]
    match_end = ev["t"].max()

    starters = set()
    tactics = ev[ev["type"] == "Starting XI"]
    for _, r in tactics.iterrows():
        lineup = r.get("tactics")
        if isinstance(lineup, dict) and "lineup" in lineup:
            for p in lineup["lineup"]:
                starters.add(p["player"]["id"])
        elif isinstance(lineup, (list, np.ndarray)):
            for p in lineup:
                if isinstance(p, dict) and "player" in p:
                    starters.add(p["player"]["id"])

    start_time = {pid: 0.0 for pid in starters}
    end_time = {}

    subs = ev[ev["type"] == "Substitution"].sort_values("t")
    for _, r in subs.iterrows():
        off_id = r["player_id"]
        on_id = r.get("substitution_replacement_id")
        end_time.setdefault(off_id, r["t"])
        if pd.notna(on_id):
            start_time.setdefault(on_id, r["t"])

    all_players = set(start_time) | set(end_time)
    # anyone who has events but no start/sub record: assume played whole match
    event_players = set(ev["player_id"].dropna().unique())
    for pid in event_players - all_players:
        start_time[pid] = 0.0

    rows = []
    for pid in set(start_time):
        st = start_time.get(pid, 0.0)
        et = end_time.get(pid, match_end)
        rows.append({"player_id": pid, "match_id": match_id,
                      "minutes": max(0.0, (et - st) / 60.0)})
    return pd.DataFrame(rows)


def build_per_pass_table(policy: pd.DataFrame, pv_model, verbose: bool = True) -> pd.DataFrame:
    """Single source of truth for per-pass Decision/Execution/Risk.
    Shared by this script's aggregation and by Gate A's reliability calc,
    so the two can't silently drift out of sync."""
    policy = policy.copy()
    grp = policy.groupby("event_id")
    policy["ev_x_prob"] = policy["ev"] * policy["policy_probability"]
    policy["var_option"] = policy["p_success"] * (1 - policy["p_success"]) * \
        (policy["v_success"] - policy["v_turnover"]) ** 2
    policy["var_x_prob"] = policy["var_option"] * policy["policy_probability"]

    per_pass = grp.agg(
        match_id=("match_id", "first"), team=("team", "first"),
        player_id=("player_id", "first"),
        ev_chosen=("ev", lambda s: s[policy.loc[s.index, "chosen"]].iloc[0]),
        policy_weighted_ev=("ev_x_prob", "sum"),
        var_chosen=("var_option", lambda s: s[policy.loc[s.index, "chosen"]].iloc[0]),
        policy_weighted_var=("var_x_prob", "sum"),
    ).reset_index()
    per_pass["decision"] = per_pass["ev_chosen"] - per_pass["policy_weighted_ev"]
    per_pass["risk"] = per_pass["var_chosen"] - per_pass["policy_weighted_var"]

    match_ids = sorted(per_pass["match_id"].unique())
    realized_frames = []
    for i, mid in enumerate(match_ids):
        realized_frames.append(compute_realized_values(mid, pv_model))
        if verbose and (i + 1) % 50 == 0:
            print(f"  realized values: {i + 1}/{len(match_ids)} matches")
    realized = pd.concat(realized_frames, ignore_index=True)
    per_pass = per_pass.merge(realized, on="event_id", how="left")
    per_pass["execution"] = per_pass["realized_value"] - per_pass["ev_chosen"]
    return per_pass


def main():
    policy = pd.read_parquet(POLICY_PATH)
    pv_model = xgb.XGBClassifier()
    pv_model.load_model(PV_MODEL_PATH)
    comp_lookup = match_competition_lookup()

    per_pass = build_per_pass_table(policy, pv_model)
    match_ids = sorted(per_pass["match_id"].unique())

    # --- aggregate Decision/Execution/Risk per player-per-competition-season ---
    per_pass["competition_id"] = per_pass["match_id"].map(lambda m: comp_lookup.get(m, (None, None))[0])
    per_pass["season_id"] = per_pass["match_id"].map(lambda m: comp_lookup.get(m, (None, None))[1])

    der = per_pass.groupby(["player_id", "competition_id", "season_id"]).agg(
        n_eligible_passes=("decision", "count"),
        decision_per_100=("decision", lambda s: s.mean() * 100),
        execution_per_100=("execution", lambda s: s.mean() * 100),
        risk_per_100=("risk", lambda s: s.mean() * 100),
    ).reset_index()

    # --- reference metrics + minutes, over full activity ---
    ref_frames, min_frames = [], []
    for i, mid in enumerate(match_ids):
        ref_frames.append(compute_reference_metrics(mid))
        min_frames.append(compute_minutes(mid))
        if (i + 1) % 50 == 0:
            print(f"  reference metrics: {i + 1}/{len(match_ids)} matches")
    ref = pd.concat(ref_frames, ignore_index=True)
    minutes = pd.concat(min_frames, ignore_index=True)

    ref["competition_id"] = ref["match_id"].map(lambda m: comp_lookup.get(m, (None, None))[0])
    ref["season_id"] = ref["match_id"].map(lambda m: comp_lookup.get(m, (None, None))[1])
    minutes["competition_id"] = minutes["match_id"].map(lambda m: comp_lookup.get(m, (None, None))[0])
    minutes["season_id"] = minutes["match_id"].map(lambda m: comp_lookup.get(m, (None, None))[1])

    ref_agg = ref.groupby(["player_id", "competition_id", "season_id"]).agg(
        n_passes_total=("n_passes", "sum"),
        n_complete_total=("n_complete", "sum"),
        n_progressive_total=("n_progressive", "sum"),
        xa_total=("xa_sum", "sum"),
    ).reset_index()
    min_agg = minutes.groupby(["player_id", "competition_id", "season_id"]).agg(
        minutes_played=("minutes", "sum"),
    ).reset_index()

    final = der.merge(ref_agg, on=["player_id", "competition_id", "season_id"], how="left")
    final = final.merge(min_agg, on=["player_id", "competition_id", "season_id"], how="left")
    final["completion_pct"] = final["n_complete_total"] / final["n_passes_total"]
    final["progressive_passes_per_90"] = final["n_progressive_total"] / (final["minutes_played"] / 90)
    final["xa_per_90"] = final["xa_total"] / (final["minutes_played"] / 90)

    final.to_parquet(OUT_PATH)
    print(f"\nWrote {len(final)} player-competition-season rows to {OUT_PATH}")
    print(final.describe().to_string())


if __name__ == "__main__":
    main()
