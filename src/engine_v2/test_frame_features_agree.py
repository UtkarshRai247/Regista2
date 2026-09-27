"""
Task 21, Step 1 (hard rule): `features.state_features_batch` and
`value_models.frame_ahead_features` were independently written and
must produce IDENTICAL values for the same frame -- this is exactly
the class of silent divergence that hid Task 19d's bug (an identical
`opp_nx_sorted[1]` error existed in both, undetected, because nothing
compared their outputs). This test asserts agreement on every field
both functions compute (not just Task 21's three new ones), against
one hand-built frame -- a plain assert-based script, no framework, per
this repo's own convention (no pytest anywhere in it).

Run: python src/engine_v2/test_frame_features_agree.py
"""
import numpy as np
import pandas as pd

from features import state_features_batch
from value_models import frame_ahead_features

DIRECTION = 1
PASSER_RAW = np.array([50.0, 40.0])
OPPONENTS_RAW = np.array([[60.0, 20.0], [65.0, 35.0], [70.0, 50.0], [90.0, 40.0]])
TEAMMATES_RAW = np.array([[45.0, 40.0], [80.0, 42.0]])
BALL_POSITIONS = [
    np.array([55.0, 40.0]),   # short, behind everything
    np.array([82.0, 41.0]),   # beyond the defensive line, near the teammate at (80,42)
    np.array([100.0, 5.0]),   # beyond the defensive line, far from any teammate
]

SHARED_FIELDS = [
    "opponents_ahead_of_ball", "teammates_ahead_of_ball", "numerical_advantage_ahead",
    "distance_to_nearest_opponent_u", "opponents_within_5u", "opponents_within_10u",
    "defensive_line_x", "ball_beyond_defensive_line", "n_visible_players",
    "distance_to_nearest_teammate_u", "teammates_within_5u", "teammates_within_10u",
]


def build_frame_df() -> pd.DataFrame:
    rows = []
    for loc in OPPONENTS_RAW:
        rows.append({"teammate": False, "actor": False, "location": list(loc)})
    for loc in TEAMMATES_RAW:
        rows.append({"teammate": True, "actor": False, "location": list(loc)})
    rows.append({"teammate": True, "actor": True, "location": list(PASSER_RAW)})  # the passer itself
    return pd.DataFrame(rows)


def values_match(a, b) -> bool:
    if a is None and (b is None or (isinstance(b, float) and np.isnan(b))):
        return True
    if isinstance(a, (bool, np.bool_)) or isinstance(b, (bool, np.bool_)):
        return bool(a) == bool(b)
    fa, fb = float(a), float(b)
    if np.isnan(fa) and np.isnan(fb):
        return True
    return abs(fa - fb) < 1e-9


def main():
    frame = build_frame_df()
    n_visible = len(frame)
    all_ok = True
    for ball_raw_single in BALL_POSITIONS:
        ball_raw = ball_raw_single[None, :]
        batch = state_features_batch(ball_raw, PASSER_RAW, DIRECTION, TEAMMATES_RAW, OPPONENTS_RAW, n_visible)
        single = frame_ahead_features(frame, ball_raw_single, DIRECTION)
        for field in SHARED_FIELDS:
            v_batch = batch[field][0]
            v_single = single[field]
            ok = values_match(v_batch, v_single)
            all_ok = all_ok and ok
            status = "OK" if ok else "MISMATCH"
            print(f"  ball={ball_raw_single.tolist()} {field}: batch={v_batch} single={v_single} [{status}]")
            assert ok, f"state_features_batch and frame_ahead_features disagree on {field} for ball={ball_raw_single.tolist()}: {v_batch} != {v_single}"
    print("test_frame_features_agree.py: ALL PASS" if all_ok else "test_frame_features_agree.py: FAIL")


if __name__ == "__main__":
    main()
