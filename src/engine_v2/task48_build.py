"""
Task 48, Step 1: measures on the RESERVED data, definitions unchanged.
docs/specs/task-48-confirmation-reserved.md.

Reuses Task 44's builders (task44_build.event_features / eligible_passes /
competition_lookup / match_folds, task44_gate.receipt_flags / fit_baseline,
task43_spells.match_spells, task42_outcomes.match_outcomes,
task35_ptest.net_xg_after) with their events and matches directories
redirected to data/raw_reserved; W via task46_part_b.fit_w. Roles by Task
32's rule (players >= 100 eligible passes); deep midfielder = >= 50% of
eligible passes at C/L/R Defensive Midfield AND >= 300 eligible passes.

Run: python src/engine_v2/task48_build.py   (after task48_ingest.py)
"""
import json
import warnings
from pathlib import Path

import pandas as pd

import task35_ptest as tp
import task42_outcomes as t42o
import task43_spells as t43s
import task44_build as tb
from task44_gate import receipt_flags, fit_baseline
from task32_step4 import ROLE_POSITIONS
from task46_part_b import fit_w

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
EVR = DATA_DIR / "raw_reserved" / "events"
MR = DATA_DIR / "raw_reserved" / "matches"
PROC = DATA_DIR / "processed" / "engine_v2"
PASSES_PATH = PROC / "task48_passes.parquet"
RECEPTIONS_PATH = PROC / "task48_receptions.parquet"
ROLES_PATH = PROC / "task48_roles.parquet"
SUMMARY_PATH = DATA_DIR / "engine_v2_task48_build.json"
ROLE_MIN, DM_MIN, SHARE = 100, 300, 0.50


def main():
    print("Task 48 Step 1: building reserved-data measures ...")
    tb.EV16, tb.M16 = EVR, MR
    for mod in (tp, t42o, t43s):
        mod.EVENTS_DIR = EVR
    comp = tb.competition_lookup()
    mids = sorted(comp)
    folds = tb.match_folds(mids)
    feats, passes, rec, spells, outs, ys = [], [], [], [], [], []
    for i, m in enumerate(mids):
        feats.append(tb.event_features(m))
        passes.append(tb.eligible_passes(m))
        rec.append(receipt_flags(m, EVR))
        spells.append(t43s.match_spells(m))
        outs.append(t42o.match_outcomes(m)[0][["match_id", "event_id", "y_f3", "y_shot"]])
        ys.append(tp.net_xg_after(m))
        if (i + 1) % 250 == 0:
            print(f"  {i + 1}/{len(mids)}", flush=True)
    feat = pd.concat(feats, ignore_index=True)
    out = pd.concat(outs, ignore_index=True).merge(pd.concat(ys, ignore_index=True), on=["match_id", "event_id"])
    P = pd.concat(passes, ignore_index=True).merge(feat, on=["match_id", "event_id"], how="left") \
        .merge(out, on=["match_id", "event_id"], how="left")
    P["competition_id"] = P["match_id"].map(lambda m: comp[m][0])
    P["season_id"] = P["match_id"].map(lambda m: comp[m][1])
    P["fold"] = P["match_id"].map(folds)
    Rc = pd.concat(rec, ignore_index=True).merge(pd.concat(spells, ignore_index=True).drop(columns=["player_id"]),
                                                on=["match_id", "event_id"], how="left")
    Rc = Rc.merge(feat.drop(columns=["play_pattern_code", "period", "minute"]), on=["match_id", "event_id"], how="left") \
           .merge(out, on=["match_id", "event_id"], how="left")
    Rc["competition_id"] = Rc["match_id"].map(lambda m: comp[m][0])
    Rc["season_id"] = Rc["match_id"].map(lambda m: comp[m][1])
    Rc["fold"] = Rc["match_id"].map(folds)

    pr = Rc[Rc["pressured_flag"] & Rc["keep_spell"].notna()].copy().reset_index(drop=True)
    pr_base = fit_baseline(pr, folds)
    Rc = Rc.merge(pr[["match_id", "event_id", "pr2_flag_keep", "pr2_flag_fwd"]], on=["match_id", "event_id"], how="left")
    W, w_base = fit_w(Rc, folds)
    Rc = Rc.merge(W[["match_id", "event_id", "w"]], on=["match_id", "event_id"], how="left")
    print(f"  passes {len(P)}; receptions {len(Rc)}; pressured with outcome {len(pr)}; PR {pr_base}; W {w_base}")

    per = P.groupby("player_id").agg(n=("event_id", "size"), n_matches=("match_id", "nunique"),
                                     **{f"n_{r}": ("position", lambda s, ps=ps: int(s.isin(ps).sum())) for r, ps in ROLE_POSITIONS.items()})
    per = per[per["n"] >= ROLE_MIN]
    for r in ROLE_POSITIONS:
        per[f"share_{r}"] = per[f"n_{r}"] / per["n"]
    per["role"] = [next((r for r in ROLE_POSITIONS if row[f"share_{r}"] >= SHARE), "MIXED") for _, row in per.iterrows()]
    per["is_dm"] = (per["share_DM"] >= SHARE) & (per["n"] >= DM_MIN)
    names = pd.concat([pd.read_parquet(EVR / f"{m}.parquet", columns=["player_id", "player"]) for m in mids]) \
        .dropna().drop_duplicates("player_id").set_index("player_id")["player"]
    per["player_name"] = per.index.map(names)
    npr = pr.groupby("player_id").size()
    per["n_pressured"] = per.index.map(npr).fillna(0).astype(int)
    per.reset_index().to_parquet(ROLES_PATH)
    P.to_parquet(PASSES_PATH)
    Rc.to_parquet(RECEPTIONS_PATH)
    dm = per[per["is_dm"]].sort_values("n", ascending=False)
    SUMMARY_PATH.write_text(json.dumps({
        "n_matches": len(mids), "n_eligible_passes": len(P), "n_completed_receipts": len(Rc),
        "n_pressured_flag": int(Rc["pressured_flag"].sum()), "n_pressured_with_outcome": len(pr),
        "pr2_flag_baseline": pr_base, "w_baseline": w_base, "role_counts": per["role"].value_counts().to_dict(),
        "dm_list": [{"name": r.player_name, "matches": int(r.n_matches), "eligible_passes": int(r.n),
                     "pressured_receptions": int(r.n_pressured)} for r in dm.itertuples()]}, indent=2, default=str))
    print(f"  roles {per['role'].value_counts().to_dict()}; DM {int(per['is_dm'].sum())}; wrote {SUMMARY_PATH}")


if __name__ == "__main__":
    main()
