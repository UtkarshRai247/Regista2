# Task 40: Freeze BENCHMARK v6
Date: 2026-09-28
Status: COMPLETE (every section run; one deviation, which the author decided, in Section 4)

## Checklist
| Section | Status |
|---|---|
| Step 0 — commit brief alone | COMPLETE (b603012) |
| Step 1 — commit BENCHMARK-v6.md and CRITIQUE-v6.md | COMPLETE: already committed by the research lead in 2d283d6, so no new commit was needed. JOURNAL.md and AGENTS.md were not staged. |
| Step 2 — snapshot + manifest | COMPLETE (36 files, 0 MISSING) |
| Step 3 — annotated tag `benchmark-v6` | COMPLETE (on 2b5e86f; not pushed) |
| Step 4 — spot-check from the snapshot only | COMPLETE (both MATCH) |

## 1. Headline
BENCHMARK v6 is frozen: 36 artifacts (128 MB) copied into `data/benchmark_v6/`, with SHA-256 checksums in `docs/benchmark/manifest-v6.txt`. The annotated tag `benchmark-v6` is on 2b5e86f and has not been pushed.
Both spot-checks, recomputed from the snapshot copies only, match BENCHMARK-v6.md:
- Task 35's v5 Decision P-test coefficient is +0.0007469385 per pass (+0.0747 per 100).
- Task 38's deep-midfield count above / below the mean is 12 / 14.

## 2. What I did
1. **Step 0:** committed `docs/specs/task-40-benchmark-v6-freeze.md` alone (b603012). The untracked Task 41 brief, JOURNAL.md and AGENTS.md were left unstaged.
2. **Step 1:** `docs/BENCHMARK-v6.md` and `docs/CRITIQUE-v6.md` were already committed in 2d283d6 (research lead).
3. **Task 35 inputs:** `.venv/bin/python src/engine_v2/task40_persist_task35_inputs.py` persisted Task 35's per-pass P-test inputs (see Section 4). It asserts that Task 35's own (a) and control coefficient and SE reproduce exactly: coef 0.0007469384836865591 / SE 0.00024360166295770252, and coef 0.02201331162937713 / SE 0.0020560019431378317. It wrote `data/processed/engine_v2/task35_ptest_inputs.parquet` (239,588 rows).
4. **Step 2:** `.venv/bin/python src/engine_v2/task40_snapshot.py` uses the Task 31 pattern and reuses `task31_snapshot.sha256_of`. It copies with `shutil.copy2`, asserts each copy's SHA-256 equals its source, and writes the manifest.
5. **Step 3:** committed the manifest and the two scripts (2b5e86f), then ran `git tag -a benchmark-v6 -m "Benchmark v6 — see docs/BENCHMARK-v6.md"`. Not pushed.
6. **Step 4:** `.venv/bin/python src/engine_v2/task40_spotcheck.py` reads only the `data/benchmark_v6/` copies.
- **Reproduce:** the three scripts above, in that order.

## 3. Numbers

### Snapshot contents (all found; full sizes and checksums in `docs/benchmark/manifest-v6.txt`)

| Source | Files |
|---|---|
| Summary JSONs, results 32-39 | Task 32 step1-6 (6); Task 33: engine_v2_step2_crossfit_v6, task33_step1, step3, step4a-d (7); Task 34 step1, step2_3 (2); Task 35 step1, ptest (2); Task 36 inventory, players, audit, clock (4); Task 37 holdout_ptest (1); Task 38 step1, tests (2); Task 39 tempo_ptest and tempo_task39_redesign_rerun (2) |
| `pass_der_crossfit_v5.parquet` | 22,178,680 bytes |
| Task 33 Decision_v6 per-pass: `decision_v6.parquet` | 18,424,196 |
| Task 34 per-reception RQ: `task34_receptions.parquet` | 18,973,234 |
| Task 35 P-test inputs: `task35_ptest_inputs.parquet` (new; see Section 4) | 16,581,673 |
| Task 37 P-test inputs: `value_model_rows_holdout.parquet` | 23,500,058 |
| Task 35 and 37 P-test outputs | the ptest JSONs above |
| Task 38: `availability_moments`, `availability_receptions`, `availability_dm_table` | 28,163,398 / 598,216 / 10,891 |
| Task 39 regenerated tempo residuals: move, hold | 1,968,275 / 2,246,535 |

Total: 36 files, 128 MB. MISSING: none.

### Step 4 — spot-check (snapshot copies only; both recomputed, not read off a stored value)

| Quantity | Recomputed from snapshot | BENCHMARK-v6.md | Result |
|---|---|---|---|
| Task 35 study v5 Decision P-test coefficient | +0.0007469385 per pass (+0.0747 per 100) | +0.0747 per 100 (the brief's +0.000747 per pass) | MATCH |
| Task 38 DM above / below group mean | 12 / 14 (of 59) | 12 / 14 | MATCH |

## 4. Deviations from the brief
- **Task 35's per-pass P-test inputs did not exist.** Task 35 computed Y, g_oof and roles in memory and saved only summary JSONs. The spot-check could not recompute the coefficient "from the snapshot only" with the files listed. I asked, and the author chose to persist the inputs, then recompute. I regenerated them with Task 35's own code on identical inputs (the same rebuild Task 39 used), asserted Task 35's saved results reproduce to 1e-9, and added the file to the snapshot. This is a new file, not a copy of a pre-existing Task 35 artifact.
- **Task 38 spot-check:** the DM player set comes from the snapshot's `availability_dm_table.parquet`. The counts were recomputed from `availability_moments.parquet` with Task 29's method, not taken from the table's interval columns.
- **Step 1:** there was no new docs commit, because both documents were already committed (2d283d6).

## 5. Problems and surprises
- None beyond the missing Task 35 inputs above.

## 6. Questions for the research lead
- None.

## 7. Files produced
- `src/engine_v2/task40_persist_task35_inputs.py`, `src/engine_v2/task40_snapshot.py`, `src/engine_v2/task40_spotcheck.py`.
- `docs/benchmark/manifest-v6.txt`.
- `data/benchmark_v6/` (36 files, not committed).
- `data/processed/engine_v2/task35_ptest_inputs.parquet` (not committed).
- `data/engine_v2_task40_spotcheck.json` (not committed).
- Side effects:
  - The local annotated tag `benchmark-v6` (not pushed).
  - No memory writes; JOURNAL.md and AGENTS.md untouched; the Task 41 brief left untracked.
- Commits: brief b603012; manifest and tag target 2b5e86f; this page: recorded in a follow-up commit.

## 8. Confidence
- Every snapshot copy is checksum-verified against its source.
- Both benchmark numbers recompute from the snapshot alone.
- The Task 35 input file is regenerated rather than original, but its exact reproduction of Task 35 is asserted in code.
