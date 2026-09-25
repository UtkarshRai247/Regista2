"""
Task 17, Step 3: Decision, Execution, Risk (engine-v2-rebuild.md section
5) computed on engine v2 for the first time. No retraining, no feature
changes -- M_for/M_against/pass-success/policy models are all Task 15's
frozen artifacts.

Decision = ev_chosen - policy_weighted_ev
Risk     = var_chosen - policy_weighted_var
(both directly from policy_score.py's per-pass summary table)

Execution = V_net(state actually observed 3 actions later) - EV(chosen),
using the REAL subsequent event (flat raw-event-index i+3, the project's
standing lookahead convention), not the destination's modelled value.
The state at i+3 is built exactly as value_models.py's/ev_policy.py's
existing per-event feature construction (most-recent-prior-touch `prev`,
that event's own real play_pattern/score_diff/time_remaining), but
normalized to the ORIGINAL passer's team throughout -- if a different
team is acting at i+3 (the ball changed hands), the freeze-frame
teammate/opponent roles are swapped (features.state_features_batch,
identical to ev_policy.py's turnover-branch construction) so V_net is
always expressed from the original team's point of view.

Aggregates to per-(player_id, competition_id, season_id) means per 100
passes -- an internal table only; no names, ranks, or leaderboards
appear anywhere in this script's output (hard rule).

Run: python src/engine_v2/decision_execution_risk.py
"""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb

from geometry import team_period_directions
from features import state_features_batch
from value_models import PATTERN_CODE, STATE_FEATURES, MODEL_FOR_PATH, MODEL_AGAINST_PATH
from validation_common import match_competition_lookup

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
EVENTS_DIR = DATA_DIR / "raw" / "events"
FRAMES_DIR = DATA_DIR / "raw" / "frames"
EV_DIR = DATA_DIR / "processed" / "engine_v2" / "options_ev"
POLICY_SUMMARY_PATH = DATA_DIR / "processed" / "engine_v2" / "pass_policy_summary.parquet"
OUT_PATH = DATA_DIR / "processed" / "engine_v2" / "pass_der.parquet"
PLAYER_SEASON_OUT = DATA_DIR / "processed" / "engine_v2" / "player_season_der.parquet"
SUMMARY_PATH = DATA_DIR / "engine_v2_step3_decision_execution_risk.json"

LOOKAHEAD_ACTIONS = 3
EXECUTION_MIN_COVERAGE = 0.80
GATE_THRESHOLD = 200


def chosen_rows_for_match(match_id: int) -> pd.DataFrame:
    df = pd.read_parquet(EV_DIR / f"{match_id}.parquet",
                          columns=["match_id", "event_id", "team", "player_id", "chosen", "EV"])
    return df[df["chosen"]][["match_id", "event_id", "team", "player_id", "EV"]]


def compute_execution_for_match(match_id: int, chosen: pd.DataFrame, model_for, model_against) -> tuple:
    events = pd.read_parquet(EVENTS_DIR / f"{match_id}.parquet").sort_values("index").reset_index(drop=True)
    frames = pd.read_parquet(FRAMES_DIR / f"{match_id}.parquet")
    frames_by_event = {eid: g for eid, g in frames.groupby("id")}
    directions = team_period_directions(events)
    events["t"] = events["minute"] * 60 + events["second"]
    period_end = events.groupby("period")["t"].transform("max")
    teams = events["team"].dropna().unique().tolist()
    is_goal = ((events["type"] == "Shot") & (events["shot_outcome"] == "Goal")) | (events["type"] == "Own Goal Against")

    n = len(events)
    score_before = []
    score = {t: 0 for t in teams}
    for k in range(n):
        score_before.append(dict(score))
        if is_goal.iloc[k]:
            r = events.iloc[k]
            if r["type"] == "Own Goal Against":
                scorer_list = [t for t in teams if t != r["team"]]
                scorer = scorer_list[0] if scorer_list else None
            else:
                scorer = r["team"]
            if scorer in score:
                score[scorer] += 1

    id_to_idx = {eid: idx for idx, eid in enumerate(events["id"])}
    locations = events["location"].values
    ids = events["id"].values
    play_patterns = events["play_pattern"].values
    periods = events["period"].values
    teams_arr = events["team"].values

    results = []
    n_total, n_out_of_bounds, n_no_loc_or_frame = 0, 0, 0
    for _, row in chosen.iterrows():
        n_total += 1
        i = id_to_idx.get(row["event_id"])
        if i is None:
            n_out_of_bounds += 1
            continue
        j = i + LOOKAHEAD_ACTIONS
        if j >= n:
            n_out_of_bounds += 1
            continue
        loc = locations[j]
        if loc is None or (isinstance(loc, float) and pd.isna(loc)):
            n_no_loc_or_frame += 1
            continue
        frame = frames_by_event.get(ids[j])
        if frame is None or len(frame) == 0:
            n_no_loc_or_frame += 1
            continue

        prev_loc = None
        for k in range(j - 1, -1, -1):
            pl = locations[k]
            if pl is not None and not (isinstance(pl, float) and pd.isna(pl)):
                prev_loc = pl
                break
        if prev_loc is None:
            prev_loc = loc

        original_team = row["team"]
        opp_teams = [t for t in teams if t != original_team]
        opponent = opp_teams[0] if opp_teams else None
        score_diff_original = score_before[j].get(original_team, 0) - score_before[j].get(opponent, 0) if opponent else 0
        time_remaining = float(period_end.iloc[j] - events["t"].iloc[j])
        direction_original = directions.get((original_team, periods[j]), 1)

        teammates = frame[(frame["teammate"] == True) & (frame["actor"] == False)]
        opponents = frame[frame["teammate"] == False]
        team_raw = np.array([list(l) for l in teammates["location"]], dtype=float) if len(teammates) else np.zeros((0, 2))
        opp_raw = np.array([list(l) for l in opponents["location"]], dtype=float) if len(opponents) else np.zeros((0, 2))

        ball_raw = np.array(loc, dtype=float)[None, :]
        prev_raw = np.array(prev_loc, dtype=float)

        team_at_j = teams_arr[j]
        if team_at_j == original_team:
            teammate_src, opponent_src = team_raw, opp_raw
        else:
            teammate_src, opponent_src = opp_raw, team_raw

        feats = state_features_batch(ball_raw, prev_raw, direction_original, teammate_src, opponent_src, len(frame))
        feats["time_remaining_period"] = np.array([time_remaining])
        feats["score_diff"] = np.array([score_diff_original])
        feats["play_pattern_code"] = np.array([PATTERN_CODE.get(play_patterns[j], PATTERN_CODE["Other"])])
        X = pd.DataFrame(feats)[STATE_FEATURES].astype(float)
        p_for = model_for.predict_proba(X)[:, 1][0]
        p_against = model_against.predict_proba(X)[:, 1][0]
        v_net_observed = float(p_for - p_against)

        results.append({"match_id": match_id, "event_id": row["event_id"], "team": original_team,
                         "player_id": row["player_id"], "v_net_observed": v_net_observed,
                         "execution": v_net_observed - float(row["EV"])})
    return results, n_total, n_out_of_bounds, n_no_loc_or_frame


def main():
    print("Step 3: Decision, Execution, Risk ...")
    policy_summary = pd.read_parquet(POLICY_SUMMARY_PATH)
    policy_summary["decision"] = policy_summary["ev_chosen"] - policy_summary["policy_weighted_ev"]
    policy_summary["risk"] = policy_summary["var_chosen"] - policy_summary["policy_weighted_var"]
    print(f"  Decision/Risk computed for {len(policy_summary)} passes")

    model_for = xgb.XGBClassifier()
    model_for.load_model(str(MODEL_FOR_PATH))
    model_against = xgb.XGBClassifier()
    model_against.load_model(str(MODEL_AGAINST_PATH))

    match_ids = sorted(int(p.stem) for p in EV_DIR.glob("*.parquet"))
    exec_rows = []
    n_total, n_out_of_bounds, n_no_loc_or_frame = 0, 0, 0
    for i, mid in enumerate(match_ids):
        chosen = chosen_rows_for_match(mid)
        rows, nt, noob, nnf = compute_execution_for_match(mid, chosen, model_for, model_against)
        exec_rows.extend(rows)
        n_total += nt
        n_out_of_bounds += noob
        n_no_loc_or_frame += nnf
        if (i + 1) % 50 == 0:
            print(f"  {i + 1}/{len(match_ids)} matches, valid Execution so far={len(exec_rows)}/{n_total}")

    execution_coverage = len(exec_rows) / n_total if n_total else 0.0
    print(f"  Execution coverage: {len(exec_rows)}/{n_total} = {execution_coverage:.4f} "
          f"(out_of_bounds={n_out_of_bounds}, no_loc_or_frame={n_no_loc_or_frame})")
    execution_kept = execution_coverage >= EXECUTION_MIN_COVERAGE
    print(f"  Execution {'KEPT' if execution_kept else 'DROPPED'} (>= {EXECUTION_MIN_COVERAGE:.0%} required)")

    exec_df = pd.DataFrame(exec_rows) if exec_rows else pd.DataFrame(
        columns=["match_id", "event_id", "team", "player_id", "v_net_observed", "execution"])

    per_pass = policy_summary.merge(
        exec_df[["match_id", "event_id", "execution"]], on=["match_id", "event_id"], how="left")
    if not execution_kept:
        per_pass = per_pass.drop(columns=["execution"])

    comp_lookup = match_competition_lookup()
    per_pass["competition_id"] = per_pass["match_id"].map(lambda m: comp_lookup.get(m, (None, None))[0])
    per_pass["season_id"] = per_pass["match_id"].map(lambda m: comp_lookup.get(m, (None, None))[1])
    # attach player_id from the EV corpus (chosen rows) since pass_policy_summary lacks it
    player_lookup = pd.concat([chosen_rows_for_match(m)[["match_id", "event_id", "player_id"]]
                                for m in match_ids], ignore_index=True)
    per_pass = per_pass.merge(player_lookup, on=["match_id", "event_id"], how="left")
    per_pass.to_parquet(OUT_PATH)

    agg_dict = {"decision": ("decision", lambda s: s.mean() * 100), "risk": ("risk", lambda s: s.mean() * 100),
                "n_passes": ("decision", "count")}
    if execution_kept:
        agg_dict["execution"] = ("execution", lambda s: s.mean() * 100)
    player_season = per_pass.groupby(["player_id", "competition_id", "season_id"]).agg(**agg_dict).reset_index()
    player_season = player_season.rename(columns={"decision": "decision_per_100", "risk": "risk_per_100"})
    if execution_kept:
        player_season = player_season.rename(columns={"execution": "execution_per_100"})
    player_season.to_parquet(PLAYER_SEASON_OUT)

    n_units_at_200 = int((player_season["n_passes"] >= GATE_THRESHOLD).sum())
    print(f"  player-season units: {len(player_season)} total, {n_units_at_200} at >= {GATE_THRESHOLD} passes")

    def pct(s):
        return {str(p): float(np.percentile(s.dropna(), p)) for p in (5, 25, 50, 75, 95)}

    summary = {
        "n_passes": len(per_pass),
        "decision_distribution_per_pass": pct(per_pass["decision"]),
        "risk_distribution_per_pass": pct(per_pass["risk"]),
        "execution_coverage": execution_coverage, "execution_kept": execution_kept,
        "n_execution_out_of_bounds": n_out_of_bounds, "n_execution_no_loc_or_frame": n_no_loc_or_frame,
        "n_player_season_units": len(player_season), "n_units_at_200_threshold": n_units_at_200,
        "decision_per_100_distribution": pct(player_season["decision_per_100"]),
        "risk_per_100_distribution": pct(player_season["risk_per_100"]),
    }
    if execution_kept:
        summary["execution_distribution_per_pass"] = pct(per_pass["execution"])
        summary["execution_per_100_distribution"] = pct(player_season["execution_per_100"])
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
    print(json.dumps(summary, indent=2, default=str))
    print(f"\nWrote {SUMMARY_PATH}")
    return summary


if __name__ == "__main__":
    main()
