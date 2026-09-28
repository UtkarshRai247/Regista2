"""
Task 33, Step 3 (fix A2): a baseline that is unbiased by construction.
Replaces "EV of the typical choice" (policy_weighted_ev) with "EV a
player typically ACHIEVES from this situation": an XGBoost regression
f(state) predicting the out-of-fold ev_chosen (Step 2's v6 version)
from ORIGIN information only.

`value_model_rows_v5.parquet` (built by value_models_v5.py's
build_match_rows_v5) already computes all 15 STATE_FEATURES --
including play_pattern_code -- AT THE PASSER'S OWN LOCATION for every
pass event, because a StatsBomb Pass event's own `location` field IS
the passer's position; "play pattern" in the brief's feature list is
satisfied by this existing play_pattern_code column, not a second,
duplicate feature (disclosed). Only `under_pressure`/`period` (from
options_ev_v4's chosen rows) and `minute` (raw events, joined on
event_id) are added on top. No destination, player, or team-identity
feature is included, per the brief.

Cross-fitted on the SAME 5 match folds as crossfit_v6.py. NO
destination/player/team feature -- verified by the exact feature list
below.

Run: python src/engine_v2/task33_step3_f_state.py
"""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import r2_score

from value_models import STATE_FEATURES
from value_models_v5 import OUT_PATH as VALUE_ROWS_PATH
from validation_common import zone_of
from task32_step1 import length_bucket
from crossfit import FOLDS_PATH, N_FOLDS

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
EVENTS_DIR = DATA_DIR / "raw" / "events"
EV_DIR = DATA_DIR / "processed" / "engine_v2" / "options_ev_v4"
CROSSFIT_V6_PATH = DATA_DIR / "processed" / "engine_v2" / "pass_der_crossfit_v6.parquet"
OUT_PATH = DATA_DIR / "processed" / "engine_v2" / "decision_v6.parquet"
SUMMARY_PATH = DATA_DIR / "engine_v2_task33_step3.json"

XGB_REGRESSOR_KWARGS = dict(objective="reg:squarederror", n_estimators=300, max_depth=6,
                             learning_rate=0.05, subsample=0.8, random_state=20260928)
# colsample_bytree not specified by the brief -- left at the XGBoost default, disclosed.

EXTRA_FEATURES = ["under_pressure", "period", "minute"]
F_STATE_FEATURES = STATE_FEATURES + EXTRA_FEATURES
V5_OVERALL_MEAN_DECISION = 0.0026745
SANITY_TOLERANCE = 0.10 * V5_OVERALL_MEAN_DECISION  # 0.00027


def build_feature_table(match_ids: list) -> pd.DataFrame:
    vm = pd.read_parquet(VALUE_ROWS_PATH, columns=["match_id", "event_id"] + STATE_FEATURES)
    vm = vm[vm["match_id"].isin(match_ids)]

    frames = []
    for mid in match_ids:
        df = pd.read_parquet(EV_DIR / f"{mid}.parquet",
                              columns=["match_id", "event_id", "team", "chosen", "period", "under_pressure",
                                       "passer_x", "pass_length", "pass_complete"])
        chosen = df[df["chosen"]].drop(columns=["chosen"])
        ev = pd.read_parquet(EVENTS_DIR / f"{mid}.parquet", columns=["id", "minute"]).rename(columns={"id": "event_id"})
        chosen = chosen.merge(ev, on="event_id", how="left")
        frames.append(chosen)
    meta = pd.concat(frames, ignore_index=True)

    out = vm.merge(meta, on=["match_id", "event_id"], how="inner")
    out["under_pressure"] = out["under_pressure"].astype(float)
    return out


def main():
    print("Task 33 Step 3 (A2): f(state) baseline ...")
    crossfit_v6 = pd.read_parquet(CROSSFIT_V6_PATH)
    match_ids = sorted(crossfit_v6["match_id"].unique())
    print(f"  {len(match_ids)} matches, {len(crossfit_v6)} passes in v6 corpus "
          f"({int(crossfit_v6['excluded'].sum())} excluded)")

    feat = build_feature_table(match_ids)
    print(f"  feature table: {len(feat)} passes, {len(F_STATE_FEATURES)} features: {F_STATE_FEATURES}")

    joined = crossfit_v6.merge(feat, on=["match_id", "event_id"], how="inner", suffixes=("", "_meta"))
    print(f"  joined with crossfit v6: {len(joined)} passes "
          f"(should equal {len(crossfit_v6)} if feature coverage is complete)")

    folds = pd.read_csv(FOLDS_PATH)
    folds = folds[folds["match_id"].isin(match_ids)]
    fold_of = dict(zip(folds["match_id"], folds["fold"]))

    joined["fold"] = joined["match_id"].map(fold_of)
    has_y = joined["ev_chosen"].notna()
    print(f"  passes with a defined target (non-excluded): {int(has_y.sum())}/{len(joined)}")

    oof_pred = np.full(len(joined), np.nan)
    for fold_id in range(N_FOLDS):
        train_mask = (joined["fold"] != fold_id) & has_y
        test_mask = joined["fold"] == fold_id
        X_train = joined.loc[train_mask, F_STATE_FEATURES].astype(float)
        y_train = joined.loc[train_mask, "ev_chosen"].astype(float)
        X_test = joined.loc[test_mask, F_STATE_FEATURES].astype(float)

        model = xgb.XGBRegressor(**XGB_REGRESSOR_KWARGS)
        model.fit(X_train, y_train)
        oof_pred[test_mask.values] = model.predict(X_test)
        print(f"  fold {fold_id}: trained on {len(X_train)} passes, scored {test_mask.sum()} passes")

    joined["f_oof"] = oof_pred
    r2_oof = float(r2_score(joined.loc[has_y, "ev_chosen"], joined.loc[has_y, "f_oof"]))
    print(f"\n  pooled out-of-fold R^2: {r2_oof:.4f} (n={int(has_y.sum())})")

    joined["decision_v6"] = joined["ev_chosen"] - joined["f_oof"]
    joined["decision_policy_v6"] = joined["ev_chosen"] - joined["policy_weighted_ev"]

    joined["zone"] = joined["passer_x"].apply(zone_of)
    joined["length_bucket"] = joined["pass_length"].apply(length_bucket)
    joined["outcome"] = np.where(joined["pass_complete"], "complete", "incomplete")

    def sanity_table(col):
        rows = []
        for group_col in ("zone", "length_bucket", "outcome"):
            g = joined.dropna(subset=[col]).groupby(group_col)[col].agg(["mean", "count"]).reset_index()
            for _, r in g.iterrows():
                rows.append({"grouping": group_col, "group": r[group_col], "n": int(r["count"]),
                             "mean": float(r["mean"]), "within_tolerance": bool(abs(r["mean"]) < SANITY_TOLERANCE)})
        return rows

    sanity_v6 = sanity_table("decision_v6")
    print(f"\n  sanity check (Decision_v6, tolerance |mean|<{SANITY_TOLERANCE:.5f}):")
    all_pass = True
    for r in sanity_v6:
        status = "PASS" if r["within_tolerance"] else "FAIL"
        all_pass = all_pass and r["within_tolerance"]
        print(f"    [{status}] {r['grouping']}={r['group']}: n={r['n']}, mean={r['mean']:.6f}")
    print(f"  sanity check overall: {'ALL PASS' if all_pass else 'AT LEAST ONE FAILURE -- reported above, see results page'}")

    overall_mean_v6 = float(joined["decision_v6"].mean())
    overall_mean_policy_v6 = float(joined["decision_policy_v6"].mean())
    print(f"\n  overall mean Decision_v6: {overall_mean_v6:.6f}")
    print(f"  overall mean Decision_policy_v6: {overall_mean_policy_v6:.6f}")
    print(f"  v5 overall mean Decision (for reference): {V5_OVERALL_MEAN_DECISION}")

    out_cols = ["match_id", "event_id", "team", "player_id", "ev_chosen", "f_oof",
                "policy_weighted_ev", "decision_v6", "decision_policy_v6", "excluded", "status"]
    joined[out_cols].to_parquet(OUT_PATH)
    print(f"\nWrote {OUT_PATH}")

    summary = {
        "n_passes": len(joined), "n_with_defined_target": int(has_y.sum()),
        "n_excluded": int(joined["excluded"].sum()), "oof_r2": r2_oof,
        "overall_mean_decision_v6": overall_mean_v6, "overall_mean_decision_policy_v6": overall_mean_policy_v6,
        "v5_overall_mean_decision": V5_OVERALL_MEAN_DECISION, "sanity_tolerance": SANITY_TOLERANCE,
        "sanity_check_decision_v6": sanity_v6, "sanity_check_all_pass": all_pass,
        "f_state_features": F_STATE_FEATURES,
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
    print(f"\nWrote {SUMMARY_PATH}")
    return summary


if __name__ == "__main__":
    main()
