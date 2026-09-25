"""
Task 15 -- Engine v2, Step 3: the shared candidate feature set
(docs/specs/engine-v2-rebuild.md section 2). Pure, vectorized (numpy),
no file I/O -- called per-pass from grid.py's per-match loop (Steps 2
and 3 are fused into one per-match pass over the ~100-150M-row candidate
corpus to avoid processing it twice; this module holds the testable
feature logic, grid.py holds the orchestration/IO).

All geometry in direction-normalized coordinates where stated; distances
in raw StatsBomb units (yards, confirmed via task04_situation_context's
penalty-spot check), named `_u`.

Lane congestion corridor half-width: 3 yards (replaces v1's
LANE_WIDTH_M=1.0-applied-to-yards unit-confusion defect, Defect 5b).
"""
import warnings

import numpy as np

from geometry import PITCH_X, PITCH_Y

warnings.filterwarnings("ignore")

CORRIDOR_HALFWIDTH_U = 3.0


def normalize_xy_arr(xy: np.ndarray, direction: int) -> np.ndarray:
    """Vectorized normalize_xy over an (N,2) array."""
    if direction == 1:
        return xy.copy()
    out = xy.copy()
    out[:, 0] = PITCH_X - xy[:, 0]
    out[:, 1] = PITCH_Y - xy[:, 1]
    return out


def lane_congestion(passer_raw: np.ndarray, candidates_raw: np.ndarray,
                     opponents_raw: np.ndarray) -> tuple:
    """For each of K candidates, against N opponents: count of opponents
    within CORRIDOR_HALFWIDTH_U of the passer->candidate segment (and
    whose projection falls within the segment), and the minimum
    perpendicular distance to that segment among all opponents
    (regardless of in-segment). Fully vectorized over (K, N).
    Returns (n_opponents_in_corridor (K,), min_perp_distance_to_lane (K,))."""
    K = len(candidates_raw)
    N = len(opponents_raw)
    if N == 0:
        return np.zeros(K, dtype=int), np.full(K, np.nan)

    A = passer_raw  # (2,)
    AB = candidates_raw - A  # (K,2)
    AP = opponents_raw - A  # (N,2)
    seg_len2 = (AB ** 2).sum(axis=1)  # (K,)
    seg_len2_safe = np.where(seg_len2 == 0, 1.0, seg_len2)

    numerator = AB @ AP.T  # (K,N)
    t = numerator / seg_len2_safe[:, None]  # (K,N)
    within = (t >= 0.0) & (t <= 1.0)
    t_clamped = np.clip(t, 0.0, 1.0)

    proj_x = A[0] + t_clamped * AB[:, 0][:, None]  # (K,N)
    proj_y = A[1] + t_clamped * AB[:, 1][:, None]  # (K,N)
    perp = np.hypot(opponents_raw[:, 0][None, :] - proj_x, opponents_raw[:, 1][None, :] - proj_y)  # (K,N)

    # degenerate zero-length segment (candidate == passer): perp distance is just point-to-A distance
    degenerate = seg_len2 == 0
    if degenerate.any():
        d = np.hypot(opponents_raw[:, 0][None, :] - A[0], opponents_raw[:, 1][None, :] - A[1])
        perp[degenerate, :] = d
        within[degenerate, :] = True

    n_in_corridor = ((perp <= CORRIDOR_HALFWIDTH_U) & within).sum(axis=1)
    min_perp = perp.min(axis=1)
    return n_in_corridor, min_perp


def state_features_batch(ball_raw: np.ndarray, passer_raw: np.ndarray, direction: int,
                          teammate_src_raw: np.ndarray, opponent_src_raw: np.ndarray, n_visible: int) -> dict:
    """Vectorized value-model state features (engine-v2-rebuild.md
    section 3's freeze-frame additions + retained game-state fields
    ball_x/y, prev_x/y, minus time_remaining_period/score_diff/
    play_pattern_code which the caller adds, since those are per-pass
    scalars not per-candidate) for K candidate ball locations against
    one frame of reference. `teammate_src_raw`/`opponent_src_raw` are
    whichever raw freeze-frame arrays play those roles in this frame of
    reference -- swap them (and pass `direction=opp_direction`) to build
    the TURNOVER branch's state, where the original opponents are now
    "their" teammates. ball_raw: (K,2). passer_raw: (2,)."""
    K = len(ball_raw)
    ball_n = normalize_xy_arr(ball_raw, direction)
    passer_n = normalize_xy_arr(passer_raw[None, :], direction)[0]

    N = len(opponent_src_raw)
    if N > 0:
        d_opp = np.hypot(ball_raw[:, 0][:, None] - opponent_src_raw[:, 0][None, :],
                          ball_raw[:, 1][:, None] - opponent_src_raw[:, 1][None, :])
        distance_to_nearest_opponent_u = d_opp.min(axis=1)
        opponents_within_5u = (d_opp <= 5.0).sum(axis=1)
        opponents_within_10u = (d_opp <= 10.0).sum(axis=1)
        opp_n = normalize_xy_arr(opponent_src_raw, direction)
        opponents_ahead_of_ball = (opp_n[:, 0][None, :] > ball_n[:, 0][:, None]).sum(axis=1)
        opp_nx_sorted = np.sort(opp_n[:, 0])
        if N >= 2:
            defensive_line_x = np.full(K, opp_nx_sorted[1])
            ball_beyond_defensive_line = ball_n[:, 0] > opp_nx_sorted[1]
        else:
            defensive_line_x = np.full(K, np.nan)
            ball_beyond_defensive_line = np.zeros(K, dtype=bool)
    else:
        distance_to_nearest_opponent_u = np.full(K, np.nan)
        opponents_within_5u = np.zeros(K, dtype=int)
        opponents_within_10u = np.zeros(K, dtype=int)
        opponents_ahead_of_ball = np.zeros(K, dtype=int)
        defensive_line_x = np.full(K, np.nan)
        ball_beyond_defensive_line = np.zeros(K, dtype=bool)

    M = len(teammate_src_raw)
    if M > 0:
        team_n = normalize_xy_arr(teammate_src_raw, direction)
        teammates_ahead_of_ball = (team_n[:, 0][None, :] > ball_n[:, 0][:, None]).sum(axis=1)
    else:
        teammates_ahead_of_ball = np.zeros(K, dtype=int)

    numerical_advantage_ahead = teammates_ahead_of_ball - opponents_ahead_of_ball

    return {
        "ball_x": ball_n[:, 0], "ball_y": ball_n[:, 1],
        "prev_x": np.full(K, passer_n[0]), "prev_y": np.full(K, passer_n[1]),
        "opponents_ahead_of_ball": opponents_ahead_of_ball, "teammates_ahead_of_ball": teammates_ahead_of_ball,
        "numerical_advantage_ahead": numerical_advantage_ahead,
        "distance_to_nearest_opponent_u": distance_to_nearest_opponent_u,
        "opponents_within_5u": opponents_within_5u, "opponents_within_10u": opponents_within_10u,
        "defensive_line_x": defensive_line_x, "ball_beyond_defensive_line": ball_beyond_defensive_line,
        "n_visible_players": np.full(K, n_visible),
    }


def compute_candidate_features(passer_raw: np.ndarray, candidates_raw: np.ndarray,
                                is_teammate_destination: np.ndarray, direction: int,
                                opponents_raw: np.ndarray, teammates_raw: np.ndarray,
                                n_visible: int) -> dict:
    """passer_raw: (2,). candidates_raw: (K,2). opponents_raw: (N,2),
    teammates_raw (excluding actor): (M,2), both raw StatsBomb coords.
    Returns a dict of (K,)-shaped numpy arrays, one per feature."""
    K = len(candidates_raw)
    N = len(opponents_raw)
    M = len(teammates_raw)

    distance_u = np.hypot(candidates_raw[:, 0] - passer_raw[0], candidates_raw[:, 1] - passer_raw[1])

    cand_n = normalize_xy_arr(candidates_raw, direction)
    passer_n = normalize_xy_arr(passer_raw[None, :], direction)[0]
    forward_progress_u = cand_n[:, 0] - passer_n[0]
    lateral_shift_u = np.abs(cand_n[:, 1] - passer_n[1])
    relative_bearing_deg = np.degrees(np.arctan2(cand_n[:, 1] - passer_n[1], cand_n[:, 0] - passer_n[0]))

    if N > 0:
        d_opp = np.hypot(candidates_raw[:, 0][:, None] - opponents_raw[:, 0][None, :],
                          candidates_raw[:, 1][:, None] - opponents_raw[:, 1][None, :])  # (K,N)
        opponents_within_3u = (d_opp <= 3.0).sum(axis=1)
        opponents_within_5u = (d_opp <= 5.0).sum(axis=1)
        opponents_within_10u = (d_opp <= 10.0).sum(axis=1)
        distance_to_nearest_opponent_u = d_opp.min(axis=1)
        opp_n = normalize_xy_arr(opponents_raw, direction)
        lo = np.minimum(passer_n[0], cand_n[:, 0])[:, None]
        hi = np.maximum(passer_n[0], cand_n[:, 0])[:, None]
        opponents_between_ball_and_destination = ((opp_n[:, 0][None, :] > lo) & (opp_n[:, 0][None, :] < hi)).sum(axis=1)
        opp_nx_sorted = np.sort(opp_n[:, 0])
        if N >= 2:
            second_rearmost_nx = opp_nx_sorted[1]
            offside_destination = (cand_n[:, 0] > second_rearmost_nx) & (cand_n[:, 0] > passer_n[0])
            offside_indeterminate = np.zeros(K, dtype=bool)
        else:
            offside_destination = np.zeros(K, dtype=bool)
            offside_indeterminate = np.ones(K, dtype=bool)
        passer_pressure_3u = int((np.hypot(opponents_raw[:, 0] - passer_raw[0], opponents_raw[:, 1] - passer_raw[1]) <= 3.0).sum())
        passer_pressure_5u = int((np.hypot(opponents_raw[:, 0] - passer_raw[0], opponents_raw[:, 1] - passer_raw[1]) <= 5.0).sum())
    else:
        opponents_within_3u = np.zeros(K, dtype=int)
        opponents_within_5u = np.zeros(K, dtype=int)
        opponents_within_10u = np.zeros(K, dtype=int)
        distance_to_nearest_opponent_u = np.full(K, np.nan)
        opponents_between_ball_and_destination = np.zeros(K, dtype=int)
        offside_destination = np.zeros(K, dtype=bool)
        offside_indeterminate = np.ones(K, dtype=bool)
        passer_pressure_3u = 0
        passer_pressure_5u = 0

    if M > 0:
        d_team = np.hypot(candidates_raw[:, 0][:, None] - teammates_raw[:, 0][None, :],
                           candidates_raw[:, 1][:, None] - teammates_raw[:, 1][None, :])
        teammates_within_5u = (d_team <= 5.0).sum(axis=1)
    else:
        teammates_within_5u = np.zeros(K, dtype=int)

    n_in_corridor, min_perp_distance_to_lane = lane_congestion(passer_raw, candidates_raw, opponents_raw)

    return {
        "distance_u": distance_u, "forward_progress_u": forward_progress_u,
        "lateral_shift_u": lateral_shift_u, "relative_bearing_deg": relative_bearing_deg,
        "opponents_within_3u": opponents_within_3u, "opponents_within_5u": opponents_within_5u,
        "opponents_within_10u": opponents_within_10u,
        "distance_to_nearest_opponent_u": distance_to_nearest_opponent_u,
        "teammates_within_5u": teammates_within_5u,
        "n_opponents_in_corridor": n_in_corridor, "min_perp_distance_to_lane": min_perp_distance_to_lane,
        "opponents_between_ball_and_destination": opponents_between_ball_and_destination,
        "passer_pressure_3u": np.full(K, passer_pressure_3u), "passer_pressure_5u": np.full(K, passer_pressure_5u),
        "is_teammate_destination": is_teammate_destination,
        "n_visible_players": np.full(K, n_visible),
        "offside_destination": offside_destination, "offside_indeterminate": offside_indeterminate,
    }
