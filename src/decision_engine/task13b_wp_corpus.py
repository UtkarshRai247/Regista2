"""
Task 13b — Win probability from the full open-data corpus.

Governing document: docs/specs/analysis-plan-v3.md, Amendments v3-1 and
v3-2. Builds a second win-probability function (WP-corpus) from the
full StatsBomb open-data corpus (men's competitions, 2010-11 onward,
excluding the 299 study matches), selects between it and WP-299 on
calibration alone (original gate + Amendment v3-2's match-clustered
refinement), applies v3-2.1's O2 clipping fix, and builds O3 for the
first time if a WP function passes.

Uses statsbombpy (not a git clone) to acquire the corpus subset -- see
docs/results/13b-wp-corpus.md Section 4 for why. Reuses pull_data.py's
own fix for statsbombpy's requests_cache slowdown, verbatim.

Run: python src/decision_engine/task13b_wp_corpus.py
"""
import json
import re
import resource
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import requests
import requests_cache
import xgboost as xgb
from statsbombpy import sb

from sklearn.model_selection import train_test_split

from decompose import DATA_DIR, EVENTS_DIR, POLICY_PATH, build_per_pass_table
from task13_objectives import (
    D_MAX, GATE_MAX_PP, GATE_MIN_N, O1_MODEL_PATH, O2_MODEL_PATH, O3_OPTIONS_PATH,
    O2_OPTIONS_PATH, PATTERN_CODE, PV_FEATURES, ROWS_DIR,
    CONCEDE_MODEL_PATH, argmax_disagreement, build_option_context,
    build_per_pass_table_generic, build_success_turnover_features,
    build_wp_grid, calibration_table_continuous, compute_ev_o3, compute_realized_o3,
    decision_correlations, estimate_wp_rates, has_loc, wp_array_lookup,
)

warnings.filterwarnings("ignore")

requests_cache.uninstall_cache()
_orig_get = requests.get


def _get_with_timeout(*args, **kwargs):
    kwargs.setdefault("timeout", 30)
    return _orig_get(*args, **kwargs)


requests.get = _get_with_timeout

GOALS_PATH = DATA_DIR / "processed" / "wp_corpus_goals.parquet"
SUMMARY_PATH = DATA_DIR / "task13b_wp_corpus.json"
BIN_WIDTH_MIN = 5
SIG_Z = 1.96  # normal-approximation critical value for the refined gate's 95% test


# ---------------------------------------------------------------------------
# Step 1: acquire (statsbombpy, not a git clone -- see results page Section 4)
# ---------------------------------------------------------------------------

def season_start_year(season_name: str):
    m = re.search(r"(\d{4})", season_name)
    return int(m.group(1)) if m else None


def get_qualifying_competitions() -> pd.DataFrame:
    comps = sb.competitions()
    comps["season_start_year"] = comps["season_name"].apply(season_start_year)
    qualifying = comps[(comps["competition_gender"] == "male") & (comps["season_start_year"] >= 2010)]
    return qualifying[["competition_id", "season_id", "competition_name", "season_name", "season_start_year"]].reset_index(drop=True)


def get_qualifying_matches(comps: pd.DataFrame, exclude_ids: set) -> pd.DataFrame:
    frames = []
    for _, c in comps.iterrows():
        m = sb.matches(competition_id=int(c["competition_id"]), season_id=int(c["season_id"]))
        m = m[["match_id", "home_team", "away_team", "home_score", "away_score"]].copy()
        m["competition_id"] = c["competition_id"]
        m["season_id"] = c["season_id"]
        m["competition_name"] = c["competition_name"]
        m["season_name"] = c["season_name"]
        frames.append(m)
    matches = pd.concat(frames, ignore_index=True)
    matches = matches[~matches["match_id"].isin(exclude_ids)].reset_index(drop=True)
    return matches


# ---------------------------------------------------------------------------
# Step 2: extract, streaming (one match's events in memory at a time)
# ---------------------------------------------------------------------------

def extract_match_goals(match_id: int, home_team: str, away_team: str) -> list:
    ev = sb.events(match_id=match_id)
    ev = ev[ev["period"] < 5].sort_values("index" if "index" in ev.columns else "minute").reset_index(drop=True)
    elapsed = ev["minute"] + ev["second"] / 60.0
    match_duration = float(elapsed.max()) if len(ev) else 0.0
    is_goal = ((ev["type"] == "Shot") & (ev["shot_outcome"] == "Goal")) | (ev["type"] == "Own Goal Against")

    rows = []
    for i in np.where(is_goal.values)[0]:
        row = ev.iloc[i]
        scorer = row["team"]
        if row["type"] == "Own Goal Against":
            scorer = away_team if row["team"] == home_team else home_team
        rows.append({
            "goal_minute": int(row["minute"]), "goal_period": int(row["period"]),
            "goal_elapsed_minutes": float(elapsed.iloc[i]), "scoring_team": scorer,
        })
    if not rows:
        rows = [{"goal_minute": None, "goal_period": None, "goal_elapsed_minutes": None, "scoring_team": None}]
    for r in rows:
        r["match_duration_minutes"] = match_duration
    return rows


def step1_step2(exclude_ids: set) -> tuple:
    print("Step 1: acquiring qualifying competition-seasons (statsbombpy) ...")
    t0 = time.time()
    comps = get_qualifying_competitions()
    print(f"  {len(comps)} men's competition-seasons, 2010-11 onward")
    matches = get_qualifying_matches(comps, exclude_ids)
    t1 = time.time()
    print(f"  {len(matches)} qualifying matches (299 study matches excluded), acquired in {t1 - t0:.1f}s")
    assert set(matches["match_id"]).isdisjoint(exclude_ids), "study matches leaked into the corpus set"

    print("\nStep 2: extracting goals + match duration (streaming, one match at a time) ...")
    all_rows = []
    n_failed = 0
    match_ids = matches["match_id"].tolist()
    home_by_mid = dict(zip(matches["match_id"], matches["home_team"]))
    away_by_mid = dict(zip(matches["match_id"], matches["away_team"]))
    for i, mid in enumerate(match_ids):
        row = matches[matches["match_id"] == mid].iloc[0]
        for attempt in range(2):
            try:
                rows = extract_match_goals(mid, home_by_mid[mid], away_by_mid[mid])
                for r in rows:
                    r["match_id"] = mid
                    r["competition_id"] = row["competition_id"]
                    r["season_id"] = row["season_id"]
                    r["competition_name"] = row["competition_name"]
                    r["season_name"] = row["season_name"]
                    r["home_team"] = row["home_team"]
                    r["away_team"] = row["away_team"]
                    r["home_score"] = row["home_score"]
                    r["away_score"] = row["away_score"]
                all_rows.extend(rows)
                break
            except Exception as e:
                if attempt == 1:
                    print(f"  FAILED match {mid}: {e}", file=sys.stderr)
                    n_failed += 1
                else:
                    time.sleep(1)
        if (i + 1) % 100 == 0:
            print(f"  {i + 1}/{len(match_ids)} matches processed (failed={n_failed})")
    t2 = time.time()

    goals_df = pd.DataFrame(all_rows)
    goals_df.to_parquet(GOALS_PATH)
    peak_rss_gb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024 ** 3)

    n_goals = goals_df["scoring_team"].notna().sum()
    n_matches_extracted = goals_df["match_id"].nunique()
    summary = {
        "n_qualifying_competitions": len(comps),
        "n_qualifying_matches": len(matches),
        "n_matches_extracted": int(n_matches_extracted),
        "n_failed": n_failed,
        "n_goals": int(n_goals),
        "competitions": sorted((matches["competition_name"] + " " + matches["season_name"]).unique().tolist()),
        "acquire_wall_clock_s": t1 - t0,
        "extract_wall_clock_s": t2 - t1,
        "peak_rss_gb": peak_rss_gb,
    }
    print(f"\n  extracted {n_matches_extracted}/{len(matches)} matches, {n_goals} goals, "
          f"{n_failed} failed, extract wall-clock {t2 - t1:.1f}s, peak RSS {peak_rss_gb:.2f}GB")
    return goals_df, summary


# ---------------------------------------------------------------------------
# Step 3: build WP-corpus
# ---------------------------------------------------------------------------

def estimate_wp_rates_from_corpus(goals_df: pd.DataFrame) -> tuple:
    exposure = {"leading": 0.0, "level": 0.0, "trailing": 0.0}
    goals = {"leading": 0, "level": 0, "trailing": 0}
    for match_id, g in goals_df.groupby("match_id"):
        home_team, away_team = g["home_team"].iloc[0], g["away_team"].iloc[0]
        match_duration = g["match_duration_minutes"].iloc[0]
        goal_rows = g.dropna(subset=["scoring_team"]).sort_values("goal_elapsed_minutes")
        score = {home_team: 0, away_team: 0}
        seg_start = 0.0
        for _, gr in goal_rows.iterrows():
            t = gr["goal_elapsed_minutes"]
            diff = score[home_team] - score[away_team]
            dur = t - seg_start
            if dur > 0:
                if diff == 0:
                    exposure["level"] += 2 * dur
                else:
                    exposure["leading"] += dur
                    exposure["trailing"] += dur
            diff_for_scorer = diff if gr["scoring_team"] == home_team else -diff
            state = "leading" if diff_for_scorer > 0 else ("trailing" if diff_for_scorer < 0 else "level")
            goals[state] += 1
            score[gr["scoring_team"]] += 1
            seg_start = t
        diff = score[home_team] - score[away_team]
        dur = match_duration - seg_start
        if dur > 0:
            if diff == 0:
                exposure["level"] += 2 * dur
            else:
                exposure["leading"] += dur
                exposure["trailing"] += dur
    rates = {k: goals[k] / exposure[k] for k in goals}
    return rates, goals, exposure


def detect_team_name_mismatches(goals_df: pd.DataFrame) -> tuple:
    """StatsBomb's events `team` field sometimes uses a short/former club
    name that differs from sb.matches()'s home_team/away_team (e.g.
    "Marseille" vs "Olympique de Marseille", "ATK Mohun Bagan" vs
    "Mohun Bagan Super Giant") -- the same class of finding
    docs/results/10-validation.md already documented for Marseille in the
    299-match study sample. A goal whose scoring_team matches neither of
    its own match's home_team/away_team can't be attributed to a side for
    score-tracking, so that whole match is excluded from rate estimation
    rather than guessed at."""
    has_goal = goals_df.dropna(subset=["scoring_team"])
    mismatched = has_goal[~has_goal.apply(lambda r: r["scoring_team"] in (r["home_team"], r["away_team"]), axis=1)]
    examples = mismatched[["match_id", "competition_name", "season_name", "home_team", "away_team", "scoring_team"]].drop_duplicates()
    return set(mismatched["match_id"].unique()), examples


def step3_wp_corpus(goals_df: pd.DataFrame, m_max: int) -> tuple:
    print("\nStep 3: building WP-corpus ...")
    mismatched_ids, mismatch_examples = detect_team_name_mismatches(goals_df)
    print(f"  team-name mismatches (events `team` vs sb.matches() home/away_team): "
          f"{len(mismatched_ids)} matches excluded from rate estimation")
    if mismatched_ids:
        print(mismatch_examples.to_string())
    goals_df_clean = goals_df[~goals_df["match_id"].isin(mismatched_ids)]

    rates, goals, exposure = estimate_wp_rates_from_corpus(goals_df_clean)
    print(f"  per-minute scoring rates: {rates}")
    print(f"  goal counts by state: {goals}")
    print(f"  exposure (team-minutes) by state: {exposure}")
    WP = build_wp_grid(rates, D_MAX, m_max)
    return WP, {"rates": rates, "goals_by_state": goals, "exposure_by_state": exposure,
                "n_matches_excluded_name_mismatch": len(mismatched_ids),
                "n_matches_used": goals_df_clean["match_id"].nunique(),
                "name_mismatch_examples": mismatch_examples.to_dict("records")}


# ---------------------------------------------------------------------------
# Step 3b: O2 clipping (v3-2.1)
# ---------------------------------------------------------------------------

def compute_ev_o2_clipped(opt: pd.DataFrame, model) -> tuple:
    X_success, X_turnover = build_success_turnover_features(opt)
    raw_success = model.predict(X_success)
    raw_turnover_opp = model.predict(X_turnover)
    v_success = np.clip(raw_success, 0, None)
    v_turnover = -np.clip(raw_turnover_opp, 0, None)
    ev = opt["p_success"].values * v_success + (1 - opt["p_success"].values) * v_turnover
    share_clipped = float(np.mean(np.concatenate([raw_success, raw_turnover_opp]) < 0))
    return v_success, v_turnover, ev, share_clipped


def compute_realized_o2_clipped(match_id: int, model) -> pd.DataFrame:
    from pitch_direction import normalize_xy, team_period_directions
    ev = pd.read_parquet(EVENTS_DIR / f"{match_id}.parquet")
    ev = ev[ev["period"] < 5].sort_values("index").reset_index(drop=True)
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

    passes = ev[(ev["type"] == "Pass") & ev["location"].apply(has_loc)
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
        rows_success.append({"ball_x": sx, "ball_y": sy, "prev_x": px, "prev_y": py,
                              "time_remaining_period": time_remaining, "score_diff": score_diff,
                              "play_pattern_code": PATTERN_CODE["Regular Play"]})
        opp_direction = -direction
        tx, ty = normalize_xy(end_loc[0], end_loc[1], opp_direction)
        opx, opy = normalize_xy(loc[0], loc[1], opp_direction)
        rows_turnover.append({"ball_x": tx, "ball_y": ty, "prev_x": opx, "prev_y": opy,
                               "time_remaining_period": time_remaining, "score_diff": -score_diff,
                               "play_pattern_code": PATTERN_CODE["From Counter"]})
        meta.append({"event_id": r["id"], "complete": complete})

    if not meta:
        return pd.DataFrame(columns=["event_id", "realized_value"])
    meta_df = pd.DataFrame(meta)
    v_success = np.clip(model.predict(pd.DataFrame(rows_success)[PV_FEATURES]), 0, None)
    v_turnover = -np.clip(model.predict(pd.DataFrame(rows_turnover)[PV_FEATURES]), 0, None)
    meta_df["realized_value"] = np.where(meta_df["complete"].values, v_success, v_turnover)
    return meta_df[["event_id", "realized_value"]]


def clipped_calibration_on_holdout(model, match_ids: list) -> dict:
    """Same held-out match-level split Task 13 Step 1 used (test_size=0.2,
    random_state=42), so the before/after-clipping calibration comparison
    is apples-to-apples."""
    parts = list(ROWS_DIR.glob("*.parquet"))
    df = pd.concat((pd.read_parquet(p) for p in parts), ignore_index=True)
    _, test_ids = train_test_split(match_ids, test_size=0.2, random_state=42)
    test_mask = df["match_id"].isin(test_ids)
    X_test, y_test = df.loc[test_mask, PV_FEATURES], df.loc[test_mask, "label_xg"]
    raw_pred = model.predict(X_test)
    clipped_pred = np.clip(raw_pred, 0, None)
    return {
        "n_test": int(test_mask.sum()),
        "share_negative_raw": float((raw_pred < 0).mean()),
        "calibration_after_clipping": calibration_table_continuous(y_test.values, clipped_pred),
    }


def step3b_o2_clipping(match_ids: list, wp_match_ends: dict) -> tuple:
    print("\nStep 3b: applying O2 clipping (v3-2.1) ...")
    policy = pd.read_parquet(POLICY_PATH)
    directions, context = build_option_context(match_ids, wp_match_ends)
    opt = policy.merge(directions, on=["match_id", "team", "period"], how="left")
    opt = opt.merge(context, on=["match_id", "event_id"], how="left")
    assert opt["direction"].notna().all() and opt["time_remaining_period"].notna().all()

    o2_model = xgb.XGBRegressor()
    o2_model.load_model(O2_MODEL_PATH)
    v_success, v_turnover, ev, share_clipped = compute_ev_o2_clipped(opt, o2_model)

    key_cols = ["match_id", "event_id", "team", "period", "candidate_x", "candidate_y", "chosen"]
    out = opt[key_cols].copy()
    out["v_success"], out["v_turnover"], out["ev"] = v_success, v_turnover, ev
    out.to_parquet(O2_OPTIONS_PATH)

    holdout_summary = clipped_calibration_on_holdout(o2_model, match_ids)
    print(f"  share of raw option-level predictions clipped (negative before clipping, "
          f"pooling success- and turnover-state predictions): {share_clipped:.4f}")
    print(f"  held-out test set: n={holdout_summary['n_test']}, "
          f"share negative before clipping={holdout_summary['share_negative_raw']:.4f}")
    print(f"  rewrote {O2_OPTIONS_PATH}")
    return opt, o2_model, ev, {"share_clipped_options": share_clipped, "n_options": len(opt), **holdout_summary}


# ---------------------------------------------------------------------------
# Step 4: select WP function; build O3 if one passes
# ---------------------------------------------------------------------------

def validate_wp_with_clusters(WP: np.ndarray, match_ids: list, d_max: int, m_max: int, bin_width: int) -> pd.DataFrame:
    """Same state-sampling as task13_objectives.validate_wp but also
    records match_id per sampled state, for the v3-2.3 match-clustered
    significance test."""
    from task13_objectives import match_segments_and_goals
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
            for d, outcome in ((diff, outcome_a), (-diff, outcome_b)):
                pred = float(wp_array_lookup(WP, d_max, m_max, np.array([d]), np.array([m_remaining]))[0])
                rows.append({"match_id": mid, "d": d, "m_remaining": m_remaining, "predicted": pred, "observed": outcome})
    df = pd.DataFrame(rows)
    df["m_bin"] = (df["m_remaining"] // bin_width * bin_width).astype(int)
    return df


def gate_verdict(states_df: pd.DataFrame) -> dict:
    """Original gate: any (d, m_bin) bucket with n>=GATE_MIN_N off by more
    than GATE_MAX_PP fails."""
    bucket = states_df.groupby(["d", "m_bin"]).agg(
        n=("observed", "size"), mean_predicted=("predicted", "mean"), mean_observed=("observed", "mean"),
    ).reset_index()
    bucket["abs_diff_pp"] = (bucket["mean_predicted"] - bucket["mean_observed"]).abs() * 100
    brier = float(((states_df["predicted"] - states_df["observed"]) ** 2).mean())
    violations = bucket[(bucket["n"] >= GATE_MIN_N) & (bucket["abs_diff_pp"] > GATE_MAX_PP)]
    return {"n_states": len(states_df), "brier": brier, "gate_passed": bool(len(violations) == 0),
            "bucket_table": bucket.to_dict("records"), "violations": violations.to_dict("records")}


def refined_gate_verdict(states_df: pd.DataFrame, original: dict) -> dict:
    """v3-2.3: a bucket fails only if it already fails the original 10pp
    threshold AND the match-clustered difference is significant at 95%
    (normal approximation)."""
    refined_violations = []
    for v in original["violations"]:
        sub = states_df[(states_df["d"] == v["d"]) & (states_df["m_bin"] == v["m_bin"])]
        per_match = sub.groupby("match_id").apply(lambda g: (g["observed"] - g["predicted"]).mean())
        n_matches = len(per_match)
        if n_matches < 2:
            refined_violations.append({**v, "n_matches": n_matches, "t_stat": None, "significant": True})
            continue
        se = per_match.std(ddof=1) / np.sqrt(n_matches)
        t_stat = float(per_match.mean() / se) if se > 0 else float("inf")
        significant = abs(t_stat) > SIG_Z
        refined_violations.append({**v, "n_matches": int(n_matches), "t_stat": t_stat, "significant": bool(significant)})
    surviving = [v for v in refined_violations if v["significant"]]
    return {"n_states": original["n_states"], "brier": original["brier"],
            "gate_passed": bool(len(surviving) == 0),
            "bucket_table": original["bucket_table"], "all_original_violations_retested": refined_violations,
            "surviving_violations": surviving}


def select_primary(wp299_orig, wp299_refined, wpcorpus_orig, wpcorpus_refined) -> tuple:
    if wpcorpus_orig["gate_passed"]:
        candidates = [("WP-corpus", wpcorpus_orig["brier"])]
        if wp299_orig["gate_passed"]:
            candidates.append(("WP-299", wp299_orig["brier"]))
        primary = min(candidates, key=lambda c: c[1])[0]
        rule = "original gate (WP-corpus passed the original gate; the v3-2.3 refinement is a footnote only)"
        return primary, rule
    candidates = []
    if wp299_refined["gate_passed"]:
        candidates.append(("WP-299", wp299_refined["brier"]))
    if wpcorpus_refined["gate_passed"]:
        candidates.append(("WP-corpus", wpcorpus_refined["brier"]))
    if candidates:
        primary = min(candidates, key=lambda c: c[1])[0]
        rule = "match-clustered refined gate (v3-2.3), since WP-corpus failed the original gate"
        return primary, rule
    return None, "neither function passed the original gate or the refined gate"


def main():
    print("Step 0 (already committed): Amendment v3-2 + revised task-13b-wp-corpus.md")

    match_ids = sorted(int(p.stem) for p in EVENTS_DIR.glob("*.parquet"))
    exclude_ids = set(match_ids)
    print(f"Study sample: {len(match_ids)} matches (excluded from the corpus)")

    if GOALS_PATH.exists():
        print(f"\nSteps 1-2: {GOALS_PATH} already exists -- resuming from it (skipping the network pull).")
        goals_df = pd.read_parquet(GOALS_PATH)
        extract_summary = {
            "n_matches_extracted": int(goals_df["match_id"].nunique()),
            "n_goals": int(goals_df["scoring_team"].notna().sum()),
            "competitions": sorted((goals_df["competition_name"] + " " + goals_df["season_name"]).unique().tolist()),
            "resumed_from_existing_file": True,
        }
    else:
        goals_df, extract_summary = step1_step2(exclude_ids)

    rates_299, _, exposure_299, match_ends_299 = estimate_wp_rates(match_ids)
    m_max = int(np.ceil(max(match_ends_299.values()))) + 1
    print(f"\nWP-299 rates (recomputed for this task's grid): {rates_299}")
    WP_299 = build_wp_grid(rates_299, D_MAX, m_max)

    WP_corpus, corpus_wp_summary = step3_wp_corpus(goals_df, m_max)

    opt, o2_model, ev_o2, clip_summary = step3b_o2_clipping(match_ids, match_ends_299)

    print("\nStep 4: validating WP-299 and WP-corpus on the 299 study matches' own states ...")
    states_299 = validate_wp_with_clusters(WP_299, match_ids, D_MAX, m_max, BIN_WIDTH_MIN)
    states_corpus = validate_wp_with_clusters(WP_corpus, match_ids, D_MAX, m_max, BIN_WIDTH_MIN)

    wp299_orig = gate_verdict(states_299)
    wpcorpus_orig = gate_verdict(states_corpus)
    wp299_refined = refined_gate_verdict(states_299, wp299_orig)
    wpcorpus_refined = refined_gate_verdict(states_corpus, wpcorpus_orig)

    print(f"  WP-299    original gate: {'PASSED' if wp299_orig['gate_passed'] else 'FAILED'}, Brier={wp299_orig['brier']:.4f}")
    print(f"  WP-corpus original gate: {'PASSED' if wpcorpus_orig['gate_passed'] else 'FAILED'}, Brier={wpcorpus_orig['brier']:.4f}")
    print(f"  WP-299    refined  gate: {'PASSED' if wp299_refined['gate_passed'] else 'FAILED'}")
    print(f"  WP-corpus refined  gate: {'PASSED' if wpcorpus_refined['gate_passed'] else 'FAILED'}")

    primary, rule = select_primary(wp299_orig, wp299_refined, wpcorpus_orig, wpcorpus_refined)
    print(f"  PRIMARY: {primary} ({rule})")

    o1_model = xgb.XGBClassifier()
    o1_model.load_model(O1_MODEL_PATH)
    concede_model = xgb.XGBClassifier()
    concede_model.load_model(CONCEDE_MODEL_PATH)

    policy = pd.read_parquet(POLICY_PATH)
    per_pass_o1 = build_per_pass_table(policy, o1_model, verbose=True)

    o2_policy_like = opt[["match_id", "event_id", "team", "player_id", "chosen", "p_success", "policy_probability"]].copy()
    o2_policy_like["ev"] = ev_o2
    per_pass_o2 = build_per_pass_table_generic(
        o2_policy_like, lambda mid: compute_realized_o2_clipped(mid, o2_model), match_ids,
    )

    per_pass_o3, ev_o3, o3_built = None, None, False
    if primary is not None:
        WP_primary = WP_299 if primary == "WP-299" else WP_corpus
        print(f"\nStep 4: building O3 for the first time with {primary} ...")
        v_s3, v_t3, ev_o3 = compute_ev_o3(opt, o1_model, concede_model, WP_primary, D_MAX, m_max)
        key_cols = ["match_id", "event_id", "team", "period", "candidate_x", "candidate_y", "chosen"]
        o3_out = opt[key_cols].copy()
        o3_out["v_success"], o3_out["v_turnover"], o3_out["ev"] = v_s3, v_t3, ev_o3
        o3_out.to_parquet(O3_OPTIONS_PATH)
        o3_built = True
        print(f"  wrote {O3_OPTIONS_PATH}")

        o3_policy_like = opt[["match_id", "event_id", "team", "player_id", "chosen", "p_success", "policy_probability"]].copy()
        o3_policy_like["ev"] = ev_o3
        per_pass_o3 = build_per_pass_table_generic(
            o3_policy_like, lambda mid: compute_realized_o3(mid, o1_model, concede_model, WP_primary, D_MAX, m_max), match_ids,
        )
    else:
        print("\nStep 4: neither WP function passed either gate -- O3 stays UNVALIDATED, not built.")

    print("\nSanity checks: argmax disagreement and Decision correlations ...")
    argmax_summary = argmax_disagreement(opt, ev_o2, ev_o3)
    corr_summary = decision_correlations(per_pass_o1, per_pass_o2, per_pass_o3)
    print(json.dumps(argmax_summary, indent=2, default=float))
    print(json.dumps({k: v for k, v in corr_summary.items() if k != "pass_level_corr" and k != "player_level_corr"}, indent=2))

    summary = {
        "status": "COMPLETE", "extract": extract_summary,
        "wp299": {"rates": rates_299, "exposure": exposure_299, "d_max": D_MAX, "m_max": m_max,
                  "original_gate": wp299_orig, "refined_gate": wp299_refined},
        "wpcorpus": {**corpus_wp_summary, "d_max": D_MAX, "m_max": m_max,
                     "original_gate": wpcorpus_orig, "refined_gate": wpcorpus_refined},
        "primary": primary, "selection_rule": rule, "o3_built": o3_built,
        "o2_clip": clip_summary, "argmax": argmax_summary, "correlations": corr_summary,
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
    print(f"\nWrote summary to {SUMMARY_PATH}")


if __name__ == "__main__":
    main()
