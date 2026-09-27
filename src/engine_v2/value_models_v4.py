"""
Task 22, Step 2+3: two definitional fixes to the value-model training
rows, found by reading `value_models.py`'s `build_match_rows` (reused
unchanged from engine v1) rather than by a new feature search:

DEFECT A (wrong perspective): every event with a location+frame becomes
a training row valued from the ACTING team's own view, even when that
team does not have the ball. Fix: a row is only written to the training
file if `team == possession_team` (StatsBomb's own `possession_team`
column, already present on every raw event). This affects ROW
SELECTION only, not label computation, and not score bookkeeping
(which must still see every event, in or out of possession, to track
the running score correctly).

DEFECT B (label skips its own event): the lookahead was
`range(i+1, min(i+1+LOOKAHEAD, n))`, so a Shot that scores at event i
gets label_for=0 on its own row. Fix: `range(i, min(i+LOOKAHEAD, n))`
-- same window length (10), shifted to include the event's own outcome.

Both label sets (old and new) are computed for every location+frame
event (regardless of possession) and written to a DIAGNOSTIC file,
so Task 22's Step 2 tables (T-a/T-b/T-c) are reproducible from this
committed script, unlike Task 21's Step 3 table. The actual new
TRAINING file (value_model_rows_v4.parquet) is the diagnostic rows
filtered to in_possession==True, with label_for_new/label_against_new
renamed to label_for/label_against so train_one/STATE_FEATURES (from
value_models.py, Task 21's 3 features already removed in Step 1) work
unchanged.

Step 3 (retraining) runs in this same script, gated on Step 2's
premise check (T-c): PASS only if, in BOTH bands 80-100 and 100-120,
beyond-line's P(score in 10) is strictly higher than not-beyond's. If
it fails, the script stops after writing the rows/diagnostic/tables --
no training, per the brief's explicit "no retraining, report, done."

Run: python src/engine_v2/value_models_v4.py
"""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

from geometry import team_period_directions, normalize_xy
from value_models import (
    frame_ahead_features, train_one, run_t2, PATTERN_CODE,
    EVENTS_DIR, FRAMES_DIR, LOOKAHEAD,
)

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
DIAGNOSTIC_PATH = DATA_DIR / "processed" / "engine_v2" / "value_model_rows_diagnostic_v4.parquet"
OUT_PATH = DATA_DIR / "processed" / "engine_v2" / "value_model_rows_v4.parquet"
MODEL_FOR_PATH = DATA_DIR / "processed" / "engine_v2" / "value_model_for_v4.json"
MODEL_AGAINST_PATH = DATA_DIR / "processed" / "engine_v2" / "value_model_against_v4.json"
TABLES_PATH = DATA_DIR / "engine_v2_step2_tables_v4.json"
SUMMARY_PATH = DATA_DIR / "engine_v2_step3_value_models_v4.json"
TASK19D_SUMMARY_PATH = DATA_DIR / "engine_v2_step3_value_models_v2.json"

BANDS = [(0, 40), (40, 60), (60, 80), (80, 100), (100, 120)]


def build_match_rows_v4(match_id: int) -> tuple:
    """Adapted from value_models.build_match_rows: computes BOTH old
    and new label sets and an in_possession flag for every event with a
    resolvable location+frame. Score bookkeeping is untouched -- it
    runs over every event, regardless of possession or row inclusion,
    exactly as before."""
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

        prev_loc = None
        for j in range(i - 1, -1, -1):
            pl = ev.iloc[j]["location"]
            if pl is not None and not (isinstance(pl, float) and pd.isna(pl)):
                prev_loc = pl
                break
        if prev_loc is None:
            prev_loc = loc

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


def build_tables(diag: pd.DataFrame) -> dict:
    # T-a: Task 21's zero cell (band 80-100, beyond line, teammate within 5u)
    zero_cell = diag[(diag["ball_x"] >= 80) & (diag["ball_x"] < 100)
                      & (diag["ball_beyond_defensive_line"]) & (diag["teammates_within_5u"] > 0)]
    n_zero_cell = len(zero_cell)
    n_out_of_poss = int((~zero_cell["in_possession"]).sum())
    top_types_out_of_poss = zero_cell[~zero_cell["in_possession"]]["type"].value_counts().head(10).to_dict()
    t_a = {
        "n_rows_in_zero_cell": n_zero_cell,
        "n_out_of_possession": n_out_of_poss,
        "share_out_of_possession": n_out_of_poss / n_zero_cell if n_zero_cell else None,
        "top_event_types_out_of_possession": top_types_out_of_poss,
    }

    # T-b: rows whose label_for changes old -> new, and how many are Shot
    changed = diag[diag["label_for_old"] != diag["label_for_new"]]
    t_b = {
        "n_rows_total": len(diag),
        "n_label_for_changed": len(changed),
        "n_label_for_changed_shot": int((changed["type"] == "Shot").sum()),
    }

    # T-c: PREMISE TABLE, in-possession rows only, new labels
    in_poss = diag[diag["in_possession"]].copy()
    in_poss["band"] = in_poss["ball_x"].apply(band_of)
    t_c_rows = []
    for lo, hi in BANDS:
        band_label = f"{lo}-{hi}"
        band_df = in_poss[in_poss["band"] == band_label]
        for beyond in (False, True):
            sub = band_df[band_df["ball_beyond_defensive_line"] == beyond]
            n = len(sub)
            t_c_rows.append({
                "band": band_label, "beyond_line": beyond, "n": n,
                "p_score_in_10": float(sub["label_for_new"].mean()) if n else None,
                "p_concede_in_10": float(sub["label_against_new"].mean()) if n else None,
            })
    t_c = {"rows": t_c_rows}

    # Premise check: in BOTH bands 80-100 and 100-120, beyond strictly > not-beyond
    def rate(band, beyond):
        for r in t_c_rows:
            if r["band"] == band and r["beyond_line"] == beyond:
                return r["p_score_in_10"]
        return None

    band_verdicts = {}
    for band in ("80-100", "100-120"):
        p_beyond = rate(band, True)
        p_not_beyond = rate(band, False)
        band_verdicts[band] = {
            "p_score_beyond": p_beyond, "p_score_not_beyond": p_not_beyond,
            "holds": bool(p_beyond is not None and p_not_beyond is not None and p_beyond > p_not_beyond),
        }
    premise_holds = all(v["holds"] for v in band_verdicts.values())

    return {"T_a": t_a, "T_b": t_b, "T_c": t_c, "premise_band_verdicts": band_verdicts, "premise_holds": premise_holds}


def main():
    print("Task 22 Step 2: building rows with both defect fixes ...")
    match_ids = sorted(int(p.stem) for p in EVENTS_DIR.glob("*.parquet"))
    all_rows, n_total, n_no_loc, n_no_frame = [], 0, 0, 0
    for i, mid in enumerate(match_ids):
        rows, n, nl, nf = build_match_rows_v4(mid)
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
    print(f"  in_possession rows: {n_in_possession} ({n_in_possession / len(diag):.4f}), "
          f"out_of_possession: {len(diag) - n_in_possession} ({1 - n_in_possession / len(diag):.4f})")

    train_df = diag[diag["in_possession"]].copy()
    train_df = train_df.rename(columns={"label_for_new": "label_for", "label_against_new": "label_against"})
    train_df = train_df.drop(columns=["label_for_old", "label_against_old"])
    train_df.to_parquet(OUT_PATH)
    print(f"  wrote {len(train_df)} in-possession training rows to {OUT_PATH}")

    print("  building T-a/T-b/T-c tables ...")
    tables = build_tables(diag)
    print(json.dumps(tables, indent=2, default=str))
    TABLES_PATH.write_text(json.dumps(tables, indent=2, default=str))
    print(f"\nWrote {TABLES_PATH}")

    if not tables["premise_holds"]:
        print("\nPREMISE FAILS -- stopping here per the brief. No retraining.")
        return {"tables": tables, "trained": False}

    print("\nPremise holds in both bands 80-100 and 100-120 -- proceeding to retrain.")
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

    task19d_summary = json.loads(TASK19D_SUMMARY_PATH.read_text())

    summary = {
        "n_total_events": n_total, "n_no_location": n_no_loc, "n_no_frame": n_no_frame,
        "n_diagnostic_rows": len(diag), "n_in_possession_rows": n_in_possession,
        "M_for": {k: v for k, v in res_for.items() if k != "model"},
        "M_against": {k: v for k, v in res_against.items() if k != "model"},
        "T2": t2, "T2_sign": t2_sign,
        "task19d_M_for": task19d_summary["M_for"], "task19d_M_against": task19d_summary["M_against"], "task19d_T2": task19d_summary["T2"],
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
    print(f"\nWrote {SUMMARY_PATH}")
    return {"tables": tables, "trained": True, "summary": summary}


if __name__ == "__main__":
    main()
