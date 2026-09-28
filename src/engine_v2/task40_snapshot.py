"""
Task 40, Step 2: snapshot the artifacts behind results pages 32-39 into
data/benchmark_v6/ (copy only, never modify the originals; data/ is
gitignored). Record path/size/SHA-256 of every copied file in
docs/benchmark/manifest-v6.txt (committed); anything not found is listed
as MISSING with the path searched. Same pattern as task31_snapshot.py.

Run: python src/engine_v2/task40_snapshot.py
"""
import shutil
from pathlib import Path

from task31_snapshot import sha256_of

REPO_ROOT = Path(__file__).parent.parent.parent
SNAPSHOT_DIR = REPO_ROOT / "data" / "benchmark_v6"
MANIFEST_PATH = REPO_ROOT / "docs" / "benchmark" / "manifest-v6.txt"

JSONS = [
    # Task 32
    *[f"engine_v2_task32_step{i}.json" for i in range(1, 7)],
    # Task 33
    "engine_v2_step2_crossfit_v6.json", "engine_v2_task33_step1.json", "engine_v2_task33_step3.json",
    "engine_v2_task33_step4a.json", "engine_v2_task33_step4b.json", "engine_v2_task33_step4c.json",
    "engine_v2_task33_step4d.json",
    # Task 34
    "engine_v2_task34_step1.json", "engine_v2_task34_step2_3.json",
    # Task 35
    "engine_v2_task35_step1.json", "engine_v2_task35_ptest.json",
    # Task 36
    "pff_task36_inventory.json", "pff_task36_players.json", "pff_task36_audit.json", "pff_task36_clock.json",
    # Task 37
    "engine_v2_task37_holdout_ptest.json",
    # Task 38
    "pff_task38_step1.json", "pff_task38_tests.json",
    # Task 39
    "engine_v2_task39_tempo_ptest.json", "tempo_task39_redesign_rerun.json",
]
FILES = [(f"data/{j}", j) for j in JSONS] + [
    ("data/processed/engine_v2/pass_der_crossfit_v5.parquet", "processed/engine_v2/pass_der_crossfit_v5.parquet"),
    ("data/processed/engine_v2/decision_v6.parquet", "processed/engine_v2/decision_v6.parquet"),  # Task 33 Decision_v6
    ("data/processed/engine_v2/task34_receptions.parquet", "processed/engine_v2/task34_receptions.parquet"),  # Task 34 RQ
    ("data/processed/engine_v2/task35_ptest_inputs.parquet", "processed/engine_v2/task35_ptest_inputs.parquet"),  # Task 35
    ("data/processed/engine_v2/value_model_rows_holdout.parquet", "processed/engine_v2/value_model_rows_holdout.parquet"),  # Task 37
    ("data/processed/pff/availability_moments.parquet", "processed/pff/availability_moments.parquet"),  # Task 38
    ("data/processed/pff/availability_receptions.parquet", "processed/pff/availability_receptions.parquet"),
    ("data/processed/pff/availability_dm_table.parquet", "processed/pff/availability_dm_table.parquet"),
    ("data/processed/tempo_task39_move_residuals.parquet", "processed/tempo_task39_move_residuals.parquet"),  # Task 39
    ("data/processed/tempo_task39_hold_residuals.parquet", "processed/tempo_task39_hold_residuals.parquet"),
]


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
        "Task 40 -- BENCHMARK v6 manifest",
        "Format: <path relative to data/benchmark_v6/>\\t<size bytes>\\t<sha256>\\t(source path)",
        "", *lines, "",
        f"MISSING files (searched for, not found): {missing if missing else 'none'}",
    ]) + "\n")
    print(f"{len(lines)} copied, {len(missing)} missing; wrote {MANIFEST_PATH}")


if __name__ == "__main__":
    main()
