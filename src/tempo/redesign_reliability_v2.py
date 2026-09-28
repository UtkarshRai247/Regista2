"""
Task 26, Step 2 (continued): re-run the reliability gate (T-2.4) on
`redesign_metrics_v2.py`'s corrected-coordinate residuals. Reuses
`reliability.reliability_sweep_pass_level`/`classify`/`THRESHOLDS`/
`GATE_THRESHOLD` and `redesign_reliability.py`'s own metric functions
unchanged, via monkeypatched residual-file paths.

Run: python src/tempo/redesign_reliability_v2.py
"""
import json
import warnings
from pathlib import Path

import redesign_reliability as rr

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
rr.MOVE_RESID_PATH = DATA_DIR / "processed" / "tempo_redesign_move_residuals_v2.parquet"
rr.HOLD_RESID_PATH = DATA_DIR / "processed" / "tempo_redesign_hold_residuals_v2.parquet"
rr.SUMMARY_PATH = DATA_DIR / "tempo_step3b_reliability_v2.json"

if __name__ == "__main__":
    rr.main()
