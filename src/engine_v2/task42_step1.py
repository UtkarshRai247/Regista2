"""
Task 42, Step 1 (A): role-appropriate outcomes (Y_F3, Y_SHOT) in Task 35's
pass-level test, study sample only. docs/specs/task-42-improvement-round-2.md.

Units and S:
  passes (Task 35's rows): S = v5 Decision (task35_ptest.add_s) and
    MOVE_ON_SPEED (Task 39's s_for_rows on per-pass residuals regenerated
    by the Task 26 Step 2 re-run, asserted identical to the stored v2 files);
  receptions (Task 34 rows with Task 35 (d)'s origin features): S = RQ_rel.
g refit per outcome with task35_ptest.crossfit_g. Model task35_ptest.fe_fit.
Controls on the same rows: pass completion (passes) or retention
(receptions; the brief's correction 4d6405a): Y = keep of the receiver's
next action, S = his raw retention rate over ALL his completed receptions
in his OTHER matches (>= 100 elsewhere), g refit on the reception features.
Y_F3 uses only units starting at x < 80.

Run: python src/engine_v2/task42_step1.py
"""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

import task33_step3_f_state as tfs
import task35_ptest as tp
from task32_step4 import assign_roles
from crossfit import FOLDS_PATH
from task39_tempo_ptest import s_for_rows, V2_MOVE, V2_HOLD, rm
from task42_outcomes import match_outcomes
from task32_step5 import leave_one_match_out

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
LEADERBOARD_V5C_PATH = DATA_DIR / "processed" / "leaderboard_v5c.parquet"
REC34_PATH = DATA_DIR / "processed" / "engine_v2" / "task34_receptions.parquet"
OUTCOMES_PATH = DATA_DIR / "processed" / "engine_v2" / "task42_event_outcomes.parquet"
RECEIPT_ACTIONS_PATH = DATA_DIR / "processed" / "engine_v2" / "task42_receipt_actions.parquet"
TASK35_PATH = DATA_DIR / "engine_v2_task35_ptest.json"
SUMMARY_PATH = DATA_DIR / "engine_v2_task42_step1.json"
F3_X = 80.0


def tempo_move_with_ids() -> pd.DataFrame:
    rm.OUT_PATH = DATA_DIR / "processed" / "tempo_task42_metrics.parquet"
    rm.MOVE_RESID_PATH = DATA_DIR / "processed" / "tempo_task42_move_residuals.parquet"
    rm.HOLD_RESID_PATH = DATA_DIR / "processed" / "tempo_task42_hold_residuals.parquet"
    rm.SUMMARY_PATH = DATA_DIR / "tempo_task42_redesign_rerun.json"
    _, move_df, hold_df, _ = rm.main()
    for new, old_path in ((move_df, V2_MOVE), (hold_df, V2_HOLD)):
        old = pd.read_parquet(old_path)
        assert len(new) == len(old) and (new["player_id"].values == old["player_id"].values).all()
        assert np.allclose(new["residual"].values, old["residual"].values, rtol=0, atol=1e-12)
    return move_df[["match_id", "event_id", "player_id", "residual"]]


def retention_s(rows: pd.DataFrame, rc_act: pd.DataFrame) -> pd.DataFrame:
    """Brief correction 4d6405a: receiver's raw retention rate over ALL his completed receptions in his
    OTHER matches (not pressured-only, not context-adjusted), >= 100 elsewhere."""
    a = rc_act.dropna(subset=["keep", "player_id"])
    vals = leave_one_match_out(a[["match_id", "player_id", "keep"]].rename(columns={"keep": "decision"}), "player_id", 100)
    out = rows.merge(vals[["match_id", "player_id", "complement_mean"]], on=["match_id", "player_id"], how="left")
    return out.rename(columns={"complement_mean": "S_raw"})


def run(d: pd.DataFrame, y: str, g: str, ctrl: pd.DataFrame, cy: str, cg: str) -> dict:
    res = tp.fe_fit(d, y, g)
    keep = set(d.loc[d["S_raw"].notna() & d[y].notna() & d[g].notna(), "event_id"])
    res["control"] = tp.fe_fit(ctrl[ctrl["event_id"].isin(keep)], cy, cg)
    return res


def main():
    print("Task 42 Step 1 ...")
    folds = pd.read_csv(FOLDS_PATH)
    ev_mids = {int(p.stem) for p in tp.EV_DIR.glob("*.parquet")}
    folds = folds[folds["match_id"].isin(ev_mids)]
    fold_of = dict(zip(folds["match_id"], folds["fold"]))
    mids = sorted(fold_of)

    outs = [match_outcomes(m) for m in mids]
    ev_out = pd.concat([o[0] for o in outs], ignore_index=True)
    rc_act = pd.concat([o[1] for o in outs], ignore_index=True)
    ev_out.to_parquet(OUTCOMES_PATH)
    rc_act.to_parquet(RECEIPT_ACTIONS_PATH)

    lb = pd.read_parquet(LEADERBOARD_V5C_PATH, columns=["player_id", "is_deep_midfield"])
    roles = assign_roles(set(lb["player_id"])).set_index("player_id")["role"]
    dm_ids = set(lb.loc[lb["is_deep_midfield"], "player_id"])

    # ---- passes (Task 35 rows, regenerated) ----
    y_all = pd.concat([tp.net_xg_after(m) for m in mids], ignore_index=True)
    feat = tfs.build_feature_table(mids).merge(y_all, on=["match_id", "event_id"], how="left")
    feat["pass_complete"] = feat["pass_complete"].astype(float)
    feat["g_xg"], _ = tp.crossfit_g(feat, "y_net_xg", fold_of)
    feat["g_cmp"], _ = tp.crossfit_g(feat, "pass_complete", fold_of)
    feat = feat.merge(ev_out[["match_id", "event_id", "y_f3", "y_shot"]], on=["match_id", "event_id"], how="left")
    feat["y_f3"] = np.where(feat["ball_x"] < F3_X, feat["y_f3"], np.nan)
    for y in ("y_f3", "y_shot"):
        sub = feat[feat[y].notna()]
        oof, r2 = tp.crossfit_g(sub, y, fold_of)
        feat.loc[sub.index, f"g_{y}"] = oof
        print(f"  passes g({y}) OOF R^2={r2:.4f}")
    v5 = pd.read_parquet(tp.CROSSFIT_V5_PATH, columns=["match_id", "event_id", "team", "player_id", "decision"])
    v5 = v5.merge(feat[["match_id", "event_id", "y_net_xg", "pass_complete", "g_xg", "g_cmp", "y_f3", "y_shot",
                        "g_y_f3", "g_y_shot", "ball_x"]], on=["match_id", "event_id"], how="inner")
    v5["role"] = v5["player_id"].map(roles).fillna("NONE")
    t35 = json.loads(TASK35_PATH.read_text())["step2"]["a_decision_v5"]
    chk = tp.add_s(v5, "decision")
    r = tp.fe_fit(chk, "y_net_xg", "g_xg")
    assert np.isclose(r["coef_per_sd"], t35["coef_per_sd"], rtol=1e-9) and np.isclose(r["se"], t35["se"], rtol=1e-9)
    print("  Task 35 (a) reproduced exactly")

    move = tempo_move_with_ids()
    pass_S = {"v5_decision": tp.add_s(v5, "decision"), "move_on_speed": s_for_rows(v5, move, "mean")}
    pass_ctrl = tp.add_s(v5, "pass_complete")

    # ---- receptions (Task 34 rows + Task 35 (d) origin features) ----
    rec = pd.read_parquet(REC34_PATH, columns=["match_id", "event_id", "team", "player_id", "period", "minute", "recv_x", "rq_rel"])
    rec = tp.reception_features(rec, mids)
    rec = rec.merge(ev_out[["match_id", "event_id", "y_f3", "y_shot"]], on=["match_id", "event_id"], how="left") \
             .merge(rc_act[["match_id", "event_id", "keep"]], on=["match_id", "event_id"], how="left")
    rec["y_f3"] = np.where(rec["recv_x"] < F3_X, rec["y_f3"], np.nan)
    for y in ("y_f3", "y_shot", "keep"):
        sub = rec[rec[y].notna()]
        oof, r2 = tp.crossfit_g(sub, y, fold_of)
        rec.loc[sub.index, f"g_{y}"] = oof
        print(f"  receptions g({y}) OOF R^2={r2:.4f}")
    rec["role"] = rec["player_id"].map(roles).fillna("NONE")
    rec_S = tp.add_s(rec, "rq_rel")
    rec_ctrl = retention_s(rec, rc_act)

    # ---- base rates ----
    def rates(df, dm):
        s = df[df["player_id"].isin(dm_ids)] if dm else df
        return {"n": len(s), "y_f3_rate": float(s["y_f3"].mean()), "n_y_f3_units": int(s["y_f3"].notna().sum()),
                "y_shot_rate": float(s["y_shot"].mean())}
    base = {"passes": {"all": rates(v5, False), "dm": rates(v5, True)},
            "receptions": {"all": rates(rec, False), "dm": rates(rec, True),
                           "keep_rate_all": float(rec["keep"].mean()), "n_keep_defined": int(rec["keep"].notna().sum())}}
    print(f"  base rates: {base}")

    tests = {}
    for grp, filt in (("all", None), ("dm", dm_ids)):
        for y in ("y_f3", "y_shot"):
            for sname, d in pass_S.items():
                dd = d if filt is None else d[d["player_id"].isin(filt)]
                tests[f"{grp}|{sname}|{y}"] = run(dd, y, f"g_{y}", pass_ctrl, "pass_complete", "g_cmp")
            dd = rec_S if filt is None else rec_S[rec_S["player_id"].isin(filt)]
            tests[f"{grp}|rq_rel|{y}"] = run(dd, y, f"g_{y}", rec_ctrl, "keep", "g_keep")
    for k, r in tests.items():
        c = r["control"]
        print(f"  {k}: n={r['n_rows']} players={r['n_players']} coef100={r['coef_per_sd_per100']:+.4f} "
              f"CI={[round(x, 4) for x in r['ci95_per100']]} p={r['p']:.4g} MDE={r['mde_80_per100']:.4f} | "
              f"control coef100={c['coef_per_sd_per100']:+.3f} p={c['p']:.3g}")
    SUMMARY_PATH.write_text(json.dumps({"base_rates": base, "tests": tests,
                                        "n_receipts_with_action_info": len(rc_act),
                                        "receipt_action_counts": rc_act["action"].value_counts(dropna=False).to_dict()},
                                       indent=2, default=str))
    print(f"Wrote {SUMMARY_PATH}")


if __name__ == "__main__":
    main()
