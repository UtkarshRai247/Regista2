"""
Task 40 (author's decision when asked): persist Task 35's per-pass P-test
inputs, which Task 35 computed in memory but never saved, so the
BENCHMARK-v6 snapshot can recompute Task 35's v5-Decision coefficient
from the snapshot alone.

Rebuilt with Task 35's own code on identical inputs (the same rebuild
Task 39 used): task33_step3_f_state.build_feature_table,
task35_ptest.net_xg_after, task35_ptest.crossfit_g (net xG and completion
g), the pass_der_crossfit_v5 join, task32_step4.assign_roles (NONE for
passers outside the 537). Before writing, Task 35's own (a) and
positive-control coefficient and SE are asserted to reproduce exactly
(rtol 1e-9) from its saved JSON.

Run: python src/engine_v2/task40_persist_task35_inputs.py
"""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

import task33_step3_f_state as tfs
import task35_ptest as tp
from task32_step4 import assign_roles
from crossfit import FOLDS_PATH

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
LEADERBOARD_V5C_PATH = DATA_DIR / "processed" / "leaderboard_v5c.parquet"
TASK35_PATH = DATA_DIR / "engine_v2_task35_ptest.json"
OUT_PATH = DATA_DIR / "processed" / "engine_v2" / "task35_ptest_inputs.parquet"


def main():
    folds = pd.read_csv(FOLDS_PATH)
    ev_mids = {int(p.stem) for p in tp.EV_DIR.glob("*.parquet")}
    folds = folds[folds["match_id"].isin(ev_mids)]
    fold_of = dict(zip(folds["match_id"], folds["fold"]))
    mids = sorted(fold_of)
    y_all = pd.concat([tp.net_xg_after(m) for m in mids], ignore_index=True)
    feat = tfs.build_feature_table(mids).merge(y_all, on=["match_id", "event_id"], how="left")
    feat["pass_complete"] = feat["pass_complete"].astype(float)
    feat["g_xg"], _ = tp.crossfit_g(feat, "y_net_xg", fold_of)
    feat["g_cmp"], _ = tp.crossfit_g(feat, "pass_complete", fold_of)
    v5 = pd.read_parquet(tp.CROSSFIT_V5_PATH, columns=["match_id", "event_id", "team", "player_id", "decision", "ev_chosen"])
    v5 = v5.merge(feat[["match_id", "event_id", "y_net_xg", "pass_complete", "g_xg", "g_cmp"]],
                  on=["match_id", "event_id"], how="inner")
    lb = pd.read_parquet(LEADERBOARD_V5C_PATH, columns=["player_id"])
    v5["role"] = v5["player_id"].map(assign_roles(set(lb["player_id"])).set_index("player_id")["role"]).fillna("NONE")

    t35 = json.loads(TASK35_PATH.read_text())["step2"]
    for key, col, y, g in (("a_decision_v5", "decision", "y_net_xg", "g_xg"),
                           ("control", "pass_complete", "pass_complete", "g_cmp")):
        d = tp.add_s(v5, col)
        d["role"] = d["player_id"].map(v5.drop_duplicates("player_id").set_index("player_id")["role"])
        r = tp.fe_fit(d, y, g)
        assert np.isclose(r["coef_per_sd"], t35[key]["coef_per_sd"], rtol=1e-9, atol=0), (key, r["coef_per_sd"])
        assert np.isclose(r["se"], t35[key]["se"], rtol=1e-9, atol=0), (key, r["se"])
        print(f"  {key}: reproduced coef={r['coef_per_sd']!r} se={r['se']!r}")

    v5.to_parquet(OUT_PATH)
    print(f"Wrote {OUT_PATH} ({len(v5)} rows)")


if __name__ == "__main__":
    main()
