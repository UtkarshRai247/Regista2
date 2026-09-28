"""
Task 32, Step 2 (A3): how much of Decision is execution? Full-corpus
(pass_der_v8.parquet, 292 matches -- same population as everywhere else
in engine v5; see the results page).

(a) Share of eligible passes incomplete; mean Decision complete vs
    incomplete; share of between-player variance in mean Decision
    contributed by incomplete passes (disclosed operationalization: on
    the 537 qualifying players, 1 - Var(complete-only player means) /
    Var(all-passes player means) -- how much removing incomplete-pass
    information shrinks the between-player spread).
(b) Player Decision recomputed on COMPLETED passes only, same
    shrinkage as Task 28 (overall, design-effect v_i + method-of-
    moments tau^2) and Task 29 (deep midfield, within-group v_i +
    DerSimonian-Laird tau^2), reusing both tasks' own functions
    unchanged. Spearman vs the all-passes version, both groups.
(c) For incomplete passes: distance from the pass's own end location to
    the nearest visible teammate in that event's own frame, and to the
    nearest visible teammate within 15 degrees of the pass line
    (passer -> end location). Distributions (median, quartiles). No fix
    here.

Run: python src/engine_v2/task32_step2.py
"""
import json
import math
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

from task28_step1_2 import estimate_sigma2w_rho, empirical_bayes_shrink
from task29_step1_2 import dersimonian_laird, shrink as dl_shrink

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
EVENTS_DIR = DATA_DIR / "raw" / "events"
FRAMES_DIR = DATA_DIR / "raw" / "frames"
EV_DIR = DATA_DIR / "processed" / "engine_v2" / "options_ev_v4"
PASS_DER_V8_PATH = DATA_DIR / "processed" / "engine_v2" / "pass_der_v8.parquet"
LEADERBOARD_V5C_PATH = DATA_DIR / "processed" / "leaderboard_v5c.parquet"
TASK29_SUMMARY_PATH = DATA_DIR / "engine_v2_task29_step1_2.json"
SUMMARY_PATH = DATA_DIR / "engine_v2_task32_step2.json"


def build_per_pass_with_outcome() -> pd.DataFrame:
    per_pass = pd.read_parquet(PASS_DER_V8_PATH, columns=["match_id", "event_id", "player_id", "decision_new"])
    match_ids = sorted(per_pass["match_id"].unique())
    frames = []
    for mid in match_ids:
        df = pd.read_parquet(EV_DIR / f"{mid}.parquet", columns=["match_id", "event_id", "chosen", "pass_complete"])
        frames.append(df[df["chosen"]][["match_id", "event_id", "pass_complete"]])
    outcome = pd.concat(frames, ignore_index=True)
    return per_pass.merge(outcome, on=["match_id", "event_id"], how="inner")


def build_group_stats(per_pass: pd.DataFrame, decision_col: str) -> pd.DataFrame:
    m_i = per_pass.groupby("player_id")[decision_col].mean().rename("m_i")
    n_i = per_pass.groupby("player_id").size().rename("n_i")
    g_i = per_pass.groupby("player_id")["match_id"].nunique().rename("G_i")
    stats = pd.concat([m_i, n_i, g_i], axis=1).reset_index()
    stats["mean_passes_per_match"] = stats["n_i"] / stats["G_i"]
    return stats


def nearest_teammate_distance(end_loc, teammates_raw):
    if len(teammates_raw) == 0:
        return None
    d = np.hypot(teammates_raw[:, 0] - end_loc[0], teammates_raw[:, 1] - end_loc[1])
    return float(d.min())


def nearest_teammate_within_angle(passer_raw, end_loc, teammates_raw, max_angle_deg=15.0):
    if len(teammates_raw) == 0:
        return None
    line_vec = np.array(end_loc) - np.array(passer_raw)
    line_len = np.hypot(*line_vec)
    if line_len < 1e-6:
        return None
    line_angle = math.degrees(math.atan2(line_vec[1], line_vec[0]))
    to_team = teammates_raw - np.array(passer_raw)
    team_angle = np.degrees(np.arctan2(to_team[:, 1], to_team[:, 0]))
    diff = np.abs((team_angle - line_angle + 180) % 360 - 180)
    within = diff <= max_angle_deg
    if not within.any():
        return None
    d = np.hypot(teammates_raw[within, 0] - end_loc[0], teammates_raw[within, 1] - end_loc[1])
    return float(d.min())


def main():
    print("Task 32 Step 2 (A3): how much of Decision is execution? ...")
    per_pass = build_per_pass_with_outcome()
    print(f"  {len(per_pass)} eligible passes (full corpus, 292 matches)")

    n_incomplete = int((~per_pass["pass_complete"]).sum())
    share_incomplete = n_incomplete / len(per_pass)
    mean_complete = float(per_pass.loc[per_pass["pass_complete"], "decision_new"].mean())
    mean_incomplete = float(per_pass.loc[~per_pass["pass_complete"], "decision_new"].mean())
    print(f"\n  (a) share incomplete: {share_incomplete:.4f} ({n_incomplete}/{len(per_pass)})")
    print(f"  (a) mean Decision complete={mean_complete:.6f}, incomplete={mean_incomplete:.6f}")

    leaderboard = pd.read_parquet(LEADERBOARD_V5C_PATH, columns=["player_id"])
    qualifying_ids = set(leaderboard["player_id"])
    pp_qual = per_pass[per_pass["player_id"].isin(qualifying_ids)]
    m_all = pp_qual.groupby("player_id")["decision_new"].mean()
    complete_only = pp_qual[pp_qual["pass_complete"]]
    m_complete_only = complete_only.groupby("player_id")["decision_new"].mean()
    common = m_all.index.intersection(m_complete_only.index)
    var_all = float(m_all.loc[common].var(ddof=1))
    var_complete_only = float(m_complete_only.loc[common].var(ddof=1))
    variance_share_incomplete = 1 - var_complete_only / var_all
    print(f"  (a) Var(all-passes player means)={var_all:.6e}, Var(complete-only player means)={var_complete_only:.6e}")
    print(f"  (a) share of between-player variance contributed by incomplete passes: {variance_share_incomplete:.4f}")

    a = {
        "n_eligible_passes": len(per_pass), "n_incomplete": n_incomplete, "share_incomplete": share_incomplete,
        "mean_decision_complete": mean_complete, "mean_decision_incomplete": mean_incomplete,
        "n_players_common": len(common), "var_all_passes_player_means": var_all,
        "var_complete_only_player_means": var_complete_only,
        "share_between_player_variance_from_incomplete": variance_share_incomplete,
    }

    print("\n  (b) recomputing shrinkage on COMPLETED passes only ...")
    complete_pp = per_pass[per_pass["pass_complete"]]

    print("    overall group (537), Task 28's design-effect + method-of-moments ...")
    complete_pp_overall = complete_pp[complete_pp["player_id"].isin(qualifying_ids)]
    sigma2_w_o, rho_o, _ = estimate_sigma2w_rho(complete_pp_overall.rename(columns={"decision_new": "decision_new"}))
    stats_o = build_group_stats(complete_pp_overall, "decision_new")
    stats_o["v_i"] = sigma2_w_o * (1 + (stats_o["mean_passes_per_match"] - 1) * rho_o) / stats_o["n_i"]
    shrunk_o, mu_o, tau2_o = empirical_bayes_shrink(stats_o)
    print(f"    overall (complete-only): sigma2_w={sigma2_w_o:.4e}, rho={rho_o:.6f}, mu={mu_o:.6f}, tau2={tau2_o:.4e}")

    old_overall_full = pd.read_parquet(LEADERBOARD_V5C_PATH, columns=["player_id", "shrunken_i_per100"])
    cmp_overall = shrunk_o.merge(old_overall_full, on="player_id", how="inner")
    from scipy.stats import spearmanr
    rho_overall_spear, p_overall_spear = spearmanr(cmp_overall["shrunken_i"] * 100, cmp_overall["shrunken_i_per100"])
    print(f"    Spearman (complete-only vs all-passes), overall: rho={rho_overall_spear:.4f}, p={p_overall_spear:.4g}, n={len(cmp_overall)}")

    print("\n    deep-midfield group (111), Task 29's within-group + DerSimonian-Laird ...")
    dm_ids = set(pd.read_parquet(LEADERBOARD_V5C_PATH, columns=["player_id", "is_deep_midfield"])
                 .loc[lambda d: d["is_deep_midfield"], "player_id"])
    complete_pp_dm = complete_pp[complete_pp["player_id"].isin(dm_ids)]
    sigma2_w_dm, rho_dm, _ = estimate_sigma2w_rho(complete_pp_dm)
    stats_dm = build_group_stats(complete_pp_dm, "decision_new")
    stats_dm["v_i_within_group"] = sigma2_w_dm * (1 + (stats_dm["mean_passes_per_match"] - 1) * rho_dm) / stats_dm["n_i"]
    dl = dersimonian_laird(stats_dm["m_i"].values, stats_dm["v_i_within_group"].values)
    shrunk_dm = dl_shrink(stats_dm, dl["mu_w"], dl["tau2"], "m_i", "v_i_within_group")
    print(f"    DM (complete-only): sigma2_w={sigma2_w_dm:.4e}, rho={rho_dm:.6f}, DL mu_w={dl['mu_w']:.6f}, "
          f"Q={dl['Q']:.2f}, p={dl['p_value']:.4f}, tau2={dl['tau2']:.4e}")

    task29 = json.loads(TASK29_SUMMARY_PATH.read_text())
    old_dm = pd.DataFrame(task29["table_primary"])[["player_id", "shrunken_i_per100"]]
    cmp_dm = shrunk_dm.merge(old_dm, on="player_id", how="inner")
    rho_dm_spear, p_dm_spear = spearmanr(cmp_dm["shrunken_i"] * 100, cmp_dm["shrunken_i_per100"])
    print(f"    Spearman (complete-only vs all-passes), deep midfield: rho={rho_dm_spear:.4f}, p={p_dm_spear:.4g}, n={len(cmp_dm)}")

    b = {
        "overall": {"sigma2_w": sigma2_w_o, "rho": rho_o, "mu": mu_o, "tau2": tau2_o,
                     "spearman_vs_all_passes": {"rho": float(rho_overall_spear), "p": float(p_overall_spear), "n": len(cmp_overall)}},
        "deep_midfield": {"sigma2_w": sigma2_w_dm, "rho": rho_dm, "dl": dl,
                           "spearman_vs_all_passes": {"rho": float(rho_dm_spear), "p": float(p_dm_spear), "n": len(cmp_dm)}},
    }

    print("\n  (c) incomplete-pass end-location vs. teammate distances ...")
    incomplete_ids = per_pass.loc[~per_pass["pass_complete"], ["match_id", "event_id"]]
    match_ids_inc = sorted(incomplete_ids["match_id"].unique())
    dists_any, dists_angle = [], []
    n_no_end_loc, n_no_frame = 0, 0
    for i, mid in enumerate(match_ids_inc):
        wanted = set(incomplete_ids.loc[incomplete_ids["match_id"] == mid, "event_id"])
        events = pd.read_parquet(EVENTS_DIR / f"{mid}.parquet",
                                  columns=["id", "location", "pass_end_location"])
        events = events[events["id"].isin(wanted)]
        frames = pd.read_parquet(FRAMES_DIR / f"{mid}.parquet")
        frames_by_event = {eid: g for eid, g in frames.groupby("id")}
        for _, row in events.iterrows():
            end_loc = row["pass_end_location"]
            passer_loc = row["location"]
            if end_loc is None or (isinstance(end_loc, float) and pd.isna(end_loc)) or passer_loc is None:
                n_no_end_loc += 1
                continue
            frame = frames_by_event.get(row["id"])
            if frame is None or len(frame) == 0:
                n_no_frame += 1
                continue
            teammates = frame[(frame["teammate"] == True) & (frame["actor"] == False)]
            if len(teammates) == 0:
                continue
            teammates_raw = np.array([list(l) for l in teammates["location"]], dtype=float)
            d_any = nearest_teammate_distance(end_loc, teammates_raw)
            d_angle = nearest_teammate_within_angle(passer_loc, end_loc, teammates_raw)
            if d_any is not None:
                dists_any.append(d_any)
            if d_angle is not None:
                dists_angle.append(d_angle)
        if (i + 1) % 50 == 0:
            print(f"    {i + 1}/{len(match_ids_inc)} matches with incomplete passes")

    def describe(arr):
        arr = np.array(arr)
        if len(arr) == 0:
            return None
        return {"n": len(arr), "median": float(np.median(arr)), "q25": float(np.percentile(arr, 25)),
                "q75": float(np.percentile(arr, 75))}

    c = {
        "n_incomplete_total": len(incomplete_ids), "n_no_end_loc_or_passer_loc": n_no_end_loc, "n_no_frame": n_no_frame,
        "distance_to_nearest_teammate_any_angle": describe(dists_any),
        "distance_to_nearest_teammate_within_15deg": describe(dists_angle),
    }
    print(f"  (c) {c}")

    summary = {"a": a, "b": b, "c": c}
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
    print(f"\nWrote {SUMMARY_PATH}")
    return summary


if __name__ == "__main__":
    main()
