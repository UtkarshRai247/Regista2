"""
Task 44, Steps 4-5: confirmatory tests on StatsBomb 2015/16 (untouched),
bars fixed in the brief. docs/specs/task-44-big-five-1516.md.

P-test = task35_ptest.fe_fit (Y ~ S + g + role FE + team-match FE, SE by
player); g = cross-fitted XGBoost regression (Task 35's settings) on the
event-only feature set (author's decision), 5 match folds seed 20260928.
PRIMARY within deep midfielders, Holm across the two:
  P1: MOVE_ON_SPEED -> net xG (passes; S from Task 39's s_for_rows, >= 100
      tempo passes elsewhere); completion control on the same rows.
  P2: PR2_flag_keep -> Y_F3 (pressured receptions; S >= 50 elsewhere);
      retention control (Task 43: row keep_spell; S = other-match
      keep_spell over ALL completed receptions, >= 100 elsewhere).
CONFIRMED iff Holm p < 0.05, coef > 0 and the control > 0 with p < 0.05.
Secondary combinations reported only. R1: Task 38's method (100 random
half-splits of a player's matches), players >= 10 matches (mean per half;
SD per half for HOLD_VARIATION). Praised list: Task 41's perm_test with
2015/16 roles, Holm across this task's praised-list tests. Step 5: Task
29's method for measures passing R1 within deep midfielders.

Run: python src/engine_v2/task44_tests.py   (after task44_build.py)
"""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import r2_score
from statsmodels.stats.multitest import multipletests

import task35_ptest as tp
from task33_step3_f_state import XGB_REGRESSOR_KWARGS
from task32_step5 import leave_one_match_out
from task39_tempo_ptest import s_for_rows
from task42_step2 import s_loo, dm_table
from task27_step1_deep_midfield import name_matches
from task41_lists_availability import perm_test, LIST_L
from task44_build import G_FEATURES, PASSES_PATH, RECEPTIONS_PATH, ROLES_PATH, MOVE_PATH, HOLD_PATH, N_FOLDS, SEED

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
SUMMARY_PATH = DATA_DIR / "engine_v2_task44_steps4_5.json"
F3_X = 80.0
R1_MIN_MATCHES, R1_SPLITS = 10, 100
MIN_TEMPO, MIN_PR = 100, 50


def crossfit_ev(df: pd.DataFrame, y: str) -> tuple:
    sub = df[df[y].notna()]
    oof = pd.Series(np.nan, index=df.index)
    for k in range(N_FOLDS):
        tr, te = sub[sub["fold"] != k], sub[sub["fold"] == k]
        m = xgb.XGBRegressor(**XGB_REGRESSOR_KWARGS).fit(tr[G_FEATURES].astype(float), tr[y].astype(float))
        oof.loc[te.index] = m.predict(te[G_FEATURES].astype(float))
    return oof, float(r2_score(sub[y], oof.loc[sub.index]))


def r1(df: pd.DataFrame, col: str, stat: str, pids=None) -> dict:
    d = df.dropna(subset=[col])
    if pids is not None:
        d = d[d["player_id"].isin(pids)]
    d = d.assign(x2=d[col] ** 2)
    pm = d.groupby(["player_id", "match_id"]).agg(s=(col, "sum"), q=("x2", "sum"), n=(col, "size")).reset_index()
    nm = pm.groupby("player_id").size()
    players = sorted(nm[nm >= R1_MIN_MATCHES].index)
    by = {p: g[["s", "q", "n"]].to_numpy() for p, g in pm[pm["player_id"].isin(players)].groupby("player_id")}
    rng = np.random.default_rng(SEED)

    def val(a):
        s, q, n = a[:, 0].sum(), a[:, 1].sum(), a[:, 2].sum()
        return s / n if stat == "mean" else np.sqrt(max((q - s ** 2 / n) / (n - 1), 0))
    sbs = []
    for _ in range(R1_SPLITS):
        h1, h2 = [], []
        for p in players:
            a = by[p]
            idx = rng.permutation(len(a))
            k = len(a) // 2
            h1.append(val(a[idx[:k]]))
            h2.append(val(a[idx[k:]]))
        r = np.corrcoef(h1, h2)[0, 1]
        sbs.append(2 * r / (1 + r))
    sbs = np.array(sbs)
    return {"n_players": len(players), "median": float(np.median(sbs)), "p5": float(np.percentile(sbs, 5)),
            "p95": float(np.percentile(sbs, 95)), "pass": bool(np.median(sbs) >= 0.60)}


def test(d: pd.DataFrame, y: str, g: str, ctrl: pd.DataFrame, cy: str, cg: str) -> dict:
    res = tp.fe_fit(d, y, g)
    ids = set(d.loc[d["S_raw"].notna() & d[y].notna() & d[g].notna(), "event_id"])
    res["control"] = tp.fe_fit(ctrl[ctrl["event_id"].isin(ids)], cy, cg)
    return res


def main():
    print("Task 44 Steps 4-5 ...")
    roles = pd.read_parquet(ROLES_PATH).set_index("player_id")
    dm_ids = set(roles.index[roles["is_dm"]])
    P = pd.read_parquet(PASSES_PATH)
    Rc = pd.read_parquet(RECEPTIONS_PATH)
    move, hold = pd.read_parquet(MOVE_PATH), pd.read_parquet(HOLD_PATH)
    step2 = json.loads((DATA_DIR / "engine_v2_task44_step2.json").read_text())
    gate = step2["gate_pass"]

    # ---- passes ----
    P["role"] = P["player_id"].map(roles["role"]).fillna("NONE")
    P["y_f3"] = np.where(P["ball_x"] < F3_X, P["y_f3"], np.nan)
    gr2 = {}
    for y, g in (("y_net_xg", "g_xg"), ("y_f3", "g_f3"), ("pass_complete", "g_cmp")):
        P[g], gr2[f"passes|{y}"] = crossfit_ev(P, y)
    pass_S = {"move_on_speed": s_for_rows(P, move, "mean"), "hold_variation": s_for_rows(P, hold, "sd")}
    pass_ctrl = tp.add_s(P, "pass_complete")

    # ---- pressured receptions ----
    R = Rc[Rc["pr2_flag_keep"].notna()].copy().reset_index(drop=True)
    R["role"] = R["player_id"].map(roles["role"]).fillna("NONE")
    R["y_f3"] = np.where(R["recv_x"] < F3_X, R["y_f3"], np.nan)
    for y, g in (("y_net_xg", "g_xg"), ("y_f3", "g_f3"), ("keep_spell", "g_keep")):
        R[g], gr2[f"pressured|{y}"] = crossfit_ev(R, y)
    allk = Rc.dropna(subset=["keep_spell", "player_id"])
    vals = leave_one_match_out(allk[["match_id", "player_id", "keep_spell"]].rename(columns={"keep_spell": "decision"}),
                               "player_id", 100)
    rec_ctrl = R.merge(vals[["match_id", "player_id", "complement_mean"]], on=["match_id", "player_id"], how="left") \
                .rename(columns={"complement_mean": "S_raw"})
    rec_S = {"pr2_flag_keep": s_loo(R, "pr2_flag_keep"), "pr2_flag_fwd": s_loo(R, "pr2_flag_fwd")}
    print(f"  passes {len(P)}, pressured receptions {len(R)}; g OOF R^2 {gr2}")

    tests = {}
    for grp, filt in (("dm", dm_ids), ("all", None)):
        for y in ("y_net_xg", "y_f3"):
            gcol = "g_xg" if y == "y_net_xg" else "g_f3"
            for name, d in pass_S.items():
                dd = d if filt is None else d[d["player_id"].isin(filt)]
                tests[f"{grp}|{name}|{y}"] = test(dd, y, gcol, pass_ctrl, "pass_complete", "g_cmp")
            if gate:
                for name, d in rec_S.items():
                    dd = d if filt is None else d[d["player_id"].isin(filt)]
                    tests[f"{grp}|{name}|{y}"] = test(dd, y, gcol, rec_ctrl, "keep_spell", "g_keep")
    for k, r in tests.items():
        c = r["control"]
        print(f"  {k}: n={r['n_rows']} players={r['n_players']} coef100={r['coef_per_sd_per100']:+.4f} "
              f"CI={[round(x, 4) for x in r['ci95_per100']]} p={r['p']:.4g} MDE={r['mde_80_per100']:.4f} | "
              f"control {c['coef_per_sd_per100']:+.3f} p={c['p']:.3g}")

    prim = ["dm|move_on_speed|y_net_xg"] + (["dm|pr2_flag_keep|y_f3"] if gate else [])
    holm = multipletests([tests[k]["p"] for k in prim], method="holm")[1] if len(prim) > 1 else [tests[prim[0]]["p"]]
    primary = []
    for k, h in zip(prim, holm):
        r, c = tests[k], tests[k]["control"]
        ok_c = c["coef_per_sd"] > 0 and c["p"] < 0.05
        primary.append({"test": k, "coef_per100": r["coef_per_sd_per100"], "ci95_per100": r["ci95_per100"], "p": r["p"],
                        "p_holm": float(h), "control_coef_per100": c["coef_per_sd_per100"], "control_p": c["p"],
                        "control_ok": bool(ok_c), "confirmed": bool(h < 0.05 and r["coef_per_sd"] > 0 and ok_c)})
        print(f"  PRIMARY {k}: p={r['p']:.4g} holm={h:.4g} control_ok={ok_c} -> CONFIRMED={primary[-1]['confirmed']}")

    # ---- R1 ----
    rel = {}
    for name, df, stat in (("move_on_speed", move, "mean"), ("hold_variation", hold, "sd"),
                           ("pr2_flag_keep", R, "mean"), ("pr2_flag_fwd", R, "mean")):
        col = "residual" if name in ("move_on_speed", "hold_variation") else name
        rel[name] = {"DM": r1(df, col, stat, dm_ids), "all": r1(df, col, stat)}
        print(f"  R1 {name}: DM {rel[name]['DM']}; all {rel[name]['all']}")

    # ---- praised list ----
    names = roles["player_name"].dropna()
    l_ids, l_report = set(), {}
    for nm in LIST_L:
        hits = names[names.apply(lambda full: name_matches(nm, full))]
        l_report[nm] = hits.tolist()
        if len(hits) == 1:
            l_ids.add(hits.index[0])
    rng = np.random.default_rng(SEED)
    measures = {"move_on_speed": move.groupby("player_id")["residual"].agg(["mean", "size"]),
                "hold_variation": hold.groupby("player_id")["residual"].agg(lambda s: s.std(ddof=1)).to_frame("mean")
                .join(hold.groupby("player_id").size().rename("size")),
                "pr2_flag_keep": R.groupby("player_id")["pr2_flag_keep"].agg(["mean", "size"]),
                "pr2_flag_fwd": R.groupby("player_id")["pr2_flag_fwd"].agg(["mean", "size"])}
    praised = {}
    for name, a in measures.items():
        floor = MIN_TEMPO if name in ("move_on_speed", "hold_variation") else MIN_PR
        a = a[a["size"] >= floor]
        v = pd.DataFrame({"sb_player_id": a.index.astype(float), "m": a["mean"].values})
        v["role"] = v["sb_player_id"].map(roles["role"])
        res = perm_test(v.dropna(subset=["role"]), l_ids, rng)
        res["present_names"] = [names.get(r["sb_player_id"]) for r in res.get("present", [])]
        praised[name] = res
    ptests = [k for k in praised if praised[k].get("n_present", 0) > 0]
    adj = multipletests([praised[k]["p_two_sided"] for k in ptests], method="holm")[1]
    for k, a in zip(ptests, adj):
        praised[k]["p_holm"] = float(a)
        print(f"  praised {k}: present={praised[k]['n_present']} T={praised[k]['T']:+.3f} p={praised[k]['p_two_sided']:.4g} holm={a:.4g}")

    # ---- Step 5 ----
    tables = {}
    for name in ("move_on_speed", "pr2_flag_keep", "pr2_flag_fwd"):
        if rel[name]["DM"]["pass"]:
            df = move.rename(columns={"residual": name}) if name == "move_on_speed" else R
            tables[name] = dm_table(df, name, dm_ids, names.to_dict())
    tables_note = "HOLD_VARIATION is a per-player SD; Task 29's per-unit-mean method does not apply to it." \
        if rel["hold_variation"]["DM"]["pass"] else None
    for k, t in tables.items():
        print(f"  table {k}: Q={t['dl']['Q']:.1f} p={t['dl']['p_value']:.3g} above={t['names_above']} below={t['names_below']}")

    SUMMARY_PATH.write_text(json.dumps({"gate_pass": gate, "g_oof_r2": gr2, "n_passes": len(P), "n_pressured": len(R),
                                        "n_dm": len(dm_ids), "tests": tests, "primary": primary, "r1": rel,
                                        "praised_list_matches": l_report, "praised": praised, "tables": tables,
                                        "tables_note": tables_note}, indent=2, default=str))
    print(f"Wrote {SUMMARY_PATH}")


if __name__ == "__main__":
    main()
