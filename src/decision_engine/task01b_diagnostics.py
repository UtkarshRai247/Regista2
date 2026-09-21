"""
Task 01b — pre-join diagnostics. No market data touched.

Section 1: sample flow table, all events -> final >=200-pass units.
Section 2: Gate A reliability re-estimated with 100 repeated random
           splits at the 200-pass threshold (supersedes single-split).
Section 3: Step 2 pass-success calibration on CHOSEN passes only.
Section 4: descriptives + top/bottom 10 by Decision for the 200-pass
           (138-unit) sample.

Run: python src/decision_engine/task01b_diagnostics.py
"""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb

from decompose import build_per_pass_table, match_competition_lookup
from options import EXCLUDED_PASS_TYPES

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
EVENTS_DIR = DATA_DIR / "raw" / "events"
FRAMES_DIR = DATA_DIR / "raw" / "frames"
POLICY_PATH = DATA_DIR / "processed" / "options_policy.parquet"
SCORED_PATH = DATA_DIR / "processed" / "options_scored.parquet"
PV_MODEL_PATH = DATA_DIR / "processed" / "possession_value_model.json"
METRICS_PATH = DATA_DIR / "processed" / "player_season_metrics.parquet"
RNG_SEED = 42
THRESHOLD = 200
N_REPEATS = 100


def spearman_brown(r: float) -> float:
    if r >= 1:
        return 1.0
    return (2 * r) / (1 + r)


# ---------- Section 1: sample flow ----------
def sample_flow():
    match_ids = sorted(int(p.stem) for p in EVENTS_DIR.glob("*.parquet"))
    n_all_events = 0
    n_passes = 0
    n_open_play = 0
    n_frame_present = 0
    n_visible_ok = 0

    for mid in match_ids:
        ev = pd.read_parquet(EVENTS_DIR / f"{mid}.parquet")
        n_all_events += len(ev)
        is_pass = ev["type"] == "Pass"
        n_passes += int(is_pass.sum())

        open_play = ev[is_pass
                        & (~ev["pass_type"].isin(EXCLUDED_PASS_TYPES))
                        & (ev["position"] != "Goalkeeper")]
        n_open_play += len(open_play)

        frames = pd.read_parquet(FRAMES_DIR / f"{mid}.parquet")
        sizes = frames.groupby("id").size()
        has_frame = open_play["id"].isin(sizes.index)
        n_frame_present += int(has_frame.sum())
        visible_ok = open_play["id"].map(sizes).fillna(0) >= 6
        n_visible_ok += int(visible_ok.sum())

    options_summary = json.loads((DATA_DIR / "options_summary.json").read_text())
    n_matched = options_summary["matched"]

    metrics = pd.read_parquet(METRICS_PATH)
    n_units_all = len(metrics)
    thresholded = metrics[metrics["n_eligible_passes"] >= THRESHOLD]
    n_units_thresholded = len(thresholded)
    n_distinct_players = thresholded["player_id"].nunique()

    return {
        "all_events": n_all_events,
        "passes": n_passes,
        "open_play": n_open_play,
        "freeze_frame_present": n_frame_present,
        "visible_ge_6": n_visible_ok,
        "angle_match_accepted": n_matched,
        "aggregated_player_competition_season_units": n_units_all,
        f"units_with_ge_{THRESHOLD}_eligible_passes": n_units_thresholded,
        "distinct_players_in_final_sample": int(n_distinct_players),
    }, thresholded


# ---------- Section 2: repeated-split reliability ----------
def repeated_split_reliability(per_pass_with_season: pd.DataFrame):
    units = per_pass_with_season.groupby(["player_id", "competition_id", "season_id"]).filter(
        lambda g: len(g) >= THRESHOLD)
    grouped = list(units.groupby(["player_id", "competition_id", "season_id"]))

    rng = np.random.default_rng(RNG_SEED)
    results = {"decision": [], "execution": []}
    for _ in range(N_REPEATS):
        rows_d, rows_e = [], []
        for key, g in grouped:
            idx = rng.permutation(len(g))
            half = len(g) // 2
            h1, h2 = g.iloc[idx[:half]], g.iloc[idx[half:2 * half]]
            rows_d.append((h1["decision"].mean(), h2["decision"].mean()))
            rows_e.append((h1["execution"].mean(), h2["execution"].mean()))
        d1, d2 = zip(*rows_d)
        e1, e2 = zip(*rows_e)
        r_d = pd.Series(d1).corr(pd.Series(d2))
        r_e = pd.Series(e1).corr(pd.Series(e2))
        results["decision"].append(spearman_brown(r_d))
        results["execution"].append(spearman_brown(r_e))

    out = {}
    for metric, vals in results.items():
        arr = np.array(vals)
        out[metric] = {
            "n_repeats": N_REPEATS, "n_units": len(grouped),
            "median": float(np.median(arr)),
            "p5": float(np.percentile(arr, 5)),
            "p95": float(np.percentile(arr, 95)),
        }
    return out


# ---------- Section 3: calibration on chosen passes ----------
def chosen_calibration():
    scored = pd.read_parquet(SCORED_PATH)
    chosen = scored[scored["chosen"]].copy()
    chosen["bin"] = pd.qcut(chosen["p_success"], 10, duplicates="drop")
    table = []
    for b, g in chosen.groupby("bin", observed=True):
        table.append({
            "bin": str(b), "n": int(len(g)),
            "mean_predicted": float(g["p_success"].mean()),
            "mean_actual": float(g["pass_complete"].mean()),
        })
    overall_pred = float(chosen["p_success"].mean())
    overall_actual = float(chosen["pass_complete"].mean())
    return table, overall_pred, overall_actual


# ---------- Section 4: descriptives ----------
def descriptives(thresholded: pd.DataFrame):
    comp_names = {
        (9, 281): "Bundesliga 2023/24", (43, 106): "FIFA World Cup 2022",
        (11, 90): "La Liga 2020/21", (7, 235): "Ligue 1 2022/23",
        (7, 108): "Ligue 1 2021/22", (44, 107): "MLS 2023",
        (55, 282): "UEFA Euro 2024", (55, 43): "UEFA Euro 2020",
    }
    match_ids = sorted(int(p.stem) for p in EVENTS_DIR.glob("*.parquet"))
    pos_counts = {}
    for mid in match_ids:
        ev = pd.read_parquet(EVENTS_DIR / f"{mid}.parquet")
        sub = ev.dropna(subset=["player_id", "position"])
        for pid, pos in zip(sub["player_id"], sub["position"]):
            pos_counts.setdefault(pid, {}).setdefault(pos, 0)
            pos_counts[pid][pos] += 1
    mode_position = {pid: max(counts, key=counts.get) for pid, counts in pos_counts.items()}

    df = thresholded.copy()
    df["position"] = df["player_id"].map(mode_position)
    df["competition"] = df.apply(
        lambda r: comp_names.get((r["competition_id"], r["season_id"]), "?"), axis=1)

    stats = {"mean": float(df["decision_per_100"].mean()), "sd": float(df["decision_per_100"].std())}
    top10 = df.nlargest(10, "decision_per_100")[
        ["player_id", "competition", "position", "decision_per_100", "n_eligible_passes"]
    ].to_dict("records")
    bottom10 = df.nsmallest(10, "decision_per_100")[
        ["player_id", "competition", "position", "decision_per_100", "n_eligible_passes"]
    ].to_dict("records")
    return stats, top10, bottom10


def main():
    print("=== Section 1: sample flow ===")
    flow, thresholded = sample_flow()
    print(json.dumps(flow, indent=2))

    print("\n=== Section 2: repeated-split reliability (100 splits, 200-pass threshold) ===")
    policy = pd.read_parquet(POLICY_PATH)
    pv_model = xgb.XGBClassifier()
    pv_model.load_model(PV_MODEL_PATH)
    per_pass = build_per_pass_table(policy, pv_model, verbose=False)
    comp_lookup = match_competition_lookup()
    per_pass["competition_id"] = per_pass["match_id"].map(lambda m: comp_lookup.get(m, (None, None))[0])
    per_pass["season_id"] = per_pass["match_id"].map(lambda m: comp_lookup.get(m, (None, None))[1])
    repeated = repeated_split_reliability(per_pass)
    print(json.dumps(repeated, indent=2))

    print("\n=== Section 3: calibration on chosen passes ===")
    calib_table, overall_pred, overall_actual = chosen_calibration()
    print(f"Overall (chosen passes only): predicted={overall_pred:.4f} actual={overall_actual:.4f}")
    print(json.dumps(calib_table, indent=2))

    print("\n=== Section 4: descriptives ===")
    stats, top10, bottom10 = descriptives(thresholded)
    print(json.dumps(stats, indent=2))
    print("Top 10:", json.dumps(top10, indent=2, default=str))
    print("Bottom 10:", json.dumps(bottom10, indent=2, default=str))

    result = {
        "sample_flow": flow, "repeated_split_reliability": repeated,
        "chosen_calibration": {"table": calib_table, "overall_predicted": overall_pred,
                                "overall_actual": overall_actual},
        "descriptives": {"stats": stats, "top10": top10, "bottom10": bottom10},
    }
    (DATA_DIR / "task01b_diagnostics.json").write_text(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
