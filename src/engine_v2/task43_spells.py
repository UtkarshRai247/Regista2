"""
Task 43, Steps 1-2: press resistance v2 (a disclosed second attempt after
Task 42). docs/specs/task-43-press-resistance-v2.md.

The receiver's SPELL, for every completed Ball Receipt* by P (team T,
possession p), scanning later events in match index order, ends at the
first of:
  - the possession id changing (possession ended)          -> keep 0
  - P's Pass: keep 1 if completed (no pass_outcome), else 0
  - P's Shot                                                -> EXCLUDED
  - P's Miscontrol, Dispossessed, or Dribble 'Incomplete'   -> keep 0
  - an opponent's Ball Recovery, Interception, Block, Clearance, or Duel
    won (Tackle: Won / Success In Play / Success Out)       -> keep 0
  - an on-ball event (Pass, Carry, Shot, Dribble, Ball Receipt*) by a
    teammate other than P, or P's own Clearance, before any of the above
    -> EXCLUDED as "other" (not in the brief's list; counted)
fwd = keep AND the completed pass's end x - reception x >= 5.
Units for Steps 1-3: Task 42's pressured receptions (task42_step2's
match_receipts and PRESSURED rule). Baseline: Task 42's classifier and
features, refit per outcome. Step 2: Task 38's R1 method.

Run: python src/engine_v2/task43_spells.py
"""
import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import roc_auc_score

sys.path.insert(0, str(Path(__file__).parent.parent / "pff"))
import availability_tests as avt  # noqa: E402
import task35_ptest as tp  # noqa: E402
from crossfit import FOLDS_PATH, N_FOLDS  # noqa: E402
from task42_step2 import match_receipts, CLF_KWARGS, BASE_FEATURES, PRESS_DIST  # noqa: E402

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
EVENTS_DIR = DATA_DIR / "raw" / "events"
LEADERBOARD_V5C_PATH = DATA_DIR / "processed" / "leaderboard_v5c.parquet"
T42_PRESSURED = DATA_DIR / "processed" / "engine_v2" / "task42_pressured_receptions.parquet"
ALL_SPELLS_PATH = DATA_DIR / "processed" / "engine_v2" / "task43_spells.parquet"
PRESSURED_PATH = DATA_DIR / "processed" / "engine_v2" / "task43_pressured_spells.parquet"
SUMMARY_PATH = DATA_DIR / "engine_v2_task43_steps1_2.json"

OPP_LOSS = {"Ball Recovery", "Interception", "Block", "Clearance"}
DUEL_WON = {"Won", "Success In Play", "Success Out"}
MATE_ON_BALL = {"Pass", "Carry", "Shot", "Dribble", "Ball Receipt*"}
FWD_MIN = 5.0
R1_MIN_MATCHES, R1_MIN_RECEPTIONS = 4, 40
CORR_MIN = 50


def _x(loc):
    return float(loc[0]) if loc is not None and not (isinstance(loc, float) and np.isnan(loc)) else np.nan


def match_spells(mid: int) -> pd.DataFrame:
    ev = pd.read_parquet(EVENTS_DIR / f"{mid}.parquet",
                         columns=["id", "index", "type", "team", "player_id", "possession", "location", "pass_outcome",
                                  "pass_end_location", "dribble_outcome", "duel_type", "duel_outcome", "ball_receipt_outcome"])
    ev = ev.sort_values("index").reset_index(drop=True)
    n = len(ev)
    typ, team, pl, poss = ev["type"].values, ev["team"].values, ev["player_id"].values, ev["possession"].values
    rows = []
    for i in np.flatnonzero((typ == "Ball Receipt*") & ev["ball_receipt_outcome"].isna().values):
        P, T, p, x0 = pl[i], team[i], poss[i], _x(ev.at[i, "location"])
        keep, fwd, reason = np.nan, np.nan, "no_end_found"
        for k in range(i + 1, n):
            if poss[k] != p:
                keep, fwd, reason = 0, 0, "possession_ended"
                break
            if pl[k] == P:
                if typ[k] == "Pass":
                    ok = pd.isna(ev.at[k, "pass_outcome"])
                    keep = int(ok)
                    fwd = int(ok and _x(ev.at[k, "pass_end_location"]) - x0 >= FWD_MIN)
                    reason = "pass_complete" if ok else "pass_incomplete"
                    break
                if typ[k] == "Shot":
                    reason = "shot_excluded"
                    break
                if typ[k] in ("Miscontrol", "Dispossessed") or (typ[k] == "Dribble" and ev.at[k, "dribble_outcome"] == "Incomplete"):
                    keep, fwd, reason = 0, 0, f"own_{typ[k].lower()}"
                    break
                if typ[k] == "Clearance":
                    reason = "other_excluded"
                    break
                continue
            if team[k] != T:
                if typ[k] in OPP_LOSS or (typ[k] == "Duel" and ev.at[k, "duel_type"] == "Tackle" and ev.at[k, "duel_outcome"] in DUEL_WON):
                    keep, fwd, reason = 0, 0, f"opp_{typ[k].lower().replace(' ', '_')}"
                    break
                continue
            if typ[k] in MATE_ON_BALL:
                reason = "other_excluded"
                break
        rows.append({"match_id": mid, "event_id": ev.at[i, "id"], "player_id": P, "keep_spell": keep, "fwd_spell": fwd,
                     "end_reason": reason})
    return pd.DataFrame(rows)


def r1_matches(df: pd.DataFrame, col: str, pids: set) -> dict:
    d = df[df["player_id"].isin(pids)].rename(columns={"player_id": "pff_player_id", "match_id": "pff_game_id"})
    return avt.r1(d, col)


def main():
    print("Task 43 Steps 1-2 ...")
    folds = pd.read_csv(FOLDS_PATH)
    ev_mids = {int(p.stem) for p in tp.EV_DIR.glob("*.parquet")}
    folds = folds[folds["match_id"].isin(ev_mids)]
    fold_of = dict(zip(folds["match_id"], folds["fold"]))
    mids = sorted(fold_of)

    spells = pd.concat([match_spells(m) for m in mids], ignore_index=True)
    spells.to_parquet(ALL_SPELLS_PATH)
    reasons_all = spells["end_reason"].value_counts().to_dict()

    rec = pd.concat([match_receipts(m) for m in mids], ignore_index=True)
    rec["pressured"] = (rec["nearest_opp"] <= PRESS_DIST) | rec["under_pressure_flag"]
    pr = rec[rec["pressured"]].merge(spells.drop(columns=["player_id"]), on=["match_id", "event_id"], how="left")
    n_pressured = len(pr)
    reasons = pr["end_reason"].value_counts().to_dict()
    pr = pr[pr["keep_spell"].notna()].reset_index(drop=True)
    pr["fold"] = pr["match_id"].map(fold_of)
    print(f"  all receipts: {len(spells)}; pressured: {n_pressured}; spells with outcome: {len(pr)}; reasons: {reasons}")

    base = {}
    for oc in ("keep_spell", "fwd_spell"):
        oof = np.full(len(pr), np.nan)
        for k in range(N_FOLDS):
            tr, te = (pr["fold"] != k).values, (pr["fold"] == k).values
            m = xgb.XGBClassifier(**CLF_KWARGS).fit(pr.loc[tr, BASE_FEATURES].astype(float), pr.loc[tr, oc].astype(int))
            oof[te] = m.predict_proba(pr.loc[te, BASE_FEATURES].astype(float))[:, 1]
        name = "pr2_keep" if oc == "keep_spell" else "pr2_fwd"
        pr[name] = pr[oc] - oof
        base[name] = {"base_rate": float(pr[oc].mean()), "auc": float(roc_auc_score(pr[oc].astype(int), oof))}
    pr.to_parquet(PRESSURED_PATH)
    print(f"  baseline: {base}")

    t42 = pd.read_parquet(T42_PRESSURED, columns=["player_id", "pr_keep"]).groupby("player_id")["pr_keep"].agg(["mean", "size"])
    t43 = pr.groupby("player_id")["pr2_keep"].agg(["mean", "size"])
    j = t42[t42["size"] >= CORR_MIN].join(t43[t43["size"] >= CORR_MIN], lsuffix="_42", rsuffix="_43", how="inner")
    corr = {"n_players": len(j), "r": float(j["mean_42"].corr(j["mean_43"]))}
    print(f"  corr(player PR2_keep, Task 42 PR_keep): {corr}")

    lb = pd.read_parquet(LEADERBOARD_V5C_PATH, columns=["player_id", "is_deep_midfield"])
    dm_ids = set(lb.loc[lb["is_deep_midfield"], "player_id"])
    per = pr.groupby("player_id").agg(n_rec=("pr2_keep", "size"), n_matches=("match_id", "nunique"))
    elig = set(per[(per["n_rec"] >= R1_MIN_RECEPTIONS) & (per["n_matches"] >= R1_MIN_MATCHES)].index)
    r1 = {}
    for col in ("pr2_keep", "pr2_fwd"):
        r1[col] = {"DM": r1_matches(pr, col, elig & dm_ids), "all": r1_matches(pr, col, elig)}
        r1[col]["pass_DM"] = bool(r1[col]["DM"]["median"] >= 0.60)
        print(f"  R1 {col}: {r1[col]}")

    SUMMARY_PATH.write_text(json.dumps({
        "n_receipts_all": len(spells), "end_reasons_all": reasons_all, "n_pressured": n_pressured,
        "end_reasons_pressured": reasons, "n_spells_with_outcome": len(pr), "baseline": base,
        "corr_with_task42": corr, "r1": r1, "n_eligible_r1": len(elig), "n_eligible_r1_dm": len(elig & dm_ids)},
        indent=2, default=str))
    print(f"Wrote {SUMMARY_PATH}")


if __name__ == "__main__":
    main()
