"""
Task 13c — WP diagnostic, and one conditional attempt.

Governing document: docs/specs/analysis-plan-v3.md, Amendments v3-1 to
v3-3. Step 1 (diagnostic) always runs: splits the bucket that fails
calibration (a one-goal lead ~5-10 minutes into the match) by whether
the leading team is the stronger side, to distinguish "the three-state
construction is too coarse" from "team strength confounds it." Step 2
(a strength-conditioned WP rebuild) runs ONLY if Step 1 supports the
strength explanation -- one attempt, no gate changes, no iterating.

Run: python src/decision_engine/task13c_wp_diagnostic.py
"""
import json
import warnings

import numpy as np
import pandas as pd
import xgboost as xgb

from decompose import DATA_DIR, EVENTS_DIR, POLICY_PATH, build_per_pass_table
from task13_objectives import (
    D_MAX, O1_MODEL_PATH, O3_OPTIONS_PATH, argmax_disagreement,
    build_option_context, build_per_pass_table_generic, build_success_turnover_features,
    build_wp_grid, compute_ev_o3, compute_realized_o3, decision_correlations,
    estimate_wp_rates, has_loc, match_segments_and_goals, state_of, wp_array_lookup,
)
from task13b_wp_corpus import (
    BIN_WIDTH_MIN, CONCEDE_MODEL_PATH, GOALS_PATH, O2_OPTIONS_PATH,
    detect_team_name_mismatches, gate_verdict,
)

warnings.filterwarnings("ignore")

SUMMARY_PATH = DATA_DIR / "task13c_wp_diagnostic.json"
RENAME_MAP = {
    "Marseille": "Olympique de Marseille",
    "Caen": "Stade Malherbe Caen",
    "Hyderabad": "Hyderabad FC",
    "ATK Mohun Bagan": "Mohun Bagan Super Giant",
}
FAILING_D, FAILING_M_BIN = 1, 85
CONTEXT_M_BINS = [80, 60]
SIG_Z = 1.96


# ---------------------------------------------------------------------------
# Strength proxy
# ---------------------------------------------------------------------------

def build_match_score_table() -> pd.DataFrame:
    study_frames = []
    for f in (DATA_DIR / "raw" / "matches").glob("*.parquet"):
        m = pd.read_parquet(f, columns=["match_id", "home_team", "away_team", "home_score", "away_score"])
        study_frames.append(m)
    study = pd.concat(study_frames, ignore_index=True)

    corpus_goals = pd.read_parquet(GOALS_PATH)
    corpus = corpus_goals[["match_id", "home_team", "away_team", "home_score", "away_score"]].drop_duplicates(subset="match_id")
    return pd.concat([study, corpus], ignore_index=True)


def compute_strength_proxy(match_table: pd.DataFrame) -> pd.Series:
    home = match_table[["home_team", "home_score", "away_score"]].rename(
        columns={"home_team": "team", "home_score": "gf", "away_score": "ga"})
    away = match_table[["away_team", "away_score", "home_score"]].rename(
        columns={"away_team": "team", "away_score": "gf", "home_score": "ga"})
    long = pd.concat([home, away], ignore_index=True)
    long["diff"] = long["gf"] - long["ga"]
    return long.groupby("team")["diff"].mean()


# ---------------------------------------------------------------------------
# Step 1: diagnostic
# ---------------------------------------------------------------------------

def validate_wp_with_teams(WP: np.ndarray, match_ids: list, d_max: int, m_max: int, bin_width: int) -> pd.DataFrame:
    """Same state-sampling as task13b_wp_corpus.validate_wp_with_clusters,
    but also records which physical team each perspective row belongs
    to (needed for the strength split)."""
    rows = []
    for mid in match_ids:
        segments, _, match_end, team_a, team_b = match_segments_and_goals(mid)
        if not segments or match_end <= 0:
            continue
        final_diff = segments[-1][2]
        outcome_a = 1.0 if final_diff > 0 else (0.5 if final_diff == 0 else 0.0)
        outcome_b = 1.0 - outcome_a
        n_minutes = int(np.floor(match_end))
        for minute in range(0, n_minutes + 1):
            diff = next(seg[2] for seg in segments if seg[0] <= minute <= seg[1])
            m_remaining = match_end - minute
            for team, opponent, d, outcome in ((team_a, team_b, diff, outcome_a), (team_b, team_a, -diff, outcome_b)):
                pred = float(wp_array_lookup(WP, d_max, m_max, np.array([d]), np.array([m_remaining]))[0])
                rows.append({"match_id": mid, "team": team, "opponent": opponent, "d": d,
                             "m_remaining": m_remaining, "predicted": pred, "observed": outcome})
    df = pd.DataFrame(rows)
    df["m_bin"] = (df["m_remaining"] // bin_width * bin_width).astype(int)
    return df


def cluster_stats(sub: pd.DataFrame) -> dict:
    n_states = len(sub)
    if n_states == 0:
        return {"n_matches": 0, "n_states": 0, "mean_predicted": None, "mean_observed": None,
                "diff_pp": None, "t_stat": None, "significant": None}
    per_match = sub.groupby("match_id").apply(lambda g: (g["observed"] - g["predicted"]).mean())
    n_matches = len(per_match)
    mean_predicted = float(sub["predicted"].mean())
    mean_observed = float(sub["observed"].mean())
    diff_pp = (mean_predicted - mean_observed) * 100
    if n_matches < 2:
        return {"n_matches": n_matches, "n_states": n_states, "mean_predicted": mean_predicted,
                "mean_observed": mean_observed, "diff_pp": diff_pp, "t_stat": None, "significant": None}
    se = per_match.std(ddof=1) / np.sqrt(n_matches)
    t_stat = float(per_match.mean() / se) if se > 0 else float("inf")
    return {"n_matches": int(n_matches), "n_states": n_states, "mean_predicted": mean_predicted,
            "mean_observed": mean_observed, "diff_pp": diff_pp, "t_stat": t_stat,
            "significant": bool(abs(t_stat) > SIG_Z)}


def strength_split(states: pd.DataFrame, m_bin: int, d: int, proxy: pd.Series) -> tuple:
    sub = states[(states["d"] == d) & (states["m_bin"] == m_bin)].copy()
    has_proxy = sub["team"].isin(proxy.index) & sub["opponent"].isin(proxy.index)
    n_no_proxy = int((~has_proxy).sum())
    sub = sub[has_proxy]
    sub["team_strength"] = sub["team"].map(proxy)
    sub["opp_strength"] = sub["opponent"].map(proxy)
    stronger = sub[sub["team_strength"] > sub["opp_strength"]]
    weaker = sub[sub["team_strength"] <= sub["opp_strength"]]
    return cluster_stats(stronger), cluster_stats(weaker), n_no_proxy


def step1_diagnostic(match_ids: list, WP_299: np.ndarray, m_max: int, proxy: pd.Series) -> dict:
    print("Step 1: diagnostic ...")
    states = validate_wp_with_teams(WP_299, match_ids, D_MAX, m_max, BIN_WIDTH_MIN)

    failing_all = states[(states["d"] == FAILING_D) & (states["m_bin"] == FAILING_M_BIN)]
    print(f"  failing bucket (d={FAILING_D}, m_bin={FAILING_M_BIN}): "
          f"{len(failing_all)} states, {failing_all['match_id'].nunique()} matches")

    stronger, weaker, n_no_proxy = strength_split(states, FAILING_M_BIN, FAILING_D, proxy)
    print(f"  leader-stronger half: {stronger}")
    print(f"  leader-weaker half:   {weaker}")
    print(f"  states dropped for missing proxy: {n_no_proxy}")

    context = {}
    for m_bin in CONTEXT_M_BINS:
        s, w, npx = strength_split(states, m_bin, FAILING_D, proxy)
        context[m_bin] = {"stronger": s, "weaker": w, "n_no_proxy": npx}
        print(f"  context m_bin={m_bin}: stronger={s}, weaker={w}")

    both_sig = stronger["significant"] and weaker["significant"]
    same_direction = (stronger["diff_pp"] is not None and weaker["diff_pp"] is not None
                       and np.sign(stronger["diff_pp"]) == np.sign(weaker["diff_pp"]))
    one_sig_other_not = (stronger["significant"] != weaker["significant"]
                          and stronger["significant"] is not None and weaker["significant"] is not None)

    if both_sig and same_direction:
        explanation = "i"
        reason = ("both halves show a significant (|t|>1.96), same-direction overconfidence gap -- "
                   "team strength does not discriminate; the construction is too coarse")
    elif one_sig_other_not:
        explanation = "ii"
        reason = ("exactly one half's miscalibration is significant and the other's is not -- "
                   "team strength discriminates who the model gets wrong")
    else:
        explanation = "inconclusive"
        reason = "neither a clean (i) nor a clean (ii) pattern -- treated as NOT supporting (ii); Step 2 does not run"

    print(f"  VERDICT: explanation {explanation} ({reason})")
    return {
        "n_teams_with_proxy": int(len(proxy)),
        "proxy_distribution": proxy.describe().to_dict(),
        "failing_bucket": {"n_states": len(failing_all), "n_matches": int(failing_all["match_id"].nunique())},
        "stronger_half": stronger, "weaker_half": weaker, "n_no_proxy_failing": n_no_proxy,
        "context": context, "explanation": explanation, "reason": reason,
    }


# ---------------------------------------------------------------------------
# Step 2: strength-conditioned rebuild (only if Step 1 supports (ii))
# ---------------------------------------------------------------------------

def match_segments_and_scorers(match_id: int) -> tuple:
    """Reconstructs which team scored at each segment boundary from the
    already-computed team_a-team_b diff sequence (a +1 step is team_a
    scoring, a -1 step is team_b scoring, own goals already folded into
    that diff by match_segments_and_goals) -- avoids a second full scan
    of the match's raw events."""
    segments, _, match_end, team_a, team_b = match_segments_and_goals(match_id)
    scorers = []
    for k in range(len(segments) - 1):
        diff_before, diff_after = segments[k][2], segments[k + 1][2]
        scorers.append(team_a if diff_after == diff_before + 1 else team_b)
    return segments, scorers, match_end, team_a, team_b


def corpus_match_segments_and_scorers(g: pd.DataFrame) -> tuple:
    home_team, away_team = g["home_team"].iloc[0], g["away_team"].iloc[0]
    match_duration = g["match_duration_minutes"].iloc[0]
    goal_rows = g.dropna(subset=["scoring_team"]).sort_values("goal_elapsed_minutes")
    score = {home_team: 0, away_team: 0}
    segments, scorers = [], []
    seg_start = 0.0
    for _, gr in goal_rows.iterrows():
        t = gr["goal_elapsed_minutes"]
        diff = score[home_team] - score[away_team]
        segments.append((seg_start, t, diff))
        scorers.append(gr["scoring_team"])
        score[gr["scoring_team"]] += 1
        seg_start = t
    segments.append((seg_start, match_duration, score[home_team] - score[away_team]))
    return segments, scorers, match_duration, home_team, away_team


def accumulate_strength_exposure(segments, team_a, team_b, scorers, proxy, exposure, goals) -> bool:
    if team_a not in proxy.index or team_b not in proxy.index or proxy[team_a] == proxy[team_b]:
        return False
    bin_of = {team_a: ("stronger" if proxy[team_a] > proxy[team_b] else "weaker"),
              team_b: ("stronger" if proxy[team_b] > proxy[team_a] else "weaker")}
    for k in range(len(segments)):
        s, e, diff = segments[k]
        dur = e - s
        if dur > 0:
            if diff == 0:
                exposure[("level", bin_of[team_a])] += dur
                exposure[("level", bin_of[team_b])] += dur
            else:
                leader, trailer = (team_a, team_b) if diff > 0 else (team_b, team_a)
                exposure[("leading", bin_of[leader])] += dur
                exposure[("trailing", bin_of[trailer])] += dur
        if k < len(scorers):
            scorer = scorers[k]
            scorer_diff = diff if scorer == team_a else -diff
            state = "leading" if scorer_diff > 0 else ("trailing" if scorer_diff < 0 else "level")
            goals[(state, bin_of[scorer])] += 1
    return True


def build_wp_grid_by_strength(rates: dict, bin_name: str, d_max: int, m_max: int, dt: float = 1.0) -> np.ndarray:
    opp_bin = "weaker" if bin_name == "stronger" else "stronger"
    ds = list(range(-d_max, d_max + 1))
    WP = np.zeros((len(ds), m_max + 1))
    for idx, d in enumerate(ds):
        WP[idx, 0] = 1.0 if d > 0 else (0.5 if d == 0 else 0.0)
    for m in range(1, m_max + 1):
        for idx, d in enumerate(ds):
            rf = (rates.get((state_of(d), bin_name)) or 0.0) * dt
            ra = (rates.get((state_of(-d), opp_bin)) or 0.0) * dt
            stay = 1.0 - rf - ra
            wp_up = WP[idx + 1, m - 1] if idx + 1 < len(ds) else 1.0
            wp_down = WP[idx - 1, m - 1] if idx - 1 >= 0 else 0.0
            WP[idx, m] = stay * WP[idx, m - 1] + rf * wp_up + ra * wp_down
    return WP


def validate_wp_strength(WP_stronger, WP_weaker, proxy, match_ids, d_max, m_max, bin_width) -> pd.DataFrame:
    rows = []
    for mid in match_ids:
        segments, _, match_end, team_a, team_b = match_segments_and_goals(mid)
        if not segments or match_end <= 0:
            continue
        if team_a not in proxy.index or team_b not in proxy.index or proxy[team_a] == proxy[team_b]:
            continue
        bin_a = "stronger" if proxy[team_a] > proxy[team_b] else "weaker"
        bin_b = "weaker" if bin_a == "stronger" else "stronger"
        final_diff = segments[-1][2]
        outcome_a = 1.0 if final_diff > 0 else (0.5 if final_diff == 0 else 0.0)
        outcome_b = 1.0 - outcome_a
        n_minutes = int(np.floor(match_end))
        for minute in range(0, n_minutes + 1):
            diff = next(seg[2] for seg in segments if seg[0] <= minute <= seg[1])
            m_remaining = match_end - minute
            for d, outcome, b in ((diff, outcome_a, bin_a), (-diff, outcome_b, bin_b)):
                WP = WP_stronger if b == "stronger" else WP_weaker
                pred = float(wp_array_lookup(WP, d_max, m_max, np.array([d]), np.array([m_remaining]))[0])
                rows.append({"match_id": mid, "d": d, "m_remaining": m_remaining, "predicted": pred, "observed": outcome})
    df = pd.DataFrame(rows)
    df["m_bin"] = (df["m_remaining"] // bin_width * bin_width).astype(int)
    return df


def build_team_bin_lookup(match_ids: list, proxy: pd.Series) -> pd.DataFrame:
    rows = []
    for mid in match_ids:
        _, _, _, team_a, team_b = match_segments_and_goals(mid)
        if team_a not in proxy.index or team_b not in proxy.index or proxy[team_a] == proxy[team_b]:
            continue
        bin_a = "stronger" if proxy[team_a] > proxy[team_b] else "weaker"
        bin_b = "weaker" if bin_a == "stronger" else "stronger"
        rows.append({"match_id": mid, "team": team_a, "strength_bin": bin_a})
        rows.append({"match_id": mid, "team": team_b, "strength_bin": bin_b})
    return pd.DataFrame(rows)


def wp_lookup_by_bin(WP_stronger, WP_weaker, d_max, m_max, d_arr, m_arr, is_stronger_mask):
    out = np.empty(len(d_arr))
    if is_stronger_mask.any():
        out[is_stronger_mask] = wp_array_lookup(WP_stronger, d_max, m_max, d_arr[is_stronger_mask], m_arr[is_stronger_mask])
    if (~is_stronger_mask).any():
        out[~is_stronger_mask] = wp_array_lookup(WP_weaker, d_max, m_max, d_arr[~is_stronger_mask], m_arr[~is_stronger_mask])
    return out


def compute_ev_o3_strength(opt: pd.DataFrame, o1_model, concede_model, WP_stronger, WP_weaker, d_max, m_max) -> tuple:
    X_success, X_turnover = build_success_turnover_features(opt)
    p_score_s = o1_model.predict_proba(X_success)[:, 1]
    p_conc_s = concede_model.predict_proba(X_success)[:, 1]
    p_score_t = o1_model.predict_proba(X_turnover)[:, 1]
    p_conc_t = concede_model.predict_proba(X_turnover)[:, 1]

    d = opt["score_diff"].values.astype(int)
    m = opt["minutes_remaining"].values
    is_stronger = (opt["strength_bin"] == "stronger").values

    wp_d = wp_lookup_by_bin(WP_stronger, WP_weaker, d_max, m_max, d, m, is_stronger)
    wp_dp = wp_lookup_by_bin(WP_stronger, WP_weaker, d_max, m_max, d + 1, m, is_stronger)
    wp_dm = wp_lookup_by_bin(WP_stronger, WP_weaker, d_max, m_max, d - 1, m, is_stronger)
    v_success = p_score_s * (wp_dp - wp_d) + p_conc_s * (wp_dm - wp_d)

    d_opp = -d
    is_stronger_opp = ~is_stronger
    wp_do = wp_lookup_by_bin(WP_stronger, WP_weaker, d_max, m_max, d_opp, m, is_stronger_opp)
    wp_dop = wp_lookup_by_bin(WP_stronger, WP_weaker, d_max, m_max, d_opp + 1, m, is_stronger_opp)
    wp_dom = wp_lookup_by_bin(WP_stronger, WP_weaker, d_max, m_max, d_opp - 1, m, is_stronger_opp)
    v_turnover_opp = p_score_t * (wp_dop - wp_do) + p_conc_t * (wp_dom - wp_do)
    v_turnover = -v_turnover_opp

    ev = opt["p_success"].values * v_success + (1 - opt["p_success"].values) * v_turnover
    return v_success, v_turnover, ev


def compute_realized_o3_strength(match_id: int, o1_model, concede_model, WP_stronger, WP_weaker, team_bin: dict, d_max, m_max) -> pd.DataFrame:
    from pitch_direction import normalize_xy, team_period_directions
    from task13_objectives import PATTERN_CODE, PV_FEATURES, SHOOTOUT_PERIOD

    ev = pd.read_parquet(EVENTS_DIR / f"{match_id}.parquet")
    ev = ev[ev["period"] < SHOOTOUT_PERIOD].sort_values("index").reset_index(drop=True)
    ev["t"] = ev["minute"] * 60 + ev["second"]
    ev["elapsed_minutes"] = ev["minute"] + ev["second"] / 60.0
    match_end_minutes = float(ev["elapsed_minutes"].max())
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

    passes = ev[(ev["type"] == "Pass") & ev["location"].apply(has_loc)
                & ev["pass_end_location"].apply(has_loc)].copy()
    if passes.empty or match_id not in team_bin:
        return pd.DataFrame(columns=["event_id", "realized_value"])

    rows_success, rows_turnover, meta = [], [], []
    for _, r in passes.iterrows():
        loc, end_loc = r["location"], r["pass_end_location"]
        direction = directions.get((r["team"], r["period"]), 1)
        time_remaining = float(period_end.loc[r.name] - r["t"])
        score_diff = score_diff_at[r["id"]]
        minutes_remaining = match_end_minutes - r["elapsed_minutes"]
        complete = pd.isna(r.get("pass_outcome"))
        sx, sy = normalize_xy(end_loc[0], end_loc[1], direction)
        px, py = normalize_xy(loc[0], loc[1], direction)
        rows_success.append({"ball_x": sx, "ball_y": sy, "prev_x": px, "prev_y": py,
                              "time_remaining_period": time_remaining, "score_diff": score_diff,
                              "play_pattern_code": PATTERN_CODE["Regular Play"]})
        opp_direction = -direction
        tx, ty = normalize_xy(end_loc[0], end_loc[1], opp_direction)
        opx, opy = normalize_xy(loc[0], loc[1], opp_direction)
        rows_turnover.append({"ball_x": tx, "ball_y": ty, "prev_x": opx, "prev_y": opy,
                               "time_remaining_period": time_remaining, "score_diff": -score_diff,
                               "play_pattern_code": PATTERN_CODE["From Counter"]})
        team_str_bin = team_bin[match_id].get(r["team"])
        meta.append({"event_id": r["id"], "complete": complete, "score_diff": score_diff,
                     "minutes_remaining": minutes_remaining, "strength_bin": team_str_bin})

    meta_df = pd.DataFrame(meta)
    meta_df = meta_df[meta_df["strength_bin"].notna()]
    if meta_df.empty:
        return pd.DataFrame(columns=["event_id", "realized_value"])
    keep_idx = meta_df.index
    X_success = pd.DataFrame(rows_success)[PV_FEATURES].loc[keep_idx]
    X_turnover = pd.DataFrame(rows_turnover)[PV_FEATURES].loc[keep_idx]

    p_score_s = o1_model.predict_proba(X_success)[:, 1]
    p_conc_s = concede_model.predict_proba(X_success)[:, 1]
    p_score_t = o1_model.predict_proba(X_turnover)[:, 1]
    p_conc_t = concede_model.predict_proba(X_turnover)[:, 1]

    d = meta_df["score_diff"].values.astype(int)
    m = meta_df["minutes_remaining"].values
    is_stronger = (meta_df["strength_bin"] == "stronger").values

    wp_d = wp_lookup_by_bin(WP_stronger, WP_weaker, d_max, m_max, d, m, is_stronger)
    wp_dp = wp_lookup_by_bin(WP_stronger, WP_weaker, d_max, m_max, d + 1, m, is_stronger)
    wp_dm = wp_lookup_by_bin(WP_stronger, WP_weaker, d_max, m_max, d - 1, m, is_stronger)
    v_success = p_score_s * (wp_dp - wp_d) + p_conc_s * (wp_dm - wp_d)

    d_opp = -d
    is_stronger_opp = ~is_stronger
    wp_do = wp_lookup_by_bin(WP_stronger, WP_weaker, d_max, m_max, d_opp, m, is_stronger_opp)
    wp_dop = wp_lookup_by_bin(WP_stronger, WP_weaker, d_max, m_max, d_opp + 1, m, is_stronger_opp)
    wp_dom = wp_lookup_by_bin(WP_stronger, WP_weaker, d_max, m_max, d_opp - 1, m, is_stronger_opp)
    v_turnover_opp = p_score_t * (wp_dop - wp_do) + p_conc_t * (wp_dom - wp_do)
    v_turnover = -v_turnover_opp

    meta_df = meta_df.copy()
    meta_df["realized_value"] = np.where(meta_df["complete"].values, v_success, v_turnover)
    return meta_df[["event_id", "realized_value"]]


def step2_strength_rebuild(match_ids: list, proxy: pd.Series, m_max: int,
                            wp299_brier: float, wpcorpus_brier: float) -> dict:
    print("\nStep 2: strength-conditioned WP rebuild (diagnostic supported explanation ii) ...")
    goals_df = pd.read_parquet(GOALS_PATH)
    goals_df["scoring_team"] = goals_df["scoring_team"].replace(RENAME_MAP)
    mismatched_ids, examples = detect_team_name_mismatches(goals_df)
    n_recovered = 41 - len(mismatched_ids)
    print(f"  rename recovery: {n_recovered}/41 matches recovered, {len(mismatched_ids)} still excluded")
    if mismatched_ids:
        print(examples.to_string())
    goals_clean = goals_df[~goals_df["match_id"].isin(mismatched_ids)]

    exposure = {(s, b): 0.0 for s in ("leading", "level", "trailing") for b in ("stronger", "weaker")}
    goals = {(s, b): 0 for s in ("leading", "level", "trailing") for b in ("stronger", "weaker")}
    n_matches_no_proxy = 0

    for mid in match_ids:
        segments, scorers, match_end, team_a, team_b = match_segments_and_scorers(mid)
        if not accumulate_strength_exposure(segments, team_a, team_b, scorers, proxy, exposure, goals):
            n_matches_no_proxy += 1

    for mid, g in goals_clean.groupby("match_id"):
        segments, scorers, match_end, team_a, team_b = corpus_match_segments_and_scorers(g)
        if not accumulate_strength_exposure(segments, team_a, team_b, scorers, proxy, exposure, goals):
            n_matches_no_proxy += 1

    rates = {k: (goals[k] / exposure[k] if exposure[k] > 0 else None) for k in goals}
    print(f"  rates by (state, strength): {rates}")
    print(f"  goal counts: {goals}")
    print(f"  exposure: {exposure}")
    print(f"  matches skipped for missing/tied proxy: {n_matches_no_proxy}")

    WP_stronger = build_wp_grid_by_strength(rates, "stronger", D_MAX, m_max)
    WP_weaker = build_wp_grid_by_strength(rates, "weaker", D_MAX, m_max)

    states = validate_wp_strength(WP_stronger, WP_weaker, proxy, match_ids, D_MAX, m_max, BIN_WIDTH_MIN)
    verdict = gate_verdict(states)
    print(f"  revalidation (original gate only, one attempt): "
          f"{'PASSED' if verdict['gate_passed'] else 'FAILED'}, Brier={verdict['brier']:.6f}")
    print(f"  compare: WP-299 Brier={wp299_brier:.6f}, WP-corpus Brier={wpcorpus_brier:.6f}")

    result = {
        "n_recovered": n_recovered, "n_still_excluded": len(mismatched_ids),
        "rates": {f"{k[0]}_{k[1]}": v for k, v in rates.items()},
        "goals": {f"{k[0]}_{k[1]}": v for k, v in goals.items()},
        "exposure": {f"{k[0]}_{k[1]}": v for k, v in exposure.items()},
        "n_matches_no_proxy": n_matches_no_proxy, "verdict": verdict,
    }

    if not verdict["gate_passed"]:
        print("  FAILED the original gate. One attempt only -- stopping, O3 not built.")
        result["o3_built"] = False
        return result, None, None

    print("\n  Gate PASSED -- building O3 for all 1,237,611 options ...")
    o1_model = xgb.XGBClassifier(); o1_model.load_model(O1_MODEL_PATH)
    concede_model = xgb.XGBClassifier(); concede_model.load_model(CONCEDE_MODEL_PATH)
    rates_299, _, _, match_ends_299 = estimate_wp_rates(match_ids)

    policy = pd.read_parquet(POLICY_PATH)
    directions, context = build_option_context(match_ids, match_ends_299)
    opt_full = policy.merge(directions, on=["match_id", "team", "period"], how="left")
    opt_full = opt_full.merge(context, on=["match_id", "event_id"], how="left")
    bin_lookup = build_team_bin_lookup(match_ids, proxy)
    opt_full = opt_full.merge(bin_lookup, on=["match_id", "team"], how="left")
    assert len(opt_full) == len(policy), "context/bin-lookup merge produced a fan-out"
    keep_mask = opt_full["strength_bin"].notna().values
    opt = opt_full[keep_mask].copy()
    print(f"  option population with a resolvable strength bin: {len(opt)}/{len(policy)}")

    # options_o2.parquet is row-for-row positionally aligned with
    # options_policy.parquet (both built by column-adding left-merges of
    # the same frozen population, never reordered/filtered) -- some
    # option rows share identical (match_id,event_id,team,period,
    # candidate_x,candidate_y,chosen) values across different option
    # TYPES, so a key-based re-join fans out; positional alignment sides
    # around that entirely.
    o2_options = pd.read_parquet(O2_OPTIONS_PATH)
    assert len(o2_options) == len(policy), "options_o2.parquet row count no longer matches options_policy.parquet"
    ev_o2_full = o2_options["ev"].values

    v_s3, v_t3, ev_o3 = compute_ev_o3_strength(opt, o1_model, concede_model, WP_stronger, WP_weaker, D_MAX, m_max)
    key_cols = ["match_id", "event_id", "team", "period", "candidate_x", "candidate_y", "chosen"]
    o3_out = opt[key_cols].copy()
    o3_out["v_success"], o3_out["v_turnover"], o3_out["ev"] = v_s3, v_t3, ev_o3
    o3_out.to_parquet(O3_OPTIONS_PATH)
    print(f"  wrote {O3_OPTIONS_PATH}")

    team_bin_by_match = {}
    for _, r in bin_lookup.iterrows():
        team_bin_by_match.setdefault(r["match_id"], {})[r["team"]] = r["strength_bin"]

    o3_policy_like = opt[["match_id", "event_id", "team", "player_id", "chosen", "p_success", "policy_probability"]].copy()
    o3_policy_like["ev"] = ev_o3
    per_pass_o3 = build_per_pass_table_generic(
        o3_policy_like,
        lambda mid: compute_realized_o3_strength(mid, o1_model, concede_model, WP_stronger, WP_weaker, team_bin_by_match, D_MAX, m_max),
        match_ids,
    )

    per_pass_o1 = build_per_pass_table(policy, o1_model, verbose=True)

    from task13_objectives import O2_MODEL_PATH
    from task13b_wp_corpus import compute_realized_o2_clipped
    o2_model = xgb.XGBRegressor(); o2_model.load_model(O2_MODEL_PATH)
    o2_policy_like = policy[["match_id", "event_id", "team", "player_id", "chosen", "p_success", "policy_probability"]].copy()
    o2_policy_like["ev"] = ev_o2_full
    per_pass_o2 = build_per_pass_table_generic(
        o2_policy_like, lambda mid: compute_realized_o2_clipped(mid, o2_model), match_ids,
    )

    corr_summary = decision_correlations(per_pass_o1, per_pass_o2, per_pass_o3)

    ev_o2_for_opt = ev_o2_full[keep_mask]
    argmax_summary = argmax_disagreement(opt, ev_o2_for_opt, ev_o3)

    result["o3_built"] = True
    result["correlations"] = corr_summary
    result["argmax"] = argmax_summary
    return result, WP_stronger, WP_weaker


def main():
    print("Step 0 (already committed): Amendment v3-3")

    match_ids = sorted(int(p.stem) for p in EVENTS_DIR.glob("*.parquet"))
    rates_299, _, _, match_ends_299 = estimate_wp_rates(match_ids)
    m_max = int(np.ceil(max(match_ends_299.values()))) + 1
    WP_299 = build_wp_grid(rates_299, D_MAX, m_max)

    match_table = build_match_score_table()
    proxy = compute_strength_proxy(match_table)
    print(f"Strength proxy: {len(proxy)} teams, distribution {proxy.describe().to_dict()}")

    diagnostic = step1_diagnostic(match_ids, WP_299, m_max, proxy)

    summary = {"status": "COMPLETE", "diagnostic": diagnostic}

    if diagnostic["explanation"] == "ii":
        import json as _json
        wp13b = _json.loads((DATA_DIR / "task13b_wp_corpus.json").read_text())
        wp299_brier = wp13b["wp299"]["original_gate"]["brier"]
        wpcorpus_brier = wp13b["wpcorpus"]["original_gate"]["brier"]
        step2_result, WP_stronger, WP_weaker = step2_strength_rebuild(match_ids, proxy, m_max, wp299_brier, wpcorpus_brier)
        summary["step2"] = step2_result
        o3_built = step2_result["o3_built"]
        verdict_line = (
            f"O3 BUILT (strength-conditioned WP, Brier={step2_result['verdict']['brier']:.6f}, "
            f"original gate PASSED)" if o3_built else
            f"O3 ABANDONED (strength-conditioned WP built and revalidated once; "
            f"FAILED the original gate, Brier={step2_result['verdict']['brier']:.6f})"
        )
    else:
        summary["step2"] = None
        verdict_line = (
            f"O3 ABANDONED (Step 1 diagnostic supports explanation '{diagnostic['explanation']}', "
            f"not (ii) -- Step 2 does not run)"
        )

    print(f"\nStep 3: VERDICT -- {verdict_line}")
    summary["verdict"] = verdict_line
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
    print(f"\nWrote summary to {SUMMARY_PATH}")


if __name__ == "__main__":
    main()
