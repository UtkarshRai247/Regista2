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
    """{(team, period): +1} for every (team, period) actually present in
    `events`. FIXED in Task 24: this function used to infer +1/-1 per
    period by sorting the two teams' mean shot x and assigning -1 to
    the lower one, on the assumption that StatsBomb event/360
    coordinates are PITCH-FIXED (teams attacking opposite ends). Direct
    coordinate evidence (reproduced corpus-wide in
    `task24_evidence.py`: 99.84% of team-periods have mean shot x > 60,
    the opponent goalkeeper in shot freeze frames sits at median
    x=117.5, 99.93% beyond x=100) shows the opposite: StatsBomb
    coordinates are already TEAM-RELATIVE -- every team attacks toward
    x=120 in its own events. Under that convention there is nothing to
    infer: every (team, period) attacks toward increasing x already, so
    this function now returns +1 for all of them. The old sort-by-mean-
    shot-x logic was really just noise (it split 646/646, a coin flip)
    that rotated roughly half of all events 180 degrees for their own
    team-period. Kept as a dict keyed by (team, period), not a bare
    constant, so every existing call site (`directions.get((team,
    period), 1)`) needs no change."""
    teams = [t for t in events["team"].dropna().unique().tolist()]
    periods = sorted(events["period"].dropna().unique().tolist())
    return {(t, p): 1 for t in teams for p in periods}


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
