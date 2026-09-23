# Task 09b: Horizon sensitivity retry

Date: 2026-09-22
Status: COMPLETE

## Per-section checklist (per brief docs/specs/task-09b-horizon.md)
- Step 0 (commit Amendment v2-7 alone): COMPLETE
- Step 1 (check the machine before starting, live memory pressure): COMPLETE
- Step 2 (resume horizon 5, then build horizon 15): COMPLETE
- Step 3 (recompute G/CI/P/L/PH-2, apply v2-6.2's rule): COMPLETE
- Hard rules (frozen `build_match_rows_horizon` untouched, no other
  analysis, no memory writes, JOURNAL.md untouched, report partial
  progress honestly): COMPLETE

## 1. Headline
All 3 candidates that were ROBUST before cross-fitting
(`middle|leading`, `middle|level`, `middle|trailing`, all
`lateral_medium`) are **horizon-robust**: G stays positive with its 95%
CI excluding zero at both the 5-action and the 15-action horizon, per
Amendment v2-6.2's fixed rule. This is the first attempt of this task to
run to completion — the first attempt (same day, docs/results/
09b-horizon.md as it stood before this update) stopped at the Step 1
preflight gate on a swap-usage reading that the research lead
subsequently identified as the wrong signal (swap is never reclaimed by
macOS, so it reflects past pressure, not present headroom). This run
used the corrected live-memory-pressure gate instead and completed
without the gate tripping even once across both horizon rebuilds.

## 2. What I did
Reproduce with: `.venv/bin/python src/decision_engine/task09b_horizon.py`
(after Step 0, which needed no new commit this run — see below).

- **Step 0**: Amendment v2-7 was already committed unchanged from the
  first attempt at `ceafdcd` (`sha256 =
  6763506804e306f17a195beec5772b31cd9c6636e7a04605a899c0ef9b046295`),
  confirmed via `git diff` showing zero changes to
  `docs/specs/analysis-plan-v2.md` this session. No new commit was made
  for Step 0 since there was nothing to commit.
- **Step 1**: `docs/specs/task-09b-horizon.md` was updated (diffed
  against the copy read for the first attempt) to replace the swap-based
  gate with a live-memory-pressure gate: `memory_pressure`'s own
  "System-wide memory free percentage" line, and an "available memory"
  figure computed from `vm_stat` as `(free + inactive + purgeable)
  pages x page size`. Rewrote `task09b_horizon.py`'s machine-check
  functions accordingly (`get_free_pct`, `get_available_gb`) and reran
  the preflight check: **61% free, 4.90 GB available** — both comfortably
  clear the brief's thresholds (>=40% free AND >=3GB available), so the
  script proceeded.
- **Step 2**: resumed `data/processed/possession_value_parts_h5/` from
  its 197/299 cached matches (Task 09) — the loop skipped those and
  built the remaining 102 in 210.3s. Then built
  `possession_value_parts_h15/` from scratch (299/299) in 1,437.7s,
  using the same *unmodified* `task09_horizon.build_match_rows_horizon`
  Task 09 already verified byte-for-byte against the frozen horizon=10
  cache — this run did not touch that function. Re-checked live memory
  pressure every 50 matches processed in both loops; free% stayed in a
  63-66% band throughout (see Section 3), never approaching the 20%/1.5GB
  runtime floor.
- **Step 3**: for each of horizon 5 and 15, concatenated that horizon's
  full 299-match cache, fit one XGBoost model with `possession_value.py`'s
  exact hyperparameters (`n_estimators=300, max_depth=5,
  learning_rate=0.05, subsample=0.8, colsample_bytree=0.8,
  random_state=42`) and its own 80/20 split (`random_state=42`). Reused
  `task09_horizon.build_ev_context_for_matches`/`recompute_ev_at_horizon`/
  `compute_g_p_l_ph2` unchanged (including the population-restriction
  fix Task 09 needed — typed rows filtered to the EV table's own
  match/event population before `join_ev`, avoiding the group-size-
  mismatch bug Task 09 hit) to recompute G/CI/P/L/PH-2 for the 3 ROBUST
  candidates on the confirmation half, using frozen (non-cross-fitted)
  `p_success` throughout, per the brief. Pulled the frozen horizon=10
  numbers alongside via the same function. Applied Amendment v2-6.2's
  rule exactly: horizon-robust only if G>0 with CI excluding zero at
  BOTH 5 and 15.

## 3. Numbers

**Preflight and runtime memory readings** (all comfortably inside both
gates; none tripped):

| Point | Free % | Available |
|---|---|---|
| Preflight (before Step 2) | 61% | 4.90 GB |
| Horizon 5, after 50 processed (247/299 cached) | 63% | 5.65 GB |
| Horizon 5, after 100 processed (297/299 cached) | 64% | 5.27 GB |
| Horizon 15, after 50 | 64% | 5.47 GB |
| Horizon 15, after 100 | 63% | 5.62 GB |
| Horizon 15, after 150 | 65% | 5.47 GB |
| Horizon 15, after 200 | 66% | 5.36 GB |
| Horizon 15, after 250 | 65% | 5.24 GB |

Row-building wall time: horizon=5 (102 remaining matches) 210.3s;
horizon=15 (299 matches from scratch) 1,437.7s.

**G/CI/P/L/PH-2 for the 3 ROBUST candidates, confirmation half, non-cross-fitted (join: 320,666/320,666 matched, 100.0%, both horizons):**

| zone | state | type | horizon | held-out AUC | G | 95% CI | P | L | n_passes | PH-2 G | PH-2 95% CI | PH-2 n (share) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| middle | leading | lateral_medium | 5 | 0.8745 | 0.000236 | [0.000185, 0.000291] | 0.553 | 0.468 | 7941 | 0.000116 | [0.000030, 0.000207] | 2340 (29.5%) |
| middle | leading | lateral_medium | 10 (frozen) | — | 0.000678 | [0.000572, 0.000789] | 0.553 | 1.345 | 7941 | 0.000318 | [0.000135, 0.000500] | 2340 (29.5%) |
| middle | leading | lateral_medium | 15 | 0.7757 | 0.000917 | [0.000785, 0.001052] | 0.558 | 1.820 | 7941 | 0.000467 | [0.000243, 0.000700] | 2340 (29.5%) |
| middle | level | lateral_medium | 5 | 0.8745 | 0.000269 | [0.000233, 0.000303] | 0.547 | 0.427 | 12320 | 0.000120 | [0.000069, 0.000176] | 3677 (29.8%) |
| middle | level | lateral_medium | 10 (frozen) | — | 0.000788 | [0.000701, 0.000882] | 0.541 | 1.250 | 12320 | 0.000357 | [0.000237, 0.000508] | 3677 (29.8%) |
| middle | level | lateral_medium | 15 | 0.7757 | 0.000779 | [0.000682, 0.000876] | 0.538 | 1.236 | 12320 | 0.000239 | [0.000086, 0.000394] | 3677 (29.8%) |
| middle | trailing | lateral_medium | 5 | 0.8745 | 0.000536 | [0.000425, 0.000677] | 0.533 | 0.842 | 6608 | 0.000309 | [0.000093, 0.000529] | 1960 (29.7%) |
| middle | trailing | lateral_medium | 10 (frozen) | — | 0.001232 | [0.000991, 0.001497] | 0.534 | 1.933 | 6608 | 0.000644 | [0.000195, 0.001100] | 1960 (29.7%) |
| middle | trailing | lateral_medium | 15 | 0.7757 | 0.001003 | [0.000772, 0.001267] | 0.522 | 1.574 | 6608 | 0.000122 | [-0.000276, 0.000525] | 1960 (29.7%) |

**Amendment v2-6.2 verdicts:**

| zone | state | type | G>0, CI excl. 0 @5 | G>0, CI excl. 0 @15 | Verdict |
|---|---|---|---|---|---|
| middle | leading | lateral_medium | True | True | **horizon-robust** |
| middle | level | lateral_medium | True | True | **horizon-robust** |
| middle | trailing | lateral_medium | True | True | **horizon-robust** |

All 3 of 3 are horizon-robust. Note PH-2's CI for `middle|trailing` at
horizon=15 does include zero ([-0.000276, 0.000525]) — but v2-6.2's rule
is stated in terms of G's CI only, not PH-2's, so this does not change
the verdict; reported here in full per the hard rule against filtering.

## 4. Deviations from the brief
None in this run. Step 1 used the brief's corrected live-memory-pressure
gate exactly as specified (thresholds 40%/3GB preflight, 20%/1.5GB
runtime); Steps 2-3 followed the frozen row-building function and the
fixed v2-6.2 rule exactly.

## 5. Problems and surprises
- **The first attempt's swap-based block was a measurement problem, not
  a resource problem**, confirmed directly: this run's preflight check,
  taken shortly after the first attempt's, found the system with 61%
  free and 4.90GB available — healthy headroom — even though swap usage
  (had it still been checked) would likely have remained elevated from
  earlier sessions, since macOS does not reclaim written swap pages.
  This validates the research lead's v2-7.2 diagnosis exactly.
- **`held_out_auc` differs meaningfully by horizon**: 0.8745 at
  horizon=5, 0.7757 at horizon=15 — a shorter scoring window is an
  easier target to predict (fewer intervening events for randomness to
  intrude), which is expected and not itself informative about the
  Study A finding.
- The `middle|trailing` candidate's PH-2 confidence interval at
  horizon=15 crosses zero (unlike its horizon=5 and horizon=10 PH-2
  intervals, both of which exclude zero) — noted in Section 3. Since
  v2-6.2's rule is explicitly about G (not PH-2) at each horizon, this
  does not affect the horizon-robust verdict, but it is a real piece of
  variability worth carrying into any broader robustness discussion
  (e.g. if a future task revisits PH-2 across horizons specifically).
- Nothing else was missing, broken, or malformed.

## 6. Questions for the research lead
None. Amendment v2-6.2's rule was fixed and applied exactly; no
definition needed adjusting.

## 7. Files produced
- `data/processed/possession_value_parts_h5/` — now 299/299 (completed
  this run; was 197/299 after Task 09).
- `data/processed/possession_value_parts_h15/` — now 299/299 (built
  from scratch this run; was empty).
- `data/task09b_horizon.json` — full run summary (memory readings, both
  horizons' stats, horizon=10 comparison, verdicts). Gitignored.
- `src/decision_engine/task09b_horizon.py` — updated in place with the
  corrected live-memory-pressure gate (this is this task's own script
  from the first attempt, not a frozen upstream file, so editing it
  directly is appropriate; the protected `task09_horizon.
  build_match_rows_horizon` was never touched).
- Git commits made this task: no new commit for Amendment v2-7 (already
  committed at `ceafdcd` from the first attempt, confirmed unchanged).
  `805d7e3` covers the updated script, the updated brief
  (`docs/specs/task-09b-horizon.md`), and this results page, per
  CLAUDE.md item 9; this line was added in a follow-up edit since a
  commit cannot record its own hash — see Tasks 05-09's results pages
  for the same pattern. No `docs/JOURNAL.md` change was found this
  session.

## 8. Confidence
High. The corrected gate behaved exactly as intended (proceeded on
healthy readings, stayed well clear of both thresholds throughout), the
row-building function was reused completely unmodified from its
already-validated form, and the confirmation-half join matched 100.0%
for both horizons. The substantive finding — all 3 candidates
horizon-robust — is a clean, unambiguous application of a rule that was
fixed before this run started. The one soft spot is `middle|trailing`'s
horizon=15 PH-2 interval crossing zero, noted above; it doesn't change
the verdict under the rule as written; but it's real variability, not
hidden.
