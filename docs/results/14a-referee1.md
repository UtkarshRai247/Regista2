# Task 14a: Referee 1 — do the objectives predict real outcomes?
Date: 2026-09-24
Status: COMPLETE

## 1. Headline
No objective wins Referee 1. O1's possession-level xG coefficient is not positive with a CI excluding zero (it is negative and non-significant), and its team-match PH-O4-form xG coefficient, while positive, has a CI that includes zero. O2 and O3 both satisfy the team-match PH-O4 condition (positive, CI excludes zero), but both fail the possession-level condition: O2's possession-xG coefficient is negative and *significantly* so (p=0.0011); O3's is negative with a CI that includes zero. All three objectives: NOT WIN.

## 2. What I did
Governing spec: `docs/specs/analysis-plan-v3.md` (Amendments v3-1 to v3-4) + `docs/specs/task-14a-referee1.md`, plan v3 section 3. Reproducing command: `python src/decision_engine/task14a_referee1.py`.

- **Step 0**: committed Amendment v3-4 alone (commit `8a696bd`).
- **Step 1 (Decision_obj at team-match/possession level)**: Decision needs no value-function call (`EV(chosen) - policy-weighted EV`, straight from each objective's own `ev`/`chosen`/`policy_probability`), so Execution/realized-value was not computed here (not needed for Referee 1, unlike Tasks 13/13b/13c). O1: `decompose.build_per_pass_table(policy, o1_model)`, unchanged. O2: `options_o2.parquet`'s `ev` attached positionally to `options_policy.parquet` (confirmed row-for-row aligned in Task 13c), then a new minimal `compute_decision_only` (the non-Execution half of `decompose.build_per_pass_table`). O3: `options_o3.parquet` only covers 99.6% of options, so this task recomputed the same `keep_mask` Task 13c used (strength proxy -> `build_team_bin_lookup`, reused unmodified from `task13c_wp_diagnostic.py`) and verified `policy[keep_mask]`'s row count matched `options_o3.parquet`'s exactly before attaching `ev` positionally.
  - Team-match units (`task10_partB_outcome.build_team_match_units` + `add_possession_share` + `add_xg`, built once, objective-independent): O1 and O2 both have 583/598 valid units (matching Task 10's own historical count exactly); O3 has 582/598 — one fewer, from the single match already documented in Task 10 (`docs/results/10-validation.md`, match 3837747, PSG vs Marseille) where the raw events label Marseille's team as "Marseille" rather than the `home_team`/`away_team` spelling "Olympique de Marseille" used everywhere else — the same naming inconsistency, now also breaking the strength-proxy lookup this task's O3 reconstruction depends on (Marseille gets no proxy at all under this spelling, so `build_team_bin_lookup` also drops PSG's own strength bin for that one match, though PSG's other 56 study-sample matches are unaffected).
  - Possessions: a new `build_possessions_multi` (a parametrized copy of Task 11's `build_possessions`, carrying `decision_o1`/`decision_o2`/`decision_o3` through the identical possession-membership logic in one pass) — 20,042 possessions with >=3 eligible passes; O1 and O2 both have all 20,042 valid; O3 has 19,964 (78 fewer, all from the same PSG-vs-Marseille match).
- **Step 2 (identical battery per objective)**: for each of O1/O2/O3 (Decision z-scored on its own team-match or possession distribution, never against another objective's):
  - (a) team-match xG and goals: `task10_partB_outcome.fit_ols`, unchanged, with H-O1's predictor set (`decision_z, possession_share, is_home` + comp-season dummies, WITH possession share) and PH-O4's (`decision_z, is_home` + comp-season dummies, WITHOUT), both clustered by `team_context`.
  - (b) possession level: a new `fit_pho3_battery` (a parametrized copy of Task 11's `step3_pho3`, parameterized on which objective's possession decision to use), reproducing the identical zone-dummy + n_passes + team-context-FE logit (ends-in-shot) and OLS (possession xG) specs, clustered by match, re-checking per objective for a zero-variance-outcome team-context (found the same one every time: Nashville SC|44|107, 12 possessions, dropped, matching Task 11's own precedent exactly).
- **Step 3**: applied the plan's fixed rule mechanically — WIN iff the possession-level xG OLS coefficient AND the team-match PH-O4-form xG coefficient are both positive with a CI excluding zero.
- **Step 4**: verdicts reported below, without further comment.

## 3. Numbers

**n per objective**:

| | O1 | O2 | O3 |
|---|---|---|---|
| team-match units (of 598) | 583 | 583 | 582 |
| possessions (of 20,042) | 20,042 | 20,042 | 19,964 |
| possession regression n (after dropping Nashville SC\|44\|107) | 20,030 | 20,030 | 19,952 |

**Team-match xG**:

| form | objective | n | coef | CI | p |
|---|---|---|---|---|---|
| H-O1 (with possession share) | O1 | 583 | -0.1381 | [-0.2104, -0.0659] | 0.0002 |
| H-O1 (with possession share) | O2 | 583 | -0.1033 | [-0.1800, -0.0266] | 0.0083 |
| H-O1 (with possession share) | O3 | 582 | -0.0148 | [-0.1205, 0.0909] | 0.7836 |
| PH-O4 (without possession share) | O1 | 583 | +0.0271 | [-0.0580, 0.1123] | 0.5323 |
| PH-O4 (without possession share) | O2 | 583 | +0.1280 | [0.0383, 0.2177] | 0.0052 |
| PH-O4 (without possession share) | O3 | 582 | +0.2237 | [0.1370, 0.3105] | <0.0001 |

**Team-match goals**:

| form | objective | n | coef | CI | p |
|---|---|---|---|---|---|
| H-O1 (with possession share) | O1 | 583 | -0.4031 | [-0.5124, -0.2939] | <0.0001 |
| H-O1 (with possession share) | O2 | 583 | -0.2453 | [-0.3428, -0.1479] | <0.0001 |
| H-O1 (with possession share) | O3 | 582 | -0.2534 | [-0.4485, -0.0583] | 0.0109 |
| PH-O4 (without possession share) | O1 | 583 | -0.2088 | [-0.3089, -0.1087] | <0.0001 |
| PH-O4 (without possession share) | O2 | 583 | +0.0152 | [-0.0772, 0.1077] | 0.7470 |
| PH-O4 (without possession share) | O3 | 582 | +0.0555 | [-0.0669, 0.1779] | 0.3739 |

**Possession-level, ends in shot (logistic, average marginal effect)**:

| objective | n | dy/dx | CI | p |
|---|---|---|---|---|
| O1 | 20,030 | +0.01194 | [0.00546, 0.01842] | 0.0003 |
| O2 | 20,030 | +0.00165 | [-0.00492, 0.00822] | 0.6221 |
| O3 | 19,952 | +0.00910 | [0.00316, 0.01503] | 0.0027 |

**Possession-level, possession xG (OLS)**:

| objective | n | coef | CI | p |
|---|---|---|---|---|
| O1 | 20,030 | -0.00059 | [-0.00157, 0.00039] | 0.2355 |
| O2 | 20,030 | -0.00221 | [-0.00353, -0.00088] | 0.0011 |
| O3 | 19,952 | -0.00085 | [-0.00188, 0.00019] | 0.1083 |

**Referee 1 verdicts** (WIN iff both the possession-xG coefficient AND the team-match PH-O4-form xG coefficient are positive with CI excluding zero):

| objective | team-match PH-O4 xG condition | possession xG condition | verdict |
|---|---|---|---|
| O1 | NOT MET (CI includes zero) | NOT MET (coefficient negative) | **NOT WIN** |
| O2 | MET | NOT MET (coefficient negative and significant) | **NOT WIN** |
| O3 | MET | NOT MET (CI includes zero) | **NOT WIN** |

## 4. Deviations from the brief
None. Every predictor set, clustering choice, fixed-effect structure, and threshold reused code already written and run for O1 in Tasks 10, 11 and 12, applied unchanged to O2 and O3. The only new code is the mechanical plumbing to compute Decision_O2/Decision_O3 at the team-match and possession level (Section 2) and to run the same fitting functions three times instead of once.

## 5. Problems and surprises
1. **O1's own numbers reproduce Tasks 10/11/12's published results exactly** (team-match H-O1 xG coefficient -0.1381, PH-O4 xG coefficient +0.0271, possession ends-in-shot dy/dx +0.01194 — all matching those tasks' results pages to 4 decimal places), which is the verification this task's plan called for before trusting O2/O3's numbers built the same way.
2. **O3's coverage gap traces to the same single data-quality issue Task 10 already found**, not a new one: match 3837747 (PSG vs Marseille), where the raw events label Marseille "Marseille" instead of "Olympique de Marseille." This surfaced here because the strength-proxy lookup (built from `home_team`/`away_team` spellings) can't find "Marseille," and `build_team_bin_lookup` drops a team-context's strength bin for a whole match when either side lacks a proxy — so PSG's bin is also dropped for that one match (not for its other 56 study-sample matches). Net effect: 1 team-match unit and 78 possessions lost for O3 relative to O1/O2, all attributable to this one match.
3. **O2 and O3 both clear the team-match PH-O4 bar that O1 doesn't** (positive coefficient, CI excludes zero) — reported as a fact of the table, not as evidence either objective is "better" (the plan's rule requires both conditions, and neither clears the possession-level one).

## 6. Questions for the research lead
None. The comparison rule was fixed in advance and applied mechanically; nothing here required a judgment call.

## 7. Files produced
- `src/decision_engine/task14a_referee1.py` — this task's full implementation. Committed together with the results page, commit `4ae6a0b`.
- `docs/specs/analysis-plan-v3.md` (Amendment v3-4) — committed at Step 0, commit `8a696bd`.
- `docs/specs/task-14a-referee1.md` — committed with the script and results page, commit `4ae6a0b`.
- `docs/results/14a-referee1.md` — this page. Committed with the script, commit `4ae6a0b`.
- `data/task14a_referee1.json` — full machine-readable summary (every number in this page traces back to it). Not committed (data/).

## 8. Confidence
High for the mechanics: O1's numbers are byte-for-byte reproductions of three prior tasks' own published results, which is strong evidence the O2/O3 pipeline (built the same way, through the same functions) is correct rather than coincidentally wrong in a way that happens to look plausible. The weakest link is O3's dependence on the strength-proxy construction from Task 13c, which this task reused rather than re-validated — an error there would flow through silently into O3's Decision values here. The single-match coverage gap (Section 5.2) is fully accounted for and does not affect the O1/O2 comparison at all.
