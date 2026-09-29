"""
Task 50, Step 1 spot-check: from the BENCHMARK v8 snapshot copies only
(data/benchmark_v8/), never the live originals, recompute Task 48 C6
(+1.281 pp per 100 pressured receptions per SD) and C4 r_true (+0.650)
with Task 48's code (via task50_robustness.run_c4_c6).

Run: python src/engine_v2/task50_spotcheck.py
"""
import json
from pathlib import Path

import pandas as pd

from task50_robustness import run_c4_c6

REPO_ROOT = Path(__file__).parent.parent.parent
SNAP = REPO_ROOT / "data" / "benchmark_v8"
SUMMARY_PATH = REPO_ROOT / "data" / "engine_v2_task50_spotcheck.json"
EXPECTED = {"C6_coef_per_sd_per100": 1.281, "C4_r_true": 0.650}


def main():
    Rc = pd.read_parquet(SNAP / "processed" / "engine_v2" / "task48_receptions.parquet")
    roles = pd.read_parquet(SNAP / "processed" / "engine_v2" / "task48_roles.parquet").set_index("player_id")
    ing = json.loads((SNAP / "engine_v2_task48_ingest.json").read_text())["per_competition_season"]
    intl_map = {(r["competition_id"], r["season_id"]): r["international"] for r in ing}
    r = run_c4_c6(Rc, roles, intl_map)
    got = {"C6_coef_per_sd_per100": r["C6"]["coef_per_sd_per100"], "C4_r_true": r["C4"]["r_true"]}
    match = {k: round(got[k], 3) == EXPECTED[k] for k in EXPECTED}
    for k in EXPECTED:
        print(f"{k} (from snapshot): {got[k]:+.6f} -> rounds to {got[k]:+.3f}; BENCHMARK-v8: {EXPECTED[k]:+.3f} "
              f"-> {'MATCH' if match[k] else 'MISMATCH'}")
    SUMMARY_PATH.write_text(json.dumps({"expected": EXPECTED, "recomputed": got, "match": match,
                                        "C6": r["C6"], "C4": r["C4"]}, indent=2, default=str))


if __name__ == "__main__":
    main()
