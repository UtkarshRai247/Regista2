"""
Task 13 — Build objectives O2 (chance creation) and O3 (winning).

Governing document: docs/specs/analysis-plan-v3.md (plan v3, Amendment
v3-1). Values only -- no leaderboards, no player names, no referee
tests (Task 14). Uses only the 299-match-sample win-probability
construction (plan v3 section 2); the corpus-based alternative is a
separate, not-yet-run task (task-13b) and must not block this one.

Reused, unmodified: possession_value.py's FEATURES/PATTERN_CODE/
LOOKAHEAD/frozen hyperparameters/calibration_table; pitch_direction's
team_period_directions/normalize_xy; task09b_horizon's live
memory-pressure gate; decompose.build_per_pass_table (for O1's own
reference Decision/Execution, called as-is since O1's classifier value
function is unchanged); options_policy.parquet as the frozen option
population.

Run: python src/decision_engine/task13_objectives.py
"""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import mean_absolute_error, r2_score, roc_auc_score
from sklearn.model_selection import train_test_split

from decompose import DATA_DIR, EVENTS_DIR, build_per_pass_table
from pitch_direction import PITCH_X, PITCH_Y, normalize_xy, team_period_directions
from possession_value import (
    FEATURES as PV_FEATURES, LOOKAHEAD, MODEL_PATH as O1_MODEL_PATH,
    PATTERN_CODE, calibration_table,
)
from task09_horizon import build_match_rows_horizon
from task09b_horizon import (
    PREFLIGHT_MIN_AVAILABLE_GB, PREFLIGHT_MIN_FREE_PCT, RUNTIME_MIN_AVAILABLE_GB,
    RUNTIME_MIN_FREE_PCT, MEMORY_CHECK_EVERY, check_memory,
)

warnings.filterwarnings("ignore")

POLICY_PATH = DATA_DIR / "processed" / "options_policy.parquet"
ROWS_DIR = DATA_DIR / "processed" / "task13_o2_concede_parts"
O2_MODEL_PATH = DATA_DIR / "processed" / "o2_value_model.json"
CONCEDE_MODEL_PATH = DATA_DIR / "processed" / "concede_model.json"
O2_OPTIONS_PATH = DATA_DIR / "processed" / "options_o2.parquet"
O3_OPTIONS_PATH = DATA_DIR / "processed" / "options_o3.parquet"
SUMMARY_PATH = DATA_DIR / "task13_objectives.json"

SHOOTOUT_PERIOD = 5  # penalty shootouts excluded from goal-rate estimation (no
                       # Pass options exist there anyway; distinct from normal play)
D_MAX = 15
BIN_WIDTH_MIN = 5
GATE_MIN_N = 100
GATE_MAX_PP = 10.0

XGB_KWARGS = dict(n_estimators=300, max_depth=5, learning_rate=0.05,
                   subsample=0.8, colsample_bytree=0.8, random_state=42)


# ---------------------------------------------------------------------------
# Step 1+2 shared: combined per-action-row builder (O2's cumulative-xG label
# and the concede model's binary label), same feature construction as
# possession_value.build_match_rows / task09_horizon.build_match_rows_horizon.
# ---------------------------------------------------------------------------

def build_match_rows_o2_concede(match_id: int, lookahead: int) -> list:
    ev = pd.read_parquet(EVENTS_DIR / f"{match_id}.parquet")
    ev = ev.sort_values("index").reset_index(drop=True)
    ev["t"] = ev["minute"] * 60 + ev["second"]
    period_end = ev.groupby("period")["t"].transform("max")
    directions, _, _ = team_period_directions(ev)
    teams = ev["team"].dropna().unique().tolist()
    score = {t: 0 for t in teams}
    is_goal = ((ev["type"] == "Shot") & (ev["shot_outcome"] == "Goal")) | (ev["type"] == "Own Goal Against")
    is_shot = (ev["type"] == "Shot")

    rows = []
    n = len(ev)
    for i in range(n):
        row = ev.iloc[i]
        team = row["team"]
        opp_teams = [t for t in teams if t != team]
        opponent = opp_teams[0] if opp_teams else None

        loc = row["location"]
        if loc is None or (isinstance(loc, float) and pd.isna(loc)):
            if is_goal.iloc[i]:
                scorer = team
                if row["type"] == "Own Goal Against":
                    scorer = opponent
                if scorer in score:
                    score[scorer] += 1
            continue

        prev_loc = None
        for j in range(i - 1, -1, -1):
            pl = ev.iloc[j]["location"]
            if pl is not None and not (isinstance(pl, float) and pd.isna(pl)):
                prev_loc = pl
                break
        if prev_loc is None:
            prev_loc = loc

        label_xg = 0.0
        label_concede = 0
        first_goal_resolved = False
        for k in range(i + 1, min(i + 1 + lookahead, n)):
            fut = ev.iloc[k]
            if is_shot.iloc[k] and fut["team"] == team:
                xg = fut["shot_statsbomb_xg"]
                if pd.notna(xg):
                    label_xg += float(xg)
            if not first_goal_resolved and is_goal.iloc[k]:
                scorer = fut["team"]
                if fut["type"] == "Own Goal Against":
                    scorer = opponent
                if scorer == opponent:
                    label_concede = 1
                first_goal_resolved = True

        score_diff = score.get(team, 0) - score.get(opponent, 0) if opponent else 0
        direction = directions.get((team, row["period"]), 1)
        attack_x, attack_y = normalize_xy(loc[0], loc[1], direction)
        prev_attack_x, prev_attack_y = normalize_xy(prev_loc[0], prev_loc[1], direction)

        rows.append({
            "match_id": match_id, "ball_x": attack_x, "ball_y": attack_y,
            "prev_x": prev_attack_x, "prev_y": prev_attack_y,
            "time_remaining_period": float(period_end.iloc[i] - row["t"]),
            "score_diff": score_diff,
            "play_pattern_code": PATTERN_CODE.get(row["play_pattern"], PATTERN_CODE["Other"]),
            "label_xg": label_xg, "label_concede": label_concede,
        })

        if is_goal.iloc[i]:
            scorer = team
            if row["type"] == "Own Goal Against":
                scorer = opponent
            if scorer in score:
                score[scorer] += 1

    return rows


def self_check_features(match_ids_sample: list):
    shared_cols = ["ball_x", "ball_y", "prev_x", "prev_y",
                   "time_remaining_period", "score_diff", "play_pattern_code"]
    for mid in match_ids_sample:
        mine = pd.DataFrame(build_match_rows_o2_concede(mid, LOOKAHEAD))
        frozen = pd.DataFrame(build_match_rows_horizon(mid, LOOKAHEAD))
        assert len(mine) == len(frozen), f"match {mid}: row count {len(mine)} vs {len(frozen)}"
        for c in shared_cols:
            assert np.allclose(mine[c].values, frozen[c].values), f"match {mid}: mismatch in {c}"
    print(f"Self-check passed on {len(match_ids_sample)} matches: feature construction "
          f"matches task09_horizon.build_match_rows_horizon exactly.")


def build_rows_cached_gated(match_ids: list) -> tuple:
    ROWS_DIR.mkdir(parents=True, exist_ok=True)
    n_processed = 0
    for mid in match_ids:
        out_path = ROWS_DIR / f"{mid}.parquet"
        if out_path.exists():
            continue
        rows = build_match_rows_o2_concede(mid, LOOKAHEAD)
        if rows:
            pd.DataFrame(rows).to_parquet(out_path)
        n_processed += 1
        if n_processed % MEMORY_CHECK_EVERY == 0:
            free_pct, available_gb = check_memory()
            n_cached = len(list(ROWS_DIR.glob("*.parquet")))
            print(f"  processed {n_processed} this run, {n_cached}/{len(match_ids)} cached, "
                  f"free={free_pct:.0f}%, available={available_gb:.2f}GB")
            if free_pct < RUNTIME_MIN_FREE_PCT or available_gb < RUNTIME_MIN_AVAILABLE_GB:
                print(f"  STOPPING: runtime memory gate breached ({n_cached}/{len(match_ids)} cached).")
                return None, True, n_cached
    parts = list(ROWS_DIR.glob("*.parquet"))
    df = pd.concat((pd.read_parquet(p) for p in parts), ignore_index=True)
    return df, False, len(parts)


def calibration_table_continuous(y_true, y_pred, n_bins=10) -> list:
    df = pd.DataFrame({"y": y_true, "p": y_pred})
    df["bin"] = pd.qcut(df["p"], n_bins, duplicates="drop")
    return [
        {"bin": str(b), "n": int(len(g)), "mean_predicted": float(g["p"].mean()),
         "mean_actual": float(g["y"].mean())}
        for b, g in df.groupby("bin", observed=True)
    ]


# ---------------------------------------------------------------------------
# Step 1: O2 value model (regression, match-level split per the brief)
# ---------------------------------------------------------------------------

def step1_o2_model(df: pd.DataFrame, match_ids: list) -> dict:
    print("\nStep 1: O2 value model (chance creation, regression) ...")
    train_ids, test_ids = train_test_split(match_ids, test_size=0.2, random_state=42)
    train_mask, test_mask = df["match_id"].isin(train_ids), df["match_id"].isin(test_ids)
    X_train, y_train = df.loc[train_mask, PV_FEATURES], df.loc[train_mask, "label_xg"]
    X_test, y_test = df.loc[test_mask, PV_FEATURES], df.loc[test_mask, "label_xg"]

    model = xgb.XGBRegressor(**XGB_KWARGS, eval_metric="rmse")
    model.fit(X_train, y_train)
    model.save_model(O2_MODEL_PATH)

    pred = model.predict(X_test)
    r2, mae = float(r2_score(y_test, pred)), float(mean_absolute_error(y_test, pred))
    calib = calibration_table_continuous(y_test.values, pred)
    summary = {
        "n_matches_train": len(train_ids), "n_matches_test": len(test_ids),
        "n_rows_train": int(train_mask.sum()), "n_rows_test": int(test_mask.sum()),
        "positive_label_rate": float((df["label_xg"] > 0).mean()),
        "r2": r2, "mae": mae, "calibration": calib,
    }
    print(f"  train matches={len(train_ids)}, test matches={len(test_ids)}, "
          f"train rows={train_mask.sum()}, test rows={test_mask.sum()}")
    print(f"  held-out R2={r2:.4f}, MAE={mae:.5f}")
    return model, summary


# ---------------------------------------------------------------------------
# Step 2: concede model (classification, row-level split, mirrors O1)
# ---------------------------------------------------------------------------

def step2_concede_model(df: pd.DataFrame) -> dict:
    print("\nStep 2: concede model (P(opponent scores within 10 actions)) ...")
    X, y = df[PV_FEATURES], df["label_concede"]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    model = xgb.XGBClassifier(**XGB_KWARGS, eval_metric="logloss")
    model.fit(X_train, y_train)
    model.save_model(CONCEDE_MODEL_PATH)

    p_test = model.predict_proba(X_test)[:, 1]
    auc = float(roc_auc_score(y_test, p_test))
    calib = calibration_table(y_test.values, p_test)
    summary = {
        "n_train": len(X_train), "n_test": len(X_test),
        "positive_rate": float(y.mean()), "auc": auc, "calibration": calib,
    }
    print(f"  n_train={len(X_train)}, n_test={len(X_test)}, positive_rate={y.mean():.4f}")
    print(f"  held-out AUC={auc:.4f}")
    return model, summary


# ---------------------------------------------------------------------------
# Step 3: WP-299 (win probability, Poisson/Markov construction)
# ---------------------------------------------------------------------------

def match_segments_and_goals(match_id: int) -> tuple:
    ev = pd.read_parquet(EVENTS_DIR / f"{match_id}.parquet")
    ev = ev[ev["period"] < SHOOTOUT_PERIOD].sort_values("index").reset_index(drop=True)
    ev["t"] = ev["minute"] + ev["second"] / 60.0
    teams = ev["team"].dropna().unique().tolist()
    if len(teams) != 2 or len(ev) == 0:
        return [], [], 0.0, None, None
    team_a, team_b = teams[0], teams[1]
    is_goal = ((ev["type"] == "Shot") & (ev["shot_outcome"] == "Goal")) | (ev["type"] == "Own Goal Against")
    match_end = float(ev["t"].max())

    score = {team_a: 0, team_b: 0}
    segments, goal_states = [], []
    seg_start = 0.0
    for i in range(len(ev)):
        if not is_goal.iloc[i]:
            continue
        row = ev.iloc[i]
        scorer = row["team"]
        if row["type"] == "Own Goal Against":
            scorer = team_b if row["team"] == team_a else team_a
        t = float(row["t"])
        diff = score[team_a] - score[team_b]
        segments.append((seg_start, t, diff))
        diff_for_scorer = diff if scorer == team_a else -diff
        state = "leading" if diff_for_scorer > 0 else ("trailing" if diff_for_scorer < 0 else "level")
        goal_states.append(state)
        score[scorer] += 1
        seg_start = t
    segments.append((seg_start, match_end, score[team_a] - score[team_b]))
    return segments, goal_states, match_end, team_a, team_b


def estimate_wp_rates(match_ids: list) -> tuple:
    exposure = {"leading": 0.0, "level": 0.0, "trailing": 0.0}
    goals = {"leading": 0, "level": 0, "trailing": 0}
    match_ends = {}
    for mid in match_ids:
        segments, goal_states, match_end, _, _ = match_segments_and_goals(mid)
        match_ends[mid] = match_end
        for (s, e, diff) in segments:
            dur = e - s
            if dur <= 0:
                continue
            if diff == 0:
                exposure["level"] += 2 * dur
            else:
                exposure["leading"] += dur
                exposure["trailing"] += dur
        for state in goal_states:
            goals[state] += 1
    rates = {k: goals[k] / exposure[k] for k in goals}
    return rates, goals, exposure, match_ends


def state_of(d: int) -> str:
    if d > 0:
        return "leading"
    if d < 0:
        return "trailing"
    return "level"


def build_wp_grid(rates: dict, d_max: int, m_max: int, dt: float = 1.0) -> np.ndarray:
    """WP_matrix[d + d_max, m] for d in [-d_max, d_max], m in [0, m_max]."""
    ds = list(range(-d_max, d_max + 1))
    WP = np.zeros((len(ds), m_max + 1))
    for idx, d in enumerate(ds):
        WP[idx, 0] = 1.0 if d > 0 else (0.5 if d == 0 else 0.0)
    for m in range(1, m_max + 1):
        for idx, d in enumerate(ds):
            rf = rates[state_of(d)] * dt
            ra = rates[state_of(-d)] * dt
            stay = 1.0 - rf - ra
            wp_up = WP[idx + 1, m - 1] if idx + 1 < len(ds) else 1.0
            wp_down = WP[idx - 1, m - 1] if idx - 1 >= 0 else 0.0
            WP[idx, m] = stay * WP[idx, m - 1] + rf * wp_up + ra * wp_down
    return WP


def wp_array_lookup(WP: np.ndarray, d_max: int, m_max: int, d_arr, m_arr) -> np.ndarray:
    d_idx = np.clip(np.asarray(d_arr, dtype=int), -d_max, d_max) + d_max
    m_idx = np.clip(np.round(np.asarray(m_arr, dtype=float)).astype(int), 0, m_max)
    return WP[d_idx, m_idx]


def validate_wp(WP: np.ndarray, match_ids: list, d_max: int, m_max: int, bin_width: int) -> dict:
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
                rows.append({"d": d, "m_remaining": m_remaining, "predicted": pred, "observed": outcome})
    df = pd.DataFrame(rows)
    df["m_bin"] = (df["m_remaining"] // bin_width * bin_width).astype(int)
    bucket = df.groupby(["d", "m_bin"]).agg(
        n=("observed", "size"), mean_predicted=("predicted", "mean"), mean_observed=("observed", "mean"),
    ).reset_index()
    bucket["abs_diff_pp"] = (bucket["mean_predicted"] - bucket["mean_observed"]).abs() * 100
    brier = float(((df["predicted"] - df["observed"]) ** 2).mean())
    violations = bucket[(bucket["n"] >= GATE_MIN_N) & (bucket["abs_diff_pp"] > GATE_MAX_PP)]
    passed = len(violations) == 0
    return {
        "n_states": len(df), "brier": brier, "gate_passed": bool(passed),
        "bucket_table": bucket.to_dict("records"), "violations": violations.to_dict("records"),
    }


def step3_win_probability(match_ids: list) -> tuple:
    print("\nStep 3: WP-299 (win probability from the 299-match sample) ...")
    rates, goals, exposure, match_ends = estimate_wp_rates(match_ids)
    d_max = D_MAX
    m_max = int(np.ceil(max(match_ends.values()))) + 1
    print(f"  per-minute scoring rates: {rates}")
    print(f"  goal counts by state: {goals}")
    print(f"  exposure (team-minutes) by state: {exposure}")
    print(f"  grid: d in [-{d_max},{d_max}], m in [0,{m_max}]")
    WP = build_wp_grid(rates, d_max, m_max)
    validation = validate_wp(WP, match_ids, d_max, m_max, BIN_WIDTH_MIN)
    print(f"  validation states: {validation['n_states']}, Brier score: {validation['brier']:.4f}")
    print(f"  gate (n>={GATE_MIN_N} buckets off by >{GATE_MAX_PP}pp): "
          f"{'PASSED' if validation['gate_passed'] else 'FAILED'}")
    if not validation["gate_passed"]:
        print(f"  VIOLATIONS ({len(validation['violations'])} buckets):")
        print(pd.DataFrame(validation["violations"]).to_string())
    summary = {
        "rates": rates, "goals_by_state": goals, "exposure_by_state": exposure,
        "d_max": d_max, "m_max": m_max, "match_ends": {int(k): v for k, v in match_ends.items()},
        **validation,
    }
    return WP, summary


# ---------------------------------------------------------------------------
# Step 4: recompute EV for every option (O2 always; O3 only if validated)
# ---------------------------------------------------------------------------

def build_option_context(match_ids: list, match_ends: dict) -> tuple:
    dir_rows, ctx_frames = [], []
    for mid in match_ids:
        ev = pd.read_parquet(EVENTS_DIR / f"{mid}.parquet")
        ev = ev[ev["period"] < SHOOTOUT_PERIOD].sort_values("index").reset_index(drop=True)
        dirs, _, _ = team_period_directions(ev)
        for (team, period), d in dirs.items():
            dir_rows.append({"match_id": mid, "team": team, "period": period, "direction": d})

        ev["t"] = ev["minute"] * 60 + ev["second"]
        ev["elapsed_minutes"] = ev["minute"] + ev["second"] / 60.0
        period_end = ev.groupby("period")["t"].transform("max")
        time_remaining = (period_end - ev["t"]).values
        teams = ev["team"].dropna().unique().tolist()
        is_goal = ((ev["type"] == "Shot") & (ev["shot_outcome"] == "Goal")) | (ev["type"] == "Own Goal Against")
        team_arr = ev["team"].values
        if len(teams) == 2:
            t0, t1 = teams
            scorer_arr = np.where(
                (ev["type"] == "Own Goal Against").values,
                np.where(team_arr == t0, t1, t0), team_arr,
            )
            goal_flag = is_goal.values
            g0 = np.where(goal_flag & (scorer_arr == t0), 1, 0)
            g1 = np.where(goal_flag & (scorer_arr == t1), 1, 0)
            cum0_before = np.concatenate([[0], np.cumsum(g0)[:-1]])
            cum1_before = np.concatenate([[0], np.cumsum(g1)[:-1]])
            score_diff = np.where(team_arr == t0, cum0_before - cum1_before, cum1_before - cum0_before)
        else:
            score_diff = np.zeros(len(ev))

        match_end = match_ends.get(mid, float(ev["elapsed_minutes"].max()))
        ctx_frames.append(pd.DataFrame({
            "match_id": mid, "event_id": ev["id"].values,
            "time_remaining_period": time_remaining, "score_diff": score_diff,
            "minutes_remaining": match_end - ev["elapsed_minutes"].values,
        }))
    directions = pd.DataFrame(dir_rows)
    context = pd.concat(ctx_frames, ignore_index=True)
    return directions, context


def self_check_context(match_ids_sample: list, directions: pd.DataFrame, context: pd.DataFrame):
    """Compares the vectorized score_diff/time_remaining_period against a
    slow per-row rebuild (decompose.py's own per-event loop style) for a
    couple of matches before trusting it at the full 1.24M-option scale."""
    for mid in match_ids_sample:
        ev = pd.read_parquet(EVENTS_DIR / f"{mid}.parquet")
        ev = ev[ev["period"] < SHOOTOUT_PERIOD].sort_values("index").reset_index(drop=True)
        ev["t"] = ev["minute"] * 60 + ev["second"]
        period_end = ev.groupby("period")["t"].transform("max")
        ev["time_remaining_period"] = period_end - ev["t"]
        teams = ev["team"].dropna().unique().tolist()
        score = {t: 0 for t in teams}
        is_goal = ((ev["type"] == "Shot") & (ev["shot_outcome"] == "Goal")) | (ev["type"] == "Own Goal Against")
        expected = {}
        for i in range(len(ev)):
            row = ev.iloc[i]
            opp = [t for t in teams if t != row["team"]]
            opp = opp[0] if opp else None
            sd = score.get(row["team"], 0) - score.get(opp, 0) if opp else 0
            expected[row["id"]] = (row["time_remaining_period"], sd)
            if is_goal.iloc[i]:
                scorer = row["team"]
                if row["type"] == "Own Goal Against":
                    scorer = opp
                if scorer in score:
                    score[scorer] += 1
        ctx_mid = context[context["match_id"] == mid].set_index("event_id")
        for eid, (tr, sd) in expected.items():
            row = ctx_mid.loc[eid]
            assert abs(row["time_remaining_period"] - tr) < 1e-6, f"{mid}/{eid}: time_remaining mismatch"
            assert row["score_diff"] == sd, f"{mid}/{eid}: score_diff mismatch"
    print(f"Self-check passed on {len(match_ids_sample)} matches: vectorized option context "
          f"matches the per-row rebuild exactly.")


def build_success_turnover_features(opt: pd.DataFrame) -> tuple:
    direction = opt["direction"].values
    opp_direction = -direction

    def norm(x, y, d):
        return np.where(d == 1, x, PITCH_X - x), np.where(d == 1, y, PITCH_Y - y)

    ax, ay = norm(opt["candidate_x"].values, opt["candidate_y"].values, direction)
    px, py = norm(opt["passer_x"].values, opt["passer_y"].values, direction)
    tx, ty = norm(opt["candidate_x"].values, opt["candidate_y"].values, opp_direction)
    opx, opy = norm(opt["passer_x"].values, opt["passer_y"].values, opp_direction)

    X_success = pd.DataFrame({
        "ball_x": ax, "ball_y": ay, "prev_x": px, "prev_y": py,
        "time_remaining_period": opt["time_remaining_period"].values,
        "score_diff": opt["score_diff"].values,
        "play_pattern_code": PATTERN_CODE["Regular Play"],
    })[PV_FEATURES]
    X_turnover = pd.DataFrame({
        "ball_x": tx, "ball_y": ty, "prev_x": opx, "prev_y": opy,
        "time_remaining_period": opt["time_remaining_period"].values,
        "score_diff": -opt["score_diff"].values,
        "play_pattern_code": PATTERN_CODE["From Counter"],
    })[PV_FEATURES]
    return X_success, X_turnover


def compute_ev_o2(opt: pd.DataFrame, model) -> tuple:
    X_success, X_turnover = build_success_turnover_features(opt)
    v_success = model.predict(X_success)
    v_turnover = -model.predict(X_turnover)
    ev = opt["p_success"].values * v_success + (1 - opt["p_success"].values) * v_turnover
    return v_success, v_turnover, ev


def compute_ev_o3(opt: pd.DataFrame, o1_model, concede_model, WP: np.ndarray, d_max: int, m_max: int) -> tuple:
    X_success, X_turnover = build_success_turnover_features(opt)
    p_score_s = o1_model.predict_proba(X_success)[:, 1]
    p_conc_s = concede_model.predict_proba(X_success)[:, 1]
    p_score_t = o1_model.predict_proba(X_turnover)[:, 1]
    p_conc_t = concede_model.predict_proba(X_turnover)[:, 1]

    d = opt["score_diff"].values.astype(int)
    m = opt["minutes_remaining"].values
    wp_d = wp_array_lookup(WP, d_max, m_max, d, m)
    wp_dp = wp_array_lookup(WP, d_max, m_max, d + 1, m)
    wp_dm = wp_array_lookup(WP, d_max, m_max, d - 1, m)
    v_success = p_score_s * (wp_dp - wp_d) + p_conc_s * (wp_dm - wp_d)

    d_opp = -d
    wp_do = wp_array_lookup(WP, d_max, m_max, d_opp, m)
    wp_dop = wp_array_lookup(WP, d_max, m_max, d_opp + 1, m)
    wp_dom = wp_array_lookup(WP, d_max, m_max, d_opp - 1, m)
    v_turnover_opp = p_score_t * (wp_dop - wp_do) + p_conc_t * (wp_dom - wp_do)
    v_turnover = -v_turnover_opp

    ev = opt["p_success"].values * v_success + (1 - opt["p_success"].values) * v_turnover
    return v_success, v_turnover, ev


def has_loc(v) -> bool:
    return v is not None and not (isinstance(v, float) and pd.isna(v))


def compute_realized_o2(match_id: int, model) -> pd.DataFrame:
    """Parametrized copy of decompose.compute_realized_values: `.predict()`
    (regressor) in place of `.predict_proba(...)[:, 1]` (classifier)."""
    ev = pd.read_parquet(EVENTS_DIR / f"{match_id}.parquet")
    ev = ev[ev["period"] < SHOOTOUT_PERIOD].sort_values("index").reset_index(drop=True)
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
    v_success = model.predict(pd.DataFrame(rows_success)[PV_FEATURES])
    v_turnover = -model.predict(pd.DataFrame(rows_turnover)[PV_FEATURES])
    meta_df["realized_value"] = np.where(meta_df["complete"].values, v_success, v_turnover)
    return meta_df[["event_id", "realized_value"]]


def compute_realized_o3(match_id: int, o1_model, concede_model, WP: np.ndarray, d_max: int, m_max: int) -> pd.DataFrame:
    """Parametrized copy of decompose.compute_realized_values using O3's
    composite (P_score, P_concede, dWP) value instead of a single model
    call; same true-pass-outcome framing."""
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
        meta.append({"event_id": r["id"], "complete": complete,
                     "score_diff": score_diff, "minutes_remaining": minutes_remaining})

    if not meta:
        return pd.DataFrame(columns=["event_id", "realized_value"])
    meta_df = pd.DataFrame(meta)
    X_success = pd.DataFrame(rows_success)[PV_FEATURES]
    X_turnover = pd.DataFrame(rows_turnover)[PV_FEATURES]

    p_score_s = o1_model.predict_proba(X_success)[:, 1]
    p_conc_s = concede_model.predict_proba(X_success)[:, 1]
    p_score_t = o1_model.predict_proba(X_turnover)[:, 1]
    p_conc_t = concede_model.predict_proba(X_turnover)[:, 1]

    d = meta_df["score_diff"].values.astype(int)
    m = meta_df["minutes_remaining"].values
    wp_d = wp_array_lookup(WP, d_max, m_max, d, m)
    wp_dp = wp_array_lookup(WP, d_max, m_max, d + 1, m)
    wp_dm = wp_array_lookup(WP, d_max, m_max, d - 1, m)
    v_success = p_score_s * (wp_dp - wp_d) + p_conc_s * (wp_dm - wp_d)

    d_opp = -d
    wp_do = wp_array_lookup(WP, d_max, m_max, d_opp, m)
    wp_dop = wp_array_lookup(WP, d_max, m_max, d_opp + 1, m)
    wp_dom = wp_array_lookup(WP, d_max, m_max, d_opp - 1, m)
    v_turnover_opp = p_score_t * (wp_dop - wp_do) + p_conc_t * (wp_dom - wp_do)
    v_turnover = -v_turnover_opp

    meta_df["realized_value"] = np.where(meta_df["complete"].values, v_success, v_turnover)
    return meta_df[["event_id", "realized_value"]]


def build_per_pass_table_generic(policy: pd.DataFrame, compute_realized_for_match, match_ids: list, verbose=True) -> pd.DataFrame:
    """Same Decision/Execution structure as decompose.build_per_pass_table,
    generalized over an objective-specific realized-value function so O2
    (regressor) and O3 (composite WP value) can reuse it without editing
    the frozen O1 version."""
    policy = policy.copy()
    policy["ev_x_prob"] = policy["ev"] * policy["policy_probability"]
    per_pass = policy.groupby("event_id").agg(
        match_id=("match_id", "first"), team=("team", "first"), player_id=("player_id", "first"),
        ev_chosen=("ev", lambda s: s[policy.loc[s.index, "chosen"]].iloc[0]),
        policy_weighted_ev=("ev_x_prob", "sum"),
    ).reset_index()
    per_pass["decision"] = per_pass["ev_chosen"] - per_pass["policy_weighted_ev"]

    realized_frames = []
    for i, mid in enumerate(match_ids):
        realized_frames.append(compute_realized_for_match(mid))
        if verbose and (i + 1) % 50 == 0:
            print(f"  realized values: {i + 1}/{len(match_ids)} matches")
    realized = pd.concat(realized_frames, ignore_index=True)
    per_pass = per_pass.merge(realized, on="event_id", how="left")
    per_pass["execution"] = per_pass["realized_value"] - per_pass["ev_chosen"]
    return per_pass


def argmax_disagreement(policy: pd.DataFrame, ev_o2, ev_o3=None) -> dict:
    df = policy[["event_id"]].copy()
    df["ev_o1"] = policy["ev"].values
    df["ev_o2"] = ev_o2
    argmax_o1 = df.groupby("event_id")["ev_o1"].idxmax()
    argmax_o2 = df.groupby("event_id")["ev_o2"].idxmax()
    result = {
        "n_passes": int(len(argmax_o1)),
        "o1_vs_o2_disagreement_share": float((argmax_o1 != argmax_o2).mean()),
    }
    if ev_o3 is not None:
        df["ev_o3"] = ev_o3
        argmax_o3 = df.groupby("event_id")["ev_o3"].idxmax()
        result["o1_vs_o3_disagreement_share"] = float((argmax_o1 != argmax_o3).mean())
        result["o2_vs_o3_disagreement_share"] = float((argmax_o2 != argmax_o3).mean())
    return result


def decision_correlations(per_pass_o1, per_pass_o2, per_pass_o3=None) -> dict:
    merged = per_pass_o1[["event_id", "player_id", "decision"]].rename(columns={"decision": "decision_o1"})
    merged = merged.merge(
        per_pass_o2[["event_id", "decision"]].rename(columns={"decision": "decision_o2"}),
        on="event_id", how="inner",
    )
    if per_pass_o3 is not None:
        merged = merged.merge(
            per_pass_o3[["event_id", "decision"]].rename(columns={"decision": "decision_o3"}),
            on="event_id", how="inner",
        )
    dcols = [c for c in merged.columns if c.startswith("decision_")]
    pass_corr = merged[dcols].corr()
    player_means = merged.groupby("player_id")[dcols].mean()
    player_corr = player_means.corr()
    return {
        "n_passes": int(len(merged)), "n_players": int(len(player_means)),
        "pass_level_corr": pass_corr.to_dict(), "player_level_corr": player_corr.to_dict(),
    }


def main():
    print("Step 0 (already committed): docs/specs/analysis-plan-v3.md")

    print("\nPreflight: live memory-pressure check ...")
    free_pct, available_gb = check_memory()
    print(f"  free={free_pct:.0f}%, available={available_gb:.2f}GB")
    if free_pct < PREFLIGHT_MIN_FREE_PCT or available_gb < PREFLIGHT_MIN_AVAILABLE_GB:
        summary = {"status": "BLOCKED", "reason": "preflight memory gate failed",
                   "free_pct": free_pct, "available_gb": available_gb}
        SUMMARY_PATH.write_text(json.dumps(summary, indent=2))
        print("STOPPING: preflight memory gate failed.")
        return

    match_ids = sorted(int(p.stem) for p in EVENTS_DIR.glob("*.parquet"))
    print(f"Matches: {len(match_ids)}")

    print("\nSelf-check: verifying combined row-builder against task09_horizon's "
          "validated feature construction on 3 sample matches ...")
    self_check_features(match_ids[:3])

    print("\nBuilding combined O2/concede row cache (memory-gated, per-match parquet parts) ...")
    df, stopped, n_cached = build_rows_cached_gated(match_ids)
    if stopped:
        summary = {"status": "PARTIAL", "reason": "runtime memory gate tripped during row-building",
                   "n_cached": n_cached, "n_total_matches": len(match_ids)}
        SUMMARY_PATH.write_text(json.dumps(summary, indent=2))
        print("STOPPING before completing the row cache.")
        return
    print(f"Row cache: {n_cached}/{len(match_ids)} matches, {len(df):,} action-state rows")

    o2_model, o2_summary = step1_o2_model(df, match_ids)
    concede_model, concede_summary = step2_concede_model(df)
    WP, wp_summary = step3_win_probability(match_ids)

    policy = pd.read_parquet(POLICY_PATH)
    directions, context = build_option_context(match_ids, wp_summary["match_ends"])
    print("\nSelf-check: verifying vectorized option context on 3 sample matches ...")
    self_check_context(match_ids[:3], directions, context)

    opt = policy.merge(directions, on=["match_id", "team", "period"], how="left")
    opt = opt.merge(context, on=["match_id", "event_id"], how="left")
    assert opt["direction"].notna().all(), "context join: missing direction for some options"
    assert opt["time_remaining_period"].notna().all(), "context join: missing time_remaining_period for some options"
    print(f"\nOption population: {len(opt):,} rows (options_policy.parquet)")

    print("\nStep 4: recomputing EV_O2 for all options ...")
    v_success_o2, v_turnover_o2, ev_o2 = compute_ev_o2(opt, o2_model)
    o2_key_cols = ["match_id", "event_id", "team", "period", "candidate_x", "candidate_y", "chosen"]
    o2_out = opt[o2_key_cols].copy()
    o2_out["v_success"], o2_out["v_turnover"], o2_out["ev"] = v_success_o2, v_turnover_o2, ev_o2
    o2_out.to_parquet(O2_OPTIONS_PATH)
    print(f"  wrote {O2_OPTIONS_PATH}")

    o2_policy_like = opt[["match_id", "event_id", "team", "player_id", "chosen", "p_success", "policy_probability"]].copy()
    o2_policy_like["ev"] = ev_o2
    per_pass_o2 = build_per_pass_table_generic(o2_policy_like, lambda mid: compute_realized_o2(mid, o2_model), match_ids)

    o1_model = xgb.XGBClassifier()
    o1_model.load_model(O1_MODEL_PATH)
    per_pass_o1 = build_per_pass_table(policy, o1_model, verbose=True)

    ev_o3, per_pass_o3, o3_written = None, None, False
    if wp_summary["gate_passed"]:
        print("\nStep 4: recomputing EV_O3 for all options (WP gate passed) ...")
        v_success_o3, v_turnover_o3, ev_o3 = compute_ev_o3(opt, o1_model, concede_model, WP, D_MAX, wp_summary["m_max"])
        o3_out = opt[o2_key_cols].copy()
        o3_out["v_success"], o3_out["v_turnover"], o3_out["ev"] = v_success_o3, v_turnover_o3, ev_o3
        o3_out.to_parquet(O3_OPTIONS_PATH)
        o3_written = True
        print(f"  wrote {O3_OPTIONS_PATH}")

        o3_policy_like = opt[["match_id", "event_id", "team", "player_id", "chosen", "p_success", "policy_probability"]].copy()
        o3_policy_like["ev"] = ev_o3
        per_pass_o3 = build_per_pass_table_generic(
            o3_policy_like, lambda mid: compute_realized_o3(mid, o1_model, concede_model, WP, D_MAX, wp_summary["m_max"]), match_ids,
        )
    else:
        print("\nStep 4: WP gate FAILED -- O3 is UNVALIDATED. Skipping EV_O3/Decision_O3/options_o3.parquet entirely.")

    print("\nSanity checks: argmax disagreement and Decision correlations ...")
    argmax_summary = argmax_disagreement(opt, ev_o2, ev_o3)
    corr_summary = decision_correlations(per_pass_o1, per_pass_o2, per_pass_o3)
    print(json.dumps(argmax_summary, indent=2))
    print(json.dumps({"pass_level_corr": corr_summary["pass_level_corr"],
                       "player_level_corr": corr_summary["player_level_corr"],
                       "n_passes": corr_summary["n_passes"], "n_players": corr_summary["n_players"]},
                      indent=2, default=float))

    summary = {
        "status": "COMPLETE", "n_matches": len(match_ids),
        "o2": o2_summary, "concede": concede_summary, "wp": wp_summary,
        "o3_written": o3_written, "argmax": argmax_summary, "correlations": corr_summary,
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
    print(f"\nWrote summary to {SUMMARY_PATH}")


if __name__ == "__main__":
    main()
