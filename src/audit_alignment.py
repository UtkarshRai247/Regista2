"""
Task 00 data audit — Section D.
1. Match-level crosswalk: all 64 PFF WC2022 matches vs StatsBomb's 64 WC2022
   matches, by date + team names.
2. Event-level alignment: for the one matched/downloaded sample game
   (PFF 3812 = Senegal vs Netherlands = StatsBomb match_id 3857285),
   compare goal timestamps between the two datasets.

Requires: data/pff_matches.json (from all_metadata/*.json), StatsBomb
open data via statsbombpy (no auth needed).
Run: python src/audit_alignment.py
"""
import json
import warnings
from pathlib import Path

from statsbombpy import sb

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent / "data"


def norm(name: str) -> str:
    return name.lower().strip()


def crosswalk():
    pff = json.loads((DATA_DIR / "pff_matches.json").read_text())
    sb_matches = sb.matches(competition_id=43, season_id=106)
    sb_recs = sb_matches[["match_id", "match_date", "home_team", "away_team"]].to_dict("records")

    sb_by_date = {}
    for m in sb_recs:
        sb_by_date.setdefault(m["match_date"], []).append(m)

    matched, unmatched = [], []
    for p in pff:
        hit = None
        for c in sb_by_date.get(p["date"], []):
            h, a = norm(c["home_team"]), norm(c["away_team"])
            ph, pa = norm(p["home"]), norm(p["away"])
            if (h == ph and a == pa) or (h == pa and a == ph):
                hit = c
                break
        (matched if hit else unmatched).append((p, hit))

    print(f"Match-level crosswalk: {len(matched)}/{len(pff)} PFF matches "
          f"matched unambiguously to a StatsBomb match by date+teams.")
    if unmatched:
        print("Unmatched:", [p for p, _ in unmatched])
    return matched


def alignment_test(sb_match_id: int):
    events = sb.events(match_id=sb_match_id)
    goals = events[(events["type"] == "Shot") & (events["shot_outcome"] == "Goal")]
    pff_events = json.loads((DATA_DIR / "pff_sample" / "3812.events.json").read_text())

    print("\nEvent-level alignment test (PFF game 3812 vs StatsBomb match "
          f"{sb_match_id}, Senegal vs Netherlands):")
    for _, row in goals.iterrows():
        minute, second = row["minute"], row["second"]
        # StatsBomb timestamp is period-relative; period 2 clock = 45:00 + elapsed
        sb_clock_sec = minute * 60 + second

        matches = [
            e for e in pff_events
            if (e.get("possessionEvents") or {}).get("shotOutcomeType") == "G"
            and row["player"].split()[-1] in (e.get("gameEvents") or {}).get("playerName", "")
        ]
        if not matches:
            print(f"  {row['player']}: no PFF match found")
            continue
        pff_clock = matches[0]["gameEvents"]["startFormattedGameClock"]
        pff_min, pff_sec = map(int, pff_clock.split(":"))
        pff_clock_sec = pff_min * 60 + pff_sec
        offset = sb_clock_sec - pff_clock_sec
        print(f"  {row['player']}: StatsBomb {minute:02d}:{second:02d} vs "
              f"PFF {pff_clock} -> offset = {offset:+.1f}s")


if __name__ == "__main__":
    crosswalk()
    alignment_test(3857285)
