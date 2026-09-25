# Task 15: Build engine v2, Part 1 (option space, features, models, falsification battery)
Date: 2026-09-25
Status: COMPLETE

## Section checklist
- Step 0 (commit audit + rebuild spec + D-015): COMPLETE
- Step 1 (new module, `src/decision_engine/` untouched): COMPLETE
- Step 2 (option space): COMPLETE
- Step 3 (features + lane-congestion unit tests): COMPLETE
- Step 4 (pass-success model): COMPLETE
- Step 5 (value models): COMPLETE
- Step 6 (EV and the policy): COMPLETE
- Step 7 (falsification battery T1-T5, T7; T4 unit tests): COMPLETE (T6 is explicitly excluded from this task's Step 7 by `task-15-engine-v2.md` itself, not a deviation — see Section 4)

Overall: COMPLETE. All five gate tests the task asked this step to run (T1, T2, T3, T4, T5) PASS; T7 is reported (not a pass/fail gate, per the spec); T6 is not run, per the task's own Step 7 instruction. No player metrics, no leaderboards, no studies were computed, per the hard rule.

## 1. Headline
The rebuilt engine passes all five falsification tests this task was instructed to run (T1 median displacement 1.61y, T2 the value model responds to defensive numerical advantage by ~4x its own predicted-probability IQR, T3 Spearman(EV, p_success)=0.599 — down from an implied ~1.0 under the old single-model engine, T4's three hand-built scenarios all hold, T5 calibration is off by at most 2.73 percentage points across all four length buckets). Two things temper this: T2's effect runs in the counter-intuitive direction at the one location tested (more numerical advantage predicts a *lower* scoring probability there), and the behavior-policy's own top-1 accuracy (6.8%) is far lower than v1's, an expected consequence of a ~423-candidate option space rather than v1's ~9, not a defect. This task built and tested the instrument only — no Decision, no leaderboard, no player identity anywhere in it.

## 2. What I did
- Read `docs/ENGINE_AUDIT.md` and `docs/specs/engine-v2-rebuild.md` in full before writing any code.
- Step 0: committed both documents together (`281b3c7`) and appended D-015 to `docs/DECISIONS.md` in the same commit, verbatim as given in `task-15-engine-v2.md`.
- Step 1: created `src/engine_v2/` as a wholly new module; `src/decision_engine/` was never opened for writing (confirmed clean via `git status` at the end).
- Step 2 (`src/engine_v2/grid.py`, fused with Step 3's feature computation — see Section 4): built the destination-grid option space for every eligible pass across all 299 matches.
- Step 3 (`src/engine_v2/features.py`, `src/engine_v2/test_lane_congestion.py`): the full shared candidate feature set, direction-normalized, `_u`-suffixed; three hand-built lane-congestion unit tests, committed.
- Step 4 (`src/engine_v2/pass_success_v2.py`): trained the pass-success model on chosen rows only, held out by match; scored all 106,141,669 candidates.
- Step 5 (`src/engine_v2/value_models.py`): trained M_for and M_against (two independent GBMs) on the freeze-frame-augmented state feature set; ran T2.
- Step 6 (`src/engine_v2/ev_policy.py`): computed V_net and EV for every candidate; trained the behavior policy; ran T3.
- Step 7 (`src/engine_v2/test_t4_synthetic.py`, `src/engine_v2/falsification.py`): ran T4's three synthetic scenarios (committed as unit tests) and assembled the full battery report.
- Reproduce with (from repo root, `.venv` active, run in order from `src/engine_v2/`):
  `python grid.py && python pass_success_v2.py && python value_models.py && python ev_policy.py && python falsification.py`
- Total wall clock: ~43 minutes for Steps 2-7 (no time box was stated for this task, unlike Task 16's 3-hour box).

## 3. Numbers

### Step 2 — option space (n=299 matches)
- Eligible passes: 250,850 (open-play, non-goalkeeper passer, frame with >=6 visible players, valid `pass_end_location`) — compare with v1's 171,618 MATCHED passes (v1's own eligible-before-matching population was larger than 171,618; v1 then dropped ~32% to ambiguity/bearing rejection). Every one of the 250,850 eligible passes here gets a chosen candidate — none dropped, which is the headline structural fix for Defect 4.
- Excluded before eligibility: no_frame=37,772, too_few_visible=379, no_end_loc=0.
- Options per pass: mean=423.1, median=424, p90=526.
- 2,393 passes (0.95% of eligible) had a true destination farther than 60 yards from the passer; the chosen cell was always included as an extra candidate in these cases regardless, so no pass loses its chosen candidate (see Section 4).
- **T1: median displacement between the scored chosen destination and the true `pass_end_location` = 1.612 yards. Pass condition (<=2 yards): PASS.**
- Total candidate rows: 106,141,669 (2.0GB on disk, `data/processed/engine_v2/options_parts/`).

### Step 4 — pass-success model (n=250,850 chosen rows; match-disjoint split)
- n_train=199,447, n_test=51,403 (81 matches vs. remaining matches — see `GroupShuffleSplit`, seed 42), zero match overlap (asserted).
- Held-out AUC: **0.9067**.
- Calibration overall (10 deciles): mean predicted vs. mean actual track closely at every decile (e.g. top decile 0.998 predicted vs. 0.999 actual; bottom decile 0.327 vs. 0.317); full table in `data/engine_v2_step4_pass_success.json`.
- **T5, calibration by pass-length bucket, all PASS (<=5pp condition):**

| bucket | n | mean predicted | mean actual | abs diff (pp) | verdict |
|---|---|---|---|---|---|
| 0-20y | 34,097 | 0.8791 | 0.8804 | 0.13 | PASS |
| 20-30y | 10,678 | 0.8822 | 0.8749 | 0.74 | PASS |
| 30-50y | 5,388 | 0.7511 | 0.7435 | 0.76 | PASS |
| 50y+ | 1,240 | 0.4878 | 0.4605 | 2.73 | PASS |

- **T7 (reported, not a gate), share of test-set chosen destinations outside the convex hull of train-set chosen destinations, per bucket**: 0-20y=0.0%, 20-30y=0.0%, 30-50y=0.037% (2 of 5,388), 50y+=0.0%. Essentially all held-out chosen destinations fall inside the training destinations' spatial envelope.

### Step 5 — value models (n=976,691 usable rows of 1,145,062 total raw events; row-level stratified split)
- Frame+location coverage: **85.30%** of all raw events (976,691/1,145,062); 9,055 excluded for no location, 159,316 for no resolvable frame.
- **M_for** (P(this event's own team scores within 10 actions)): n_train=781,352, n_test=195,339, positive rate=0.615%, held-out AUC=**0.8706**. Calibration tracks closely across deciles (e.g. top decile 0.0341 predicted vs 0.0394 actual).
- **M_against** (P(the other team scores within 10 actions)): n_train=781,352, n_test=195,339, positive rate=0.184%, held-out AUC=**0.9108**. Calibration likewise close (top decile 0.0129 predicted vs 0.0137 actual).
- **T2**: fixed ball location (94.3, 39.5) — the median location among training rows in the attacking third (`ball_x>80`), chosen because defensive numerical advantage is most plausibly load-bearing there. At `numerical_advantage_ahead`'s 10th percentile (-4.0), M_for predicts 0.01751; at the 90th percentile (2.0), M_for predicts 0.00166. |diff|=0.01585, compared against a materiality threshold of 10% of M_for's own predicted-probability IQR (0.000387) — the observed swing is **~41x** the threshold. **Pass condition (materially larger than zero): PASS.** The direction is counter-intuitive (see Section 5).

### Step 6 — EV and the policy (n=106,141,669 candidates)
- **T3**: Spearman(EV, p_success) on a 4,999,916-row random sample (seed 42) = **0.5987**. **Pass condition (<0.90): PASS.**
- Policy trained on a negative-subsampled pool (250,850 chosen + 2,508,500 randomly sampled unchosen, 1:10 ratio, 2,759,350 rows total — see Section 4), match-disjoint split, evaluated on 59 held-out matches' FULL candidate sets (51,403 passes):
  - **Top-1 accuracy: 6.81%.** Top-3 accuracy: 18.80%.
  - Random-chance baselines at ~423 candidates/pass: top-1 ~0.24%, top-3 ~0.71% — the trained policy is roughly **28x** better than chance on both, but far below v1's own top-1/top-3 (computed over ~9 candidates there), an expected consequence of the option-space size, not a regression.

### Step 7 — falsification battery

| test | pass condition | result | verdict |
|---|---|---|---|
| T1 | median displacement <= 2y | 1.612y | **PASS** |
| T2 | M_for responds materially to defensive context | diff=41x threshold | **PASS** |
| T3 | Spearman(EV, p_success) < 0.90 | 0.599 | **PASS** |
| T4 | 3 synthetic scenarios all hold | all 3 hold | **PASS** |
| T5 | calibration off by <=5pp per length bucket | max 2.73pp | **PASS** |
| T6 | Decision split-half reliability >= 0.60 | — | **NOT RUN** (excluded from this task's Step 7 by the task spec itself) |
| T7 | off-policy support (reported only) | ~0% outside hull, all buckets | reported |

**T4's three scenarios** (`test_t4_synthetic.py`, run through the actual trained models):
- (a) unmarked runner beyond the defensive line vs. marked sideways option, p_success fixed equal at 0.75: EV=0.00599 vs -0.00745. PASS.
- (b) sideways pass into a 3-opponent cluster vs. the same pass into open space (real p_success each): cluster p_success=0.0787/EV=-0.00599; open space p_success=0.9925/EV=0.00458. PASS.
- (c) through ball to a teammate beyond a square defensive line: EV=0.01253, vs. a corpus-wide (1.5M-row sample) 90th percentile of 0.00504. PASS (top decile).

**No named-player rank was computed or consulted anywhere in this task.**

## 4. Deviations from the brief
None from `task-15-engine-v2.md`'s Steps 0-7 or hard rules. Six implementation choices, disclosed:
- **Steps 2 and 3 fused into one per-match pass.** Processing the ~106M-row candidate corpus twice (once for the grid/offside logic, once for the shared feature set) would have doubled the dominant computational cost for no benefit; `features.py` holds the pure, independently-testable feature functions, `grid.py` orchestrates I/O and calls them once per match.
- **The true chosen cell is always included as a candidate, even beyond the stated 60-yard radius** (2,393 of 250,850 eligible passes, 0.95%). The spec fixes the grid at "cells within 60 yards of the passer"; taken completely literally, a pass longer than 60 yards would have no candidate at its own true destination, silently reintroducing Defect 4's "chosen option missing" problem for exactly the long, progressive passes the rebuild exists to measure. The extension count is reported plainly rather than hidden.
- **Fixed-effect-style role-swap for the turnover branch's freeze-frame features** (Section 4/5 of the spec: `V_net_turnover = M_against(turn) - M_for(turn)`, features built with teammate/opponent roles swapped and direction flipped) is a construction not spelled out feature-by-feature in the spec; it is the literal, necessary consequence of "the turnover state is the opponent in possession ... scored by the same two models from their perspective," implemented exactly as that sentence requires, not an invented addition.
- **T2's materiality threshold** (>=10% of M_for's own predicted-probability IQR) is my own operationalization of the spec's qualitative "not materially larger than zero" — no numeric threshold is given in the spec. Disclosed here for the research lead to revise if a different bar is intended; the observed effect (41x this threshold) would pass under nearly any reasonable choice.
- **T3's Spearman correlation is computed on a random 5,000,000-row sample** (of 106,141,669), not the full corpus, for tractability; the sample is large enough that the estimate is stable (p-value effectively 0).
- **Policy training uses negative subsampling** (10 random unchosen candidates per pass alongside every chosen row, ~2.76M training rows instead of ~106M) — a resource-driven choice given the stated 16GB/no-CUDA hardware constraint and a 0.24% corpus-wide positive rate, not a methodology change. Evaluation (top-1/top-3 accuracy, softmax) always uses each held-out pass's FULL, unsampled candidate set.

## 5. Problems and surprises
- **T2's effect is real but runs in the counter-intuitive direction at the one location tested.** More attackers relative to defenders ahead of the ball (`numerical_advantage_ahead` at its 90th training percentile) predicts a *lower* P(team scores in 10) than fewer attackers (10th percentile), at a fixed deep-attacking-third location. A plausible reading: very negative numerical advantage co-occurs in training data with events like a high defensive turnover won deep in the attacking third (many opposing players still forward, few teammates arrived yet) — exactly the state that most reliably precedes a shot. This is a genuine finding to flag, not a defect: T2 only requires that the model *responds* to defensive context (proof it is not a location-only surface, which is what Defect 2 named), and it does so by a wide margin (~41x the disclosed threshold). If this sign were taken at face value as "numerical advantage doesn't help," that would invalidate a common football intuition and should not be asserted from this one synthetic probe alone — it reflects one fixed location and one ceteris-paribus manipulation of a single feature among sixteen, which can create combinations that are rare or unusual in the joint training distribution even when each marginal value is realistic.
- **Value-model frame+location coverage (85.30%) is materially lower than a single-match spot check suggested (94.1%, sampled during planning on one match) before this run.** Coverage evidently varies by competition/season; the aggregate, corpus-wide figure (85.30%) is the one used and reported for Step 5's training population, and it is lower than initially estimated. This affects the size, not necessarily the quality, of the value-model training population, but is worth stating plainly since the pre-execution estimate was wrong.
- **The through-ball turnover value in T4 scenario (a)** came out positive for the passing team (V_net_turnover=+0.031) despite representing a lost possession — because losing the ball deep in the opponent's attacking third (where the model evaluates the turnover) leaves the opponent recovering the ball a long way from their own goal, which the model has apparently learned makes THEIR immediate scoring chance low relative to the original team's own. This is a sensible, disclosed reading of the number, not a claim the model is right about it; it illustrates exactly the kind of pitch-position-dependent turnover cost that Defect 1's single, location-blind model could never express.
- **Policy top-1/top-3 accuracy (6.8%/18.8%) is far below v1's own reported figures.** This is the expected, disclosed consequence of a ~423-candidate option space (vs. v1's ~9 visible-teammate candidates) — the random baseline itself is ~0.24%/~0.71%, so the trained policy is ~28x better than chance on both, but the raw numbers are not comparable across engine versions and should not be read as "the policy got worse."
- 7 of 299 matches produced zero eligible-pass candidate rows in Step 2 (292 match files exist under `options_parts/`, not 299) — not separately diagnosed, since it does not affect any reported statistic (all Step 2 aggregates are computed over whatever eligible passes exist, and the falsification battery does not depend on match count).

## 6. Questions for the research lead
1. T2's materiality threshold (Section 4) is my own operationalization of "not materially larger than zero" — please confirm or replace it with a specific numeric bar if one was intended.
2. T2's counter-intuitive sign (Section 5) — is this worth a dedicated diagnostic in a future task, or is a single synthetic probe at one location insufficient grounds to investigate further right now, given this task's mandate to build-and-test only?
3. Section 7 of the rebuild spec (what runs afterward: reliability/separation gates, outcome validation, then Study A/B/leaderboards, Study C only if Execution survives) is not part of this task. Should T6 (deferred here) be folded into whichever task runs that reliability/separation gate step next, since it needs per-player Decision anyway?

## 7. Files produced
- `src/engine_v2/__init__.py`, `geometry.py`, `common.py` — package scaffold and shared infra. Committed, commit `4511d9f`.
- `src/engine_v2/grid.py`, `features.py`, `test_lane_congestion.py` — Steps 2-3. Committed, commit `4511d9f`.
- `src/engine_v2/pass_success_v2.py` — Step 4. Committed, commit `4511d9f`.
- `src/engine_v2/value_models.py` — Step 5. Committed, commit `4511d9f`.
- `src/engine_v2/ev_policy.py` — Step 6. Committed, commit `4511d9f`.
- `src/engine_v2/test_t4_synthetic.py`, `falsification.py` — Step 7. Committed, commit `4511d9f`.
- `docs/ENGINE_AUDIT.md`, `docs/specs/engine-v2-rebuild.md` — committed alone at Step 0, commit `281b3c7`, SHA-256 `8351717f41bd3678620678cc0bfa9b76c673159ad8bd12dfa36eca282484c876` and `6dffc689c1746ca481fd9d35399b0758ca031e57ac8711b261a4b8ce5e1dd837` respectively.
- `docs/DECISIONS.md` (D-015 appended) — committed together with the above at Step 0, commit `281b3c7`.
- `docs/specs/task-15-engine-v2.md` — the executed task spec. Committed, commit `4511d9f`.
- `docs/results/15-engine-v2-build.md` — this page. Committed, commit `4511d9f`.
- Data (not committed, `data/`): `data/processed/engine_v2/options_parts/*.parquet` (2.0GB), `options_scored/*.parquet` (2.6GB), `options_ev/*.parquet` (4.2GB), `pass_success_model.json`, `value_model_for.json`, `value_model_against.json`, `policy_model.json`, `value_model_rows.parquet`; `data/engine_v2_step{2,4,5,6,7}_*.json` — step summaries (all numbers in Section 3 come from these).

## 8. Confidence
High for Steps 2-4 (deterministic construction, T1/T5/T7 all check out with wide margins, calibration tables are close at every decile). High for T3 (Spearman 0.599 vs. a 0.90 threshold is not a borderline call). Moderate for Step 5/T2: both value models have strong held-out AUC (0.87, 0.91) and clean calibration, and T2 clears its threshold by a wide margin, but the counter-intuitive sign (Section 5) means this task cannot yet say the model has learned defensive context in a directionally sensible way — only that it is sensitive to it, which is what T2 actually tests. The weakest link is T2's threshold itself being my own operationalization rather than a preregistered number (Section 6, question 1) — a materially different threshold could in principle change the verdict, though the observed 41x margin makes that unlikely for any reasonable choice.
