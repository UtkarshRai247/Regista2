# Task 03: Primary Model
Date: 2026-09-20
Status: COMPLETE

## 1. Headline
The rebuilt join (Amendment 2: 180-day window, 3 crosswalk resolutions)
produces 125 units across 96 players (61 tournament, 64 league); the 79
originally-matched units kept identical valuation records, verified
directly. In the primary specification, **Decision's coefficient is
-0.285 (p=0.733, 95% CI [-1.92, 1.35])** — not statistically
distinguishable from zero, an imprecise null. **Two of six robustness
variants (90-day/79-unit window, league-only) show a statistically
significant NEGATIVE Decision coefficient** (p=0.043 and p=0.033
respectively); the other four (primary, ≥250-passes, midfielders-only,
without-club-strength) do not reach significance. None of the six show
a significant positive coefficient.

## 2. What I did
- **Step 1**: applied A2.3's 3 crosswalk resolutions
  (`src/market_join/crosswalk_overrides.py`), rebuilt valuations at a
  180-day window (`valuations.py --window-days 180`), rebuilt controls.
  Directly verified (not assumed) that all 79 originally-matched units'
  valuation records are byte-identical between the 90-day and 180-day
  runs.
- **Step 2-3**: fit the primary OLS (`src/market_join/fit_model.py`),
  cluster-robust by player, computed VIF, and transformed Decision's
  coefficient and CI into a percentage-market-value interpretation.
- **Step 4**: fit the H3 secondary model on the same script.
- **Step 5**: built the 250-passes join variant
  (`valuations.py --min-passes 250`, `controls.py`) and fit all 6
  robustness specifications.
- **Step 6**: fit one exploratory model (Execution added), reported
  separately with its reliability caveat inline.
- Reproduce: `python src/market_join/crosswalk_overrides.py &&
  python src/market_join/valuations.py --window-days 180 --min-passes 200
  --crosswalk data/processed/player_crosswalk_v2.csv
  --out data/processed/units_with_valuations_180d.parquet &&
  python src/market_join/controls.py
  --units data/processed/units_with_valuations_180d.parquet
  --out data/processed/market_join_analysis_sample_180d.parquet &&
  python src/market_join/fit_model.py`

## 3. Numbers

### Step 1 — Rebuilt sample flow
| Filter | Units | Lost here |
|---|---|---|
| ≥200 eligible passes | 138 | — |
| Crosswalk resolved (all 102 players, post-A2.3) | 138 | 0 |
| Valuation within 180 days | 125 | 13 |
| Club strength available | 125 | 0 |
| Age available | 125 | 0 |
| **Final analysis sample** | **125** | **96 distinct players** |

Tournament vs. league: 61 vs. 64. Position group: 72 Defender, 42
Midfielder, 11 Forward.

**79-unit stability check (explicit requirement): PASS.** All 79 units
from the original 90-day join are present in the 180-day join, with
identical `valuation_date` and `valuation_eur` in every case (0
mismatches, verified by direct comparison, not by argument from how the
window-widening logic works).

### Step 2/3 — Primary model
OLS, log(market value) ~ Decision + completion% + progressive passes/90
+ goals+assists/90 + minutes + age + position group (Defender ref.) +
tournament + club strength (€M) + days_to_valuation. Cluster-robust SE
by player. **n=125, 96 clusters, R²=0.588.**

| Term | Coef | Clustered SE | t | p | 95% CI |
|---|---|---|---|---|---|
| const | 17.857 | 1.582 | 11.29 | <0.001 | [14.758, 20.957] |
| **Decision** | **-0.285** | **0.837** | **-0.34** | **0.733** | **[-1.925, 1.355]** |
| Completion% | 0.739 | 1.826 | 0.41 | 0.686 | [-2.840, 4.318] |
| Progressive passes/90 | 0.0014 | 0.0133 | 0.11 | 0.914 | [-0.025, 0.027] |
| Goals+assists/90 | 0.473 | 0.241 | 1.96 | 0.050 | [0.001, 0.945] |
| Minutes | 0.00048 | 0.00009 | 5.25 | <0.001 | [0.0003, 0.0007] |
| Age | -0.114 | 0.015 | -7.71 | <0.001 | [-0.142, -0.085] |
| Tournament | 1.018 | 0.201 | 5.07 | <0.001 | [0.624, 1.412] |
| Club strength (€M) | 0.0213 | 0.0081 | 2.62 | 0.009 | [0.005, 0.037] |
| Days to valuation | -0.0005 | 0.0014 | -0.35 | 0.725 | [-0.003, 0.002] |
| Midfielder | 0.385 | 0.127 | 3.03 | 0.003 | [0.136, 0.634] |
| Forward | 0.838 | 0.255 | 3.29 | 0.001 | [0.338, 1.337] |

**VIF** (all well under conventional concern thresholds of 5-10, despite
the pairwise correlations flagged in Task 02):
| Term | VIF |
|---|---|
| **Decision** | **1.787** |
| Completion% | 2.584 |
| Progressive passes/90 | 1.557 |
| Goals+assists/90 | 2.592 |
| Minutes | 2.254 |
| Age | 1.424 |
| Tournament | 3.530 |
| Club strength | 1.022 |
| Days to valuation | 2.909 |
| Midfielder | 1.285 |
| Forward | 2.198 |

### Step 3 — Decision's coefficient in plain units
- Decision's SD in this sample: 0.0853.
- Point estimate: a one-SD increase in Decision corresponds to
  **-2.40% change in market value**.
- 95% CI on that percentage: **[-15.13%, +12.24%]**.
- **The CI includes zero.**
- Smallest-magnitude effect the data rule out: since the CI's
  near-zero bound is +12.24%, the data cannot rule out effects smaller
  than a ~12% swing in either direction.
- **Classified as an imprecise null**: the CI spans a 27-percentage-point
  range, wide relative to plausible effect sizes — this is "we can't
  tell," not "we've established the effect is small."

### Step 4 — H3 secondary
Outcome: change in log(market value) from the join valuation to the
closest record ~12 months later, controlling for starting log(value).
**n=125, R²=0.374. Not underpowered** (n≥60).

| Term | Coef | SE | p | 95% CI |
|---|---|---|---|---|
| Decision | -0.775 | 0.486 | 0.111 | [-1.729, 0.178] |
| Starting log(value) | 0.0093 | 0.063 | 0.883 | [-0.114, 0.133] |

Decision's coefficient here is larger in magnitude and closer to
(but still not past) conventional significance than in the primary
model; CI still includes zero.

### Step 5 — Robustness set, all 6 reported

| Variant | n | Clusters | Decision coef | SE | p | 95% CI |
|---|---|---|---|---|---|---|
| **Primary (180d, 200p)** | 125 | 96 | -0.285 | 0.837 | 0.733 | [-1.925, 1.355] |
| a. 90-day window, orig. 79 | 79 | 65 | **-1.812** | 0.897 | **0.043** | **[-3.571, -0.054]** |
| b. League units only | 64 | 53 | **-2.224** | 1.041 | **0.033** | **[-4.264, -0.184]** |
| c. ≥250 passes | 86 | 67 | -0.907 | 0.878 | 0.302 | [-2.628, 0.815] |
| d. Midfielders only | 42 | 33 | -1.090 | 1.310 | 0.405 | [-3.656, 1.477] |
| e. Without club strength | 125 | 96 | -0.163 | 0.873 | 0.852 | [-1.873, 1.547] |

**f. Attenuation-corrected** (reliability 0.744, 5th-95th 0.691-0.792;
method: `corrected = raw / reliability_point`, corrected CI =
`[raw_ci_low / 0.792, raw_ci_high / 0.691]`, the conservative
combination of coefficient and reliability uncertainty):
- Raw: -0.285 [-1.925, 1.355]
- **Corrected: -0.383 [-2.430, 1.960]**
- Still includes zero; correction widens the CI further, as expected.

**Reported without selection, as instructed**: (a) and (b) show a
statistically significant negative coefficient; (c), (d), (e), and the
primary model do not reach significance; none of the six show a
significant positive coefficient.

### Step 6 — Exploratory (clearly separated, NOT part of the primary or robustness results)
Primary specification + Execution added. **Execution's reliability is
0.482 [0.300, 0.603] — NOT TRUSTWORTHY.** Reported in its own table
below, never combined with the primary/robustness tables above.

| Term | Coef | SE | p | 95% CI |
|---|---|---|---|---|
| Decision | -0.178 | 0.870 | 0.838 | [-1.883, 1.527] |
| Execution (reliability 0.482 [0.300, 0.603], not trustworthy) | 0.656 | 0.708 | 0.354 | [-0.732, 2.045] |

n=125, R²=0.592.

## 4. Deviations from the brief
- Attenuation-correction CI method (Step 5f) isn't specified in the
  brief beyond "the corrected CI reflecting that range" — implemented
  as stated in Section 3, a defensible but not uniquely-specified
  construction, flagged rather than silently chosen.
- Robustness variant (c) holds the 180-day window fixed and only raises
  the pass threshold to 250, isolating that one factor — the brief
  doesn't say explicitly which window to pair with the threshold change,
  but this reading is consistent with variant (a) separately isolating
  the window choice alone.
- Position-group dummies use Defender as the reference category (the
  modal group) — not specified in the brief.
- `club_strength_eur` was rescaled to millions (`club_strength_m`) for
  coefficient readability — purely cosmetic, doesn't change
  significance, R², or any other substantive result.

## 5. Problems and surprises
- **The 90-day/79-unit and league-only variants both show a
  statistically significant NEGATIVE Decision coefficient, while the
  primary (180-day, full) specification does not.** This is reported
  factually per the task's instruction not to editorialize: none of the
  6 robustness variants show a significant POSITIVE coefficient (the
  specific condition that would refute H2 under the preregistration's
  failure conditions), but the pattern of significant negative results
  in 2 of 6 variants is itself a fact worth the research lead's
  attention when interpreting the primary model's null.
- VIFs are all comfortably low (max 3.53) despite Task 02 flagging two
  pairwise correlations above 0.7 — multicollinearity among the full
  predictor set is not a real concern here, confirming that the earlier
  flagged pairs weren't a fitting-time problem.
- Tournament units nearly quadrupled (17 → 61) between the 90-day and
  180-day samples, changing the tournament/league balance substantially
  — worth keeping in mind when comparing coefficients on `is_tournament`
  or `days_to_valuation` across the two window specifications.

## 6. Questions for the research lead
None — the task's own instruction was "do not stop again unless
something specified here is impossible," and nothing was. The pattern
in Section 3/5 (significant-negative in 2 robustness variants,
null in the primary model) is reported as a fact for interpretation,
not raised as a blocking question.

## 7. Files produced
- `src/market_join/crosswalk_overrides.py` — A2.3 resolutions.
- `src/market_join/valuations.py` — now parameterized
  (`--window-days`, `--min-passes`, `--crosswalk`, `--out`).
- `src/market_join/controls.py` — now parameterized (`--units`, `--out`).
- `src/market_join/fit_model.py` — Steps 2-6, all models.
- `data/processed/player_crosswalk_v2.csv`,
  `units_with_valuations_180d.parquet`,
  `market_join_analysis_sample_180d.parquet`,
  `units_with_valuations_250p.parquet`,
  `market_join_analysis_sample_250p.parquet` (gitignored) — new join
  variants.
- `data/primary_model_results.json` (gitignored) — full numeric output,
  every model, every coefficient.
- `docs/results/03-primary-model.md` — this page.

## 8. Confidence
High confidence in the mechanics: the 79-unit stability check passed by
direct comparison (not assumption), VIFs are computed correctly and are
low, cluster-robust SEs are used throughout, and every robustness
variant's full coefficient table is reported without selection. The
substantive result itself (Decision's null in the primary spec,
alongside two significant-negative robustness variants) is exactly as
computed — no result was adjusted, hidden, or reframed. The weakest
link is n=125 with only 96 clusters for an 11-parameter model — VIFs
are fine, but coefficient precision is still limited, as Section 3's
wide confidence intervals throughout make clear.
