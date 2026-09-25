"""
Task 15 -- Engine v2, shared pure geometry.

Ported verbatim from src/decision_engine/pitch_direction.py
(team_period_directions, normalize_xy, PITCH_X/PITCH_Y) and
src/decision_engine/options.py (point_segment_perp_distance, bearing,
circular_diff, dist) -- named as surviving infra in docs/ENGINE_AUDIT.md
("What survives: ... the direction-normalisation utility itself"), with
no modeling assumption in any of these functions. Ported rather than
cross-imported because src/decision_engine/ scripts are run with their
own directory on sys.path (sibling imports like `from decompose import
...`), so a cross-directory import doesn't resolve cleanly -- the same
independence pattern already used by src/tempo/.

Run standalone for a smoke check: python src/engine_v2/geometry.py
"""
import math
import warnings

import pandas as pd

warnings.filterwarnings("ignore")

PITCH_X, PITCH_Y = 120.0, 80.0
GRID_STEP = 4.0


def team_period_directions(events: pd.DataFrame) -> dict:
    """{(team, period): +1 or -1}, +1 = attacks toward increasing x in
    that period. Inferred per period from where that team's shots
    concentrate; falls back to the opponent's shots, then to the
    period-1-to-period-2 switch rule. Ported unchanged from
    pitch_direction.team_period_directions (drops that function's
    fallback-count/period-count return values, unused here)."""
    teams = [t for t in events["team"].dropna().unique().tolist()]
    periods = sorted(events["period"].dropna().unique().tolist())
    shots = events[events["type"] == "Shot"]
    directions = {}
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
            if period1_dir is not None and len(teams) == 2:
                flip = -1 if period % 2 == 0 else 1
                directions[(teams[0], period)] = period1_dir[teams[0]] * flip
                directions[(teams[1], period)] = period1_dir[teams[1]] * flip
            else:
                directions[(teams[0], period)] = 1
                if len(teams) > 1:
                    directions[(teams[1], period)] = -1
        if period == 1:
            period1_dir = {t: directions.get((t, 1), 1) for t in teams}
    return directions


def normalize_xy(x: float, y: float, direction: int) -> tuple:
    """direction=+1: unchanged. direction=-1: rotate 180 degrees so
    'attack_x' is consistently toward the opponent's goal."""
    if direction == 1:
        return x, y
    return PITCH_X - x, PITCH_Y - y


def bearing(a, b) -> float:
    dx, dy = b[0] - a[0], b[1] - a[1]
    return math.degrees(math.atan2(dy, dx)) % 360.0


def circular_diff(a: float, b: float) -> float:
    d = abs(a - b) % 360.0
    return min(d, 360.0 - d)


def dist(a, b) -> float:
    return math.hypot(b[0] - a[0], b[1] - a[1])


def point_segment_perp_distance(p, a, b) -> tuple:
    """Perpendicular distance from p to segment a-b, and whether the
    projection of p falls within the segment (not past either end)."""
    ax, ay = a
    bx, by = b
    px, py = p
    abx, aby = bx - ax, by - ay
    seg_len2 = abx ** 2 + aby ** 2
    if seg_len2 == 0:
        return dist(p, a), True
    t = ((px - ax) * abx + (py - ay) * aby) / seg_len2
    within = 0.0 <= t <= 1.0
    t_clamped = max(0.0, min(1.0, t))
    proj = (ax + t_clamped * abx, ay + t_clamped * aby)
    return dist(p, proj), within


if __name__ == "__main__":
    assert normalize_xy(10, 20, 1) == (10, 20)
    assert normalize_xy(10, 20, -1) == (110, 60)
    assert abs(bearing((0, 0), (1, 0))) < 1e-9
    assert circular_diff(350, 10) == 20
    perp, within = point_segment_perp_distance((5, 1), (0, 0), (10, 0))
    assert abs(perp - 1.0) < 1e-9 and within
    perp2, within2 = point_segment_perp_distance((15, 1), (0, 0), (10, 0))
    assert not within2
    print("geometry.py self-check: PASS")
