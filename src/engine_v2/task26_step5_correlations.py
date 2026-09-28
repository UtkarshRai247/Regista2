"""
Task 26, Step 5: correlation matrix among Decision, Risk, move_on_speed,
hold_variation, median_time_on_ball, completion rate,
progressive_passes_per_90, xA per 90 -- at the Step 3 threshold (100
pooled eligible passes), overall AND within the DEEP/DEFENSIVE
MIDFIELD group. Execution is omitted (engine v5 does not compute it,
per Task 24/25's disclosed exclusion).

Pooling, disclosed: every metric is pooled per player_id the SAME way
Decision itself is pooled for the leaderboard (Step 4) -- fully across
all of a player's own raw observations, ignoring competition-season
boundaries, rather than a weighted-average-of-per-season-means (a
second aggregation layer that isn't needed when the raw per-observation
file is available): Decision/Risk from `pass_der_v8.parquet`'s own
rows; move_on_speed/hold_variation from `redesign_metrics_v2.py`'s own
per-observation residual files; median_time_on_ball from
`tempo_time_on_ball.parquet`'s own per-pass rows. completion_pct/
progressive_passes_per_90/xa_per_90 exist only as pre-aggregated
per-(player, competition, season) rates in
`player_season_metrics.parquet` (engine v1 infrastructure, reused only
for these non-Decision columns, per `src/tempo/relationships.py`'s own
precedent) -- these are pooled per player as an eligible-passes-weighted
average across the player's own rows in that table, disclosed as the
one place a second-layer aggregation was unavoidable.

Run: python src/engine_v2/task26_step5_correlations.py
"""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
PASS_DER_V8_PATH = DATA_DIR / "processed" / "engine_v2" / "pass_der_v8.parquet"
MOVE_RESID_V2_PATH = DATA_DIR / "processed" / "tempo_redesign_move_residuals_v2.parquet"
HOLD_RESID_V2_PATH = DATA_DIR / "processed" / "tempo_redesign_hold_residuals_v2.parquet"
TIME_ON_BALL_PATH = DATA_DIR / "processed" / "tempo_time_on_ball.parquet"
PLAYER_SEASON_METRICS_PATH = DATA_DIR / "processed" / "player_season_metrics.parquet"
LEADERBOARD_PATH = DATA_DIR / "processed" / "leaderboard_v5.parquet"
SUMMARY_PATH = DATA_DIR / "engine_v2_task26_step5_correlations.json"

METRIC_COLS = ["decision_per_100", "risk_per_100", "move_on_speed", "hold_variation",
               "median_time_on_ball", "completion_pct", "progressive_passes_per_90", "xa_per_90"]
CORR_THRESHOLD = 0.7


def weighted_avg(g: pd.DataFrame, val_col: str, w_col: str):
    w = g[w_col]
    if w.sum() == 0 or g[val_col].isna().all():
        return np.nan
    return float(np.average(g[val_col].dropna(), weights=w.loc[g[val_col].dropna().index]))


def main():
    print("Task 26 Step 5: correlation matrix at the Step 3 threshold ...")
    leaderboard = pd.read_parquet(LEADERBOARD_PATH, columns=["player_id", "is_deep_def_mid"])
    qualifying_ids = set(leaderboard["player_id"])
    print(f"  qualifying players: {len(qualifying_ids)}")

    per_pass = pd.read_parquet(PASS_DER_V8_PATH, columns=["player_id", "decision_new", "risk_new"])
    per_pass = per_pass[per_pass["player_id"].isin(qualifying_ids)]
    dr = per_pass.groupby("player_id").agg(
        decision_per_100=("decision_new", lambda s: s.mean() * 100),
        risk_per_100=("risk_new", lambda s: s.mean() * 100)).reset_index()

    move_resid = pd.read_parquet(MOVE_RESID_V2_PATH, columns=["player_id", "residual"])
    move_resid = move_resid[move_resid["player_id"].isin(qualifying_ids)]
    move = move_resid.groupby("player_id")["residual"].mean().rename("move_on_speed").reset_index()

    hold_resid = pd.read_parquet(HOLD_RESID_V2_PATH, columns=["player_id", "residual"])
    hold_resid = hold_resid[hold_resid["player_id"].isin(qualifying_ids)]
    hold = hold_resid.groupby("player_id")["residual"].agg(lambda s: float(s.std(ddof=1)) if len(s) > 1 else None).rename("hold_variation").reset_index()

    tob = pd.read_parquet(TIME_ON_BALL_PATH, columns=["player_id", "time_on_ball", "resolved"])
    tob = tob[tob["resolved"] & tob["player_id"].isin(qualifying_ids)]
    tob_med = tob.groupby("player_id")["time_on_ball"].median().rename("median_time_on_ball").reset_index()

    psm = pd.read_parquet(PLAYER_SEASON_METRICS_PATH,
                           columns=["player_id", "n_eligible_passes", "completion_pct",
                                    "progressive_passes_per_90", "xa_per_90"])
    psm = psm[psm["player_id"].isin(qualifying_ids)]
    ref_rows = []
    for pid, g in psm.groupby("player_id"):
        ref_rows.append({
            "player_id": pid,
            "completion_pct": weighted_avg(g, "completion_pct", "n_eligible_passes"),
            "progressive_passes_per_90": weighted_avg(g, "progressive_passes_per_90", "n_eligible_passes"),
            "xa_per_90": weighted_avg(g, "xa_per_90", "n_eligible_passes"),
        })
    ref = pd.DataFrame(ref_rows)

    table = leaderboard.merge(dr, on="player_id", how="left").merge(move, on="player_id", how="left") \
        .merge(hold, on="player_id", how="left").merge(tob_med, on="player_id", how="left") \
        .merge(ref, on="player_id", how="left")

    def corr_report(df: pd.DataFrame, label: str) -> dict:
        sub = df[METRIC_COLS]
        n_available = {c: int(sub[c].notna().sum()) for c in METRIC_COLS}
        corr = sub.corr()
        pairs_beyond = []
        for i, a in enumerate(METRIC_COLS):
            for b in METRIC_COLS[i + 1:]:
                r = corr.loc[a, b]
                if pd.notna(r) and abs(r) > CORR_THRESHOLD:
                    pairs_beyond.append({"pair": [a, b], "r": float(r)})
        print(f"\n  [{label}] n={len(df)}, pairs with |r|>{CORR_THRESHOLD}: {pairs_beyond}")
        print(f"  [{label}] Decision vs xA per 90: r={corr.loc['decision_per_100', 'xa_per_90']:.4f}")
        return {"n": len(df), "n_available_per_metric": n_available,
                "correlation_matrix": corr.to_dict(), "pairs_beyond_threshold": pairs_beyond,
                "decision_vs_xa_per_90": float(corr.loc["decision_per_100", "xa_per_90"])}

    overall_report = corr_report(table, "overall")
    deep_def_mid_report = corr_report(table[table["is_deep_def_mid"]], "DEEP/DEFENSIVE MIDFIELD")

    summary = {"overall": overall_report, "deep_defensive_midfield": deep_def_mid_report,
               "correlation_threshold": CORR_THRESHOLD}
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
    print(f"\nWrote {SUMMARY_PATH}")
    return summary


if __name__ == "__main__":
    main()
