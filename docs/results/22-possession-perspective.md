# Task 22: Value model rows — possessing team's view + label that counts its own event
Date: 2026-09-27
Status: PARTIAL — stopped at Step 2 per the brief's own instruction (premise check failed in both required bands)

## Section checklist
- Step 0 (commit brief; second commit for CHAT-HANDOFF.md/task-20 spec): COMPLETE
- Step 1 (revert Task 21's 3 features from STATE_FEATURES only): COMPLETE
- Step 2 (rebuild rows with fixes A+B, diagnostic file, tables T-a/T-b/T-c, premise check): COMPLETE — reads FAIL in both required bands, stop before Step 3 (per brief)
- Step 3 (retrain, recompute EV/policy/Decision/Risk, T6): NOT RUN — brief requires stopping if Step 2's premise fails
- Step 4 (falsification battery): NOT RUN — gated on Step 3
- Step 5 (cross-fitted outcome validation): NOT RUN — gated on Step 4

Running only Steps 0–2 is not a deviation: the brief's own text says "If
[the premise] does not hold: STOP here: no retraining, report, done."
Steps 3–5 not running is the literal, pre-specified consequence of what
Step 2 found, not a scope cut made here.

## 1. Headline
Fixing both defects the brief identified — restricting value-model
training rows to events where the acting team actually has the ball
(Defect A), and letting a scoring event's own row count toward its own
label (Defect B) — does not produce the predicted pattern. In-possession
rows with the ball beyond the defensive line score LESS often than
in-possession rows with the ball not beyond it, in both band 80-100
(0.28% vs 1.04%) and band 100-120 (1.86% vs 4.70%) — the opposite of
prediction P2, and a larger gap than Task 21 found before either fix.
Per the brief's own stop condition, this halts the task before Step 3:
no retraining, no falsification battery, no outcome validation.
Per the brief's own text, this closes the engine's line of fixes before
the Oct 1 abstract deadline — "There is no Task 22b" — and no
engine-based player claim is made.

## 2. What I did
1. Committed `task-22-possession-perspective.md` alone, then a second
   commit adding `docs/CHAT-HANDOFF.md` and
   `docs/specs/task-20-player-results.md` (both untracked), per Step 0's
   explicit instruction. `docs/JOURNAL.md` was left untouched.
2. Removed `distance_to_nearest_teammate_u`, `teammates_within_5u`,
   `teammates_within_10u` from `value_models.py`'s `STATE_FEATURES` list
   only (Task 21's premise failed, per that task's results page). Left
   both feature builders computing all three unchanged and re-ran
   `test_frame_features_agree.py` — still `ALL PASS` (Step 1).
3. Wrote `value_models_v4.py`: a new `build_match_rows_v4` that computes,
   for every event with a resolvable location+frame, BOTH the old label
   window (`range(i+1, ...)`) and the new one (`range(i, ...)`, Defect
   B's fix), plus an `in_possession` flag (`team == possession_team`,
   Defect A). Wrote the full diagnostic file (all 976,691 location+frame
   rows) and the new training file (in-possession rows only, new labels
   renamed to `label_for`/`label_against`). Built and printed the T-a/
   T-b/T-c tables from the diagnostic file, applied the premise check
   exactly as specified, and stopped before training since it failed
   (Step 2).

Reproduce with (from `src/engine_v2/`, `.venv` activated):
`python value_models_v4.py`.

## 3. Numbers

### Row counts
| quantity | value |
|---|---|
| total raw events (all 299 matches) | 1,145,062 |
| no location | 9,055 |
| no frame | 159,316 |
| diagnostic rows (location+frame, both possession states) | 976,691 |
| in-possession rows (the new training file) | 828,728 (84.85%) |
| out-of-possession rows (excluded from training) | 147,963 (15.15%) |

The 15.15% out-of-possession share is close to, but somewhat higher
than, the brief's own "~13.5%" figure quoted from its match-3764440
sample — expected, since the brief's figure was a single-match estimate
and this is the full 299-match corpus.

### T-a — Task 21's zero cell (band 80-100, beyond line, teammate within
5u of ball), out-of-possession share
| quantity | value |
|---|---|
| n rows in the zero cell | 2,602 (matches Task 21's own count exactly) |
| out-of-possession rows in the cell | 1,209 |
| share out-of-possession | 46.46% |

Top out-of-possession event types in this cell: Pressure (482),
Pass (160 — the OPPONENT's own passes, since these are opponent-team
rows in a cell defined by the passer's-own-team frame), Clearance (150),
Duel (89), Interception (77), Block (68), Carry (61), Foul Committed
(50), Ball Recovery (40), Ball Receipt* (15).

**P1 ("a majority of the 2,602 rows... are out-of-possession") is
WRONG**: 46.46% is a substantial share, and out-of-possession
contamination is real and large, but it is not a majority of this cell.

### T-b — rows whose label_for changes under Defect B's fix
| quantity | value |
|---|---|
| n rows total (diagnostic) | 976,691 |
| n rows where label_for_old != label_for_new | 1,401 |
| of those, n Shot events | 827 (59.03%) |

Defect B's fix changes 0.14% of all rows' label_for, concentrated in
Shot events (59% of changed rows) as the brief predicted, plus other
event types whose own action is itself immediately followed by a goal
within the same event slot in a way the old window missed (e.g., a Shot
that deflects for an Own Goal recorded as a separate event at the same
index boundary, or a non-Shot event at index i that is followed in the
old window's first slot i+1 by the goal — 1,401 − 827 = 574 non-Shot
rows change, a share this page reports but does not further break down,
since the brief does not ask for a further split).

### T-c — PREMISE TABLE (in-possession rows only, new labels)
| band | beyond line | n | P(score in 10) | P(concede in 10) |
|---|---|---|---|---|
| 0-40 | No | 173,524 | 0.9543% | 0.0519% |
| 0-40 | Yes | 30,255 | 1.0940% | 0.0364% |
| 40-60 | No | 153,642 | 0.2493% | 0.0072% |
| 40-60 | Yes | 53,220 | 0.1954% | 0.0132% |
| 60-80 | No | 141,646 | 0.2979% | 0.0148% |
| 60-80 | Yes | 64,846 | 0.1064% | 0.0200% |
| 80-100 | No | 94,233 | 1.0421% | 0.0329% |
| 80-100 | Yes | 47,605 | 0.2815% | 0.0441% |
| 100-120 | No | 26,446 | 4.7001% | 0.0303% |
| 100-120 | Yes | 38,995 | 1.8618% | 0.0590% |

Premise check (both required bands, beyond-line must score STRICTLY
HIGHER than not-beyond):
- 80-100: 0.2815% vs 1.0421% — **FAILS** (beyond-line scores at 27% of
  the not-beyond rate)
- 100-120: 1.8618% vs 4.7001% — **FAILS** (beyond-line scores at 40% of
  the not-beyond rate)

**Both required bands fail — the premise does not hold.** Per Step 2's
literal instruction, the task stops here.

**P2 ("in-possession rows beyond the line score MORE than in-possession
rows not beyond the line, in bands 80-100 and 100-120") is WRONG** — the
opposite holds in both bands, by a wide margin, even after removing
out-of-possession rows and letting scoring events count their own
outcome.

**P3 is NOT EVALUATED** — T2 was never run, since Step 3 (retraining)
did not execute.

## 4. Deviations from the brief
None. Every step ran exactly as specified up to the point the brief's
own stop condition fired: `STATE_FEATURES`-only removal (Step 1),
possession-based row filtering with score bookkeeping left untouched
(Step 2A), lookahead window shifted to `range(i, ...)` with the same
length (Step 2B), diagnostic file with the exact column set named in
the brief, premise check applied with the brief's own literal
threshold (strict inequality, both bands required). `git diff --stat`
for existing files shows only the 1-line `STATE_FEATURES` removal in
`value_models.py`.

## 5. Problems and surprises
- Applying BOTH fixes together makes the "beyond the line is safer"
  finding MORE pronounced, not less: band 100-120's beyond/not-beyond
  ratio was 0.7564%/1.1996% = 63% in Task 21's (uncorrected-perspective,
  old-label) data, and is 1.8618%/4.7001% = 40% here. Two defects that
  were each independently plausible causes of a data-representation
  artifact, once fixed together, sharpened the pattern the fixes were
  meant to dissolve. That is itself informative: it weakens the
  standing hypothesis (carried since Task 19d) that "beyond the line
  scores less" is purely a labeling/definition artifact, and raises the
  alternative that the finding may reflect something closer to genuine
  signal in this data — e.g., that advanced-but-uncontrolled possessions
  (which end in turnovers, clearances, or simply running out of danger
  before a shot materializes) are simply more common than clean
  breakthroughs, even after removing the two specific definitional
  errors named in this brief.
- Defect B's fix touched far fewer rows (1,401 of 976,691, 0.14%) than
  Defect A's (147,963 of 976,691, 15.15%) — the perspective fix is by
  far the larger data change of the two, even though the label-window
  fix was the one directly motivated by scenario_c's own shot-adjacent
  states.
- The out-of-possession share in Task 21's zero cell (46.46%) is large
  but not the majority P1 predicted — meaning more than half of that
  cell's rows were already legitimate in-possession states with zero
  goals in 10 actions, which is consistent with this page's main
  finding that the pattern survives, and sharpens, once the
  out-of-possession rows are removed.

## 6. Questions for the research lead
1. The brief states, if this premise fails, "the engine is not accepted
   before Oct 1 and no engine-based player claim is made" and "There is
   no Task 22b." I have followed the stop condition exactly and gone no
   further. Is there a different next step you want taken with the
   abstract (e.g., report Study A/B without engine-based player-level
   claims, using only the aggregate/team-level findings that don't
   depend on Decision), or is this results page the final word on the
   engine track for the abstract deadline?
2. Section 5 raises a substantive possibility: that "beyond the line
   scores less" may not be an artifact of these two specific defects,
   since fixing both sharpened rather than dissolved it. That is a
   substantive interpretive claim about what the data is telling us,
   which this project's rules reserve for the research lead — it is
   raised here as a question, not adopted as a conclusion.
3. `value_model_rows_v4.parquet` and `value_model_rows_diagnostic_v4.parquet`
   exist and are fully built (828,728 and 976,691 rows respectively).
   Should they be kept in case a future methodology change wants to
   reuse the possession-corrected, own-event-inclusive labels, or
   treated as a dead end alongside Task 21's `_v3` files?

## 7. Files produced
- `src/engine_v2/value_models.py` — modified (−1 line): Task 21's 3
  possession-state fields removed from `STATE_FEATURES` only (Step 1).
- `src/engine_v2/value_models_v4.py` — new. `build_match_rows_v4`
  (both defect fixes + both label sets + `in_possession` flag), table
  builder (T-a/T-b/T-c), premise check, and the gated retrain path
  (not reached this run).
- `data/processed/engine_v2/value_model_rows_diagnostic_v4.parquet`,
  `value_model_rows_v4.parquet` — new data artifacts (not committed,
  per project rule: `data/` is never committed).
- `data/engine_v2_step2_tables_v4.json` — new summary JSON backing
  Section 3's T-a/T-b/T-c tables (also under `data/`, not committed).
- `docs/CHAT-HANDOFF.md`, `docs/specs/task-20-player-results.md` —
  committed per Step 0's explicit instruction (previously untracked,
  unrelated content, not authored as part of this task's own work).
- `docs/specs/task-22-possession-perspective.md` — committed alone at
  Step 0.
- `docs/results/22-possession-perspective.md` — this file.
- Commit hashes: `2fd7517` (brief alone, Step 0a), `16b8bcf`
  (CHAT-HANDOFF.md + task-20 spec, Step 0b), `<pending>` (this results
  page + Steps 1–2 code) — to be filled in a follow-up commit per
  CLAUDE.md rule 9.

## 8. Confidence
High confidence in the numbers themselves: T-a/T-b/T-c come directly
from a single, committed row-builder script's diagnostic output, with
no modeling step between the raw StatsBomb `possession_team` column and
the reported shares, and the 2,602-row zero cell reproduces Task 21's
own count exactly, which cross-checks that the two builders (this one
and Task 21's, now retired) agree on cell membership. Lower confidence
in what the surviving pattern means: Section 5's alternative reading
(that this may be closer to genuine signal than artifact) is a
possibility raised by the direction of the change, not something this
page can adjudicate — that requires the research lead's judgment. The
weakest link is that neither Step 3's retrain nor any part of the
falsification battery ran, so nothing here speaks to whether a
differently-defined fix might have passed; this page reports only that
the two specific, code-level defects named in the brief, fixed exactly
as specified, do not produce the predicted pattern.
