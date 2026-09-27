"""
Task 23, Step 2 (D2): is a ball behind the defence dangerous IN THE
MIDDLE specifically? No model, feature, or threshold changes -- this
only measures, using Task 22's already-corrected rows
(value_model_rows_diagnostic_v4.parquet: in-possession rows, new
labels that count the event's own outcome).

Splits by band (80-100, 100-120) x channel (CENTRAL = |ball_y-40|<=10,
WIDE = everything else) x beyond line (yes/no). Reports n,
P(score in 10), P(concede in 10) per cell, plus the same split with
play_pattern "From Corner"/"From Free Kick"/"From Throw In" rows
removed as a sensitivity check. Nothing is gated here -- this script
only reports; the research lead's decision rules (R1-R4 in the brief)
are applied by hand against this output, not by this script.

Run: python src/engine_v2/task23_d2.py
"""
import json
import warnings
from pathlib import Path

import pandas as pd

from value_models import PATTERN_CODE

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
DIAGNOSTIC_PATH = DATA_DIR / "processed" / "engine_v2" / "value_model_rows_diagnostic_v4.parquet"
OUT_PATH = DATA_DIR / "engine_v2_task23_d2.json"

BANDS = [(80, 100), (100, 120)]
DEAD_BALL_CODES = {PATTERN_CODE["From Corner"], PATTERN_CODE["From Free Kick"], PATTERN_CODE["From Throw In"]}


def band_of(x: float):
    for lo, hi in BANDS:
        if lo <= x < hi:
            return f"{lo}-{hi}"
    return None


def build_table(df: pd.DataFrame) -> list:
    rows = []
    for lo, hi in BANDS:
        band_label = f"{lo}-{hi}"
        band_df = df[(df["ball_x"] >= lo) & (df["ball_x"] < hi)]
        for channel, is_central in (("CENTRAL", True), ("WIDE", False)):
            central_mask = (band_df["ball_y"] - 40).abs() <= 10
            chan_df = band_df[central_mask] if is_central else band_df[~central_mask]
            for beyond in (False, True):
                sub = chan_df[chan_df["ball_beyond_defensive_line"] == beyond]
                n = len(sub)
                rows.append({
                    "band": band_label, "channel": channel, "beyond_line": beyond, "n": n,
                    "p_score_in_10": float(sub["label_for_new"].mean()) if n else None,
                    "p_concede_in_10": float(sub["label_against_new"].mean()) if n else None,
                })
    return rows


def check_r2_r3(rows: list, label: str) -> dict:
    def rate(band, channel, beyond):
        for r in rows:
            if r["band"] == band and r["channel"] == channel and r["beyond_line"] == beyond:
                return r["p_score_in_10"]
        return None

    verdicts = {}
    for lo, hi in BANDS:
        band_label = f"{lo}-{hi}"
        p_beyond = rate(band_label, "CENTRAL", True)
        p_not_beyond = rate(band_label, "CENTRAL", False)
        verdicts[band_label] = {
            "p_score_central_beyond": p_beyond, "p_score_central_not_beyond": p_not_beyond,
            "central_beyond_scores_higher": bool(p_beyond is not None and p_not_beyond is not None and p_beyond > p_not_beyond),
        }
    both_bands_higher = all(v["central_beyond_scores_higher"] for v in verdicts.values())
    neither_band_higher = not any(v["central_beyond_scores_higher"] for v in verdicts.values())
    print(f"  [{label}] central beyond-line vs not-beyond, both bands higher (R2 condition): {both_bands_higher}")
    print(f"  [{label}] central beyond-line NOT higher in either band (R3 condition): {neither_band_higher}")
    return {"band_verdicts": verdicts, "both_bands_central_beyond_higher_R2": both_bands_higher,
            "neither_band_central_beyond_higher_R3": neither_band_higher}


def main():
    print("Task 23 Step 2 (D2): band x channel x beyond-line, in-possession rows, new labels ...")
    diag = pd.read_parquet(DIAGNOSTIC_PATH)
    in_poss = diag[diag["in_possession"]].copy()
    print(f"  {len(in_poss)} in-possession rows (of {len(diag)} total diagnostic rows)")

    print("\n  main table (all in-possession rows) ...")
    main_table = build_table(in_poss)
    for r in main_table:
        print(f"    {r}")
    main_verdict = check_r2_r3(main_table, "main")

    no_dead_ball = in_poss[~in_poss["play_pattern_code"].isin(DEAD_BALL_CODES)]
    n_dropped = len(in_poss) - len(no_dead_ball)
    print(f"\n  sensitivity: dropping From Corner/Free Kick/Throw In rows ({n_dropped} rows dropped, "
          f"{n_dropped / len(in_poss):.4f} of in-possession rows) ...")
    sensitivity_table = build_table(no_dead_ball)
    for r in sensitivity_table:
        print(f"    {r}")
    sensitivity_verdict = check_r2_r3(sensitivity_table, "sensitivity, no dead balls")

    summary = {
        "n_in_possession_rows": len(in_poss), "n_diagnostic_rows_total": len(diag),
        "main_table": main_table, "main_verdict": main_verdict,
        "n_dead_ball_rows_dropped": n_dropped, "n_rows_sensitivity": len(no_dead_ball),
        "sensitivity_table": sensitivity_table, "sensitivity_verdict": sensitivity_verdict,
    }
    OUT_PATH.write_text(json.dumps(summary, indent=2, default=str))
    print(f"\nWrote {OUT_PATH}")
    return summary


if __name__ == "__main__":
    main()
