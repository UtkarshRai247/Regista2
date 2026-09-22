"""
Task 08 — PART 1: Study B corrections (Amendment v2-5).

1. bootstrap_by_player's fresh-id bug fix lives in reml_crossed.py now
   (reused here), not edited into Task 07's historical script -- v2-5.1
   says the Task 07 intervals are SUPERSEDED, not deleted.
2. Corrected 95% CIs for B4 (primary) and B5a (position-matched refit),
   reported next to Task 07's (superseded) intervals.
3. PH-B1 (position-group fixed effects), PH-B2 (disattenuated mover
   correlation), PH-B3 (2+-unit players only).
4. v2-5.4 claim-rule verdicts (fixed; not adjusted here).
5. v2-5.5 design calculation, only if Tier 2 is NOT ALLOWED.

Run: python src/decision_engine/task08_studyb_corrections.py
"""
import json
import warnings

import numpy as np
import pandas as pd
from scipy.stats import norm

from decompose import match_competition_lookup
from reml_crossed import bootstrap_by_player, fit_reml
from task04_situation_context import CLUB_COMPETITIONS, DATA_DIR, INTL_COMPETITIONS
from task07_study_b import POLICY_PATH, X_COLS, compute_decision_per_pass

warnings.filterwarnings("ignore")

UNITS_PATH = DATA_DIR / "processed" / "study_b_units.parquet"
SUMMARY_PATH = DATA_DIR / "task08_studyb_corrections.json"

SEED = 20260920
N_BOOTSTRAP = 1000
N_SPLITS_PH_B2 = 100
N_SPLITS_PH_B2_BOOT = 20
POSITION_DUMMY_GROUPS = ["GK", "Defender", "Forward"]  # Midfielder is the reference

# Task 07's (superseded) intervals, from docs/results/07-study-b.md (2026-09-21).
TASK07_B4_CI = (0.6263058878913235, 0.7846293331242485)
TASK07_B5A_CI = (0.6304623522612661, 0.7854298095266051)


def ci_of(s_boot: np.ndarray) -> tuple:
    return float(np.percentile(s_boot, 2.5)), float(np.percentile(s_boot, 97.5))


def build_movers(units: pd.DataFrame):
    movers, mover_position_match = {}, {}
    for pid, g in units.groupby("player_id"):
        is_club = g.apply(lambda r: (r["competition_id"], r["season_id"]) in CLUB_COMPETITIONS, axis=1)
        is_intl = g.apply(lambda r: (r["competition_id"], r["season_id"]) in INTL_COMPETITIONS, axis=1)
        club, intl = g[is_club], g[is_intl]
        if len(club) and len(intl):
            movers[pid] = {"club": club, "intl": intl}
            club_groups = set(club["position_group"].dropna())
            intl_groups = set(intl["position_group"].dropna())
            mover_position_match[pid] = bool(club_groups & intl_groups)
    return movers, mover_position_match


def part1_2(units: pd.DataFrame, movers: dict, mover_position_match: dict) -> dict:
    print("Part 1.2: corrected B4/B5a intervals ...")
    fit_b4 = fit_reml(units, x_cols=X_COLS)
    s_boot_b4 = bootstrap_by_player(units, X_COLS, N_BOOTSTRAP, SEED)
    ci_b4 = ci_of(s_boot_b4)

    mismatched = {pid for pid, ok in mover_position_match.items() if not ok}
    restricted = units[~units["player_id"].isin(mismatched)].copy()
    fit_b5a = fit_reml(restricted, x_cols=X_COLS)
    s_boot_b5a = bootstrap_by_player(restricted, X_COLS, N_BOOTSTRAP, SEED)
    ci_b5a = ci_of(s_boot_b5a)

    result = {
        "b4": {"fit": fit_b4, "corrected_ci": ci_b4, "task07_superseded_ci": list(TASK07_B4_CI)},
        "b5a": {"fit": fit_b5a, "corrected_ci": ci_b5a, "task07_superseded_ci": list(TASK07_B5A_CI),
                "n_units_excluded": len(units) - len(restricted)},
    }
    print(json.dumps(result, indent=2, default=str))
    return result


def ph_b1(units: pd.DataFrame) -> dict:
    print("PH-B1: position-group fixed effects ...")
    u = units.copy()
    group_counts = units["position_group"].value_counts()
    dropped_zero_count = [g for g in POSITION_DUMMY_GROUPS if group_counts.get(g, 0) == 0]
    dummy_groups = [g for g in POSITION_DUMMY_GROUPS if group_counts.get(g, 0) > 0]
    if dropped_zero_count:
        print(f"  NOTE: {dropped_zero_count} has zero units in this data (goalkeepers are excluded "
              "from eligible passes since Task 01's options.py eligibility filter) -- a fixed effect "
              "for an all-zero dummy is unidentifiable, so it is dropped rather than causing a singular "
              "design matrix. See Section 5 of the results page.")
    for g in dummy_groups:
        u[f"is_{g}"] = (u["position_group"] == g).astype(float)
    x_cols = X_COLS + [f"is_{g}" for g in dummy_groups]
    fit = fit_reml(u, x_cols=x_cols)
    s_boot = bootstrap_by_player(u, x_cols, N_BOOTSTRAP, SEED)
    result = {"fit": fit, "ci": ci_of(s_boot), "x_cols": x_cols,
              "position_group_counts": group_counts.to_dict(), "dropped_zero_count_groups": dropped_zero_count}
    print(json.dumps(result, indent=2, default=str))
    return result


def ph_b3(units: pd.DataFrame) -> dict:
    print("PH-B3: players with 2+ units only ...")
    counts = units.groupby("player_id").size()
    multi_players = counts[counts >= 2].index
    subset = units[units["player_id"].isin(multi_players)].copy()
    fit = fit_reml(subset, x_cols=X_COLS)
    s_boot = bootstrap_by_player(subset, X_COLS, N_BOOTSTRAP, SEED)
    result = {"fit": fit, "ci": ci_of(s_boot), "n_units": len(subset), "n_players": int(len(multi_players))}
    print(json.dumps(result, indent=2, default=str))
    return result


def build_pass_level_decision() -> pd.DataFrame:
    policy = pd.read_parquet(POLICY_PATH)
    per_pass = compute_decision_per_pass(policy)
    comp_lookup = match_competition_lookup()
    per_pass["competition_id"] = per_pass["match_id"].map(lambda m: comp_lookup.get(m, (None, None))[0])
    per_pass["season_id"] = per_pass["match_id"].map(lambda m: comp_lookup.get(m, (None, None))[1])
    per_pass["ctx_key"] = (per_pass["team"].astype(str) + "|" + per_pass["competition_id"].astype(str)
                            + "|" + per_pass["season_id"].astype(str))
    return per_pass[["match_id", "event_id", "player_id", "ctx_key", "decision"]]


def build_side_pass_arrays(per_pass: pd.DataFrame, movers: dict):
    mover_pids = set(movers.keys())
    per_pass_mv = per_pass[per_pass["player_id"].isin(mover_pids)]
    club_passes, intl_passes = {}, {}
    for pid, v in movers.items():
        club_keys = set(v["club"]["team"].astype(str) + "|" + v["club"]["competition_id"].astype(str)
                         + "|" + v["club"]["season_id"].astype(str))
        intl_keys = set(v["intl"]["team"].astype(str) + "|" + v["intl"]["competition_id"].astype(str)
                         + "|" + v["intl"]["season_id"].astype(str))
        sub = per_pass_mv[per_pass_mv["player_id"] == pid]
        club_passes[pid] = sub[sub["ctx_key"].isin(club_keys)]["decision"].values
        intl_passes[pid] = sub[sub["ctx_key"].isin(intl_keys)]["decision"].values
    return club_passes, intl_passes


def split_half_reliability(arrays: list, n_splits: int, seed: int) -> float:
    """Spearman-Brown-corrected split-half reliability, median over
    n_splits random halvings. `arrays` is a list of per-mover pass-value
    arrays (duplicates allowed and preserved, as needed inside a
    bootstrap draw where the same mover can be resampled more than once)."""
    rng = np.random.default_rng(seed)
    r_sb_list = []
    for _ in range(n_splits):
        h1_means, h2_means = [], []
        for arr in arrays:
            n = len(arr)
            perm = rng.permutation(n)
            half = n // 2
            h1_means.append(arr[perm[:half]].mean())
            h2_means.append(arr[perm[half:]].mean())
        r = np.corrcoef(h1_means, h2_means)[0, 1]
        r_sb_list.append(2 * r / (1 + r) if not np.isnan(r) else np.nan)
    return float(np.nanmedian(r_sb_list))


def weighted_side_means(units: pd.DataFrame, movers: dict) -> pd.DataFrame:
    rows = []
    for pid, v in movers.items():
        club_mean = float(np.average(v["club"]["mean_decision"], weights=v["club"]["n_passes"]))
        intl_mean = float(np.average(v["intl"]["mean_decision"], weights=v["intl"]["n_passes"]))
        rows.append({"player_id": pid, "club_mean": club_mean, "intl_mean": intl_mean})
    return pd.DataFrame(rows)


def ph_b2(units: pd.DataFrame, movers: dict) -> dict:
    print("PH-B2: disattenuated mover correlation ...")
    per_pass = build_pass_level_decision()
    club_passes, intl_passes = build_side_pass_arrays(per_pass, movers)
    mean_intl_passes_per_mover = float(np.mean([len(a) for a in intl_passes.values()]))

    pids_sorted = sorted(movers.keys())
    rel_club = split_half_reliability([club_passes[p] for p in pids_sorted], N_SPLITS_PH_B2, SEED)
    rel_intl = split_half_reliability([intl_passes[p] for p in pids_sorted], N_SPLITS_PH_B2, SEED + 1)

    mover_df = weighted_side_means(units, movers).set_index("player_id")
    r_obs = float(mover_df.loc[pids_sorted, "club_mean"].corr(mover_df.loc[pids_sorted, "intl_mean"]))

    result = {"rel_club": rel_club, "rel_intl": rel_intl, "r_obs": r_obs, "n_movers": len(movers),
              "mean_intl_passes_per_mover": mean_intl_passes_per_mover}

    if rel_club < 0.10 or rel_intl < 0.10:
        result["unmeasurable"] = True
        result["r_true"] = None
        result["r_true_ci"] = None
        result["share_capped"] = None
        print(json.dumps(result, indent=2, default=str))
        return result

    result["unmeasurable"] = False
    r_true_raw = r_obs / np.sqrt(rel_club * rel_intl)
    r_true = float(np.clip(r_true_raw, -1.0, 1.0))
    result["r_true_uncapped"] = float(r_true_raw)
    result["r_true"] = r_true

    print("  bootstrapping PH-B2 (1,000 draws, 20 splits/draw, resampling movers) ...")
    rng = np.random.default_rng(SEED)
    pids_arr = np.array(pids_sorted)
    n_movers = len(pids_arr)
    r_true_boot = np.empty(N_BOOTSTRAP)
    n_capped = 0
    for b in range(N_BOOTSTRAP):
        drawn = rng.choice(pids_arr, size=n_movers, replace=True)
        club_means_b = mover_df.loc[drawn, "club_mean"].values
        intl_means_b = mover_df.loc[drawn, "intl_mean"].values
        r_obs_b = np.corrcoef(club_means_b, intl_means_b)[0, 1]
        rel_club_b = split_half_reliability([club_passes[p] for p in drawn], N_SPLITS_PH_B2_BOOT, SEED + 1000 + b)
        rel_intl_b = split_half_reliability([intl_passes[p] for p in drawn], N_SPLITS_PH_B2_BOOT, SEED + 2000 + b)
        denom = np.sqrt(max(rel_club_b, 1e-8) * max(rel_intl_b, 1e-8))
        r_true_b = r_obs_b / denom
        if abs(r_true_b) > 1:
            n_capped += 1
        r_true_boot[b] = np.clip(r_true_b, -1.0, 1.0)

    result["r_true_ci"] = ci_of(r_true_boot)
    result["share_capped"] = n_capped / N_BOOTSTRAP
    print(json.dumps(result, indent=2, default=str))
    return result


def design_calculation(rel_club: float, rel_intl: float, mean_intl_passes: float) -> dict:
    print("v2-5.5: design calculation (Tier 2 NOT ALLOWED) ...")
    z_a2 = norm.ppf(1 - 0.05 / 2)
    z_b = norm.ppf(0.80)
    power = {}
    for true_r in (0.3, 0.5):
        r_eff = true_r * np.sqrt(rel_club * rel_intl)
        n_req = ((z_a2 + z_b) / np.arctanh(r_eff)) ** 2 + 3
        power[str(true_r)] = {"r_effective": float(r_eff), "n_movers_required": float(np.ceil(n_req))}
    sb = {}
    for target in (0.5, 0.7):
        k = target * (1 - rel_intl) / (rel_intl * (1 - target))
        n_new = k * mean_intl_passes
        sb[str(target)] = {"k": float(k), "intl_passes_per_mover_required": float(np.ceil(n_new))}
    result = {"power_for_true_r": power, "spearman_brown_projection": sb,
              "rel_club_used": rel_club, "rel_intl_used": rel_intl,
              "mean_intl_passes_per_mover_used": mean_intl_passes}
    print(json.dumps(result, indent=2, default=str))
    return result


def apply_claim_rules(corrected: dict, phb1: dict, phb2: dict, phb3: dict) -> dict:
    tier1 = (corrected["b4"]["corrected_ci"][0] > 0.5) and (phb1["ci"][0] > 0.5)
    if phb2.get("unmeasurable") or phb2.get("r_true_ci") is None:
        phb2_ok = False
    else:
        phb2_ok = (phb2["r_true"] > 0) and (phb2["r_true_ci"][0] > 0)
    tier2 = tier1 and phb2_ok and (phb3["ci"][0] > 0.5)
    return {
        "tier1_allowed": bool(tier1), "tier2_allowed": bool(tier2),
        "tier1_conditions": {"b4_ci_low_gt_0.5": corrected["b4"]["corrected_ci"][0] > 0.5,
                              "phb1_ci_low_gt_0.5": phb1["ci"][0] > 0.5},
        "tier2_conditions": {"tier1": bool(tier1), "phb2_positive_excl_zero": bool(phb2_ok),
                              "phb3_ci_low_gt_0.5": phb3["ci"][0] > 0.5},
    }


def main():
    units = pd.read_parquet(UNITS_PATH)
    print(f"Loaded {len(units)} stage-1 units from Task 07.")
    movers, mover_position_match = build_movers(units)
    print(f"Movers: {len(movers)}; position-matched: {sum(mover_position_match.values())}")

    corrected = part1_2(units, movers, mover_position_match)
    phb1 = ph_b1(units)
    phb2 = ph_b2(units, movers)
    phb3 = ph_b3(units)

    tiers = apply_claim_rules(corrected, phb1, phb2, phb3)
    print(json.dumps(tiers, indent=2, default=str))

    design_calc = None
    if not tiers["tier2_allowed"]:
        if phb2.get("unmeasurable"):
            print("PH-B2 unmeasurable (a reliability < 0.10) -- design calculation cannot use its estimates "
                  "meaningfully, but computing it anyway from whatever rel_club/rel_intl were estimated, "
                  "flagged as such.")
        design_calc = design_calculation(phb2["rel_club"], phb2["rel_intl"], phb2["mean_intl_passes_per_mover"])
    else:
        print("Tier 2 ALLOWED -- v2-5.5 design calculation skipped, per the brief.")

    summary = {
        "status": "COMPLETE", "n_units": len(units), "n_movers": len(movers),
        "n_movers_position_matched": sum(mover_position_match.values()),
        "part1_2": corrected, "ph_b1": phb1, "ph_b2": phb2, "ph_b3": phb3,
        "claim_rules": tiers, "design_calculation": design_calc,
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
    print(f"\nWrote summary to {SUMMARY_PATH}")


if __name__ == "__main__":
    main()
