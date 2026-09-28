"""
Task 35, Step 1: minimum detectable effects (80% power, alpha 0.05:
MDE = 2.8 x SE) of the out-of-match team-match tests already run --
Task 32 Step 5, Task 33 Step 4a, Task 34 R3 -- read from their own
summary JSONs (no refit). Scale: SD across team-contexts of the
team-context's mean xG (and goals) per match, over the 292 engine v5
matches.

Run: python src/engine_v2/task35_step1_mde.py
"""
import json
from pathlib import Path

import pandas as pd

from outcome_validation import build_team_match_units, add_xg
from crossfit import FOLDS_PATH

DATA_DIR = Path(__file__).parent.parent.parent / "data"
EV_DIR = DATA_DIR / "processed" / "engine_v2" / "options_ev_v4"
SUMMARY_PATH = DATA_DIR / "engine_v2_task35_step1.json"
MDE_FACTOR = 2.8


def rows_from(task: str, label: str, results: dict, n_fit) -> list:
    out = []
    for spec, res in results.items():
        c = res["coefficients"]["decision_z"]
        out.append({"task": task, "test": label, "spec": spec, "n": res["n"], "coef": c["coef"], "se": c["se"],
                    "p": c["p_value"], "mde_80": MDE_FACTOR * c["se"]})
    return out


def main():
    rows = []
    t32 = json.loads((DATA_DIR / "engine_v2_task32_step5.json").read_text())
    rows += rows_from("32 Step 5", "LINEUP decision_v5", t32["lineup"]["results"], t32["lineup"]["n_fit"])
    rows += rows_from("32 Step 5", "TEAM decision_v5", t32["team"]["results"], t32["team"]["n_fit"])
    t33 = json.loads((DATA_DIR / "engine_v2_task33_step4a.json").read_text())
    for label, v in t33["versions"].items():
        rows += rows_from("33 Step 4a", f"LINEUP {label}", v["results"], v["n_fit"])
    t34 = json.loads((DATA_DIR / "engine_v2_task34_step2_3.json").read_text())
    rows += rows_from("34 R3", "LINEUP RQ", t34["r3"]["results"], t34["r3"]["n_fit"])
    for r in rows:
        print(f"  {r['task']:10s} {r['test']:28s} {r['spec']:12s} n={r['n']} coef={r['coef']:+.4f} "
              f"se={r['se']:.4f} MDE={r['mde_80']:.4f}")

    fold_mids = set(pd.read_csv(FOLDS_PATH)["match_id"]) & {int(p.stem) for p in EV_DIR.glob("*.parquet")}
    assert len(fold_mids) == 292
    units, _ = build_team_match_units()
    units = add_xg(units[units["match_id"].isin(fold_mids)])
    units["team_context"] = units["team"].astype(str) + "|" + units["competition_id"].astype(str) + "|" + \
        units["season_id"].astype(str)
    ctx = units.groupby("team_context").agg(xg=("xg", "mean"), goals=("goals", "mean"), n_matches=("match_id", "size"))
    scale = {"n_team_matches": len(units), "n_team_contexts": len(ctx),
             "mean_matches_per_context": float(ctx["n_matches"].mean()),
             "median_matches_per_context": float(ctx["n_matches"].median()),
             "sd_ctx_mean_xg": float(ctx["xg"].std(ddof=1)), "sd_ctx_mean_goals": float(ctx["goals"].std(ddof=1)),
             "sd_ctx_mean_xg_contexts_ge5_matches": float(ctx.loc[ctx["n_matches"] >= 5, "xg"].std(ddof=1)),
             "n_contexts_ge5_matches": int((ctx["n_matches"] >= 5).sum()),
             "sd_team_match_xg": float(units["xg"].std(ddof=1))}
    print(f"  scale: {scale}")
    SUMMARY_PATH.write_text(json.dumps({"mde_factor": MDE_FACTOR, "rows": rows, "scale": scale}, indent=2))
    print(f"Wrote {SUMMARY_PATH}")


if __name__ == "__main__":
    main()
