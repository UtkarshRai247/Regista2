"""
Task 37: Task 35's pass-level test (P-test) on the untouched women's
holdout -- the final holdout use. docs/specs/task-37-holdout-ptest.md.

No engine change, no retraining on the holdout, no tuning:
- Decision = Task 26 Step 1's frozen-engine-v5 holdout scores
  (pass_der_holdout.parquet), unchanged.
- Origin features: value_models_v5.build_match_rows_v5 (engine v5's own
  feature function, corrected coordinates) run on data/raw_holdout,
  plus Task 33's f(state) extras via task33_step3_f_state.build_feature_table,
  both redirected to the holdout directories.
- g: ONE XGBoost regression per target (net xG; completion) trained on ALL
  study-sample passes (Task 35's feature table and hyperparameters), then
  applied unchanged to holdout passes.
- Y: net shot xG over events i+1..i+10 (task35_ptest.net_xg_after).
- S: leave-one-match-out over OTHER HOLDOUT matches, >= 100 eligible
  passes elsewhere (task35_ptest.add_s).
- Roles: task32_step4.assign_roles on holdout pass positions.
- Model: task35_ptest.fe_fit (Y ~ S + g + role FE + team-match FE, SE
  clustered by passer).

Run: python src/engine_v2/task37_holdout_ptest.py
"""
import json
import tempfile
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb

import value_models_v5 as vm5
import task33_step3_f_state as tfs
import task35_ptest as tp
import task32_step4 as t32
from crossfit import FOLDS_PATH

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
H_EVENTS = DATA_DIR / "raw_holdout" / "events"
H_FRAMES = DATA_DIR / "raw_holdout" / "frames"
H_MATCHES = DATA_DIR / "raw_holdout" / "matches"
H_EV_DIR = DATA_DIR / "processed" / "engine_v2" / "options_ev_holdout"
H_DER_PATH = DATA_DIR / "processed" / "engine_v2" / "pass_der_holdout.parquet"
H_VALUE_ROWS_PATH = DATA_DIR / "processed" / "engine_v2" / "value_model_rows_holdout.parquet"
STUDY_EV_DIR = tfs.EV_DIR
TASK35_PATH = DATA_DIR / "engine_v2_task35_ptest.json"
SUMMARY_PATH = DATA_DIR / "engine_v2_task37_holdout_ptest.json"

DM_SHARE_MIN = 0.50
STEP3_MIN_DM = 20


def study_g_models() -> tuple:
    folds = pd.read_csv(FOLDS_PATH)
    ev_mids = {int(p.stem) for p in STUDY_EV_DIR.glob("*.parquet")}
    mids = sorted(set(folds["match_id"]) & ev_mids)
    assert len(mids) == 292
    feat = tfs.build_feature_table(mids)
    y = pd.concat([tp.net_xg_after(m) for m in mids], ignore_index=True)
    feat = feat.merge(y, on=["match_id", "event_id"], how="left")
    assert feat["y_net_xg"].notna().all()
    X = feat[tfs.F_STATE_FEATURES].astype(float)
    g_xg = xgb.XGBRegressor(**tfs.XGB_REGRESSOR_KWARGS).fit(X, feat["y_net_xg"].astype(float))
    g_cmp = xgb.XGBRegressor(**tfs.XGB_REGRESSOR_KWARGS).fit(X, feat["pass_complete"].astype(float))
    return g_xg, g_cmp, len(feat)


def holdout_value_rows(mids: list) -> tuple:
    vm5.EVENTS_DIR, vm5.FRAMES_DIR = H_EVENTS, H_FRAMES
    rows, skipped = [], []
    for mid in mids:
        if not (H_FRAMES / f"{mid}.parquet").exists():
            skipped.append(mid)
            continue
        r, *_ = vm5.build_match_rows_v5(mid)
        rows.extend(r)
    df = pd.DataFrame(rows)
    keep = ["match_id", "event_id", "type"] + list(tfs.STATE_FEATURES)
    df[keep].to_parquet(H_VALUE_ROWS_PATH)
    return df, skipped


def competition_of() -> dict:
    out = {}
    for f in H_MATCHES.glob("*.parquet"):
        for mid in pd.read_parquet(f, columns=["match_id"])["match_id"]:
            out[int(mid)] = f.stem
    return out


def main():
    print("Task 37: holdout P-test ...")
    g_xg, g_cmp, n_train = study_g_models()
    print(f"  g models trained on {n_train} study passes")

    der = pd.read_parquet(H_DER_PATH)
    mids = sorted(der["match_id"].unique())
    _, skipped = holdout_value_rows(sorted(int(p.stem) for p in H_EVENTS.glob("*.parquet")))
    print(f"  holdout value rows written; matches skipped (no frames file): {skipped}")

    tfs.VALUE_ROWS_PATH, tfs.EV_DIR, tfs.EVENTS_DIR = H_VALUE_ROWS_PATH, H_EV_DIR, H_EVENTS
    feat = tfs.build_feature_table(mids)
    tp.EVENTS_DIR = H_EVENTS
    y = pd.concat([tp.net_xg_after(m) for m in mids], ignore_index=True)
    feat = feat.merge(y, on=["match_id", "event_id"], how="left")
    X = feat[tfs.F_STATE_FEATURES].astype(float)
    feat["g_xg"] = g_xg.predict(X)
    feat["g_cmp"] = g_cmp.predict(X)
    feat["pass_complete"] = feat["pass_complete"].astype(float)

    chosen = pd.concat([pd.read_parquet(H_EV_DIR / f"{m}.parquet", columns=["match_id", "event_id", "player_id", "chosen"])
                        .query("chosen") for m in mids], ignore_index=True).drop(columns=["chosen"])
    df = der.merge(chosen, on=["match_id", "event_id"], how="left") \
        .merge(feat[["match_id", "event_id", "y_net_xg", "pass_complete", "g_xg", "g_cmp"]],
               on=["match_id", "event_id"], how="inner")
    print(f"  holdout passes: {len(der)} scored; {len(df)} with origin features; "
          f"{int(df['player_id'].isna().sum())} without player_id")

    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "holdout_passes.parquet"
        df[["match_id", "event_id", "player_id"]].to_parquet(p)
        t32.PASS_DER_V8_PATH, t32.EVENTS_DIR = p, H_EVENTS
        roles = t32.assign_roles(set(df["player_id"].dropna()))
    df["role"] = df["player_id"].map(roles.set_index("player_id")["role"]).fillna("NONE")

    comp = competition_of()
    df["competition"] = df["match_id"].map(comp)
    control = tp.add_s(df, "pass_complete")
    primary = tp.add_s(df, "decision")
    for d in (control, primary):
        d["role"] = d["player_id"].map(roles.set_index("player_id")["role"]).fillna("NONE")
        assert (d.loc[d["S_raw"].notna(), "complement_count"] >= tp.MIN_ELSEWHERE).all()

    q = primary.dropna(subset=["S_raw"])
    qual_per_comp = q.groupby("competition")["player_id"].nunique().to_dict()
    inputs = {"n_passes_scored": len(der), "n_passes_with_features": len(df),
              "n_passers_total": int(df["player_id"].nunique()), "n_team_matches_total": int(df.groupby(["match_id", "team"]).ngroups),
              "n_matches": len(mids), "matches_skipped_no_frames": skipped,
              "n_passes_analysis": len(q), "n_passers_qualifying": int(q["player_id"].nunique()),
              "n_team_matches_analysis": int(q.groupby(["match_id", "team"]).ngroups),
              "qualifying_passers_per_competition": qual_per_comp,
              "role_counts_players": roles["role"].value_counts().to_dict(),
              "y_mean": float(df["y_net_xg"].mean()), "y_sd": float(df["y_net_xg"].std())}
    print(f"  inputs: {inputs}")

    res_control = tp.fe_fit(control, "pass_complete", "g_cmp")
    control_ok = res_control["coef_per_sd"] > 0 and res_control["p"] < 0.05
    res_primary = tp.fe_fit(primary, "y_net_xg", "g_xg")
    gate = res_primary["coef_per_sd"] > 0 and res_primary["p"] < 0.05
    print(f"  CONTROL: {res_control['coef_per_sd']:+.5f} p={res_control['p']:.3g} -> {'POSITIVE' if control_ok else 'NOT POSITIVE'}")
    print(f"  PRIMARY: {res_primary['coef_per_sd']:+.6f} (x100 {res_primary['coef_per_sd_per100']:+.4f}) "
          f"CI100={res_primary['ci95_per100']} p={res_primary['p']:.4g} MDE100={res_primary['mde_80_per100']:.4f} "
          f"-> GATE {'PASS' if gate else 'FAIL'}{'' if control_ok else ' (control not positive: primary not interpreted)'}")

    dm_ids = set(roles.loc[roles["share_DM"] >= DM_SHARE_MIN, "player_id"])
    dm_qual = set(q["player_id"]) & dm_ids
    step3 = {"n_dm_share_players_all": len(dm_ids), "n_dm_qualifying": len(dm_qual)}
    for name, x in (("all", q), ("dm", q[q["player_id"].isin(dm_ids)])):
        k = x.groupby(["match_id", "team"])["player_id"].nunique()
        step3[f"team_matches_with_2plus_players_{name}"] = [int((k >= 2).sum()), len(k)]
    if len(dm_qual) >= STEP3_MIN_DM:
        step3["control"] = tp.fe_fit(control[control["player_id"].isin(dm_ids)], "pass_complete", "g_cmp")
        step3["primary"] = tp.fe_fit(primary[primary["player_id"].isin(dm_ids)], "y_net_xg", "g_xg")
    print(f"  Step 3: DM-share players {len(dm_ids)}, qualifying {len(dm_qual)}")

    t35 = json.loads(TASK35_PATH.read_text())["step2"]
    summary = {"inputs": inputs, "g_train_n_study_passes": n_train,
               "control": res_control, "control_positive": bool(control_ok),
               "primary_decision_v5": res_primary, "gate_pass": bool(gate),
               "task35_study": {"control": t35["control"], "a_decision_v5": t35["a_decision_v5"]},
               "step3_deep_midfield": step3}
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
    print(f"Wrote {SUMMARY_PATH}")


if __name__ == "__main__":
    main()
