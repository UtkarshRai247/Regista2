"""
Task 45: vetting press resistance -- team style (A1) and usual passing
style (A2). SECOND use of the 2015/16 data. Measurement only; PR2_flag is
unchanged. docs/specs/task-45-press-resistance-vetting.md.

A1: unit-level PR2_flag_keep residual after team x season fixed effects
    (one season: team fixed effects), OLS with equal unit weights, i.e. the
    unit minus its team's mean. Player score = mean residual.
A2: A1 player score residualised (WLS across players, weight = pressured
    receptions) on his completion rate, share of passes < 15 units and
    share with end x - start x < 0, all from his eligible passes NOT under
    pressure; fitted on players with >= 50 pressured receptions and >= 100
    unpressured eligible passes. Unit A2 = unit A1 - that player's fitted
    value, so player means equal the WLS residuals.
Reuses: Task 44's r1 / crossfit_ev / roles and files, task35_ptest.fe_fit,
task42_step2.s_loo / dm_table, Task 41's perm_test and list.

Run: python src/engine_v2/task45_vetting.py
"""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats import spearmanr
from statsmodels.stats.multitest import multipletests

import task35_ptest as tp
from task32_step5 import leave_one_match_out
from task42_step2 import s_loo, dm_table
from task27_step1_deep_midfield import name_matches
from task41_lists_availability import perm_test, LIST_L
from task44_build import PASSES_PATH, RECEPTIONS_PATH, ROLES_PATH, EV16
from task44_tests import r1, crossfit_ev

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
SUMMARY_PATH = DATA_DIR / "engine_v2_task45.json"
SEED = 20260928
MIN_PR, MIN_UNPRESSURED = 50, 100
SHORT = 15.0
FWD = 5.0
F3_X = 80.0
ROLES6 = ["CB", "FB", "DM", "CM", "AM/W", "FW"]
LEAGUES = {2: "Premier League", 7: "Ligue 1", 9: "Bundesliga", 11: "La Liga", 12: "Serie A"}


def pass_geometry(mids) -> tuple:
    """Per Pass: length and end x - start x; per completed receipt: the receiver's first Pass after it in the
    same possession (the spell-ending pass when keep_spell = 1)."""
    pg, ends = [], []
    for m in mids:
        ev = pd.read_parquet(EV16 / f"{m}.parquet", columns=["id", "index", "type", "player_id", "possession",
                                                             "location", "pass_end_location", "pass_length",
                                                             "ball_receipt_outcome"])
        ev = ev.sort_values("index").reset_index(drop=True)
        isp = (ev["type"] == "Pass").values
        sx = np.array([l[0] if isinstance(l, (list, np.ndarray)) else np.nan for l in ev["location"]])
        ex = np.array([l[0] if isinstance(l, (list, np.ndarray)) else np.nan for l in ev["pass_end_location"]])
        pg.append(pd.DataFrame({"match_id": m, "event_id": ev["id"][isp].values, "length": ev["pass_length"][isp].values,
                                "dx": (ex - sx)[isp]}))
        typ, pl, poss = ev["type"].values, ev["player_id"].values, ev["possession"].values
        for i in np.flatnonzero((typ == "Ball Receipt*") & ev["ball_receipt_outcome"].isna().values):
            for k in range(i + 1, len(ev)):
                if poss[k] != poss[i]:
                    break
                if pl[k] == pl[i] and typ[k] == "Pass":
                    ends.append((m, ev.at[i, "id"], float(ev.at[k, "pass_length"]), float(ex[k] - sx[k])))
                    break
    return pd.concat(pg, ignore_index=True), pd.DataFrame(ends, columns=["match_id", "event_id", "end_length", "end_dx"])


def end_shares(df: pd.DataFrame) -> dict:
    d = df[(df["keep_spell"] == 1) & df["end_dx"].notna()]
    if len(d) == 0:
        return {"n": 0}
    return {"n": len(d), "forward": float((d["end_dx"] >= FWD).mean()), "backward": float((d["end_dx"] <= -FWD).mean()),
            "sideways": float(((d["end_dx"] > -FWD) & (d["end_dx"] < FWD)).mean()),
            "median_length": float(d["end_length"].median())}


def main():
    print("Task 45: press-resistance vetting (second use of 2015/16) ...")
    roles = pd.read_parquet(ROLES_PATH).set_index("player_id")
    names = roles["player_name"].dropna()
    dm_ids = set(roles.index[roles["is_dm"]])
    Rc = pd.read_parquet(RECEPTIONS_PATH)
    P = pd.read_parquet(PASSES_PATH, columns=["match_id", "event_id", "player_id", "under_pressure", "pass_complete"])
    mids = sorted(Rc["match_id"].unique())
    pg, ends = pass_geometry(mids)
    P = P.merge(pg, on=["match_id", "event_id"], how="left")

    R = Rc[Rc["pr2_flag_keep"].notna()].copy().reset_index(drop=True)
    R = R.merge(ends, on=["match_id", "event_id"], how="left")
    R["role"] = R["player_id"].map(roles["role"]).fillna("NONE")

    # ---- A1 ----
    tm = R.groupby("team")["pr2_flag_keep"].transform("mean")
    R["a1"] = R["pr2_flag_keep"] - tm
    sst = float(((R["pr2_flag_keep"] - R["pr2_flag_keep"].mean()) ** 2).sum())
    team_share = 1 - float((R["a1"] ** 2).sum()) / sst
    assert np.allclose(R.groupby("team")["a1"].mean(), 0, atol=1e-12)
    lg_mean = R.groupby("competition_id")["a1"].transform("mean")
    assert np.allclose(lg_mean, 0, atol=1e-12)  # league FE added to A1 changes nothing: league is nested in team

    # ---- A2 ----
    un = P[P["under_pressure"] == 0]
    style = un.groupby("player_id").agg(n_unpressured=("event_id", "size"), completion=("pass_complete", "mean"),
                                        short_share=("length", lambda s: float((s < SHORT).mean())),
                                        back_side_share=("dx", lambda s: float((s < 0).mean())))
    pl = R.groupby("player_id").agg(a1=("a1", "mean"), n_pr=("a1", "size")).join(style, how="inner")
    fit_set = pl[(pl["n_pr"] >= MIN_PR) & (pl["n_unpressured"] >= MIN_UNPRESSURED)]
    X = sm.add_constant(fit_set[["completion", "short_share", "back_side_share"]])
    wls = sm.WLS(fit_set["a1"], X, weights=fit_set["n_pr"]).fit()
    fitted = pd.Series(wls.predict(sm.add_constant(pl[["completion", "short_share", "back_side_share"]])), index=pl.index)
    R["a2"] = R["a1"] - R["player_id"].map(fitted)
    chk = R.dropna(subset=["a2"]).groupby("player_id")["a2"].mean()
    assert np.allclose(chk.loc[fit_set.index], wls.resid.loc[fit_set.index], atol=1e-9)
    a2_fit = {"n_players": len(fit_set), "params": wls.params.to_dict(), "pvalues": wls.pvalues.to_dict(),
              "r2": float(wls.rsquared)}
    print(f"  team FE share {team_share:.4f}; A2 WLS {a2_fit}")

    # ---- praised-list ids (as Task 44) ----
    l_ids, l_names = set(), {}
    for nm in LIST_L:
        hits = names[names.apply(lambda full: name_matches(nm, full))]
        if len(hits) == 1:
            l_ids.add(hits.index[0])
            l_names[hits.index[0]] = hits.iloc[0]

    def praised(col, pool=None, ids=None, seed=SEED):
        a = R.groupby("player_id")[col].agg(["mean", "size"])
        a = a[a["size"] >= MIN_PR]
        if pool is not None:
            a = a[a.index.isin(pool)]
        v = pd.DataFrame({"sb_player_id": a.index.astype(float), "m": a["mean"].values})
        v["role"] = v["sb_player_id"].map(roles["role"])
        res = perm_test(v.dropna(subset=["role"]), l_ids if ids is None else ids, np.random.default_rng(seed))
        res["present_names"] = [names.get(r["sb_player_id"]) for r in res.get("present", [])]
        return res

    measures = {"unadjusted": "pr2_flag_keep", "A1": "a1", "A2": "a2"}
    s12 = {}
    for lab, col in measures.items():
        s12[lab] = {"R1_DM": r1(R, col, "mean", dm_ids), "table": dm_table(R.dropna(subset=[col]), col, dm_ids, names.to_dict()),
                    "praised": praised(col)}
        t = s12[lab]["table"]
        print(f"  {lab}: R1 DM {s12[lab]['R1_DM']}; Q={t['dl']['Q']:.1f} p={t['dl']['p_value']:.3g} "
              f"above={len(t['names_above'])} below={len(t['names_below'])}; praised T={s12[lab]['praised']['T']:+.3f} "
              f"p={s12[lab]['praised']['p_two_sided']:.4g}")
    adj = multipletests([s12["A1"]["praised"]["p_two_sided"], s12["A2"]["praised"]["p_two_sided"]], method="holm")[1]
    s12["A1"]["praised"]["p_holm_A1_A2"], s12["A2"]["praised"]["p_holm_A1_A2"] = float(adj[0]), float(adj[1])
    dmm = R[R["player_id"].isin(dm_ids)].groupby("player_id")[["pr2_flag_keep", "a1", "a2"]].mean()
    s12["spearman_DM"] = {"A1_vs_unadjusted": float(spearmanr(dmm["pr2_flag_keep"], dmm["a1"], nan_policy="omit")[0]),
                          "A2_vs_unadjusted": float(spearmanr(dmm["pr2_flag_keep"], dmm["a2"], nan_policy="omit")[0]),
                          "n": int(len(dmm))}
    st = dmm.join(style, how="left")
    s12["raw_corr_DM_unadjusted_vs_style"] = {c: {"r": float(st["pr2_flag_keep"].corr(st[c])), "n": int(st[c].notna().sum())}
                                              for c in ("completion", "short_share", "back_side_share")}
    ranked = [r["player_id"] for r in s12["unadjusted"]["table"]["rows"]]
    desc = {"top20": end_shares(R[R["player_id"].isin(ranked[:20])]), "bottom20": end_shares(R[R["player_id"].isin(ranked[-20:])])}
    for pid, nm in l_names.items():
        desc[nm] = end_shares(R[R["player_id"] == pid])
    s12["ending_pass_descriptive"] = desc
    print(f"  spearman {s12['spearman_DM']}; style corr {s12['raw_corr_DM_unadjusted_vs_style']}; desc {desc}")

    # ---- Step 3: league ----
    pl_league = roles["league"]
    s3 = {}
    for c, lname in LEAGUES.items():
        in_lg = set(pl_league.index[pl_league == c])
        s3[lname] = {}
        for lab, col in measures.items():
            rel = r1(R, col, "mean", dm_ids & in_lg)
            pr = praised(col, pool=in_lg)
            s3[lname][lab] = {"R1_DM": rel, "praised_T": pr.get("T"), "praised_p": pr.get("p_two_sided"),
                              "n_present": pr["n_present"], "n_qualifying": pr.get("n_qualifying")}
    s3["A1_plus_league_FE"] = "identical to A1: league is nested in team (asserted: A1 league means are 0)"
    print(f"  Step 3 done")

    # ---- Step 4: leave-one-out ----
    s4 = {}
    for lab, col in measures.items():
        s4[lab] = {}
        present = [r["sb_player_id"] for r in s12[lab]["praised"].get("present", [])]
        for pid in present:
            res = praised(col, ids=l_ids - {pid, int(pid)})
            s4[lab][names.get(pid)] = {"T": res.get("T"), "p": res.get("p_two_sided"), "n_present": res["n_present"]}
    print(f"  Step 4: {s4}")

    # ---- Step 5: adjusted P-tests ----
    R["y_f3"] = np.where(R["recv_x"] < F3_X, R["y_f3"], np.nan)
    gr2 = {}
    for y, g in (("y_net_xg", "g_xg"), ("y_f3", "g_f3"), ("keep_spell", "g_keep")):
        R[g], gr2[y] = crossfit_ev(R, y)
    allk = Rc.dropna(subset=["keep_spell", "player_id"])
    vals = leave_one_match_out(allk[["match_id", "player_id", "keep_spell"]].rename(columns={"keep_spell": "decision"}),
                               "player_id", 100)
    ctrl = R.merge(vals[["match_id", "player_id", "complement_mean"]], on=["match_id", "player_id"], how="left") \
            .rename(columns={"complement_mean": "S_raw"})

    def ptest(d, y):
        g = "g_xg" if y == "y_net_xg" else "g_f3"
        res = tp.fe_fit(d, y, g)
        ids = set(d.loc[d["S_raw"].notna() & d[y].notna(), "event_id"])
        res["control"] = tp.fe_fit(ctrl[ctrl["event_id"].isin(ids)], "keep_spell", "g_keep")
        return res
    s5 = {}
    for lab, col in (("A1", "a1"), ("A2", "a2")):
        d = s_loo(R.dropna(subset=[col]), col)
        for grp, filt in (("DM", dm_ids), ("all", None)):
            for y in ("y_f3", "y_net_xg"):
                dd = d if filt is None else d[d["player_id"].isin(filt)]
                s5[f"{lab}|{grp}|{y}"] = ptest(dd, y)
                r, c = s5[f"{lab}|{grp}|{y}"], s5[f"{lab}|{grp}|{y}"]["control"]
                print(f"  Step 5 {lab}|{grp}|{y}: n={r['n_rows']} players={r['n_players']} coef100={r['coef_per_sd_per100']:+.4f} "
                      f"p={r['p']:.4g} | control {c['coef_per_sd_per100']:+.3f} p={c['p']:.3g}")

    # ---- Step 6: every role (exploratory) ----
    s6 = {}
    for role in ROLES6:
        pids = set(roles.index[roles["role"] == role])
        s6[role] = {"n_players_role": len(pids),
                    "fwd_R1": r1(R, "pr2_flag_fwd", "mean", pids),
                    "ending_pass": end_shares(R[R["player_id"].isin(pids)])}
        for lab, col in (("unadjusted", "pr2_flag_keep"), ("A1", "a1")):
            d = s_loo(R, col)
            dd = d[d["player_id"].isin(pids)]
            t = dm_table(R, col, pids, names.to_dict())
            s6[role][lab] = {"R1": r1(R, col, "mean", pids),
                             "ptest_y_f3": ptest(dd, "y_f3"), "ptest_y_net_xg": ptest(dd, "y_net_xg"),
                             "Q": t["dl"], "top10": [{"name": r["name"], "shrunken": r["shrunken_i"], "n": r["n_i"]} for r in t["rows"][:10]]}
        print(f"  Step 6 {role}: R1 unadj {s6[role]['unadjusted']['R1']['median']:.3f} A1 {s6[role]['A1']['R1']['median']:.3f}")

    SUMMARY_PATH.write_text(json.dumps({"n_units": len(R), "team_fe_share": team_share, "a2_fit": a2_fit,
                                        "praised_ids": {str(k): v for k, v in l_names.items()}, "g_oof_r2": gr2,
                                        "steps1_2": s12, "step3": s3, "step4": s4, "step5": s5, "step6": s6},
                                       indent=2, default=str))
    print(f"Wrote {SUMMARY_PATH}")


if __name__ == "__main__":
    main()
