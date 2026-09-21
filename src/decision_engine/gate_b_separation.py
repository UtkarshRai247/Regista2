"""
Task 01 — GATE B: Separation. STOP AND REPORT.

Full correlation matrix between Decision, Execution, Risk, progressive
passes/90, xA/90, and pass completion percentage, computed on the
per-player-per-competition-season table from Step 6. Per the spec:
report exactly as it comes out, do not proceed past this gate without an
instruction from the research lead.

Run: python src/decision_engine/gate_b_separation.py
"""
import json
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).parent.parent.parent / "data"
METRICS_PATH = DATA_DIR / "processed" / "player_season_metrics.parquet"

COLUMNS = [
    "decision_per_100", "execution_per_100", "risk_per_100",
    "progressive_passes_per_90", "xa_per_90", "completion_pct",
]


def main():
    df = pd.read_parquet(METRICS_PATH)
    corr = df[COLUMNS].corr()
    print(corr.round(3).to_string())

    flagged = []
    for i, a in enumerate(COLUMNS):
        for b in COLUMNS[i + 1:]:
            r = corr.loc[a, b]
            if abs(r) > 0.7:
                flagged.append({"pair": [a, b], "r": float(r)})

    result = {"correlation_matrix": corr.round(4).to_dict(), "n_rows": len(df),
              "pairs_above_0.7": flagged}
    (DATA_DIR / "gate_b_separation.json").write_text(json.dumps(result, indent=2))
    print(f"\nPairs with |r| > 0.7: {flagged if flagged else 'none'}")
    print("\n*** GATE B: reported above. STOP — do not proceed without research-lead instruction. ***")


if __name__ == "__main__":
    main()
