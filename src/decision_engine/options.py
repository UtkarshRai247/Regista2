"""
Task 01 — Step 1: option sets.

Builds, for each eligible open-play pass, the candidate option set from
every visible teammate in the freeze frame (excluding the passer).

StatsBomb's 360 freeze frames carry NO player identity (confirmed from
statsbombpy's own source: only id/teammate/actor/keeper/location) so the
actual pass recipient can't be read off a frame row directly. Per D-011,
the chosen candidate is identified by ANGLE-MATCHING: the visible
teammate whose bearing from the passer is closest to the bearing of the
real pass_end_location, accepted only within 15 degrees, and rejected as
AMBIGUOUS if a second teammate rivals the match within 10 degrees and 5m.
pass_end_location is used ONLY for this matching step - once a candidate
is matched, every candidate (chosen and unchosen alike) gets its features
computed from its own freeze-frame location, so they stay comparable.

Run: python src/decision_engine/options.py
"""
import json
import math
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
EVENTS_DIR = DATA_DIR / "raw" / "events"
FRAMES_DIR = DATA_DIR / "raw" / "frames"
OUT_DIR = DATA_DIR / "processed" / "options_parts"

BEARING_ACCEPT_DEG = 15.0
AMBIGUITY_BEARING_DEG = 10.0
AMBIGUITY_DIST_M = 5.0
LANE_WIDTH_M = 1.0  # perpendicular distance threshold for "lane crosses opponent"

EXCLUDED_PASS_TYPES = {"Corner", "Free Kick", "Throw-in", "Kick Off", "Goal Kick"}


def bearing(a, b) -> float:
    dx, dy = b[0] - a[0], b[1] - a[1]
    return math.degrees(math.atan2(dy, dx)) % 360.0


def circular_diff(a: float, b: float) -> float:
    d = abs(a - b) % 360.0
    return min(d, 360.0 - d)


def dist(a, b) -> float:
    return math.hypot(b[0] - a[0], b[1] - a[1])


def point_segment_perp_distance(p, a, b) -> tuple[float, bool]:
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


def process_match(match_id: int) -> tuple[list[dict], dict]:
    events = pd.read_parquet(EVENTS_DIR / f"{match_id}.parquet")
    frames = pd.read_parquet(FRAMES_DIR / f"{match_id}.parquet")

    passes = events[
        (events["type"] == "Pass")
        & (~events["pass_type"].isin(EXCLUDED_PASS_TYPES))
        & (events["position"] != "Goalkeeper")
    ].copy()

    frames_by_event = {eid: g for eid, g in frames.groupby("id")}

    rows = []
    stats = {
        "eligible": 0, "no_frame": 0, "too_few_visible": 0, "no_candidates": 0,
        "matched": 0, "unmatched": 0, "ambiguous": 0,
        "matched_complete": 0, "unmatched_complete": 0, "ambiguous_complete": 0,
        "matched_incomplete": 0, "unmatched_incomplete": 0, "ambiguous_incomplete": 0,
        "bearing_diffs": [], "agree_nearest_endpoint": 0, "agree_checked": 0,
        "option_set_sizes": [],
    }

    for _, ev in passes.iterrows():
        eid = ev["id"]
        frame = frames_by_event.get(eid)
        if frame is None or len(frame) == 0:
            stats["no_frame"] += 1
            continue
        if len(frame) < 6:
            stats["too_few_visible"] += 1
            continue

        stats["eligible"] += 1
        is_complete = pd.isna(ev.get("pass_outcome"))

        teammates = frame[(frame["teammate"] == True) & (frame["actor"] == False)]
        opponents = frame[frame["teammate"] == False]
        if len(teammates) == 0:
            stats["no_candidates"] += 1
            continue

        stats["option_set_sizes"].append(len(teammates))

        passer_loc = tuple(ev["location"])
        end_loc = ev.get("pass_end_location")
        if end_loc is None or (isinstance(end_loc, float) and math.isnan(end_loc)):
            stats["no_candidates"] += 1
            continue
        end_loc = tuple(end_loc)
        target_bearing = bearing(passer_loc, end_loc)

        cands = []
        for _, t in teammates.iterrows():
            loc = tuple(t["location"])
            b = bearing(passer_loc, loc)
            cands.append({"location": loc, "bearing": b,
                          "diff": circular_diff(b, target_bearing)})
        cands.sort(key=lambda c: c["diff"])
        best = cands[0]

        outcome_bucket = "complete" if is_complete else "incomplete"

        if best["diff"] > BEARING_ACCEPT_DEG:
            stats["unmatched"] += 1
            stats[f"unmatched_{outcome_bucket}"] += 1
            continue

        ambiguous = False
        for c in cands[1:]:
            if (circular_diff(c["bearing"], best["bearing"]) <= AMBIGUITY_BEARING_DEG
                    and dist(c["location"], best["location"]) <= AMBIGUITY_DIST_M):
                ambiguous = True
                break
        if ambiguous:
            stats["ambiguous"] += 1
            stats[f"ambiguous_{outcome_bucket}"] += 1
            continue

        stats["matched"] += 1
        stats[f"matched_{outcome_bucket}"] += 1
        stats["bearing_diffs"].append(best["diff"])

        # validation: nearest-to-endpoint agreement, completed passes only
        if is_complete:
            stats["agree_checked"] += 1
            nearest = min(cands, key=lambda c: dist(c["location"], end_loc))
            if nearest["location"] == best["location"]:
                stats["agree_nearest_endpoint"] += 1

        opp_locs = [tuple(o["location"]) for _, o in opponents.iterrows()]

        for c in cands:
            loc = c["location"]
            n_near = sum(1 for o in opp_locs if dist(o, loc) <= 5.0)
            nearest_opp_dist = min((dist(o, loc) for o in opp_locs), default=np.nan)
            lane_crossed = False
            for o in opp_locs:
                perp, within = point_segment_perp_distance(o, passer_loc, loc)
                if within and perp <= LANE_WIDTH_M:
                    lane_crossed = True
                    break
            rows.append({
                "match_id": match_id, "event_id": eid,
                "team": ev["team"], "period": int(ev["period"]),
                "player_id": ev.get("player_id"),
                "passer_x": passer_loc[0], "passer_y": passer_loc[1],
                "candidate_x": loc[0], "candidate_y": loc[1],
                "distance": dist(passer_loc, loc),
                "angle": c["bearing"],
                "lane_crosses_opponent": lane_crossed,
                "opponents_within_5m": n_near,
                "distance_to_nearest_opponent": nearest_opp_dist,
                "n_opponents_visible": len(opp_locs),
                "chosen": c["location"] == best["location"],
                "pass_complete": is_complete,
            })

    return rows, stats


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    match_ids = sorted(int(p.stem) for p in EVENTS_DIR.glob("*.parquet")
                        if (FRAMES_DIR / p.name).exists())
    print(f"{len(match_ids)} matches with both events and frames on disk")

    agg = None
    for i, mid in enumerate(match_ids):
        out_path = OUT_DIR / f"{mid}.parquet"
        rows, stats = process_match(mid)
        if rows:
            pd.DataFrame(rows).to_parquet(out_path)
        if agg is None:
            agg = stats
            agg["bearing_diffs"] = list(stats["bearing_diffs"])
            agg["option_set_sizes"] = list(stats["option_set_sizes"])
        else:
            for k, v in stats.items():
                if isinstance(v, list):
                    agg[k].extend(v)
                else:
                    agg[k] = agg.get(k, 0) + v
        if (i + 1) % 50 == 0:
            print(f"  {i + 1}/{len(match_ids)} matches processed")

    summary = {k: v for k, v in agg.items() if not isinstance(v, list)}
    summary["bearing_diff_mean"] = float(np.mean(agg["bearing_diffs"])) if agg["bearing_diffs"] else None
    summary["bearing_diff_median"] = float(np.median(agg["bearing_diffs"])) if agg["bearing_diffs"] else None
    summary["bearing_diff_p90"] = float(np.percentile(agg["bearing_diffs"], 90)) if agg["bearing_diffs"] else None
    summary["option_set_size_mean"] = float(np.mean(agg["option_set_sizes"])) if agg["option_set_sizes"] else None
    summary["option_set_size_median"] = float(np.median(agg["option_set_sizes"])) if agg["option_set_sizes"] else None
    summary["agreement_rate_nearest_endpoint"] = (
        agg["agree_nearest_endpoint"] / agg["agree_checked"] if agg["agree_checked"] else None
    )
    summary["match_rate"] = agg["matched"] / agg["eligible"] if agg["eligible"] else None
    summary["unmatched_rate"] = agg["unmatched"] / agg["eligible"] if agg["eligible"] else None
    summary["ambiguous_rate"] = agg["ambiguous"] / agg["eligible"] if agg["eligible"] else None
    total_complete = agg["matched_complete"] + agg["unmatched_complete"] + agg["ambiguous_complete"]
    total_incomplete = agg["matched_incomplete"] + agg["unmatched_incomplete"] + agg["ambiguous_incomplete"]
    summary["drop_rate_complete"] = (
        (agg["unmatched_complete"] + agg["ambiguous_complete"]) / total_complete if total_complete else None
    )
    summary["drop_rate_incomplete"] = (
        (agg["unmatched_incomplete"] + agg["ambiguous_incomplete"]) / total_incomplete if total_incomplete else None
    )

    print(json.dumps(summary, indent=2))
    (DATA_DIR / "options_summary.json").write_text(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
