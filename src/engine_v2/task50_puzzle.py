"""
Task 50, Step 2: the "fewer chances" puzzle. docs/specs/task-50-puzzle-robustness-pooling.md.
2015/16 (further use after Tasks 44-47) and reserved (second use after
Task 48); report only.

Design = Task 44's P-test: unit = pressured reception (pr2_flag_keep not
null) from the saved receptions tables; S = other-match mean (>= 50
elsewhere, task42_step2.s_loo) of PR2_flag_keep, and separately of A1
(2015/16: unit minus team mean, task45_vetting; reserved: minus team x
competition-season mean, task48_tests); event-only g refit per outcome
(task44_tests.crossfit_ev); role FE; team-match FE; SE by player
(task35_ptest.fe_fit); retention control (task48_tests.ptest). All players
and deep midfielders (each dataset's own roles table is_dm).

Outcomes, per event i in index order, from the event's own team's view
(the same ordering and shot-xG source as task35_ptest.net_xg_after):
  y_net_xg       reference: own minus opponent shot xG, events i+1..i+10
  xg_for_10      own shot xG, events i+1..i+10
  xg_against_10  opponent shot xG, events i+1..i+10
  net_xg_20/30   as y_net_xg with 20 / 30 events
  poss_xg        own shot xG in events after i with the same `possession`
  poss_len       number of own-team events after i with the same `possession`
  next_against   opponent shot xG in the first later possession whose
                 possession_team is the opponent (0 if there is none)

Run: python src/engine_v2/task50_puzzle.py
"""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

import task35_ptest as tp
import task48_tests as t48
from task32_step5 import leave_one_match_out
from task42_step2 import s_loo
from task44_tests import crossfit_ev
from task50_robustness import mem_gate, MEM_LOG

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
SUMMARY_PATH = DATA_DIR / "engine_v2_task50_step2.json"
PROC = DATA_DIR / "processed" / "engine_v2"
DATASETS = {
    "2015/16": {"use": "further use after Tasks 44-47", "events": DATA_DIR / "raw_1516" / "events",
                "receptions": PROC / "task44_receptions.parquet", "roles": PROC / "task44_roles.parquet",
                "a1_keys": ["team"]},
    "reserved": {"use": "second use after Task 48", "events": DATA_DIR / "raw_reserved" / "events",
                 "receptions": PROC / "task48_receptions.parquet", "roles": PROC / "task48_roles.parquet",
                 "a1_keys": ["team", "competition_id", "season_id"]},
}
OUTCOMES = ["y_net_xg", "xg_for_10", "xg_against_10", "net_xg_20", "net_xg_30", "poss_xg", "poss_len", "next_against"]
NEW = OUTCOMES[1:] + ["net_xg_10_check"]


def window_sum(v: np.ndarray, w: int) -> np.ndarray:
    cs = np.concatenate([[0.0], np.cumsum(v)])
    i, n = np.arange(len(v)), len(v)
    return cs[np.minimum(i + 1 + w, n)] - cs[np.minimum(i + 1, n)]


def suffix_after(v: np.ndarray, grp: np.ndarray) -> np.ndarray:
    """Sum of v over later rows (strictly after) with the same grp value; rows are in index order."""
    s = pd.Series(v)
    return (s[::-1].groupby(grp[::-1]).cumsum()[::-1] - s).values


def match_outcomes(path: Path, event_ids: set) -> pd.DataFrame:
    ev = pd.read_parquet(path, columns=["id", "index", "team", "type", "shot_statsbomb_xg", "possession", "possession_team"])
    ev = ev.sort_values("index").reset_index(drop=True)
    teams = ev["team"].dropna().unique().tolist()
    assert len(teams) == 2
    xg = np.where(ev["type"] == "Shot", ev["shot_statsbomb_xg"].fillna(0.0), 0.0)
    poss = ev["possession"].values
    # per possession: possession team and the xG of shots taken by that team inside it
    pt = ev.groupby("possession")["possession_team"].first()
    pxg = pd.Series(np.where(ev["team"].values == ev["possession_team"].values, xg, 0.0)).groupby(poss).sum()
    plist = pt.index.values
    out = {c: np.zeros(len(ev)) for c in NEW}
    for t in teams:
        own = (ev["team"] == t).values
        opp = (~own) & ev["team"].notna().values
        f, a = np.where(own, xg, 0.0), np.where(opp, xg, 0.0)
        cols = {"xg_for_10": window_sum(f, 10), "xg_against_10": window_sum(a, 10),
                "net_xg_10_check": window_sum(f - a, 10), "net_xg_20": window_sum(f - a, 20),
                "net_xg_30": window_sum(f - a, 30), "poss_xg": suffix_after(f, poss),
                "poss_len": suffix_after(own.astype(float), poss)}
        # next opponent possession after each possession p
        nxt, following = {}, 0.0
        for p in plist[::-1]:
            nxt[p] = following
            if pt[p] != t:
                following = float(pxg[p])
        cols["next_against"] = np.array([nxt[p] for p in poss])
        for c, v in cols.items():
            out[c] = np.where(own, v, out[c])
    df = pd.DataFrame(out)
    df["event_id"] = ev["id"].values
    return df[df["event_id"].isin(event_ids)]


def safe_dummy_check(d, y, g):
    """task35_ptest.dummy_check uses the first 40 team-matches only; S can lack within variation there."""
    try:
        return tp.dummy_check(d, y, g)
    except KeyError as e:
        return f"not computable on the first 40 team-matches ({e!r} dropped)"


def run_dataset(name: str, cfg: dict) -> dict:
    mem_gate(f"{name}: load receptions")
    Rc = pd.read_parquet(cfg["receptions"])
    roles = pd.read_parquet(cfg["roles"]).set_index("player_id")
    dm = set(roles.index[roles["is_dm"]])
    Rc["role"] = Rc["player_id"].map(roles["role"]).fillna("NONE")
    R = Rc[Rc["pr2_flag_keep"].notna()].copy().reset_index(drop=True)

    mem_gate(f"{name}: per-match outcomes")
    parts = []
    for mid, ids in R.groupby("match_id")["event_id"]:
        parts.append(match_outcomes(cfg["events"] / f"{mid}.parquet", set(ids)).assign(match_id=mid))
    O = pd.concat(parts, ignore_index=True)
    R = R.merge(O, on=["match_id", "event_id"], how="left")
    assert R[NEW].notna().all().all()
    ref_diff = float((R["net_xg_10_check"] - R["y_net_xg"]).abs().max())
    print(f"  {name}: {len(R)} pressured receptions; max |recomputed net xG 10 - saved y_net_xg| = {ref_diff:.2e}", flush=True)

    mem_gate(f"{name}: g cross-fits")
    gr2 = {}
    for y in OUTCOMES + ["keep_spell"]:
        R[f"g_{y}"], gr2[y] = crossfit_ev(R, y)
    allk = Rc.dropna(subset=["keep_spell", "player_id"])
    keep_s = leave_one_match_out(allk[["match_id", "player_id", "keep_spell"]].rename(columns={"keep_spell": "decision"}),
                                 "player_id", 100)[["match_id", "player_id", "complement_mean"]]
    ctrl = R.rename(columns={"g_keep_spell": "g_keep"}).merge(keep_s, on=["match_id", "player_id"], how="left") \
            .rename(columns={"complement_mean": "S_raw"})
    R["a1"] = R["pr2_flag_keep"] - R.groupby(cfg["a1_keys"])["pr2_flag_keep"].transform("mean")
    S = {"PR2_flag_keep": s_loo(R, "pr2_flag_keep"), "A1": s_loo(R, "a1")}

    cells = {}
    for grp in ("all", "DM"):
        for sname, d in S.items():
            dd = d if grp == "all" else d[d["player_id"].isin(dm)]
            for y in OUTCOMES:
                r = t48.ptest(dd, y, f"g_{y}", ctrl)
                r["dummy_check"] = safe_dummy_check(dd, y, f"g_{y}")
                cells[f"{grp}|{sname}|{y}"] = r
                print(f"    {grp:3s} {sname:13s} {y:13s} coef/SD {r['coef_per_sd']:+.5f} "
                      f"[{r['ci95'][0]:+.5f}, {r['ci95'][1]:+.5f}] p={r['p']:.3g} n={r['n_rows']}/{r['n_players']} "
                      f"mean={r['y_mean']:.4f} | ctrl {r['control']['coef_per_sd']:+.4f} p={r['control']['p']:.3g}", flush=True)
    return {"use": cfg["use"], "n_pressured": len(R), "n_matches": int(R["match_id"].nunique()), "n_dm": len(dm),
            "max_abs_diff_net_xg_10_vs_saved": ref_diff, "g_oof_r2": gr2,
            "outcome_means": R[OUTCOMES].mean().to_dict(),
            "n_next_against_zero": int((R["next_against"] == 0).sum()), "cells": cells}


def main():
    print("Task 50 Step 2: the fewer-chances puzzle (report only) ...")
    res = {name: run_dataset(name, cfg) for name, cfg in DATASETS.items()}
    SUMMARY_PATH.write_text(json.dumps({"datasets": res, "memory_log": MEM_LOG}, indent=2, default=str))
    print(f"Wrote {SUMMARY_PATH}")


if __name__ == "__main__":
    main()
