"""
Task 41, Steps 1-6: vetting the pass-level test (P-test) on the study
sample. docs/specs/task-41-vetting-round-2.md. Measurement only.

Task 35's inputs are regenerated with its own functions and its v5
Decision coefficient/SE asserted to reproduce (as Tasks 39/40 did).
fit_multi() is task35_ptest.fe_fit's estimator generalised to several
standardised covariates and any fixed-effect label column; it is asserted
equal to fe_fit on the base model.

Run: python src/engine_v2/task41_ptest_vetting.py
"""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.stats.multitest import multipletests

import task33_step3_f_state as tfs
import task35_ptest as tp
from task32_step4 import assign_roles
from task32_step5 import leave_one_match_out
from crossfit import FOLDS_PATH

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
EVENTS_DIR = DATA_DIR / "raw" / "events"
LEADERBOARD_V5C_PATH = DATA_DIR / "processed" / "leaderboard_v5c.parquet"
TASK35_PATH = DATA_DIR / "engine_v2_task35_ptest.json"
TASK37_PATH = DATA_DIR / "engine_v2_task37_holdout_ptest.json"
SUMMARY_PATH = DATA_DIR / "engine_v2_task41_steps1_6.json"
SEED = 20260928
N_BOOT = 1000
ROLES = ["CB", "FB", "DM", "CM", "AM/W", "FW"]


def loo(df: pd.DataFrame, col: str) -> pd.Series:
    """Passer's mean of `col` over his OTHER matches, >= 100 eligible passes elsewhere (Task 35's rule)."""
    vals = leave_one_match_out(df[["match_id", "player_id", col]].rename(columns={col: "decision"}),
                               "player_id", tp.MIN_ELSEWHERE)
    return df[["match_id", "player_id"]].merge(vals, on=["match_id", "player_id"], how="left")["complement_mean"].values


def fit_multi(df: pd.DataFrame, y: str, xcols: list, g: str, fe_col: str = "role", two_way: bool = False) -> dict:
    d = df.dropna(subset=xcols + [y, g]).copy()
    zcols = []
    for c in xcols:
        d[f"z_{c}"] = (d[c] - d[c].mean()) / d[c].std(ddof=1)
        zcols.append(f"z_{c}")
    d["tm"] = d["match_id"].astype(str) + "|" + d["team"].astype(str)
    levels = sorted(d[fe_col].unique())
    fe_cols = [f"fe_{i}" for i in range(1, len(levels))]
    for lv, c in zip(levels[1:], fe_cols):
        d[c] = (d[fe_col] == lv).astype(float)
    cols = [y] + zcols + [g] + fe_cols
    dm = d[cols].astype(float) - d.groupby("tm")[cols].transform("mean").astype(float)
    X = dm[zcols + [g] + fe_cols]
    X = X.loc[:, X.abs().max() > 1e-12]
    if two_way:
        groups = np.column_stack([pd.factorize(d["player_id"])[0], pd.factorize(d["match_id"])[0]])
    else:
        groups = d["player_id"].astype(int)
    m = sm.OLS(dm[y], X).fit(cov_type="cluster", cov_kwds={"groups": groups})
    out = {"n_rows": len(d), "n_players": int(d["player_id"].nunique()), "n_team_matches": int(d["tm"].nunique())}
    for c, z in zip(xcols, zcols):
        ci = m.conf_int().loc[z].tolist()
        out[c] = {"coef_per_sd": float(m.params[z]), "coef_per_sd_per100": 100 * float(m.params[z]),
                  "se": float(m.bse[z]), "ci95": [float(ci[0]), float(ci[1])],
                  "ci95_per100": [100 * float(ci[0]), 100 * float(ci[1])], "p": float(m.pvalues[z]),
                  "mde_80_per100": 100 * tp.MDE_FACTOR * float(m.bse[z])}
    return out


def net_xg(mid: int, window: int, exclude_self: bool) -> pd.DataFrame:
    """Task 35's Y (net shot xG over events i+1..i+window, the event's own team perspective); optionally
    excluding shots taken by the event's own player."""
    ev = pd.read_parquet(EVENTS_DIR / f"{mid}.parquet", columns=["id", "index", "team", "type", "shot_statsbomb_xg", "player_id"])
    ev = ev.sort_values("index").reset_index(drop=True)
    n = len(ev)
    team = ev["team"].values
    xg = np.where(ev["type"] == "Shot", ev["shot_statsbomb_xg"].fillna(0.0), 0.0)
    out = np.zeros(n)
    for i in range(n):
        lo, hi = i + 1, min(i + 1 + window, n)
        if lo >= hi:
            continue
        seg = slice(lo, hi)
        s = np.where(team[seg] == team[i], xg[seg], -xg[seg])
        if exclude_self:
            s = np.where(ev["player_id"].values[seg] == ev["player_id"].values[i], 0.0, s)
        out[i] = s.sum()
    return pd.DataFrame({"match_id": mid, "event_id": ev["id"], "y": out})


def main():
    print("Task 41 Steps 1-6 ...")
    folds = pd.read_csv(FOLDS_PATH)
    ev_mids = {int(p.stem) for p in tp.EV_DIR.glob("*.parquet")}
    folds = folds[folds["match_id"].isin(ev_mids)]
    fold_of = dict(zip(folds["match_id"], folds["fold"]))
    mids = sorted(fold_of)
    y_all = pd.concat([tp.net_xg_after(m) for m in mids], ignore_index=True)
    feat = tfs.build_feature_table(mids).merge(y_all, on=["match_id", "event_id"], how="left")
    feat["g_xg"], _ = tp.crossfit_g(feat, "y_net_xg", fold_of)
    v5 = pd.read_parquet(tp.CROSSFIT_V5_PATH, columns=["match_id", "event_id", "team", "player_id", "decision", "ev_chosen"])
    v5 = v5.merge(feat[["match_id", "event_id", "y_net_xg", "g_xg", "ball_x", "ball_y"]], on=["match_id", "event_id"], how="inner")
    lb = pd.read_parquet(LEADERBOARD_V5C_PATH, columns=["player_id", "is_deep_midfield"])
    v5["role"] = v5["player_id"].map(assign_roles(set(lb["player_id"])).set_index("player_id")["role"]).fillna("NONE")
    pos = pd.concat([pd.read_parquet(EVENTS_DIR / f"{m}.parquet", columns=["id", "position"]).rename(columns={"id": "event_id"})
                     .assign(match_id=m) for m in mids], ignore_index=True)
    v5 = v5.merge(pos, on=["match_id", "event_id"], how="left")
    v5["position"] = v5["position"].fillna("UNKNOWN")

    for c, src in (("S_raw", "decision"), ("S_x", "ball_x"), ("S_y", "ball_y"), ("S_ev", "ev_chosen")):
        v5[c] = loo(v5, src)
    t35 = json.loads(TASK35_PATH.read_text())
    base_fe = tp.fe_fit(v5, "y_net_xg", "g_xg")
    base = fit_multi(v5, "y_net_xg", ["S_raw"], "g_xg")
    assert np.isclose(base_fe["coef_per_sd"], t35["step2"]["a_decision_v5"]["coef_per_sd"], rtol=1e-9, atol=0)
    assert np.isclose(base_fe["se"], t35["step2"]["a_decision_v5"]["se"], rtol=1e-9, atol=0)
    assert np.isclose(base["S_raw"]["coef_per_sd"], base_fe["coef_per_sd"], rtol=1e-9, atol=0)
    assert np.isclose(base["S_raw"]["se"], base_fe["se"], rtol=1e-9, atol=0)
    print(f"  base reproduced: coef={base_fe['coef_per_sd']!r} se={base_fe['se']!r}")

    # Step 1 (1a): where he usually plays
    s1 = {"base": base}
    s1["A_Sx_Sy"] = fit_multi(v5, "y_net_xg", ["S_raw", "S_x", "S_y"], "g_xg")
    s1["B_Sev"] = fit_multi(v5, "y_net_xg", ["S_raw", "S_ev"], "g_xg")
    s1["C_Sx_Sy_Sev"] = fit_multi(v5, "y_net_xg", ["S_raw", "S_x", "S_y", "S_ev"], "g_xg")
    s1["D_position_FE"] = fit_multi(v5, "y_net_xg", ["S_raw", "S_x", "S_y", "S_ev"], "g_xg", fe_col="position")
    s1["n_position_labels"] = int(v5["position"].nunique())
    for k in ("base", "A_Sx_Sy", "B_Sev", "C_Sx_Sy_Sev", "D_position_FE"):
        r = s1[k]["S_raw"]
        print(f"  Step 1 {k}: n={s1[k]['n_rows']} coef100={r['coef_per_sd_per100']:+.4f} CI={r['ci95_per100']} p={r['p']:.4g}")

    # Step 2 (1b): which roles carry it
    s2 = {}
    for role in ROLES:
        s2[role] = tp.fe_fit(v5[v5["role"] == role], "y_net_xg", "g_xg")
    adj = multipletests([s2[r]["p"] for r in ROLES], method="holm")[1]
    for r, a in zip(ROLES, adj):
        s2[r]["p_holm_info"] = float(a)
        print(f"  Step 2 {r}: players={s2[r]['n_players']} coef100={s2[r]['coef_per_sd_per100']:+.4f} p={s2[r]['p']:.4g}")

    # Step 3 (1c): outcome definition
    ref = pd.concat([net_xg(m, 10, False) for m in mids], ignore_index=True)
    chk = y_all.merge(ref, on=["match_id", "event_id"])
    assert np.allclose(chk["y_net_xg"], chk["y"], atol=1e-12)
    s3 = {}
    for label, window, excl in (("a_exclude_own_shots", 10, True), ("b_horizon_5", 5, False), ("c_horizon_15", 15, False)):
        yv = pd.concat([net_xg(m, window, excl) for m in mids], ignore_index=True).rename(columns={"y": "y_var"})
        f2 = feat[["match_id", "event_id"] + tfs.F_STATE_FEATURES].merge(yv, on=["match_id", "event_id"], how="left")
        f2["g_var"], r2 = tp.crossfit_g(f2, "y_var", fold_of)
        d = v5.merge(f2[["match_id", "event_id", "y_var", "g_var"]], on=["match_id", "event_id"], how="left")
        s3[label] = {**tp.fe_fit(d, "y_var", "g_var"), "g_oof_r2": r2}
        r = s3[label]
        print(f"  Step 3 {label}: coef100={r['coef_per_sd_per100']:+.4f} CI={r['ci95_per100']} p={r['p']:.4g}")

    # Step 4 (1d): inference
    two = fit_multi(v5, "y_net_xg", ["S_raw"], "g_xg", two_way=True)["S_raw"]
    d = v5.dropna(subset=["S_raw", "y_net_xg", "g_xg"]).copy()
    d["S_z"] = (d["S_raw"] - d["S_raw"].mean()) / d["S_raw"].std(ddof=1)
    roles_present = sorted(d["role"].unique())
    for r in roles_present[1:]:
        d[f"r_{r}"] = (d["role"] == r).astype(float)
    xcols = ["S_z", "g_xg"] + [f"r_{r}" for r in roles_present[1:]]
    d["tm"] = pd.factorize(d["match_id"].astype(str) + "|" + d["team"].astype(str))[0]
    arr_y, arr_x, tm = d["y_net_xg"].to_numpy(float), d[xcols].to_numpy(float), d["tm"].to_numpy()
    rows_of = list(pd.Series(np.arange(len(d))).groupby(d["player_id"].to_numpy()).apply(np.asarray))
    rng = np.random.default_rng(SEED)
    boot = np.empty(N_BOOT)
    for b in range(N_BOOT):
        pick = rng.integers(0, len(rows_of), len(rows_of))
        idx = np.concatenate([rows_of[p] for p in pick])
        yy, xx, gg = arr_y[idx], arr_x[idx], tm[idx]
        _, inv = np.unique(gg, return_inverse=True)
        cnt = np.bincount(inv)
        ym = yy - np.bincount(inv, yy)[inv] / cnt[inv]
        xm = xx - np.stack([np.bincount(inv, xx[:, j]) for j in range(xx.shape[1])], 1)[inv] / cnt[inv][:, None]
        keep = np.abs(xm).max(0) > 1e-12
        boot[b] = np.linalg.lstsq(xm[:, keep], ym, rcond=None)[0][0]
    s4 = {"two_way_cluster": two, "bootstrap": {"n": N_BOOT, "seed": SEED, "mean": float(boot.mean()),
          "ci95_percentile": [float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))],
          "ci95_percentile_per100": [100 * float(np.percentile(boot, 2.5)), 100 * float(np.percentile(boot, 97.5))],
          "share_le_0": float((boot <= 0).mean())},
          "one_way_base": base["S_raw"]}
    print(f"  Step 4: two-way se={two['se']:.6g} p={two['p']:.4g}; bootstrap CI100={s4['bootstrap']['ci95_percentile_per100']}")

    # Step 5 (1e): size in football terms
    coef = base["S_raw"]["coef_per_sd"]
    per_pm = v5.groupby(["player_id", "match_id", "role"]).size().rename("n").reset_index()
    s5 = {"coef_per_pass_per_sd": coef, "S_raw_sd_base": base_fe["S_raw_sd"]}
    for role in ("DM", "CM", "AM/W", "FW"):
        med = float(per_pm.loc[per_pm["role"] == role, "n"].median())
        s5[role] = {"median_eligible_passes_per_match": med, "xg_per_match": coef * med, "xg_per_38": coef * med * 38,
                    "n_player_matches": int((per_pm["role"] == role).sum())}
        print(f"  Step 5 {role}: median passes/match={med} -> xG/match={coef * med:.4f}, per 38={coef * med * 38:.3f}")

    # Step 6 (1f): what the DM tests rule out
    t37 = json.loads(TASK37_PATH.read_text())
    s6 = {"study": {"dm_upper95": t35["step3_deep_midfield"]["a_decision_v5"]["ci95"][1],
                    "all_coef": t35["step2"]["a_decision_v5"]["coef_per_sd"]},
          "holdout": {"dm_upper95": t37["step3_deep_midfield"]["primary"]["ci95"][1],
                      "all_coef": t37["primary_decision_v5"]["coef_per_sd"]}}
    for k in s6:
        s6[k]["fraction"] = s6[k]["dm_upper95"] / s6[k]["all_coef"]
    print(f"  Step 6: {s6}")

    SUMMARY_PATH.write_text(json.dumps({"step1": s1, "step2": s2, "step3": s3, "step4": s4, "step5": s5, "step6": s6},
                                       indent=2, default=str))
    print(f"Wrote {SUMMARY_PATH}")


if __name__ == "__main__":
    main()
