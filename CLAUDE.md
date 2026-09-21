# Regista 2 — Project Guide

## What this is
Research project for the MIT Sloan Sports Analytics Conference (SSAC27)
Research Papers Competition. Abstract due Oct 1 2026. Full paper due
Dec 4 2026 if selected. Solo author: Utkarsh Rai (UW).

Subject: measuring the decision quality of deep-lying creative
midfielders from free public soccer data. Successor to "Regista 1"
(the Architect Framework).

## Roles — read this carefully
- The research lead is Claude in a separate chat window. ALL
  methodology, evaluation design, metric definitions, and
  interpretation decisions are made there.
- You (Claude Code) are the builder. You implement briefs, report
  results honestly, and flag problems.
- The user is the messenger between the two. He is not writing specs
  or configs by hand. Do not ask him to make methodology decisions.

## Rules for you
1. Do not invent methodology. If a brief is ambiguous or you think the
   approach is wrong, STOP and write the question into your results
   page rather than choosing for yourself.
2. Never silently change a metric definition, a filter, a sample, or a
   model choice that a brief specified. If you must deviate, say so
   loudly at the top of the results page.
3. Report negative, null, and broken results exactly as they are. A
   failed result is useful. A result that quietly got massaged is not.
4. Always report sample sizes, and uncertainty wherever a number is
   compared to another number.
5. No new dependencies without saying why. Keep the environment
   reproducible.
6. Every task ends by writing a results page (see
   docs/RESULTS_TEMPLATE.md) to docs/results/<task-id>.md.
7. Append every methodology decision you are TOLD to make into
   docs/DECISIONS.md. Do not add decisions you made yourself — raise
   those as questions instead.

## Hardware constraints
MacBook Pro, Apple M4, 16GB unified memory. No CUDA. Assume:
- Gradient-boosted trees and small neural nets are fine.
- Large transformer training is NOT available. Do not propose it.
- Watch memory on full-season event data; chunk where needed.

## Repo layout
/data/raw        — downloaded datasets, never edited, never committed
/data/processed  — derived files, reproducible from scripts
/src             — pipeline code
/notebooks       — exploration only, never the source of a result
/docs            — roadmap, decisions, results pages
/docs/results    — one page per task

## Open-source requirement
SSAC requires a public repo with the data used. Every dataset must
have its license and attribution recorded in docs/DATA_LICENSES.md
before we publish. If a dataset cannot be redistributed, we record
the download script instead of the data, and say so.

## Reproducibility
Every number in the paper must be regenerable from scripts in /src by
a single documented command. No result lives only in a notebook.

## Standing routines

1. After finishing any task I ask for, write the results page using
   `docs/results/TEMPLATE.md`, save it as `docs/results/NN-name.md`
   (NN = next unused number), and show me its contents.
2. When I say "wrap up", update `docs/STATUS.md` in under 15 lines:
   done, next, open problems. Then show me the final section.

## Reporting discipline

These exist because each one has already gone wrong.

1. "Print" means the literal text appears in your reply. A file-read
   tool call is not printing. Never write that you showed, printed, or
   displayed something unless the text is actually in the reply body.
2. Never report a task COMPLETE without a per-section checklist. List
   every section of the brief by name with COMPLETE / PARTIAL / NOT RUN.
   Partial completion of any section makes the task PARTIAL.
3. Running a subset of what a brief specifies IS a deviation. If the
   brief lists three reference event types and you use one, that goes in
   Section 4 of the results page. So does any sample smaller than asked.
4. Do not make research decisions. You do not choose the headline, make
   go/no-go calls, cut scope, defer spec items to a later task, or
   recommend a direction. If something in a brief looks unnecessary or
   better done later, that is a question for Section 6, not a choice you
   make. Reporting a finding is your job; deciding what it means for the
   project is not.
5. The headline of a results page must reflect the weakest evidence, not
   the most promising. If a
9. At the end of every task, commit all new or changed files under
   src/ and docs/ (never data/). Record the commit hash in Section 7 of
   the results page.
