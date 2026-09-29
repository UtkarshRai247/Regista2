"""
Task 46, Part B: spatial vs physical press resistance (exploratory).
docs/specs/task-46-movers-and-spatial-physical.md.

W (physical willingness): cross-fitted XGBoost classifier (Task 42's
settings) of PRESSURED (Task 44's flag rule) on reception x, y, play
pattern, period, minute, score difference; W unit = PRESSURED - p_oof over
all completed receptions. 2015/16 (Task 44's seeded 5 match folds) and
study sample (Task 35's folds; score difference by task44_build's
event_features logic on the study events).
PR = PR2_flag_keep (unadjusted). S1 = Task 34 RQ_rel. S2 = AV_out = Task
38's AV restricted to moments where the passer is under pressure
(pressureType != 'N'), baseline refit on those moments (Task 38 settings).
B1: W stability on 2015/16 (Task 44's r1, >= 10 matches).
B2: trade-off correlations and top-quartile overlap (hypergeometric).
B3: 2015/16 P-test with S = other-match W, and S_W + S_PR together.

Run: python src/engine_v2/task46_part_b.py   (after task46_part_a.py)
"""
import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from scipy.stats import hypergeom
from sklearn.metrics import roc_auc_score

sys.path.insert(0, str(Path(__file__).parent.parent / "pff"))
import availability as av  # noqa: E402
import availability_tests as avt  # noqa: E402
import task44_build as tb  # noqa: E402
import task35_ptest as tp  # noqa: E402
from crossfit import FOLDS_PATH  # noqa: E402
from task32_step5 import leave_one_match_out  # noqa: E402
from task42_step2 import CLF_KWARGS  # noqa: E402
from task44_gate import receipt_flags, EV_DIR  # noqa: E402
from task44_tests import r1, crossfit_ev  # noqa: E402
from task41_ptest_vetting import fit_multi  # noqa: E402
from task46_part_a import STUDY_PR_PATH  # noqa: E402

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
STUDY_EVENTS = DATA_DIR / "raw" / "events"
LEADERBOARD_V5C_PATH = DATA_DIR / "processed" / "leaderboard_v5c.parquet"
REC34_PATH = DATA_DIR / "processed" / "engine_v2" / "task34_receptions.parquet"
SUMMARY_PATH = DATA_DIR / "engine_v2_task46_part_b.json"
W_FEATURES = ["recv_x", "recv_y", "play_pattern_code", "period", "minute", "score_diff"]
F3_X = 80.0


def fit_w(df: pd.DataFrame, fold) -> tuple:
    d = df.dropna(subset=["recv_x"]).copy()
    f = d["match_id"].map(fold).values
    oof = np.full(len(d), np.nan)
    for k in range(5):
        tr, te = f != k, f == k
        m = xgb.XGBClassifier(**CLF_KWARGS).fit(d.loc[tr, W_FEATURES].astype(float), d.loc[tr, "pressured_flag"].astype(int))
        oof[te] = m.predict_proba(d.loc[te, W_FEATURES].astype(float))[:, 1]
    d["w"] = d["pressured_flag"].astype(float) - oof
    return d, {"n": len(d), "base_rate": float(d["pressured_flag"].mean()),
               "auc": float(roc_auc_score(d["pressured_flag"].astype(int), oof))}


def pearson_ci(x, y):
    r = float(np.corrcoef(x, y)[0, 1])
    n = len(x)
    z, se = np.arctanh(r), 1 / np.sqrt(n - 3)
    return {"n": n, "r": r, "ci95": [float(np.tanh(z - 1.96 * se)), float(np.tanh(z + 1.96 * se))]}


def tradeoff(a: pd.Series, b: pd.Series) -> dict:
    j = pd.concat([a.rename("a"), b.rename("b")], axis=1).dropna()
    if len(j) < 8:
        return {"n": len(j), "note": "too few"}
    out = pearson_ci(j["a"].values, j["b"].values)
    ta, tb_ = j["a"] >= j["a"].quantile(0.75), j["b"] >= j["b"].quantile(0.75)
    N, K, n, k = len(j), int(ta.sum()), int(tb_.sum()), int((ta & tb_).sum())
    out.update({"top_q_a": K, "top_q_b": n, "both_observed": k, "both_expected": K * n / N,
                "p_fewer": float(hypergeom.cdf(k, N, K, n)), "p_more": float(hypergeom.sf(k - 1, N, K, n))})
    return out


def pmean(df, col, floor, pid="player_id"):
    a = df.dropna(subset=[col]).groupby(pid)[col].agg(["mean", "size"])
    return a.loc[a["size"] >= floor, "mean"]


def main():
    print("Task 46 Part B ...")
    # ---- W on 2015/16 ----
    Rc = pd.read_parquet(tb.RECEPTIONS_PATH)
    roles16 = pd.read_parquet(tb.ROLES_PATH).set_index("player_id")
    dm16 = set(roles16.index[roles16["is_dm"]])
    folds16 = tb.match_folds(sorted(Rc["match_id"].unique()))
    W16, w16_base = fit_w(Rc, folds16)
    print(f"  W 2015/16: {w16_base}")
    b1 = {"DM": r1(W16, "w", "mean", dm16), "all": r1(W16, "w", "mean")}
    print(f"  B1: {b1}")

    # ---- W on study ----
    folds = pd.read_csv(FOLDS_PATH)
    ev_mids = {int(p.stem) for p in EV_DIR.glob("*.parquet")}
    folds = folds[folds["match_id"].isin(ev_mids)]
    fold_st = dict(zip(folds["match_id"], folds["fold"]))
    mids = sorted(fold_st)
    tb.EV16 = STUDY_EVENTS
    sd = pd.concat([tb.event_features(m)[["match_id", "event_id", "score_diff"]] for m in mids], ignore_index=True)
    rst = pd.concat([receipt_flags(m) for m in mids], ignore_index=True).merge(sd, on=["match_id", "event_id"], how="left")
    Wst, wst_base = fit_w(rst, fold_st)
    print(f"  W study: {wst_base}")

    # ---- B2 ----
    lb = pd.read_parquet(LEADERBOARD_V5C_PATH, columns=["player_id", "is_deep_midfield"])
    dm_st = set(lb.loc[lb["is_deep_midfield"], "player_id"])
    pr_st = pd.read_parquet(STUDY_PR_PATH)
    rq = pmean(pd.read_parquet(REC34_PATH, columns=["player_id", "rq_rel"]), "rq_rel", 100)
    w_st, p_st = pmean(Wst, "w", 100), pmean(pr_st, "pr2_flag_keep", 50)
    b2 = {"S1": {}, "S2": {}}
    for grp, ids in (("DM", dm_st), ("all", None)):
        f = (lambda s: s if ids is None else s[s.index.isin(ids)])
        b2["S1"][grp] = {"RQ_rel_vs_W": tradeoff(f(rq), f(w_st)), "RQ_rel_vs_PR": tradeoff(f(rq), f(p_st))}

    mom = pd.read_parquet(av.MOMENTS_PATH)
    cw = pd.read_csv(av.OUT_DIR / "crosswalk.csv")
    mo = mom[mom["under_pressure"] == 1].copy()
    gids = sorted(cw["pff_game_id"].astype(int))
    mo["p_out"], auc_out = av.fit_oof(mo, av.match_folds(gids))
    mo["av_out"] = mo["available"] - mo["p_out"]
    pm = avt.player_map()
    pff2sb = pm.drop_duplicates("pff_player_id").set_index("pff_player_id")["sb_player_id"]
    avo = pmean(mo, "av_out", 100, "pff_player_id")
    avo.index = avo.index.map(pff2sb)
    wc = set(cw["statsbomb_match_id"])
    w_wc = pmean(Wst[Wst["match_id"].isin(wc)], "w", 100)
    p_wc = pmean(pr_st[pr_st["match_id"].isin(wc)], "pr2_flag_keep", 30)
    dm_pff, _ = avt.dm_group(mom, pm, cw)
    dm_wc = {pff2sb.get(p) for p in dm_pff}
    for grp, ids in (("DM", dm_wc), ("all", None)):
        f = (lambda s: s if ids is None else s[s.index.isin(ids)])
        b2["S2"][grp] = {"AV_out_vs_W": tradeoff(f(avo), f(w_wc)), "AV_out_vs_PR": tradeoff(f(avo), f(p_wc))}
    b2["AV_out_baseline"] = {"n_moments": len(mo), "base_rate": float(mo["available"].mean()), "auc": auc_out}
    print(f"  B2: {json.dumps(b2, default=str)[:1500]}")

    # ---- B3 (2015/16) ----
    R = W16.copy()
    R["role"] = R["player_id"].map(roles16["role"]).fillna("NONE")
    R["y_f3"] = np.where(R["recv_x"] < F3_X, R["y_f3"], np.nan)
    R["fold"] = R["match_id"].map(folds16)
    for y, g in (("y_net_xg", "g_xg"), ("y_f3", "g_f3"), ("keep_spell", "g_keep")):
        R[g], _ = crossfit_ev(R, y)
    def loo(df, col, floor, name):
        v = leave_one_match_out(df.dropna(subset=[col])[["match_id", "player_id", col]].rename(columns={col: "decision"}), "player_id", floor)
        return v[["match_id", "player_id", "complement_mean"]].rename(columns={"complement_mean": name})
    R = R.merge(loo(R, "w", 100, "S_W"), on=["match_id", "player_id"], how="left") \
         .merge(loo(R, "pr2_flag_keep", 50, "S_PR"), on=["match_id", "player_id"], how="left") \
         .merge(loo(R, "keep_spell", 100, "S_keep"), on=["match_id", "player_id"], how="left")
    b3 = {}
    for grp, ids in (("all", None), ("DM", dm16)):
        d = R if ids is None else R[R["player_id"].isin(ids)]
        for y, g in (("y_f3", "g_f3"), ("y_net_xg", "g_xg")):
            res = tp.fe_fit(d.assign(S_raw=d["S_W"]), y, g)
            ids_rows = set(d.loc[d["S_W"].notna() & d[y].notna(), "event_id"])
            res["control"] = tp.fe_fit(d[d["event_id"].isin(ids_rows)].assign(S_raw=lambda x: x["S_keep"]), "keep_spell", "g_keep")
            joint = fit_multi(d, y, ["S_W", "S_PR"], g)
            b3[f"{grp}|{y}"] = {"W_alone": res, "joint": joint}
            print(f"  B3 {grp}|{y}: W coef100={res['coef_per_sd_per100']:+.4f} p={res['p']:.3g} (n={res['n_rows']}) | "
                  f"control {res['control']['coef_per_sd_per100']:+.3f} p={res['control']['p']:.2g} | joint W "
                  f"{joint['S_W']['coef_per_sd_per100']:+.4f} p={joint['S_W']['p']:.3g}, PR {joint['S_PR']['coef_per_sd_per100']:+.4f} "
                  f"p={joint['S_PR']['p']:.3g} (n={joint['n_rows']})")

    SUMMARY_PATH.write_text(json.dumps({"W_1516": w16_base, "W_study": wst_base, "B1": b1, "B2": b2, "B3": b3},
                                       indent=2, default=str))
    print(f"Wrote {SUMMARY_PATH}")


if __name__ == "__main__":
    main()
