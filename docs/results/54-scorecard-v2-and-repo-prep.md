# Task 54: Scorecard v2 and repo preparation
Date: 2026-09-29
Status: BLOCKED. Stopped at B1: committed files under `data/` exist in the git history. Per the brief ("If data or a secret is found, STOP and report; do not rewrite history"), nothing after the scan was run and no history was rewritten.

## Checklist
| Section | Status |
|---|---|
| Step 0: brief + abstract draft committed by the research lead | COMPLETE (4fef446; later abstract edits 94b2eee, 054bf01 by the research lead) |
| B1: history scan | COMPLETE (scan run in full); result = STOP condition met (committed data under `data/`) |
| A1: tempo on Card A | NOT RUN (stopped at B1) |
| A2: tiers | NOT RUN |
| A3: HOLD_VARIATION interval | NOT RUN |
| A4: Card B stability | NOT RUN |
| A5: Figure 1 | NOT RUN |
| A6: Busquets / Kroos values | NOT RUN |
| A7: index.html + index_public.html | NOT RUN |
| B2: list of files with PFF-derived numbers | NOT RUN |
| B3: README.md | NOT RUN |
| B4: .gitignore / LICENSE / requirements.txt | NOT RUN |
| B5: JOURNAL.md / AGENTS.md not staged | COMPLETE (neither staged) |
| B6: command to make the repo public | NOT RUN |

## 1. Headline
- **Data found:** five files under `data/` are committed in the git history and tracked at HEAD, 229 KB in total. They are split files, a frozen metric parquet, a worked example and expert selections. `.gitignore` whitelists them deliberately.
- **Clean:**
  - no secret found;
  - no blob over 10 MB (the largest is 829 KB);
  - no author or committer email other than rai.utkarsh2007@gmail.com.
- **Emails in file contents:** besides the two allowed addresses, two PFF organisational addresses (`fchelp@pff.com`, `gradientsports.archive@pff.com`) appear in three committed docs.

## 2. What I did
Read-only git commands over all 228 commits (`git rev-list --all`); nothing was modified.
- **Paths:** `git log --all --name-only` gives every path ever committed (372), filtered for `data/` and for data-like extensions (parquet, json, jsonl, csv, zip, bz2, gz, pkl, joblib, feather, arrow).
- **Sizes:** `git rev-list --objects --all | git cat-file --batch-check` gives blob sizes; threshold 10 MB.
- **Secret paths:** scanned for `.env`, `id_rsa`, `id_ed25519`, `*.pem`, `*.key`, `credentials`, `secret`.
- **Secret contents:** `git grep` over every revision for:
  - AWS keys (`AKIA…`), private-key headers, GitHub tokens (`ghp_…`), `sk-…` keys, Slack tokens;
  - `api_key` / `secret` / `password` / `passwd` / `token` assigned a quoted value of 8 or more characters.
- **Emails:** in author and committer fields, and by a regex over file contents in every revision.
- **Committed `data/` files:** for each, when it was added and whether it is tracked now.

## 3. Numbers
**Committed files under `data/`** (all still tracked at HEAD):

| Path | Size (bytes) | Added in | Commits touching |
|---|---|---|---|
| `data/splits/match_split.csv` | 7,789 | a9021eb, 2026-09-20: "Commit discovery/confirmation match split (Task 04 Step 3, D-014)" | 1 |
| `data/processed/player_season_metrics.parquet` | 200,536 | 9db72ef, 2026-09-18: "Freeze Decision/Execution/Risk metric before market data join (D-008)" | 1 |
| `data/splits/cv_folds.csv` | 4,944 | e1b95c8, 2026-09-22: "Commit cross-fitting fold assignment (Task 09 Step 0/Part 1 Step 1)" | 1 |
| `data/processed/worked_example.csv` | 3,130 | f5cfec0, 2026-09-23: "Task 12: total-effect spec, leaderboard, worked example (Amendment v2-9)" | 1 |
| `data/expert_lists/selections.csv` | 13,656 | 3fe3a77, 2026-09-24: "Task 14b-prep: compile expert selection lists (compile only)" | 2 |

- No raw StatsBomb event, frame or lineup file, and no PFF file, was found among committed paths.
- Other committed data-like files outside `data/`:
  - `docs/results/05-study-a-candidates.csv`
  - `docs/splits/praised_ids.csv`
  - `docs/splits/tempo_split.csv`

**Large files:** none over 10 MB. The five largest blobs in history:
1. `docs/scorecard/index.html` (829,253 bytes)
2. `data/processed/player_season_metrics.parquet` (200,536)
3. `docs/scorecard/figure_praised.png` (132,384)
4. `docs/scorecard/figure_career.png` (70,883)
5. `docs/splits/tempo_split.csv` (61,419)

**Secrets:** no secret-like path and no content match in any revision.

**Emails:**
- Author and committer fields: `rai.utkarsh2007@gmail.com` only (456 author and committer lines).
- File contents across all revisions (occurrence counts):

| Address | Count |
|---|---|
| fchelp@pff.com | 808 |
| gradientsports.archive@pff.com | 450 |
| urai2@uw.edu | 3 |
| rai.utkarsh2007@gmail.com | 3 |

- At HEAD the two PFF addresses appear in `docs/CHAT-HANDOFF.md`, `docs/DATA_LICENSES.md` and `docs/results/00-data-audit.md`.

## 4. Deviations from the brief
None. The brief's STOP rule was followed: Part A and B2-B6 were not run, and history was not rewritten.

## 5. Problems and surprises
- **The five `data/` files were committed on purpose.** `.gitignore` whitelists exactly these paths. Their commit messages tie them to preregistration steps (a split, folds, a frozen metric, expert lists). They are derived files, not raw event data, but they are under `data/`, which is the brief's STOP condition. If B1's rule is applied as written, the repo cannot be made public until they are dealt with.
- **`player_season_metrics.parquet`** holds per-player metric values derived from StatsBomb data. Whether publishing derived values is covered by StatsBomb's user agreement is recorded as unresolved in `docs/DATA_LICENSES.md`.
- **The two PFF addresses** are organisational contacts from the PFF data folder and licensing note, not personal emails. They appear in committed docs.

## 6. Questions for the research lead
1. **The five committed `data/` files:** are they acceptable to publish, being intentionally committed derived and preregistration files? If so, should B1 continue and the rest of Task 54 (Part A, B2-B6) run? Or should they be removed, which would need a history rewrite that I will not do without an explicit instruction?
2. **Part A:** should Part A (scorecard v2, Figure 1) run while the B1 question is open? The brief's STOP was applied to the whole task.
3. **PFF addresses in docs:** keep `fchelp@pff.com` and `gradientsports.archive@pff.com` in `docs/DATA_LICENSES.md`, `docs/CHAT-HANDOFF.md` and `docs/results/00-data-audit.md`?

## 7. Files produced
- This page only. The scan used read-only git commands; its path list went to a temporary file (`/tmp/t54_paths.txt`, outside the repo).
- Commits: 164e291 (this page).
- Not staged (B5): `docs/JOURNAL.md` (pre-existing uncommitted change) and `AGENTS.md` (untracked).

## 8. Confidence
- **High for:** the path, size and author-email findings, which come directly from git object listings.
- **Pattern-based:** the secret scan. It would miss secrets in formats outside the listed patterns.
