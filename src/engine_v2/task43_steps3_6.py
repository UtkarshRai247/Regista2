"""
Task 43, Steps 3, 4 and 6 plus the claim family (second attempt, study
sample only). docs/specs/task-43-press-resistance-v2.md.

Step 3: Task 42 Step 2 R2's design on the Task 43 spell units
(task35_ptest.reception_features, crossfit_g, fe_fit; S = other-match PR2,
>= 50 elsewhere). Retention control redefined: Y = the row's keep_spell;
S = the receiver's keep_spell rate over ALL his completed receptions in
his other matches (>= 100 elsewhere); g refit.
Step 4: Task 41's perm_test, >= 50 pressured receptions; Holm across all
seven directional praised-list tests so far.
Step 6: Task 29's method via task42_step2.dm_table.

Run: python src/engine_v2/task43_steps3_6.py   (after task43_spells.py)
"""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from statsmodels.stats.multitest import multipletests

import task35_ptest as tp
from crossfit import FOLDS_PATH
from task32_step4 import assign_roles
from task32_step5 import leave_one_match_out
from task27_step1_deep_midfield import name_matches
from task41_lists_availability import perm_test, LIST_L
from task42_step2 import s_loo, dm_table, F3_X

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
LEADERBOARD_V5C_PATH = DATA_DIR / "processed" / "leaderboard_v5c.parquet"
ALL_SPELLS_PATH = DATA_DIR / "processed" / "engine_v2" / "task43_spells.parquet"
PRESSURED_PATH = DATA_DIR / "processed" / "engine_v2" / "task43_pressured_spells.parquet"
OUTCOMES_PATH = DATA_DIR / "processed" / "engine_v2" / "task42_event_outcomes.parquet"
SUMMARY_PATH = DATA_DIR / "engine_v2_task43_steps3_6.json"
SEED = 20260928
MIN_PR_RECEPTIONS = 50


def main():
    print("Task 43 Steps 3, 4, 6 ...")
    folds = pd.read_csv(FOLDS_PATH)
    ev_mids = {int(p.stem) for p in tp.EV_DIR.glob("*.parquet")}
    folds = folds[folds["match_id"].isin(ev_mids)]
    fold_of = dict(zip(folds["match_id"], folds["fold"]))
    mids = sorted(fold_of)

    pr = pd.read_parquet(PRESSURED_PATH)
    lb = pd.read_parquet(LEADERBOARD_V5C_PATH, columns=["player_id", "player_name", "is_deep_midfield"])
    roles = assign_roles(set(lb["player_id"])).set_index("player_id")["role"]
    dm_ids = set(lb.loc[lb["is_deep_midfield"], "player_id"])
    names = lb.set_index("player_id")["player_name"].to_dict()

    # ---- Step 3 ----
    n0 = len(pr)
    pr3 = tp.reception_features(pr.drop(columns=["play_pattern_code"]), mids)
    ev_out = pd.read_parquet(OUTCOMES_PATH, columns=["match_id", "event_id", "y_f3"])
    y10 = pd.concat([tp.net_xg_after(m) for m in mids], ignore_index=True)
    pr3 = pr3.merge(ev_out, on=["match_id", "event_id"], how="left").merge(y10, on=["match_id", "event_id"], how="left")
    pr3["y_f3"] = np.where(pr3["recv_x"] < F3_X, pr3["y_f3"], np.nan)
    for y in ("y_f3", "y_net_xg", "keep_spell"):
        sub = pr3[pr3[y].notna()]
        oof, _ = tp.crossfit_g(sub.reset_index(drop=True), y, fold_of)
        pr3.loc[sub.index, f"g_{y}"] = oof
    pr3["role"] = pr3["player_id"].map(roles).fillna("NONE")
    print(f"  Step 3 units with value-model features: {len(pr3)}/{n0}")

    allsp = pd.read_parquet(ALL_SPELLS_PATH).dropna(subset=["keep_spell", "player_id"])
    vals = leave_one_match_out(allsp[["match_id", "player_id", "keep_spell"]].rename(columns={"keep_spell": "decision"}),
                               "player_id", 100)
    ctrl = pr3.merge(vals[["match_id", "player_id", "complement_mean"]], on=["match_id", "player_id"], how="left") \
              .rename(columns={"complement_mean": "S_raw"})
    r2 = {}
    for col in ("pr2_keep", "pr2_fwd"):
        d = s_loo(pr3, col)
        for y in ("y_f3", "y_net_xg"):
            for grp in ("all", "dm"):
                dd = d if grp == "all" else d[d["player_id"].isin(dm_ids)]
                res = tp.fe_fit(dd, y, f"g_{y}")
                ids = set(dd.loc[dd["S_raw"].notna() & dd[y].notna(), "event_id"])
                res["control"] = tp.fe_fit(ctrl[ctrl["event_id"].isin(ids)], "keep_spell", "g_keep_spell")
                r2[f"{grp}|{col}|{y}"] = res
                c = res["control"]
                print(f"  R2 {grp}|{col}|{y}: n={res['n_rows']} players={res['n_players']} coef100={res['coef_per_sd_per100']:+.4f} "
                      f"p={res['p']:.4g} MDE={res['mde_80_per100']:.4f} | control {c['coef_per_sd_per100']:+.3f} p={c['p']:.3g}")
    fam = [k for k in r2 if k.startswith("dm|")]
    holm = multipletests([r2[k]["p"] for k in fam], method="holm")[1]
    family = []
    for k, h in zip(fam, holm):
        c = r2[k]["control"]
        ok = c["coef_per_sd"] > 0 and c["p"] < 0.05
        family.append({"test": k, "coef_per100": r2[k]["coef_per_sd_per100"], "p": r2[k]["p"], "p_holm": float(h),
                       "control_coef_per100": c["coef_per_sd_per100"], "control_p": c["p"], "control_ok": bool(ok),
                       "claim_allowed": bool(h < 0.05 and ok)})

    # ---- Step 4 ----
    l_ids = set()
    for nm in LIST_L:
        hits = lb[lb["player_name"].apply(lambda full: name_matches(nm, full))]
        assert len(hits) == 1
        l_ids.add(hits["player_id"].iloc[0])
    rng = np.random.default_rng(SEED)
    s4 = {}
    for col in ("pr2_keep", "pr2_fwd"):
        a = pr.groupby("player_id")[col].agg(["mean", "size"])
        a = a[a["size"] >= MIN_PR_RECEPTIONS]
        v = pd.DataFrame({"sb_player_id": a.index.astype(float), "m": a["mean"].values})
        v["role"] = v["sb_player_id"].map(roles)
        res = perm_test(v.dropna(subset=["role"]), l_ids, rng)
        res["present_names"] = [names.get(r["sb_player_id"]) for r in res.get("present", [])]
        s4[col] = res
        print(f"  Step 4 {col}: n_qual={res['n_qualifying']} present={res['n_present']} T={res['T']:.3f} p={res['p_two_sided']:.4g}")
    t41 = json.loads((DATA_DIR / "engine_v2_task41_steps7_10.json").read_text())["step7"]
    t42 = json.loads((DATA_DIR / "engine_v2_task42_step2.json").read_text())["r3"]
    directional = [("Task 41 AV (lower)", t41["AV"]["T"], t41["AV"]["p_two_sided"]),
                   ("Task 41 AV_vis (lower)", t41["AV_vis"]["T"], t41["AV_vis"]["p_two_sided"]),
                   ("Task 41 RQ_rel (lower)", t41["rq_rel"]["T"], t41["rq_rel"]["p_two_sided"]),
                   ("Task 42 PR_keep (higher)", t42["pr_keep"]["T"], t42["pr_keep"]["p_two_sided"]),
                   ("Task 42 PR_fwd (higher)", t42["pr_fwd"]["T"], t42["pr_fwd"]["p_two_sided"]),
                   ("Task 43 PR2_keep (higher)", s4["pr2_keep"]["T"], s4["pr2_keep"]["p_two_sided"]),
                   ("Task 43 PR2_fwd (higher)", s4["pr2_fwd"]["T"], s4["pr2_fwd"]["p_two_sided"])]
    adj = multipletests([p for _, _, p in directional], method="holm")[1]
    s4["holm_all_directional"] = [{"test": n, "T": T, "p": p, "p_holm": float(a)} for (n, T, p), a in zip(directional, adj)]
    for r in s4["holm_all_directional"]:
        print(f"    {r['test']}: T={r['T']:+.3f} p={r['p']:.4g} holm={r['p_holm']:.4g}")

    # ---- Step 6 ----
    tables = {col: dm_table(pr, col, dm_ids, names) for col in ("pr2_keep", "pr2_fwd")}
    for col, t in tables.items():
        print(f"  Step 6 {col}: Q={t['dl']['Q']:.1f} p={t['dl']['p_value']:.3g} above={t['names_above']} below={t['names_below']}")

    SUMMARY_PATH.write_text(json.dumps({"n_step3_units": len(pr3), "n_spells": n0, "r2": r2, "family": family,
                                        "step4": s4, "tables": tables}, indent=2, default=str))
    print(f"Wrote {SUMMARY_PATH}")


if __name__ == "__main__":
    main()
