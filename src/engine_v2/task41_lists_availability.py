"""
Task 41, Steps 7-10: the pre-existing praised-players list against four
measures (2a), availability thresholds (2c), space at reception and
availability together (2d), and one Holm correction across every
within-DM results test (3b). docs/specs/task-41-vetting-round-2.md.

Reuses unchanged: task27_step1_deep_midfield.name_matches (plan v3's fixed
list), task32_step4.assign_roles, src/pff/availability.py (match_folds,
fit_oof) and src/pff/availability_tests.py (player_map, dm_group, r1, r2,
loo_match_mean, G_FEATURES), task41_ptest_vetting.fit_multi.

Run: python src/engine_v2/task41_lists_availability.py   (after task41_ptest_vetting.py)
"""
import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from statsmodels.stats.multitest import multipletests

sys.path.insert(0, str(Path(__file__).parent.parent / "pff"))
import availability as av  # noqa: E402
import availability_tests as avt  # noqa: E402
from task27_step1_deep_midfield import name_matches  # noqa: E402
from task32_step4 import assign_roles  # noqa: E402
from task33_step3_f_state import XGB_REGRESSOR_KWARGS  # noqa: E402
from task41_ptest_vetting import fit_multi  # noqa: E402

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
PFF_OUT = DATA_DIR / "processed" / "pff"
LEADERBOARD_V5C_PATH = DATA_DIR / "processed" / "leaderboard_v5c.parquet"
CROSSFIT_V5_PATH = DATA_DIR / "processed" / "engine_v2" / "pass_der_crossfit_v5.parquet"
REC34_PATH = DATA_DIR / "processed" / "engine_v2" / "task34_receptions.parquet"
SUMMARY_PATH = DATA_DIR / "engine_v2_task41_steps7_10.json"
SEED = 20260928
N_PERM = 10000
LIST_L = ["Kroos", "Modric", "Verratti", "Busquets", "De Bruyne", "Xhaka", "de Jong", "Kimmich", "Rodri", "Pedri",
          "Gundogan", "Grillitsch", "Shaparenko"]
MIN_PFF_MOMENTS = 300   # Task 38's deep-midfield moments floor
MIN_RQ_RECEPTIONS = 100
RQ_MIN_ELSEWHERE = 100


def perm_test(vals: pd.DataFrame, l_ids: set, rng) -> dict:
    """vals: sb_player_id, role, m. Within-role z; T = mean z of L present; relabel within roles."""
    v = vals.copy()
    v["z"] = v.groupby("role")["m"].transform(lambda s: (s - s.mean()) / s.std(ddof=1))
    v = v.dropna(subset=["z"])
    present = v[v["sb_player_id"].isin(l_ids)]
    if len(present) == 0:
        return {"n_present": 0}
    T = float(present["z"].mean())
    k_by_role = present["role"].value_counts().to_dict()
    pools = {r: v.loc[v["role"] == r, "z"].to_numpy() for r in k_by_role}
    tstar = np.empty(N_PERM)
    for i in range(N_PERM):
        tstar[i] = np.concatenate([rng.choice(pools[r], k, replace=False) for r, k in k_by_role.items()]).mean()
    p = (1 + int((np.abs(tstar) >= abs(T)).sum())) / (1 + N_PERM)
    return {"n_qualifying": len(v), "n_present": len(present), "T": T, "p_two_sided": p,
            "present": present[["sb_player_id", "role", "m", "z"]].to_dict("records"), "k_by_role": k_by_role}


def main():
    print("Task 41 Steps 7-10 ...")
    lb = pd.read_parquet(LEADERBOARD_V5C_PATH, columns=["player_id", "player_name", "is_deep_midfield"])
    roles = assign_roles(set(lb["player_id"])).set_index("player_id")["role"]
    l_ids, l_names = set(), {}
    for nm in LIST_L:
        hits = lb[lb["player_name"].apply(lambda full: name_matches(nm, full))]
        assert len(hits) == 1, (nm, hits["player_name"].tolist())
        l_ids.add(hits["player_id"].iloc[0])
        l_names[int(hits["player_id"].iloc[0])] = (nm, hits["player_name"].iloc[0])

    mom = pd.read_parquet(av.MOMENTS_PATH)
    rec = pd.read_parquet(av.RECEPTIONS_PATH)
    cw = pd.read_csv(PFF_OUT / "crosswalk.csv")
    pm = avt.player_map()
    pff2sb = pm.drop_duplicates("pff_player_id").set_index("pff_player_id")["sb_player_id"]

    # ---- Step 7 (2a) ----
    measures = {}
    dec = pd.read_parquet(CROSSFIT_V5_PATH, columns=["player_id", "decision"]).groupby("player_id")["decision"].mean()
    measures["v5_decision"] = dec[dec.index.isin(roles.index)]
    r34 = pd.read_parquet(REC34_PATH, columns=["player_id", "rq_rel"]).groupby("player_id")["rq_rel"].agg(["mean", "size"])
    measures["rq_rel"] = r34.loc[r34["size"] >= MIN_RQ_RECEPTIONS, "mean"]
    for col, name in (("av", "AV"), ("av_vis", "AV_vis")):
        a = mom.dropna(subset=[col]).groupby("pff_player_id")[col].agg(["mean", "size"])
        a = a[a["size"] >= MIN_PFF_MOMENTS]
        a.index = a.index.map(pff2sb)
        measures[name] = a["mean"][a.index.notna()]
    rng = np.random.default_rng(SEED)
    s7 = {"list_matched": {str(k): v for k, v in l_names.items()}}
    for name in ("AV", "AV_vis", "rq_rel", "v5_decision"):
        m = measures[name]
        vals = pd.DataFrame({"sb_player_id": m.index.astype(float), "m": m.values})
        vals["role"] = vals["sb_player_id"].map(roles)
        vals = vals.dropna(subset=["role"])
        res = perm_test(vals, l_ids, rng)
        res["present_names"] = [l_names[int(r["sb_player_id"])][1] for r in res.get("present", [])]
        s7[name] = res
        print(f"  Step 7 {name}: n_qual={res.get('n_qualifying')} present={res['n_present']} T={res.get('T')} p={res.get('p_two_sided')}")

    # ---- Step 8 (2c) ----
    gids = sorted(cw["pff_game_id"].astype(int))
    folds = av.match_folds(gids)
    dm_ids, _ = avt.dm_group(mom, pm, cw)
    oof = np.full(len(rec), np.nan)
    for k in range(av.N_FOLDS):
        tr, te = (rec["fold"] != k).values, (rec["fold"] == k).values
        mdl = xgb.XGBRegressor(**XGB_REGRESSOR_KWARGS).fit(rec.loc[tr, avt.G_FEATURES].astype(float), rec.loc[tr, "y_net_xg"])
        oof[te] = mdl.predict(rec.loc[te, avt.G_FEATURES].astype(float))
    rec["g_oof"] = oof
    t38 = json.loads((DATA_DIR / "pff_task38_tests.json").read_text())
    s8 = {}
    for space in (2, 3, 5):
        for lane in (1, 2, 3):
            key = f"space{space}_lane{lane}"
            mm = mom[["pff_game_id", "pff_player_id"] + av.FEATURES].copy()
            mm["available"] = ((mom["d_ball"].between(5, 40)) & (mom["space"] >= space) & (mom["lane"] >= lane)).astype(int)
            mm["p"], auc = av.fit_oof(mm, folds)
            mm["av_k"] = mm["available"] - mm["p"]
            r1 = avt.r1(mm, "av_k", dm_ids)
            r2 = avt.r2(rec, mm, "av_k", dm_ids)["PRIMARY_all_outfield"]
            s8[key] = {"base_rate": float(mm["available"].mean()), "baseline_auc": auc, "R1_DM": r1,
                       "R2_all_outfield": {k2: r2[k2] for k2 in ("n_rows", "n_players", "coef_per_sd", "coef_per_sd_per100",
                                                                  "ci95_per100", "p", "mde_80_per100")}}
            print(f"  Step 8 {key}: base={s8[key]['base_rate']:.3f} R1={r1['median']:.3f} "
                  f"R2 coef100={r2['coef_per_sd_per100']:+.4f} p={r2['p']:.4g}")
    ref = s8["space3_lane2"]
    assert np.isclose(ref["R2_all_outfield"]["coef_per_sd"], t38["r2"]["AV"]["PRIMARY_all_outfield"]["coef_per_sd"], rtol=1e-9)
    assert np.isclose(ref["R1_DM"]["median"], t38["r1"]["AV_DM"]["median"], rtol=1e-9)

    # ---- Step 9 (2d) ----
    rq = pd.read_parquet(REC34_PATH, columns=["match_id", "player_id", "rq_rel"])
    rq_pm = rq.groupby(["player_id", "match_id"])["rq_rel"].agg(["sum", "count"])
    rq_tot = rq_pm.groupby("player_id").sum()
    d = rec.merge(avt.loo_match_mean(mom, "av").rename(columns={"S_raw": "S_AV"}), on=["pff_player_id", "pff_game_id"], how="left")
    d["sb_player_id"] = d["pff_player_id"].map(pff2sb)
    d["sb_match_id"] = d["pff_game_id"].map(dict(zip(cw["pff_game_id"], cw["statsbomb_match_id"])))
    key = pd.MultiIndex.from_arrays([d["sb_player_id"], d["sb_match_id"]])
    own = rq_pm.reindex(key).fillna(0).to_numpy()
    tot = rq_tot.reindex(d["sb_player_id"]).fillna(0).to_numpy()
    s, n = (tot - own).T
    d["S_RQ"] = np.where(n >= RQ_MIN_ELSEWHERE, s / np.where(n > 0, n, 1), np.nan)
    d = d.rename(columns={"pff_player_id": "player_id", "pff_game_id": "match_id", "team_id": "team"})
    d["role"] = d["role"].fillna("NONE")
    d = d[d["role"] != "GK"]
    s9 = {"all_outfield": fit_multi(d, "y_net_xg", ["S_AV", "S_RQ"], "g_oof"),
          "DM": fit_multi(d[d["player_id"].isin(dm_ids)], "y_net_xg", ["S_AV", "S_RQ"], "g_oof")}
    for k, r in s9.items():
        print(f"  Step 9 {k}: n={r['n_rows']} players={r['n_players']} S_AV={r['S_AV']['coef_per_sd_per100']:+.4f} "
              f"(p={r['S_AV']['p']:.3g}) S_RQ={r['S_RQ']['coef_per_sd_per100']:+.4f} (p={r['S_RQ']['p']:.3g})")

    # ---- Step 10 (3b) ----
    t35 = json.loads((DATA_DIR / "engine_v2_task35_ptest.json").read_text())["step3_deep_midfield"]
    t37 = json.loads((DATA_DIR / "engine_v2_task37_holdout_ptest.json").read_text())["step3_deep_midfield"]
    t39 = json.loads((DATA_DIR / "engine_v2_task39_tempo_ptest.json").read_text())["step3_deep_midfield"]
    t41 = json.loads((DATA_DIR / "engine_v2_task41_steps1_6.json").read_text())
    fam = [("Task 35 Step 3 (a) v5 Decision", t35["a_decision_v5"]["p"]),
           ("Task 35 Step 3 (b) v6 Decision", t35["b_decision_v6"]["p"]),
           ("Task 35 Step 3 (c) v5 ev_chosen", t35["c_ev_chosen_v5"]["p"]),
           ("Task 35 Step 3 (d) reception RQ_rel", t35["d_reception_rq_rel"]["p"]),
           ("Task 37 Step 3 holdout v5 Decision", t37["primary"]["p"]),
           ("Task 38 R2 DM AV", t38["r2"]["AV"]["DM_report"]["p"]),
           ("Task 38 R2 DM AV_vis", t38["r2"]["AV_vis"]["DM_report"]["p"]),
           ("Task 39 Step 3 MOVE_ON_SPEED", t39["S_move"]["p"]),
           ("Task 39 Step 3 HOLD_VARIATION", t39["S_hold"]["p"]),
           ("Task 41 Step 2 DM row (v5 Decision)", t41["step2"]["DM"]["p"]),
           ("Task 41 Step 9 DM S_AV", s9["DM"]["S_AV"]["p"]),
           ("Task 41 Step 9 DM S_RQ", s9["DM"]["S_RQ"]["p"])]
    adj = multipletests([p for _, p in fam], method="holm")[1]
    s10 = [{"test": n, "p_raw": float(p), "p_holm": float(a)} for (n, p), a in zip(fam, adj)]
    for r in s10:
        print(f"  Step 10 {r['test']}: raw={r['p_raw']:.4g} holm={r['p_holm']:.4g}")

    SUMMARY_PATH.write_text(json.dumps({"step7": s7, "step8": s8, "step9": s9, "step10": s10,
                                        "n_dm_pff": len(dm_ids)}, indent=2, default=str))
    print(f"Wrote {SUMMARY_PATH}")


if __name__ == "__main__":
    main()
