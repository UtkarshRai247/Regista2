"""
Task 50, Step 3: how solid are Task 48's C4 and C6 on the RESERVED data
(second use, report only)? docs/specs/task-50-puzzle-robustness-pooling.md.

C4 and C6 are repeated with Task 48's code (task48_tests.c4_movers, ptest,
summarise; the C6 lines of task48_tests.main copied into run_c4_c6) on
subsets of the reserved receptions table:
  men only, women only; club only, national team only (C6 only);
  excluding every match involving a team named Barcelona / Barcelona WFC;
  excluding Sergio Busquets (5203) and Keira Walsh (4658).
The built per-unit measures (pr2_flag_keep, keep_spell, y_f3, fold) are
taken as saved; every test-stage step (g cross-fit, retention S, A1
demeaning, leave-match-out S, reliabilities, bootstrap) is re-run inside
the subset. No correction, no claim.

Run: python src/engine_v2/task50_robustness.py
"""
import json
import subprocess
import re
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

import task48_tests as t48
from task32_step5 import leave_one_match_out
from task42_step2 import s_loo
from task44_tests import crossfit_ev

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
SUMMARY_PATH = DATA_DIR / "engine_v2_task50_step3.json"
BARCELONA = {"Barcelona", "Barcelona WFC"}
EXCLUDED_PLAYERS = {5203: "Sergio Busquets i Burgos", 4658: "Keira Walsh"}
MEM_LOG = []


def mem_gate(label: str):
    """Task 25 memory gate: proceed at >= 40% free and >= 3 GB available; wait and re-check otherwise."""
    # Same readings as src/decision_engine/task09b_horizon.get_free_pct / get_available_gb.
    while True:
        mp = subprocess.run(["memory_pressure"], capture_output=True, text=True).stdout
        free = float(re.search(r"System-wide memory free percentage:\s*(\d+)%", mp).group(1))
        vm = subprocess.run(["vm_stat"], capture_output=True, text=True).stdout
        page = int(re.search(r"page size of (\d+) bytes", vm).group(1))
        pages = sum(int(re.search(rf"{k}:\s*(\d+)\.", vm).group(1)) for k in ("Pages free", "Pages inactive", "Pages purgeable"))
        gb = pages * page / 1024 ** 3
        ok = free >= 40 and gb >= 3
        MEM_LOG.append({"label": label, "free_pct": free, "avail_gb": round(gb, 2), "proceed": ok})
        print(f"  [mem] {label}: {free:.0f}% free, {gb:.1f} GB -> {'proceed' if ok else 'wait'}", flush=True)
        if ok:
            return
        time.sleep(60)


def run_c4_c6(Rc: pd.DataFrame, roles: pd.DataFrame, intl_map: dict, do_c4: bool = True) -> dict:
    """Task 48 C4 and C6 exactly as in task48_tests.main, on whatever receptions table is passed."""
    Rc = Rc.copy()
    Rc["role"] = Rc["player_id"].map(roles["role"]).fillna("NONE")
    Rc["y_f3"] = np.where(Rc["recv_x"] < t48.F3_X, Rc["y_f3"], np.nan)
    allk = Rc.dropna(subset=["keep_spell", "player_id"])
    keep_s = leave_one_match_out(allk[["match_id", "player_id", "keep_spell"]].rename(columns={"keep_spell": "decision"}),
                                 "player_id", 100)[["match_id", "player_id", "complement_mean"]]
    R = Rc[Rc["pr2_flag_keep"].notna()].copy().reset_index(drop=True)
    for y, g in (("y_f3", "g_f3"), ("keep_spell", "g_keep")):
        R[g], _ = crossfit_ev(R, y)
    ctrl_R = R.merge(keep_s, on=["match_id", "player_id"], how="left").rename(columns={"complement_mean": "S_raw"})
    R["a1"] = R["pr2_flag_keep"] - R.groupby(["team", "competition_id", "season_id"])["pr2_flag_keep"].transform("mean")
    out = {"C6": t48.summarise(t48.ptest(s_loo(R, "a1"), "y_f3", "g_f3", ctrl_R))}
    if do_c4:
        out["C4"] = t48.c4_movers(R, intl_map)
    return out


def main():
    print("Task 50 Step 3 (reserved data, second use; report only) ...")
    mem_gate("load reserved receptions")
    Rc = pd.read_parquet(t48.RECEPTIONS_PATH)
    roles = pd.read_parquet(t48.ROLES_PATH).set_index("player_id")
    ing = json.loads((DATA_DIR / "engine_v2_task48_ingest.json").read_text())["per_competition_season"]
    intl_map = {(r["competition_id"], r["season_id"]): r["international"] for r in ing}
    gender = {(r["competition_id"], r["season_id"]): r["gender"] for r in ing}
    cs = list(zip(Rc["competition_id"], Rc["season_id"]))
    is_male = np.array([gender[k] == "male" for k in cs])
    is_intl = np.array([intl_map[k] for k in cs])
    barca_matches = set(Rc.loc[Rc["team"].isin(BARCELONA), "match_id"])
    subsets = {
        "full (reproduction of Task 48)": (np.ones(len(Rc), bool), True),
        "men only": (is_male, True),
        "women only": (~is_male, True),
        "club only": (~is_intl, False),
        "national team only": (is_intl, False),
        "excluding Barcelona matches": (~Rc["match_id"].isin(barca_matches).values, True),
        "excluding Busquets and Walsh": (~Rc["player_id"].isin(EXCLUDED_PLAYERS).values, True),
    }
    res = {}
    for name, (mask, do_c4) in subsets.items():
        mem_gate(name)
        sub = Rc[mask].reset_index(drop=True)
        r = run_c4_c6(sub, roles, intl_map, do_c4)
        r["n_matches"] = int(sub["match_id"].nunique())
        r["n_receptions"] = len(sub)
        if not do_c4:
            r["C4"] = "not run: the brief marks this subset C6 only"
        res[name] = r
        c4 = r["C4"] if isinstance(r["C4"], dict) else {}
        print(f"  {name}: matches={r['n_matches']} C6={r['C6']['coef_per_sd_per100']:+.3f} {r['C6']['ci95_per100']} "
              f"p={r['C6']['p']:.3g} n={r['C6']['n_rows']}/{r['C6']['n_players']} | "
              f"C4 r_true={c4.get('r_true')} {c4.get('r_true_ci')} p={c4.get('p')} movers={c4.get('n_movers')}", flush=True)
    SUMMARY_PATH.write_text(json.dumps({
        "dataset": "reserved (second use, after Task 48)", "barcelona_teams": sorted(BARCELONA),
        "n_barcelona_matches": len(barca_matches), "excluded_players": EXCLUDED_PLAYERS,
        "subsets": res, "memory_log": MEM_LOG}, indent=2, default=str))
    print(f"Wrote {SUMMARY_PATH}")


if __name__ == "__main__":
    main()
