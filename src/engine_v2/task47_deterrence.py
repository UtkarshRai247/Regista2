"""
Task 47: do opponents learn to stop pressing a press-resistant player?
Exploratory, 2015/16 (a further use). docs/specs/task-47-pressure-deterrence.md.

PRESSURED = Task 44's flag rule (task44_receptions). Expected pressure
p(context): XGBoost classifier (Task 42's settings, Task 44's seeded 5
match folds) of PRESSURED on reception x, y, play pattern, minute, score
difference and the player's Task 32 role (NONE when he has none); no
identity. Unit value = PRESSURED - p.
Units: outfield player x match, >= 10 completed receptions in period 1 AND
in period 2; P_H = his mean unit value in half H; E1 = his mean
PR2_flag_keep over first-half pressured receptions (>= 5, else dropped).
Main model: (P_H2 - P_H1) ~ E1 + P_H1 + team-match FE + role FE, SE by
player (task41_ptest_vetting.fit_multi with an all-zero g column, which the
estimator drops after demeaning).

Run: python src/engine_v2/task47_deterrence.py
"""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import roc_auc_score

from task42_step2 import CLF_KWARGS
from task44_build import RECEPTIONS_PATH, ROLES_PATH, EV16, match_folds
from task41_ptest_vetting import fit_multi

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
SUMMARY_PATH = DATA_DIR / "engine_v2_task47.json"
FEATURES = ["recv_x", "recv_y", "play_pattern_code", "minute", "score_diff", "role_code"]
MIN_HALF, MIN_E1, MIN_PART, MIN_SEASON_MATCHES = 10, 5, 5, 10


def fisher(r, n):
    z, se = np.arctanh(r), 1 / np.sqrt(n - 3)
    return [float(np.tanh(z - 1.96 * se)), float(np.tanh(z + 1.96 * se))]


def main():
    print("Task 47: pressure deterrence (2015/16, further use) ...")
    Rc = pd.read_parquet(RECEPTIONS_PATH)
    roles = pd.read_parquet(ROLES_PATH).set_index("player_id")
    pos = pd.concat([pd.read_parquet(EV16 / f"{m}.parquet", columns=["id", "position"]).rename(columns={"id": "event_id"})
                     .assign(match_id=m) for m in sorted(Rc["match_id"].unique())], ignore_index=True)
    d = Rc.merge(pos, on=["match_id", "event_id"], how="left")
    n_all = len(d)
    d = d[(d["position"] != "Goalkeeper") & d["recv_x"].notna() & d["period"].isin([1, 2])].reset_index(drop=True)
    d["role"] = d["player_id"].map(roles["role"]).fillna("NONE")
    codes = {r: i for i, r in enumerate(sorted(d["role"].unique()))}
    d["role_code"] = d["role"].map(codes)
    folds = match_folds(sorted(d["match_id"].unique()))
    f = d["match_id"].map(folds).values
    oof = np.full(len(d), np.nan)
    for k in range(5):
        tr, te = f != k, f == k
        m = xgb.XGBClassifier(**CLF_KWARGS).fit(d.loc[tr, FEATURES].astype(float), d.loc[tr, "pressured_flag"].astype(int))
        oof[te] = m.predict_proba(d.loc[te, FEATURES].astype(float))[:, 1]
    d["v"] = d["pressured_flag"].astype(float) - oof
    base = {"n_receptions_all": n_all, "n_receptions_outfield_p12": len(d),
            "pressured_rate": float(d["pressured_flag"].mean()), "baseline_auc": float(roc_auc_score(d["pressured_flag"].astype(int), oof))}
    print(f"  {base}")

    key = ["match_id", "team", "player_id"]
    h = d.groupby(key + ["period"])["v"].agg(["sum", "count"]).unstack("period")
    h.columns = [f"{a}_{b}" for a, b in h.columns]
    h = h.fillna(0).reset_index()
    e1 = d[(d["period"] == 1) & d["pr2_flag_keep"].notna()].groupby(key)["pr2_flag_keep"].agg(E1="mean", n_e1="size").reset_index()
    u = h.merge(e1, on=key, how="left")
    u = u[(u["count_1"] >= MIN_HALF) & (u["count_2"] >= MIN_HALF)].copy()
    n_before_e1 = len(u)
    u = u[u["n_e1"].fillna(0) >= MIN_E1].copy()
    u["P_H1"], u["P_H2"] = u["sum_1"] / u["count_1"], u["sum_2"] / u["count_2"]
    u["dP"] = u["P_H2"] - u["P_H1"]
    u["role"] = u["player_id"].map(roles["role"]).fillna("NONE")
    u["g0"] = 0.0
    # teammates' change (placebo): all his team's outfield receptions in that match, excluding his own
    t = d.groupby(["match_id", "team", "period"])["v"].agg(["sum", "count"]).unstack("period")
    t.columns = [f"t{a}_{b}" for a, b in t.columns]
    u = u.merge(t.reset_index(), on=["match_id", "team"], how="left")
    u["dP_mates"] = (u["tsum_2"] - u["sum_2"]) / (u["tcount_2"] - u["count_2"]) - (u["tsum_1"] - u["sum_1"]) / (u["tcount_1"] - u["count_1"])
    # second-half parts
    h2 = d[d["period"] == 2].assign(part=lambda x: np.where(x["minute"] <= 67, "early", "late"))
    parts = h2.groupby(key + ["part"])["v"].agg(["mean", "size"]).unstack("part")
    parts.columns = [f"{a}_{b}" for a, b in parts.columns]
    u = u.merge(parts.reset_index(), on=key, how="left")
    units = {"n_units_min_receptions": n_before_e1, "n_units": len(u), "n_players": int(u["player_id"].nunique()),
             "n_team_matches": int(u.groupby(["match_id", "team"]).ngroups), "mean_P_H1": float(u["P_H1"].mean()),
             "mean_P_H2": float(u["P_H2"].mean()), "mean_E1": float(u["E1"].mean()), "mean_n_e1": float(u["n_e1"].mean())}
    print(f"  units {units}")

    def fit(df, y):
        r = fit_multi(df.dropna(subset=[y]), y, ["E1", "P_H1"], "g0")
        return {"n": r["n_rows"], "players": r["n_players"], "team_matches": r["n_team_matches"], "E1": r["E1"], "P_H1": r["P_H1"]}
    res = {"main": fit(u, "dP"), "placebo_teammates": fit(u, "dP_mates")}
    for part in ("early", "late"):
        uu = u[u[f"size_{part}"].fillna(0) >= MIN_PART].copy()
        uu["dP_part"] = uu[f"mean_{part}"] - uu["P_H1"]
        res[f"h2_{part}"] = fit(uu, "dP_part")
    dm = set(roles.index[roles["is_dm"]])
    res["dm_main"] = fit(u[u["player_id"].isin(dm)], "dP")
    res["dm_placebo"] = fit(u[u["player_id"].isin(dm)], "dP_mates")
    for k, r in res.items():
        e = r["E1"]
        print(f"  {k}: n={r['n']} players={r['players']} E1 coef/SD={e['coef_per_sd']:+.5f} CI={[round(x, 5) for x in e['ci95']]} p={e['p']:.4g}")

    seas = d.groupby("player_id").agg(P=("v", "mean"), n_matches=("match_id", "nunique"))
    pr = d.dropna(subset=["pr2_flag_keep"]).groupby("player_id")["pr2_flag_keep"].mean().rename("PR")
    seas = seas.join(pr, how="inner")
    seas = seas[seas["n_matches"] >= MIN_SEASON_MATCHES]
    seas["role"] = seas.index.map(roles["role"])
    seas = seas.dropna(subset=["role"])
    season = {}
    for role, g in seas.groupby("role"):
        if len(g) >= 4:
            r = float(g["PR"].corr(g["P"]))
            season[role] = {"n": len(g), "r": r, "ci95": fisher(r, len(g))}
    dem = seas[["PR", "P"]] - seas.groupby("role")[["PR", "P"]].transform("mean")
    r = float(dem["PR"].corr(dem["P"]))
    season["pooled_within_role"] = {"n": len(dem), "r": r, "ci95": fisher(r, len(dem))}
    print(f"  season: {season}")

    m, pl = res["main"]["E1"], res["placebo_teammates"]["E1"]
    claim = {"main_negative_p05": bool(m["coef_per_sd"] < 0 and m["p"] < 0.05),
             "placebo_negative_p05": bool(pl["coef_per_sd"] < 0 and pl["p"] < 0.05)}
    claim["propose_for_confirmation"] = bool(claim["main_negative_p05"] and not claim["placebo_negative_p05"])
    SUMMARY_PATH.write_text(json.dumps({"base": base, "role_codes": codes, "units": units, "results": res,
                                        "season": season, "claim": claim}, indent=2, default=str))
    print(f"  claim {claim}; wrote {SUMMARY_PATH}")


if __name__ == "__main__":
    main()
