"""
Task 50, Step 4: all the deep-midfield evidence together (report only).
docs/specs/task-50-puzzle-robustness-pooling.md. The pre-registered
confirmation (Task 48 C1/C2) did not confirm; this pooling was decided
after seeing it.

(i)  PR2_flag_keep -> Y_F3 within DMs
     study (computed here): Task 44 Step 2's event-only measure on the study
       sample (task46_study_pr_flag.parquet), Task 44 P-test design
       (task44_tests.main's pressured-reception lines), study DM group
       (leaderboard_v5c.is_deep_midfield), study roles as Task 42
       (task32_step4.assign_roles), Task 35's match folds;
     2015/16 = Task 44 P2; reserved = Task 48 C1.
(ii) W -> Y_F3 within DMs
     study (computed here): Task 46's study W (task46_part_b.fit_w on the
       study receptions, rebuilt exactly as Task 46 did because the table
       was never saved), Task 46 B3 design;
     2015/16 = Task 46 B3; reserved = Task 48 C2.
Task 48 did not save an SE; it is recovered as (CI high - CI low) / 3.92
(fe_fit's CI is normal-theory: estimate +/- 1.96 SE). Pooling: inverse-
variance fixed effect; DerSimonian-Laird random effects (tau^2 from
task29_step1_2.dersimonian_laird); I^2 = max(0, (Q - df) / Q).

Run: python src/engine_v2/task50_pooling.py
"""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

import task35_ptest as tp
import task42_outcomes as t42o
import task44_build as tb
from crossfit import FOLDS_PATH
from task29_step1_2 import dersimonian_laird
from task32_step4 import assign_roles
from task32_step5 import leave_one_match_out
from task42_step2 import s_loo
from task44_gate import receipt_flags, EV_DIR
from task44_tests import crossfit_ev
from task46_part_a import STUDY_PR_PATH
from task46_part_b import fit_w
from task50_robustness import mem_gate, MEM_LOG
from task50_puzzle import safe_dummy_check

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
SUMMARY_PATH = DATA_DIR / "engine_v2_task50_step4.json"
STUDY_EVENTS = DATA_DIR / "raw" / "events"
LEADERBOARD_V5C_PATH = DATA_DIR / "processed" / "leaderboard_v5c.parquet"
T43_SPELLS = DATA_DIR / "processed" / "engine_v2" / "task43_spells.parquet"
F3_X = 80.0
TASK46_W_STUDY = {"n": 271830, "auc": 0.6134970381155733}


def loo(df, col, floor, name):
    v = leave_one_match_out(df.dropna(subset=[col])[["match_id", "player_id", col]].rename(columns={col: "decision"}),
                            "player_id", floor)
    return v[["match_id", "player_id", "complement_mean"]].rename(columns={"complement_mean": name})


def study_estimates() -> dict:
    mem_gate("study: build receptions")
    folds = pd.read_csv(FOLDS_PATH)
    folds = folds[folds["match_id"].isin({int(p.stem) for p in EV_DIR.glob("*.parquet")})]
    fold_st = dict(zip(folds["match_id"], folds["fold"]))
    mids = sorted(fold_st)
    tb.EV16 = STUDY_EVENTS
    feats = pd.concat([tb.event_features(m) for m in mids], ignore_index=True)
    f3 = pd.concat([t42o.match_outcomes(m)[0][["match_id", "event_id", "y_f3"]] for m in mids], ignore_index=True)
    rst = pd.concat([receipt_flags(m) for m in mids], ignore_index=True) \
        .merge(feats[["match_id", "event_id", "score_diff"]], on=["match_id", "event_id"], how="left")
    Wst, wst_base = fit_w(rst, fold_st)
    print(f"  study W baseline {wst_base}; Task 46: {TASK46_W_STUDY}", flush=True)

    lb = pd.read_parquet(LEADERBOARD_V5C_PATH, columns=["player_id", "is_deep_midfield"])
    dm = set(lb.loc[lb["is_deep_midfield"], "player_id"])
    roles = assign_roles(set(lb["player_id"])).set_index("player_id")["role"]
    spells = pd.read_parquet(T43_SPELLS, columns=["match_id", "event_id", "keep_spell"])
    gcols = ["match_id", "event_id"] + tb.G_FEATURES

    def prep(df):
        d = df.drop(columns=[c for c in tb.G_FEATURES + ["keep_spell"] if c in df.columns]) \
            .merge(feats[gcols], on=["match_id", "event_id"], how="left") \
            .merge(f3, on=["match_id", "event_id"], how="left") \
            .merge(spells, on=["match_id", "event_id"], how="left")
        d["y_f3"] = np.where(d["recv_x"] < F3_X, d["y_f3"], np.nan)
        d["role"] = d["player_id"].map(roles).fillna("NONE")
        d["fold"] = d["match_id"].map(fold_st)
        d = d.reset_index(drop=True)
        for y, g in (("y_f3", "g_f3"), ("keep_spell", "g_keep")):
            d[g], _ = crossfit_ev(d, y)
        return d

    mem_gate("study: (i) PR2_flag_keep")
    R = prep(pd.read_parquet(STUDY_PR_PATH))
    keep_s = loo(rst.merge(spells, on=["match_id", "event_id"], how="left"), "keep_spell", 100, "S_raw")
    ctrl = R.merge(keep_s, on=["match_id", "player_id"], how="left")
    S = s_loo(R, "pr2_flag_keep")
    d = S[S["player_id"].isin(dm)]
    pr = tp.fe_fit(d, "y_f3", "g_f3")
    ids = set(d.loc[d["S_raw"].notna() & d["y_f3"].notna() & d["g_f3"].notna(), "event_id"])
    pr["control"] = tp.fe_fit(ctrl[ctrl["event_id"].isin(ids)], "keep_spell", "g_keep")
    pr["dummy_check"] = safe_dummy_check(d, "y_f3", "g_f3")

    mem_gate("study: (ii) W")
    A = prep(Wst)
    A = A.merge(loo(A, "w", 100, "S_W"), on=["match_id", "player_id"], how="left") \
         .merge(loo(A, "keep_spell", 100, "S_keep"), on=["match_id", "player_id"], how="left")
    d = A[A["player_id"].isin(dm)]
    w = tp.fe_fit(d.assign(S_raw=d["S_W"]), "y_f3", "g_f3")
    ids = set(d.loc[d["S_W"].notna() & d["y_f3"].notna(), "event_id"])
    w["control"] = tp.fe_fit(d[d["event_id"].isin(ids)].assign(S_raw=lambda x: x["S_keep"]), "keep_spell", "g_keep")
    w["dummy_check"] = safe_dummy_check(d.assign(S_raw=d["S_W"]), "y_f3", "g_f3")
    return {"W_study_baseline": wst_base, "W_study_matches_task46": bool(
                wst_base["n"] == TASK46_W_STUDY["n"] and abs(wst_base["auc"] - TASK46_W_STUDY["auc"]) < 1e-9),
            "n_dm_group": len(dm), "PR": pr, "W": w}


def se_from_ci(ci95_per100):
    return (ci95_per100[1] - ci95_per100[0]) / 3.92 / 100


def pool(rows: list) -> dict:
    m = np.array([r["coef_per_sd"] for r in rows])
    v = np.array([r["se"] ** 2 for r in rows])
    dl = dersimonian_laird(m, v)
    wf = 1 / v
    se_fe = float(1 / np.sqrt(wf.sum()))
    wr = 1 / (v + dl["tau2"])
    mu_re = float((wr * m).sum() / wr.sum())
    se_re = float(1 / np.sqrt(wr.sum()))
    i2 = max(0.0, (dl["Q"] - dl["df"]) / dl["Q"]) if dl["Q"] > 0 else 0.0
    ci = lambda mu, se: [mu - 1.96 * se, mu + 1.96 * se]
    return {"fixed": {"est": dl["mu_w"], "se": se_fe, "ci95": ci(dl["mu_w"], se_fe), "p": float(2 * norm.sf(abs(dl["mu_w"] / se_fe)))},
            "random_dl": {"est": mu_re, "se": se_re, "ci95": ci(mu_re, se_re), "p": float(2 * norm.sf(abs(mu_re / se_re))),
                          "tau2": dl["tau2"]},
            "Q": dl["Q"], "df": dl["df"], "Q_p": dl["p_value"], "I2": i2}


def main():
    print("Task 50 Step 4: pooling the deep-midfield evidence (report only) ...")
    st = study_estimates()
    t44 = json.loads((DATA_DIR / "engine_v2_task44_steps4_5.json").read_text())["tests"]["dm|pr2_flag_keep|y_f3"]
    b3 = json.loads((DATA_DIR / "engine_v2_task46_part_b.json").read_text())["B3"]["DM|y_f3"]["W_alone"]
    fam = json.loads((DATA_DIR / "engine_v2_task48.json").read_text())["family"]
    se_check = {"task44_P2_saved_se": t44["se"], "task44_P2_se_from_ci": se_from_ci(t44["ci95_per100"])}

    def row(label, use, r, se=None, se_source="saved"):
        return {"sample": label, "use": use, "coef_per_sd": r["coef_per_sd"], "se": r["se"] if se is None else se,
                "se_source": se_source, "n_rows": r["n_rows"], "n_players": r["n_players"], "p": r["p"]}

    tables = {
        "i_PR2_flag_keep_to_Y_F3_DM": [
            row("study", "study sample (as usual); first time this cell is computed", st["PR"]),
            row("2015/16", "Task 44 P2 (first use); reused here", t44),
            row("reserved", "Task 48 C1 (first use); reused here", fam["C1"], se_from_ci(fam["C1"]["ci95_per100"]), "(CI width)/3.92"),
        ],
        "ii_W_to_Y_F3_DM": [
            row("study", "study sample (as usual); first time this cell is computed", st["W"]),
            row("2015/16", "Task 46 B3 (2015/16 further use); reused here", b3),
            row("reserved", "Task 48 C2 (first use); reused here", fam["C2"], se_from_ci(fam["C2"]["ci95_per100"]), "(CI width)/3.92"),
        ],
    }
    pooled = {k: pool(v) for k, v in tables.items()}
    for k, v in tables.items():
        print(f"  {k}:")
        for r in v:
            print(f"    {r['sample']:8s} {100 * r['coef_per_sd']:+.4f} (SE {100 * r['se']:.4f}) p={r['p']:.3g} n={r['n_rows']}/{r['n_players']}")
        p = pooled[k]
        print(f"    FE {100 * p['fixed']['est']:+.4f} {[round(100 * c, 4) for c in p['fixed']['ci95']]} p={p['fixed']['p']:.3g} | "
              f"DL {100 * p['random_dl']['est']:+.4f} {[round(100 * c, 4) for c in p['random_dl']['ci95']]} p={p['random_dl']['p']:.3g} "
              f"tau2={p['random_dl']['tau2']:.3g} | I2={p['I2']:.3f} Q={p['Q']:.3f} (p {p['Q_p']:.3g})")
    SUMMARY_PATH.write_text(json.dumps({"study": st, "tables": tables, "pooled": pooled, "se_check": se_check,
                                        "memory_log": MEM_LOG}, indent=2, default=str))
    print(f"  SE check (Task 44 P2): {se_check}")
    print(f"Wrote {SUMMARY_PATH}")


if __name__ == "__main__":
    main()
