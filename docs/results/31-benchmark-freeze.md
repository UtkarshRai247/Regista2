# Task 31: Freeze the benchmark (engine v5)
Date: 2026-09-28
Status: COMPLETE

## Section checklist
- Step 0 (commit brief alone): COMPLETE
- Step 1 (commit the research lead's documents): COMPLETE
- Step 2 (snapshot the artifacts): COMPLETE -- 31/31 files found, 0 missing
- Step 3 (tag): COMPLETE
- Step 4 (spot-check the snapshot): COMPLETE -- both values match BENCHMARK-v5.md exactly

## 1. Headline
All 31 named artifacts were found and copied into `data/benchmark_v5/`
with recorded path/size/SHA-256 in `docs/benchmark/manifest-v5.txt`
(committed); none were missing. The ~106M-row EV corpus
(`options_ev_v4`) was not copied, per the brief -- its directory, file
count (292), and total size (4,507,814,882 bytes, ~4.2GB) are recorded
instead. The annotated tag `benchmark-v5` was created on the commit
containing the manifest. Both spot-check numbers, recomputed from the
snapshot copies only, match `docs/BENCHMARK-v5.md` exactly: T6
reliability at 200 passes = 0.8191, and 2 deep midfielders' 90%
intervals lie entirely above the group mean.

## 2. What I did
1. Committed `task-31-benchmark-freeze.md` alone (Step 0).
2. Committed the four named research-lead documents in one commit
   (Step 1): `docs/BENCHMARK-v5.md`, `docs/CRITIQUE-v5.md`,
   `docs/abstract/SSAC27-abstract-draft.md`,
   `docs/specs/task-30-repo-public-prep.md`. `docs/JOURNAL.md`
   (pre-existing modification) and two other untracked files not named
   in this task's Step 1 (`AGENTS.md`, `docs/specs/task-32-critique-diagnostics.md`)
   were left out of every commit in this task.
3. `task31_snapshot.py` (Step 2): copied the 31 named artifacts into
   `data/benchmark_v5/` (mirroring each file's original relative path
   for traceability), computed SHA-256 for each, wrote
   `docs/benchmark/manifest-v5.txt`, and recorded the EV corpus's own
   directory name/file count/total size without copying it.
4. Created the annotated git tag `benchmark-v5` (Step 3) on the commit
   containing the manifest, message "Engine v5 benchmark — see
   docs/BENCHMARK-v5.md". Not pushed.
5. `task31_spotcheck.py` (Step 4): reloaded ONLY from the snapshot
   copies (`data/benchmark_v5/`), recomputed T6 reliability at 200
   passes from the snapshotted `pass_der_v8.parquet` (same
   `reliability_sweep` definition `step8_regate.py` uses) and the
   deep-midfield above/below-mu_w count from the snapshotted
   `task29_dm_shrunk.parquet` (recomputing mu_w via the same
   precision-weighted formula `task29_step1_2.py` uses, not reading a
   cached value), and compared both against `BENCHMARK-v5.md`.

Reproduce with (from `src/engine_v2/`, `.venv` activated):
`python task31_snapshot.py && python task31_spotcheck.py`.

## 3. Step 2 -- the snapshot

### File list resolution (disclosed operationalization)
Two of the brief's bullets named a file by DESCRIPTION rather than an
exact path; both were resolved to one concrete file (or two, where the
brief itself used "definition/summary"), disclosed here rather than
guessed silently:
- "the policy model file used by `policy_score_v8.py`" ->
  `data/processed/engine_v2/policy_model.json` (the path
  `policy_score_v8.py` imports, unchanged, from
  `policy_baseline_fix.POLICY_MODEL_PATH`).
- "the offside rule R1_K10 definition/summary JSON" -> BOTH
  `src/engine_v2/offside_v4.py` (the code defining
  `SELECTED_K=10`/`SELECTED_M=0`/`SELECTED_ATTACKING_HALF_ONLY=False`)
  AND `data/engine_v2_step2_offside_calibration_v3.json` (the
  calibration run that selected R1_K10 as the winning rule).
- "the summary JSONs behind results pages 25-29" was read as the FULL
  set of summary JSONs each page's own numbers are drawn from, not only
  the four analyses named in the parenthetical -- since the brief
  separately says "Tasks 27-29" wholesale for those three pages, the
  same completeness was applied to Tasks 25-26's own additional
  analyses (tempo, threshold, leaderboard, correlations) that the
  parenthetical does not individually name. All 20 such files were
  found; none reported as missing.

### Files copied (31 total, 0 missing)
| category | files |
|---|---|
| Value/pass-success/policy models | `value_model_for_v5.json`, `value_model_against_v5.json`, `pass_success_model_v3.json`, `policy_model.json` |
| Temperature + fill values | `engine_v2_step3_policy_baseline_fix_v5.json` |
| Offside rule | `offside_v4.py`, `engine_v2_step2_offside_calibration_v3.json` |
| Decision/Risk per-pass | `pass_der_v8.parquet` |
| Player tables | `leaderboard_v5c.parquet`, `task29_dm_shrunk.parquet`, `task27_dm_share.parquet` |
| Task 25 (falsification, cross-fitted outcome validation) | `engine_v2_step5_falsification_v3.json`, `engine_v2_step6_crossfit_v5.json`, `engine_v2_step6_outcome_validation_crossfit_v5.json` |
| Task 26 (holdout, tempo, threshold, leaderboard, correlations, Study B) | `engine_v2_task26_holdout_evidence.json`, `engine_v2_task26_step1b_options_holdout.json`, `engine_v2_task26_step1b_policy_holdout.json`, `engine_v2_task26_step1c_outcome_validation_holdout.json`, `tempo_step2b_redesign_v2.json`, `tempo_step3b_reliability_v2.json`, `engine_v2_task26_step3_threshold.json`, `engine_v2_task26_step4_leaderboard.json`, `engine_v2_task26_step5_correlations.json`, `engine_v2_task26_step6_recovery.json`, `engine_v2_task26_step6_study_b.json` |
| Task 27 | `engine_v2_task27_step1_deep_midfield.json`, `engine_v2_task27_step2_4_tables.json`, `engine_v2_task27_step3_studyb_sensitivity.json` |
| Task 28 | `engine_v2_task28_step1_2.json` |
| Task 29 | `engine_v2_task29_step1_2.json`, `engine_v2_task29_step3.json` |

Every file's path, size, and SHA-256 are in `docs/benchmark/manifest-v5.txt`
(committed) -- not reproduced in full here to avoid duplicating a
32-line manifest inside a results page.

### EV corpus (not copied)
| quantity | value |
|---|---|
| directory | `data/processed/engine_v2/options_ev_v4` |
| file count | 292 |
| total size | 4,507,814,882 bytes (~4.20 GB) |

## 4. Step 3 -- tag
Annotated tag `benchmark-v5` created locally on the commit containing
`docs/benchmark/manifest-v5.txt`, message "Engine v5 benchmark — see
docs/BENCHMARK-v5.md". Not pushed, per the hard rule.

## 5. Step 4 -- spot-check (from the snapshot copies only)
| quantity | recomputed from snapshot | BENCHMARK-v5.md | match |
|---|---|---|---|
| T6 reliability at 200 passes | 0.8191 | 0.8191 | YES |
| Deep-midfield intervals entirely above group mean | 2 | 2 | YES |

Both numbers were recomputed from scratch using only the files under
`data/benchmark_v5/` (T6 via `pass_der_v8.parquet`'s own per-pass rows,
re-running the exact split-half procedure; the above/below count via
`task29_dm_shrunk.parquet`'s own `m_i`/`v_i_within_group` columns,
recomputing the precision-weighted mu_w rather than trusting a cached
field) -- neither the live originals nor any other results-page JSON
were read for this step. Nothing was missing.

## 6. `git diff --stat`
No pre-existing tracked file was modified. New files only:
```
 src/engine_v2/task31_snapshot.py   | new
 src/engine_v2/task31_spotcheck.py  | new
 docs/benchmark/manifest-v5.txt     | new (committed)
 docs/BENCHMARK-v5.md               | new (committed, Step 1)
 docs/CRITIQUE-v5.md                | new (committed, Step 1)
 docs/abstract/SSAC27-abstract-draft.md | new (committed, Step 1)
 docs/specs/task-30-repo-public-prep.md | new (committed, Step 1)
```
`docs/JOURNAL.md` was left untouched throughout, per the hard rule.
`data/benchmark_v5/` (the actual snapshot copies) is under `data/`,
gitignored, and never committed.

## 7. Deviations from the brief
None from the hard rules. Two disclosed resolutions of description-not-
path bullets and one disclosed operationalization of "the summary JSONs
behind results pages 25-29" are documented in Section 3, not silently
assumed.

## 8. Problems and surprises
None. Every named file existed exactly where expected; the spot-check
matched the benchmark document on the first run with no discrepancy to
investigate.

## 9. Questions for the research lead
None -- this was pure bookkeeping with no ambiguity requiring a
methodology decision, beyond the two disclosed path resolutions in
Section 3.

## 10. Files produced
- `src/engine_v2/task31_snapshot.py` -- new. Copies the 31 named
  artifacts into `data/benchmark_v5/`, writes the SHA-256 manifest,
  records the EV corpus's own size/file-count without copying it.
- `src/engine_v2/task31_spotcheck.py` -- new. Recomputes T6 and the
  deep-midfield above/below count from the snapshot copies only.
- `docs/benchmark/manifest-v5.txt` -- new, committed. Path/size/SHA-256
  for all 31 snapshotted files.
- `data/benchmark_v5/` -- new snapshot directory (31 files; not
  committed, `data/` is never committed).
- `data/engine_v2_task31_snapshot.json`, `data/engine_v2_task31_spotcheck.json`
  -- new summary JSONs (also under `data/`, not committed).
- `docs/BENCHMARK-v5.md`, `docs/CRITIQUE-v5.md`,
  `docs/abstract/SSAC27-abstract-draft.md`,
  `docs/specs/task-30-repo-public-prep.md` -- committed in Step 1 (the
  research lead's own documents, not authored by this task).
- Git tag `benchmark-v5` (annotated, local only, not pushed).
- `docs/results/31-benchmark-freeze.md` -- this file.
- Commit hashes: `d7a6202` (Step 0, brief alone), `4a2b6fc` (Step 1,
  the four research-lead documents), `<pending>` (this results page +
  Step 2/4 code + manifest -- the commit the `benchmark-v5` tag points
  to) -- to be filled in a follow-up commit per CLAUDE.md rule 9.

## 11. Confidence
High confidence throughout: this is bookkeeping with a built-in,
independent verification step (Step 4), and that verification passed
exactly on the first attempt with no discrepancy between the snapshot
and the benchmark document. The only judgment calls made (Section 3's
two path resolutions and one scope operationalization) are disclosed
plainly rather than left implicit. No weak link identified.
