"""
Task 10 — PART C: Detectable-effect audit (Amendment v2-7.1). For all 107
analyzable pairs (Task 05's >=100-chosen discovery-half rule, not just the
10 candidates Task 06's own hard rule scoped it to -- this task explicitly
supersedes that scope for this one audit, per the brief), compute the
confirmation-half bootstrap SE of G and the minimum detectable effect at
80% power (2.802 x SE), in both G units and L units.

Run: python src/decision_engine/task10_partC_mde_audit.py
"""
import json
import warnings

import numpy as np
import pandas as pd

from task04_situation_context import DATA_DIR
from task05_study_a_discovery import (
    BOOTSTRAP_SEED, N_BOOTSTRAP, STANDARD_SEASON_MATCHES,
    analyzable_pairs, build_available_types_table, discovery_match_ids, load_discovery_data,
)
from task06_study_a_confirmation import confirmation_match_ids, load_and_prepare

warnings.filterwarnings("ignore")

SUMMARY_PATH = DATA_DIR / "task10_partC_mde_audit.json"
MDE_MULTIPLIER = 2.802  # z_{0.025} + z_{0.80}, two-sided alpha=0.05, 80% power


def bootstrap_g_stats_se(sub: pd.DataFrame, match_universe: list, seed: int = BOOTSTRAP_SEED,
                          n_boot: int = N_BOOTSTRAP) -> dict:
    """Same computation as task06_study_a_confirmation.bootstrap_g_stats,
    with one extra return value: the bootstrap draws' own standard
    deviation (SE of G), needed for Part C's MDE. Kept as a local variant
    (not a change to the shared function other tasks depend on)."""
    n = len(match_universe)
    match_pos = {m: i for i, m in enumerate(match_universe)}
    rng = np.random.default_rng(seed)
    idx_matrix = rng.integers(0, n, size=(n_boot, n))

    n_passes = len(sub)
    if n_passes == 0:
        return {"G": None, "se": None, "P": None, "L": None, "n_passes": 0, "n_matches": 0}
    G = float(sub["g"].mean())
    P = float((sub["g"] > 0).mean())
    n_team_matches = sub[["team", "match_id"]].drop_duplicates().shape[0]
    n_matches_contrib = sub["match_id"].nunique()
    L = G * (n_passes / n_team_matches) * STANDARD_SEASON_MATCHES if n_team_matches else None
    pass_rate = (n_passes / n_team_matches) if n_team_matches else None

    per_match = sub.groupby("match_id")["g"].agg(["sum", "count"])
    sums = np.zeros(n)
    counts = np.zeros(n)
    for mid, r in per_match.iterrows():
        if mid in match_pos:
            sums[match_pos[mid]] = r["sum"]
            counts[match_pos[mid]] = r["count"]
    boot_sums = sums[idx_matrix].sum(axis=1)
    boot_counts = counts[idx_matrix].sum(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        boot_G = np.where(boot_counts > 0, boot_sums / boot_counts, np.nan)
    se = float(np.nanstd(boot_G, ddof=1))
    return {"G": G, "se": se, "P": P, "L": L, "pass_rate_per_team_match": pass_rate,
            "n_passes": n_passes, "n_matches": int(n_matches_contrib)}


def main():
    print("Rebuilding discovery-half analyzable-pairs list (Task 05's own machinery) ...")
    discovery_ids = discovery_match_ids()
    typed_d, passes_d, ev_d = load_discovery_data(discovery_ids)
    from task05_study_a_discovery import join_ev, recover_raw_positions
    typed_d = recover_raw_positions(typed_d)
    opt_d, join_report_d = join_ev(typed_d, ev_d)
    if join_report_d["match_rate"] != 1.0 or join_report_d["n_group_size_mismatches"]:
        raise RuntimeError(f"Discovery-half options_ev join failed: {join_report_d}")
    cell_info_d = passes_d[["match_id", "event_id", "zone", "under_pressure", "game_state"]]
    avail_d = build_available_types_table(opt_d, cell_info_d)
    pairs_table = analyzable_pairs(avail_d)
    analyzable = pairs_table[pairs_table["analyzable"]].copy()
    n_analyzable = len(analyzable)
    print(f"Analyzable pairs (independently rebuilt): {n_analyzable} (expected 107)")

    print("Loading confirmation half and building g_table for all analyzable pairs ...")
    confirmation_ids = confirmation_match_ids()
    opt_c, passes_c, join_report_c = load_and_prepare(confirmation_ids)
    if join_report_c["match_rate"] != 1.0 or join_report_c["n_group_size_mismatches"]:
        raise RuntimeError(f"Confirmation-half options_ev join failed: {join_report_c}")
    cell_info_c = passes_c[["match_id", "event_id", "zone", "under_pressure", "game_state", "team"]]
    avail_c = build_available_types_table(opt_c, cell_info_c)
    g_table = avail_c[avail_c["option_type"] != avail_c["j"]].copy()
    g_table["g"] = g_table["ev_star"] - g_table["ev_star_j"]

    rows = []
    for _, pair in analyzable.sort_values(["zone", "under_pressure", "game_state", "option_type"]).iterrows():
        z, p, gs, k = pair["zone"], pair["under_pressure"], pair["game_state"], pair["option_type"]
        sub = g_table[(g_table["zone"] == z) & (g_table["under_pressure"] == p)
                      & (g_table["game_state"] == gs) & (g_table["option_type"] == k)]
        stats = bootstrap_g_stats_se(sub, confirmation_ids)
        mde_g = MDE_MULTIPLIER * stats["se"] if stats["se"] is not None else None
        mde_l = (mde_g * stats["pass_rate_per_team_match"] * STANDARD_SEASON_MATCHES
                 if mde_g is not None and stats["pass_rate_per_team_match"] is not None else None)
        rows.append({
            "zone": z, "under_pressure": bool(p), "game_state": gs, "option_type": k,
            "G": stats["G"], "se_G": stats["se"], "mde_G": mde_g, "L": stats["L"], "mde_L": mde_l,
            "n_passes": stats["n_passes"], "n_matches": stats["n_matches"],
        })
    table = pd.DataFrame(rows)

    n_zero_confirmation_passes = int((table["n_passes"] == 0).sum())
    valid = table.dropna(subset=["mde_L"])
    median_mde_l = float(valid["mde_L"].median()) if len(valid) else None
    share_detect_1_0 = float((valid["mde_L"] <= 1.0).mean()) if len(valid) else None
    share_detect_0_5 = float((valid["mde_L"] <= 0.5).mean()) if len(valid) else None

    print(f"\n107-row table built. Pairs with zero confirmation-half passes: {n_zero_confirmation_passes}")
    print(f"Median MDE in L units: {median_mde_l}")
    print(f"Share with MDE <= 1.0 L: {share_detect_1_0}")
    print(f"Share with MDE <= 0.5 L: {share_detect_0_5}")

    table_out_path = DATA_DIR / "processed" / "task10_partC_mde_table.csv"
    table.to_csv(table_out_path, index=False)

    summary = {
        "status": "COMPLETE", "n_analyzable_pairs": n_analyzable,
        "discovery_join_report": join_report_d, "confirmation_join_report": join_report_c,
        "n_zero_confirmation_passes": n_zero_confirmation_passes,
        "median_mde_L": median_mde_l, "share_mde_le_1_0_L": share_detect_1_0,
        "share_mde_le_0_5_L": share_detect_0_5,
        "table_path": str(table_out_path),
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
    print(f"\nWrote summary to {SUMMARY_PATH}, full table to {table_out_path}")


if __name__ == "__main__":
    main()
