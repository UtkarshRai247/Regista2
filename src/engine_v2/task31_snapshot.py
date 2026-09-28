"""
Task 31, Step 2: snapshot engine v5's artifacts into data/benchmark_v5/
(copy only, never modify the originals; data/ is gitignored, this
directory is not committed itself). Record path/size/SHA-256 for every
file copied into docs/benchmark/manifest-v5.txt (committed). The
~106M-row EV corpus (options_ev_v4) is NOT copied -- its directory
name, file count and total size are recorded instead.

File list, exactly as the brief specifies, resolved to concrete paths
(each existence-checked; anything missing is listed as MISSING with
what was searched for, not silently skipped):
  - value_model_for_v5.json, value_model_against_v5.json,
    pass_success_model_v3.json (data/processed/engine_v2/)
  - the policy model file used by policy_score_v8.py
    (policy_model.json, per policy_baseline_fix.POLICY_MODEL_PATH,
    which policy_score_v8.py imports unchanged)
  - the summary JSON holding temperature 0.1562 and fill values
    (engine_v2_step3_policy_baseline_fix_v5.json)
  - the offside rule R1_K10 definition (src/engine_v2/offside_v4.py,
    the code that defines SELECTED_K/M/ATTACKING_HALF_ONLY) and its
    summary JSON (engine_v2_step2_offside_calibration_v3.json, which
    recorded R1_K10 as the winning rule)
  - the Decision/Risk per-pass output behind step8_regate.py
    (pass_der_v8.parquet)
  - leaderboard_v5c.parquet, task29_dm_shrunk.parquet,
    task27_dm_share.parquet
  - the summary JSONs behind results pages 25-29: this is read as the
    FULL set of summary JSONs each page's own numbers are drawn from
    (not just the parenthetical's four named analyses), since the
    brief separately says "Tasks 27-29" wholesale for those three
    pages -- disclosed as the operationalization used, in the results
    page.

Run: python src/engine_v2/task31_snapshot.py
"""
import hashlib
import json
import shutil
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

REPO_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = REPO_ROOT / "data"
SNAPSHOT_DIR = DATA_DIR / "benchmark_v5"
MANIFEST_PATH = REPO_ROOT / "docs" / "benchmark" / "manifest-v5.txt"
EV_CORPUS_DIR = DATA_DIR / "processed" / "engine_v2" / "options_ev_v4"

# (source path relative to REPO_ROOT, destination path relative to SNAPSHOT_DIR, what-searched-for note)
FILES = [
    ("data/processed/engine_v2/value_model_for_v5.json", "processed/engine_v2/value_model_for_v5.json"),
    ("data/processed/engine_v2/value_model_against_v5.json", "processed/engine_v2/value_model_against_v5.json"),
    ("data/processed/engine_v2/pass_success_model_v3.json", "processed/engine_v2/pass_success_model_v3.json"),
    ("data/processed/engine_v2/policy_model.json", "processed/engine_v2/policy_model.json"),
    ("data/engine_v2_step3_policy_baseline_fix_v5.json", "engine_v2_step3_policy_baseline_fix_v5.json"),
    ("src/engine_v2/offside_v4.py", "src_engine_v2/offside_v4.py"),
    ("data/engine_v2_step2_offside_calibration_v3.json", "engine_v2_step2_offside_calibration_v3.json"),
    ("data/processed/engine_v2/pass_der_v8.parquet", "processed/engine_v2/pass_der_v8.parquet"),
    ("data/processed/leaderboard_v5c.parquet", "processed/leaderboard_v5c.parquet"),
    ("data/processed/engine_v2/task29_dm_shrunk.parquet", "processed/engine_v2/task29_dm_shrunk.parquet"),
    ("data/processed/engine_v2/task27_dm_share.parquet", "processed/engine_v2/task27_dm_share.parquet"),
    # Task 25 (falsification, cross-fitted outcome validation)
    ("data/engine_v2_step5_falsification_v3.json", "engine_v2_step5_falsification_v3.json"),
    ("data/engine_v2_step6_crossfit_v5.json", "engine_v2_step6_crossfit_v5.json"),
    ("data/engine_v2_step6_outcome_validation_crossfit_v5.json", "engine_v2_step6_outcome_validation_crossfit_v5.json"),
    # Task 26 (holdout, tempo, threshold, leaderboard, correlations, Study B)
    ("data/engine_v2_task26_holdout_evidence.json", "engine_v2_task26_holdout_evidence.json"),
    ("data/engine_v2_task26_step1b_options_holdout.json", "engine_v2_task26_step1b_options_holdout.json"),
    ("data/engine_v2_task26_step1b_policy_holdout.json", "engine_v2_task26_step1b_policy_holdout.json"),
    ("data/engine_v2_task26_step1c_outcome_validation_holdout.json", "engine_v2_task26_step1c_outcome_validation_holdout.json"),
    ("data/tempo_step2b_redesign_v2.json", "tempo_step2b_redesign_v2.json"),
    ("data/tempo_step3b_reliability_v2.json", "tempo_step3b_reliability_v2.json"),
    ("data/engine_v2_task26_step3_threshold.json", "engine_v2_task26_step3_threshold.json"),
    ("data/engine_v2_task26_step4_leaderboard.json", "engine_v2_task26_step4_leaderboard.json"),
    ("data/engine_v2_task26_step5_correlations.json", "engine_v2_task26_step5_correlations.json"),
    ("data/engine_v2_task26_step6_recovery.json", "engine_v2_task26_step6_recovery.json"),
    ("data/engine_v2_task26_step6_study_b.json", "engine_v2_task26_step6_study_b.json"),
    # Task 27
    ("data/engine_v2_task27_step1_deep_midfield.json", "engine_v2_task27_step1_deep_midfield.json"),
    ("data/engine_v2_task27_step2_4_tables.json", "engine_v2_task27_step2_4_tables.json"),
    ("data/engine_v2_task27_step3_studyb_sensitivity.json", "engine_v2_task27_step3_studyb_sensitivity.json"),
    # Task 28
    ("data/engine_v2_task28_step1_2.json", "engine_v2_task28_step1_2.json"),
    # Task 29
    ("data/engine_v2_task29_step1_2.json", "engine_v2_task29_step1_2.json"),
    ("data/engine_v2_task29_step3.json", "engine_v2_task29_step3.json"),
]


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    print("Task 31 Step 2: snapshotting engine v5's artifacts ...")
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)

    manifest_lines = []
    missing = []
    for src_rel, dst_rel in FILES:
        src = REPO_ROOT / src_rel
        dst = SNAPSHOT_DIR / dst_rel
        if not src.exists():
            print(f"  MISSING: {src_rel}")
            missing.append(src_rel)
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        size = dst.stat().st_size
        digest = sha256_of(dst)
        manifest_lines.append(f"{dst_rel}\t{size}\t{digest}\t(source: {src_rel})")
        print(f"  copied {src_rel} -> data/benchmark_v5/{dst_rel} ({size} bytes)")

    ev_files = sorted(EV_CORPUS_DIR.glob("*.parquet")) if EV_CORPUS_DIR.exists() else []
    ev_total_size = sum(f.stat().st_size for f in ev_files)
    ev_note = f"NOT COPIED: {EV_CORPUS_DIR.relative_to(REPO_ROOT)} -- {len(ev_files)} files, {ev_total_size} bytes total"
    print(f"  {ev_note}")

    manifest_text = "\n".join([
        "Task 31 -- engine v5 benchmark manifest",
        "Format: <path relative to data/benchmark_v5/>\\t<size bytes>\\t<sha256>\\t(source path)",
        "",
        *manifest_lines,
        "",
        ev_note,
        "",
        f"MISSING files (searched for, not found): {missing if missing else 'none'}",
    ])
    MANIFEST_PATH.write_text(manifest_text + "\n")
    print(f"\nWrote {MANIFEST_PATH}")

    summary = {
        "n_files_copied": len(manifest_lines), "n_missing": len(missing), "missing": missing,
        "ev_corpus_dir": str(EV_CORPUS_DIR.relative_to(REPO_ROOT)), "ev_corpus_n_files": len(ev_files),
        "ev_corpus_total_bytes": ev_total_size,
    }
    (DATA_DIR / "engine_v2_task31_snapshot.json").write_text(json.dumps(summary, indent=2, default=str))
    print(json.dumps(summary, indent=2, default=str))
    return summary


if __name__ == "__main__":
    main()
