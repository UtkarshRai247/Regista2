"""
Task 26, Step 4: the leaderboard, engine v5. Players pooled ACROSS
CONTEXTS (all competition-seasons summed) at the Step 3 threshold
(100 eligible passes), Decision per 100 shrunk toward the mean at the
measured reliability -- same pooling/shrinkage pattern as
`task12_artifacts.py`'s `step2_leaderboard` (`shrunken = overall_mean +
reliability * (raw - overall_mean)`), adapted to engine v5's
`pass_der_v8.parquet` (already has player_id/competition_id/season_id,
no `match_competition_lookup` join needed).

Position/name lookup: `build_position_and_name_lookup()` (ported once
here, per this project's own per-task independence convention -- the
same logic already used 3x elsewhere in the codebase), scanning
data/raw/events/*.parquet (the STUDY sample, not the holdout). The
coarse 4-way `position_group()` (GK/Defender/Midfielder/Forward,
`task04_situation_context.py`) is reused unchanged. There is no
existing "DEEP / DEFENSIVE MIDFIELD" group anywhere in this codebase;
it is defined here, disclosed, as the raw StatsBomb `position` string
containing "Defensive Midfield" (Center/Left/Right Defensive
Midfield) -- an assumption of the same kind and prominence as
`position_group()`'s own (its docstring already flags itself as
"not specified anywhere in the plan/codebase").

Run: python src/engine_v2/task26_step4_leaderboard.py
"""
import json
import re
import unicodedata
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
EVENTS_DIR = DATA_DIR / "raw" / "events"
PASS_DER_V8_PATH = DATA_DIR / "processed" / "engine_v2" / "pass_der_v8.parquet"
STEP3_SUMMARY_PATH = DATA_DIR / "engine_v2_task26_step3_threshold.json"
OUT_PARQUET = DATA_DIR / "processed" / "leaderboard_v5.parquet"
SUMMARY_PATH = DATA_DIR / "engine_v2_task26_step4_leaderboard.json"

TOP_BOTTOM_N = 20
FIXED_LIST = ["Kroos", "Modric", "Verratti", "Busquets", "De Bruyne", "Xhaka", "de Jong",
              "Kimmich", "Rodri", "Pedri", "Gundogan", "Grillitsch", "Shaparenko"]

COMP_NAMES = {
    (9, 281): "Bundesliga 2023/24", (43, 106): "FIFA World Cup 2022",
    (11, 90): "La Liga 2020/21", (7, 235): "Ligue 1 2022/23",
    (7, 108): "Ligue 1 2021/22", (44, 107): "MLS 2023",
    (55, 282): "UEFA Euro 2024", (55, 43): "UEFA Euro 2020",
}


def position_group(pos) -> str:
    """Ported unchanged from task04_situation_context.py."""
    if pos is None or (isinstance(pos, float) and pd.isna(pos)):
        return None
    if pos == "Goalkeeper":
        return "GK"
    if "Back" in pos:
        return "Defender"
    if "Midfield" in pos:
        return "Midfielder"
    return "Forward"


def is_deep_defensive_midfield(pos) -> bool:
    """Disclosed assumption (Section 4/6 of the results page): raw
    StatsBomb position string containing "Defensive Midfield"."""
    if pos is None or (isinstance(pos, float) and pd.isna(pos)):
        return False
    return "Defensive Midfield" in pos


def build_position_and_name_lookup() -> tuple:
    match_ids = sorted(int(p.stem) for p in EVENTS_DIR.glob("*.parquet"))
    pos_counts, name_counts = {}, {}
    for mid in match_ids:
        ev = pd.read_parquet(EVENTS_DIR / f"{mid}.parquet", columns=["player_id", "position", "player"])
        sub = ev.dropna(subset=["player_id", "position"])
        for pid, pos, name in zip(sub["player_id"], sub["position"], sub["player"]):
            pos_counts.setdefault(pid, {}).setdefault(pos, 0)
            pos_counts[pid][pos] += 1
            if pd.notna(name):
                name_counts.setdefault(pid, {}).setdefault(name, 0)
                name_counts[pid][name] += 1
    pos_lookup = {pid: max(counts, key=counts.get) for pid, counts in pos_counts.items()}
    name_lookup = {pid: max(counts, key=counts.get) for pid, counts in name_counts.items()}
    deep_def_mid_lookup = {pid: any(is_deep_defensive_midfield(p) for p in counts) for pid, counts in pos_counts.items()}
    return pos_lookup, name_lookup, deep_def_mid_lookup


NICKNAME_ALIASES = {
    "marquinhos": "marcos aoas correa",
    "jorginho": "jorge luiz frello filho",
    "pedri": "pedro gonzalez lopez",
    "rodri": "rodrigo hernandez cascante",
}


def normalize_name(s) -> str:
    """Ported unchanged from task14b_leaderboards_referee2.py: strips
    diacritics (NFKD) and punctuation, lowercases, collapses whitespace."""
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return ""
    s = re.sub(r"'[^']*'", " ", str(s))
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-zA-Z\s]", " ", s)
    return " ".join(s.lower().split())


def name_matches(short_name: str, full_name: str) -> bool:
    """Ported unchanged from task14b_leaderboards_referee2.py: token-subset
    matching after diacritic normalization, with nickname aliases for the
    footballing nicknames that are not morphological substrings of the
    player's registered name (found there by manual verification, not
    guessed)."""
    norm_short = normalize_name(short_name)
    norm_short = NICKNAME_ALIASES.get(norm_short, norm_short)
    short_tokens = set(norm_short.split())
    full_tokens = set(normalize_name(full_name).split())
    return len(short_tokens) > 0 and short_tokens <= full_tokens


def fixed_list_ranks(qualifying: pd.DataFrame, pooled: pd.DataFrame, name_lookup: dict, rank_col: str,
                      within_group: bool = False) -> list:
    rows = []
    for short_name in FIXED_LIST:
        row = {"name": short_name}
        hits = qualifying[qualifying["player_name"].apply(lambda n: name_matches(short_name, n))]
        if len(hits) == 1:
            r = hits.iloc[0]
            row["rank"] = int(r[rank_col])
            row["n_qualifying"] = len(qualifying) if not within_group else int((qualifying["position_group"] == r["position_group"]).sum())
            row["player_name"] = r["player_name"]
            row["position_group"] = r["position_group"]
            row["n_eligible_passes"] = int(r["n_eligible_passes"])
        elif len(hits) > 1:
            row["rank"] = "AMBIGUOUS: " + "; ".join(hits["player_name"].tolist())
        else:
            pool = pooled.copy()
            pool["player_name"] = pool["player_id"].map(lambda p: name_lookup.get(p, "?"))
            pool_hits = pool[pool["player_name"].apply(lambda n: name_matches(short_name, n))]
            if len(pool_hits) >= 1:
                row["rank"] = f"did not qualify (<{int(pooled.attrs.get('threshold', 0))} passes)"
                row["player_name"] = "; ".join(pool_hits["player_name"].tolist())
                row["n_eligible_passes"] = int(pool_hits["n_eligible_passes"].max())
            else:
                row["rank"] = "not found in our data"
        rows.append(row)
    return rows


def main():
    print("Task 26 Step 4: leaderboard, engine v5 ...")
    step3 = json.loads(STEP3_SUMMARY_PATH.read_text())
    threshold = step3["chosen_threshold"]
    reliability = step3["chosen_threshold_reliability"]
    provisional = step3["provisional"]
    print(f"  threshold={threshold}, reliability={reliability:.4f}, provisional={provisional}")

    per_pass = pd.read_parquet(PASS_DER_V8_PATH, columns=["player_id", "competition_id", "season_id", "decision_new"])
    pooled = per_pass.groupby("player_id").agg(
        n_eligible_passes=("decision_new", "count"), decision_per_100=("decision_new", lambda s: s.mean() * 100),
    ).reset_index()
    pooled.attrs["threshold"] = threshold
    qualifying = pooled[pooled["n_eligible_passes"] >= threshold].copy()
    n_qualifying = len(qualifying)
    print(f"  qualifying players (>= {threshold} pooled eligible passes): {n_qualifying}")

    comps_per_player = per_pass[per_pass["player_id"].isin(qualifying["player_id"])].groupby(
        "player_id").apply(lambda g: sorted(set(
            COMP_NAMES.get((c, s), f"comp={c},season={s}")
            for c, s in zip(g["competition_id"], g["season_id"])))).rename("competitions").reset_index()
    qualifying = qualifying.merge(comps_per_player, on="player_id", how="left")

    print("  building position/name lookup from raw events ...")
    pos_lookup, name_lookup, deep_def_mid_lookup = build_position_and_name_lookup()
    qualifying["position_group"] = qualifying["player_id"].map(lambda p: position_group(pos_lookup.get(p)))
    qualifying["player_name"] = qualifying["player_id"].map(lambda p: name_lookup.get(p, "?"))
    qualifying["is_deep_def_mid"] = qualifying["player_id"].map(lambda p: deep_def_mid_lookup.get(p, False))

    overall_mean = float(qualifying["decision_per_100"].mean())
    qualifying["shrunken_decision_per_100"] = overall_mean + reliability * (qualifying["decision_per_100"] - overall_mean)

    qualifying = qualifying.sort_values("shrunken_decision_per_100", ascending=False).reset_index(drop=True)
    qualifying["rank_overall"] = qualifying.index + 1

    qualifying["group_mean"] = qualifying.groupby("position_group")["shrunken_decision_per_100"].transform("mean")
    qualifying["group_std"] = qualifying.groupby("position_group")["shrunken_decision_per_100"].transform(lambda s: s.std(ddof=1))
    qualifying["z_within_position"] = (qualifying["shrunken_decision_per_100"] - qualifying["group_mean"]) / qualifying["group_std"]
    qualifying["rank_within_position"] = qualifying.groupby("position_group")["z_within_position"].rank(ascending=False).astype(int)

    cols = ["player_id", "player_name", "position_group", "competitions", "n_eligible_passes",
            "decision_per_100", "shrunken_decision_per_100", "z_within_position", "rank_overall", "rank_within_position"]
    top20 = qualifying.nlargest(TOP_BOTTOM_N, "shrunken_decision_per_100")[cols].to_dict("records")
    bottom20 = qualifying.nsmallest(TOP_BOTTOM_N, "shrunken_decision_per_100")[cols].to_dict("records")
    print(f"  overall_mean={overall_mean:.5f}")
    print(f"  top 5 (overall): {[r['player_name'] for r in top20[:5]]}")
    print(f"  bottom 5 (overall): {[r['player_name'] for r in bottom20[:5]]}")

    deep_def_mid = qualifying[qualifying["is_deep_def_mid"]].copy()
    deep_def_mid = deep_def_mid.sort_values("z_within_position", ascending=False).reset_index(drop=True)
    deep_def_mid["rank_deep_def_mid"] = deep_def_mid.index + 1
    print(f"  DEEP/DEFENSIVE MIDFIELD qualifying players: {len(deep_def_mid)}")

    fixed_overall = fixed_list_ranks(qualifying, pooled, name_lookup, "rank_overall")
    fixed_within_position = fixed_list_ranks(qualifying, pooled, name_lookup, "rank_within_position", within_group=True)
    print(f"  fixed-list overall ranks: {[(r['name'], r.get('rank')) for r in fixed_overall]}")

    qualifying.drop(columns=["group_mean", "group_std"]).to_parquet(OUT_PARQUET)
    print(f"\nWrote {OUT_PARQUET}")

    summary = {
        "threshold": threshold, "reliability": reliability, "provisional": provisional,
        "n_qualifying_players": n_qualifying, "overall_mean_decision_per_100": overall_mean,
        "top20": top20, "bottom20": bottom20,
        "n_deep_def_mid_qualifying": len(deep_def_mid),
        "deep_def_mid_table": deep_def_mid[cols + ["rank_deep_def_mid"]].to_dict("records"),
        "fixed_list_overall": fixed_overall, "fixed_list_within_position": fixed_within_position,
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
    print(f"\nWrote {SUMMARY_PATH}")
    return summary


if __name__ == "__main__":
    main()
