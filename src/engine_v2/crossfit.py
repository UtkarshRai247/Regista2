"""
Task 18, Step 3: the circularity problem in outcome validation. Task
17's possession-level result is partly mechanical -- EV is built from a
value model trained to predict scoring within 10 actions on THESE
events, then tested against whether the possession ends in a shot. Fix
with Task 09's cross-fitting harness (Amendment v2-4): 5 match-level
folds (data/splits/cv_folds.csv, seed 20260920, stratified by
competition-season -- reused as-is; its match_id set is a strict
superset of engine v2's 292-match corpus, so no rebuild is needed).

For each fold: retrain the pass-success model and both value models
(M_for, M_against) -- and, extending Task 09's precedent to engine v2's
now-calibrated policy (Task 18 Steps 1-2), the policy model too -- on
the other four folds, with EXACTLY the frozen hyperparameters/features
of Tasks 15/18 Steps 1-2. Only the training data changes. Score the
held-out fold: p_success_oof, V_net_success_oof/V_net_turnover_oof/
EV_oof (via features.state_features_batch, identical construction to
ev_policy.py's, just with the fold's own models), policy_probability_oof
(restricted candidate set + Step 1's fixed temperature), Decision_oof,
Risk_oof, and Execution_oof (decision_execution_risk.compute_execution_
for_match, reused directly, fold's own M_for/M_against passed in).

Disclosed simplification: the restriction filter's p_success threshold
for selecting the POLICY's TRAINING pool (train folds only) uses each
candidate's original in-sample p_success -- a data-selection criterion,
not a leaked label (the policy model's own features never include
p_success). Held-out TEST-fold candidates are always restricted using
their own fold-specific p_success_oof, so the final EV/Decision for
every held-out pass never uses in-sample information. Step 1's fitted
temperature (a single global scalar, already validated on held-out
policy accuracy) is reused fixed across all 5 folds rather than refit
per fold, to avoid 5x the tuning-adjacent computation for a parameter
whose role is calibration sharpness, not a decision-relevant threshold.

Run: python src/engine_v2/crossfit.py
"""
import json
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import roc_auc_score

from geometry import team_period_directions
from features import state_features_batch
from value_models import PATTERN_CODE, STATE_FEATURES, XGB_KWARGS as VM_KWARGS, OUT_PATH as VALUE_ROWS_PATH
from pass_success_v2 import XGB_KWARGS as PS_KWARGS, load_chosen_rows
from decision_execution_risk import compute_execution_for_match
from common import CANDIDATE_FEATURES, prep_X
from policy_baseline_fix import RESTRICT_MIN_P_SUCCESS, RESTRICT_MAX_DISTANCE_U

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
EVENTS_DIR = DATA_DIR / "raw" / "events"
FRAMES_DIR = DATA_DIR / "raw" / "frames"
EV_DIR = DATA_DIR / "processed" / "engine_v2" / "options_ev"
FOLDS_PATH = DATA_DIR / "splits" / "cv_folds.csv"
STEP1_SUMMARY_PATH = DATA_DIR / "engine_v2_step1_policy_baseline_fix.json"
OUT_PATH = DATA_DIR / "processed" / "engine_v2" / "pass_der_crossfit.parquet"
SUMMARY_PATH = DATA_DIR / "engine_v2_step3_crossfit.json"

POLICY_XGB_KWARGS = dict(n_estimators=200, max_depth=4, learning_rate=0.05,
                          subsample=0.8, colsample_bytree=0.8, random_state=42, eval_metric="logloss")
NEG_SAMPLES_PER_PASS = 10
N_FOLDS = 5


def build_ev_oof_for_match(match_id: int, cand: pd.DataFrame, model_for, model_against) -> pd.DataFrame:
    """cand: this match's full options_ev rows, already carrying a
    fold-specific `p_success_oof` column. Recomputes V_net_success_oof/
    V_net_turnover_oof/EV_oof using the fold's own M_for/M_against --
    identical geometry to ev_policy.build_ev_for_match, adapted to take
    an in-memory, already-scored dataframe instead of reading Task 15's
    frozen options_scored file."""
    frames = pd.read_parquet(FRAMES_DIR / f"{match_id}.parquet")
    frames_by_event = {eid: g for eid, g in frames.groupby("id")}
    events = pd.read_parquet(EVENTS_DIR / f"{match_id}.parquet").sort_values("index").reset_index(drop=True)
    events["t"] = events["minute"] * 60 + events["second"]
    period_end = events.groupby("period")["t"].transform("max")
    directions = team_period_directions(events)
    teams = events["team"].dropna().unique().tolist()
    is_goal = ((events["type"] == "Shot") & (events["shot_outcome"] == "Goal")) | (events["type"] == "Own Goal Against")
    score = {t: 0 for t in teams}
    ctx_by_event = {}
    for i in range(len(events)):
        row = events.iloc[i]
        team = row["team"]
        opp_teams = [t for t in teams if t != team]
        opponent = opp_teams[0] if opp_teams else None
        ctx_by_event[row["id"]] = {
            "score_diff": score.get(team, 0) - score.get(opponent, 0) if opponent else 0,
            "time_remaining_period": float(period_end.iloc[i] - row["t"]),
            "direction": directions.get((team, row["period"]), 1),
        }
        if is_goal.iloc[i]:
            scorer = opponent if row["type"] == "Own Goal Against" else team
            if scorer in score:
                score[scorer] += 1

    succ_rows, turn_rows, order = [], [], []
    for eid, g in cand.groupby("event_id", sort=False):
        ctx = ctx_by_event.get(eid)
        frame = frames_by_event.get(eid)
        if ctx is None or frame is None:
            continue
        direction = ctx["direction"]
        opp_direction = -direction
        passer_raw = np.array([g["passer_x"].iloc[0], g["passer_y"].iloc[0]])
        cand_raw = g[["candidate_x", "candidate_y"]].values.astype(float)

        teammates = frame[(frame["teammate"] == True) & (frame["actor"] == False)]
        opponents = frame[frame["teammate"] == False]
        team_raw = np.array([list(l) for l in teammates["location"]], dtype=float) if len(teammates) else np.zeros((0, 2))
        opp_raw = np.array([list(l) for l in opponents["location"]], dtype=float) if len(opponents) else np.zeros((0, 2))

        succ = state_features_batch(cand_raw, passer_raw, direction, team_raw, opp_raw, len(frame))
        succ["time_remaining_period"] = np.full(len(g), ctx["time_remaining_period"])
        succ["score_diff"] = np.full(len(g), ctx["score_diff"])
        succ["play_pattern_code"] = np.full(len(g), PATTERN_CODE["Regular Play"])

        turn = state_features_batch(cand_raw, passer_raw, opp_direction, opp_raw, team_raw, len(frame))
        turn["time_remaining_period"] = np.full(len(g), ctx["time_remaining_period"])
        turn["score_diff"] = np.full(len(g), -ctx["score_diff"])
        turn["play_pattern_code"] = np.full(len(g), PATTERN_CODE["From Counter"])

        succ_rows.append(pd.DataFrame(succ))
        turn_rows.append(pd.DataFrame(turn))
        order.append(g.index.values)

    if not succ_rows:
        return cand.iloc[0:0]

    X_succ = pd.concat(succ_rows, ignore_index=True)[STATE_FEATURES].astype(float)
    X_turn = pd.concat(turn_rows, ignore_index=True)[STATE_FEATURES].astype(float)
    p_for_succ = model_for.predict_proba(X_succ)[:, 1]
    p_against_succ = model_against.predict_proba(X_succ)[:, 1]
    p_for_turn = model_for.predict_proba(X_turn)[:, 1]
    p_against_turn = model_against.predict_proba(X_turn)[:, 1]
    v_net_success = p_for_succ - p_against_succ
    v_net_turnover = p_against_turn - p_for_turn

    idx_order = np.concatenate(order)
    cand = cand.loc[idx_order].reset_index(drop=True)
    cand["V_net_success"] = v_net_success.astype("float32")
    cand["V_net_turnover"] = v_net_turnover.astype("float32")
    cand["EV"] = (cand["p_success_oof"] * cand["V_net_success"] + (1 - cand["p_success_oof"]) * cand["V_net_turnover"]).astype("float32")
    return cand


def softmax_per_group(scores: np.ndarray, groups: np.ndarray) -> np.ndarray:
    df = pd.DataFrame({"score": scores, "group": groups})
    out = np.empty(len(df))
    for _, g in df.groupby("group"):
        s = g["score"].values
        e = np.exp(s - s.max())
        out[g.index] = e / e.sum()
    return out


def main():
    t_start = time.time()
    print("Step 3: cross-fitting harness (Task 09 / Amendment v2-4) ...")
    folds = pd.read_csv(FOLDS_PATH)
    v2_match_ids = sorted(int(p.stem) for p in EV_DIR.glob("*.parquet"))
    folds = folds[folds["match_id"].isin(v2_match_ids)]
    print(f"  fold file matches restricted to engine v2's {len(v2_match_ids)} matches: {len(folds)} matched")
    fold_of = dict(zip(folds["match_id"], folds["fold"]))
    for mid in v2_match_ids:
        if mid not in fold_of:
            print(f"  WARNING: match {mid} not in cv_folds.csv, excluding from cross-fit")
    v2_match_ids = [m for m in v2_match_ids if m in fold_of]

    step1 = json.loads(STEP1_SUMMARY_PATH.read_text())
    T = step1["fitted_temperature"]
    fill_values = step1["fill_values"]

    chosen_pop = load_chosen_rows()
    chosen_pop = chosen_pop[chosen_pop["match_id"].isin(v2_match_ids)]
    value_rows = pd.read_parquet(VALUE_ROWS_PATH)
    value_rows = value_rows[value_rows["match_id"].isin(v2_match_ids)]

    ps_oof_pred, ps_oof_true = [], []
    for_oof_pred, for_oof_true = [], []
    against_oof_pred, against_oof_true = [], []
    policy_oof_ranks = []
    all_der_rows = []

    for fold_id in range(N_FOLDS):
        t_fold = time.time()
        test_mids = set(folds.loc[folds["fold"] == fold_id, "match_id"])
        train_mids = set(v2_match_ids) - test_mids
        print(f"\n  Fold {fold_id}: {len(train_mids)} train matches, {len(test_mids)} test matches")

        # --- pass-success ---
        ps_train = chosen_pop[chosen_pop["match_id"].isin(train_mids)]
        X_ps, _ = prep_X(ps_train, CANDIDATE_FEATURES)
        ps_model = xgb.XGBClassifier(**PS_KWARGS)
        ps_model.fit(X_ps, ps_train["pass_complete"].astype(int))

        ps_test = chosen_pop[chosen_pop["match_id"].isin(test_mids)]
        X_ps_test, _ = prep_X(ps_test, CANDIDATE_FEATURES, fill_values)
        ps_test_pred = ps_model.predict_proba(X_ps_test)[:, 1]
        ps_oof_pred.extend(ps_test_pred.tolist())
        ps_oof_true.extend(ps_test["pass_complete"].astype(int).tolist())

        # --- value models ---
        vm_train = value_rows[value_rows["match_id"].isin(train_mids)]
        vm_test = value_rows[value_rows["match_id"].isin(test_mids)]
        X_vm_train = vm_train[STATE_FEATURES].astype(float)
        X_vm_test = vm_test[STATE_FEATURES].astype(float)

        model_for = xgb.XGBClassifier(**VM_KWARGS)
        model_for.fit(X_vm_train, vm_train["label_for"])
        for_pred = model_for.predict_proba(X_vm_test)[:, 1]
        for_oof_pred.extend(for_pred.tolist())
        for_oof_true.extend(vm_test["label_for"].tolist())

        model_against = xgb.XGBClassifier(**VM_KWARGS)
        model_against.fit(X_vm_train, vm_train["label_against"])
        against_pred = model_against.predict_proba(X_vm_test)[:, 1]
        against_oof_pred.extend(against_pred.tolist())
        against_oof_true.extend(vm_test["label_against"].tolist())
        print(f"    models trained ({time.time() - t_fold:.1f}s)")

        # --- score held-out fold: p_success_oof, EV_oof, restricted+policy ---
        fold_der_rows = []
        for mid in sorted(test_mids):
            cand = pd.read_parquet(EV_DIR / f"{mid}.parquet")
            X_cand, _ = prep_X(cand, CANDIDATE_FEATURES, fill_values)
            cand["p_success_oof"] = ps_model.predict_proba(X_cand)[:, 1]

            cand = build_ev_oof_for_match(mid, cand, model_for, model_against)
            if len(cand) == 0:
                continue

            restricted = cand[(cand["p_success_oof"] >= RESTRICT_MIN_P_SUCCESS) & (~cand["offside_destination"])
                               & (cand["distance_u"] <= RESTRICT_MAX_DISTANCE_U)]
            fold_der_rows.append((mid, cand, restricted))

        # policy training pool: restricted TRAIN-fold candidates, using
        # in-sample p_success for the restriction filter (disclosed above)
        train_restricted_parts = []
        for mid in sorted(train_mids):
            df = pd.read_parquet(EV_DIR / f"{mid}.parquet",
                                  columns=CANDIDATE_FEATURES + ["match_id", "event_id", "chosen", "p_success",
                                                                  "offside_destination"])
            r = df[(df["p_success"] >= RESTRICT_MIN_P_SUCCESS) & (~df["offside_destination"])
                   & (df["distance_u"] <= RESTRICT_MAX_DISTANCE_U)]
            chosen_r = r[r["chosen"]]
            unchosen_r = r[~r["chosen"]]
            n_neg = min(NEG_SAMPLES_PER_PASS * len(chosen_r), len(unchosen_r))
            neg_sample = unchosen_r.sample(n=n_neg, random_state=42 + fold_id) if n_neg > 0 else unchosen_r.iloc[0:0]
            train_restricted_parts.append(pd.concat([chosen_r, neg_sample], ignore_index=True))
        policy_train_pool = pd.concat(train_restricted_parts, ignore_index=True)
        X_pol, _ = prep_X(policy_train_pool, CANDIDATE_FEATURES)
        policy_model = xgb.XGBClassifier(**POLICY_XGB_KWARGS)
        policy_model.fit(X_pol, policy_train_pool["chosen"].astype(int))
        print(f"    policy trained on {len(policy_train_pool)} rows ({time.time() - t_fold:.1f}s total)")

        fold_records = []
        for mid, cand, restricted in fold_der_rows:
            if len(restricted) == 0:
                continue
            X_r, _ = prep_X(restricted, CANDIDATE_FEATURES, fill_values)
            raw_score = policy_model.predict_proba(X_r)[:, 1]
            restricted = restricted.copy()
            restricted["policy_probability"] = softmax_per_group(raw_score / T, restricted["event_id"].values)
            restricted["var_option"] = restricted["p_success_oof"] * (1 - restricted["p_success_oof"]) * \
                (restricted["V_net_success"] - restricted["V_net_turnover"]) ** 2
            restricted["ev_x_prob"] = restricted["EV"] * restricted["policy_probability"]
            restricted["var_x_prob"] = restricted["var_option"] * restricted["policy_probability"]

            chosen_rows = cand[cand["chosen"]].set_index("event_id")
            var_chosen_all = chosen_rows["p_success_oof"] * (1 - chosen_rows["p_success_oof"]) * \
                (chosen_rows["V_net_success"] - chosen_rows["V_net_turnover"]) ** 2

            for eid, g in restricted.groupby("event_id"):
                if bool(g["chosen"].any()):
                    ranked = g.sort_values("policy_probability", ascending=False).reset_index(drop=True)
                    rank = ranked.index[ranked["chosen"]].tolist()[0]
                    policy_oof_ranks.append(rank)
                if eid not in chosen_rows.index:
                    continue
                fold_records.append({
                    "match_id": mid, "event_id": eid, "team": chosen_rows.loc[eid, "team"],
                    "player_id": chosen_rows.loc[eid, "player_id"],
                    "ev_chosen": float(chosen_rows.loc[eid, "EV"]),
                    "var_chosen": float(var_chosen_all.loc[eid]),
                    "policy_weighted_ev": float(g["ev_x_prob"].sum()),
                    "policy_weighted_var": float(g["var_x_prob"].sum()),
                })

        # --- Execution (reuses decision_execution_risk.compute_execution_for_match, fold's own models) ---
        fold_der_df = pd.DataFrame(fold_records)
        ev_lookup_by_match = {mid: g.set_index("event_id")["ev_chosen"] for mid, g in fold_der_df.groupby("match_id")}
        exec_by_match_event = {}
        for mid in sorted(test_mids):
            ev_lookup = ev_lookup_by_match.get(mid)
            if ev_lookup is None or len(ev_lookup) == 0:
                continue
            full_chosen = pd.read_parquet(EV_DIR / f"{mid}.parquet", columns=["match_id", "event_id", "team", "player_id", "chosen"])
            full_chosen = full_chosen[full_chosen["chosen"]][["match_id", "event_id", "team", "player_id"]].copy()
            full_chosen["EV"] = full_chosen["event_id"].map(ev_lookup)
            full_chosen = full_chosen.dropna(subset=["EV"])
            exec_rows, _, _, _ = compute_execution_for_match(mid, full_chosen, model_for, model_against)
            for r in exec_rows:
                exec_by_match_event[(mid, r["event_id"])] = r["execution"]

        fold_der_df["execution"] = fold_der_df.apply(
            lambda r: exec_by_match_event.get((r["match_id"], r["event_id"])), axis=1)
        all_der_rows.append(fold_der_df)

        print(f"  Fold {fold_id} done ({time.time() - t_fold:.1f}s)")

    der_df = pd.concat(all_der_rows, ignore_index=True)
    der_df["decision"] = der_df["ev_chosen"] - der_df["policy_weighted_ev"]
    der_df["risk"] = der_df["var_chosen"] - der_df["policy_weighted_var"]
    der_df.to_parquet(OUT_PATH)
    print(f"\n  Cross-fitted Decision/Execution/Risk: {len(der_df)} passes "
          f"({der_df['execution'].notna().sum()} with valid Execution)")

    ps_auc_oof = float(roc_auc_score(ps_oof_true, ps_oof_pred))
    for_auc_oof = float(roc_auc_score(for_oof_true, for_oof_pred))
    against_auc_oof = float(roc_auc_score(against_oof_true, against_oof_pred))
    policy_ranks = np.array(policy_oof_ranks)
    policy_top1_oof = float((policy_ranks == 0).mean())
    policy_top3_oof = float((policy_ranks < 3).mean())

    print(f"\n  OOF AUC -- pass_success: {ps_auc_oof:.4f}, M_for: {for_auc_oof:.4f}, M_against: {against_auc_oof:.4f}")
    print(f"  OOF policy top1: {policy_top1_oof:.4f}, top3: {policy_top3_oof:.4f}")
    print(f"\n  Total wall clock: {time.time() - t_start:.1f}s")

    summary = {
        "n_folds": N_FOLDS, "n_matches": len(v2_match_ids),
        "n_der_rows": len(der_df), "n_with_execution": int(der_df["execution"].notna().sum()),
        "oof_auc": {"pass_success": ps_auc_oof, "M_for": for_auc_oof, "M_against": against_auc_oof},
        "oof_policy": {"top1_accuracy": policy_top1_oof, "top3_accuracy": policy_top3_oof,
                        "n_covered": len(policy_ranks)},
        "wall_clock_seconds": time.time() - t_start,
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
    print(f"\nWrote {SUMMARY_PATH}")
    return summary


if __name__ == "__main__":
    main()
