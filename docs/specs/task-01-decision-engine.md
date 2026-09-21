# Task 01 — Decision Engine and Reliability Gate

## Purpose
Build the minimum working decision engine and run the two gates from
docs/specs/analysis-plan-pillar4.md. NO market value data in this task.
Do not load, download, or join transfermarkt data. That is Task 2.

## Terms
- Behavior policy: a model of which option a typical player chooses in
  a given situation, learned from what players actually did.
- Gradient boosting: a tree-based model that works well on tabular data
  and trains fast on CPU.
- Spearman-Brown correction: adjusts a split-half correlation upward to
  estimate reliability of the full-length measure.

## Sample
StatsBomb open data, men's competition-seasons WITH 360 coverage only.
Use the audit output from Task 00 to pick them. Exclude all women's
competitions and exclude AFCON 2023 (1/52 coverage, too partial).
Re-pull 360 frames from scratch; Regista 1's frames are not on disk.
Report the final list of competition-seasons and match counts before
proceeding to modeling.

## Scope
Open-play passes only. Exclude set pieces, throw-ins, corners, free
kicks, kick-offs, and goalkeeper distributions. Exclude any pass whose
freeze frame is missing or has fewer than 6 visible players.

## Step 1 — Option sets
For each eligible pass, build the candidate option set:
- Every VISIBLE TEAMMATE in the freeze frame, excluding the passer.
- Record, for each candidate: distance, angle, whether the lane crosses
  an opponent, number of opponents within 5m of the candidate, distance
  to nearest opponent, and the candidate's pitch location.
Passes into space are NOT modeled in v1. Note this as a scope limit.
Report the distribution of option-set sizes.

## Step 2 — Pass success model
Train a gradient-boosted classifier predicting whether a pass is
completed, using ONLY features that exist for both chosen and unchosen
options (see Step 1). Do not use any feature that is only observable
after the pass.
Report AUC and a calibration check on a held-out set, split by MATCH
(not by row) to avoid leakage.
Report how often unchosen options fall outside the feature range the
model was trained on. This matters: those predictions are
extrapolations.

## Step 3 — Possession value model
Train a model estimating the probability that the possessing team scores
within the next 10 actions, given the game state.
Features: ball location, recent action locations, time remaining, score
difference, and possession phase. Use the full StatsBomb open event data
for training volume, not just the 360 subset.
Do NOT use a location-only grid. A location-only value function is the
known flaw we are fixing from the previous project.
Report calibration.

## Step 4 — Expected value of each option
For each candidate option:
  EV = p_success * V(state after successful pass)
       + (1 - p_success) * V(state after turnover, valued negatively
         from the possessing team's perspective)
Report the EV distribution for chosen vs unchosen options.

## Step 5 — Behavior policy
Train a model that, given an option set, predicts which option a typical
player chooses. Use the same features as Step 1.
Report top-1 and top-3 accuracy against what players actually chose.

## Step 6 — The three components
For each pass:
- Decision = EV(chosen option) - sum over all options of
  [ policy_probability(option) * EV(option) ]
- Execution = realized value of the pass outcome - EV(chosen option)
- Risk = EV variance of the chosen option relative to the
  policy-weighted average variance
Aggregate per player per competition-season, as a mean per 100 passes.
Also compute, for the same rows: progressive passes per 90, xA per 90,
pass completion percentage, minutes played.

## GATE A — Reliability. STOP AND REPORT.
Randomly split each player's passes into two halves. Compute Decision,
Execution and Risk on each half. Report the correlation between halves
with a Spearman-Brown correction, plus a bootstrap confidence interval.
Report separately for players above and below 500 passes.
Do NOT proceed past this gate without an instruction from the research
lead, whatever the number is.

## GATE B — Separation. STOP AND REPORT.
Report the full correlation matrix between Decision, Execution, Risk,
progressive passes per 90, xA per 90, and pass completion percentage.
Do NOT proceed past this gate without an instruction.

## Hard rules
- No market value data in this task.
- If a modeling choice is not specified above, STOP and ask in Section 6
  of the results page. Do not choose for yourself.
- Report both gates exactly as they come out. A bad number here is a
  valid project outcome and must not be worked around.
- Everything must run on 16GB RAM. Chunk the event data if needed.

## Output
docs/results/01-decision-engine.md following docs/results/TEMPLATE.md.
Per-player outputs written to data/processed/ (gitignored).
All code in src/.
