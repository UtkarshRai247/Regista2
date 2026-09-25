"""
Task 15 -- Engine v2, Step 3: committed unit tests for the lane-
congestion calculation (features.lane_congestion), against three
hand-built cases with known right answers. Plain assert-based, no
framework (no pytest anywhere in this repo) -- matches every other
script's own if __name__ == "__main__" convention.

Run: python src/engine_v2/test_lane_congestion.py
"""
import numpy as np

from features import lane_congestion, CORRIDOR_HALFWIDTH_U

PASSER = np.array([0.0, 0.0])
CANDIDATE = np.array([[10.0, 0.0]])  # single candidate, passer->candidate along the x-axis


def case_1_opponent_on_the_line():
    """An opponent sitting exactly on the passing line, halfway along
    it, must be counted (perpendicular distance 0) and be within the
    segment."""
    opponents = np.array([[5.0, 0.0]])
    n_in_corridor, min_perp = lane_congestion(PASSER, CANDIDATE, opponents)
    assert n_in_corridor[0] == 1, f"expected 1 opponent in corridor, got {n_in_corridor[0]}"
    assert abs(min_perp[0] - 0.0) < 1e-9, f"expected min_perp 0.0, got {min_perp[0]}"
    print("case_1_opponent_on_the_line: PASS")


def case_2_opponent_off_the_line_but_within_segment():
    """An opponent 5 yards perpendicular to the line (beyond the
    3-yard corridor half-width) must NOT be counted, even though its
    projection falls within the segment; min_perp reports the true
    distance."""
    opponents = np.array([[5.0, 5.0]])
    n_in_corridor, min_perp = lane_congestion(PASSER, CANDIDATE, opponents)
    assert n_in_corridor[0] == 0, f"expected 0 opponents in corridor, got {n_in_corridor[0]}"
    assert abs(min_perp[0] - 5.0) < 1e-9, f"expected min_perp 5.0, got {min_perp[0]}"
    assert min_perp[0] > CORRIDOR_HALFWIDTH_U
    print("case_2_opponent_off_the_line_but_within_segment: PASS")


def case_3_opponent_projects_outside_the_segment():
    """An opponent close to the candidate but past it along the line's
    direction (projection parameter t > 1) must NOT be counted despite
    being geometrically close -- its projection falls outside the
    passer->candidate segment, not just off to the side."""
    opponents = np.array([[12.0, 1.0]])  # t = 1.2, past the candidate
    n_in_corridor, min_perp = lane_congestion(PASSER, CANDIDATE, opponents)
    expected_min_perp = np.hypot(12.0 - 10.0, 1.0 - 0.0)  # distance to the clamped (candidate) endpoint
    assert n_in_corridor[0] == 0, f"expected 0 opponents in corridor (outside segment), got {n_in_corridor[0]}"
    assert abs(min_perp[0] - expected_min_perp) < 1e-9, f"expected min_perp {expected_min_perp}, got {min_perp[0]}"
    print("case_3_opponent_projects_outside_the_segment: PASS")


def main():
    case_1_opponent_on_the_line()
    case_2_opponent_off_the_line_but_within_segment()
    case_3_opponent_projects_outside_the_segment()
    print("test_lane_congestion.py: ALL PASS")


if __name__ == "__main__":
    main()
