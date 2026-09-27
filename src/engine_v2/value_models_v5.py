"""
Task 24, Step 2+3: value-model rows rebuilt on CORRECTED coordinates
(geometry.py's team_period_directions now returns +1 for every
(team, period), fixed after direct coordinate evidence showed
StatsBomb events/360 frames are already team-relative -- see
geometry.py's docstring and task24_evidence.py).

`build_match_rows_v5` is copied from Task 22's `build_match_rows_v4`
(value_models_v4.py) -- NOT modified in place, preserving Task 22's own
results page's exact reproducibility from its own recorded commit --
with ONE further fix: `prev_x`/`prev_y` (Step 1(c)'s cross-team-
combination defect) is now rotated 180 degrees whenever the located
previous event's own team differs from the current event's team. Under
team-relative coordinates a location from a DIFFERENT team's event is
expressed in THAT team's own attacking frame, not the current event's
team's frame, so combining it unrotated is wrong regardless of
`team_period_directions`'s own fix. Task 22's fixes A (in-possession
rows only) and B (label counts its own event) are kept exactly. Task
21's 3 possession-state features stay out of STATE_FEATURES (already
true in value_models.py since Task 22's Step 1).

Step 3's geometry checkpoint (G1-G4) runs entirely off the rows this
script builds -- no candidate/EV corpus needed yet, so a G1/G2 failure
is caught before the much more expensive Step 4 rebuild (grid.py
onward). Retraining (M_for/M_against, T2) only happens if BOTH G1 and
G2 pass.

Run: python src/engine_v2/value_models_v5.py
"""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

from geometry import team_period_directions, normalize_xy, PITCH_X, PITCH_Y
from value_models import (
    frame_ahead_features, train_one, run_t2, PATTERN_CODE,
    EVENTS_DIR, FRAMES_DIR, LOOKAHEAD,
)

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
DIAGNOSTIC_PATH = DATA_DIR / "processed" / "engine_v2" / "value_model_rows_diagnostic_v5.parquet"
OUT_PATH = DATA_DIR / "processed" / "engine_v2" / "value_model_rows_v5.parquet"
MODEL_FOR_PATH = DATA_DIR / "processed" / "engine_v2" / "value_model_for_v5.json"
MODEL_AGAINST_PATH = DATA_DIR / "processed" / "engine_v2" / "value_model_against_v5.json"
CHECKPOINT_PATH = DATA_DIR / "engine_v2_task24_step3_checkpoint.json"
SUMMARY_PATH = DATA_DIR / "engine_v2_step3_value_models_v5.json"
TASK15_SUMMARY_PATH = DATA_DIR / "engine_v2_step5_value_models.json"
TASK19D_SUMMARY_PATH = DATA_DIR / "engine_v2_step3_value_models_v2.json"

BANDS = [(0, 40), (40, 60), (60, 80), (80, 100), (100, 120)]
G1_MAX_SHARE_BAND_0_40_BEYOND = 0.01


def build_match_rows_v5(match_id: int) -> tuple:
    """Identical to value_models_v4.build_match_rows_v4 except prev_loc
    is rotated 180 degrees when the previous event's own team differs
    from the current event's team (Step 1(c)'s cross-team-combination
    fix)."""
    ev = pd.read_parquet(EVENTS_DIR / f"{match_id}.parquet")
    frames = pd.read_parquet(FRAMES_DIR / f"{match_id}.parquet")
    ev = ev.sort_values("index").reset_index(drop=True)
    frames_by_event = {eid: g for eid, g in frames.groupby("id")}

    ev["t"] = ev["minute"] * 60 + ev["second"]
    period_end = ev.groupby("period")["t"].transform("max")
    directions = team_period_directions(ev)

    teams = ev["team"].dropna().unique().tolist()
    score = {t: 0 for t in teams}
    is_goal = ((ev["type"] == "Shot") & (ev["shot_outcome"] == "Goal")) | (ev["type"] == "Own Goal Against")

    rows = []
    n = len(ev)
    n_no_location, n_no_frame = 0, 0
    for i in range(n):
        row = ev.iloc[i]
        team = row["team"]
        opp_teams = [t for t in teams if t != team]
        opponent = opp_teams[0] if opp_teams else None

        loc = row["location"]
        if loc is None or (isinstance(loc, float) and pd.isna(loc)):
            n_no_location += 1
            if is_goal.iloc[i]:
                scorer = opponent if row["type"] == "Own Goal Against" else team
                if scorer in score:
                    score[scorer] += 1
            continue

        frame = frames_by_event.get(row["id"])
        if frame is None or len(frame) == 0:
            n_no_frame += 1
            if is_goal.iloc[i]:
                scorer = opponent if row["type"] == "Own Goal Against" else team
                if scorer in score:
                    score[scorer] += 1
            continue

        prev_loc, prev_team = None, None
        for j in range(i - 1, -1, -1):
            pl = ev.iloc[j]["location"]
            if pl is not None and not (isinstance(pl, float) and pd.isna(pl)):
                prev_loc = pl
                prev_team = ev.iloc[j]["team"]
                break
        if prev_loc is None:
            prev_loc = loc
            prev_team = team
        if prev_team != team:
            # Step 1(c) fix: the previous event belongs to the OTHER team,
            # whose own event is expressed in ITS OWN attacking frame under
            # team-relative coordinates -- rotate into the current team's frame.
            prev_loc = (PITCH_X - prev_loc[0], PITCH_Y - prev_loc[1])

        def label_in_window(k_range):
            lf, la = 0, 0
            for k in k_range:
                if is_goal.iloc[k]:
                    fut = ev.iloc[k]
                    if fut["type"] == "Own Goal Against":
                        scorer_k = [t for t in teams if t != fut["team"]]
                        scorer_k = scorer_k[0] if scorer_k else None
                    else:
                        scorer_k = fut["team"]
                    if scorer_k == team:
                        lf = 1
                    elif scorer_k == opponent:
                        la = 1
                    break
            return lf, la

        label_for_old, label_against_old = label_in_window(range(i + 1, min(i + 1 + LOOKAHEAD, n)))
        label_for_new, label_against_new = label_in_window(range(i, min(i + LOOKAHEAD, n)))

        score_diff = score.get(team, 0) - score.get(opponent, 0) if opponent else 0
        direction = directions.get((team, row["period"]), 1)
        ball_raw = np.array(loc, dtype=float)
        attack_x, attack_y = normalize_xy(loc[0], loc[1], direction)
        prev_attack_x, prev_attack_y = normalize_xy(prev_loc[0], prev_loc[1], direction)
        ahead = frame_ahead_features(frame, ball_raw, direction)

        rec = {
            "match_id": match_id, "event_id": row["id"], "type": row["type"],
            "team": team, "possession_team": row["possession_team"],
            "in_possession": bool(team == row["possession_team"]),
            "ball_x": attack_x, "ball_y": attack_y,
            "prev_x": prev_attack_x, "prev_y": prev_attack_y,
            "time_remaining_period": float(period_end.iloc[i] - row["t"]),
            "score_diff": score_diff,
            "play_pattern_code": PATTERN_CODE.get(row["play_pattern"], PATTERN_CODE["Other"]),
            "label_for_old": label_for_old, "label_against_old": label_against_old,
            "label_for_new": label_for_new, "label_against_new": label_against_new,
        }
        rec.update(ahead)
        rows.append(rec)

        if is_goal.iloc[i]:
            scorer = opponent if row["type"] == "Own Goal Against" else team
            if scorer in score:
                score[scorer] += 1

    return rows, n, n_no_location, n_no_frame


def band_of(x: float) -> str:
    for lo, hi in BANDS:
        if lo <= x < hi:
            return f"{lo}-{hi}"
    return None


def g1_check(in_poss: pd.DataFrame) -> dict:
    band_df = in_poss[(in_poss["ball_x"] >= 0) & (in_poss["ball_x"] < 40)]
    n = len(band_df)
    n_beyond = int(band_df["ball_beyond_defensive_line"].sum())
    share = n_beyond / n if n else None
    return {"n_rows_band_0_40": n, "n_beyond_line": n_beyond, "share_beyond_line": share,
            "G1_pass": bool(share is not None and share < G1_MAX_SHARE_BAND_0_40_BEYOND)}


def g2_check(in_poss: pd.DataFrame) -> dict:
    rates = {}
    for lo, hi in BANDS:
        band_label = f"{lo}-{hi}"
        sub = in_poss[(in_poss["ball_x"] >= lo) & (in_poss["ball_x"] < hi)]
        rates[band_label] = {"n": len(sub), "p_score_in_10": float(sub["label_for_new"].mean()) if len(sub) else None}
    r040, r80100, r100120 = rates["0-40"]["p_score_in_10"], rates["80-100"]["p_score_in_10"], rates["100-120"]["p_score_in_10"]
    ordered = r040 is not None and r80100 is not None and r100120 is not None and r040 < r80100 < r100120
    return {"rates_by_band": rates, "G2_pass": bool(ordered)}


def g4_task22_premise_table(in_poss: pd.DataFrame) -> list:
    rows = []
    for lo, hi in BANDS:
        band_label = f"{lo}-{hi}"
        band_df = in_poss[in_poss["band"] == band_label]
        for beyond in (False, True):
            sub = band_df[band_df["ball_beyond_defensive_line"] == beyond]
            n = len(sub)
            rows.append({"band": band_label, "beyond_line": beyond, "n": n,
                         "p_score_in_10": float(sub["label_for_new"].mean()) if n else None,
                         "p_concede_in_10": float(sub["label_against_new"].mean()) if n else None})
    return rows


def g4_task23_central_channel_table(in_poss: pd.DataFrame) -> list:
    rows = []
    for lo, hi in ((80, 100), (100, 120)):
        band_label = f"{lo}-{hi}"
        band_df = in_poss[in_poss["band"] == band_label]
        central_mask = (band_df["ball_y"] - 40).abs() <= 10
        for channel, mask in (("CENTRAL", central_mask), ("WIDE", ~central_mask)):
            chan_df = band_df[mask]
            for beyond in (False, True):
                sub = chan_df[chan_df["ball_beyond_defensive_line"] == beyond]
                n = len(sub)
                rows.append({"band": band_label, "channel": channel, "beyond_line": beyond, "n": n,
                             "p_score_in_10": float(sub["label_for_new"].mean()) if n else None,
                             "p_concede_in_10": float(sub["label_against_new"].mean()) if n else None})
    return rows


def main():
    print("Task 24 Step 2+3: rebuilding value-model rows on corrected coordinates ...")
    match_ids = sorted(int(p.stem) for p in EVENTS_DIR.glob("*.parquet"))
    all_rows, n_total, n_no_loc, n_no_frame = [], 0, 0, 0
    for i, mid in enumerate(match_ids):
        rows, n, nl, nf = build_match_rows_v5(mid)
        all_rows.extend(rows)
        n_total += n
        n_no_loc += nl
        n_no_frame += nf
        if (i + 1) % 50 == 0:
            print(f"  {i + 1}/{len(match_ids)} matches, rows so far={len(all_rows)}")

    diag = pd.DataFrame(all_rows)
    diag.to_parquet(DIAGNOSTIC_PATH)
    print(f"  total raw events={n_total}, no_location={n_no_loc}, no_frame={n_no_frame}, diagnostic rows={len(diag)}")

    n_in_possession = int(diag["in_possession"].sum())
    print(f"  in_possession rows: {n_in_possession} ({n_in_possession / len(diag):.4f})")

    train_df = diag[diag["in_possession"]].copy()
    train_df = train_df.rename(columns={"label_for_new": "label_for", "label_against_new": "label_against"})
    train_df = train_df.drop(columns=["label_for_old", "label_against_old"])
    train_df.to_parquet(OUT_PATH)
    print(f"  wrote {len(train_df)} in-possession training rows to {OUT_PATH}")

    in_poss = diag[diag["in_possession"]].copy()
    in_poss["band"] = in_poss["ball_x"].apply(band_of)

    print("\n  G1 (share of band 0-40 in-possession rows beyond the defensive line, must be <1%) ...")
    g1 = g1_check(in_poss)
    print(f"    {g1}")

    print("  G2 (P(score in 10) must satisfy 0-40 < 80-100 < 100-120) ...")
    g2 = g2_check(in_poss)
    print(f"    {g2}")

    print("  G4 (report only): Task 22 premise table ...")
    g4_premise = g4_task22_premise_table(in_poss)
    for r in g4_premise:
        print(f"    {r}")
    print("  G4 (report only): Task 23 central-channel table ...")
    g4_channel = g4_task23_central_channel_table(in_poss)
    for r in g4_channel:
        print(f"    {r}")

    checkpoint = {
        "n_diagnostic_rows": len(diag), "n_in_possession_rows": n_in_possession,
        "G1": g1, "G2": g2, "G4_task22_premise_table": g4_premise, "G4_task23_central_channel_table": g4_channel,
        "checkpoint_pass": bool(g1["G1_pass"] and g2["G2_pass"]),
    }
    CHECKPOINT_PATH.write_text(json.dumps(checkpoint, indent=2, default=str))
    print(f"\nWrote {CHECKPOINT_PATH}")

    if not checkpoint["checkpoint_pass"]:
        print("\nG1 or G2 FAILED -- STOPPING. No models trained. Step 4 does not run.")
        return {"checkpoint": checkpoint, "trained": False}

    print("\nG1 and G2 both PASS -- proceeding to retrain M_for/M_against.")
    print("  training M_for ...")
    res_for = train_one(train_df, "label_for")
    print(f"    n_train={res_for['n_train']}, n_test={res_for['n_test']}, positive_rate={res_for['positive_rate']:.4f}, AUC={res_for['auc']:.4f}")
    print("  training M_against ...")
    res_against = train_one(train_df, "label_against")
    print(f"    n_train={res_against['n_train']}, n_test={res_against['n_test']}, positive_rate={res_against['positive_rate']:.4f}, AUC={res_against['auc']:.4f}")

    res_for["model"].save_model(str(MODEL_FOR_PATH))
    res_against["model"].save_model(str(MODEL_AGAINST_PATH))

    print("  T2 (magnitude verdict AND sign) ...")
    t2 = run_t2(res_for["model"], train_df)
    print(f"    {t2}")
    t2_sign = "POSITIVE (more numerical advantage ahead -> higher scoring probability)" if t2["diff"] > 0 else \
              "NEGATIVE (more numerical advantage ahead -> lower scoring probability)"
    print(f"    T2 sign: {t2_sign}")

    task15_summary = json.loads(TASK15_SUMMARY_PATH.read_text())
    task19d_summary = json.loads(TASK19D_SUMMARY_PATH.read_text())

    summary = {
        "n_total_events": n_total, "n_no_location": n_no_loc, "n_no_frame": n_no_frame,
        "n_diagnostic_rows": len(diag), "n_in_possession_rows": n_in_possession,
        "M_for": {k: v for k, v in res_for.items() if k != "model"},
        "M_against": {k: v for k, v in res_against.items() if k != "model"},
        "T2": t2, "T2_sign": t2_sign,
        "task15_M_for": task15_summary["M_for"], "task15_M_against": task15_summary["M_against"], "task15_T2": task15_summary["T2"],
        "task19d_M_for": task19d_summary["M_for"], "task19d_M_against": task19d_summary["M_against"], "task19d_T2": task19d_summary["T2"],
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
    print(f"\nWrote {SUMMARY_PATH}")
    return {"checkpoint": checkpoint, "trained": True, "summary": summary}


if __name__ == "__main__":
    main()
