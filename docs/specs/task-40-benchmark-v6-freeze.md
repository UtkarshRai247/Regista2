# Task 40 — Freeze BENCHMARK v6

Written 2026-09-28 by the research lead. Bookkeeping only, like Task 31.

## Step 0 — Commit this brief alone. Record the hash.

## Step 1 — Commit docs
One commit with `docs/BENCHMARK-v6.md` and `docs/CRITIQUE-v6.md`
(if not already committed). Do NOT stage `docs/JOURNAL.md` or AGENTS.md.

## Step 2 — Snapshot
Copy, unmodified, into `data/benchmark_v6/` (not committed): the summary
JSONs behind results pages 32-39; `pass_der_crossfit_v5.parquet`; the
Task 33 Decision_v6 per-pass output; the Task 34 per-reception RQ output;
the Task 35 and 37 P-test inputs/outputs; the Task 38
`availability_moments.parquet`, `availability_receptions.parquet`,
`availability_dm_table.parquet`; the Task 39 regenerated tempo residual
files. Record path, size and SHA-256 of each in
`docs/benchmark/manifest-v6.txt` (committed). List anything not found
as MISSING with what was searched.

## Step 3 — Tag
Annotated tag `benchmark-v6` on the commit with the manifest, message
"Benchmark v6 — see docs/BENCHMARK-v6.md". Do not push.

## Step 4 — Spot-check from the snapshot only
Recompute and print: the Task 35 study v5 Decision P-test coefficient
(+0.000747 per pass) and the Task 38 deep-midfield count above / below
the mean (12 / 14). Both must match BENCHMARK-v6.md.

## HARD RULES
- No analysis changes. Do not push or change visibility.
- No memory writes. Don't edit docs/JOURNAL.md. No interpretation.
- When finished, reply only that the task is done plus commit hashes.

## Output
docs/results/40-benchmark-v6-freeze.md (template). Commit per rule 9.
