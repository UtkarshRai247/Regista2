"""
Task 33, Step 2: cross-fitted EV for the corrected chosen options.
Identical to crossfit_v5.py (same 5 folds, same frozen
PS_KWARGS/VM_KWARGS/POLICY_XGB_KWARGS hyperparameters, same frozen
temperature T and fill_values, same offside_v4 rule R1_K10) -- the ONE
difference is which candidate row counts as "chosen" for computing
ev_chosen/var_chosen: Step 1's retarget table
(incomplete_retarget_v6.parquet) instead of grid.py's original
end-location cell.

"No retraining of value, pass-success or policy models" (Task 33's hard
rule) is read as: no NEW/DIFFERENT training spec (hyperparameters,
features, population, frozen temperature) -- not as "skip the per-fold
model fits crossfit_v5.py's own cross-fitting harness already performs
and that Step 2 explicitly asks this script to reproduce". Every
PS_KWARGS/VM_KWARGS/POLICY_XGB_KWARGS/temperature/fill_values/offside
value is byte-identical to crossfit_v5.py; nothing about HOW the models
are trained changes, only which row supplies ev_chosen. Disclosed here
and at the top of the results page, not silently assumed.

`build_ev_oof_for_match` already recomputes EV fresh for EVERY candidate
row (including every is_teammate_destination row), so redirecting
"chosen" to Step 1's target requires no extra EV computation -- just
picking a different already-scored row. A new boolean column
`chosen_v6` marks that row (or no row, for excluded passes); everything
downstream that used to key off `chosen` now keys off `chosen_v6`.

Run: python src/engine_v2/crossfit_v6.py
"""
import json
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import roc_auc_score

from value_models import STATE_FEATURES, XGB_KWARGS as VM_KWARGS
from value_models_v5 import OUT_PATH as VALUE_ROWS_PATH
import pass_success_v3  # noqa: F401 -- monkeypatch side effect, same as crossfit_v5.py
from pass_success_v2 import XGB_KWARGS as PS_KWARGS, load_chosen_rows
from common import CANDIDATE_FEATURES, prep_X
from policy_baseline_fix import RESTRICT_MIN_P_SUCCESS, RESTRICT_MAX_DISTANCE_U
from crossfit import build_ev_oof_for_match, softmax_per_group, FOLDS_PATH, POLICY_XGB_KWARGS, NEG_SAMPLES_PER_PASS, N_FOLDS
from offside_v4 import add_offside_v4_column
from grid import chosen_cell

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
EVENTS_DIR = DATA_DIR / "raw" / "events"
FRAMES_DIR = DATA_DIR / "raw" / "frames"
EV_DIR = DATA_DIR / "processed" / "engine_v2" / "options_ev_v4"
RETARGET_PATH = DATA_DIR / "processed" / "engine_v2" / "incomplete_retarget_v6.parquet"
OUT_PATH = DATA_DIR / "processed" / "engine_v2" / "pass_der_crossfit_v6.parquet"
V5_PATH = DATA_DIR / "processed" / "engine_v2" / "pass_der_crossfit_v5.parquet"
SUMMARY_PATH = DATA_DIR / "engine_v2_step2_crossfit_v6.json"


def mark_chosen_v6(cand: pd.DataFrame, retarget: pd.DataFrame) -> tuple:
    """Adds a `chosen_v6` bool column to cand: the original `chosen` row
    for status=unchanged; the matching is_teammate_destination row (or,
    failing that, the matching grid-cell row) for status=retargeted; no
    row at all for status=excluded. Returns (cand, n_fallback_used,
    n_double_fallback_excluded)."""
    chosen_v6 = np.zeros(len(cand), dtype=bool)
    n_fallback_used, n_double_fallback_excluded = 0, 0
    retarget_by_event = retarget.set_index("event_id")

    for eid, g in cand.groupby("event_id", sort=False):
        if eid not in retarget_by_event.index:
            continue
        r = retarget_by_event.loc[eid]
        status = r["status"]
        if status == "unchanged":
            mask = g["chosen"].values
        elif status == "excluded":
            continue
        else:
            tx, ty = r["target_x"], r["target_y"]
            mask = ((g["is_teammate_destination"].values == 1)
                     & np.isclose(g["candidate_x"].values, tx, atol=1e-6)
                     & np.isclose(g["candidate_y"].values, ty, atol=1e-6))
            if not mask.any():
                cell = chosen_cell(np.array([tx, ty]))
                mask = ((g["is_teammate_destination"].values == 0)
                         & np.isclose(g["candidate_x"].values, cell[0], atol=1e-6)
                         & np.isclose(g["candidate_y"].values, cell[1], atol=1e-6))
                n_fallback_used += 1
                if not mask.any():
                    n_double_fallback_excluded += 1
                    continue
        chosen_v6[g.index[mask]] = True

    cand = cand.copy()
    cand["chosen_v6"] = chosen_v6
    return cand, n_fallback_used, n_double_fallback_excluded


def main():
    t_start = time.time()
    print("Task 33 Step 2: cross-fitted EV for the corrected chosen options ...")
    retarget = pd.read_parquet(RETARGET_PATH)
    print(f"  retarget table: {retarget['status'].value_counts().to_dict()}")

    folds = pd.read_csv(FOLDS_PATH)
    match_ids = sorted(int(p.stem) for p in EV_DIR.glob("*.parquet"))
    folds = folds[folds["match_id"].isin(match_ids)]
    fold_of = dict(zip(folds["match_id"], folds["fold"]))
    match_ids = [m for m in match_ids if m in fold_of]
    print(f"  {len(match_ids)} matches across 5 folds")

    step3 = json.loads((DATA_DIR / "engine_v2_step3_policy_baseline_fix_v5.json").read_text())
    T = step3["fitted_temperature"]
    fill_values = step3["fill_values"]
    print(f"  using v5's frozen temperature T={T:.4f} (unchanged)")

    chosen_pop = load_chosen_rows()
    chosen_pop = chosen_pop[chosen_pop["match_id"].isin(match_ids)]
    value_rows = pd.read_parquet(VALUE_ROWS_PATH)
    value_rows = value_rows[value_rows["match_id"].isin(match_ids)]

    ps_oof_pred, ps_oof_true = [], []
    for_oof_pred, for_oof_true = [], []
    against_oof_pred, against_oof_true = [], []
    policy_oof_ranks = []
    all_der_rows = []
    n_fallback_total, n_double_fallback_total = 0, 0

    for fold_id in range(N_FOLDS):
        t_fold = time.time()
        test_mids = set(folds.loc[folds["fold"] == fold_id, "match_id"])
        train_mids = set(match_ids) - test_mids
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

            events = pd.read_parquet(EVENTS_DIR / f"{mid}.parquet").sort_values("index").reset_index(drop=True)
            frames = pd.read_parquet(FRAMES_DIR / f"{mid}.parquet")
            cand = add_offside_v4_column(cand, events, frames)

            cand = build_ev_oof_for_match(mid, cand, model_for, model_against)
            if len(cand) == 0:
                continue

            match_retarget = retarget[retarget["match_id"] == mid]
            cand, n_fb, n_dfb = mark_chosen_v6(cand, match_retarget)
            n_fallback_total += n_fb
            n_double_fallback_total += n_dfb

            restricted = cand[(cand["p_success_oof"] >= RESTRICT_MIN_P_SUCCESS)
                               & (cand["distance_u"] <= RESTRICT_MAX_DISTANCE_U) & (~cand["offside_v4"])]
            fold_der_rows.append((mid, cand, restricted, match_retarget.set_index("event_id")))

        train_restricted_parts = []
        for mid in sorted(train_mids):
            df = pd.read_parquet(EV_DIR / f"{mid}.parquet",
                                  columns=CANDIDATE_FEATURES + ["match_id", "event_id", "team", "period", "chosen",
                                                                  "p_success", "candidate_x", "candidate_y",
                                                                  "passer_x", "passer_y"])
            events = pd.read_parquet(EVENTS_DIR / f"{mid}.parquet").sort_values("index").reset_index(drop=True)
            frames = pd.read_parquet(FRAMES_DIR / f"{mid}.parquet")
            df = add_offside_v4_column(df, events, frames)
            r = df[(df["p_success"] >= RESTRICT_MIN_P_SUCCESS) & (df["distance_u"] <= RESTRICT_MAX_DISTANCE_U)
                   & (~df["offside_v4"])]
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
        for mid, cand, restricted, match_retarget_idx in fold_der_rows:
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

            chosen_v6_rows = cand[cand["chosen_v6"]].set_index("event_id")
            var_chosen_all = chosen_v6_rows["p_success_oof"] * (1 - chosen_v6_rows["p_success_oof"]) * \
                (chosen_v6_rows["V_net_success"] - chosen_v6_rows["V_net_turnover"]) ** 2

            for eid, g in restricted.groupby("event_id"):
                if bool(g["chosen_v6"].any()):
                    ranked = g.sort_values("policy_probability", ascending=False).reset_index(drop=True)
                    rank = ranked.index[ranked["chosen_v6"]].tolist()[0]
                    policy_oof_ranks.append(rank)

                status = match_retarget_idx.loc[eid, "status"] if eid in match_retarget_idx.index else None
                team_val = g["team"].iloc[0]
                player_val = g["player_id"].iloc[0]

                if eid in chosen_v6_rows.index:
                    fold_records.append({
                        "match_id": mid, "event_id": eid, "team": team_val, "player_id": player_val,
                        "ev_chosen": float(chosen_v6_rows.loc[eid, "EV"]),
                        "var_chosen": float(var_chosen_all.loc[eid]),
                        "policy_weighted_ev": float(g["ev_x_prob"].sum()),
                        "policy_weighted_var": float(g["var_x_prob"].sum()),
                        "status": status, "excluded": False,
                    })
                elif status == "excluded":
                    fold_records.append({
                        "match_id": mid, "event_id": eid, "team": team_val, "player_id": player_val,
                        "ev_chosen": np.nan, "var_chosen": np.nan,
                        "policy_weighted_ev": float(g["ev_x_prob"].sum()),
                        "policy_weighted_var": float(g["var_x_prob"].sum()),
                        "status": status, "excluded": True,
                    })

        fold_der_df = pd.DataFrame(fold_records)
        all_der_rows.append(fold_der_df)

        print(f"  Fold {fold_id} done ({time.time() - t_fold:.1f}s)")

    der_df = pd.concat(all_der_rows, ignore_index=True)
    der_df["decision"] = der_df["ev_chosen"] - der_df["policy_weighted_ev"]
    der_df["risk"] = der_df["var_chosen"] - der_df["policy_weighted_var"]
    der_df.to_parquet(OUT_PATH)
    print(f"\n  Cross-fitted v6 Decision/Risk: {len(der_df)} passes "
          f"({int(der_df['excluded'].sum())} excluded, no ev_chosen/decision)")
    print(f"  is_teammate_destination-row-missing fallback used: {n_fallback_total}; "
          f"double-fallback (still not found, forced excluded): {n_double_fallback_total}")

    ps_auc_oof = float(roc_auc_score(ps_oof_true, ps_oof_pred))
    for_auc_oof = float(roc_auc_score(for_oof_true, for_oof_pred))
    against_auc_oof = float(roc_auc_score(against_oof_true, against_oof_pred))
    policy_ranks = np.array(policy_oof_ranks)
    policy_top1_oof = float((policy_ranks == 0).mean())
    policy_top3_oof = float((policy_ranks < 3).mean())

    print(f"\n  OOF AUC -- pass_success: {ps_auc_oof:.4f}, M_for: {for_auc_oof:.4f}, M_against: {against_auc_oof:.4f}")
    print(f"  OOF policy top1 (vs v6's chosen_v6): {policy_top1_oof:.4f}, top3: {policy_top3_oof:.4f}")

    print("\n  correlation of v6 ev_chosen with v5's (unchanged passes should match exactly) ...")
    v5 = pd.read_parquet(V5_PATH, columns=["match_id", "event_id", "ev_chosen"]).rename(columns={"ev_chosen": "ev_chosen_v5"})
    joined = der_df.dropna(subset=["ev_chosen"]).merge(v5, on=["match_id", "event_id"], how="inner")
    r_all = float(joined["ev_chosen"].corr(joined["ev_chosen_v5"]))
    unchanged_joined = joined[joined["status"] == "unchanged"]
    r_unchanged = float(unchanged_joined["ev_chosen"].corr(unchanged_joined["ev_chosen_v5"]))
    max_abs_diff_unchanged = float((unchanged_joined["ev_chosen"] - unchanged_joined["ev_chosen_v5"]).abs().max())
    print(f"  r (all non-excluded, n={len(joined)}): {r_all:.4f}")
    print(f"  r (unchanged only, n={len(unchanged_joined)}): {r_unchanged:.4f}, max abs diff: {max_abs_diff_unchanged:.6g}")

    print(f"\n  Total wall clock: {time.time() - t_start:.1f}s")

    summary = {
        "n_folds": N_FOLDS, "n_matches": len(match_ids), "n_der_rows": len(der_df),
        "n_excluded": int(der_df["excluded"].sum()),
        "n_fallback_used": n_fallback_total, "n_double_fallback_excluded": n_double_fallback_total,
        "oof_auc": {"pass_success": ps_auc_oof, "M_for": for_auc_oof, "M_against": against_auc_oof},
        "oof_policy_vs_chosen_v6": {"top1_accuracy": policy_top1_oof, "top3_accuracy": policy_top3_oof,
                                     "n_covered": len(policy_ranks)},
        "ev_chosen_v6_vs_v5_correlation": {"r_all_non_excluded": r_all, "n_all": len(joined),
                                            "r_unchanged_only": r_unchanged, "n_unchanged": len(unchanged_joined),
                                            "max_abs_diff_unchanged": max_abs_diff_unchanged},
        "wall_clock_seconds": time.time() - t_start,
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
    print(f"\nWrote {SUMMARY_PATH}")
    return summary


if __name__ == "__main__":
    main()
