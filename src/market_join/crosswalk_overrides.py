"""
Task 03 — Step 1: apply Amendment 2's A2.3 crosswalk resolutions.
Applied as an explicit override on top of the existing automated
crosswalk output, not by re-running or hand-tuning the matching
algorithm — traceable, and doesn't risk disturbing the 99 already-
correct automated matches.
Run: python src/market_join/crosswalk_overrides.py
"""
import warnings
from pathlib import Path

import pandas as pd

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
IN_PATH = DATA_DIR / "processed" / "player_crosswalk.csv"
OUT_PATH = DATA_DIR / "processed" / "player_crosswalk_v2.csv"

# player_id (StatsBomb) -> (tm_player_id, resolution note), per A2.3
OVERRIDES = {
    3436: (126665, "Idrissa Gana Gueye -> Idrissa Gueye b.1989-09-26, Everton"),
    8519: (344695, "Dayotchanculle Upamecano -> Dayot Upamecano b.1998-10-27, Bayern Munich"),
    8804: (7161, "Jonas Hofmann -> Jonas Hofmann b.1992-07-14, Bayer Leverkusen"),
}


def main():
    df = pd.read_csv(IN_PATH)
    applied = []
    for pid, (tmid, note) in OVERRIDES.items():
        mask = df["player_id"] == pid
        if not mask.any():
            print(f"WARNING: player_id {pid} not found in crosswalk")
            continue
        before = df.loc[mask, "match_method"].iloc[0]
        df.loc[mask, "tm_player_id"] = tmid
        df.loc[mask, "match_method"] = "manual_review"  # per spec: "recorded as manual_review"
        df.loc[mask, "note"] = f"A2.3 resolution: {note}"
        applied.append({"player_id": pid, "was": before, "tm_player_id": tmid})

    df.to_csv(OUT_PATH, index=False)
    print(f"Applied {len(applied)} overrides:")
    for a in applied:
        print(f"  {a}")
    print(f"\nRemaining unresolved (tm_player_id null): "
          f"{df['tm_player_id'].isna().sum()}")
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
