# Task 45 — Vetting press resistance: is it the team, or just safe passing?

Written 2026-09-28 by the research lead after reading
docs/results/44-big-five-1516.md, before any result. This is the SECOND
use of the 2015/16 data (labelled so); study sample and PFF also allowed;
holdout spent. Measurement only: PR2_flag's definition is unchanged.

Answer to Task 44 Q1: no HOLD_VARIATION table is wanted.

## Why
Task 44 found press resistance (PR2_flag_keep) is a stable deep-midfield
trait on 1,551 fresh matches, strongly separates deep midfielders, and
the pre-existing praised list scores higher (Holm p = 0.0044). Two
obvious attacks could explain all of it without any individual skill:
(1) TEAM STYLE: the top of the table is dominated by dominant possession
sides (PSG, Napoli, Juventus, Barcelona, Real Madrid, Lazio). Teammates
who give options make keeping the ball easier.
(2) SAFE PASSING: keep = "the spell ends in a completed pass", so a
player who always plays the short, safe ball scores high whether or not
he beats pressure.

## Step 0 — Commit this brief alone. Record the hash.

## Step 1 — Team-adjusted press resistance (2015/16)
A1: PR2_flag_keep with team style removed: regress unit-level
PR2_flag_keep (outcome - p_oof) on team x season fixed effects, weighted
equally per unit; player score = mean residual. Also report the team FE
share of variance.
Report within the 185 deep midfielders: stability (Task 38's method),
Q test, count above/below (Task 29's method), the praised list (Task 41
Step 7's method, direction higher), and Spearman vs unadjusted.

## Step 2 — Team- and safe-passing-adjusted
A2: as A1, and additionally residualise the PLAYER score on his
completion rate, share of passes under 15 units, and share of passes
that go backward or sideways (end x - start x < 0), all from his
eligible passes (weighted least squares across players, weights =
pressured receptions). Report the same outputs as Step 1.
Also report, within deep midfielders, raw correlations of unadjusted
PR2_flag_keep with those three passing-style variables.

## Step 3 — League
For unadjusted, A1 and A2: stability and praised-list T within each
league separately (report n; no claim), and with league FE added to A1.

## Step 4 — Praised list robustness
For unadjusted, A1 and A2: leave-one-out T and p dropping each of the
five present players in turn.

## Step 5 — Results link, adjusted (report only)
Task 44's P-test (DM and all, Y_F3 and net xG) with S = the player's
other-match A1 score, then A2 score. Same design and controls.

## Claim rule (fixed now)
The statement "keeping the ball under pressure is a stable deep-midfield
trait on which the pre-existing praised list scores higher, beyond team
style and safe passing" is allowed only if A2 has deep-midfield
stability >= 0.60 AND a praised-list p < 0.05 in the higher direction
after Holm across A1 and A2. If only A1 passes, the statement drops
"and safe passing". If neither passes, no statement beyond Task 44's
unadjusted result, which is then described as possibly team style.

## HARD RULES
- No change to PR2_flag or any earlier definition or artifact.
- Holdout untouched.
- No memory writes. Don't edit docs/JOURNAL.md. No interpretation.
- When finished, reply only that the task is done plus commit hashes.

## Output
docs/results/45-press-resistance-vetting.md (template). Commit per rule 9.
