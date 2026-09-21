"""
Task 01 — Step 3: possession value model.

Estimates P(possessing team scores within next 10 actions | game state),
trained on the FULL event stream (all action types) of the 299-match
study sample (per D-010) — not restricted to passes-with-freeze-frames.
Deliberately NOT a location-only grid: includes recent-action context,
time remaining in the period, score differential, and possession phase.

Per D-010, this model may train on the same matches later used for
player evaluation (not leakage — it estimates a game-state property, not
a player-level target), so the held-out split here is a random row
split, not match-disjoint (match-disjointness is Step 2's requirement,
where leakage would matter).

Run: python src/decision_engine/possession_value.py
"""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split

from pitch_direction import team_period_directions, normalize_xy

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
EVENTS_DIR = DATA_DIR / "raw" / "events"
OUT_DIR = DATA_DIR / "processed" / "possession_value_parts"
MODEL_PATH = DATA_DIR / "processed" / "possession_value_model.json"

LOOKAHEAD = 10
FEATURES = [
    "ball_x", "ball_y", "prev_x", "prev_y",
    "time_remaining_period", "score_diff", "play_pattern_code",
]

PLAY_PATTERNS = [
    "Regular Play", "From Corner", "From Free Kick", "From Throw In",
    "From Counter", "From Goal Kick", "From Keeper", "From Kick Off", "Other",
]
PATTERN_CODE = {p: i for i, p in enumerate(PLAY_PATTERNS)}


def build_match_rows(match_id: int) -> tuple[list[dict], int]:
    ev = pd.read_parquet(EVENTS_DIR / f"{match_id}.parquet")
    ev = ev.sort_values("index").reset_index(drop=True)

    # period end time (proxy for "time remaining"): max timestamp seen per period
    ev["t"] = ev["minute"] * 60 + ev["second"]
    period_end = ev.groupby("period")["t"].transform("max")

    directions, fallback_used, n_periods = team_period_directions(ev)

    # running score per team
    teams = ev["team"].dropna().unique().tolist()
    score = {t: 0 for t in teams}

    is_goal = (
        (ev["type"] == "Shot") & (ev["shot_outcome"] == "Goal")
    ) | (ev["type"] == "Own Goal Against")

    rows = []
    n = len(ev)
    for i in range(n):
        row = ev.iloc[i]
        team = row["team"]
        opp_teams = [t for t in teams if t != team]
        opponent = opp_teams[0] if opp_teams else None

        loc = row["location"]
        if loc is None or (isinstance(loc, float) and pd.isna(loc)):
            # still update score before skipping
            if is_goal.iloc[i]:
                scorer = team
                if row["type"] == "Own Goal Against":
                    scorer = opponent
                if scorer in score:
                    score[scorer] += 1
            continue

        prev_loc = None
        for j in range(i - 1, -1, -1):
            pl = ev.iloc[j]["location"]
            if pl is not None and not (isinstance(pl, float) and pd.isna(pl)):
                prev_loc = pl
                break
        if prev_loc is None:
            prev_loc = loc

        label = 0
        for k in range(i + 1, min(i + 1 + LOOKAHEAD, n)):
            fut = ev.iloc[k]
            if is_goal.iloc[k]:
                scorer = fut["team"]
                if fut["type"] == "Own Goal Against":
                    scorer = [t for t in teams if t != fut["team"]]
                    scorer = scorer[0] if scorer else None
                if scorer == team:
                    label = 1
                break

        score_diff = score.get(team, 0) - score.get(opponent, 0) if opponent else 0

        direction = directions.get((team, row["period"]), 1)
        attack_x, attack_y = normalize_xy(loc[0], loc[1], direction)
        prev_attack_x, prev_attack_y = normalize_xy(prev_loc[0], prev_loc[1], direction)

        rows.append({
            "match_id": match_id,
            "ball_x": attack_x, "ball_y": attack_y,
            "prev_x": prev_attack_x, "prev_y": prev_attack_y,
            "time_remaining_period": float(period_end.iloc[i] - row["t"]),
            "score_diff": score_diff,
            "play_pattern_code": PATTERN_CODE.get(row["play_pattern"], PATTERN_CODE["Other"]),
            "label": label,
        })

        if is_goal.iloc[i]:
            scorer = team
            if row["type"] == "Own Goal Against":
                scorer = opponent
            if scorer in score:
                score[scorer] += 1

    return rows, fallback_used, n_periods


def calibration_table(y_true, y_pred, n_bins=10) -> list[dict]:
    df = pd.DataFrame({"y": y_true, "p": y_pred})
    df["bin"] = pd.qcut(df["p"], n_bins, duplicates="drop")
    return [
        {"bin": str(b), "n": int(len(g)), "mean_predicted": float(g["p"].mean()),
         "mean_actual": float(g["y"].mean())}
        for b, g in df.groupby("bin", observed=True)
    ]


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    match_ids = sorted(int(p.stem) for p in EVENTS_DIR.glob("*.parquet"))
    print(f"{len(match_ids)} matches available for possession-value training")

    total_fallback, total_periods = 0, 0
    for i, mid in enumerate(match_ids):
        out_path = OUT_DIR / f"{mid}.parquet"
        if out_path.exists():
            continue
        rows, fallback_used, n_periods = build_match_rows(mid)
        if rows:
            pd.DataFrame(rows).to_parquet(out_path)
        total_fallback += fallback_used
        total_periods += n_periods
        if (i + 1) % 50 == 0:
            print(f"  {i + 1}/{len(match_ids)} matches processed")

    # separate lightweight pass so fallback stats are accurate even on a
    # resumed run where most matches were already built (and skipped above)
    total_fallback, total_periods = 0, 0
    for mid in match_ids:
        ev = pd.read_parquet(EVENTS_DIR / f"{mid}.parquet")
        _, fb, npd = team_period_directions(ev)
        total_fallback += fb
        total_periods += npd
    print(f"Attacking-direction fallback used in {total_fallback}/{total_periods} "
          f"team-periods (no shots by either team to infer direction from)")

    parts = list(OUT_DIR.glob("*.parquet"))
    df = pd.concat((pd.read_parquet(p) for p in parts), ignore_index=True)
    print(f"Total action-state rows: {len(df):,}, positive rate: {df['label'].mean():.4f}")

    X, y = df[FEATURES], df["label"]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    model = xgb.XGBClassifier(
        n_estimators=300, max_depth=5, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.8, random_state=42,
        eval_metric="logloss",
    )
    model.fit(X_train, y_train)
    model.save_model(MODEL_PATH)

    p_test = model.predict_proba(X_test)[:, 1]
    auc = roc_auc_score(y_test, p_test)
    calib = calibration_table(y_test.values, p_test)

    summary = {
        "n_matches": len(match_ids),
        "n_rows": len(df),
        "positive_rate": float(y.mean()),
        "n_train": len(X_train), "n_test": len(X_test),
        "auc": float(auc),
        "calibration": calib,
        "direction_fallback_periods": total_fallback,
        "direction_total_periods": total_periods,
    }
    print(json.dumps({k: v for k, v in summary.items() if k != "calibration"}, indent=2))
    (DATA_DIR / "possession_value_summary.json").write_text(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
