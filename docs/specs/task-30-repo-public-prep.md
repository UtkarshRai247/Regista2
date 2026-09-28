# Task 30 — Prepare the repo to go public (do NOT make it public)

Written 2026-09-28 by the research lead. SSAC requires an open-source
repository linked from the abstract. This task makes the repo safe and
readable in public. The author flips the visibility switch himself.

## Step 0 — Commit this brief alone. Record the hash.
In the same step, commit `docs/abstract/SSAC27-abstract-draft.md` in a
second commit.

## Step 1 — Nothing that must stay private is in git history
Across ALL of git history (not just the working tree), report:
(a) any file under `data/` or any `.parquet`, `.json` of StatsBomb raw
    data, `.csv` of events or frames ever committed;
(b) any secret: API keys, tokens, passwords, `.env` files, SSH keys,
    personal email addresses other than the author's university address;
(c) any file over 10 MB.
If (a) or (b) finds anything, STOP and report — do not rewrite history
without the author's explicit go-ahead in chat.

## Step 2 — README.md at the repo root (replace or create)
Plain and short. Sections: what the project measures (one paragraph, no
results claims beyond what the abstract draft states); data source with
the credit "Data: StatsBomb (open data)" and a link to
https://github.com/statsbomb/open-data and a note that users must
accept StatsBomb's user agreement and register at the StatsBomb resource
centre; the StatsBomb logo if a copy is available from their media pack
(if not, leave a clearly marked TODO line — do not invent or draw one);
how to download the data (the repo's existing ingestion script and
command); how to reproduce the engine v5 pipeline end to end (the exact
script sequence from Tasks 24-29, in order); where the pre-registrations,
decisions, journal and every results page live (docs/specs, docs/results,
docs/DECISIONS.md, docs/JOURNAL.md), stating that failed tests are kept
on purpose.

## Step 3 — Housekeeping
- `.gitignore` covers `data/`, `.venv/`, `__pycache__/`, `.DS_Store`,
  model files and outputs.
- LICENSE file: MIT, copyright holder "Utkarsh Rai", year 2026 — unless
  the author says otherwise in chat before this task runs.
- `requirements.txt` (or lock file) reflects the packages actually
  imported by the engine v5 pipeline, with versions from the current
  `.venv`.
- Do NOT stage `docs/JOURNAL.md` (research lead is updating it).

## Step 4 — Report
List every file added or changed, the history scan results, and the
exact command the author runs to make the repo public (for example the
GitHub setting path or `gh repo edit --visibility public`), without
running it.

## HARD RULES
- Do NOT change visibility. Do NOT push history rewrites.
- No engine or analysis changes.
- No memory writes.
- When finished, reply only that the task is done plus commit hashes.

## Output
docs/results/30-repo-public-prep.md (template). Commit per rule 9.
