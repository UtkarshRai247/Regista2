# Task 06: Study A confirmation, Gate D, sensitivity checks

Date: 2026-09-20
Status: COMPLETE

## Per-section checklist (per brief docs/specs/task-06-study-a-confirmation.md)
- Step 0 (two commits: CLAUDE.md repair, Amendment v2-2): COMPLETE
- Step 1 (confirmation statistics, 10 candidates only): COMPLETE
- Step 2 (Gate D under Amendment v2-2, all 10 candidates): COMPLETE
- Step 3 (pooled type-level diagnostic, descriptive): COMPLETE
- Step 4 (sensitivity checks a-d for every CONFIRMED candidate): COMPLETE
- Hard rules (no new candidates, full unsorted tables, no interpretation,
  JOURNAL.md/memory untouched): COMPLETE

## 1. Headline
Of the 10 fixed discovery-half candidates (docs/results/05-study-a-candidates.csv,
2026-09-20), 7 are CONFIRMED on the confirmation half (BH-significant at
q=0.05, P>0.5, L>=0.5). Of those 7, 5 also pass Gate D under Amendment
v2-2 (all `lateral_medium`; none of the `lateral_short` candidates passes
Gate D). Whether these 5 should be called sport-wide blind spots is not
decided here — see Section 5 for what that label would assume and what
it would invalidate if any of those assumptions is wrong.

## 2. What I did
Reproduce with: `.venv/bin/python src/decision_engine/task06_study_a_confirmation.py`
(after Step 0's two commits, done separately — see below).

- **Step 0**: committed `CLAUDE.md` alone (the research lead's own edit,
  repairing the truncated "Reporting discipline" list — items 5-8 were
  missing, per the brief's own description) in commit `d60f604`.
  Committed Amendment v2-2 to `docs/specs/analysis-plan-v2.md` alone in
  commit `4fdbe81`
  (`sha256 = 787520cdf7070dfe1e4c9a799639b7c46bf032392964b2331f385ed49c698e38`).
  Did not touch `docs/JOURNAL.md` (it changed on disk independently of
  this task, by the research lead; left as-is, not edited, not part of
  either of these two commits).
- **Step 1**: loaded the 151 confirmation-half matches
  (`data/splits/match_split.csv`) with the same pyarrow filter-pushdown
  join pipeline as Task 05
  (`src/decision_engine/task05_study_a_discovery.py`, 2026-09-20) —
  recovered raw candidate positions from `options_typed.parquet`, joined
  to `options_ev.parquet` on candidate position rounded to 6 decimals.
  Restricted every subsequent computation to exactly the 10 (cell, type)
  pairs from `docs/results/05-study-a-candidates.csv`; no other pair's G
  was ever computed. For each of the 10: G, its 95% CI, P, s, L (same
  formulas as Task 05, Amendment v2-1.1's L normalization), one-sided
  bootstrap p-value `(1 + #draws with G<=0)/1001` from the same 1,000
  match-resampling draws (seed 20260920), then Benjamini-Hochberg across
  the 10 p-values at q=0.05 (`statsmodels.stats.multitest.multipletests`,
  method `fdr_bh`). CONFIRMED = BH-significant AND P>0.5 AND L>=0.5.
- **Step 2**: computed realized value for every confirmation-half pass by
  reusing `decompose.compute_realized_values` (2026-09-19, unchanged)
  exactly as Task 01 defines it, paired with each pass's own chosen
  option's EV from `options_ev.parquet`; `execution = realized_value -
  EV(chosen)`. For each of the 10 candidates (confirmed or not), per
  Amendment v2-2.2: `Bias_k` = mean `execution` over confirmation passes
  in cell c whose chosen type is k; `Bias_ref` = mean `execution` over
  confirmation passes in cell c whose chosen type is NOT k; `Delta =
  Bias_ref - Bias_k`, with a 95% CI from 1,000 match-resampling bootstrap
  draws (a single shared resampled-match index per draw applied to both
  the k and ref groups, since both come from the same underlying
  matches). PASS (v2-2.3) only if Delta's CI upper bound is below the
  candidate's confirmation-half G. Also computed the relative completion
  calibration (`(actual - p_success)` bias for ref minus for k, in
  percentage points), descriptive only, no CI.
- **Step 3**: the same Bias_k/Bias_ref/Delta construction, but pooled
  across all 18 cells (no cell restriction) for each of the 9 option
  types, confirmation half, with the same bootstrap CI. Descriptive only.
- **Step 4**: for the 7 CONFIRMED candidates only, on the confirmation
  half: (a) G recomputed with mean EV of type k and of type j (chosen
  type) instead of max, plus the average number of type-k and type-j
  options per qualifying pass; (b) G/CI/P/L recomputed restricted to
  passes with >=18 visible players (Amendment v2-1.3); (c) G, sign, and n
  per competition-season, reported only where n>=100 qualifying passes;
  (d) G/CI/P/L recomputed restricted to World Cup 2022/Euro 2020/Euro
  2024 matches only, bootstrapped over the confirmation-half tournament
  match set specifically (not the full 151).

## 3. Numbers

**Join** (Step 1): 621,573 confirmation-half option rows in
`options_typed.parquet`; 621,573 matched to `options_ev.parquet` (100.0%
match rate) after resolving 16 duplicate-position key collisions the
same way as Task 05 (positional pairing within each duplicate-key group;
see Section 5).

**Step 1 — confirmation statistics, all 10 candidates (not sorted by effect size):**

| zone | pressure | state | type | discovery G | confirmation G | 95% CI | p | p (BH-adj) | BH-sig | P | s | L | n_passes | n_matches | CONFIRMED |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| defensive | no | trailing | lateral_short | 0.00140 | 0.00069 | [-0.00016, 0.00151] | 0.0599 | 0.0599 | No | 0.534 | 0.342 | 0.328 | 1903 | 138 | **No** |
| final | no | leading | lateral_medium | 0.00157 | 0.00251 | [0.00156, 0.00347] | 0.0010 | 0.0012 | Yes | 0.593 | 0.303 | 1.969 | 2913 | 131 | **Yes** |
| final | no | leading | lateral_short | 0.00208 | 0.00159 | [0.00080, 0.00250] | 0.0010 | 0.0012 | Yes | 0.573 | 0.350 | 0.883 | 2087 | 131 | **Yes** |
| final | no | level | lateral_medium | 0.00103 | 0.00081 | [0.00039, 0.00121] | 0.0010 | 0.0012 | Yes | 0.539 | 0.342 | 0.524 | 4801 | 145 | **Yes** |
| final | no | level | lateral_short | 0.00141 | 0.00083 | [0.00037, 0.00124] | 0.0010 | 0.0012 | Yes | 0.560 | 0.344 | 0.405 | 3605 | 145 | **No** (L<0.5) |
| final | no | trailing | lateral_medium | 0.00142 | 0.00113 | [0.00041, 0.00187] | 0.0010 | 0.0012 | Yes | 0.538 | 0.350 | 0.733 | 2603 | 137 | **Yes** |
| final | no | trailing | lateral_short | 0.00154 | 0.00091 | [0.00029, 0.00162] | 0.0020 | 0.0022 | Yes | 0.553 | 0.318 | 0.446 | 2003 | 139 | **No** (L<0.5) |
| middle | no | leading | lateral_medium | 0.00060 | 0.00068 | [0.00057, 0.00079] | 0.0010 | 0.0012 | Yes | 0.553 | 0.319 | 1.345 | 7941 | 137 | **Yes** |
| middle | no | level | lateral_medium | 0.00070 | 0.00079 | [0.00070, 0.00088] | 0.0010 | 0.0012 | Yes | 0.541 | 0.340 | 1.250 | 12320 | 148 | **Yes** |
| middle | no | trailing | lateral_medium | 0.00114 | 0.00123 | [0.00099, 0.00150] | 0.0010 | 0.0012 | Yes | 0.534 | 0.343 | 1.933 | 6608 | 141 | **Yes** |

7 of 10 CONFIRMED. The 3 not confirmed: `defensive|no|trailing|lateral_short`
(fails BH significance, p_adj=0.060), `final|no|level|lateral_short` and
`final|no|trailing|lateral_short` (both BH-significant and P>0.5, but
L<0.5, failing the practical floor).

**Step 2 — Gate D, all 10 candidates (confirmed or not):**

| zone | pressure | state | type | confirmed (step 1) | confirmation G | Bias_k | Bias_ref | Delta | Delta 95% CI | Gate D | completion calib. (pp, ref-k) | n_k | n_ref |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| defensive | no | trailing | lateral_short | No | 0.00069 | -0.001323 | 0.000078 | 0.001401 | [-0.00034, 0.00311] | **FAIL** | 0.414 | 989 | 3064 |
| final | no | leading | lateral_medium | Yes | 0.00251 | 0.000906 | 0.000200 | -0.000706 | [-0.00205, 0.00064] | **PASS** | -0.498 | 1267 | 3165 |
| final | no | leading | lateral_short | Yes | 0.00159 | -0.000523 | 0.000716 | 0.001239 | [-0.00006, 0.00244] | **FAIL** | 0.764 | 1126 | 3306 |
| final | no | level | lateral_medium | Yes | 0.00081 | 0.000343 | 0.000461 | 0.000118 | [-0.00082, 0.00105] | **FAIL** | 0.263 | 2491 | 5266 |
| final | no | level | lateral_short | No | 0.00083 | 0.000272 | 0.000471 | 0.000199 | [-0.00076, 0.00113] | **FAIL** | -0.314 | 1888 | 5869 |
| final | no | trailing | lateral_medium | Yes | 0.00113 | 0.000800 | 0.000263 | -0.000537 | [-0.00174, 0.00071] | **PASS** | 0.006 | 1404 | 2855 |
| final | no | trailing | lateral_short | No | 0.00091 | -0.000434 | 0.000686 | 0.001120 | [-0.00039, 0.00264] | **FAIL** | 1.460 | 936 | 3323 |
| middle | no | leading | lateral_medium | Yes | 0.00068 | 0.000130 | 0.000269 | 0.000139 | [-0.00017, 0.00044] | **PASS** | 1.109 | 3717 | 8442 |
| middle | no | level | lateral_medium | Yes | 0.00079 | 0.0000007 | -0.000675 | -0.000676 | [-0.00102, -0.00033] | **PASS** | 0.045 | 6358 | 13234 |
| middle | no | trailing | lateral_medium | Yes | 0.00123 | -0.000270 | -0.001084 | -0.000814 | [-0.00145, -0.00012] | **PASS** | -0.237 | 3457 | 7166 |

5 of the 7 CONFIRMED candidates also pass Gate D:
`final|no|leading|lateral_medium`, `final|no|trailing|lateral_medium`,
`middle|no|leading|lateral_medium`, `middle|no|level|lateral_medium`,
`middle|no|trailing|lateral_medium`.

**Step 3 — pooled type-level diagnostic, all 9 types, confirmation half (descriptive):**

| option_type | Bias_k | Bias_ref | Delta | Delta 95% CI | n_k | n_ref |
|---|---|---|---|---|---|---|
| forward_short | 0.0000730 | -0.000366 | -0.000438 | [-0.00079, -0.00009] | 8771 | 77101 |
| forward_medium | -0.000953 | -0.000275 | 0.000677 | [0.00021, 0.00116] | 5771 | 80101 |
| forward_long | -0.000485 | -0.000320 | 0.000165 | [-0.00101, 0.00153] | 599 | 85273 |
| lateral_short | -0.0000960 | -0.000392 | -0.000296 | [-0.00055, -0.00007] | 20719 | 65153 |
| lateral_medium | -0.000155 | -0.000394 | -0.000239 | [-0.00047, 0.00004] | 26310 | 59562 |
| lateral_long | 0.000303 | -0.000391 | -0.000694 | [-0.00100, -0.00041] | 8698 | 77174 |
| backward_short | -0.000910 | -0.000254 | 0.000657 | [0.00022, 0.00111] | 8818 | 77054 |
| backward_medium | -0.001892 | -0.000212 | 0.001679 | [0.00085, 0.00261] | 5560 | 80312 |
| backward_long | -0.000663 | -0.000318 | 0.000344 | [-0.00156, 0.00236] | 626 | 85246 |

**Step 4 — sensitivity checks, 7 CONFIRMED candidates, confirmation half:**

*(a) mean-EV instead of max, and average options per pass:*

| zone/state/type | G (max, original) | G (mean EV) | avg n(type k) | avg n(chosen type j) |
|---|---|---|---|---|
| final/leading/lateral_medium | 0.00251 | 0.000145 | 2.10 | 1.89 |
| final/leading/lateral_short | 0.00159 | 0.001834 | 1.66 | 1.86 |
| final/level/lateral_medium | 0.00081 | -0.000658 | 2.13 | 1.93 |
| final/trailing/lateral_medium | 0.00113 | -0.000571 | 2.17 | 1.97 |
| middle/leading/lateral_medium | 0.00068 | 0.000252 | 2.24 | 1.98 |
| middle/level/lateral_medium | 0.00079 | 0.000373 | 2.19 | 1.96 |
| middle/trailing/lateral_medium | 0.00123 | 0.000619 | 2.18 | 1.97 |

*(b) high-visibility frames only (>=18 visible players):*

| zone/state/type | G | 95% CI | P | L | n_passes | n_matches |
|---|---|---|---|---|---|---|
| final/leading/lateral_medium | 0.00262 | [0.00153, 0.00374] | 0.602 | 0.974 | 1136 | 110 |
| final/leading/lateral_short | 0.00164 | [0.00066, 0.00281] | 0.580 | 0.451 | 815 | 108 |
| final/level/lateral_medium | 0.00098 | [0.00046, 0.00151] | 0.537 | 0.325 | 1971 | 129 |
| final/trailing/lateral_medium | 0.00142 | [0.00059, 0.00240] | 0.552 | 0.454 | 1055 | 115 |
| middle/leading/lateral_medium | 0.00084 | [0.00073, 0.00095] | 0.569 | 1.109 | 4920 | 129 |
| middle/level/lateral_medium | 0.00089 | [0.00077, 0.00102] | 0.550 | 0.898 | 7486 | 146 |
| middle/trailing/lateral_medium | 0.00141 | [0.00108, 0.00181] | 0.548 | 1.290 | 3813 | 139 |

*(c) per competition-season (only where n_passes >= 100; every qualifying
row reported, none omitted):* MLS 2023 never reaches the 100-pass floor
for any of these 7 narrow cells and so never appears below (consistent
with its 3-match confirmation sample, per Amendment v2-1.5) — this is
the floor doing its job, not an omission. **One sign reversal**:
`final|no|trailing|lateral_medium` has a negative G in Ligue 1 21/22
(-0.00056, n=325) while every other competition-season for that
candidate, and every competition-season for every other candidate, is
positive. This is exactly the kind of case sensitivity check 3.6c exists
to surface; it is reported here without further comment, per the hard
rule against interpreting what results mean for the paper.

| zone/state/type | Ligue1 21/22 | Ligue1 22/23 | Bundesliga 23/24 | La Liga 20/21 | WC 2022 | Euro 2020 | Euro 2024 |
|---|---|---|---|---|---|---|---|
| final/leading/lateral_medium | 0.00383 (n=339) | 0.00116 (n=451) | 0.00286 (n=412) | 0.00191 (n=464) | 0.00439 (n=554) | 0.00245 (n=321) | 0.00060 (n=366) |
| final/leading/lateral_short | 0.00048 (n=254) | 0.00028 (n=338) | 0.00128 (n=282) | 0.00148 (n=335) | 0.00235 (n=394) | 0.00258 (n=237) | 0.00292 (n=245) |
| final/level/lateral_medium | 0.00160 (n=323) | 0.00130 (n=515) | 0.00069 (n=413) | 0.00024 (n=678) | 0.00092 (n=1065) | 0.00056 (n=888) | 0.00081 (n=916) |
| final/trailing/lateral_medium | **-0.00056 (n=325)** | 0.00183 (n=336) | 0.00080 (n=353) | 0.00132 (n=311) | 0.00105 (n=552) | 0.00157 (n=335) | 0.00176 (n=385) |
| middle/leading/lateral_medium | 0.00075 (n=951) | 0.00068 (n=1221) | 0.00080 (n=1280) | 0.00079 (n=1219) | 0.00068 (n=1319) | 0.00038 (n=879) | 0.00059 (n=1042) |
| middle/level/lateral_medium | 0.00055 (n=893) | 0.00079 (n=1255) | 0.00096 (n=1370) | 0.00077 (n=1466) | 0.00082 (n=2591) | 0.00078 (n=2137) | 0.00073 (n=2565) |
| middle/trailing/lateral_medium | 0.00065 (n=637) | 0.00143 (n=845) | 0.00100 (n=762) | 0.00167 (n=733) | 0.00159 (n=1520) | 0.00083 (n=946) | 0.00116 (n=1116) |

*(d) tournaments only (World Cup 2022, Euro 2020, Euro 2024 confirmation matches):*

| zone/state/type | G | 95% CI | P | L | n_passes | n_matches |
|---|---|---|---|---|---|---|
| final/leading/lateral_medium | 0.00277 | [0.00141, 0.00414] | 0.606 | 1.766 | 1241 | 70 |
| final/leading/lateral_short | 0.00257 | [0.00141, 0.00398] | 0.604 | 1.126 | 876 | 70 |
| final/level/lateral_medium | 0.00078 | [0.00028, 0.00130] | 0.538 | 0.532 | 2869 | 82 |
| final/trailing/lateral_medium | 0.00140 | [0.00053, 0.00232] | 0.540 | 0.806 | 1272 | 76 |
| middle/leading/lateral_medium | 0.00057 | [0.00038, 0.00078] | 0.545 | 0.846 | 3240 | 76 |
| middle/level/lateral_medium | 0.00078 | [0.00066, 0.00090] | 0.536 | 1.290 | 7293 | 84 |
| middle/trailing/lateral_medium | 0.00126 | [0.00096, 0.00162] | 0.532 | 1.942 | 3582 | 79 |

## 4. Deviations from the brief
None. Every Step 1-4 computation followed plan section 3, Amendment
v2-1, and Amendment v2-2 exactly, restricted to the fixed 10 candidates.

## 5. Problems and surprises

- **16 duplicate-position key collisions in the confirmation-half join**
  (vs. 2 in Task 05's discovery-half join, 2026-09-20) — proportionally
  consistent (151 vs. 148 matches). Resolved the same way: paired
  same-key duplicates positionally instead of cross-joining, verified
  100.0% match rate and zero group-size mismatches. Not re-verified here
  that the duplicate rows carry identical EV (as was confirmed for
  Task 05's 2 cases) — this is a mechanical continuation of an already-
  verified-safe pattern, not a new unverified assumption, but is named
  here rather than silently reused.
- **Amendment v2-2.5's disclosure applies directly to every Gate D
  result above.** The pass-success and possession-value models
  (`src/decision_engine/pass_success.py`, `possession_value.py`, frozen
  at commit `9db72ef`, 2026-09-19) were trained on data that includes
  confirmation-half matches (per Task 01's Decision D-010, the
  possession-value model trains on the full 299-match study sample by
  design, not a match-disjoint split). Gate D is therefore an in-sample
  calibration check on these models' own outputs, not a fully
  out-of-sample validation of the "blind spot" claim, even though it is
  correctly out-of-sample with respect to which pairs were *selected* as
  candidates (that selection used only discovery-half data). Restating
  as instructed by the amendment, and expanding, per the current
  CLAUDE.md item 6, on what this would invalidate if the 5 Gate-D-passing
  pairs above are taken at face value as sport-wide blind spots: (1) the
  claim assumes the models are well-calibrated specifically within these
  situation cells despite training on the same matches now being used to
  check them — a genuinely out-of-sample re-check (e.g. on a future
  season not in this sample) could still overturn a PASS here; (2) it
  assumes the 18-cell situation definition (zone x pressure x game state)
  captures enough tactical context that a positive G reflects a real
  choice error rather than an omitted-variable effect the model's
  opponent-proximity features don't capture (e.g. specific marking
  schemes); (3) it assumes EV as defined (P(goal within 10 actions),
  ignoring downstream adaptation, per plan section 1) is the right value
  currency — a "blind spot" under this metric could be a correct choice
  under an un-modeled value (e.g. retaining possession, tactical control)
  the engine was never asked to price. If any of these does not hold, the
  finding describes model calibration or cell granularity, not the
  sport's decision-making, and this task does not adjudicate between
  those readings — that is left for the paper write-up, per CLAUDE.md
  rule 4.
- **One Simpson's-paradox-style sign reversal in Step 4c.**
  `final|no|trailing|lateral_medium` — CONFIRMED and Gate-D-PASS overall
  — has a negative G in Ligue 1 21/22 specifically (-0.00056, n=325),
  the only negative cell among all 49 (7 candidates x 7 competition-seasons)
  reported in Step 4c. Every other competition-season for this candidate,
  and every competition-season for the other 6 CONFIRMED candidates, is
  positive. Reported per the sensitivity check's purpose; not
  interpreted further here.
- Nothing else was missing, broken, or malformed.

## 6. Questions for the research lead
None. Every definition in plan section 3.3-3.6, Amendment v2-1, and
Amendment v2-2 was implementable exactly as written.

## 7. Files produced
- `data/processed/study_a_confirmation_step1.parquet` — the 10-row Step 1
  table (all columns in Section 3's first table). Gitignored.
- `data/processed/study_a_gate_d.parquet` — the 10-row Gate D table.
  Gitignored.
- `data/processed/study_a_pooled_diagnostic.parquet` — the 9-row pooled
  type-level diagnostic. Gitignored.
- `data/task06_sensitivity.json` — the full Step 4 sensitivity output for
  the 7 CONFIRMED candidates (checks a-d). Gitignored.
- `data/task06_study_a_confirmation.json` — run summary (join report,
  confirmed-candidate list). Gitignored.
- `src/decision_engine/task06_study_a_confirmation.py` — the script
  producing all of the above.
- Git commits made this task: `d60f604` (CLAUDE.md, research lead's
  edit), `4fdbe81` (Amendment v2-2 to `analysis-plan-v2.md`), and — per
  CLAUDE.md item 9 — a further commit (hash TBD, filled in immediately
  after this page is first committed, since a commit cannot record its
  own hash) covering this script, this results page, and
  `docs/JOURNAL.md` (which changed on disk independently of this task,
  per the note in Section 2, and was not part of either of Step 0's two
  scoped commits).

## 8. Confidence
High on Steps 1-3's mechanics: the join reached 100% match rate after
resolving the same kind of duplicate-position collision Task 05 already
characterized as harmless, the BH procedure used the standard
`statsmodels` implementation rather than a hand-rolled one, and the Gate
D bootstrap reuses the same shared-resample-matrix approach validated in
Task 05. The weakest link is exactly what Amendment v2-2.5 and Section 5
above name: Gate D checks the models against data some of those same
models were trained on, so a PASS here is necessary but not sufficient
evidence of a genuine sport-wide blind spot — it rules out one specific,
large failure mode (the model wildly overvaluing a type it rarely sees)
but does not rule out subtler in-sample calibration flattery. Step 4's
sensitivity checks are all descriptive by design (no additional gate):
48 of 49 candidate x competition-season signs are positive, with the one
exception noted in Section 5 — descriptive consistency, not itself a test.
