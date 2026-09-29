"""
Task 44, Step 2: event-only press resistance (PR2_flag), checked on the
292-match STUDY sample before any 2015/16 analysis.
docs/specs/task-44-big-five-1516.md.

PR2_flag: Task 43's spell, keep_spell and fwd_spell (task43_spells), but
PRESSURED = StatsBomb under_pressure on the Ball Receipt* OR on the
receiver's first on-ball event of the spell (his first Pass, Carry,
Dribble, Shot, Miscontrol or Dispossessed after the receipt in the same
possession). No frame needed. Baseline: Task 42's classifier settings;
context from events only: reception x, y (event location), play pattern,
period, minute; Task 35's folds.
GATE: Pearson r >= 0.70 between player mean PR2_flag_keep and Task 43's
PR2_keep, players with >= 50 pressured receptions in both.

Run: python src/engine_v2/task44_gate.py
"""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import roc_auc_score

from value_models import PATTERN_CODE
from crossfit import FOLDS_PATH, N_FOLDS
from task42_step2 import CLF_KWARGS

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
EVENTS_DIR = DATA_DIR / "raw" / "events"
EV_DIR = DATA_DIR / "processed" / "engine_v2" / "options_ev_v4"
T43_SPELLS = DATA_DIR / "processed" / "engine_v2" / "task43_spells.parquet"
T43_PRESSURED = DATA_DIR / "processed" / "engine_v2" / "task43_pressured_spells.parquet"
SUMMARY_PATH = DATA_DIR / "engine_v2_task44_step2.json"
FLAG_FEATURES = ["recv_x", "recv_y", "play_pattern_code", "period", "minute"]
SPELL_FIRST = {"Pass", "Carry", "Dribble", "Shot", "Miscontrol", "Dispossessed"}
GATE_R = 0.70
MIN_BOTH = 50


def receipt_flags(mid: int, events_dir: Path = EVENTS_DIR) -> pd.DataFrame:
    ev = pd.read_parquet(events_dir / f"{mid}.parquet",
                         columns=["id", "index", "type", "player_id", "possession", "location", "under_pressure",
                                  "play_pattern", "period", "minute", "ball_receipt_outcome", "team"])
    ev = ev.sort_values("index").reset_index(drop=True)
    typ, pl, poss = ev["type"].values, ev["player_id"].values, ev["possession"].values
    up = ev["under_pressure"].fillna(False).astype(bool).values
    rows = []
    for i in np.flatnonzero((typ == "Ball Receipt*") & ev["ball_receipt_outcome"].isna().values):
        first_up = False
        for k in range(i + 1, len(ev)):
            if poss[k] != poss[i]:
                break
            if pl[k] == pl[i] and typ[k] in SPELL_FIRST:
                first_up = bool(up[k])
                break
        loc = ev.at[i, "location"]
        rows.append({"match_id": mid, "event_id": ev.at[i, "id"], "player_id": pl[i], "team": ev.at[i, "team"],
                     "recv_x": float(loc[0]) if loc is not None else np.nan, "recv_y": float(loc[1]) if loc is not None else np.nan,
                     "play_pattern_code": PATTERN_CODE.get(ev.at[i, "play_pattern"], PATTERN_CODE["Other"]),
                     "period": int(ev.at[i, "period"]), "minute": int(ev.at[i, "minute"]),
                     "up_receipt": bool(up[i]), "up_first": first_up, "pressured_flag": bool(up[i] or first_up)})
    return pd.DataFrame(rows)


def fit_baseline(df: pd.DataFrame, fold_of: dict) -> dict:
    fold = df["match_id"].map(fold_of).values
    out = {}
    for oc, name in (("keep_spell", "pr2_flag_keep"), ("fwd_spell", "pr2_flag_fwd")):
        oof = np.full(len(df), np.nan)
        for k in range(N_FOLDS):
            tr, te = fold != k, fold == k
            m = xgb.XGBClassifier(**CLF_KWARGS).fit(df.loc[tr, FLAG_FEATURES].astype(float), df.loc[tr, oc].astype(int))
            oof[te] = m.predict_proba(df.loc[te, FLAG_FEATURES].astype(float))[:, 1]
        df[name] = df[oc] - oof
        out[name] = {"base_rate": float(df[oc].mean()), "auc": float(roc_auc_score(df[oc].astype(int), oof))}
    return out


def main():
    print("Task 44 Step 2: event-only press resistance gate (study sample) ...")
    folds = pd.read_csv(FOLDS_PATH)
    ev_mids = {int(p.stem) for p in EV_DIR.glob("*.parquet")}
    folds = folds[folds["match_id"].isin(ev_mids)]
    fold_of = dict(zip(folds["match_id"], folds["fold"]))
    mids = sorted(fold_of)
    rec = pd.concat([receipt_flags(m) for m in mids], ignore_index=True)
    sp = pd.read_parquet(T43_SPELLS, columns=["match_id", "event_id", "keep_spell", "fwd_spell"])
    rec = rec.merge(sp, on=["match_id", "event_id"], how="left")
    n_all = len(rec)
    pr = rec[rec["pressured_flag"] & rec["keep_spell"].notna()].reset_index(drop=True)
    counts = {"n_receipts": n_all, "n_pressured_flag": int(rec["pressured_flag"].sum()),
              "n_flag_on_receipt": int(rec["up_receipt"].sum()), "n_flag_on_first_event_only": int((~rec["up_receipt"] & rec["up_first"]).sum()),
              "n_units_with_spell_outcome": len(pr)}
    base = fit_baseline(pr, fold_of)
    print(f"  {counts}; {base}")

    t43 = pd.read_parquet(T43_PRESSURED, columns=["player_id", "pr2_keep"]).groupby("player_id")["pr2_keep"].agg(["mean", "size"])
    t44 = pr.groupby("player_id")["pr2_flag_keep"].agg(["mean", "size"])
    j = t43[t43["size"] >= MIN_BOTH].join(t44[t44["size"] >= MIN_BOTH], lsuffix="_43", rsuffix="_flag", how="inner")
    n = len(j)
    r = float(j["mean_43"].corr(j["mean_flag"]))
    ci = [float(np.tanh(np.arctanh(r) - 1.96 / np.sqrt(n - 3))), float(np.tanh(np.arctanh(r) + 1.96 / np.sqrt(n - 3)))]
    gate = r >= GATE_R
    shared = pr.merge(pd.read_parquet(T43_PRESSURED, columns=["match_id", "event_id"]), on=["match_id", "event_id"], how="inner")
    print(f"  players in both: {n}; r = {r:.4f} {ci}; GATE {'PASS' if gate else 'FAIL'}; "
          f"flag units also in Task 43's pressured set: {len(shared)}")
    SUMMARY_PATH.write_text(json.dumps({"counts": counts, "baseline": base, "n_players_both": n, "r": r, "ci95": ci,
                                        "gate_pass": bool(gate), "n_units_overlap_task43": len(shared),
                                        "n_task43_units": int(t43["size"].sum())}, indent=2))
    print(f"Wrote {SUMMARY_PATH}")


if __name__ == "__main__":
    main()
