"""
Task 35, Steps 2-3: the pass-level out-of-match test (P-test).
docs/specs/task-35-power-and-pass-level-test.md.

Y  = net StatsBomb shot xG (passer's team minus opponent) over events
     i+1..i+10 after the pass/reception (events sorted by `index`).
S  = player's mean of the measure in his OTHER matches
     (task32_step5.leave_one_match_out), >= 100 rows elsewhere,
     standardised across the analysis rows.
g  = cross-fitted XGBoost regression of Y on origin features only:
     task33_step3_f_state's F_STATE_FEATURES, XGB_REGRESSOR_KWARGS,
     crossfit.FOLDS_PATH folds. For receptions the same 18 features are
     taken from value_model_rows_v5's Ball Receipt* rows plus the
     receipt event's under_pressure/period/minute.
Model: Y ~ S + g_oof + role FE + team-match FE, SE clustered by player.
     Team-match FE absorbed by within-transformation (Frisch-Waugh:
     identical point estimates to the dummy regression).

Run: python src/engine_v2/task35_ptest.py
"""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
import xgboost as xgb
from sklearn.metrics import r2_score
from statsmodels.stats.multitest import multipletests

from value_models import STATE_FEATURES
from value_models_v5 import OUT_PATH as VALUE_ROWS_PATH
from task33_step3_f_state import build_feature_table, F_STATE_FEATURES, XGB_REGRESSOR_KWARGS
from crossfit import FOLDS_PATH, N_FOLDS
from task32_step5 import leave_one_match_out
from task32_step4 import assign_roles

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
EVENTS_DIR = DATA_DIR / "raw" / "events"
EV_DIR = DATA_DIR / "processed" / "engine_v2" / "options_ev_v4"
CROSSFIT_V5_PATH = DATA_DIR / "processed" / "engine_v2" / "pass_der_crossfit_v5.parquet"
DECISION_V6_PATH = DATA_DIR / "processed" / "engine_v2" / "decision_v6.parquet"
REC_PATH = DATA_DIR / "processed" / "engine_v2" / "task34_receptions.parquet"
LEADERBOARD_V5C_PATH = DATA_DIR / "processed" / "leaderboard_v5c.parquet"
SUMMARY_PATH = DATA_DIR / "engine_v2_task35_ptest.json"

WINDOW = 10
MIN_ELSEWHERE = 100
MDE_FACTOR = 2.8


def net_xg_after(mid: int) -> pd.DataFrame:
    """Per event: net shot xG for the event's own team over events i+1..i+10."""
    ev = pd.read_parquet(EVENTS_DIR / f"{mid}.parquet", columns=["id", "index", "team", "type", "shot_statsbomb_xg"])
    ev = ev.sort_values("index").reset_index(drop=True)
    teams = ev["team"].dropna().unique().tolist()
    assert len(teams) == 2
    xg = np.where(ev["type"] == "Shot", ev["shot_statsbomb_xg"].fillna(0.0), 0.0)
    n = len(ev)
    out = np.zeros(n)
    for t in teams:
        signed = np.where(ev["team"] == t, xg, -xg)  # from team t's perspective
        cs = np.concatenate([[0.0], np.cumsum(signed)])
        i = np.arange(n)
        s = cs[np.minimum(i + 1 + WINDOW, n)] - cs[np.minimum(i + 1, n)]
        out = np.where(ev["team"] == t, s, out)
    return pd.DataFrame({"match_id": mid, "event_id": ev["id"], "y_net_xg": out})


def crossfit_g(df: pd.DataFrame, target: str, fold_of: dict) -> tuple:
    fold = df["match_id"].map(fold_of)
    assert fold.notna().all()
    oof = np.full(len(df), np.nan)
    for k in range(N_FOLDS):
        tr, te = (fold != k).values, (fold == k).values
        m = xgb.XGBRegressor(**XGB_REGRESSOR_KWARGS)
        m.fit(df.loc[tr, F_STATE_FEATURES].astype(float), df.loc[tr, target].astype(float))
        oof[te] = m.predict(df.loc[te, F_STATE_FEATURES].astype(float))
    return oof, float(r2_score(df[target].astype(float), oof))


def reception_features(rec: pd.DataFrame, match_ids: list) -> pd.DataFrame:
    vm = pd.read_parquet(VALUE_ROWS_PATH, columns=["match_id", "event_id", "type"] + STATE_FEATURES)
    vm = vm[(vm["type"] == "Ball Receipt*") & vm["match_id"].isin(match_ids)].drop(columns=["type"])
    extra = []
    for mid in match_ids:
        ev = pd.read_parquet(EVENTS_DIR / f"{mid}.parquet", columns=["id", "under_pressure"])
        extra.append(ev.rename(columns={"id": "event_id"}).assign(match_id=mid))
    extra = pd.concat(extra, ignore_index=True)
    out = rec.merge(vm, on=["match_id", "event_id"], how="inner").merge(extra, on=["match_id", "event_id"], how="left")
    out["under_pressure"] = out["under_pressure"].fillna(False).astype(float)
    return out


def add_s(df: pd.DataFrame, col: str) -> pd.DataFrame:
    pp = df[["match_id", "player_id", col]].rename(columns={col: "decision"})
    vals = leave_one_match_out(pp, "player_id", MIN_ELSEWHERE)
    out = df.merge(vals[["match_id", "player_id", "complement_mean", "complement_count"]],
                   on=["match_id", "player_id"], how="left")
    return out.rename(columns={"complement_mean": "S_raw"})


def fe_fit(df: pd.DataFrame, y: str, g: str) -> dict:
    """Y ~ S_z + g + role dummies + team-match FE (within), cluster by player."""
    d = df.dropna(subset=["S_raw", y, g]).copy()
    d["S_z"] = (d["S_raw"] - d["S_raw"].mean()) / d["S_raw"].std(ddof=1)
    d["tm"] = d["match_id"].astype(str) + "|" + d["team"].astype(str)
    roles = sorted(d["role"].unique())
    role_cols = [f"role_{r}" for r in roles[1:]]
    for r, c in zip(roles[1:], role_cols):
        d[c] = (d["role"] == r).astype(float)
    cols = [y, "S_z", g] + role_cols
    tm_size = d.groupby("tm")[y].transform("size")
    dm = d[cols].astype(float) - d.groupby("tm")[cols].transform("mean").astype(float)
    X = dm[["S_z", g] + role_cols]
    X = X.loc[:, X.abs().max() > 1e-12]  # drop role dummies with no within-team-match variation
    model = sm.OLS(dm[y], X).fit(cov_type="cluster", cov_kwds={"groups": d["player_id"].astype(int)})
    b, se = float(model.params["S_z"]), float(model.bse["S_z"])
    ci = model.conf_int().loc["S_z"].tolist()
    return {"n_rows": len(d), "n_players": int(d["player_id"].nunique()), "n_team_matches": int(d["tm"].nunique()),
            "n_rows_in_singleton_team_matches": int((tm_size == 1).sum()),
            "role_counts_rows": d["role"].value_counts().to_dict(),
            "coef_per_sd": b, "coef_per_sd_per100": 100 * b, "se": se, "ci95": [float(ci[0]), float(ci[1])],
            "ci95_per100": [100 * float(ci[0]), 100 * float(ci[1])], "p": float(model.pvalues["S_z"]),
            "mde_80": MDE_FACTOR * se, "mde_80_per100": 100 * MDE_FACTOR * se,
            "coef_g": float(model.params[g]), "y_mean": float(d[y].mean()), "S_raw_sd": float(d["S_raw"].std(ddof=1))}


def dummy_check(df: pd.DataFrame, y: str, g: str, n_tm: int = 40) -> dict:
    """Frisch-Waugh check on a subsample: within-estimate == full-dummy OLS estimate."""
    d = df.dropna(subset=["S_raw", y, g]).copy()
    keys = (d["match_id"].astype(str) + "|" + d["team"].astype(str))
    keep = sorted(keys.unique())[:n_tm]
    d = d[keys.isin(keep)]
    fe = fe_fit(d, y, g)
    d["S_z"] = (d["S_raw"] - d["S_raw"].mean()) / d["S_raw"].std(ddof=1)
    X = pd.concat([d[["S_z", g]].astype(float),
                   pd.get_dummies(d["role"], prefix="r", drop_first=True).astype(float),
                   pd.get_dummies(d["match_id"].astype(str) + "|" + d["team"].astype(str), drop_first=True).astype(float)],
                  axis=1)
    full = sm.OLS(d[y].astype(float), sm.add_constant(X)).fit()
    return {"within": fe["coef_per_sd"], "dummies": float(full.params["S_z"])}


def run_family(tests: dict, label: str) -> dict:
    names = [k for k in tests if k != "control"]
    ps = [tests[k]["p"] for k in names]
    adj = multipletests(ps, method="holm")[1]
    for k, a in zip(names, adj):
        tests[k]["p_holm"] = float(a)
    for k, r in tests.items():
        print(f"  [{label}] {k}: n={r['n_rows']} players={r['n_players']} coef/SD={r['coef_per_sd']:+.6f} "
              f"(x100 {r['coef_per_sd_per100']:+.4f}) CI100={[round(x, 4) for x in r['ci95_per100']]} "
              f"p={r['p']:.4g} p_holm={r.get('p_holm')} MDE100={r['mde_80_per100']:.4f}")
    return tests


def main():
    print("Task 35 Steps 2-3: P-test ...")
    folds = pd.read_csv(FOLDS_PATH)
    ev_mids = {int(p.stem) for p in EV_DIR.glob("*.parquet")}
    folds = folds[folds["match_id"].isin(ev_mids)]
    fold_of = dict(zip(folds["match_id"], folds["fold"]))
    match_ids = sorted(fold_of)
    assert len(match_ids) == 292

    y_all = pd.concat([net_xg_after(m) for m in match_ids], ignore_index=True)
    lb = pd.read_parquet(LEADERBOARD_V5C_PATH, columns=["player_id", "is_deep_midfield"])
    dm_ids = set(lb.loc[lb["is_deep_midfield"], "player_id"])
    roles = assign_roles(set(lb["player_id"])).set_index("player_id")["role"]

    # --- pass population: every chosen pass in options_ev_v4 with origin features (covers v5 and v6 passes) ---
    feat = build_feature_table(match_ids).merge(y_all, on=["match_id", "event_id"], how="left")
    assert feat["y_net_xg"].notna().all()
    feat["pass_complete"] = feat["pass_complete"].astype(float)
    feat["g_xg"], r2_g_xg = crossfit_g(feat, "y_net_xg", fold_of)
    feat["g_cmp"], r2_g_cmp = crossfit_g(feat, "pass_complete", fold_of)
    print(f"  pass feature table: {len(feat)} passes; g(net xG) OOF R^2={r2_g_xg:.4f}; g(completion) OOF R^2={r2_g_cmp:.4f}")
    keep_cols = ["match_id", "event_id", "y_net_xg", "pass_complete", "g_xg", "g_cmp"]

    v5 = pd.read_parquet(CROSSFIT_V5_PATH, columns=["match_id", "event_id", "team", "player_id", "decision", "ev_chosen"])
    v5 = v5.merge(feat[keep_cols], on=["match_id", "event_id"], how="inner")
    v6 = pd.read_parquet(DECISION_V6_PATH, columns=["match_id", "event_id", "team", "player_id", "decision_v6", "excluded"])
    v6 = v6[~v6["excluded"]].dropna(subset=["decision_v6"]).merge(feat[keep_cols], on=["match_id", "event_id"], how="inner")
    print(f"  v5 passes joined: {len(v5)}; v6 non-excluded passes joined: {len(v6)}")

    # --- receptions ---
    rec = pd.read_parquet(REC_PATH, columns=["match_id", "event_id", "team", "player_id", "period", "minute",
                                             "play_pattern_code", "rq_rel"])
    n_rec_task34 = len(rec)
    rec = reception_features(rec.drop(columns=["play_pattern_code"]), match_ids)
    rec = rec.merge(y_all, on=["match_id", "event_id"], how="left")
    rec["g_xg"], r2_g_rec = crossfit_g(rec, "y_net_xg", fold_of)
    print(f"  receptions: {n_rec_task34} in Task 34 table, {len(rec)} with value-model origin features; "
          f"g OOF R^2={r2_g_rec:.4f}")

    datasets = {
        "control": (add_s(v5, "pass_complete"), "pass_complete", "g_cmp"),
        "a_decision_v5": (add_s(v5, "decision"), "y_net_xg", "g_xg"),
        "b_decision_v6": (add_s(v6, "decision_v6"), "y_net_xg", "g_xg"),
        "c_ev_chosen_v5": (add_s(v5, "ev_chosen"), "y_net_xg", "g_xg"),
        "d_reception_rq_rel": (add_s(rec, "rq_rel"), "y_net_xg", "g_xg"),
    }
    for d, _, _ in datasets.values():
        d["role"] = d["player_id"].map(roles).fillna("NONE")
        assert (d.loc[d["S_raw"].notna(), "complement_count"] >= MIN_ELSEWHERE).all()

    fw = dummy_check(datasets["a_decision_v5"][0], "y_net_xg", "g_xg")
    print(f"  Frisch-Waugh check (40 team-matches): within={fw['within']:.8f}, dummies={fw['dummies']:.8f}")

    step2 = run_family({k: fe_fit(d, y, g) for k, (d, y, g) in datasets.items()}, "Step 2 all")
    step3 = run_family({k: fe_fit(d[d["player_id"].isin(dm_ids)], y, g) for k, (d, y, g) in datasets.items()},
                       "Step 3 DM")
    control_ok = step2["control"]["coef_per_sd"] > 0 and step2["control"]["p"] < 0.05
    print(f"  positive control (Step 2): {'POSITIVE' if control_ok else 'NOT POSITIVE -- (a)-(d) not interpreted'}")

    summary = {"n_matches": len(match_ids), "n_pass_feature_rows": len(feat), "n_v5_joined": len(v5),
               "n_v6_joined": len(v6), "n_receptions_task34": n_rec_task34, "n_receptions_with_features": len(rec),
               "g_oof_r2": {"pass_net_xg": r2_g_xg, "pass_completion": r2_g_cmp, "reception_net_xg": r2_g_rec},
               "y_net_xg_pass_mean": float(feat["y_net_xg"].mean()), "y_net_xg_pass_sd": float(feat["y_net_xg"].std()),
               "frisch_waugh_check": fw, "control_positive_step2": bool(control_ok),
               "step2": step2, "step3_deep_midfield": step3}
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
    print(f"Wrote {SUMMARY_PATH}")


if __name__ == "__main__":
    main()
