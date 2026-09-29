"""
Task 48, Steps 2-3: the confirmatory family on the RESERVED data (single
use) and the report-only extras. docs/specs/task-48-confirmation-reserved.md.

C1 DM : PR2_flag_keep -> Y_F3 (pressured receptions; S >= 50 elsewhere).
C2 DM : W -> Y_F3 (completed receptions; S >= 100 elsewhere).
C3 ALL: Task 47 Step 2's model (E1 < 0) with its placebo (a).
C4 ALL: club vs international PR2_flag_keep, disattenuated (Task 46 A-ii
        recipe); p = 2 x share of bootstrap r_true <= 0; NOT RUN if < 15 movers.
C6 ALL: PR2_flag_keep A1 (minus team x competition-season mean) -> Y_F3.
Holm across the family. CONFIRMED: Holm p < 0.05, stated sign, and (C1, C2,
C6) the retention control on the same rows positive with p < 0.05; (C3) the
placebo not negative with p < 0.05.
Estimators reused unchanged: task35_ptest.fe_fit, task41_ptest_vetting.fit_multi,
task44_tests.crossfit_ev / r1, task42_step2.s_loo / dm_table, Task 41's
perm_test, Task 46's split-half reliability (Study B's).

Run: python src/engine_v2/task48_tests.py   (after task48_build.py)
"""
import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import roc_auc_score
from statsmodels.stats.multitest import multipletests

sys.path.insert(0, str(Path(__file__).parent.parent / "decision_engine"))
import task26_step6_study_b as sb  # noqa: E402
import task35_ptest as tp  # noqa: E402
from task32_step5 import leave_one_match_out  # noqa: E402
from task42_step2 import s_loo, dm_table, CLF_KWARGS  # noqa: E402
from task44_tests import crossfit_ev, r1  # noqa: E402
from task41_ptest_vetting import fit_multi  # noqa: E402
from task41_lists_availability import perm_test, LIST_L  # noqa: E402
from task27_step1_deep_midfield import name_matches  # noqa: E402
from task48_build import RECEPTIONS_PATH, ROLES_PATH, EVR  # noqa: E402

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
SUMMARY_PATH = DATA_DIR / "engine_v2_task48.json"
SEED = 20260928
F3_X = 80.0
MIN_MOVERS, MIN_CTX = 15, 30
T47_FEATURES = ["recv_x", "recv_y", "play_pattern_code", "minute", "score_diff", "role_code"]


def ptest(d, y, g, ctrl):
    res = tp.fe_fit(d, y, g)
    ids = set(d.loc[d["S_raw"].notna() & d[y].notna() & d[g].notna(), "event_id"])
    res["control"] = tp.fe_fit(ctrl[ctrl["event_id"].isin(ids)], "keep_spell", "g_keep")
    return res


def summarise(r):
    return {"coef_per_sd": r["coef_per_sd"], "coef_per_sd_per100": r["coef_per_sd_per100"], "ci95_per100": r["ci95_per100"],
            "p": r["p"], "mde_80_per100": r["mde_80_per100"], "n_rows": r["n_rows"], "n_players": r["n_players"],
            "control": {k: r["control"][k] for k in ("coef_per_sd", "coef_per_sd_per100", "ci95_per100", "p", "n_rows")}}


def c3_model(Rc, roles, folds):
    pos = pd.concat([pd.read_parquet(EVR / f"{m}.parquet", columns=["id", "position"]).rename(columns={"id": "event_id"})
                     .assign(match_id=m) for m in sorted(Rc["match_id"].unique())], ignore_index=True)
    d = Rc.merge(pos, on=["match_id", "event_id"], how="left")
    d = d[(d["position"] != "Goalkeeper") & d["recv_x"].notna() & d["period"].isin([1, 2])].reset_index(drop=True)
    d["role"] = d["player_id"].map(roles["role"]).fillna("NONE")
    codes = {r: i for i, r in enumerate(sorted(d["role"].unique()))}
    d["role_code"] = d["role"].map(codes)
    f = d["match_id"].map(folds).values
    oof = np.full(len(d), np.nan)
    for k in range(5):
        tr, te = f != k, f == k
        m = xgb.XGBClassifier(**CLF_KWARGS).fit(d.loc[tr, T47_FEATURES].astype(float), d.loc[tr, "pressured_flag"].astype(int))
        oof[te] = m.predict_proba(d.loc[te, T47_FEATURES].astype(float))[:, 1]
    auc = float(roc_auc_score(d["pressured_flag"].astype(int), oof))
    d["v"] = d["pressured_flag"].astype(float) - oof
    key = ["match_id", "team", "player_id"]
    h = d.groupby(key + ["period"])["v"].agg(["sum", "count"]).unstack("period")
    h.columns = [f"{a}_{b}" for a, b in h.columns]
    h = h.fillna(0).reset_index()
    e1 = d[(d["period"] == 1) & d["pr2_flag_keep"].notna()].groupby(key)["pr2_flag_keep"].agg(E1="mean", n_e1="size").reset_index()
    u = h.merge(e1, on=key, how="left")
    u = u[(u["count_1"] >= 10) & (u["count_2"] >= 10) & (u["n_e1"].fillna(0) >= 5)].copy()
    u["P_H1"], u["P_H2"] = u["sum_1"] / u["count_1"], u["sum_2"] / u["count_2"]
    u["dP"] = u["P_H2"] - u["P_H1"]
    t = d.groupby(["match_id", "team", "period"])["v"].agg(["sum", "count"]).unstack("period")
    t.columns = [f"t{a}_{b}" for a, b in t.columns]
    u = u.merge(t.reset_index(), on=["match_id", "team"], how="left")
    u["dP_mates"] = (u["tsum_2"] - u["sum_2"]) / (u["tcount_2"] - u["count_2"]) - (u["tsum_1"] - u["sum_1"]) / (u["tcount_1"] - u["count_1"])
    u["role"] = u["player_id"].map(roles["role"]).fillna("NONE")
    u["g0"] = 0.0
    main = fit_multi(u.dropna(subset=["dP"]), "dP", ["E1", "P_H1"], "g0")
    plac = fit_multi(u.dropna(subset=["dP_mates"]), "dP_mates", ["E1", "P_H1"], "g0")
    return {"baseline_auc": auc, "n_units": len(u), "n_players": int(u["player_id"].nunique()),
            "main": {"n": main["n_rows"], "E1": main["E1"], "P_H1": main["P_H1"]},
            "placebo": {"n": plac["n_rows"], "E1": plac["E1"]}}


def c4_movers(R, intl_map):
    R = R.assign(intl=[intl_map.get((c, s)) for c, s in zip(R["competition_id"], R["season_id"])])
    ctx = R.groupby(["player_id", "team", "competition_id", "season_id", "intl"])["pr2_flag_keep"].size().rename("n").reset_index()
    ctx = ctx[ctx["n"] >= MIN_CTX]
    club, intl = {}, {}
    for pid, g in ctx.groupby("player_id"):
        if g["intl"].any() and (~g["intl"]).any():
            for side, store in ((False, club), (True, intl)):
                keys = set(zip(g.loc[g["intl"] == side, "team"], g.loc[g["intl"] == side, "competition_id"], g.loc[g["intl"] == side, "season_id"]))
                sub = R[R["player_id"] == pid]
                store[pid] = sub[[k in keys for k in zip(sub["team"], sub["competition_id"], sub["season_id"])]]["pr2_flag_keep"].values
    n = len(club)
    if n < MIN_MOVERS:
        return {"n_movers": n, "run": False}
    pids = sorted(club)
    ma, mb = np.array([club[p].mean() for p in pids]), np.array([intl[p].mean() for p in pids])
    ra = sb.split_half_reliability([club[p] for p in pids], sb.N_SPLITS_PH_B2, SEED)
    rb = sb.split_half_reliability([intl[p] for p in pids], sb.N_SPLITS_PH_B2, SEED + 1)
    r_obs = float(np.corrcoef(ma, mb)[0, 1])
    out = {"n_movers": n, "run": True, "rel_club": ra, "rel_intl": rb, "r_obs": r_obs}
    if ra < 0.10 or rb < 0.10:
        return {**out, "unmeasurable": True, "p": 1.0, "r_true": None}
    out["r_true"] = float(np.clip(r_obs / np.sqrt(ra * rb), -1, 1))
    rng = np.random.default_rng(SEED)
    boot = np.empty(sb.N_BOOTSTRAP)
    idx = np.arange(n)
    for k in range(sb.N_BOOTSTRAP):
        dd = rng.choice(idx, size=n, replace=True)
        r = np.corrcoef(ma[dd], mb[dd])[0, 1]
        a = sb.split_half_reliability([club[pids[i]] for i in dd], sb.N_SPLITS_PH_B2_BOOT, SEED + 1000 + k)
        b = sb.split_half_reliability([intl[pids[i]] for i in dd], sb.N_SPLITS_PH_B2_BOOT, SEED + 2000 + k)
        boot[k] = np.clip(r / np.sqrt(max(a, 1e-8) * max(b, 1e-8)), -1, 1)
    out["r_true_ci"] = [float(np.nanpercentile(boot, 2.5)), float(np.nanpercentile(boot, 97.5))]
    out["p"] = float(min(1.0, 2 * np.nanmean(boot <= 0)))
    return out


def main():
    print("Task 48 Steps 2-3 (reserved data, single use) ...")
    Rc = pd.read_parquet(RECEPTIONS_PATH)
    roles = pd.read_parquet(ROLES_PATH).set_index("player_id")
    dm = set(roles.index[roles["is_dm"]])
    names = roles["player_name"].dropna()
    ing = json.loads((DATA_DIR / "engine_v2_task48_ingest.json").read_text())["per_competition_season"]
    intl_map = {(r["competition_id"], r["season_id"]): r["international"] for r in ing}
    Rc["role"] = Rc["player_id"].map(roles["role"]).fillna("NONE")
    Rc["y_f3"] = np.where(Rc["recv_x"] < F3_X, Rc["y_f3"], np.nan)
    from task44_build import match_folds
    folds = match_folds(sorted(Rc["match_id"].unique()))

    allk = Rc.dropna(subset=["keep_spell", "player_id"])
    keep_s = leave_one_match_out(allk[["match_id", "player_id", "keep_spell"]].rename(columns={"keep_spell": "decision"}),
                                 "player_id", 100)[["match_id", "player_id", "complement_mean"]]

    R = Rc[Rc["pr2_flag_keep"].notna()].copy().reset_index(drop=True)
    A = Rc[Rc["w"].notna()].copy().reset_index(drop=True)
    gr2 = {}
    for name, df in (("pressured", R), ("completed", A)):
        for y, g in (("y_f3", "g_f3"), ("y_net_xg", "g_xg"), ("keep_spell", "g_keep")):
            df[g], gr2[f"{name}|{y}"] = crossfit_ev(df, y)
    ctrl_R = R.merge(keep_s, on=["match_id", "player_id"], how="left").rename(columns={"complement_mean": "S_raw"})
    ctrl_A = A.merge(keep_s, on=["match_id", "player_id"], how="left").rename(columns={"complement_mean": "S_raw"})
    R["a1"] = R["pr2_flag_keep"] - R.groupby(["team", "competition_id", "season_id"])["pr2_flag_keep"].transform("mean")

    S_pr = s_loo(R, "pr2_flag_keep")
    wv = leave_one_match_out(A[["match_id", "player_id", "w"]].rename(columns={"w": "decision"}), "player_id", 100)
    S_w = A.merge(wv[["match_id", "player_id", "complement_mean"]], on=["match_id", "player_id"], how="left") \
           .rename(columns={"complement_mean": "S_raw"})
    S_a1 = s_loo(R, "a1")

    fam = {}
    fam["C1"] = summarise(ptest(S_pr[S_pr["player_id"].isin(dm)], "y_f3", "g_f3", ctrl_R))
    fam["C2"] = summarise(ptest(S_w[S_w["player_id"].isin(dm)], "y_f3", "g_f3", ctrl_A))
    c3 = c3_model(Rc, roles, folds)
    fam["C3"] = {"coef_per_sd": c3["main"]["E1"]["coef_per_sd"], "ci95": c3["main"]["E1"]["ci95"], "p": c3["main"]["E1"]["p"],
                 "n_rows": c3["main"]["n"], "n_players": c3["n_players"], "mde_80": 2.8 * c3["main"]["E1"]["se"],
                 "placebo": c3["placebo"]["E1"], "baseline_auc": c3["baseline_auc"], "P_H1": c3["main"]["P_H1"]}
    c4 = c4_movers(R, intl_map)
    fam["C4"] = c4
    fam["C6"] = summarise(ptest(S_a1, "y_f3", "g_f3", ctrl_R))
    run = [k for k in ("C1", "C2", "C3", "C4", "C6") if not (k == "C4" and not c4["run"])]
    adj = multipletests([fam[k]["p"] for k in run], method="holm")[1]
    for k, a in zip(run, adj):
        f = fam[k]
        f["p_holm"] = float(a)
        if k in ("C1", "C2", "C6"):
            sign_ok = f["coef_per_sd"] > 0
            extra = f["control"]["coef_per_sd"] > 0 and f["control"]["p"] < 0.05
        elif k == "C3":
            sign_ok = f["coef_per_sd"] < 0
            extra = not (f["placebo"]["coef_per_sd"] < 0 and f["placebo"]["p"] < 0.05)
        else:
            sign_ok = f.get("r_true") is not None and f["r_true"] > 0
            extra = True
        f["confirmed"] = bool(a < 0.05 and sign_ok and extra)
        print(f"  {k}: p={f['p']:.4g} holm={a:.4g} confirmed={f['confirmed']} | {json.dumps(f, default=str)[:300]}")
    if not c4["run"]:
        print(f"  C4 NOT RUN: {c4['n_movers']} movers (< {MIN_MOVERS})")

    rep = {"C1_net_xg": summarise(ptest(S_pr[S_pr["player_id"].isin(dm)], "y_net_xg", "g_xg", ctrl_R)),
           "C2_net_xg": summarise(ptest(S_w[S_w["player_id"].isin(dm)], "y_net_xg", "g_xg", ctrl_A)),
           "R1": {"pr2_flag_keep": {"DM": r1(R, "pr2_flag_keep", "mean", dm), "all": r1(R, "pr2_flag_keep", "mean")},
                  "w": {"DM": r1(A, "w", "mean", dm), "all": r1(A, "w", "mean")}}}
    l_ids = set()
    rep["praised_list_matches"] = {}
    for nm in LIST_L:
        hits = names[names.apply(lambda full: name_matches(nm, full))]
        rep["praised_list_matches"][nm] = hits.tolist()
        if len(hits) == 1:
            l_ids.add(hits.index[0])
    rng = np.random.default_rng(SEED)
    for col, df, floor in (("pr2_flag_keep", R, 50), ("w", A, 100)):
        a = df.groupby("player_id")[col].agg(["mean", "size"])
        a = a[a["size"] >= floor]
        v = pd.DataFrame({"sb_player_id": a.index.astype(float), "m": a["mean"].values})
        v["role"] = v["sb_player_id"].map(roles["role"])
        res = perm_test(v.dropna(subset=["role"]), l_ids, rng)
        res["present_names"] = [names.get(r["sb_player_id"]) for r in res.get("present", [])]
        rep[f"praised_{col}"] = res
        rep[f"table_{col}"] = dm_table(df, col, dm, names.to_dict()) if len(dm) >= 3 else None
    print(f"  R1: {rep['R1']}")
    print(f"  praised: PR T={rep['praised_pr2_flag_keep'].get('T')} p={rep['praised_pr2_flag_keep'].get('p_two_sided')}; "
          f"W T={rep['praised_w'].get('T')} p={rep['praised_w'].get('p_two_sided')}")
    SUMMARY_PATH.write_text(json.dumps({"g_oof_r2": gr2, "family": fam, "family_run": run, "report_only": rep,
                                        "n_dm": len(dm), "c3_detail": c3}, indent=2, default=str))
    print(f"Wrote {SUMMARY_PATH}")


if __name__ == "__main__":
    main()
