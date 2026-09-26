"""
Task 19d, Step 3 (continued): recomputes V_net_success/V_net_turnover/EV
corpus-wide using the CORRECTED `state_features_batch` (features.py,
already fixed) and the RETRAINED value models (value_models_v2.py).
Reuses `ev_policy.build_ev_for_match` unchanged (it already takes
model_for/model_against as parameters) via monkeypatching its output
directory -- Task 15's original `options_ev/` (built with the buggy
`defensive_line_x` and the OLD value models) is left untouched, so
Tasks 15/17/18/19/19c's own results remain reproducible from their own
commits. `options_scored/` (the pass-success-scored input, unaffected
by this task -- the pass-success model and its features were never
touched) is read as-is.

Run: python src/engine_v2/ev_recompute_v2.py
"""
import warnings
from pathlib import Path

import xgboost as xgb

import ev_policy as evp

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
MODEL_FOR_PATH_V2 = DATA_DIR / "processed" / "engine_v2" / "value_model_for_v2.json"
MODEL_AGAINST_PATH_V2 = DATA_DIR / "processed" / "engine_v2" / "value_model_against_v2.json"

evp.EV_DIR = DATA_DIR / "processed" / "engine_v2" / "options_ev_v2"


def main():
    print("Step 3: recomputing EV corpus-wide with the corrected feature + retrained value models ...")
    model_for = xgb.XGBClassifier()
    model_for.load_model(str(MODEL_FOR_PATH_V2))
    model_against = xgb.XGBClassifier()
    model_against.load_model(str(MODEL_AGAINST_PATH_V2))

    match_ids = sorted(int(p.stem) for p in evp.SCORED_DIR.glob("*.parquet"))
    n_rows = 0
    for i, mid in enumerate(match_ids):
        n = evp.build_ev_for_match(mid, model_for, model_against)
        if n:
            n_rows += n
        if (i + 1) % 50 == 0:
            print(f"  {i + 1}/{len(match_ids)} matches, EV rows so far={n_rows}")
    print(f"  total EV rows: {n_rows}")
    print(f"\nWrote per-match files to {evp.EV_DIR}")
    return n_rows


if __name__ == "__main__":
    main()
