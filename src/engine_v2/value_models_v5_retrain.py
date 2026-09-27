"""
Task 25, Step 2 (continuing Task 24's Step 4): retrain M_for/M_against
on the already-built `value_model_rows_v5.parquet` (Task 24's
corrected-coordinate, in-possession, own-event-label rows). This is a
small addendum to `value_models_v5.py`, needed because Task 24's own
script gates training on ITS OWN G1/G2 checkpoint (which technically
still reads G1 as failing, 2.30% > 1%) -- Task 25's Step 1 diagnostic
established, with its own fixed decision rule, that the residual is
the known 360-visibility limitation, not a remaining coordinate error,
and its brief explicitly instructs continuing to the rebuild. No row-
building logic is touched or duplicated here; the rows themselves are
unchanged from Task 24's own build.

Run: python src/engine_v2/value_models_v5_retrain.py
"""
import json
import warnings
from pathlib import Path

import pandas as pd

from value_models import train_one, run_t2

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
ROWS_PATH = DATA_DIR / "processed" / "engine_v2" / "value_model_rows_v5.parquet"
MODEL_FOR_PATH = DATA_DIR / "processed" / "engine_v2" / "value_model_for_v5.json"
MODEL_AGAINST_PATH = DATA_DIR / "processed" / "engine_v2" / "value_model_against_v5.json"
SUMMARY_PATH = DATA_DIR / "engine_v2_step3_value_models_v5.json"
TASK15_SUMMARY_PATH = DATA_DIR / "engine_v2_step5_value_models.json"
TASK19D_SUMMARY_PATH = DATA_DIR / "engine_v2_step3_value_models_v2.json"


def main():
    print("Task 25 Step 2: retraining M_for/M_against on value_model_rows_v5.parquet ...")
    train_df = pd.read_parquet(ROWS_PATH)
    print(f"  n_rows={len(train_df)}")

    print("  training M_for ...")
    res_for = train_one(train_df, "label_for")
    print(f"    n_train={res_for['n_train']}, n_test={res_for['n_test']}, positive_rate={res_for['positive_rate']:.4f}, AUC={res_for['auc']:.4f}")
    print("  training M_against ...")
    res_against = train_one(train_df, "label_against")
    print(f"    n_train={res_against['n_train']}, n_test={res_against['n_test']}, positive_rate={res_against['positive_rate']:.4f}, AUC={res_against['auc']:.4f}")

    res_for["model"].save_model(str(MODEL_FOR_PATH))
    res_against["model"].save_model(str(MODEL_AGAINST_PATH))

    print("  T2 (magnitude verdict AND sign) ...")
    t2 = run_t2(res_for["model"], train_df)
    print(f"    {t2}")
    t2_sign = "POSITIVE (more numerical advantage ahead -> higher scoring probability)" if t2["diff"] > 0 else \
              "NEGATIVE (more numerical advantage ahead -> lower scoring probability)"
    print(f"    T2 sign: {t2_sign}")

    task15_summary = json.loads(TASK15_SUMMARY_PATH.read_text())
    task19d_summary = json.loads(TASK19D_SUMMARY_PATH.read_text())

    summary = {
        "n_rows": len(train_df),
        "M_for": {k: v for k, v in res_for.items() if k != "model"},
        "M_against": {k: v for k, v in res_against.items() if k != "model"},
        "T2": t2, "T2_sign": t2_sign,
        "task15_M_for": task15_summary["M_for"], "task15_M_against": task15_summary["M_against"], "task15_T2": task15_summary["T2"],
        "task19d_M_for": task19d_summary["M_for"], "task19d_M_against": task19d_summary["M_against"], "task19d_T2": task19d_summary["T2"],
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
    print(f"\nWrote {SUMMARY_PATH}")
    return summary


if __name__ == "__main__":
    main()
