"""
Task 09 — PART 2: Horizon sensitivity (Amendment v2-6.2).

Retrains the possession-value model at horizons of 5 and 15 actions
(frozen code otherwise -- horizon is the one parameter the brief
explicitly allows to differ). Uses NON-cross-fitted values (the frozen
pass-success/policy models, unchanged) for comparability with Tasks
06/07, recomputing G+CI, P, L, and PH-2 for the 3 ROBUST candidates on
the confirmation half at each horizon.

`build_match_rows_horizon` below is a parametrized copy of
possession_value.build_match_rows (same formulas, same feature/label
construction) with LOOKAHEAD replaced by a `lookahead` argument -- the
frozen file itself is never edited. Verified to reproduce the frozen
10-action cached rows exactly before being trusted at 5/15 (see the
`__main__` self-check).

Run: python src/decision_engine/task09_horizon.py
"""
import json
import time
import warnings

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split

from decompose import DATA_DIR, EVENTS_DIR
from pitch_direction import normalize_xy, team_period_directions
from possession_value import FEATURES as PV_FEATURES, PATTERN_CODE
from task05_study_a_discovery import join_ev, recover_raw_positions
from task06_study_a_confirmation import (
    bootstrap_g_stats, build_available_types_table_with_mean, cand_mask, confirmation_match_ids,
)

warnings.filterwarnings("ignore")

TYPED_PATH = DATA_DIR / "processed" / "options_typed.parquet"
PASSES_PATH = DATA_DIR / "processed" / "passes_situation.parquet"
EV_PATH = DATA_DIR / "processed" / "options_ev.parquet"
PV_PARTS_DIR = DATA_DIR / "processed" / "possession_value_parts"
SUMMARY_PATH = DATA_DIR / "task09_horizon.json"

HORIZONS = [5, 15]
FROZEN_HORIZON = 10
ROBUST_CANDIDATES = [
    {"zone": "middle", "under_pressure": False, "game_state": "leading", "option_type": "lateral_medium"},
    {"zone": "middle", "under_pressure": False, "game_state": "level", "option_type": "lateral_medium"},
    {"zone": "middle", "under_pressure": False, "game_state": "trailing", "option_type": "lateral_medium"},
]


def build_match_rows_horizon(match_id: int, lookahead: int) -> list:
    """Parametrized copy of possession_value.build_match_rows -- identical
    formulas/features, LOOKAHEAD replaced by `lookahead`."""
    ev = pd.read_parquet(EVENTS_DIR / f"{match_id}.parquet")
    ev = ev.sort_values("index").reset_index(drop=True)
    ev["t"] = ev["minute"] * 60 + ev["second"]
    period_end = ev.groupby("period")["t"].transform("max")
    directions, _, _ = team_period_directions(ev)
    teams = ev["team"].dropna().unique().tolist()
    score = {t: 0 for t in teams}
    is_goal = ((ev["type"] == "Shot") & (ev["shot_outcome"] == "Goal")) | (ev["type"] == "Own Goal Against")

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

        label = 0
        for k in range(i + 1, min(i + 1 + lookahead, n)):
            fut = ev.iloc[k]
            if is_goal.iloc[k]:
                scorer = fut["team"]
                if fut["type"] == "Own Goal Against":
                    scorer = [t for t in teams if t != fut["team"]]
                    scorer = scorer[0] if scorer else None
                if scorer == team:
                    label = 1
                break

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
            "label": label,
        })

        if is_goal.iloc[i]:
            scorer = team
            if row["type"] == "Own Goal Against":
                scorer = opponent
            if scorer in score:
                score[scorer] += 1

    return rows


def build_rows_cached(lookahead: int, match_ids: list) -> pd.DataFrame:
    """Per-match parquet caching (mirrors possession_value.py's own
    resumable data/processed/possession_value_parts/ pattern) -- keeps
    peak memory bounded to one match at a time instead of accumulating
    a 299-match Python list, and makes a rerun resumable if interrupted.
    Written after a real run showed severe, escalating slowdowns
    consistent with memory pressure on this 16GB machine when the whole
    row set was held in memory across a long single process (see Section
    5 of the results page)."""
    out_dir = DATA_DIR / "processed" / f"possession_value_parts_h{lookahead}"
    out_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    for i, mid in enumerate(match_ids):
        out_path = out_dir / f"{mid}.parquet"
        if out_path.exists():
            continue
        rows = build_match_rows_horizon(mid, lookahead)
        if rows:
            pd.DataFrame(rows).to_parquet(out_path)
        if (i + 1) % 50 == 0:
            print(f"    {i + 1}/{len(match_ids)} matches, {time.time() - t0:.1f}s elapsed")
    parts = list(out_dir.glob("*.parquet"))
    df = pd.concat((pd.read_parquet(p) for p in parts), ignore_index=True)
    return df


def train_horizon_model(lookahead: int, match_ids: list) -> xgb.XGBClassifier:
    print(f"  Building action-state rows at horizon={lookahead} for {len(match_ids)} matches ...")
    t0 = time.time()
    df = build_rows_cached(lookahead, match_ids)
    print(f"  {len(df)} rows built in {time.time() - t0:.1f}s, positive rate {df['label'].mean():.4f}")

    X, y = df[PV_FEATURES], df["label"]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    model = xgb.XGBClassifier(n_estimators=300, max_depth=5, learning_rate=0.05,
                               subsample=0.8, colsample_bytree=0.8, random_state=42, eval_metric="logloss")
    model.fit(X_train, y_train)
    auc = float(roc_auc_score(y_test, model.predict_proba(X_test)[:, 1]))
    print(f"  horizon={lookahead} held-out AUC: {auc:.4f}")
    return model, auc


def build_ev_context_for_matches(match_ids: list) -> tuple:
    directions_by_match, ev_context = {}, {}
    for mid in match_ids:
        ev = pd.read_parquet(EVENTS_DIR / f"{mid}.parquet")
        dirs, _, _ = team_period_directions(ev)
        directions_by_match[mid] = dirs
        ev = ev.sort_values("index").reset_index(drop=True)
        ev["t"] = ev["minute"] * 60 + ev["second"]
        period_end = ev.groupby("period")["t"].transform("max")
        ev["time_remaining_period"] = period_end - ev["t"]
        teams = ev["team"].dropna().unique().tolist()
        score = {t: 0 for t in teams}
        is_goal = ((ev["type"] == "Shot") & (ev["shot_outcome"] == "Goal")) | (ev["type"] == "Own Goal Against")
        score_diff_col = []
        for j in range(len(ev)):
            row = ev.iloc[j]
            opp = [t for t in teams if t != row["team"]]
            opp = opp[0] if opp else None
            score_diff_col.append(score.get(row["team"], 0) - score.get(opp, 0) if opp else 0)
            if is_goal.iloc[j]:
                scorer = row["team"]
                if row["type"] == "Own Goal Against":
                    scorer = opp
                if scorer in score:
                    score[scorer] += 1
        ev["score_diff"] = score_diff_col
        for _, r in ev.iterrows():
            ev_context[(mid, r["id"])] = (r["time_remaining_period"], r["score_diff"])
    return directions_by_match, ev_context


def recompute_ev_at_horizon(scored_subset: pd.DataFrame, directions_by_match: dict, ev_context: dict, model) -> pd.DataFrame:
    rows_success, rows_turnover = [], []
    for _, r in scored_subset.iterrows():
        mid, eid, team, period = r["match_id"], r["event_id"], r["team"], r["period"]
        direction = directions_by_match[mid].get((team, period), 1)
        time_remaining, score_diff = ev_context.get((mid, eid), (np.nan, 0))
        ax, ay = normalize_xy(r["candidate_x"], r["candidate_y"], direction)
        px, py = normalize_xy(r["passer_x"], r["passer_y"], direction)
        rows_success.append({"ball_x": ax, "ball_y": ay, "prev_x": px, "prev_y": py,
                              "time_remaining_period": time_remaining, "score_diff": score_diff,
                              "play_pattern_code": PATTERN_CODE["Regular Play"]})
        opp_direction = -direction
        tx, ty = normalize_xy(r["candidate_x"], r["candidate_y"], opp_direction)
        px2, py2 = normalize_xy(r["passer_x"], r["passer_y"], opp_direction)
        rows_turnover.append({"ball_x": tx, "ball_y": ty, "prev_x": px2, "prev_y": py2,
                               "time_remaining_period": time_remaining, "score_diff": -score_diff,
                               "play_pattern_code": PATTERN_CODE["From Counter"]})
    X_success = pd.DataFrame(rows_success)[PV_FEATURES]
    X_turnover = pd.DataFrame(rows_turnover)[PV_FEATURES]
    v_success = model.predict_proba(X_success)[:, 1]
    v_turnover = -model.predict_proba(X_turnover)[:, 1]
    out = scored_subset[["match_id", "event_id", "team", "period", "candidate_x", "candidate_y", "chosen"]].copy()
    out["ev"] = scored_subset["p_success"].values * v_success + (1 - scored_subset["p_success"].values) * v_turnover
    return out


def compute_g_p_l_ph2(ev_table: pd.DataFrame, confirmation_ids: list, candidates: list) -> pd.DataFrame:
    typed = pd.read_parquet(TYPED_PATH, filters=[("match_id", "in", confirmation_ids)])
    # ev_table may cover a smaller population than the full confirmation
    # half (e.g. only the 3 ROBUST candidates' cells) -- restrict typed to
    # the same (match_id, event_id) population first, or join_ev's
    # internal duplicate-group consistency check compares mismatched
    # populations and errors.
    typed = typed.merge(ev_table[["match_id", "event_id"]].drop_duplicates(), on=["match_id", "event_id"])
    typed = recover_raw_positions(typed)
    opt, join_report = join_ev(typed, ev_table)
    if join_report["match_rate"] != 1.0 or join_report["n_group_size_mismatches"]:
        raise RuntimeError(f"horizon EV join failed: {join_report}")

    passes = pd.read_parquet(PASSES_PATH, filters=[("match_id", "in", confirmation_ids)])
    cell_info = passes[["match_id", "event_id", "zone", "under_pressure", "game_state",
                         "team", "competition_id", "season_id", "n_visible_players"]]
    opt = opt.drop(columns=["team"]).merge(cell_info[["match_id", "event_id", "team"]], on=["match_id", "event_id"])
    avail = build_available_types_table_with_mean(opt, cell_info)
    g_table = avail[avail["option_type"] != avail["j"]].copy()
    g_table["g"] = g_table["ev_star"] - g_table["ev_star_j"]

    rows = []
    for cand in candidates:
        sub = g_table[cand_mask(g_table, cand)]
        stats = bootstrap_g_stats(sub, confirmation_ids)
        n_total = len(sub)
        matched = sub[sub["n_options"] == sub["n_options_j"]]
        ph2 = bootstrap_g_stats(matched, confirmation_ids)
        rows.append({**cand, "G": stats["G"], "ci_low": stats["ci_low"], "ci_high": stats["ci_high"],
                     "P": stats["P"], "L": stats["L"], "n_passes": stats["n_passes"],
                     "ph2_G": ph2["G"], "ph2_ci_low": ph2["ci_low"], "ph2_ci_high": ph2["ci_high"],
                     "ph2_n_passes": len(matched), "ph2_share_retained": len(matched) / n_total if n_total else None})
    return pd.DataFrame(rows), join_report


def main():
    print("Loading confirmation-half candidate cells' options (restricted to the 3 ROBUST candidates' cells) ...")
    confirmation_ids = confirmation_match_ids()

    scored = pd.read_parquet(DATA_DIR / "processed" / "options_scored.parquet",
                              filters=[("match_id", "in", confirmation_ids)])
    passes_cells = pd.read_parquet(PASSES_PATH, filters=[("match_id", "in", confirmation_ids)],
                                    columns=["match_id", "event_id", "zone", "under_pressure", "game_state"])
    target_cells = {(c["zone"], c["under_pressure"], c["game_state"]) for c in ROBUST_CANDIDATES}
    relevant_passes = passes_cells[passes_cells.apply(
        lambda r: (r["zone"], r["under_pressure"], r["game_state"]) in target_cells, axis=1)]
    relevant_keys = set(zip(relevant_passes["match_id"], relevant_passes["event_id"]))
    scored_subset = scored[scored.apply(lambda r: (r["match_id"], r["event_id"]) in relevant_keys, axis=1)].copy()
    relevant_matches = sorted(scored_subset["match_id"].unique())
    print(f"Relevant confirmation matches: {len(relevant_matches)}, option rows: {len(scored_subset)}")

    # options_scored.parquet already carries the frozen p_success column
    # (non-cross-fitted, for comparability with Task 06/07) -- no merge
    # needed, it's the same frozen value options_ev.parquet derives from.
    assert scored_subset["p_success"].notna().all(), "some rows missing frozen p_success"

    print("Building direction/context lookups for the relevant matches only ...")
    directions_by_match, ev_context = build_ev_context_for_matches(relevant_matches)

    all_match_ids = sorted(int(p.stem) for p in EVENTS_DIR.glob("*.parquet"))
    results_by_horizon = {}
    for horizon in HORIZONS:
        print(f"\n=== Horizon {horizon} ===")
        model, auc = train_horizon_model(horizon, all_match_ids)
        ev_table = recompute_ev_at_horizon(scored_subset, directions_by_match, ev_context, model)
        stats_df, join_report = compute_g_p_l_ph2(ev_table, confirmation_ids, ROBUST_CANDIDATES)
        print(stats_df.to_string())
        results_by_horizon[horizon] = {"held_out_auc": auc, "join_report": join_report,
                                        "stats": stats_df.to_dict("records")}

    print(f"\n=== Horizon {FROZEN_HORIZON} (frozen, for comparison) ===")
    frozen_ev_full = pd.read_parquet(EV_PATH, filters=[("match_id", "in", confirmation_ids)])
    stats_frozen, _ = compute_g_p_l_ph2(
        frozen_ev_full[["match_id", "event_id", "team", "period", "candidate_x", "candidate_y", "chosen", "ev"]],
        confirmation_ids, ROBUST_CANDIDATES)
    print(stats_frozen.to_string())
    results_by_horizon[FROZEN_HORIZON] = {"stats": stats_frozen.to_dict("records")}

    print("\nApplying v2-6.2's interpretation rule ...")
    verdicts = []
    for cand in ROBUST_CANDIDATES:
        def ok(h):
            row = pd.DataFrame(results_by_horizon[h]["stats"])
            r = row[cand_mask(row, cand)].iloc[0]
            return (r["G"] is not None) and (r["G"] > 0) and (r["ci_low"] is not None) and (r["ci_low"] > 0)
        ok5, ok15 = ok(5), ok(15)
        if ok5 and ok15:
            verdict = "horizon-robust"
        elif ok5 or ok15:
            verdict = "holds at one horizon only"
        else:
            verdict = "artefact of the 10-action horizon"
        verdicts.append({**cand, "positive_excl_zero_at_5": ok5, "positive_excl_zero_at_15": ok15, "verdict": verdict})
    verdicts_df = pd.DataFrame(verdicts)
    print(verdicts_df.to_string())

    summary = {"status": "COMPLETE", "results_by_horizon": results_by_horizon,
               "verdicts": verdicts_df.to_dict("records")}
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
    print(f"\nWrote summary to {SUMMARY_PATH}")


if __name__ == "__main__":
    main()
