# Task 10 — Interval validity, outcome validation, detectable-effect audit

Governing document: docs/specs/analysis-plan-v2.md, Amendments v2-1 to
v2-7. Three independent parts; do them in order and commit after each.

## Step 0 — No new amendment to commit. Confirm the plan's SHA-256 is
unchanged from ceafdcd and record it.

## PART A — Study B interval method (v2-6.1)
Select the interval method for S by SIMULATED COVERAGE, not by outcome.
1. Implement three methods: (i) cluster bootstrap with fresh ids (the
   Task 08 version), (ii) parametric bootstrap — simulate unit means
   from the fitted model on the real design (same players, team
   contexts and stage-1 SEs), refit, take percentiles, (iii)
   profile-likelihood interval for S from the REML objective.
2. Coverage test: 100 simulated datasets on the REAL design at the
   fitted variances (var_player 4.9024e-7, var_team 2.5967e-7, true
   S = 0.6537). For each, build all three 95% intervals. Report each
   method's coverage and mean width. Bootstraps use B = 200 draws
   inside each simulation. If projected runtime exceeds 2 hours, cut to
   50 simulations and disclose it.
3. PRIMARY = coverage closest to 0.95 among methods with coverage
   >= 0.90. If none reaches 0.90, Study B reports the point estimate
   with NO interval and is descriptive only.
4. Report all three methods' intervals on the REAL data, then re-apply
   the v2-5.4 tier rules using the primary interval. Report Tier 1 and
   Tier 2 verdicts. The rules are fixed.

## PART B — Outcome validation (v2-6.3)
Unit: team-match (expect 598; report the actual count and how it is
built). Predictor: that team's mean Decision in that match, from the
frozen (non-cross-fitted) per-pass table.
Outcomes: team xG in that match (primary), team goals (secondary).
Build xG per team-match by summing StatsBomb shot xG for that team in
that match; report how many matches have complete shot data.
  H-O1: xG ~ Decision + possession share + competition-season fixed
        effects (+ home/away if derivable; report whether it is).
  H-O2: H-O1 plus the team's completion rate, progressive-pass rate and
        xA per pass in that match.
Standard errors clustered by team context. Report coefficients in xG per
SD of Decision, with CIs, plus n and R-squared. Repeat both for goals.
Report exactly as they come out, including nulls or negative signs.

## PART C — Detectable-effect audit (v2-7.1)
For all 107 analyzable pairs, using each pair's confirmation-half
bootstrap SE of G: minimum detectable effect at 80% power
(2.802 x SE), converted to L units with that pair's own pass rate.
Report: the full 107-row table (pair, SE, MDE in G units, MDE in L
units), the median MDE in L, and the share of pairs where an effect of
1.0 L and of 0.5 L would have been detected.

## HARD RULES
- No changes to definitions, thresholds or claim rules.
- Full tables, nothing filtered or sorted by effect size.
- No interpretation for the paper. No memory writes. Don't edit
  docs/JOURNAL.md.
- If Part A's runtime blows up, do Parts B and C first and report A's
  status honestly.
- When finished, reply only that the task is done plus commit hashes.

## Output
docs/results/10-validation.md (template). Commit per rule 9.
