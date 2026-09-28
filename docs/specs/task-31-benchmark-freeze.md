# Task 31 — Freeze the benchmark (engine v5)

Written 2026-09-28 by the research lead. Pure bookkeeping: no analysis,
no engine change. After this task, engine v5 can always be restored and
compared against.

## Step 0 — Commit this brief alone. Record the hash.

## Step 1 — Commit the research lead's documents
One commit containing `docs/BENCHMARK-v5.md`, `docs/CRITIQUE-v5.md`,
`docs/abstract/SSAC27-abstract-draft.md` (parked, not final),
`docs/specs/task-30-repo-public-prep.md` (parked, not to be run yet).
Do NOT stage `docs/JOURNAL.md`.

## Step 2 — Snapshot the artifacts
Copy, without modifying, into `data/benchmark_v5/` (not committed; data/
is ignored):
- value_model_for_v5.json, value_model_against_v5.json,
  pass_success_model_v3.json, the policy model file used by
  policy_score_v8.py, and the summary JSON holding temperature 0.1562
  and fill values;
- the offside rule R1_K10 definition/summary JSON;
- the Decision/Risk per-pass output behind step8_regate.py;
- leaderboard_v5c.parquet, task29_dm_shrunk.parquet,
  task27_dm_share.parquet;
- the summary JSONs behind results pages 25-29 (falsification,
  cross-fitted outcome validation, holdout, Study B, Tasks 27-29).
Do NOT copy the ~106M-row EV corpus; record its directory name, file
count and total size instead.
For every file copied, record path, size and SHA-256 in
`docs/benchmark/manifest-v5.txt` (committed). If any file named above
cannot be found, list it as MISSING with what you searched for.

## Step 3 — Tag
Create the annotated git tag `benchmark-v5` on the commit that contains
the manifest, message "Engine v5 benchmark — see docs/BENCHMARK-v5.md".
Do not push anything.

## Step 4 — Spot-check the snapshot
From the snapshot copies only (not the originals), reload and print:
T6 reliability at 200 passes, and the count of deep midfielders with
90% intervals entirely above the group mean. Both must equal
BENCHMARK-v5.md (0.8191; 2). If either cannot be recomputed from the
snapshot alone, say exactly what is missing.

## HARD RULES
- No code changes to the engine or analysis scripts.
- Do not push. Do not change repo visibility.
- No memory writes. Don't edit docs/JOURNAL.md. No interpretation.
- When finished, reply only that the task is done plus commit hashes.

## Output
docs/results/31-benchmark-freeze.md (template). Commit per rule 9.
