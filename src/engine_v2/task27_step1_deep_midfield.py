"""
Task 27, Step 1: fix the deep-midfield group. Task 26's group included
anyone EVER listed at a defensive midfield position (a single event is
enough under `position_group()`'s own modal logic combined with a
substring-based DM check), ranking players like De Bruyne/Gakpo who
are not deep midfielders by any reasonable reading against a group of
genuine number 6s.

FIX: a player is DEEP MIDFIELD if at least 50% of his eligible passes
(at the Task 26 Step 3 threshold, 100, pooled across all competitions)
were made while his event `position` was Center, Left, or Right
Defensive Midfield -- computed PER PASS (not by a modal/ever-played
check), over the exact same 537-player qualifying population Task 26
built.

Run: python src/engine_v2/task27_step1_deep_midfield.py
"""
import json
import re
import unicodedata
import warnings
from pathlib import Path

import pandas as pd

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
EVENTS_DIR = DATA_DIR / "raw" / "events"
PASS_DER_V8_PATH = DATA_DIR / "processed" / "engine_v2" / "pass_der_v8.parquet"
LEADERBOARD_V5_PATH = DATA_DIR / "processed" / "leaderboard_v5.parquet"
OUT_PATH = DATA_DIR / "engine_v2_task27_step1_deep_midfield.json"
DM_SHARE_PATH = DATA_DIR / "processed" / "engine_v2" / "task27_dm_share.parquet"

DM_POSITIONS = {"Center Defensive Midfield", "Left Defensive Midfield", "Right Defensive Midfield"}
DM_SHARE_THRESHOLD = 0.50

FIXED_LIST = ["Kroos", "Modric", "Verratti", "Busquets", "De Bruyne", "Xhaka", "de Jong",
              "Kimmich", "Rodri", "Pedri", "Gundogan", "Grillitsch", "Shaparenko"]

NICKNAME_ALIASES = {
    "marquinhos": "marcos aoas correa",
    "jorginho": "jorge luiz frello filho",
    "pedri": "pedro gonzalez lopez",
    "rodri": "rodrigo hernandez cascante",
}


def normalize_name(s) -> str:
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return ""
    s = re.sub(r"'[^']*'", " ", str(s))
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-zA-Z\s]", " ", s)
    return " ".join(s.lower().split())


def name_matches(short_name: str, full_name: str) -> bool:
    norm_short = normalize_name(short_name)
    norm_short = NICKNAME_ALIASES.get(norm_short, norm_short)
    short_tokens = set(norm_short.split())
    full_tokens = set(normalize_name(full_name).split())
    return len(short_tokens) > 0 and short_tokens <= full_tokens


def main():
    print("Task 27 Step 1: fixing the deep-midfield group ...")
    qualifying = pd.read_parquet(LEADERBOARD_V5_PATH, columns=["player_id", "player_name", "n_eligible_passes"])
    qualifying_ids = set(qualifying["player_id"])
    print(f"  qualifying players (Task 26's 537, threshold=100): {len(qualifying_ids)}")

    per_pass = pd.read_parquet(PASS_DER_V8_PATH, columns=["match_id", "event_id", "player_id"])
    per_pass = per_pass[per_pass["player_id"].isin(qualifying_ids)]

    print("  looking up each pass's own event position (not modal) ...")
    match_ids = sorted(per_pass["match_id"].unique())
    pos_frames = []
    for mid in match_ids:
        ev = pd.read_parquet(EVENTS_DIR / f"{mid}.parquet", columns=["id", "position"])
        ev = ev.rename(columns={"id": "event_id"})
        ev["match_id"] = mid
        pos_frames.append(ev)
    positions = pd.concat(pos_frames, ignore_index=True)
    per_pass = per_pass.merge(positions, on=["match_id", "event_id"], how="left")
    per_pass["is_dm"] = per_pass["position"].isin(DM_POSITIONS)

    dm_share = per_pass.groupby("player_id").agg(
        n_eligible_passes=("is_dm", "size"), n_dm_passes=("is_dm", "sum")).reset_index()
    dm_share["dm_share"] = dm_share["n_dm_passes"] / dm_share["n_eligible_passes"]
    dm_share["is_deep_midfield"] = dm_share["dm_share"] >= DM_SHARE_THRESHOLD
    dm_share = dm_share.merge(qualifying[["player_id", "player_name"]], on="player_id", how="left")
    dm_share.to_parquet(DM_SHARE_PATH)

    n_deep_midfield = int(dm_share["is_deep_midfield"].sum())
    print(f"  DEEP MIDFIELD group size (>= {DM_SHARE_THRESHOLD:.0%} of passes at DM position): {n_deep_midfield}")

    fixed_list_shares = []
    for short_name in FIXED_LIST:
        hits = dm_share[dm_share["player_name"].apply(lambda n: name_matches(short_name, n))]
        if len(hits) == 1:
            r = hits.iloc[0]
            fixed_list_shares.append({"name": short_name, "player_name": r["player_name"],
                                       "dm_share": float(r["dm_share"]), "is_deep_midfield": bool(r["is_deep_midfield"]),
                                       "n_eligible_passes": int(r["n_eligible_passes"])})
        else:
            fixed_list_shares.append({"name": short_name, "dm_share": None, "note": f"{len(hits)} matches found"})
    for r in fixed_list_shares:
        print(f"    {r}")

    summary = {
        "n_qualifying_players": len(qualifying_ids), "dm_share_threshold": DM_SHARE_THRESHOLD,
        "n_deep_midfield": n_deep_midfield, "fixed_list_dm_shares": fixed_list_shares,
    }
    OUT_PATH.write_text(json.dumps(summary, indent=2, default=str))
    print(f"\nWrote {OUT_PATH} and {DM_SHARE_PATH}")
    return summary


if __name__ == "__main__":
    main()
