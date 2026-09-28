"""
Task 26, Step 1(b): compute V_net_success/V_net_turnover/EV on the
holdout corpus using the FROZEN engine v5 value models
(`value_model_for_v5.json`/`value_model_against_v5.json`). No
retraining -- reuses `ev_policy.build_ev_for_match` unchanged via
monkeypatched I/O directories.

Run: python src/engine_v2/ev_compute_holdout.py
"""
import warnings
from pathlib import Path

import xgboost as xgb

import ev_policy as evp

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
MODEL_FOR_PATH_V5 = DATA_DIR / "processed" / "engine_v2" / "value_model_for_v5.json"
MODEL_AGAINST_PATH_V5 = DATA_DIR / "processed" / "engine_v2" / "value_model_against_v5.json"

evp.EVENTS_DIR = DATA_DIR / "raw_holdout" / "events"
evp.FRAMES_DIR = DATA_DIR / "raw_holdout" / "frames"
evp.SCORED_DIR = DATA_DIR / "processed" / "engine_v2" / "options_scored_holdout"
evp.EV_DIR = DATA_DIR / "processed" / "engine_v2" / "options_ev_holdout"


def main():
    print("Task 26 Step 1(b): computing EV on the holdout with the frozen engine v5 value models ...")
    model_for = xgb.XGBClassifier()
    model_for.load_model(str(MODEL_FOR_PATH_V5))
    model_against = xgb.XGBClassifier()
    model_against.load_model(str(MODEL_AGAINST_PATH_V5))

    match_ids = sorted(int(p.stem) for p in evp.SCORED_DIR.glob("*.parquet"))
    n_rows = 0
    for i, mid in enumerate(match_ids):
        n = evp.build_ev_for_match(mid, model_for, model_against)
        if n:
            n_rows += n
        if (i + 1) % 20 == 0:
            print(f"  {i + 1}/{len(match_ids)} matches, EV rows so far={n_rows}")
    print(f"  total EV rows: {n_rows}")
    print(f"\nWrote per-match files to {evp.EV_DIR}")
    return n_rows


if __name__ == "__main__":
    main()
