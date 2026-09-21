"""
Task 07 — PART 1: Study A post-hoc robustness checks (Amendment v2-3.1),
confirmation half, for the 7 CONFIRMED candidates from Task 06.

PH-1: mean-EV G (guards against max-over-more-candidates inflation).
PH-2: count-matched max-vs-max G (restricted to passes where the number
of type-k options equals the number of chosen-type-j options).

Interpretation rule (fixed, not adjusted here): a candidate is ROBUST
only if it passed confirmation (given -- all 7 here did) AND Gate D AND
both PH-1 and PH-2 are positive with 95% CIs excluding zero.

Run: python src/decision_engine/task07_posthoc.py
"""
import json
import warnings

import pandas as pd

from task04_situation_context import DATA_DIR
from task06_study_a_confirmation import (
    bootstrap_g_stats, build_available_types_table_with_mean, cand_mask,
    confirmation_match_ids, load_and_prepare, parse_candidates,
)

warnings.filterwarnings("ignore")

STEP1_PATH = DATA_DIR / "processed" / "study_a_confirmation_step1.parquet"
GATE_D_PATH = DATA_DIR / "processed" / "study_a_gate_d.parquet"
OUT_PATH = DATA_DIR / "processed" / "study_a_posthoc.parquet"
SUMMARY_PATH = DATA_DIR / "task07_posthoc.json"


def main():
    confirmation_ids = confirmation_match_ids()
    print(f"Confirmation matches: {len(confirmation_ids)}")

    print("Loading confirmation-only data and joining EV (same pipeline as Task 06) ...")
    opt, passes, join_report = load_and_prepare(confirmation_ids)
    print(json.dumps(join_report, indent=2))
    if join_report["match_rate"] != 1.0 or join_report["n_group_size_mismatches"]:
        raise RuntimeError(f"options_ev join failed on confirmation half: {join_report}")

    cell_info = passes[["match_id", "event_id", "zone", "under_pressure", "game_state",
                         "team", "competition_id", "season_id", "n_visible_players"]]
    avail = build_available_types_table_with_mean(opt, cell_info)
    g_table = avail[avail["option_type"] != avail["j"]].copy()
    g_table["g"] = g_table["ev_star"] - g_table["ev_star_j"]
    g_table["g_mean"] = g_table["ev_mean"] - g_table["ev_mean_j"]

    step1 = pd.read_parquet(STEP1_PATH)
    gate_d = pd.read_parquet(GATE_D_PATH)
    confirmed = step1[step1["confirmed"]]
    print(f"CONFIRMED candidates from Task 06: {len(confirmed)}")
    assert len(confirmed) == 7, f"expected 7 confirmed candidates (Task 06), found {len(confirmed)}"

    rows = []
    for _, cand_row in confirmed.iterrows():
        cand = {"zone": cand_row["zone"], "under_pressure": bool(cand_row["under_pressure"]),
                "game_state": cand_row["game_state"], "option_type": cand_row["option_type"]}
        sub = g_table[cand_mask(g_table, cand)]
        n_total = len(sub)

        ph1_input = sub.rename(columns={"g": "g_max_tmp", "g_mean": "g"})
        ph1 = bootstrap_g_stats(ph1_input, confirmation_ids)

        matched = sub[sub["n_options"] == sub["n_options_j"]]
        n_matched = len(matched)
        ph2 = bootstrap_g_stats(matched, confirmation_ids)
        ph2_share = n_matched / n_total if n_total else None

        gd_row = gate_d[cand_mask(gate_d, cand)].iloc[0]
        gate_d_pass = bool(gd_row["gate_d_pass"])

        ph1_ok = (ph1["G"] is not None) and (ph1["G"] > 0) and (ph1["ci_low"] is not None) and (ph1["ci_low"] > 0)
        ph2_ok = (ph2["G"] is not None) and (ph2["G"] > 0) and (ph2["ci_low"] is not None) and (ph2["ci_low"] > 0)
        robust = bool(gate_d_pass and ph1_ok and ph2_ok)

        rows.append({
            "zone": cand["zone"], "under_pressure": cand["under_pressure"],
            "game_state": cand["game_state"], "option_type": cand["option_type"],
            "gate_d_pass": gate_d_pass,
            "ph1_G": ph1["G"], "ph1_ci_low": ph1["ci_low"], "ph1_ci_high": ph1["ci_high"],
            "ph1_P": ph1["P"], "ph1_n_passes": ph1["n_passes"], "ph1_positive_excl_zero": ph1_ok,
            "ph2_G": ph2["G"], "ph2_ci_low": ph2["ci_low"], "ph2_ci_high": ph2["ci_high"],
            "ph2_P": ph2["P"], "ph2_n_passes": n_matched, "ph2_share_retained": ph2_share,
            "ph2_positive_excl_zero": ph2_ok,
            "robust": robust,
        })

    result = pd.DataFrame(rows)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    result.to_parquet(OUT_PATH)
    print(result.to_string())
    SUMMARY_PATH.write_text(json.dumps(result.to_dict("records"), indent=2, default=str))
    print(f"\nROBUST: {int(result['robust'].sum())} / {len(result)}")
    print(f"Wrote {OUT_PATH} and {SUMMARY_PATH}")


if __name__ == "__main__":
    main()
