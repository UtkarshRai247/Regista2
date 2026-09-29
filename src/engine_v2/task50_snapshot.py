"""
Task 50, Step 1: snapshot the artifacts behind results pages 44-48 into
data/benchmark_v8/ (copy only, never modify the originals; data/ is
gitignored). Record path/size/SHA-256 of every copied file in
docs/benchmark/manifest-v8.txt (committed); anything not found is listed
as MISSING. Same pattern as task40_snapshot.py.

Run: python src/engine_v2/task50_snapshot.py
"""
import shutil
from pathlib import Path

from task31_snapshot import sha256_of

REPO_ROOT = Path(__file__).parent.parent.parent
SNAPSHOT_DIR = REPO_ROOT / "data" / "benchmark_v8"
MANIFEST_PATH = REPO_ROOT / "docs" / "benchmark" / "manifest-v8.txt"

JSONS = [
    # Task 44
    "engine_v2_task44_step1.json", "engine_v2_task44_step2.json", "engine_v2_task44_step3.json",
    "engine_v2_task44_steps4_5.json", "tempo_task44_redesign.json", "tempo_task44_time_on_ball.json",
    # Task 45
    "engine_v2_task45.json",
    # Task 46
    "engine_v2_task46_part_a.json", "engine_v2_task46_part_b.json",
    # Task 47
    "engine_v2_task47.json",
    # Task 48
    "engine_v2_task48_ingest.json", "engine_v2_task48_build.json", "engine_v2_task48.json",
]
PARQUETS = [
    # Task 44: 2015/16 reception/spell table, passes, roles, tempo residuals
    "processed/engine_v2/task44_receptions.parquet", "processed/engine_v2/task44_passes.parquet",
    "processed/engine_v2/task44_roles.parquet",
    "processed/tempo_task44_metrics.parquet", "processed/tempo_task44_time_on_ball.parquet",
    "processed/tempo_task44_move_residuals.parquet", "processed/tempo_task44_hold_residuals.parquet",
    "processed/tempo_task44_move_residuals_ids.parquet", "processed/tempo_task44_hold_residuals_ids.parquet",
    # Task 46: study press-resistance flag table
    "processed/engine_v2/task46_study_pr_flag.parquet",
    # Task 48: built measures on the reserved data
    "processed/engine_v2/task48_receptions.parquet", "processed/engine_v2/task48_passes.parquet",
    "processed/engine_v2/task48_roles.parquet",
]
FILES = [(f"data/{j}", j) for j in JSONS] + [(f"data/{p}", p) for p in PARQUETS]
# Task 46's W tables (W16, Wst in task46_part_b.py) exist only in memory during that
# script; no file was ever written, so there is nothing to copy.
NEVER_WRITTEN = ["Task 46 W tables (2015/16 W16 and study Wst, task46_part_b.py): never written to disk"]


def main():
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
        "Task 50 -- BENCHMARK v8 manifest",
        "Format: <path relative to data/benchmark_v8/>\\t<size bytes>\\t<sha256>\\t(source path)",
        "", *lines, "",
        f"MISSING files (searched for, not found): {missing if missing else 'none'}",
        f"MISSING (never written): {NEVER_WRITTEN}",
    ]) + "\n")
    print(f"{len(lines)} copied, {len(missing)} missing; wrote {MANIFEST_PATH}")


if __name__ == "__main__":
    main()
