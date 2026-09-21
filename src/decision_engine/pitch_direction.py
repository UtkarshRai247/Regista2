"""
Shared helper: normalizes StatsBomb's absolute pitch coordinates (0-120 x
0-80, fixed regardless of which end a team attacks) into attack-relative
coordinates, so "high attack_x" consistently means "close to the
opponent's goal" for whichever team currently possesses.

Without this, a possession-value model trained on raw x/y can't learn a
consistent notion of danger, since teams switch ends between periods.

Direction is inferred per (team, period) from where that team's shots
concentrate; if a team has no shots in a period, inferred from the
opponent's shots (they attack opposite ends), falling back to the
period-1-to-period-2 switch rule when neither team has any shots at all
in a given period (rare, but recorded when it happens).
"""
import warnings

import pandas as pd

warnings.filterwarnings("ignore")

PITCH_X, PITCH_Y = 120.0, 80.0


def team_period_directions(events: pd.DataFrame) -> tuple[dict, int, int]:
    """Returns {(team, period): +1 or -1} where +1 means this team
    attacks toward increasing x in this period, the count of periods
    that needed the no-shots-in-period fallback, and the total number
    of periods in the match."""
    teams = [t for t in events["team"].dropna().unique().tolist()]
    periods = sorted(events["period"].dropna().unique().tolist())
    shots = events[events["type"] == "Shot"]

    directions = {}
    fallback_used = 0
    period1_dir = None

    for period in periods:
        pshots = shots[shots["period"] == period]
        means = {}
        for t in teams:
            tshots = pshots[pshots["team"] == t]
            locs = [loc[0] for loc in tshots["location"] if loc is not None
                    and not (isinstance(loc, float) and pd.isna(loc))]
            if locs:
                means[t] = sum(locs) / len(locs)

        if len(means) >= 2:
            ordered = sorted(means, key=means.get)
            directions[(ordered[0], period)] = -1
            directions[(ordered[1], period)] = 1
        elif len(means) == 1:
            known_team = next(iter(means))
            other = [t for t in teams if t != known_team]
            directions[(known_team, period)] = 1 if means[known_team] > PITCH_X / 2 else -1
            if other:
                directions[(other[0], period)] = -directions[(known_team, period)]
        else:
            fallback_used += 1
            if period1_dir is not None and len(teams) == 2:
                # alternate from period 1 per the standard "switch ends" rule
                flip = -1 if period % 2 == 0 else 1
                directions[(teams[0], period)] = period1_dir[teams[0]] * flip
                directions[(teams[1], period)] = period1_dir[teams[1]] * flip
            else:
                directions[(teams[0], period)] = 1
                if len(teams) > 1:
                    directions[(teams[1], period)] = -1

        if period == 1:
            period1_dir = {t: directions.get((t, 1), 1) for t in teams}

    return directions, fallback_used, len(periods)


def normalize_xy(x: float, y: float, direction: int) -> tuple[float, float]:
    """direction=+1: already attacking toward increasing x, no change.
    direction=-1: rotate 180 degrees so 'attack_x' is consistently
    toward the opponent's goal regardless of actual attacking end."""
    if direction == 1:
        return x, y
    return PITCH_X - x, PITCH_Y - y
