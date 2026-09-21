"""
Task 02 — Step 2: player crosswalk.
Matches our 102 players (from the 138-unit, >=200-pass sample) to
transfermarkt player records.

Match order:
1. Exact match on normalized full name.
2. Exact match on StatsBomb's own `player_nickname` field against
   transfermarkt's `name` (this directly handles "known nickname forms"
   the spec asks for — e.g. StatsBomb records Jorge Luiz Frello Filho's
   nickname as "Jorginho", which IS transfermarkt's `name` for him;
   without this, naive string-distance fuzzy matching on full legal
   names picks confidently wrong candidates, not just low-confidence
   ones — caught and fixed before finalizing the crosswalk).
3. Token-subset match: one side's name tokens are all contained in the
   other's, restricted to the same StatsBomb-reported country (handles
   e.g. "Ronald Federico Araujo da Silva" vs transfermarkt's "Ronald
   Araujo" — a real person, not a nickname, just a truncated name that
   whole-string fuzzy ratio scores too low to trust).
4. Whole-string fuzzy ratio (difflib), same-country pool only, high bar.
Anything left, or genuinely ambiguous (multiple equally-good
candidates), goes to manual_review — not auto-resolved.
Run: python src/market_join/crosswalk.py
"""
import difflib
import json
import re
import unicodedata
import warnings
from pathlib import Path

import duckdb
import pandas as pd

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
LINEUPS_DIR = DATA_DIR / "raw" / "lineups"
METRICS_PATH = DATA_DIR / "processed" / "player_season_metrics.parquet"
DUCKDB_PATH = DATA_DIR / "transfermarkt-datasets.duckdb"
OUT_PATH = DATA_DIR / "processed" / "player_crosswalk.csv"

FUZZY_ACCEPT_RATIO = 0.90


def normalize_name(name) -> str:
    if not isinstance(name, str):
        return ""
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_name = nfkd.encode("ascii", "ignore").decode("ascii").lower()
    ascii_name = re.sub(r"[.\-']", " ", ascii_name)
    ascii_name = re.sub(r"[^a-z0-9 ]", "", ascii_name)
    return re.sub(r"\s+", " ", ascii_name).strip()


def normalize_country(country) -> str:
    if not isinstance(country, str):
        return ""
    nfkd = unicodedata.normalize("NFKD", country)
    return nfkd.encode("ascii", "ignore").decode("ascii").lower().strip()


def token_subset_match(norm_a: str, norm_b: str) -> bool:
    ta, tb = set(norm_a.split()), set(norm_b.split())
    if not ta or not tb:
        return False
    shorter, longer = (ta, tb) if len(ta) <= len(tb) else (tb, ta)
    return shorter.issubset(longer)


def load_our_players() -> pd.DataFrame:
    metrics = pd.read_parquet(METRICS_PATH)
    sample = metrics[metrics["n_eligible_passes"] >= 200]
    player_ids = sample["player_id"].unique()

    info = {}
    for f in LINEUPS_DIR.glob("*.parquet"):
        lu = pd.read_parquet(f)
        for _, r in lu.iterrows():
            pid = r["player_id"]
            if pid in info:
                continue
            info[pid] = {"name": r["player_name"], "nickname": r["player_nickname"],
                         "country": r["country"]}

    rows = []
    for pid in player_ids:
        i = info.get(pid, {"name": None, "nickname": None, "country": None})
        rows.append({"player_id": pid, "sb_name": i["name"], "sb_nickname": i["nickname"],
                     "sb_country": i["country"]})
    return pd.DataFrame(rows)


def main():
    our_players = load_our_players()
    our_players["norm_name"] = our_players["sb_name"].apply(normalize_name)
    our_players["norm_nickname"] = our_players["sb_nickname"].apply(normalize_name)

    con = duckdb.connect(str(DUCKDB_PATH), read_only=True)
    tm = con.execute(
        "SELECT player_id, name, country_of_citizenship, date_of_birth, current_club_name FROM players"
    ).fetchdf()
    tm["norm_name"] = tm["name"].apply(normalize_name)
    tm["norm_country"] = tm["country_of_citizenship"].apply(normalize_country)
    by_norm_name = tm.groupby("norm_name")["player_id"].apply(list).to_dict()

    def country_disambiguate(candidates, country):
        nc = normalize_country(country)
        return tm[(tm["player_id"].isin(candidates)) & (tm["norm_country"] == nc)]

    def describe_candidates(rows) -> str:
        return "; ".join(
            f"id={r['player_id']} '{r['name']}' b.{r['date_of_birth']} @{r['current_club_name']}"
            for r in rows
        )

    results = []
    for _, p in our_players.iterrows():
        base = p.to_dict()

        # 1. exact full-name match
        cands = by_norm_name.get(p["norm_name"], [])
        if len(cands) == 1:
            results.append({**base, "tm_player_id": cands[0], "match_method": "exact"})
            continue
        if len(cands) > 1:
            m = country_disambiguate(cands, p["sb_country"])
            if len(m) == 1:
                results.append({**base, "tm_player_id": int(m.iloc[0]["player_id"]),
                                 "match_method": "normalized",
                                 "note": f"{len(cands)} exact-name candidates, disambiguated by country"})
            else:
                all_cands = tm[tm["player_id"].isin(cands)].to_dict("records")
                results.append({**base, "tm_player_id": None, "match_method": "manual_review",
                                 "note": f"{len(cands)} exact-name candidates, "
                                         f"country disambiguation gave {len(m)}: "
                                         f"{describe_candidates(all_cands)}"})
            continue

        # 2. nickname exact match against transfermarkt's name field
        if p["norm_nickname"]:
            nick_cands = by_norm_name.get(p["norm_nickname"], [])
            if len(nick_cands) == 1:
                results.append({**base, "tm_player_id": nick_cands[0], "match_method": "normalized",
                                 "note": f"matched via StatsBomb nickname '{p['sb_nickname']}'"})
                continue
            if len(nick_cands) > 1:
                m = country_disambiguate(nick_cands, p["sb_country"])
                if len(m) == 1:
                    results.append({**base, "tm_player_id": int(m.iloc[0]["player_id"]),
                                     "match_method": "normalized",
                                     "note": f"nickname '{p['sb_nickname']}' + country"})
                    continue

        # 3. token-subset match, same country only
        norm_c = normalize_country(p["sb_country"])
        pool = tm[tm["norm_country"] == norm_c] if norm_c else tm
        subset_hits = [row for _, row in pool.iterrows()
                       if token_subset_match(p["norm_name"], row["norm_name"])]
        if len(subset_hits) == 1:
            results.append({**base, "tm_player_id": int(subset_hits[0]["player_id"]),
                             "match_method": "fuzzy",
                             "note": f"token-subset vs '{subset_hits[0]['name']}'"})
            continue
        if len(subset_hits) > 1:
            results.append({**base, "tm_player_id": None, "match_method": "manual_review",
                             "note": f"{len(subset_hits)} token-subset candidates: "
                                     f"{describe_candidates(subset_hits)}"})
            continue

        # 4. whole-string fuzzy ratio, same country, high bar
        best_ratio, best_row = 0.0, None
        for _, t in pool.iterrows():
            ratio = difflib.SequenceMatcher(None, p["norm_name"], t["norm_name"]).ratio()
            if ratio > best_ratio:
                best_ratio, best_row = ratio, t
        if best_ratio >= FUZZY_ACCEPT_RATIO:
            results.append({**base, "tm_player_id": int(best_row["player_id"]), "match_method": "fuzzy",
                             "note": f"ratio={best_ratio:.3f} vs '{best_row['name']}'"})
        elif best_row is not None and len(pool) == 1:
            # exactly one same-country candidate at all, just below the bar —
            # worth a confident-looking flag rather than a bare low ratio
            results.append({**base, "tm_player_id": None, "match_method": "manual_review",
                             "note": f"only 1 same-country candidate, ratio {best_ratio:.3f}: "
                                     f"{describe_candidates([best_row.to_dict()])}"})
        else:
            note = (f"best fuzzy ratio only {best_ratio:.3f} vs "
                    f"{describe_candidates([best_row.to_dict()]) if best_row is not None else 'no candidates in pool'}")
            results.append({**base, "tm_player_id": None, "match_method": "manual_review", "note": note})

    df = pd.DataFrame(results)
    df.to_csv(OUT_PATH, index=False)

    counts = df["match_method"].value_counts().to_dict()
    unresolved = df[df["match_method"] == "manual_review"][
        ["player_id", "sb_name", "sb_country", "note"]
    ].to_dict("records")

    summary = {"counts": counts, "n_total": len(df), "manual_review_list": unresolved}
    print(json.dumps(summary, indent=2, default=str))
    (DATA_DIR / "crosswalk_summary.json").write_text(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
