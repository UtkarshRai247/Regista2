# Task 06 — Study A: confirmation, Gate D, sensitivity checks

Governing document: docs/specs/analysis-plan-v2.md including Amendments
v2-1 AND v2-2. Read both fully first. v2-2 replaces Gate D's reference
group and pass criterion.

## Step 0 — Commits
1. Commit CLAUDE.md (the research lead repaired its truncated Reporting
   discipline list; items 5-8 were missing) in its own commit.
2. Commit Amendment v2-2 in its own commit. Record both hashes and the
   new SHA-256 of analysis-plan-v2.md in the results page.

## Step 1 — Confirmation statistics (the 10 candidates ONLY)
Load confirmation-half matches. For each of the 10 candidates in
docs/results/05-study-a-candidates.csv, compute on the confirmation half:
G, 95% CI, P, s, L, n passes, n matches — same code path as Task 05.
One-sided bootstrap p-value for G > 0: (1 + number of draws with G <= 0)
/ 1001, from 1,000 match-resampling draws, seed 20260920.
Benjamini-Hochberg across the 10 at q = 0.05.
CONFIRMED = BH-significant AND P > 0.5 AND L >= 0.5 (plan 3.4).
Do NOT compute G for any non-candidate pair on the confirmation half.

## Step 2 — Gate D (Amendment v2-2) for all 10 candidates
Report for every candidate, confirmed or not, clearly labeled.
Realized value: reuse the Execution definition
(src/decision_engine/decompose.py). Bias_k, Bias_ref, Delta, Delta's 95%
CI (1,000 match draws, confirmation half), the candidate's confirmation
G, and PASS/FAIL under v2-2.3. Also relative completion calibration in
percentage points.

## Step 3 — Pooled type-level diagnostic (v2-2.4)
Delta for each of the 9 option types pooled across all 18 cells,
confirmation half, with CIs. Descriptive only.

## Step 4 — Sensitivity checks for every CONFIRMED candidate
On the confirmation half, all four, reported in full including failures:
 a. mean EV of type k instead of max (and of type j likewise)
 b. high-visibility frames only (>= 18 visible players)
 c. each competition-season separately (sign, G, n; only where >= 100
    qualifying passes)
 d. tournaments only (World Cup 2022, Euro 2020, Euro 2024)

## HARD RULES
- No new candidates. No changes to thresholds. The 10 are fixed.
- Full tables for Steps 1-4; nothing filtered or sorted by effect size.
- No interpretation of what the results mean for the paper.
- Do not edit docs/JOURNAL.md. No memory writes.

## Output
docs/results/06-study-a-confirmation.md (template). Commit per rule 9.
