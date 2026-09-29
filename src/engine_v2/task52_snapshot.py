"""
Task 52, Step 1: freeze BENCHMARK v9. docs/specs/task-52-tempo-development.md.

Runs BEFORE the development/replication split exists. First writes to disk
the per-unit tables that until now existed only in memory:
  - W 2015/16 and W study (task46_part_b.fit_w exactly as Task 46 / Task 51);
    asserted to reproduce Task 46's n and AUC;
  - Task 51's study tempo residuals WITH match/event ids (Task 39's recipe,
    rm.main redirected to a scratch folder so no earlier file is rewritten);
    asserted identical to tempo_redesign_*_residuals_v2.
Then copies the Task 50 and Task 51 JSONs and per-unit tables plus these
tables into data/benchmark_v9/ (copy only; data/ is gitignored) and writes
docs/benchmark/manifest-v9.txt (path, size, SHA-256). Same pattern as
task50_snapshot.py.

Run: python src/engine_v2/task52_snapshot.py
"""
import json
import shutil
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.append(str(Path(__file__).parent.parent / "tempo"))
import redesign_metrics_v2  # noqa: E402,F401 -- applies Task 26 Step 2's patch to redesign_metrics
import redesign_metrics as rm  # noqa: E402
import task44_build as tb  # noqa: E402
from task31_snapshot import sha256_of  # noqa: E402
from task46_part_b import fit_w  # noqa: E402
from task39_tempo_ptest import V2_MOVE, V2_HOLD  # noqa: E402
from task51_scorecard import w_study  # noqa: E402

REPO_ROOT = Path(__file__).parent.parent.parent
DATA = REPO_ROOT / "data"
SNAPSHOT_DIR = DATA / "benchmark_v9"
MANIFEST_PATH = REPO_ROOT / "docs" / "benchmark" / "manifest-v9.txt"
W16_PATH = DATA / "processed" / "engine_v2" / "task52_w_1516.parquet"
WST_PATH = DATA / "processed" / "engine_v2" / "task52_w_study.parquet"
TEMPO_IDS = {k: DATA / "processed" / f"tempo_task52_study_{k}_residuals_ids.parquet" for k in ("move", "hold")}
TASK46 = json.loads((DATA / "engine_v2_task46_part_b.json").read_text())
W_COLS = ["match_id", "event_id", "player_id", "team", "recv_x", "recv_y", "pressured_flag", "w"]

JSONS = ["engine_v2_task50_spotcheck.json", "engine_v2_task50_step2.json", "engine_v2_task50_step3.json",
         "engine_v2_task50_step4.json", "engine_v2_task51.json", "tempo_task51_redesign_rerun.json"]
PARQUETS = ["processed/scorecard_card_a.parquet", "processed/scorecard_card_b.parquet", "processed/scorecard_card_c.parquet",
            "processed/tempo_task51_metrics.parquet", "processed/tempo_task51_move_residuals.parquet",
            "processed/tempo_task51_hold_residuals.parquet",
            "processed/engine_v2/task52_w_1516.parquet", "processed/engine_v2/task52_w_study.parquet",
            "processed/tempo_task52_study_move_residuals_ids.parquet",
            "processed/tempo_task52_study_hold_residuals_ids.parquet"]
FILES = [(f"data/{j}", j) for j in JSONS] + [(f"data/{p}", p) for p in PARQUETS]
NEVER_WRITTEN = ["Task 50 per-unit tables: task50_puzzle / task50_robustness / task50_pooling wrote JSON summaries only"]


def write_missing_tables() -> dict:
    Rc = pd.read_parquet(tb.RECEPTIONS_PATH)
    W16, b16 = fit_w(Rc, tb.match_folds(sorted(Rc["match_id"].unique())))
    assert b16 == TASK46["W_1516"], (b16, TASK46["W_1516"])
    W16[W_COLS].to_parquet(W16_PATH)
    del Rc, W16
    Wst, bst = w_study()
    assert bst == TASK46["W_study"], (bst, TASK46["W_study"])
    Wst[W_COLS].to_parquet(WST_PATH)
    del Wst
    with tempfile.TemporaryDirectory() as tmp:
        rm.OUT_PATH = Path(tmp) / "metrics.parquet"
        rm.MOVE_RESID_PATH = Path(tmp) / "move.parquet"
        rm.HOLD_RESID_PATH = Path(tmp) / "hold.parquet"
        rm.SUMMARY_PATH = Path(tmp) / "summary.json"
        _, move_df, hold_df, _ = rm.main()
    for k, new, old_path in (("move", move_df, V2_MOVE), ("hold", hold_df, V2_HOLD)):
        old = pd.read_parquet(old_path)
        assert len(new) == len(old)
        assert (new["player_id"].values == old["player_id"].values).all()
        assert np.allclose(new["residual"].values, old["residual"].values, rtol=0, atol=1e-12)
        new[["match_id", "event_id", "player_id", "competition_id", "season_id", "residual"]].to_parquet(TEMPO_IDS[k])
    return {"W_1516": b16, "W_study": bst, "tempo_rows": {"move": len(move_df), "hold": len(hold_df)}}


def main():
    checks = write_missing_tables()
    print(f"  wrote missing tables: {checks}")
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    lines, missing = [], []
    for src_rel, dst_rel in FILES:
        src, dst = REPO_ROOT / src_rel, SNAPSHOT_DIR / dst_rel
        if not src.exists():
            missing.append(src_rel)
            print(f"  MISSING: {src_rel}")
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        assert sha256_of(src) == sha256_of(dst)
        lines.append(f"{dst_rel}\t{dst.stat().st_size}\t{sha256_of(dst)}\t(source: {src_rel})")
        print(f"  copied {src_rel}")
    MANIFEST_PATH.write_text("\n".join([
        "Task 52 -- BENCHMARK v9 manifest",
        "Format: <path relative to data/benchmark_v9/>\\t<size bytes>\\t<sha256>\\t(source path)",
        "", *lines, "",
        f"MISSING files (searched for, not found): {missing if missing else 'none'}",
        f"MISSING (never written): {NEVER_WRITTEN}",
        f"Written to disk in Task 52 Step 1 (were in memory only): task52_w_1516, task52_w_study (reproduce Task 46: "
        f"{checks['W_1516']}, {checks['W_study']}); tempo_task52_study_{{move,hold}}_residuals_ids (identical to v2 residuals)",
    ]) + "\n")
    print(f"{len(lines)} copied, {len(missing)} missing; wrote {MANIFEST_PATH}")


if __name__ == "__main__":
    main()
