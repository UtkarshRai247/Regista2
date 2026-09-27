"""
Task 21, Step 2: retrain both value models with the three new possession-
state features (`distance_to_nearest_teammate_u`, `teammates_within_5u`,
`teammates_within_10u`) added to `frame_ahead_features` / `STATE_FEATURES`
in value_models.py. Reuses `build_match_rows`, `train_one`, `run_t2`,
`EVENTS_DIR` from value_models.py UNCHANGED except for the two authorized
additions already made there. Writes to NEW output paths -- Task 19d's
`value_model_rows_v2.parquet`/`value_model_for_v2.json`/
`value_model_against_v2.json` (and every prior task's own originals) are
left untouched, so all prior tasks' results pages remain exactly
reproducible from their own recorded commits.

Run: python src/engine_v2/value_models_v3.py
"""
import json
import warnings
from pathlib import Path

import pandas as pd

from value_models import build_match_rows, train_one, run_t2, EVENTS_DIR

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
OUT_PATH = DATA_DIR / "processed" / "engine_v2" / "value_model_rows_v3.parquet"
MODEL_FOR_PATH = DATA_DIR / "processed" / "engine_v2" / "value_model_for_v3.json"
MODEL_AGAINST_PATH = DATA_DIR / "processed" / "engine_v2" / "value_model_against_v3.json"
SUMMARY_PATH = DATA_DIR / "engine_v2_step3_value_models_v3.json"
TASK19D_SUMMARY_PATH = DATA_DIR / "engine_v2_step3_value_models_v2.json"


def main():
    print("Task 21 Step 2: retraining M_for / M_against with possession-state features ...")
    match_ids = sorted(int(p.stem) for p in EVENTS_DIR.glob("*.parquet"))
    all_rows, n_total, n_no_loc, n_no_frame = [], 0, 0, 0
    for i, mid in enumerate(match_ids):
        rows, n, nl, nf = build_match_rows(mid)
        all_rows.extend(rows)
        n_total += n
        n_no_loc += nl
        n_no_frame += nf
        if (i + 1) % 50 == 0:
            print(f"  {i + 1}/{len(match_ids)} matches, rows so far={len(all_rows)}")

    df = pd.DataFrame(all_rows)
    df.to_parquet(OUT_PATH)
    print(f"  total raw events={n_total}, no_location={n_no_loc}, no_frame={n_no_frame}, usable rows={len(df)}")

    print("  training M_for ...")
    res_for = train_one(df, "label_for")
    print(f"    n_train={res_for['n_train']}, n_test={res_for['n_test']}, positive_rate={res_for['positive_rate']:.4f}, AUC={res_for['auc']:.4f}")
    print("  training M_against ...")
    res_against = train_one(df, "label_against")
    print(f"    n_train={res_against['n_train']}, n_test={res_against['n_test']}, positive_rate={res_against['positive_rate']:.4f}, AUC={res_against['auc']:.4f}")

    res_for["model"].save_model(str(MODEL_FOR_PATH))
    res_against["model"].save_model(str(MODEL_AGAINST_PATH))

    print("  T2 (value model sees the defence, with possession-state features) ...")
    t2 = run_t2(res_for["model"], df)
    print(f"    {t2}")

    task19d_summary = json.loads(TASK19D_SUMMARY_PATH.read_text())

    summary = {
        "n_total_events": n_total, "n_no_location": n_no_loc, "n_no_frame": n_no_frame,
        "n_usable_rows": len(df), "frame_coverage_share": (n_total - n_no_loc - n_no_frame) / n_total if n_total else None,
        "M_for": {k: v for k, v in res_for.items() if k != "model"},
        "M_against": {k: v for k, v in res_against.items() if k != "model"},
        "T2": t2,
        "task19d_M_for": task19d_summary["M_for"], "task19d_M_against": task19d_summary["M_against"], "task19d_T2": task19d_summary["T2"],
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
    print(f"\nWrote {SUMMARY_PATH}")
    return summary


if __name__ == "__main__":
    main()
