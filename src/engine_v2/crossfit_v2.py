"""
Task 19, Step 4: re-run the cross-fitting harness with offside filtering
DROPPED from the restriction (per Step 2's calibration verdict), using
Task 19's own refit temperature. Identical to crossfit.py in every other
respect -- same 5 folds, same models/hyperparameters, same "no other
engine change" scope -- reuses build_ev_oof_for_match and
softmax_per_group from crossfit.py unchanged; only the two restriction
lines (dropping `~cand["offside_destination"]` / `~df["offside_destination"]`)
and the temperature/fill-values source differ.

Run: python src/engine_v2/crossfit_v2.py
"""
import json
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import roc_auc_score

from value_models import STATE_FEATURES, XGB_KWARGS as VM_KWARGS, OUT_PATH as VALUE_ROWS_PATH
from pass_success_v2 import XGB_KWARGS as PS_KWARGS, load_chosen_rows
from decision_execution_risk import compute_execution_for_match
from common import CANDIDATE_FEATURES, prep_X
from policy_baseline_fix import RESTRICT_MIN_P_SUCCESS, RESTRICT_MAX_DISTANCE_U
from crossfit import build_ev_oof_for_match, softmax_per_group, FOLDS_PATH, POLICY_XGB_KWARGS, NEG_SAMPLES_PER_PASS, N_FOLDS

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
EV_DIR = DATA_DIR / "processed" / "engine_v2" / "options_ev"
STEP3_SUMMARY_PATH = DATA_DIR / "engine_v2_step3_policy_baseline_fix_v2.json"
OUT_PATH = DATA_DIR / "processed" / "engine_v2" / "pass_der_crossfit_v2.parquet"
SUMMARY_PATH = DATA_DIR / "engine_v2_step4_crossfit.json"


def main():
    t_start = time.time()
    print("Step 4: cross-fitting harness, offside filtering dropped ...")
    folds = pd.read_csv(FOLDS_PATH)
    v2_match_ids = sorted(int(p.stem) for p in EV_DIR.glob("*.parquet"))
    folds = folds[folds["match_id"].isin(v2_match_ids)]
    fold_of = dict(zip(folds["match_id"], folds["fold"]))
    v2_match_ids = [m for m in v2_match_ids if m in fold_of]
    print(f"  {len(v2_match_ids)} matches across 5 folds")

    step3 = json.loads(STEP3_SUMMARY_PATH.read_text())
    T = step3["fitted_temperature"]
    fill_values = step3["fill_values"]
    print(f"  using Task 19's fitted temperature T={T:.4f}")

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

        ps_train = chosen_pop[chosen_pop["match_id"].isin(train_mids)]
        X_ps, _ = prep_X(ps_train, CANDIDATE_FEATURES)
        ps_model = xgb.XGBClassifier(**PS_KWARGS)
        ps_model.fit(X_ps, ps_train["pass_complete"].astype(int))

        ps_test = chosen_pop[chosen_pop["match_id"].isin(test_mids)]
        X_ps_test, _ = prep_X(ps_test, CANDIDATE_FEATURES, fill_values)
        ps_test_pred = ps_model.predict_proba(X_ps_test)[:, 1]
        ps_oof_pred.extend(ps_test_pred.tolist())
        ps_oof_true.extend(ps_test["pass_complete"].astype(int).tolist())

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

        fold_der_rows = []
        for mid in sorted(test_mids):
            cand = pd.read_parquet(EV_DIR / f"{mid}.parquet")
            X_cand, _ = prep_X(cand, CANDIDATE_FEATURES, fill_values)
            cand["p_success_oof"] = ps_model.predict_proba(X_cand)[:, 1]

            cand = build_ev_oof_for_match(mid, cand, model_for, model_against)
            if len(cand) == 0:
                continue

            restricted = cand[(cand["p_success_oof"] >= RESTRICT_MIN_P_SUCCESS)
                               & (cand["distance_u"] <= RESTRICT_MAX_DISTANCE_U)]
            fold_der_rows.append((mid, cand, restricted))

        train_restricted_parts = []
        for mid in sorted(train_mids):
            df = pd.read_parquet(EV_DIR / f"{mid}.parquet",
                                  columns=CANDIDATE_FEATURES + ["match_id", "event_id", "chosen", "p_success"])
            r = df[(df["p_success"] >= RESTRICT_MIN_P_SUCCESS) & (df["distance_u"] <= RESTRICT_MAX_DISTANCE_U)]
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
