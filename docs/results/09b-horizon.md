# Task 09b: Horizon sensitivity retry

Date: 2026-09-22
Status: BLOCKED

## Per-section checklist (per brief docs/specs/task-09b-horizon.md)
- Step 0 (commit Amendment v2-7 alone): COMPLETE
- Step 1 (check the machine before starting): COMPLETE — and it
  correctly triggered the stop condition.
- Step 2 (resume horizon 5, then build horizon 15): **NOT RUN** — never
  started, per Step 1's own gate.
- Step 3 (recompute G/CI/P/L/PH-2, apply v2-6.2's rule): **NOT RUN** —
  depends on Step 2.
- Hard rules (frozen `build_match_rows_horizon` untouched, no other
  analysis, no memory writes, JOURNAL.md untouched, report partial
  progress honestly): COMPLETE for what ran.

## 1. Headline
The Step 1 preflight check found **1,746.56 MB of swap in use**
(limit: 1,024 MB) before any rebuild work started, so the script
stopped immediately, exactly as the brief instructs. No row-building,
model retraining, or recomputation ran. The horizon=5 cache from Task 09
(197 of 299 matches) is untouched and still resumable; horizon=15's
cache remains empty. This is the second consecutive time this machine
has been under enough memory pressure to block this specific
computation — see Section 5.

## 2. What I did
Reproduce with: `.venv/bin/python src/decision_engine/task09b_horizon.py`
(after Step 0's commit, done separately — see Section 7). Since Step 1
blocked immediately, this is also the complete run.

- **Step 0**: committed `docs/specs/analysis-plan-v2.md` (Amendment
  v2-7, 31 lines, already on disk) alone, in commit `ceafdcd`
  (`sha256 = 6763506804e306f17a195beec5772b31cd9c6636e7a04605a899c0ef9b046295`).
  Amendment v2-7.1 (the detectable-effect audit) is explicitly for
  Task 10, not this task, and was not acted on here.
- **Step 1**: wrote `src/decision_engine/task09b_horizon.py`, which
  parses `sysctl vm.swapusage` and `vm_stat` for the live swap-used and
  free-physical-page readings, and checks swap against the brief's
  1.0 GB preflight threshold before touching anything else. Ran it:
  swap was 1,746.56 MB, free physical pages 76.17 MB (page size 16,384
  bytes) — both readings consistent with genuine memory pressure, not a
  measurement artifact. The script stopped immediately per the hard
  rule, before Step 2's row-building loop, before importing/using
  `possession_value`'s XGBoost machinery for anything beyond feature-name
  constants, and before touching either cache directory.
- **Steps 2-3**: not started, per Step 1's own gate. The script does
  implement them (a resumable per-match-parquet loop over the
  *unmodified* `task09_horizon.build_match_rows_horizon`, re-checking
  swap every 50 matches against a 2.0 GB runtime limit, and — only if
  both horizons complete — refitting and reusing `task09_horizon`'s
  already-validated `build_ev_context_for_matches`/
  `recompute_ev_at_horizon`/`compute_g_p_l_ph2` to recompute G/CI/P/L/
  PH-2 and apply Amendment v2-6.2's fixed rule), but none of that code
  path executed this run.

## 3. Numbers

| Reading | Value | Threshold | Result |
|---|---|---|---|
| Swap in use (`sysctl vm.swapusage`) | 1,746.56 MB | 1,024 MB (1.0 GB) | **Exceeded — STOP** |
| Free physical pages (`vm_stat`) | 76.17 MB | (reported, not gated) | — |

Cache state (unchanged by this run): `data/processed/
possession_value_parts_h5/` = 197/299 matches; `data/processed/
possession_value_parts_h15/` = 0/299 matches.

## 4. Deviations from the brief
None. Step 1 was followed exactly: check first, stop above 1.0 GB,
do not start the rebuild under pressure.

## 5. Problems and surprises

- **This is the second time this exact machine has been too
  memory-constrained to run this computation** — Task 09 (2026-09-22,
  same day) hit swap usage of ~2.6 GB mid-run and was stopped there;
  this retry found 1.75 GB present even before starting anything. Both
  readings are well above what a fresh, idle system should show, which
  suggests the memory pressure is coming from other applications/
  processes on this machine persisting across sessions, not from
  anything in this project's own code (confirmed already in Task 09:
  the row-building function itself ran at 3.7 seconds/match on a clean
  system baseline). This is worth surfacing plainly rather than
  attempting another retry immediately: repeated automatic retries
  without the user first closing other applications (as the brief's
  Step 1 comment anticipates: "the user needs to close other
  applications first") would likely just hit the same gate again.
- Per Amendment v2-7.2's own contingency: "If it cannot complete, the
  paper states that horizon sensitivity was not testable within the
  available compute, and the 10-action horizon stands as an explicit,
  unvalidated assumption. It may not be quietly omitted." That
  contingency is now the operative state after two consecutive blocked
  attempts, until a future retry runs on a machine confirmed clear of
  this pressure.
- Nothing else was missing, broken, or malformed — the one thing this
  task asked to check first is exactly the thing that stopped it.

## 6. Questions for the research lead
1. Should a third retry be scheduled only after the user manually
   confirms low swap usage (e.g. `sysctl vm.swapusage` checked directly
   by the user before asking for a rerun), rather than this task
   retrying itself automatically? This task cannot make that scheduling
   call itself (CLAUDE.md rule 4), and per Amendment v2-7.2's own
   language, the alternative — reporting horizon sensitivity as
   "not testable within the available compute" and treating the
   10-action horizon as an explicit, unvalidated assumption in the
   paper — is already a valid, specified fallback if a further retry
   isn't warranted.

## 7. Files produced
- `data/task09b_horizon.json` — the blocked-run summary (swap/free-page
  readings). Gitignored.
- `src/decision_engine/task09b_horizon.py` — the retry script (ran only
  through Step 1 this time; Steps 2-3 are implemented and ready for a
  future rerun on a clear machine).
- No changes to `data/processed/possession_value_parts_h5/` or
  `possession_value_parts_h15/` — both left exactly as Task 09 left them.
- Git commits made this task: `ceafdcd` (Amendment v2-7), `950932f`
  (`docs/JOURNAL.md`, research lead's edit, same pattern as Tasks 05-09),
  `6023da9` (the new script and this results page, per CLAUDE.md item 9;
  this line was added in a follow-up edit since a commit cannot record
  its own hash — see Tasks 05-09's results pages for the same pattern).

## 8. Confidence
High. The only substantive action this task took was a machine-health
check, and it did exactly what the brief specified: read real swap
usage, compare against the stated threshold, and stop before any
expensive or resumable-but-risky work began. There is no analytical
claim to be uncertain about here — the finding is entirely about the
environment, not the science, and is reported as such.
