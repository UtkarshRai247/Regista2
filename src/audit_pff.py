"""
Task 00 data audit — Section C.
Inspects the one downloaded PFF sample match (game 3812) and reports
format, size, frame rate, coordinate system, identifiers, ball tracking,
visibility/confidence flags, and completeness across the match.
Run: python src/audit_pff.py
"""
import bz2
import json
from pathlib import Path

SAMPLE_DIR = Path(__file__).parent.parent / "data" / "pff_sample"


def main():
    meta = json.loads((SAMPLE_DIR / "3812.metadata.json").read_text())[0]
    print("=== Metadata ===")
    print(f"Match: {meta['homeTeam']['name']} vs {meta['awayTeam']['name']}, "
          f"{meta['date']}, {meta['stadium']['name']}")
    pitch = meta["stadium"]["pitches"][0]
    print(f"Pitch: {pitch['length']}m x {pitch['width']}m")
    print(f"fps: {meta['fps']}")

    tracking_path = SAMPLE_DIR / "3812.tracking.jsonl.bz2"
    print(f"\n=== Tracking file ===")
    print(f"Compressed size: {tracking_path.stat().st_size / 1e6:.1f} MB")

    n_frames = 0
    periods = set()
    vis_counts = {}
    conf_counts = {}
    x_min = y_min = float("inf")
    x_max = y_max = float("-inf")
    ball_present_frames = 0
    n_events_linked = 0
    first_time = last_time = None

    with bz2.open(tracking_path, "rt") as f:
        for line in f:
            frame = json.loads(line)
            n_frames += 1
            periods.add(frame["period"])
            t = frame["videoTimeMs"]
            if first_time is None:
                first_time = t
            last_time = t

            for side in ("homePlayers", "awayPlayers"):
                for p in frame.get(side) or []:
                    vis_counts[p["visibility"]] = vis_counts.get(p["visibility"], 0) + 1
                    conf_counts[p["confidence"]] = conf_counts.get(p["confidence"], 0) + 1
                    x_min, x_max = min(x_min, p["x"]), max(x_max, p["x"])
                    y_min, y_max = min(y_min, p["y"]), max(y_max, p["y"])

            balls = frame.get("balls") or []
            if balls:
                ball_present_frames += 1
            if frame.get("game_event_id") is not None:
                n_events_linked += 1

    print(f"Total frames: {n_frames:,}")
    print(f"Periods present: {sorted(periods)}")
    print(f"Video time range: {first_time:.0f}ms - {last_time:.0f}ms "
          f"({(last_time - first_time) / 60000:.1f} min)")
    print(f"Implied fps from frame count/duration: "
          f"{n_frames / ((last_time - first_time) / 1000):.2f}")
    print(f"\nCoordinate bounds observed: x=[{x_min:.1f}, {x_max:.1f}], "
          f"y=[{y_min:.1f}, {y_max:.1f}] (pitch is {pitch['length']}x{pitch['width']}m, "
          f"so origin is pitch center)")
    print(f"\nPlayer-frame visibility counts: {vis_counts}")
    pct_estimated = vis_counts.get("ESTIMATED", 0) / sum(vis_counts.values()) * 100
    print(f"  -> {pct_estimated:.1f}% of player-frames are ESTIMATED (not directly visible)")
    print(f"Player-frame confidence counts: {conf_counts}")
    print(f"\nFrames with ball position present: {ball_present_frames:,} / {n_frames:,} "
          f"({ball_present_frames / n_frames * 100:.1f}%)")
    print(f"Frames linked to a game_event_id: {n_events_linked:,} / {n_frames:,}")

    events = json.loads((SAMPLE_DIR / "3812.events.json").read_text())
    print(f"\n=== Event data (3812.events.json) ===")
    print(f"Total events for this match: {len(events):,}")

    roster = json.loads((SAMPLE_DIR / "3812.roster.json").read_text())
    print(f"\n=== Roster ===")
    print(f"Roster entries: {len(roster)}")


if __name__ == "__main__":
    main()
