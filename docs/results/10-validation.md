# Task 10: Interval validity, outcome validation, detectable-effect audit
Date: 2026-09-22
Status: PARTIAL (Part A complete; Parts B and C in progress)

## Per-section checklist (per brief docs/specs/task-10-validation.md)
- Step 0 (confirm plan SHA-256 unchanged from ceafdcd): COMPLETE
- Part A (Study B interval method by simulated coverage, v2-6.1): COMPLETE
- Part B (outcome validation, v2-6.3): NOT RUN
- Part C (detectable-effect audit, v2-7.1): NOT RUN
- Hard rules (no changed definitions, full tables, no interpretation for
  the paper, no memory writes, JOURNAL.md untouched): COMPLETE for the
  work done so far.

## 1. Headline
[Placeholder — finalized once Parts B and C are run. Part A: the
previously-used cluster-bootstrap interval method severely undercovers
(10% of 100 simulations contained the true S), confirming Amendment
v2-6.1's diagnosis that it was invalid. Parametric bootstrap and
profile-likelihood both reached 93% coverage — below the 95% target —
and tied exactly, a tie the code resolved by list order rather than a
specified rule (Section 6). Under either candidate, Study B's Tier 1
verdict changes from NOT ALLOWED (Task 08, invalid interval) to ALLOWED;
Tier 2 remains NOT ALLOWED under both.]

## 2. What I did

### Part A
Reproduce with: `.venv/bin/python src/decision_engine/task10_partA_interval.py`
(then, for the tie-break addendum below, `.venv/bin/python
src/decision_engine/task10_partA_tiebreak.py`).

- Added `profile_likelihood_ci_S` to `src/decision_engine/reml_crossed.py`:
  reparametrizes `(var_player, var_team)` as `(S, total_var)`, profiles
  out `total_var` by bounded 1-D search over `log(total_var)` at each
  candidate `S` (reusing the module's existing sparse REML objective),
  then solves for the two `S` values where the profile deviance crosses
  `chi2(1, 0.95)` above the MLE deviance.
- Implemented all three candidate methods in
  `src/decision_engine/task10_partA_interval.py`: (i) cluster bootstrap
  with fresh ids (Task 08's fix, `reml_crossed.bootstrap_by_player`),
  (ii) parametric bootstrap (`reml_crossed.simulate_units` from the
  fitted variances, refit, percentile), (iii) profile likelihood.
- Ran the coverage test: 100 simulated datasets on the real 1,701-unit
  design at the fitted variances (var_player=4.9024e-7,
  var_team=2.5967e-7, true S=0.653732), B=200 bootstrap draws per
  simulation for methods (i) and (ii), per the task brief. Checkpointed
  at sim 25 (elapsed 1,782s, projected total 7,128s = 1.98h) — under the
  2-hour budget, so continued to the full 100 (did not cut to 50).
  Actual total: 7,039s (~1.96h).
- Selected PRIMARY = method with coverage closest to 0.95 among those
  >=0.90. Built all three intervals on the real `study_b_units.parquet`,
  then re-applied the fixed v2-5.4 Tier 1/Tier 2 rules using PRIMARY.
- **Found a tie**: methods (ii) and (iii) both reached exactly 0.93
  coverage (both 0.02 from 0.95). The brief specifies the selection rule
  but not a tie-break; the code's `select_primary()` resolves ties via
  `min()` over a fixed `("i","ii","iii")` iteration order, which returns
  (ii) — an implementation-order artifact, not a considered rule. Wrote
  `src/decision_engine/task10_partA_tiebreak.py` to compute PH-B1/PH-B3/
  tier verdicts under the untied alternate, (iii), reusing the same real
  fit and unit subsets, so this is disclosed with full information
  rather than silently resolved (Section 6).

### Part B / Part C
Scripts (`src/decision_engine/task10_partB_outcome.py`,
`src/decision_engine/task10_partC_mde_audit.py`) are written but not yet
run — updating this page once they complete.

## 3. Numbers

### Part A — coverage test (100 simulations, B=200 bootstrap draws each)

| Method | Coverage (target 0.95) | Mean CI width |
|---|---|---|
| (i) cluster bootstrap, fresh ids | **0.10** | 0.1606 |
| (ii) parametric bootstrap | 0.93 | 0.1813 |
| (iii) profile likelihood | 0.93 | 0.1857 |

PRIMARY selected by code: **(ii)**, via the tie-break described in
Section 2/6.

### Part A — real-data fit and intervals (study_b_units.parquet, n=1,701 units, 1,232 players, 157 team-contexts)
Point estimate: S = 0.653731 (var_player=4.9024e-7, var_team=2.5967e-7).

| Method | 95% CI for S | Contains point estimate? |
|---|---|---|
| (i) cluster bootstrap | [0.3789, 0.5657] | No |
| (ii) parametric bootstrap (PRIMARY) | [0.5662, 0.7550] | Yes |
| (iii) profile likelihood (tied alternate) | [0.5444, 0.7515] | Yes |

Method (i)'s real-data interval reproduces the exact pathology Amendment
v2-6.1 diagnosed: it excludes the point estimate it was built from.

### Part A — post-hoc checks and v2-5.4 tier verdict, using PRIMARY = (ii)

| Check | Fit S | 95% CI | n units |
|---|---|---|---|
| PH-B1 (+ position-group FE) | 0.6379 | [0.5473, 0.7427] | 1,701 |
| PH-B3 (movers with >=2 units only) | 0.5793 | [0.4656, 0.6970] | 814 |

PH-B2 (disattenuated mover correlation, unaffected by interval method):
r_obs=0.0534, split-half reliabilities club=0.5007/intl=0.5522,
r_true=0.1015, 95% CI=[-0.2476, 0.5263] (includes zero).

| Tier | Condition | Verdict under PRIMARY=(ii) |
|---|---|---|
| Tier 1 | B4 CI lower bound > 0.5 (0.5662 — passes) AND PH-B1 CI lower bound > 0.5 (0.5473 — passes) | **ALLOWED** |
| Tier 2 | Tier 1 (passes) AND PH-B2 positive w/ CI excl. zero (r_true=0.1015>0 but CI includes zero — fails) AND PH-B3 CI lower bound > 0.5 (0.4656 — fails) | **NOT ALLOWED** |

### Part A — tie-break addendum: same tier verdict under the untied alternate, (iii)

| Check | 95% CI (method iii) |
|---|---|
| B4 (real data) | [0.5444, 0.7515] |
| PH-B1 | [0.5274, 0.7381] |
| PH-B3 | [0.4344, 0.7160] |

| Tier | Verdict under (iii) |
|---|---|
| Tier 1 | **ALLOWED** (both lower bounds > 0.5) |
| Tier 2 | **NOT ALLOWED** (same two failures: PH-B2 CI includes zero, PH-B3 CI lower bound < 0.5) |

The tier verdicts are identical under both tied candidates. The tie is
disclosed in full (Section 6) but does not change Part A's substantive
conclusion.

### For comparison — Task 08's verdict under the now-invalid interval method
Tier 1: NOT ALLOWED (corrected B4 CI lower bound 0.3631, PH-B1 CI lower
bound 0.3513, both failed). Tier 2: NOT ALLOWED. Source:
`docs/results/08-studies-b-c.md`.

### Part B / Part C
Not yet run.

## 4. Deviations from the brief
- **None in method or scope for Part A.** All three candidate methods,
  the 100-simulation coverage test with the brief's own checkpoint-and-
  disclose contingency, and the fixed v2-5.4 tier re-application were
  run exactly as specified.
- **Ambiguity encountered, not resolved by me**: the coverage tie between
  methods (ii) and (iii) (Section 2/6) — the brief's selection rule
  ("PRIMARY = coverage closest to 0.95 among methods with coverage
  >= 0.90") does not define a tie-break, and the code I wrote resolved
  it via Python `min()`'s first-match behavior on an unordered tie
  without my having previously flagged that this was a live possibility.
  I am disclosing this as a question (Section 6) rather than asserting
  (ii) is correctly primary, and have computed the untied alternate's
  full downstream consequences so nothing is hidden by the choice.
- The task brief (`docs/specs/task-10-validation.md`) specifies **100**
  coverage-test simulations; Amendment v2-6.1's original text specifies
  **200**. I followed the task brief's explicit number, since it is the
  document that governs this task's execution and was given after the
  amendment — noted here as a discrepancy between the two governing
  documents, not a decision I made myself.

## 5. Problems and surprises
- Neither method that reached the >=0.90 coverage floor actually reached
  0.95 — both (ii) and (iii) sit at 0.93. This is not itself a failure
  under the brief's stated rule, but it means Study B's validated
  interval is still not exactly nominal; a table this small (100
  simulations) can't distinguish "true coverage is 0.93" from "true
  coverage is 0.95 and this is Monte Carlo noise" — the 95% CI on a
  binomial proportion of 93/100 is roughly [0.863, 0.972].
- Method (i)'s catastrophic 10% coverage is a strong, direct confirmation
  of Amendment v2-6.1's mechanism argument (crossed-design resampling
  damages the un-resampled factor) — not a surprise given the amendment,
  but worth stating plainly since it is the paper's justification for
  discarding Task 07/08's original interval entirely.
- If taken at face value, Part A's Tier 1 "ALLOWED" result would
  invalidate the Task 08 conclusion that Study B's player-vs-context
  finding was descriptive only — that conclusion rested entirely on the
  now-demonstrated-invalid interval method's lower bound (0.3631) failing
  the 0.5 threshold. The corrected lower bound (0.5662/0.5444 depending
  on method) clears it. This is exactly the kind of correction v2-6.1
  anticipated, not a new finding independent of the interval-method fix.

## 6. Questions for the research lead
1. **Tie-break rule for PRIMARY selection.** Methods (ii) and (iii) tied
   exactly at 0.93 coverage in the 100-simulation test. The brief does
   not specify how to break a tie. My code resolved it via Python's
   `min()` iteration order (returns (ii)), which is an implementation
   detail I introduced, not a rule from the brief or the amendment. I
   have NOT chosen a tie-break rule myself, and computed the untied
   alternate's PH-B1/PH-B3/tier verdicts for comparison
   (`data/task10_partA_tiebreak.json`, Section 3 above) — under this
   audit, both alternates give the SAME tier verdict, so nothing hinges
   on the answer here for this task, but I did not want to silently rely
   on Python dict-iteration order as if it were a methodology decision,
   and a future re-run with different bootstrap draws could plausibly
   land on a tie the two methods' tier verdicts do NOT agree on. Please
   specify a tie-break rule (e.g. narrower mean width, or a preference
   order) for the preregistration record.
2. **100 vs. 200 simulations.** Amendment v2-6.1 specifies 200 simulated
   datasets for the coverage test; the task-10 brief specifies 100 (with
   B=200 bootstrap draws inside each simulation). I ran 100, following
   the task brief. Flagging the discrepancy between the two documents in
   case it was not an intentional narrowing.

## 7. Files produced
- `src/decision_engine/reml_crossed.py` — added `profile_likelihood_ci_S`
  (method iii)'s CI construction), plus a self-check in `__main__`. No
  existing function in this file was changed.
- `src/decision_engine/task10_partA_interval.py` — Part A's main script
  (coverage test, real-data intervals, PH-B1/PH-B2/PH-B3, tier
  application).
- `src/decision_engine/task10_partA_tiebreak.py` — addendum computing the
  tied alternate's downstream PH-B1/PH-B3/tier verdict (Section 6, item 1).
- `data/task10_partA_interval.json` — full Part A run summary. Gitignored.
- `data/task10_partA_tiebreak.json` — tie-break addendum summary.
  Gitignored.
- Git commits made so far this task: `746ac3c` (docs/JOURNAL.md,
  research lead's own Task 09b entry, committed separately per the
  established pattern); `4116455` (Part A: `reml_crossed.py`,
  `task10_partA_interval.py`, `task10_partA_tiebreak.py`, this results
  page, and `docs/specs/task-10-validation.md`).

## 8. Confidence
Part A: moderate-high. The coverage test ran to completion at the full
100 simulations without needing the runtime-cut contingency, method (i)'s
failure is a clean, large-margin confirmation of the amendment's
diagnosis, and the tier verdict is identical under both tied primary
candidates so the one real ambiguity found (Section 6, item 1) turns out
not to be load-bearing for this task's conclusion. The soft spots are:
neither validated method reaches the nominal 95% coverage target (both at
93%, within Monte Carlo noise of 95% but not confirming it), and the
tie-break itself remains an open methodology question for future reruns
where it might not be inconsequential. Parts B and C not yet assessed.
