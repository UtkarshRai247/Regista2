# Regista 2: measuring deep-lying playmakers from free data

Research code for an MIT Sloan Sports Analytics Conference (SSAC27) research-paper submission. Solo author: Utkarsh Rai (University of Washington).

## What the project measures
The project asks which qualities of deep-lying midfielders ("registas") can be measured reliably from free event data. It also asks whether they belong to the player rather than his team, and whether they relate to team results. Every test was pre-registered and judged on data held back from its development.

The measures are:
- **Press resistance:** keeping the ball after receiving it under pressure, relative to what is typical for the situation.
- **Tempo choices:** how often a player speeds play up, recycles, or switches play, relative to the situation. These describe a player's style, not quality.
- **Quick and safe release under pressure.**
- **Pass-choice value (v5 Decision):** the value of the chosen pass option minus a typical choice.
- **Availability:** being open to receive, from tracking data.

What the evidence supports, with every number traced to a results page, is in the abstract draft (`docs/abstract/SSAC27-abstract-v2.md`) and the benchmark files (`docs/BENCHMARK-v*.md`). This README makes no claims beyond those.

The scorecard (`docs/scorecard/index.html`; public variant `docs/scorecard/index_public.html`) shows every deep midfielder with uncertainty intervals and an evidence tier per dimension.

## Data and credits
**Data: StatsBomb (open data)**: https://github.com/statsbomb/open-data.
- Before downloading or using it, accept StatsBomb's user agreement and register at the StatsBomb resource centre, as their open-data README asks.
- StatsBomb asks users to credit the data source as StatsBomb and to use their logo.
- TODO: add the StatsBomb logo from StatsBomb's Media Pack (no Media Pack copy is in this repository).

**Tracking: PFF FC / Gradient Sports World Cup 2022.**
- PFF data is **not redistributed** here: no raw PFF file is in this repository.
- PFF-derived numbers (the availability measure, "AV") appear in some results pages and in `docs/scorecard/index.html`. `docs/scorecard/index_public.html` omits them.
- Licence status: `docs/DATA_LICENSES.md`.

**Nothing under `data/` is committed except five small files:**
- `data/splits/match_split.csv` and `data/splits/cv_folds.csv`: match ids with split / fold labels, needed to reproduce the preregistered splits.
- `data/processed/player_season_metrics.parquet`: **engine v1, withdrawn; do not use.** Engine v1 was withdrawn (`docs/DECISIONS.md`, D-015). The file is kept only as the historical record behind the early results pages.
- `data/processed/worked_example.csv`: seven rows illustrating one pass.
- `data/expert_lists/selections.csv`: published media selections, with source URLs.

## Getting the data
Create the environment first: `python3.14 -m venv .venv && .venv/bin/pip install -r requirements.txt`.

| Dataset | What | How |
|---|---|---|
| Study sample | 299 StatsBomb open-data matches with 360 frames (Ligue 1 21/22 and 22/23, Bundesliga 23/24, La Liga 20/21, MLS 2023, World Cup 2022, Euro 2020, Euro 2024) | `.venv/bin/python src/decision_engine/pull_data.py` (statsbombpy, open data) |
| Holdout | 126 women's international matches (Women's Euro 2022 and 2025, Women's World Cup 2023) | `.venv/bin/python src/decision_engine/pull_holdout_data.py` |
| 2015/16 big five | 1,551 matches (Premier League, Bundesliga, La Liga, Serie A, Ligue 1) | Download the StatsBomb open-data ZIP, unzip into `data/raw_1516/open-data-master/`, then `.venv/bin/python src/engine_v2/task44_ingest.py` |
| Reserved | 64 further competition-seasons (1,985 matches) | Same open-data ZIP, then `.venv/bin/python src/engine_v2/task48_ingest.py` |
| PFF WC2022 | 64 World Cup 2022 matches of broadcast tracking and events | Not redistributed. Obtained from the author's source (see `docs/DATA_LICENSES.md`), then `src/pff/align.py --stage players`, `src/pff/frames.py`, `src/pff/align.py --stage clock` (order in `src/pff/align.py`) |

## Reproducing the headline results
Run each block from `src/engine_v2/` with the environment's Python (`../../.venv/bin/python <script>`), in order. The memory gate (at least 40% free and 3 GB available) is checked inside the later scripts.

- **Tasks 24-25 (engine v5: direction fix and rebuild):**
  1. `task24_evidence.py`
  2. `task25_step1.py`
  3. `value_models_v5_retrain.py`
  4. `grid_v2.py`
  5. `pass_success_v3.py`
  6. `ev_recompute_v4.py`
  7. `offside_diagnostic_v3.py`
  8. `policy_baseline_fix_v5.py`
  9. `policy_score_v8.py`
  10. `step8_regate.py`
  11. `falsification_v3.py`
  12. `crossfit_v5.py`
  13. `outcome_validation_crossfit_v5.py`
- **Task 35 (pass-level P-test, study sample):** `task35_step1_mde.py`, then `task35_ptest.py`.
- **Task 37 (holdout replication):** `task37_holdout_ptest.py`.
- **Task 44 (2015/16 big five):** `task44_ingest.py`, `task44_gate.py`, `task44_build.py`, `task44_tests.py`.
- **Task 48 (single-use confirmation on the reserved data):** `task48_ingest.py`, `task48_build.py`, `task48_tests.py`.
- **Tasks 52-53 (tempo development / replication):** `task52_split.py`, `task52_build.py`, `task52_tests.py`, then `task53_praised_audit.py`, `task53_build.py`, `task53_tests.py`.
- **Tasks 51 / 54 (scorecard):** `task51_scorecard.py`, `task51_outputs.py`, `task54_scorecard.py`, `task54_outputs.py`.

Each results page names its exact commands and output files.

## Where things live
| Path | Contents |
|---|---|
| `docs/specs/` | Every task brief (the preregistrations), written and committed before the task's results existed |
| `docs/results/` | One results page per task, **including every failed or null test** (template: `docs/results/TEMPLATE.md`) |
| `docs/BENCHMARK-v*.md`, `docs/benchmark/manifest-v*.txt` | Frozen benchmarks and checksums of the artifacts behind them (git tags `benchmark-v5` ... `benchmark-v9`) |
| `docs/DECISIONS.md` | Every methodology decision, with dates and reasons |
| `docs/DATA_LICENSES.md` | Licence and attribution status of each dataset |
| `docs/splits/` | The locked tempo development / replication split and the praised-list player ids |
| `docs/abstract/` | Abstract drafts |
| `src/` | All pipeline code (`decision_engine/` engine v1 and early studies; `engine_v2/` engine v2-v5 and Tasks 15-54; `tempo/`; `pff/`) |

## Licence
Code: MIT (see `LICENSE`). Data are not covered by this licence; see the data section above.
