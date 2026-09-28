"""
Task 42: role-appropriate outcomes and next-action retention from
StatsBomb events (study sample). docs/specs/task-42-improvement-round-2.md.

Per event (from the event's own team perspective, StatsBomb `possession`):
  y_f3   = 1 if the team has an on-ball event (Pass, Carry, Ball Receipt*,
           Dribble, Shot) at x >= 80 LATER in the same possession.
  y_shot = 1 if the same possession contains a LATER Shot by the team.
Coordinates are StatsBomb team-relative (the acting team attacks toward
x = 120), i.e. already normalised.

Per completed Ball Receipt* (receiver P), the receiver's next action:
scan later events in the same possession; if P's Miscontrol or
Dispossessed comes first -> keep = 0; else the first P event in {Pass,
Carry, Dribble, Shot} is the action; if none -> no action (excluded).
  keep = action not failed (Pass with a pass_outcome, Dribble 'Incomplete',
         any Shot) AND the event right after the action (match index
         order) is in the same possession and is not P's Miscontrol /
         Dispossessed.
  fwd  = keep AND action end x - reception x >= 5 (Pass end, Carry end,
         Dribble location).
"""
from pathlib import Path

import numpy as np
import pandas as pd

EVENTS_DIR = Path(__file__).parent.parent.parent / "data" / "raw" / "events"
ON_BALL = {"Pass", "Carry", "Ball Receipt*", "Dribble", "Shot"}
ACTIONS = {"Pass", "Carry", "Dribble", "Shot"}
LOSSES = {"Miscontrol", "Dispossessed"}
F3_X = 80.0
FWD_MIN = 5.0


def _x(loc):
    return float(loc[0]) if loc is not None and not (isinstance(loc, float) and np.isnan(loc)) else np.nan


def match_outcomes(mid: int) -> tuple:
    ev = pd.read_parquet(EVENTS_DIR / f"{mid}.parquet",
                         columns=["id", "index", "type", "team", "player_id", "possession", "location",
                                  "pass_outcome", "pass_end_location", "carry_end_location", "dribble_outcome",
                                  "ball_receipt_outcome"])
    ev = ev.sort_values("index").reset_index(drop=True)
    n = len(ev)
    typ, team, pl, poss = ev["type"].values, ev["team"].values, ev["player_id"].values, ev["possession"].values
    x = np.array([_x(l) for l in ev["location"]])

    y_f3, y_shot = np.zeros(n, dtype=int), np.zeros(n, dtype=int)
    for p, idx in pd.Series(np.arange(n)).groupby(poss):
        seen_f3, seen_shot = set(), set()
        for i in idx.values[::-1]:
            y_f3[i] = int(team[i] in seen_f3)
            y_shot[i] = int(team[i] in seen_shot)
            if typ[i] in ON_BALL and x[i] >= F3_X:
                seen_f3.add(team[i])
            if typ[i] == "Shot":
                seen_shot.add(team[i])
    per_event = pd.DataFrame({"match_id": mid, "event_id": ev["id"], "y_f3": y_f3, "y_shot": y_shot, "x": x})

    rows = []
    rec_idx = np.flatnonzero((typ == "Ball Receipt*") & ev["ball_receipt_outcome"].isna().values)
    for i in rec_idx:
        keep = fwd = np.nan
        action = None
        for k in range(i + 1, n):
            if poss[k] != poss[i]:
                break
            if pl[k] == pl[i] and typ[k] in LOSSES:
                keep, fwd, action = 0, 0, typ[k]
                break
            if pl[k] == pl[i] and typ[k] in ACTIONS:
                action = typ[k]
                failed = (typ[k] == "Pass" and pd.notna(ev.at[k, "pass_outcome"])) or \
                         (typ[k] == "Dribble" and ev.at[k, "dribble_outcome"] == "Incomplete") or typ[k] == "Shot"
                nxt_ok = k + 1 < n and poss[k + 1] == poss[i] and not (pl[k + 1] == pl[i] and typ[k + 1] in LOSSES)
                keep = int((not failed) and nxt_ok)
                if typ[k] == "Pass":
                    end_x = _x(ev.at[k, "pass_end_location"])
                elif typ[k] == "Carry":
                    end_x = _x(ev.at[k, "carry_end_location"])
                elif typ[k] == "Dribble":
                    end_x = x[k]
                else:
                    end_x = np.nan
                fwd = int(keep == 1 and end_x - x[i] >= FWD_MIN)
                break
        rows.append({"match_id": mid, "event_id": ev.at[i, "id"], "action": action, "keep": keep, "fwd": fwd})
    return per_event, pd.DataFrame(rows)


if __name__ == "__main__":
    pe, rc = match_outcomes(3764440)
    print(pe[["y_f3", "y_shot"]].mean().to_dict(), len(rc), rc["action"].value_counts(dropna=False).to_dict(),
          rc[["keep", "fwd"]].mean().to_dict())
