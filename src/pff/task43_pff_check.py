"""
Task 43, Step 5: a second data source for press resistance (report only).
docs/specs/task-43-press-resistance-v2.md.

Units: Task 38's PFF receptions (completed PA/CR to a receiver) where the
receiver's next PFF event carries pressure (pressureType, or the initial
touch's initialPressureType, not 'N' -- Task 38's rec_pressure == 1).
keep_pff: the receiver's spell over PFF possession events after the pass:
his PA/CR ends it (1 if passOutcomeType 'C', else 0); his SH -> excluded;
an opposing team's possession event first -> 0; a teammate's possession
event first -> excluded; no end within 30 possession events -> excluded.
Baseline of the same form as Task 42/43 (XGBoost classifier, same
settings) on PFF context: reception x, y (Task 38), nearest-opponent
distance and opponents within 5 m (receiver's next-event snapshot),
setpieceType code, period, minute; Task 38's match folds.
Convergence: Pearson r (Fisher 95% CI) between player mean PFF score and
player mean StatsBomb PR2_keep over WC2022 matches only, players with
>= 30 pressured receptions in both.

Run: python src/pff/task43_pff_check.py   (after src/engine_v2/task43_spells.py)
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import roc_auc_score

sys.path.insert(0, str(Path(__file__).parent.parent / "engine_v2"))
import availability as av  # noqa: E402
import availability_tests as avt  # noqa: E402
from task42_step2 import CLF_KWARGS  # noqa: E402

DATA_DIR = Path(__file__).parent.parent.parent / "data"
SB_SPELLS = DATA_DIR / "processed" / "engine_v2" / "task43_pressured_spells.parquet"
SUMMARY_PATH = DATA_DIR / "pff_task43_step5.json"
MIN_BOTH = 30
FEATURES = ["rec_x", "rec_y", "nearest_opp", "opp_within_5", "setpiece_code", "period", "minute"]


def spell_and_context(rec: pd.DataFrame) -> pd.DataFrame:
    out = []
    for gid, g in rec.groupby("pff_game_id"):
        events = json.loads((av.EVENTS_DIR / f"{gid}.json").read_text())
        poss = [k for k, e in enumerate(events) if (e.get("possessionEvents") or {}).get("possessionEventType")]
        for r in g.itertuples():
            i, pid, team = int(r.event_idx), int(r.pff_player_id), int(r.team_id)
            keep, reason = np.nan, "no_end"
            for k in [k for k in poss if k > i][:30]:
                pe, ge = events[k]["possessionEvents"], events[k].get("gameEvents") or {}
                if ge.get("teamId") != team:
                    keep, reason = 0, "opponent"
                    break
                if ge.get("playerId") == pid:
                    t = pe.get("possessionEventType")
                    if t in ("PA", "CR"):
                        keep, reason = int(pe.get("passOutcomeType") == "C"), "pass"
                        break
                    if t == "SH":
                        reason = "shot_excluded"
                        break
                    continue
                reason = "teammate_excluded"
                break
            nxt = next((k for k in range(i + 1, min(i + 4, len(events)))
                        if (events[k].get("gameEvents") or {}).get("playerId") == pid), None)
            near, within5 = np.nan, np.nan
            if nxt is not None:
                e = events[nxt]
                mates, opps = (e["homePlayers"], e["awayPlayers"]) if r.side == "home" else (e["awayPlayers"], e["homePlayers"])
                me = next((m for m in mates if m.get("playerId") == pid and m.get("x") is not None), None)
                if me is not None:
                    d = np.array([np.hypot(o["x"] - me["x"], o["y"] - me["y"]) for o in opps if o.get("x") is not None])
                    if len(d):
                        near, within5 = float(d.min()), int((d <= 5).sum())
            sp = (events[i].get("gameEvents") or {}).get("setpieceType")
            out.append({"idx": r.Index, "keep_pff": keep, "end_reason": reason, "nearest_opp": near,
                        "opp_within_5": within5, "setpiece": sp})
    o = pd.DataFrame(out).set_index("idx")
    return rec.join(o)


def main():
    print("Task 43 Step 5: PFF convergent check ...")
    rec = pd.read_parquet(av.RECEPTIONS_PATH)
    rec = rec[rec["rec_pressure"] == 1].copy()
    n_pressured = len(rec)
    rec = spell_and_context(rec)
    reasons = rec["end_reason"].value_counts().to_dict()
    codes = {s: i for i, s in enumerate(sorted(rec["setpiece"].dropna().unique()))}
    rec["setpiece_code"] = rec["setpiece"].map(codes)
    u = rec[rec["keep_pff"].notna()].reset_index(drop=True)
    oof = np.full(len(u), np.nan)
    for k in range(av.N_FOLDS):
        tr, te = (u["fold"] != k).values, (u["fold"] == k).values
        m = xgb.XGBClassifier(**CLF_KWARGS).fit(u.loc[tr, FEATURES].astype(float), u.loc[tr, "keep_pff"].astype(int))
        oof[te] = m.predict_proba(u.loc[te, FEATURES].astype(float))[:, 1]
    u["pr_pff"] = u["keep_pff"] - oof
    auc = float(roc_auc_score(u["keep_pff"].astype(int), oof))
    print(f"  pressured PFF receptions {n_pressured}; ends {reasons}; units {len(u)}; base {u['keep_pff'].mean():.3f}; AUC {auc:.3f}")

    pm = avt.player_map()
    pff2sb = pm.drop_duplicates("pff_player_id").set_index("pff_player_id")["sb_player_id"]
    a = u.groupby("pff_player_id")["pr_pff"].agg(["mean", "size"])
    a = a[a["size"] >= MIN_BOTH]
    a.index = a.index.map(pff2sb)
    wc = set(pd.read_csv(av.OUT_DIR / "crosswalk.csv")["statsbomb_match_id"])
    sb = pd.read_parquet(SB_SPELLS, columns=["match_id", "player_id", "pr2_keep"])
    b = sb[sb["match_id"].isin(wc)].groupby("player_id")["pr2_keep"].agg(["mean", "size"])
    b = b[b["size"] >= MIN_BOTH]
    j = a.join(b, lsuffix="_pff", rsuffix="_sb", how="inner")
    n = len(j)
    r = float(j["mean_pff"].corr(j["mean_sb"])) if n >= 3 else None
    ci = [float(np.tanh(np.arctanh(r) - 1.96 / np.sqrt(n - 3))), float(np.tanh(np.arctanh(r) + 1.96 / np.sqrt(n - 3)))] if n >= 4 else [None, None]
    print(f"  players with >= {MIN_BOTH} in both: {n}; r = {r}; 95% CI {ci}")
    SUMMARY_PATH.write_text(json.dumps({"n_pressured_pff": n_pressured, "end_reasons": reasons, "n_units": len(u),
                                        "base_rate": float(u["keep_pff"].mean()), "auc": auc, "setpiece_codes": codes,
                                        "n_players_pff_ge30": int(len(a)), "n_players_sb_wc_ge30": int(len(b)),
                                        "n_players_both": n, "r": r, "ci95": ci}, indent=2, default=str))
    print(f"Wrote {SUMMARY_PATH}")


if __name__ == "__main__":
    main()
