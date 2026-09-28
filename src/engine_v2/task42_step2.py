"""
Task 42, Step 2 (B): press resistance from StatsBomb 360 (study sample,
all 292 matches). docs/specs/task-42-improvement-round-2.md.

Unit: completed Ball Receipt* with a 360 frame and an actor (the receiver).
PRESSURED: nearest visible opponent <= 3 units (recomputed from the frame,
uncapped) OR the receipt's under_pressure flag. Next action, keep and fwd
from task42_outcomes (receipts with no next action are excluded, counted).
Baseline: cross-fitted XGBoost classifier on Task 35's folds from context
only; PR = outcome - p_oof. R1 via step8_regate.reliability_sweep; R2 via
task35_ptest.fe_fit (S = other-match mean PR, >= 50 pressured receptions
elsewhere; retention control per the brief's correction 4d6405a: S = raw
retention over ALL the receiver's completed receptions in other matches,
>= 100 elsewhere); R3 via Task 41's
perm_test; table via Task 29's method.

Run: python src/engine_v2/task42_step2.py   (after task42_step1.py)
"""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import roc_auc_score

import task35_ptest as tp
from value_models import PATTERN_CODE
from validation_common import match_competition_lookup
from crossfit import FOLDS_PATH, N_FOLDS
from step8_regate import reliability_sweep
from task32_step4 import assign_roles
from task32_step5 import leave_one_match_out
from task28_step1_2 import estimate_sigma2w_rho
from task29_step1_2 import dersimonian_laird, shrink
from task27_step1_deep_midfield import name_matches
from task41_lists_availability import perm_test, LIST_L
from task42_step1 import retention_s

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
EVENTS_DIR = DATA_DIR / "raw" / "events"
FRAMES_DIR = DATA_DIR / "raw" / "frames"
LEADERBOARD_V5C_PATH = DATA_DIR / "processed" / "leaderboard_v5c.parquet"
OUTCOMES_PATH = DATA_DIR / "processed" / "engine_v2" / "task42_event_outcomes.parquet"
RECEIPT_ACTIONS_PATH = DATA_DIR / "processed" / "engine_v2" / "task42_receipt_actions.parquet"
OUT_PATH = DATA_DIR / "processed" / "engine_v2" / "task42_pressured_receptions.parquet"
SUMMARY_PATH = DATA_DIR / "engine_v2_task42_step2.json"

SEED = 20260928
PRESS_DIST = 3.0
NEAR_R = 5.0
MIN_ELSEWHERE = 50
F3_X = 80.0
CLF_KWARGS = dict(objective="binary:logistic", n_estimators=300, max_depth=6, learning_rate=0.05,
                  subsample=0.8, random_state=SEED)
BASE_FEATURES = ["recv_x", "recv_y", "nearest_opp", "opp_within_5", "play_pattern_code", "period", "minute"]


def match_receipts(mid: int) -> pd.DataFrame:
    ev = pd.read_parquet(EVENTS_DIR / f"{mid}.parquet",
                         columns=["id", "type", "ball_receipt_outcome", "player_id", "team", "period", "minute",
                                  "play_pattern", "under_pressure"])
    rec = ev[(ev["type"] == "Ball Receipt*") & ev["ball_receipt_outcome"].isna()]
    fr = pd.read_parquet(FRAMES_DIR / f"{mid}.parquet", columns=["id", "teammate", "actor", "location"])
    fr = fr[fr["id"].isin(set(rec["id"]))]
    xy = np.array(fr["location"].tolist(), dtype=float).reshape(-1, 2)
    fr = fr.assign(x=xy[:, 0], y=xy[:, 1])
    actor = fr[fr["actor"]].drop_duplicates("id").set_index("id")[["x", "y"]]
    opp = fr[~fr["teammate"]].join(actor, on="id", rsuffix="_a", how="inner")
    opp["d"] = np.hypot(opp["x"] - opp["x_a"], opp["y"] - opp["y_a"])
    agg = opp.groupby("id")["d"].agg(nearest_opp="min", opp_within_5=lambda s: int((s <= NEAR_R).sum()))
    rec = rec[rec["id"].isin(actor.index)].copy()
    rec["recv_x"], rec["recv_y"] = rec["id"].map(actor["x"]), rec["id"].map(actor["y"])
    rec["nearest_opp"] = rec["id"].map(agg["nearest_opp"])
    rec["opp_within_5"] = rec["id"].map(agg["opp_within_5"]).fillna(0)
    rec["play_pattern_code"] = rec["play_pattern"].map(lambda p: PATTERN_CODE.get(p, PATTERN_CODE["Other"]))
    rec["under_pressure_flag"] = rec["under_pressure"].fillna(False).astype(bool)
    rec["match_id"] = mid
    return rec.rename(columns={"id": "event_id"}).drop(columns=["type", "ball_receipt_outcome", "play_pattern", "under_pressure"])


def s_loo(df: pd.DataFrame, col: str) -> pd.DataFrame:
    vals = leave_one_match_out(df[["match_id", "player_id", col]].rename(columns={col: "decision"}), "player_id", MIN_ELSEWHERE)
    out = df.merge(vals[["match_id", "player_id", "complement_mean"]], on=["match_id", "player_id"], how="left")
    return out.rename(columns={"complement_mean": "S_raw"})


def dm_table(df: pd.DataFrame, col: str, dm_ids: set, names: dict) -> dict:
    pp = df[df["player_id"].isin(dm_ids)][["player_id", "match_id", col]].rename(columns={col: "decision_new"})
    s2, rho, _ = estimate_sigma2w_rho(pp)
    g = pp.groupby("player_id")
    st = pd.DataFrame({"m_i": g["decision_new"].mean(), "n_i": g.size(), "G_i": g["match_id"].nunique()}).reset_index()
    st["v_i"] = s2 * (1 + (st["n_i"] / st["G_i"] - 1) * rho) / st["n_i"]
    dl = dersimonian_laird(st["m_i"].values, st["v_i"].values)
    t = shrink(st, dl["mu_w"], dl["tau2"], "m_i", "v_i").sort_values("shrunken_i", ascending=False).reset_index(drop=True)
    t["rank"] = t.index + 1
    t["name"] = t["player_id"].map(names)
    above, below = t[t["ci_low_90"] > dl["mu_w"]], t[t["ci_high_90"] < dl["mu_w"]]
    return {"sigma2_w": s2, "rho": rho, "dl": dl, "n_players": len(t), "names_above": above["name"].tolist(),
            "names_below": below["name"].tolist(),
            "rows": t[["rank", "player_id", "name", "G_i", "n_i", "m_i", "shrunken_i", "ci_low_90", "ci_high_90"]].to_dict("records")}


def main():
    print("Task 42 Step 2 ...")
    folds = pd.read_csv(FOLDS_PATH)
    ev_mids = {int(p.stem) for p in tp.EV_DIR.glob("*.parquet")}
    folds = folds[folds["match_id"].isin(ev_mids)]
    fold_of = dict(zip(folds["match_id"], folds["fold"]))
    mids = sorted(fold_of)

    rec = pd.concat([match_receipts(m) for m in mids], ignore_index=True)
    n_receipts = len(rec)
    rec = rec.merge(pd.read_parquet(RECEIPT_ACTIONS_PATH)[["match_id", "event_id", "keep", "fwd"]],
                    on=["match_id", "event_id"], how="left")
    rec["pressured"] = (rec["nearest_opp"] <= PRESS_DIST) | rec["under_pressure_flag"]
    pr = rec[rec["pressured"]].copy()
    n_pressured = len(pr)
    n_no_action = int(pr["keep"].isna().sum())
    pr = pr[pr["keep"].notna()].reset_index(drop=True)
    comp = match_competition_lookup()
    pr["competition_id"] = pr["match_id"].map(lambda m: comp[m][0])
    pr["season_id"] = pr["match_id"].map(lambda m: comp[m][1])
    pr["fold"] = pr["match_id"].map(fold_of)

    base = {}
    for oc in ("keep", "fwd"):
        oof = np.full(len(pr), np.nan)
        for k in range(N_FOLDS):
            tr, te = (pr["fold"] != k).values, (pr["fold"] == k).values
            m = xgb.XGBClassifier(**CLF_KWARGS).fit(pr.loc[tr, BASE_FEATURES].astype(float), pr.loc[tr, oc].astype(int))
            oof[te] = m.predict_proba(pr.loc[te, BASE_FEATURES].astype(float))[:, 1]
        pr[f"p_{oc}"] = oof
        pr[f"pr_{oc}"] = pr[oc] - oof
        base[oc] = {"base_rate": float(pr[oc].mean()), "auc": float(roc_auc_score(pr[oc].astype(int), oof))}
    print(f"  receipts with frame+actor: {n_receipts}; pressured: {n_pressured}; no next action: {n_no_action}; "
          f"analysed: {len(pr)}; {base}")

    lb = pd.read_parquet(LEADERBOARD_V5C_PATH, columns=["player_id", "player_name", "is_deep_midfield"])
    roles = assign_roles(set(lb["player_id"])).set_index("player_id")["role"]
    dm_ids = set(lb.loc[lb["is_deep_midfield"], "player_id"])
    names = lb.set_index("player_id")["player_name"].to_dict()
    pr["role"] = pr["player_id"].map(roles).fillna("NONE")

    # R1
    r1 = {oc: reliability_sweep(pr[pr["player_id"].isin(dm_ids)], f"pr_{oc}", [50, 100, 150]) for oc in ("keep", "fwd")}
    for oc in r1:
        r1[oc]["pass"] = bool(r1[oc][100]["median"] is not None and r1[oc][100]["median"] >= 0.60)
    print(f"  R1: {r1}")

    # R2 (unit = pressured reception)
    n_before_features = len(pr)
    pr = tp.reception_features(pr.drop(columns=["play_pattern_code"]), mids)  # value-model rows supply their own code
    print(f"  pressured receptions with value-model origin features: {len(pr)}/{n_before_features}")
    ev_out = pd.read_parquet(OUTCOMES_PATH, columns=["match_id", "event_id", "y_f3", "y_shot"])
    y10 = pd.concat([tp.net_xg_after(m) for m in mids], ignore_index=True)
    pr = pr.merge(ev_out, on=["match_id", "event_id"], how="left").merge(y10, on=["match_id", "event_id"], how="left")
    pr["y_f3"] = np.where(pr["recv_x"] < F3_X, pr["y_f3"], np.nan)
    for y in ("y_f3", "y_net_xg", "keep"):
        sub = pr[pr[y].notna()]
        oof, _ = tp.crossfit_g(sub.reset_index(drop=True), y, fold_of)
        pr.loc[sub.index, f"g_{y}"] = oof
    pr.to_parquet(OUT_PATH)
    ctrl = retention_s(pr, pd.read_parquet(RECEIPT_ACTIONS_PATH))
    r2 = {}
    for oc in ("keep", "fwd"):
        d = s_loo(pr, f"pr_{oc}")
        for y in ("y_f3", "y_net_xg"):
            for grp in ("all", "dm"):
                dd = d if grp == "all" else d[d["player_id"].isin(dm_ids)]
                res = tp.fe_fit(dd, y, f"g_{y}")
                keep_ids = set(dd.loc[dd["S_raw"].notna() & dd[y].notna(), "event_id"])
                res["control"] = tp.fe_fit(ctrl[ctrl["event_id"].isin(keep_ids)], "keep", "g_keep")
                r2[f"{grp}|pr_{oc}|{y}"] = res
                c = res["control"]
                print(f"  R2 {grp}|pr_{oc}|{y}: n={res['n_rows']} players={res['n_players']} "
                      f"coef100={res['coef_per_sd_per100']:+.4f} p={res['p']:.4g} MDE={res['mde_80_per100']:.4f} | "
                      f"control coef100={c['coef_per_sd_per100']:+.3f} p={c['p']:.3g}")

    # R3
    l_ids = set()
    for nm in LIST_L:
        hits = lb[lb["player_name"].apply(lambda full: name_matches(nm, full))]
        assert len(hits) == 1
        l_ids.add(hits["player_id"].iloc[0])
    rng = np.random.default_rng(SEED)
    r3 = {}
    for oc in ("keep", "fwd"):
        a = pr.groupby("player_id")[f"pr_{oc}"].agg(["mean", "size"])
        a = a[a["size"] >= MIN_ELSEWHERE]
        vals = pd.DataFrame({"sb_player_id": a.index.astype(float), "m": a["mean"].values})
        vals["role"] = vals["sb_player_id"].map(roles)
        res = perm_test(vals.dropna(subset=["role"]), l_ids, rng)
        res["present_names"] = [names.get(r["sb_player_id"]) for r in res.get("present", [])]
        r3[f"pr_{oc}"] = res
        print(f"  R3 pr_{oc}: present={res['n_present']} T={res.get('T')} p={res.get('p_two_sided')}")

    tables = {oc: dm_table(pr, f"pr_{oc}", dm_ids, names) for oc in ("keep", "fwd")}
    for oc, t in tables.items():
        print(f"  table pr_{oc}: players={t['n_players']} Q={t['dl']['Q']:.1f} p={t['dl']['p_value']:.3g} "
              f"above={len(t['names_above'])} below={len(t['names_below'])}")

    SUMMARY_PATH.write_text(json.dumps({"n_receipts_frame_actor": n_receipts, "n_pressured": n_pressured,
                                        "n_pressured_no_action": n_no_action, "n_analysed": int(len(pr)),
                                        "n_pressured_by_distance": int((rec["nearest_opp"] <= PRESS_DIST).sum()),
                                        "n_pressured_by_flag": int(rec["under_pressure_flag"].sum()),
                                        "baseline": base, "r1": r1, "r2": r2, "r3": r3, "tables": tables},
                                       indent=2, default=str))
    print(f"Wrote {SUMMARY_PATH}")


if __name__ == "__main__":
    main()
