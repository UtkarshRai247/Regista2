# Task 01b: Pre-join Diagnostics
Date: 2026-09-20
Status: COMPLETE

## 1. Headline
The sample flow lands at exactly the 138-unit / 102-player sample
Amendment 1 references. Repeated-split reliability (100 independent
splits, not one) confirms Decision is stable at the 200-pass threshold
(median 0.744, 5th percentile 0.691 — just under 0.70) while Execution
stays unreliable and volatile (median 0.482, range 0.300-0.603) —
consistent with Amendment 1's decision to drop Execution from the
primary specification. **Chosen-pass calibration is essentially
unbiased (predicted 0.889 vs. actual 0.889)** — the persistent negative
Execution mean is NOT explained by Step 2 miscalibration on the passes
players actually chose, which rules out the most obvious hypothesis and
leaves that finding still open.

## 2. What I did
- Recomputed the full sample-flow attrition table directly from the 299
  matches' raw event files on disk (no new network calls) — all events
  down through open-play filtering, freeze-frame presence, visibility,
  angle-matching, aggregation, and the 200-pass threshold.
- Re-ran Gate A's split-half reliability calculation 100 times with
  independent random splits (not the single split used before) for
  Decision and Execution at the 200-pass threshold, reporting the
  median and 5th/95th percentile across splits.
- Checked Step 2's (pass-success model) calibration specifically on
  chosen (matched, actually-attempted) passes, in deciles of predicted
  probability, using the existing scored options data — no retraining.
- Computed Decision's distribution and the 10 highest/10 lowest players
  by `decision_per_100` for the 138-unit sample, with each player's most
  common position that competition-season and their competition.
- Reproduce: `python src/decision_engine/task01b_diagnostics.py`

## 3. Numbers

### Section 1 — Sample flow
| Filter | Count remaining |
|---|---|
| All events (299 matches) | 1,145,062 |
| → Passes | 328,892 |
| → Open play (excl. set pieces/throw-ins/kick-offs/keeper) | 289,001 |
| → Freeze frame present | 251,229 |
| → ≥6 visible players | 250,850 |
| → Angle match accepted (D-011) | 171,618 |
| → Aggregated to player-competition-season | 2,901 units |
| → ≥200 eligible passes | **138 units** |

**Final sample: 138 player-competition-season units, 102 distinct
players** (some players clear 200 passes in more than one
competition-season in this sample).

### Section 2 — Repeated-split reliability (100 splits, 200-pass threshold, 138 units)
| Metric | Median | 5th pct | 95th pct |
|---|---|---|---|
| Decision | **0.744** | 0.691 | 0.792 |
| Execution | **0.482** | 0.300 | 0.603 |

This supersedes the single-split numbers reported earlier (Decision
0.703, Execution 0.460 at this same threshold) — both single-split
values fall inside this wider picture, but the spread itself is the
finding: Decision is a comfortably tighter, higher-sitting distribution
than Execution's, which ranges across a full 0.30 band and never
approaches 0.70 even at its upper end.

### Section 3 — Step 2 calibration on chosen passes only
Overall (171,618 chosen passes): **predicted mean 0.8890, actual mean
0.8886** — a 0.0004 gap, not meaningfully different from perfect
calibration.

| Predicted-probability decile | n | Mean predicted | Mean actual |
|---|---|---|---|
| (0.110, 0.672] | 17,162 | 0.502 | 0.496 |
| (0.672, 0.808] | 17,162 | 0.749 | 0.740 |
| (0.808, 0.887] | 17,162 | 0.850 | 0.848 |
| (0.887, 0.938] | 17,161 | 0.915 | 0.914 |
| (0.938, 0.964] | 17,162 | 0.953 | 0.948 |
| (0.964, 0.976] | 17,162 | 0.970 | 0.972 |
| (0.976, 0.984] | 17,162 | 0.980 | 0.984 |
| (0.984, 0.989] | 17,161 | 0.987 | 0.990 |
| (0.989, 0.992] | 17,162 | 0.991 | 0.995 |
| (0.992, 0.998] | 17,162 | 0.994 | 0.998 |

No systematic over- or under-prediction: the model runs marginally
*low* at the very top deciles (predicting 0.994 where actual is 0.998)
and is essentially exact everywhere else. This is a well-calibrated
model on exactly the population Execution is computed from — **it does
not explain the negative Execution mean.**

### Section 4 — Descriptives (138-unit sample, face validity only)
Decision (`decision_per_100`): mean **0.208**, SD **0.083**.

**Top 10 by Decision:**
| Player ID | Competition | Position | Decision/100 | Eligible passes |
|---|---|---|---|---|
| 39073 | La Liga 2020/21 | Right Center Midfield | 0.395 | 201 |
| 8519 | UEFA Euro 2024 | Right Center Back | 0.384 | 237 |
| 30486 | La Liga 2020/21 | Left Center Midfield | 0.378 | 991 |
| 3501 | La Liga 2020/21 | Center Attacking Midfield | 0.368 | 295 |
| 3567 | Ligue 1 2021/22 | Right Center Midfield | 0.336 | 216 |
| 3166 | UEFA Euro 2020 | Center Defensive Midfield | 0.336 | 252 |
| 5549 | UEFA Euro 2024 | Center Back | 0.331 | 231 |
| 32480 | La Liga 2020/21 | Right Center Back | 0.326 | 513 |
| 3500 | UEFA Euro 2024 | Left Defensive Midfield | 0.322 | 282 |
| 6765 | FIFA World Cup 2022 | Right Center Back | 0.317 | 501 |

**Bottom 10 by Decision:**
| Player ID | Competition | Position | Decision/100 | Eligible passes |
|---|---|---|---|---|
| 33401 | Bundesliga 2023/24 | Left Attacking Midfield | -0.027 | 227 |
| 3311 | UEFA Euro 2020 | Left Wing Back | 0.022 | 211 |
| 2995 | Ligue 1 2021/22 | Right Wing | 0.039 | 542 |
| 4320 | Ligue 1 2022/23 | Left Wing | 0.051 | 544 |
| 3009 | Ligue 1 2022/23 | Center Forward | 0.057 | 621 |
| 5211 | UEFA Euro 2020 | Left Back | 0.058 | 274 |
| 5503 | Ligue 1 2022/23 | Right Center Forward | 0.060 | 1,099 |
| 4320 | Ligue 1 2021/22 | Left Wing | 0.064 | 574 |
| 5211 | FIFA World Cup 2022 | Left Back | 0.071 | 209 |
| 20572 | FIFA World Cup 2022 | Right Center Back | 0.075 | 246 |

Face-validity read only, per the spec: the top 10 skews toward central/
defensive positions (center backs, defensive/central midfielders), the
bottom 10 skews toward wide attacking positions (wingers, forwards,
wing backs). Plausible on its face (a pooled "typical player" policy
baseline may not fully separate the situational risk-taking that wide
attacking positions face from a genuine decision-quality signal), but
this is not being asserted as a finding — it's exactly the kind of
pattern that would need Pillar 1 / Gate B scrutiny before being read as
real, and no such scrutiny was run here.

## 4. Deviations from the brief
- "Position" for each player in Section 4 is that player's single most
  frequent `position` value across their own events in that
  competition-season (StatsBomb records position per-event, since it
  can change mid-match/tournament). The spec didn't specify how to
  collapse this to one label; mode was the natural choice, stated here
  for visibility rather than silently picked.
- Everything else follows the spec directly — no other deviations.

## 5. Problems and surprises
- **The calibration check came back clean, which itself is notable**:
  it was a real candidate explanation for the negative Execution mean
  (Task 01, Section 5/6), and it's now ruled out. The negative mean is
  still unexplained — worth stating plainly rather than letting a clean
  calibration table quietly imply the issue is resolved.
- **Decision's 5th percentile (0.691) sits just under the 0.70
  proceed-cleanly threshold**, even though the median (0.744) clears it
  comfortably. Amendment A1.1 already accounted for this kind of
  variability by citing the single-split number (0.703) rather than
  claiming a clean pass — this repeated-split result is consistent with
  that framing, not a contradiction of it, but the 5th-percentile edge
  case is worth having on record.

## 6. Questions for the research lead
1. **The negative Execution mean is still unexplained** — chosen-pass
   calibration was the most obvious candidate and it's clean. Do you
   want further diagnosis (e.g., checking the turnover-value
   construction from Task 01 Section 4), or does Amendment A1.2's
   decision to drop Execution from the primary spec make this moot for
   the paper regardless of cause?
2. **Decision's repeated-split 5th percentile (0.691) is just under
   0.70** — worth a sentence in the paper's methods/limitations
   acknowledging this, or is citing the median (0.744, matching
   Amendment A1.1's reasoning) sufficient?

## 7. Files produced
- `src/decision_engine/task01b_diagnostics.py` — all four sections.
- `data/task01b_diagnostics.json` (gitignored) — full numeric output.
- `docs/results/01b-diagnostics.md` — this page.

## 8. Confidence
High confidence in Sections 1-3 — direct counts cross-check against
values already reported in Task 01 and Amendment 1 (the 138-unit/
200-pass figure matches exactly), and the repeated-split methodology is
a straightforward, more robust re-run of already-verified logic (100
independent draws rather than one). Section 4 is explicitly a
face-validity check, not a result, per the spec, and is reported with
that caveat intact rather than overstated. The weakest link is that
Section 3's clean calibration result narrows but doesn't close the
open question about the negative Execution mean — it rules out one
explanation without supplying another.
