# Regista 2 — Roadmap

## Deadlines (Eastern Time)
- Oct 1 2026, 11:59pm — abstract due (target submission: Sep 30)
- Late Oct 2026 — full paper requests sent
- Dec 4 2026, 11:59pm — full paper due if selected

## The five pillars (from the research plan)
1. Decision engine: value function + full action space + behavior-policy
   baseline. Decomposes into Decision / Execution / Risk.
2. Visibility calibration: use full tracking data to measure and correct
   the bias caused by partial freeze-frame visibility.
3. Hierarchical model: separate player skill from team, opponent,
   game state and pitch zone; produce uncertainty intervals.
4. Outcome and market grounding: does decision quality predict future
   team performance, and is it priced into player market value?
5. Role discovery (CUT for SSAC — may return later).

Off-ball availability extension: CUT for SSAC.

## Phase 1 — Abstract sprint (Sep 18 – Sep 30)
- Task 0: data audit + license check (Claude Code)
- Literature check on Pillars 2 and 4 (research lead)
- GO/NO-GO 1 (Sep 20): choose the headline pillar
- Analysis plan written and frozen BEFORE results are run (Sep 20-21)
- Task 1: minimum credible evidence for the headline pillar (Sep 21-24)
- GO/NO-GO 2 (Sep 25): submit / reframe as null result / fall back
- Robustness, abstract draft, repo cleanup (Sep 25-29)
- Submit Sep 30

## Phase 2 — Waiting period (Oct 2 – Oct 25)
Build Pillar 1 end to end. Checkpoint Oct 25: running end to end.

## Phase 3 — Full paper build (Oct 26 – Nov 22)
Pillar 3, plus the full version of the non-headline pillar.
Checkpoint Nov 15: all results frozen. Unfinished work is cut.

## Phase 4 — Writing (Nov 23 – Dec 4)
Draft, figures, reproducibility check, final repo. Submit Dec 3.

## Status
Current task: Task 0 (data audit)
Headline pillar: UNDECIDED — set at GO/NO-GO 1

---

## REVISED ROADMAP — 2026-09-20 (supersedes Phases 1-4 above)

Headline pivoted (D-012) to three studies on one engine, governed by
docs/specs/analysis-plan-v2.md. Market work closed.

| Date | Task | Gate |
|---|---|---|
| Sep 20 | Task 04 situation context — DONE | — |
| Sep 20 | Task 05 Study A discovery — DONE | — |
| Sep 20 | Task 06 Study A confirmation + Gate D — DONE | Gate D |
| Sep 21-22 | Task 07 Study A post-hoc checks + Study B | Gate E |
| Sep 23 | Task 08 Study C + reliability audit | — |
| Sep 24-25 | Task 09 Cross-fitting (Amendment v2-4) | Robustness rule |
| Sep 26 | Go/No-Go 2: which study leads | Decision |
| Sep 27 | Leaderboard + face validity | — |
| Sep 27-28 | Abstract draft, two figures | — |
| Sep 29 | Repo cleanup, make public | — |
| Sep 30 | Submit | — |

Deferred to the full paper: type-aware models, out-of-sample
recalibration, EV shrinkage before maxima (a Regista 2.1 engine).
