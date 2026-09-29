"""
Task 53, Step 1: praised-list name audit, BEFORE any replication row is
opened. docs/specs/task-53-tempo-replication.md.

Reads PLAYER-LEVEL tables only (no per-match event rows):
  study    data/processed/leaderboard_v5c.parquet (player_id, player_name)
  PFF      data/processed/pff/player_map.csv (pff_player_id, pff_name, sb_player_id, sb_name)
  2015/16  data/processed/engine_v2/task44_roles.parquet (player_id, player_name, league)
  reserved data/processed/engine_v2/task48_roles.parquet (player_id, player_name)
  holdout  no player-level name table exists; not opened (see the results page).
For each of the 13 names: every name_matches hit (Task 27's matcher) and
every loose hit (accent/case-insensitive surname substring), then the one
intended StatsBomb player_id. Writes docs/splits/praised_ids.csv and
data/engine_v2_task53_audit.json. Then re-checks which ids each earlier
praised-list test included, from the saved JSONs (no test is re-run).

Run: python src/engine_v2/task53_praised_audit.py
"""
import json
from pathlib import Path

import pandas as pd

from task27_step1_deep_midfield import name_matches, normalize_name

REPO = Path(__file__).parent.parent.parent
DATA = REPO / "data"
OUT_CSV = REPO / "docs" / "splits" / "praised_ids.csv"
OUT_JSON = DATA / "engine_v2_task53_audit.json"

# (list name as in Task 41's LIST_L, loose surname stem, intended player_id, intended player)
INTENDED = [
    ("Kroos", "kroos", 5574, "Toni Kroos"), ("Modric", "modri", 5463, "Luka Modric"),
    ("Verratti", "verratti", 3166, "Marco Verratti"), ("Busquets", "busquets", 5203, "Sergio Busquets"),
    ("De Bruyne", "bruyne", 3089, "Kevin De Bruyne"), ("Xhaka", "xhaka", 3500, "Granit Xhaka"),
    ("de Jong", "jong", 8118, "Frenkie de Jong"), ("Kimmich", "kimmich", 5579, "Joshua Kimmich"),
    ("Rodri", "rodri", 6765, "Rodri (Rodrigo Hernandez Cascante)"), ("Pedri", "pedr", 30486, "Pedri (Pedro Gonzalez Lopez)"),
    ("Gundogan", "gundo", 10287, "Ilkay Gundogan"), ("Grillitsch", "grillitsch", 11396, "Florian Grillitsch"),
    ("Shaparenko", "shaparenko", 21294, "Mykola Shaparenko"),
]


def name_tables() -> dict:
    pm = pd.read_csv(DATA / "processed" / "pff" / "player_map.csv")
    return {
        "study": pd.read_parquet(DATA / "processed" / "leaderboard_v5c.parquet", columns=["player_id", "player_name"]),
        "pff_map": pd.DataFrame({"player_id": pm["sb_player_id"], "player_name": pm["sb_name"].fillna(pm["pff_name"]),
                                 "pff_name": pm["pff_name"], "status": pm["status"]}),
        "2015/16": pd.read_parquet(DATA / "processed" / "engine_v2" / "task44_roles.parquet", columns=["player_id", "player_name", "league"]),
        "reserved": pd.read_parquet(DATA / "processed" / "engine_v2" / "task48_roles.parquet", columns=["player_id", "player_name"]),
    }


def audit_names(tables: dict) -> tuple:
    rows, cand = [], {}
    for short, stem, pid, label in INTENDED:
        hits = []
        for ds, t in tables.items():
            for _, r in t.dropna(subset=["player_name"]).iterrows():
                full = str(r["player_name"])
                nm = name_matches(short, full) or ("pff_name" in r and isinstance(r["pff_name"], str) and name_matches(short, r["pff_name"]))
                loose = stem in normalize_name(full) or ("pff_name" in r and isinstance(r["pff_name"], str) and stem in normalize_name(r["pff_name"]))
                if nm or loose:
                    hits.append({"dataset": ds, "player_id": None if pd.isna(r["player_id"]) else int(r["player_id"]),
                                 "full_name": full, "name_matches": bool(nm), "intended": bool(r["player_id"] == pid)})
        cand[short] = hits
        present = sorted({h["dataset"] for h in hits if h["intended"]})
        full = next((h["full_name"] for h in hits if h["intended"]), label)
        rows.append({"list_name": short, "player_id": pid, "full_name": full, "intended": label,
                     "datasets_present": ";".join(present) if present else "none of the audited tables"})
    return pd.DataFrame(rows), cand


def get(d, *path):
    for p in path:
        if not isinstance(d, dict) or p not in d:
            return None
        d = d[p]
    return d


def ids_of(present) -> list:
    if not present:
        return []
    out = []
    for p in present:
        v = p.get("sb_player_id", p.get("player_id")) if isinstance(p, dict) else p
        out.append(int(float(v)))
    return sorted(set(out))


def earlier_tests(intended: set) -> dict:
    load = lambda f: json.loads((DATA / f).read_text()) if (DATA / f).exists() else None
    t41, t42, t42p, t43 = load("engine_v2_task41_steps7_10.json"), load("engine_v2_task42_step2.json"), load("pff_task42_step3.json"), load("engine_v2_task43_steps3_6.json")
    t44, t45, t48, t52 = load("engine_v2_task44_steps4_5.json"), load("engine_v2_task45.json"), load("engine_v2_task48.json"), load("engine_v2_task52_tests.json")
    cells = {}
    for k in ("v5_decision", "rq_rel", "AV", "AV_vis"):
        cells[f"Task 41 step7.{k}"] = get(t41, "step7", k, "present")
    for k in ("pr_keep", "pr_fwd"):
        cells[f"Task 42 r3.{k}"] = get(t42, "r3", k, "present")
    cells["Task 42 (PFF) praised_list"] = get(t42p, "praised_list", "present")
    for k in ("pr2_keep", "pr2_fwd"):
        cells[f"Task 43 step4.{k}"] = get(t43, "step4", k, "present")
    for k in (get(t44, "praised") or {}):
        cells[f"Task 44 praised.{k}"] = get(t44, "praised", k, "present")
    for k in (get(t45, "steps1_2") or {}):
        cells[f"Task 45 steps1_2.{k}"] = get(t45, "steps1_2", k, "praised", "present")
    for k in ("praised_pr2_flag_keep", "praised_w"):
        cells[f"Task 48 report_only.{k}"] = get(t48, "report_only", k, "present")
    for ds in ("2015/16", "study"):
        for k in (get(t52, ds, "D5") or {}):
            cells[f"Task 52 {ds}.D5.{k}"] = get(t52, ds, "D5", k, "present")
    out = {}
    for k, pres in cells.items():
        ids = ids_of(pres)
        out[k] = {"ids": ids, "wrong_ids": [i for i in ids if i not in intended]}
    notes = {"Task 44 praised_list_matches": get(t44, "praised_list_matches"),
             "Task 45 praised_ids": get(t45, "praised_ids"),
             "Task 48 praised_list_matches": get(t48, "report_only", "praised_list_matches"),
             "Task 41 list_matched": get(t41, "step7", "list_matched")}
    return out, notes


def main():
    tables = name_tables()
    ids, cand = audit_names(tables)
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    ids[["list_name", "player_id", "full_name", "datasets_present"]].to_csv(OUT_CSV, index=False)
    intended = set(ids["player_id"])
    tests, notes = earlier_tests(intended)
    OUT_JSON.write_text(json.dumps({"praised_ids": ids.to_dict("records"), "candidates": cand, "earlier_tests": tests,
                                    "earlier_notes": notes,
                                    "holdout": "no player-level name table exists; holdout events not opened"}, indent=2, default=str))
    print(ids.to_string())
    for k, v in cand.items():
        wrong = [h for h in v if not h["intended"]]
        print(f"{k}: intended in {sorted({h['dataset'] for h in v if h['intended']})}; name_matches non-intended: "
              f"{[(h['dataset'], h['player_id'], h['full_name']) for h in wrong if h['name_matches']]}; loose-only: {len([h for h in wrong if not h['name_matches']])}")
    for k, v in tests.items():
        print(f"  {k}: {v}")
    print(f"Wrote {OUT_CSV} and {OUT_JSON}")


if __name__ == "__main__":
    main()
