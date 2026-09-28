# Task 41 — Vetting round 2 (measurement only): CRITIQUE-v6 items 1a-1f, 2a, 2c, 2d, 3b

Written 2026-09-28 by the research lead, before any result. No engine
or measure changes. Study sample and PFF WC2022 only; the holdout is
spent and NOT touched (reading Task 37's saved summary JSON is allowed;
no new holdout computation). Every number goes beside BENCHMARK-v6.

Unless stated otherwise, "P-test" = Task 35 Step 2's design exactly
(unit = eligible pass, Y = net xG over events i+1 ... i+10, S = the
passer's leave-one-match-out mean with >= 100 elsewhere, g_oof, role
FE, team-match FE, SE clustered by passer), with S = v5 Decision
(cross-fitted). Regenerate Task 35's inputs with its own functions and
assert its v5 Decision coefficient reproduces (as Task 39 did) before
computing anything new.

## Step 0 — Commit this brief alone. Record the hash.

## Step 1 (1a) — Is it "where he usually plays"?
Add, each standardised: S_x, S_y = the passer's other-match mean
normalised starting x and y of his eligible passes; S_ev = his
other-match mean ev_chosen (cross-fitted v5). Models:
  A: + S_x + S_y        B: + S_ev        C: + S_x + S_y + S_ev
  D: role FE replaced by FE for the pass's exact StatsBomb position
     label (e.g. Right Center Back), with S_x, S_y, S_ev.
Report the Decision coefficient, CI and p in each, beside the base.

## Step 2 (1b) — Which roles carry it?
P-test within each Task 32 role (CB, FB, DM, CM, AM/W, FW), S
standardised within that role's rows. Report n players, coefficient,
CI, p, MDE per role. No correction is applied for the claim; report
Holm across the six for information.

## Step 3 (1c) — Outcome definition
(a) Y excluding shots taken by the passer himself.
(b) Horizon 5 events. (c) Horizon 15 events.
g refit for each Y with Task 35's function and settings.

## Step 4 (1d) — Inference
For the base model: two-way clustered SEs (passer and match), and a
passer-level cluster bootstrap (1,000 resamples of passers, seed
20260928) giving a 95% percentile CI.

## Step 5 (1e) — Size in football terms
Using the base coefficient per pass and each role's median eligible
passes per match: xG per match and per 38 matches for a player one SD
above his role's average Decision, for DM, CM, AM/W and FW. (Uses the
overall coefficient; state that assumption.)

## Step 6 (1f) — What the deep-midfield tests rule out
From Task 35 Step 3 (study) and Task 37 Step 3 (holdout summary JSON):
the upper 95% bound of the DM Decision coefficient, as a fraction of the
all-player coefficient in the same sample.

## Step 7 (2a) — The pre-existing "praised players" list
List L = plan v3 section 5's fixed list: Kroos, Modric, Verratti,
Busquets, De Bruyne, Xhaka, de Jong, Kimmich, Rodri, Pedri, Gundogan,
Grillitsch, Shaparenko (written before any of these measures).
For each measure M in {AV (Task 38), AV_vis (Task 38), RQ_rel (Task 34),
v5 Decision per pass (cross-fitted)}: compute each qualifying player's
within-role z-score (Task 32 roles; for PFF measures use the same role
via the player map). Statistic T = mean z of L-players present. p =
two-sided permutation p over 10,000 random relabellings of the same
number of players WITHIN roles (seed 20260928). Report which
L-players are present per measure, T and p. Pre-declared direction of
interest: lower on AV, AV_vis and RQ_rel.

## Step 8 (2c) — Availability thresholds
Recompute Task 38's AV for space in {2, 3, 5} m x lane in {1, 2, 3} m
(nine versions; the baseline refit each time, same settings). For
each: base rate, R1 (deep midfielders, as Task 38) and R2 (all outfield,
as Task 38): coefficient, CI, p.

## Step 9 (2d) — Space at reception vs availability, together
Unit = Task 38's R2 receptions (PFF WC2022). Add S_RQ = the receiver's
other-match mean RQ_rel from Task 34 (StatsBomb, all 292 matches except
this one; receivers with >= 100 receptions elsewhere), standardised.
Fit Y ~ S_AV + S_RQ + Task 38's controls, for all outfield and for deep
midfielders. Report both coefficients, CIs, p, n.

## Step 10 (3b) — One correction across all within-DM tests
Collect every within-DM results-test p-value reported in Tasks 35
(a)-(d), 37 Step 3, 38 (R2 AV, AV_vis) and 39 (move, hold), plus Steps
2 (DM row) and 9 (DM) of this task. Report raw and Holm-adjusted across
the whole family.

## HARD RULES
- Measurement only: no change to engine v5, v6 Decision, RQ, AV or
  tempo definitions except the declared variants in Steps 1, 3 and 8.
- Holdout untouched.
- Commit the results page after Step 6, then at the end.
- Memory gate as in Task 25.
- No memory writes. Don't edit docs/JOURNAL.md. No interpretation.
- When finished, reply only that the task is done plus commit hashes.

## Output
docs/results/41-vetting-round-2.md (template). Commit per rule 9.
