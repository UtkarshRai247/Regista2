# Task 46 — Player or team? And spatial vs physical press resistance

Written 2026-09-28 by the research lead after reading
docs/results/45-press-resistance-vetting.md, before any result.
DEVELOPMENT task (exploratory): study sample (292 matches), PFF WC2022,
and 2015/16 (third use, labelled). Holdout spent.

RESERVED — must NOT be read by this task or any task until the
confirmation brief: every StatsBomb competition-season not already used,
in particular La Liga 2004/05-2020/21, Premier League 2003/04, FIFA
World Cup 2018 (if present), Copa America 2024, Indian Super League
2021/22 and all non-360 Champions League seasons. They sit in
data/raw_1516/open-data-master/; list them by id and do not open them.

Answer to Task 45 Q1: yes, the A2 fit population was intended.

## Why
Task 45's A1 removed each TEAM's mean. With one season, a player and his
team are almost the same thing, so A1 compares Busquets with Iniesta and
Xavi rather than removing "Barcelona's style". That cannot tell team
style from good players clustering at good teams. The standard way to
separate them is players seen in MORE THAN ONE team: club and country.
Separately, the author proposes two kinds of press resistance: SPATIAL
(finding space to be the outlet) and PHYSICAL (asking for the ball while
marked, and keeping it), rarely excellent together.

## Step 0 — Commit this brief alone. Record the hash.

## Part A — Does press resistance travel with the player? (movers)
Measure: PR2_flag_keep (Task 44 Step 2 definition), unadjusted.
A-i (PRIMARY for Part A): study sample. Units = player x team context
    (club or national team, as Study B defines contexts). Players with
    >= 2 contexts of >= 30 pressured receptions each. Correlation of the
    player's PR2_flag_keep between contexts, disattenuated and
    bootstrapped exactly as Study B's PH-B2. Also Study B's variance
    split (player vs team context, crossed random effects, parametric
    bootstrap interval) on PR units. Report n, r_obs, reliabilities,
    r_true and CI, S share and CI; all players and deep midfielders.
A-ii: 2015/16 club score vs study-sample national-team score for
    players in both (>= 50 and >= 30 pressured receptions). Same
    disattenuated correlation. State the time gap plainly.
Part A claim (fixed now): "press resistance travels with the player
    across teams" if A-i's r_true 95% lower bound > 0 (all players);
    the deep-midfield version is reported, and claimed only if its own
    lower bound > 0.

## Part B — Spatial vs physical
Definitions (fixed now):
- PHYSICAL-WILLINGNESS W: share of a player's completed receptions that
  are PRESSURED (Task 44's flag rule), context-adjusted: cross-fitted
  XGBoost classifier (Task 42's settings) of PRESSURED on reception x, y,
  play pattern, period, minute, score difference; W = mean(PRESSURED -
  p_oof). Computed on 2015/16 and on the study sample.
- PHYSICAL-SUCCESS: PR2_flag_keep (unadjusted), as before.
- SPATIAL S1 (study sample, 360): RQ_rel (Task 34).
- SPATIAL S2 (PFF WC2022): AV_out = Task 38's AV restricted to moments
  where the PASSER is under pressure (pressureType != 'N'), baseline
  refit on those moments with Task 38's settings.
Tests:
B1 Stability of W on 2015/16 (Task 38's method, >= 10 matches): deep
   midfielders and all players; bar 0.60.
B2 Trade-off, within deep midfielders (report all players too):
   Pearson r with 95% CI between each spatial measure and each physical
   measure (S1 with W and PR on the study sample; S2 with W and PR on
   WC2022 StatsBomb matches); and the number of players in the top
   quartile of BOTH vs the number expected if independent
   (hypergeometric p). The author's hypothesis: negative r / fewer than
   expected in both.
B3 Results: Task 44's P-test on 2015/16 with S = other-match W (all
   players and deep midfielders; Y_F3 and net xG; retention control).
   Also with S = W and S = PR2_flag_keep together.
Part B is exploratory; any result must be confirmed on the RESERVED
data before it is claimed.

## HARD RULES
- Do not open RESERVED data. Holdout untouched.
- No change to earlier definitions or artifacts.
- Memory gate as in Task 25. Commit after Part A, then at the end.
- No memory writes. Don't edit docs/JOURNAL.md. No interpretation.
- When finished, reply only that the task is done plus commit hashes.

## Output
docs/results/46-movers-and-spatial-physical.md (template). Commit per rule 9.
