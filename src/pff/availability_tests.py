"""
Task 38, Steps 2-4: deep-midfield group, R1 stability, R2 pass-level
out-of-match results test, R3 distinctness, and the Task 29-method DM
table, on availability.py's outputs. docs/specs/task-38-availability.md.

Reuses unchanged: task35_ptest.fe_fit (Y ~ S + g + role FE + team-match FE,
cluster by player), task33_step3_f_state.XGB_REGRESSOR_KWARGS (Task 35's
hyperparameters), task28_step1_2.estimate_sigma2w_rho,
task29_step1_2.dersimonian_laird / shrink.

Run: python src/pff/availability_tests.py   (after availability.py)
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import r2_score

sys.path.insert(0, str(Path(__file__).parent.parent / "engine_v2"))
from task35_ptest import fe_fit  # noqa: E402
from task33_step3_f_state import XGB_REGRESSOR_KWARGS  # noqa: E402
from task28_step1_2 import estimate_sigma2w_rho  # noqa: E402
from task29_step1_2 import dersimonian_laird, shrink  # noqa: E402
from availability import MOMENTS_PATH, RECEPTIONS_PATH, N_FOLDS, SEED, BONO_OVERRIDE  # noqa: E402
from frames import OUT_DIR, load_meta  # noqa: E402

DATA_DIR = Path(__file__).parent.parent.parent / "data"
SB_EVENTS = DATA_DIR / "raw" / "events"
CROSSFIT_V5_PATH = DATA_DIR / "processed" / "engine_v2" / "pass_der_crossfit_v5.parquet"
REC34_PATH = DATA_DIR / "processed" / "engine_v2" / "task34_receptions.parquet"
SUMMARY_PATH = DATA_DIR / "pff_task38_tests.json"
TABLE_PATH = OUT_DIR / "availability_dm_table.parquet"

DM_POSITIONS = {"Center Defensive Midfield", "Left Defensive Midfield", "Right Defensive Midfield"}
DM_SHARE_MIN, DM_MIN_MATCHES, DM_MIN_MOMENTS = 0.50, 3, 300
R1_MIN_MATCHES, R1_SPLITS, R1_BAR = 4, 100, 0.60
R2_MIN_OTHER_MATCHES = 2
G_FEATURES = ["rec_x", "rec_y", "rec_pressure", "period", "minute"]


def fisher_ci(r, n):
    if r is None or n < 4 or np.isnan(r):
        return [None, None]
    z, se = np.arctanh(r), 1 / np.sqrt(n - 3)
    return [float(np.tanh(z - 1.96 * se)), float(np.tanh(z + 1.96 * se))]


def player_map() -> pd.DataFrame:
    pm = pd.read_csv(OUT_DIR / "player_map.csv")
    ok = (pm["status"] == "mapped") | ((pm["team"] == BONO_OVERRIDE["team"]) & (pm["shirt"].astype(str) == BONO_OVERRIDE["shirt"]))
    return pm[ok]


def dm_group(mom: pd.DataFrame, pm: pd.DataFrame, cw: pd.DataFrame) -> tuple:
    wc = set(cw["statsbomb_match_id"])
    cf = pd.read_parquet(CROSSFIT_V5_PATH, columns=["match_id", "event_id", "player_id"])
    cf = cf[cf["match_id"].isin(wc)]
    pos = pd.concat([pd.read_parquet(SB_EVENTS / f"{m}.parquet", columns=["id", "position"]).assign(match_id=m)
                     for m in sorted(wc)]).rename(columns={"id": "event_id"})
    cf = cf.merge(pos, on=["match_id", "event_id"], how="left")
    share = cf.assign(is_dm=cf["position"].isin(DM_POSITIONS)).groupby("player_id").agg(
        n_wc_passes=("is_dm", "size"), dm_share=("is_dm", "mean")).reset_index()
    sb2pff = pm.drop_duplicates("sb_player_id").set_index("sb_player_id")["pff_player_id"]
    share["pff_player_id"] = share["player_id"].map(sb2pff)
    pl = mom.groupby("pff_player_id").agg(n_matches=("pff_game_id", "nunique"), n_moments=("av", "size"))
    share = share.join(pl, on="pff_player_id")
    dm = share[(share["dm_share"] >= DM_SHARE_MIN) & (share["n_matches"] >= DM_MIN_MATCHES)
               & (share["n_moments"] >= DM_MIN_MOMENTS)]
    return set(dm["pff_player_id"].astype(int)), share


def r1(mom: pd.DataFrame, col: str, pids=None) -> dict:
    d = mom.dropna(subset=[col])
    if pids is not None:
        d = d[d["pff_player_id"].isin(pids)]
    pm = d.groupby(["pff_player_id", "pff_game_id"])[col].agg(["sum", "count"]).reset_index()
    nm = pm.groupby("pff_player_id").size()
    players = sorted(nm[nm >= R1_MIN_MATCHES].index)
    by = {p: g[["sum", "count"]].to_numpy() for p, g in pm[pm["pff_player_id"].isin(players)].groupby("pff_player_id")}
    rng = np.random.default_rng(SEED)
    sbs = []
    for _ in range(R1_SPLITS):
        h1, h2 = [], []
        for p in players:
            a = by[p]
            idx = rng.permutation(len(a))
            k = len(a) // 2
            x, y = a[idx[:k]], a[idx[k:]]
            h1.append(x[:, 0].sum() / x[:, 1].sum())
            h2.append(y[:, 0].sum() / y[:, 1].sum())
        r = np.corrcoef(h1, h2)[0, 1]
        sbs.append(2 * r / (1 + r))
    sbs = np.array(sbs)
    return {"n_players": len(players), "median": float(np.median(sbs)), "p5": float(np.percentile(sbs, 5)),
            "p95": float(np.percentile(sbs, 95))}


def loo_match_mean(mom: pd.DataFrame, col: str) -> pd.DataFrame:
    d = mom.dropna(subset=[col])
    pm = d.groupby(["pff_player_id", "pff_game_id"])[col].agg(["sum", "count"]).reset_index()
    tot = pm.groupby("pff_player_id").agg(s=("sum", "sum"), c=("count", "sum"), nm=("pff_game_id", "size"))
    pm = pm.join(tot, on="pff_player_id")
    pm["n_other_matches"] = pm["nm"] - 1
    pm["S_raw"] = np.where(pm["n_other_matches"] >= R2_MIN_OTHER_MATCHES,
                           (pm["s"] - pm["sum"]) / (pm["c"] - pm["count"]), np.nan)
    return pm[["pff_player_id", "pff_game_id", "S_raw", "n_other_matches"]]


def r2(rec: pd.DataFrame, mom: pd.DataFrame, col: str, dm_ids: set) -> dict:
    d = rec.merge(loo_match_mean(mom, col), on=["pff_player_id", "pff_game_id"], how="left")
    d = d.rename(columns={"pff_player_id": "player_id", "pff_game_id": "match_id", "team_id": "team"})
    d["role"] = d["role"].fillna("NONE")
    d = d[d["role"] != "GK"]
    out = {"PRIMARY_all_outfield": fe_fit(d, "y_net_xg", "g_oof"),
           "DM_report": fe_fit(d[d["player_id"].isin(dm_ids)], "y_net_xg", "g_oof")}
    p = out["PRIMARY_all_outfield"]
    out["pass"] = bool(p["coef_per_sd"] > 0 and p["p"] < 0.05)
    return out


def table(mom: pd.DataFrame, col: str, dm_ids: set, names: dict, teams: dict) -> dict:
    pp = mom[mom["pff_player_id"].isin(dm_ids)].dropna(subset=[col])
    pp = pp[["pff_player_id", "pff_game_id", col]].rename(columns={"pff_player_id": "player_id", "pff_game_id": "match_id",
                                                                     col: "decision_new"})
    s2, rho, anova = estimate_sigma2w_rho(pp)
    g = pp.groupby("player_id")
    st = pd.DataFrame({"m_i": g["decision_new"].mean(), "n_i": g.size(), "G_i": g["match_id"].nunique()}).reset_index()
    st["v_i"] = s2 * (1 + (st["n_i"] / st["G_i"] - 1) * rho) / st["n_i"]
    dl = dersimonian_laird(st["m_i"].values, st["v_i"].values)
    t = shrink(st, dl["mu_w"], dl["tau2"], "m_i", "v_i").sort_values("shrunken_i", ascending=False).reset_index(drop=True)
    t["rank"] = t.index + 1
    t["name"] = t["player_id"].map(names)
    t["team"] = t["player_id"].map(teams)
    above = t[t["ci_low_90"] > dl["mu_w"]]
    below = t[t["ci_high_90"] < dl["mu_w"]]
    return {"sigma2_w": s2, "rho": rho, "dl": dl, "n_above": len(above), "names_above": above["name"].tolist(),
            "n_below": len(below), "names_below": below["name"].tolist(),
            "rows": t[["rank", "player_id", "name", "team", "G_i", "n_i", "m_i", "shrunken_i", "ci_low_90", "ci_high_90"]]
            .to_dict("records")}


def main():
    mom = pd.read_parquet(MOMENTS_PATH)
    rec = pd.read_parquet(RECEPTIONS_PATH)
    cw = pd.read_csv(OUT_DIR / "crosswalk.csv")
    pm = player_map()
    names = pm.drop_duplicates("pff_player_id").set_index("pff_player_id")["pff_name"].to_dict()
    team_name = {}
    for gid in cw["pff_game_id"]:
        m = load_meta(int(gid))
        team_name[int(m["homeTeam"]["id"])] = m["homeTeam"]["name"]
        team_name[int(m["awayTeam"]["id"])] = m["awayTeam"]["name"]
    teams = mom.groupby("pff_player_id")["team_id"].agg(lambda s: team_name[int(s.mode().iloc[0])]).to_dict()

    dm_ids, share = dm_group(mom, pm, cw)
    dm_list = [{"pff_player_id": p, "name": names.get(p), "team": teams.get(p),
                **share.loc[share["pff_player_id"] == p, ["dm_share", "n_wc_passes", "n_matches", "n_moments"]].iloc[0].to_dict()}
               for p in sorted(dm_ids, key=lambda x: names.get(x, ""))]
    n_dm_share_only = int((share["dm_share"] >= DM_SHARE_MIN).sum())
    print(f"  DM group: {len(dm_ids)} (DM share >= 0.5 before match/moment minimums: {n_dm_share_only})")

    res_r1 = {"AV_DM": r1(mom, "av", dm_ids), "AV_all_outfield": r1(mom, "av"),
              "AV_vis_DM": r1(mom, "av_vis", dm_ids), "AV_vis_all_outfield": r1(mom, "av_vis")}
    res_r1["pass_AV_DM"] = res_r1["AV_DM"]["median"] >= R1_BAR
    res_r1["pass_AV_vis_DM"] = res_r1["AV_vis_DM"]["median"] >= R1_BAR
    print(f"  R1: {res_r1}")

    oof = np.full(len(rec), np.nan)
    for k in range(N_FOLDS):
        tr, te = (rec["fold"] != k).values, (rec["fold"] == k).values
        mdl = xgb.XGBRegressor(**XGB_REGRESSOR_KWARGS).fit(rec.loc[tr, G_FEATURES].astype(float), rec.loc[tr, "y_net_xg"])
        oof[te] = mdl.predict(rec.loc[te, G_FEATURES].astype(float))
    rec["g_oof"] = oof
    g_r2 = float(r2_score(rec["y_net_xg"], oof))
    res_r2 = {"g_oof_r2": g_r2, "n_receptions": len(rec), "y_mean": float(rec["y_net_xg"].mean()),
              "y_sd": float(rec["y_net_xg"].std()),
              "AV": r2(rec, mom, "av", dm_ids), "AV_vis": r2(rec, mom, "av_vis", dm_ids)}
    for k in ("AV", "AV_vis"):
        for kk in ("PRIMARY_all_outfield", "DM_report"):
            r = res_r2[k][kk]
            print(f"  R2 {k} {kk}: n={r['n_rows']} players={r['n_players']} coef100={r['coef_per_sd_per100']:+.4f} "
                  f"CI100={[round(x, 4) for x in r['ci95_per100']]} p={r['p']:.4g} MDE100={r['mde_80_per100']:.4f}")

    wc = set(cw["statsbomb_match_id"])
    pl = mom.groupby("pff_player_id")["av"].mean().rename("av")
    sb_of = pm.drop_duplicates("pff_player_id").set_index("pff_player_id")["sb_player_id"]
    cf = pd.read_parquet(CROSSFIT_V5_PATH, columns=["match_id", "player_id", "decision"])
    dec = cf[cf["match_id"].isin(wc)].groupby("player_id")["decision"].mean()
    r34 = pd.read_parquet(REC34_PATH, columns=["match_id", "player_id", "rq_rel"])
    rq = r34[r34["match_id"].isin(wc)].groupby("player_id")["rq_rel"].mean()
    rpm = rec.groupby("pff_player_id").size() / mom.groupby("pff_player_id")["pff_game_id"].nunique()
    t3 = pd.DataFrame({"av": pl}).loc[sorted(dm_ids)]
    t3["decision_v5"] = t3.index.map(lambda p: dec.get(sb_of.get(p)))
    t3["rq_rel_task34"] = t3.index.map(lambda p: rq.get(sb_of.get(p)))
    t3["receptions_per_match"] = t3.index.map(lambda p: rpm.get(p))
    res_r3 = {}
    for c in ("decision_v5", "rq_rel_task34", "receptions_per_match"):
        s = t3[["av", c]].astype(float).dropna()
        r = float(s["av"].corr(s[c])) if len(s) >= 3 else None
        res_r3[c] = {"n": len(s), "r": r, "fisher_95": fisher_ci(r, len(s))}
    print(f"  R3: {res_r3}")

    tab_av = table(mom, "av", dm_ids, names, teams)
    tab_vis = table(mom, "av_vis", dm_ids, names, teams)
    pd.DataFrame(tab_av["rows"]).to_parquet(TABLE_PATH)
    print(f"  Step 4 AV: Q={tab_av['dl']['Q']:.2f} df={tab_av['dl']['df']} p={tab_av['dl']['p_value']:.4g} "
          f"above={tab_av['n_above']} below={tab_av['n_below']}")
    print(f"  Step 4 AV_vis: Q={tab_vis['dl']['Q']:.2f} p={tab_vis['dl']['p_value']:.4g} "
          f"above={tab_vis['n_above']} below={tab_vis['n_below']}")

    summary = {"dm_group": dm_list, "n_dm": len(dm_ids), "n_dm_share_only": n_dm_share_only,
               "r1": res_r1, "r2": res_r2, "r3": res_r3, "step4_av": tab_av, "step4_av_vis": tab_vis}
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
    print(f"Wrote {SUMMARY_PATH}")


if __name__ == "__main__":
    main()
