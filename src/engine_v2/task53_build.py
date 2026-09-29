"""
Task 53, Step 2: build Task 52's measures on the 2015/16 REPLICATION leagues
(La Liga 11/27, Serie A 12/27, Ligue 1 7/27) -- the single use of that half.
docs/specs/task-53-tempo-replication.md.

Definitions exactly as Task 52 (task52_build.match_units: Step 3 spells and
context, M2's FK, M3's r, Amendment A's categories and M4 baselines). Every
baseline is refit on replication-league folds only (5 match folds, seed
20260929). M1, M5, M6 are not replicated (the M6 columns match_units
computes are left unused; no M6 baseline is fitted).
Guard: task52_build's id sets are replaced in place so its open_dev()
admits ONLY 2015/16 replication match ids; the study set is emptied, so no
study file can be opened.
Sensitivity for M2 (report only, per the brief's answer 3): units restricted
to pressured receptions whose spell ends in his Pass or a loss (spells
excluded from T for a shot, foul, period end, another player's on-ball
event or no end found are dropped); baseline refit on those units.

Run: python src/engine_v2/task53_build.py
"""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

import task52_build as b
from task50_robustness import mem_gate, MEM_LOG
from task52_split import SPLIT_PATH

warnings.filterwarnings("ignore")

DATA = Path(__file__).parent.parent.parent / "data"
OUT = DATA / "processed" / "engine_v2"
SUMMARY_PATH = DATA / "engine_v2_task53_build.json"
REP_LEAGUES = {(11, 27), (12, 27), (7, 27)}


def replication_ids() -> set:
    sp = pd.read_csv(SPLIT_PATH)
    sp = sp[(sp["dataset"] == "2015/16") & (sp["half"] == "REPLICATION")]
    assert set(zip(sp["competition_id"], sp["season_id"])) == REP_LEAGUES
    return set(sp["match_id"].astype(int))


def switch_guard() -> set:
    rep = replication_ids()
    b.DEV["2015/16"].clear()
    b.DEV["2015/16"].update(rep)
    b.DEV["study"].clear()
    return rep


def main():
    rep = switch_guard()
    mids = sorted(rep)
    print(f"Task 53 build: {len(mids)} 2015/16 REPLICATION matches ...")
    mem_gate(f"2015/16 replication: build units ({len(mids)} matches)")
    parts = [b.match_units("2015/16", m) for m in mids]
    R = pd.concat([p[0] for p in parts], ignore_index=True)
    P = pd.concat([p[1] for p in parts], ignore_index=True)
    fold = b.folds_for(mids)
    R["fold"], P["fold"] = R["match_id"].map(fold), P["match_id"].map(fold)
    ctx = b.CTX
    out = {"n_matches": len(mids), "n_completed_receptions": len(R), "end_reason": R["end_reason"].value_counts().to_dict(),
           "fold_sizes": pd.Series(fold).value_counts().sort_index().to_dict()}

    R["timed"] = (R["end_reason"] == "pass") & (R["T"] > 0) & (R["T"] <= b.T_MAX)
    Tm = R[R["timed"]].copy()
    Tm["logT"] = np.log(Tm["T"])
    Tm["g_T"], out["g_T_oof_r2"] = b.crossfit(Tm, ctx, "logT", "reg")
    R["r"] = R["event_id"].map(Tm.set_index("event_id")["logT"] - Tm.set_index("event_id")["g_T"])
    out["T_distribution"] = b.dist(Tm["T"])
    out["n_T_le_0"] = int(((R["end_reason"] == "pass") & (R["T"] <= 0)).sum())
    out["n_T_gt_15"] = int(((R["end_reason"] == "pass") & (R["T"] > b.T_MAX)).sum())

    Pr = R[R["pressured_flag"]].copy()
    for c in b.FK_CUTS:
        Pr[f"fk_{c}"] = ((Pr["end_reason"] == "pass") & (Pr["end_pass_complete"] == 1) & (Pr["T"] > 0) & (Pr["T"] <= c)).astype(int)
        p, out[f"fk_{c}_auc"] = b.crossfit(Pr, ctx, f"fk_{c}", "clf")
        out[f"fk_{c}_base_rate"] = float(Pr[f"fk_{c}"].mean())
        R.loc[Pr.index, f"fk_{c}"] = Pr[f"fk_{c}"]
        R.loc[Pr.index, f"fk_res_{c}"] = Pr[f"fk_{c}"] - p
    out["n_pressured_receptions"] = len(Pr)
    Sn = Pr[Pr["end_reason"].isin(["pass", "loss"])].copy()
    p, out["fk_sens_1.5_auc"] = b.crossfit(Sn, ctx, "fk_1.5", "clf")
    R.loc[Sn.index, "fk_sens_res_1.5"] = Sn["fk_1.5"] - p
    out["n_sensitivity_units"], out["fk_sens_1.5_base_rate"] = len(Sn), float(Sn["fk_1.5"].mean())

    out["category_share_all"] = P["category"].value_counts(normalize=True).to_dict()
    for cat in ("ACCEL", "KEEP", "SLOW", "SWITCH"):
        P[f"is_{cat}"] = (P["category"] == cat).astype(int)
        p, out[f"m4_{cat}_auc"] = b.crossfit(P, ctx, f"is_{cat}", "clf")
        P[f"res_{cat}"] = P[f"is_{cat}"] - p
    out["n_eligible_passes"] = len(P)
    out["n_players_receptions"], out["n_players_passes"] = int(R["player_id"].nunique()), int(P["player_id"].nunique())
    P = P.drop(columns=["v_before", "v_after"])  # M6 not replicated
    R.to_parquet(OUT / "task53_1516rep_receptions.parquet")
    P.to_parquet(OUT / "task53_1516rep_passes.parquet")
    SUMMARY_PATH.write_text(json.dumps({"build": out, "memory_log": MEM_LOG}, indent=2, default=str))
    print(json.dumps(out, default=str)[:2500])
    print(f"Wrote {SUMMARY_PATH}")


if __name__ == "__main__":
    main()
