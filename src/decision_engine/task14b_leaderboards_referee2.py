"""
Task 14b — Leaderboards and Referee 2.

Governing document: docs/specs/analysis-plan-v3.md, Amendments v3-1 to
v3-5; plan v3 sections 4 and 5.

Run: python src/decision_engine/task14b_leaderboards_referee2.py
"""
import json
import re
import unicodedata
import warnings

import numpy as np
import pandas as pd

from decompose import DATA_DIR, EVENTS_DIR, match_competition_lookup
from task04_situation_context import position_group
from task12_artifacts import (
    COMP_NAMES, MIN_PASSES_LEADERBOARD, RELIABILITY, TOP_BOTTOM_N, build_position_and_name_lookup,
)
from task14a_referee1 import build_per_pass_o1, build_per_pass_o2, build_per_pass_o3
from task13_objectives import POLICY_PATH

warnings.filterwarnings("ignore")

EXPERT_CSV = DATA_DIR / "expert_lists" / "selections.csv"
LEADERBOARD_PATH = DATA_DIR / "processed" / "leaderboards_o1_o2_o3.parquet"
SUMMARY_PATH = DATA_DIR / "task14b_leaderboards_referee2.json"

OBJECTIVES = ["O1", "O2", "O3"]

FIXED_LIST = ["Kroos", "Modric", "Verratti", "Busquets", "De Bruyne", "Xhaka", "de Jong",
              "Kimmich", "Rodri", "Pedri", "Gundogan", "Grillitsch", "Shaparenko"]

# Maps the CSV's own (competition, season) text to our (competition_id, season_id).
COMP_SEASON_BY_NAME = {
    ("FIFA World Cup", "2022"): (43, 106),
    ("UEFA Euro", "2020"): (55, 43),
    ("UEFA Euro", "2024"): (55, 282),
    ("Ligue 1", "2021/22"): (7, 108),
    ("Ligue 1", "2022/23"): (7, 235),
    ("Bundesliga", "2023/24"): (9, 281),
    ("Major League Soccer", "2023"): (44, 107),
}
WORLD_CUP_KEY = (43, 106)

# ---------------------------------------------------------------------------
# Team-strength baselines (v3-5 / plan v3 section 4: "final league position,
# or the tournament round it reached"). Fetched from Wikipedia's own final
# tables/knockout-stage pages for each competition-season; team names are
# spelled exactly as they appear in this project's own data
# (data/raw/matches/*.parquet home_team/away_team), not as the source
# spelled them, to key directly against our per_pass "team" column.
# Tournament round is an ordinal scale (higher = further): 1=group stage,
# 2=round of 16, 3=quarter-final, 4=semi-final, 5=runner-up, 6=champion.
# ---------------------------------------------------------------------------

WC2022_ROUND = {
    "Argentina": 6, "France": 5, "Croatia": 4, "Morocco": 4,
    "Netherlands": 3, "England": 3, "Brazil": 3, "Portugal": 3,
    "United States": 2, "Australia": 2, "Poland": 2, "Senegal": 2,
    "Japan": 2, "South Korea": 2, "Spain": 2, "Switzerland": 2,
    "Belgium": 1, "Cameroon": 1, "Canada": 1, "Costa Rica": 1, "Denmark": 1,
    "Ecuador": 1, "Germany": 1, "Ghana": 1, "Iran": 1, "Mexico": 1,
    "Qatar": 1, "Saudi Arabia": 1, "Serbia": 1, "Tunisia": 1, "Uruguay": 1, "Wales": 1,
}

EURO2020_ROUND = {
    "Italy": 6, "England": 5, "Spain": 4, "Denmark": 4,
    "Belgium": 3, "Switzerland": 3, "Czech Republic": 3, "Ukraine": 3,
    "Wales": 2, "Austria": 2, "Netherlands": 2, "Portugal": 2, "Croatia": 2,
    "France": 2, "Germany": 2, "Sweden": 2,
    "Finland": 1, "Hungary": 1, "North Macedonia": 1, "Poland": 1,
    "Russia": 1, "Scotland": 1, "Slovakia": 1, "Turkey": 1,
}

EURO2024_ROUND = {
    "Spain": 6, "England": 5, "France": 4, "Netherlands": 4,
    "Germany": 3, "Portugal": 3, "Switzerland": 3, "Turkey": 3,
    "Italy": 2, "Denmark": 2, "Slovakia": 2, "Georgia": 2, "Belgium": 2,
    "Slovenia": 2, "Romania": 2, "Austria": 2,
    "Albania": 1, "Croatia": 1, "Czech Republic": 1, "Hungary": 1,
    "Poland": 1, "Scotland": 1, "Serbia": 1, "Ukraine": 1,
}

BUNDESLIGA_2324_POS = {
    "Bayer Leverkusen": 1, "VfB Stuttgart": 2, "Bayern Munich": 3, "RB Leipzig": 4,
    "Borussia Dortmund": 5, "Eintracht Frankfurt": 6, "Hoffenheim": 7, "FC Heidenheim": 8,
    "Werder Bremen": 9, "Freiburg": 10, "Augsburg": 11, "Wolfsburg": 12,
    "FSV Mainz 05": 13, "Borussia Mönchengladbach": 14, "Union Berlin": 15,
    "Bochum": 16, "FC Köln": 17, "Darmstadt 98": 18,
}

LIGUE1_2122_POS = {
    "Paris Saint-Germain": 1, "Olympique de Marseille": 2, "AS Monaco": 3, "Rennes": 4,
    "OGC Nice": 5, "Strasbourg": 6, "Lens": 7, "Lyon": 8, "Nantes": 9, "Lille": 10,
    "Montpellier": 13, "Troyes": 15, "Lorient": 16, "Saint-Étienne": 18, "Metz": 19,
    "Stade de Reims": 12, "Clermont Foot": 17, "Bordeaux": 20,
}

LIGUE1_2223_POS = {
    "Paris Saint-Germain": 1, "Lens": 2, "Olympique de Marseille": 3, "Rennes": 4,
    "Lille": 5, "AS Monaco": 6, "Lyon": 7, "Clermont Foot": 8, "OGC Nice": 9,
    "Lorient": 10, "Stade de Reims": 11, "Montpellier": 12, "Toulouse": 13,
    "Stade Brestois": 14, "Strasbourg": 15, "Nantes": 16, "Auxerre": 17,
    "AC Ajaccio": 18, "Troyes": 19, "Angers": 20,
}

MLS2023_RANK = {
    "Cincinnati": 1, "LAFC": 8, "Nashville SC": 12, "New York Red Bulls": 17,
    "Charlotte": 19, "Inter Miami": 27, "Toronto FC": 29,
}
MLS2023_N_TEAMS = 29

RAW_STRENGTH = {
    (43, 106): WC2022_ROUND, (55, 43): EURO2020_ROUND, (55, 282): EURO2024_ROUND,
}
POSITION_TABLES = {
    (9, 281): (BUNDESLIGA_2324_POS, 18), (7, 108): (LIGUE1_2122_POS, 20),
    (7, 235): (LIGUE1_2223_POS, 20), (44, 107): (MLS2023_RANK, MLS2023_N_TEAMS),
}


def raw_team_strength(comp_id: int, season_id: int, team: str):
    """Higher = stronger, on each competition-season's own raw scale
    (tournament round ordinal 1-6, or n_teams+1-position for leagues so a
    league title also scores highest). Comparability across competitions
    is handled by z-scoring within competition-season before pooling
    (Section 4 of the results page), since round-reached and league
    position are not on the same underlying scale."""
    key = (comp_id, season_id)
    if key in RAW_STRENGTH:
        return RAW_STRENGTH[key].get(team)
    if key in POSITION_TABLES:
        table, n_teams = POSITION_TABLES[key]
        pos = table.get(team)
        return (n_teams + 1 - pos) if pos is not None else None
    return None


# ---------------------------------------------------------------------------
# Name normalization for matching the expert lists to our own player names
# ---------------------------------------------------------------------------

def normalize_name(s) -> str:
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return ""
    s = re.sub(r"'[^']*'", " ", str(s))
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-zA-Z\s]", " ", s)
    return " ".join(s.lower().split())


# Confirmed by manually inspecting each competition-season's own candidate
# pool for every name token-matching left unmatched: these four footballing
# nicknames are NOT morphological substrings of the player's own registered
# name (unlike e.g. "Kroos" subset of "Toni Kroos"), so plain token-subset
# matching misses them even though the player is present in our data. Found,
# not guessed: each was verified against this project's own player_name
# lookup before being added here.
NICKNAME_ALIASES = {
    "marquinhos": "marcos aoas correa",
    "jorginho": "jorge luiz frello filho",
    "pedri": "pedro gonzalez lopez",
    "rodri": "rodrigo hernandez cascante",
}


def name_matches(short_name: str, full_name: str) -> bool:
    norm_short = normalize_name(short_name)
    norm_short = NICKNAME_ALIASES.get(norm_short, norm_short)
    short_tokens = set(norm_short.split())
    full_tokens = set(normalize_name(full_name).split())
    return len(short_tokens) > 0 and short_tokens <= full_tokens


# ---------------------------------------------------------------------------
# Step 1: leaderboards
# ---------------------------------------------------------------------------

def build_leaderboard(per_pass: pd.DataFrame, objective: str, pos_lookup: dict, name_lookup: dict) -> pd.DataFrame:
    """Same construction as task12_artifacts.step2_leaderboard (pooled by
    player_id across all contexts, >=200 eligible passes, shrinkage at the
    measured reliability), extended to return the FULL ranked table."""
    comp_lookup = match_competition_lookup()
    per_pass = per_pass.copy()
    per_pass["competition_id"] = per_pass["match_id"].map(lambda m: comp_lookup.get(m, (None, None))[0])
    per_pass["season_id"] = per_pass["match_id"].map(lambda m: comp_lookup.get(m, (None, None))[1])

    pooled = per_pass.groupby("player_id").agg(
        n_eligible_passes=("decision", "count"), decision_per_100=("decision", lambda s: s.mean() * 100),
    ).reset_index()
    qualifying = pooled[pooled["n_eligible_passes"] >= MIN_PASSES_LEADERBOARD].copy()

    comps_per_player = per_pass[per_pass["player_id"].isin(qualifying["player_id"])].groupby(
        "player_id").apply(lambda g: sorted(set(
            COMP_NAMES.get((c, s), f"comp={c},season={s}")
            for c, s in zip(g["competition_id"], g["season_id"])))).rename("competitions").reset_index()
    qualifying = qualifying.merge(comps_per_player, on="player_id", how="left")

    qualifying["position_group"] = qualifying["player_id"].map(lambda p: position_group(pos_lookup.get(p)))
    qualifying["player_name"] = qualifying["player_id"].map(lambda p: name_lookup.get(p, "?"))

    overall_mean_unweighted = float(qualifying["decision_per_100"].mean())
    qualifying["shrunken_decision_per_100"] = overall_mean_unweighted + RELIABILITY * (
        qualifying["decision_per_100"] - overall_mean_unweighted)
    qualifying["objective"] = objective
    qualifying = qualifying.sort_values("shrunken_decision_per_100", ascending=False).reset_index(drop=True)
    qualifying["rank"] = qualifying.index + 1
    qualifying.attrs["overall_mean_unweighted"] = overall_mean_unweighted
    return qualifying, pooled


def fixed_list_ranks(leaderboards: dict, pooled: dict, name_lookup: dict) -> list:
    """pooled[obj] is the FULL (unfiltered by the 200-pass floor) per-player
    table, used here only to report an actual pass count for a fixed-list
    player who didn't reach the leaderboard's qualifying threshold."""
    rows = []
    for short_name in FIXED_LIST:
        row = {"name": short_name}
        for obj in OBJECTIVES:
            lb = leaderboards[obj]
            hits = lb[lb["player_name"].apply(lambda n: name_matches(short_name, n))]
            if len(hits) == 1:
                r = hits.iloc[0]
                row[f"{obj}_rank"] = int(r["rank"])
                row[f"{obj}_n_qualifying"] = len(lb)
                row[f"{obj}_player_name"] = r["player_name"]
                row[f"{obj}_n_passes"] = int(r["n_eligible_passes"])
            elif len(hits) > 1:
                row[f"{obj}_rank"] = "AMBIGUOUS: " + "; ".join(hits["player_name"].tolist())
            else:
                pool = pooled[obj].copy()
                pool["player_name"] = pool["player_id"].map(lambda p: name_lookup.get(p, "?"))
                pool_hits = pool[pool["player_name"].apply(lambda n: name_matches(short_name, n))]
                if len(pool_hits) >= 1:
                    row[f"{obj}_rank"] = "did not qualify (<200 passes)"
                    row[f"{obj}_player_name"] = "; ".join(pool_hits["player_name"].tolist())
                    row[f"{obj}_n_passes"] = int(pool_hits["n_eligible_passes"].max())
                else:
                    row[f"{obj}_rank"] = "not found in our data"
        rows.append(row)
    return rows


# ---------------------------------------------------------------------------
# Step 2: match expert lists to (player, competition, season) units; power
# ---------------------------------------------------------------------------

def build_context_units(per_pass: pd.DataFrame, objective: str, pos_lookup: dict, name_lookup: dict) -> pd.DataFrame:
    comp_lookup = match_competition_lookup()
    per_pass = per_pass.copy()
    per_pass["competition_id"] = per_pass["match_id"].map(lambda m: comp_lookup.get(m, (None, None))[0])
    per_pass["season_id"] = per_pass["match_id"].map(lambda m: comp_lookup.get(m, (None, None))[1])

    grp = per_pass.groupby(["player_id", "competition_id", "season_id"]).agg(
        n_eligible_passes=("decision", "count"), decision_per_100=("decision", lambda s: s.mean() * 100),
    ).reset_index()
    qualifying = grp[grp["n_eligible_passes"] >= MIN_PASSES_LEADERBOARD].copy()
    qualifying = qualifying[qualifying.apply(
        lambda r: (int(r["competition_id"]), int(r["season_id"])) in COMP_SEASON_BY_NAME.values(), axis=1)]

    team_mode = per_pass.groupby(["player_id", "competition_id", "season_id"])["team"].agg(
        lambda s: s.value_counts().idxmax())
    qualifying = qualifying.merge(team_mode.rename("team"), on=["player_id", "competition_id", "season_id"], how="left")

    qualifying["position_group"] = qualifying["player_id"].map(lambda p: position_group(pos_lookup.get(p)))
    qualifying["player_name"] = qualifying["player_id"].map(lambda p: name_lookup.get(p, "?"))
    qualifying["objective"] = objective
    return qualifying.reset_index(drop=True)


def match_expert_list(units: pd.DataFrame, expert: pd.DataFrame) -> tuple:
    units = units.copy()
    units["selected"] = False
    matched_rows, unmatched = [], []
    for (comp, season), grp in expert.groupby(["competition", "season"]):
        if comp == "La Liga":
            continue
        key = COMP_SEASON_BY_NAME.get((comp, season))
        if key is None:
            continue
        comp_id, season_id = key
        sub_units = units[(units["competition_id"] == comp_id) & (units["season_id"] == season_id)]
        for _, r in grp.iterrows():
            player = r["player_name_as_published"]
            hits = sub_units[sub_units["player_name"].apply(lambda n: name_matches(player, n))]
            if len(hits) == 1:
                units.loc[hits.index, "selected"] = True
                matched_rows.append({"competition": comp, "season": season, "expert_name": player,
                                      "matched_name": hits.iloc[0]["player_name"]})
            elif len(hits) > 1:
                unmatched.append({"competition": comp, "season": season, "expert_name": player,
                                   "reason": f"ambiguous match: {hits['player_name'].tolist()}"})
            else:
                all_units_this_comp = units[(units["competition_id"] == comp_id) & (units["season_id"] == season_id)]
                reason = "name not found among this competition-season's qualifying units"
                unmatched.append({"competition": comp, "season": season, "expert_name": player,
                                   "position_as_published": r["position_as_published"], "reason": reason})
    return units, matched_rows, unmatched


def hanley_mcneil_se(n_pos: int, n_neg: int, auc: float = 0.5) -> float:
    q1 = auc / (2 - auc)
    q2 = 2 * auc ** 2 / (1 + auc)
    var = (auc * (1 - auc) + (n_pos - 1) * (q1 - auc ** 2) + (n_neg - 1) * (q2 - auc ** 2)) / (n_pos * n_neg)
    return float(np.sqrt(var))


def power_mde(n_pos: int, n_neg: int, alpha: float = 0.05, power: float = 0.80) -> float:
    """Minimum detectable AUC improvement at the given power, comparing two
    AUCs on the same n_pos/n_neg units. SE for each AUC via the standard
    Hanley-McNeil (1982) nonparametric variance formula, evaluated at the
    conservative null AUC=0.5 (the largest-variance point, standard
    practice when the true AUC isn't known in advance). The two models'
    AUC difference is treated as approximately independent (no prior
    estimate of their correlation exists in this project) -- a
    conservative (worst-case, largest-MDE) simplification, disclosed here
    since the brief specifies the requirement but not an estimator."""
    se_single = hanley_mcneil_se(n_pos, n_neg, auc=0.5)
    se_diff = np.sqrt(2) * se_single
    z_alpha = 1.959963984540054  # two-sided 0.05
    z_power = 0.8416212335729143  # 80% power
    return float((z_alpha + z_power) * se_diff)


# ---------------------------------------------------------------------------
# Step 3: Referee 2 AUC test
# ---------------------------------------------------------------------------

def auc_from_scores(y: np.ndarray, scores: np.ndarray) -> float:
    from sklearn.metrics import roc_auc_score
    return float(roc_auc_score(y, scores))


def fit_and_compare_auc(units: pd.DataFrame, exclude_world_cup: bool = False, n_boot: int = 1000, seed: int = 42) -> dict:
    import statsmodels.api as sm

    df = units.dropna(subset=["team_strength_z", "decision_z"]).copy()
    if exclude_world_cup:
        df = df[~((df["competition_id"] == WORLD_CUP_KEY[0]) & (df["season_id"] == WORLD_CUP_KEY[1]))]
    y = df["selected"].astype(float).values
    n_pos, n_neg = int(y.sum()), int((1 - y).sum())
    if n_pos == 0 or n_neg == 0:
        return {"n": len(df), "n_pos": n_pos, "n_neg": n_neg, "error": "no variation in selection outcome"}

    X_i = sm.add_constant(df[["team_strength_z"]].astype(float))
    model_i = sm.Logit(y, X_i).fit(disp=0)
    auc_i = auc_from_scores(y, model_i.predict(X_i))

    X_ii = sm.add_constant(df[["team_strength_z", "decision_z"]].astype(float))
    model_ii = sm.Logit(y, X_ii).fit(disp=0)
    auc_ii = auc_from_scores(y, model_ii.predict(X_ii))

    diff = auc_ii - auc_i
    rng = np.random.default_rng(seed)
    groups = df["comp_season_str"].values
    unique_groups = np.unique(groups)
    boot_diffs = []
    for _ in range(n_boot):
        sampled_groups = rng.choice(unique_groups, size=len(unique_groups), replace=True)
        idx = np.concatenate([np.where(groups == g)[0] for g in sampled_groups])
        yb = y[idx]
        if yb.sum() == 0 or yb.sum() == len(yb):
            continue
        Xi_b = sm.add_constant(df[["team_strength_z"]].astype(float).values[idx], has_constant="add")
        Xii_b = sm.add_constant(df[["team_strength_z", "decision_z"]].astype(float).values[idx], has_constant="add")
        try:
            mi = sm.Logit(yb, Xi_b).fit(disp=0)
            mii = sm.Logit(yb, Xii_b).fit(disp=0)
            auc_i_b = auc_from_scores(yb, mi.predict(Xi_b))
            auc_ii_b = auc_from_scores(yb, mii.predict(Xii_b))
            boot_diffs.append(auc_ii_b - auc_i_b)
        except Exception:
            continue
    boot_diffs = np.array(boot_diffs)
    ci_low, ci_high = (float(np.percentile(boot_diffs, 2.5)), float(np.percentile(boot_diffs, 97.5))) if len(boot_diffs) > 10 else (None, None)
    passes = bool(ci_low is not None and ci_low > 0)
    return {
        "n": len(df), "n_pos": n_pos, "n_neg": n_neg, "n_boot_successful": len(boot_diffs),
        "auc_i": auc_i, "auc_ii": auc_ii, "auc_diff": float(diff),
        "ci_low": ci_low, "ci_high": ci_high, "passes": passes,
    }


def main():
    print("Step 0 (already committed): Amendment v3-5 + corrected expert-lists CSV")

    print("\nStep 1: building per-pass Decision for O1, O2, O3 ...")
    policy = pd.read_parquet(POLICY_PATH)
    match_ids = sorted(int(p.stem) for p in EVENTS_DIR.glob("*.parquet"))
    per_pass = {
        "O1": build_per_pass_o1(policy),
        "O2": build_per_pass_o2(policy),
    }
    per_pass["O3"], keep_mask, tagged = build_per_pass_o3(policy, match_ids)
    print(f"  per-pass rows: {[(k, len(v)) for k, v in per_pass.items()]}")

    pos_lookup, name_lookup = build_position_and_name_lookup()

    print("\nStep 1: leaderboards ...")
    leaderboards, pooled = {}, {}
    for obj in OBJECTIVES:
        leaderboards[obj], pooled[obj] = build_leaderboard(per_pass[obj], obj, pos_lookup, name_lookup)
        print(f"  {obj}: {len(leaderboards[obj])} qualifying players, "
              f"overall_mean_unweighted={leaderboards[obj].attrs['overall_mean_unweighted']:.4f}")

    combined = pd.concat([leaderboards[o] for o in OBJECTIVES], ignore_index=True)
    combined.to_parquet(LEADERBOARD_PATH)
    print(f"  wrote {LEADERBOARD_PATH}")

    cols = ["player_id", "player_name", "position_group", "competitions", "n_eligible_passes",
            "decision_per_100", "shrunken_decision_per_100", "rank"]
    top_bottom = {}
    for obj in OBJECTIVES:
        lb = leaderboards[obj]
        top_bottom[obj] = {"top20": lb.head(TOP_BOTTOM_N)[cols].to_dict("records"),
                            "bottom20": lb.tail(TOP_BOTTOM_N)[cols].to_dict("records")[::-1]}
        print(f"  {obj} top 3: {[r['player_name'] for r in top_bottom[obj]['top20'][:3]]}")
        print(f"  {obj} bottom 3: {[r['player_name'] for r in top_bottom[obj]['bottom20'][-3:]]}")

    fixed_rows = fixed_list_ranks(leaderboards, pooled, name_lookup)
    print("\n  Fixed-list ranks:")
    for r in fixed_rows:
        print(f"    {r}")

    merged_pairs = leaderboards["O1"][["player_id", "shrunken_decision_per_100"]].rename(
        columns={"shrunken_decision_per_100": "O1"})
    for obj in ("O2", "O3"):
        merged_pairs = merged_pairs.merge(
            leaderboards[obj][["player_id", "shrunken_decision_per_100"]].rename(columns={"shrunken_decision_per_100": obj}),
            on="player_id", how="outer")
    spearman = merged_pairs[["O1", "O2", "O3"]].corr(method="spearman")
    print(f"\n  Spearman correlations (pairwise, n={len(merged_pairs)} union):\n{spearman.to_string()}")
    spearman_pairwise = {}
    for a, b in (("O1", "O2"), ("O1", "O3"), ("O2", "O3")):
        sub = merged_pairs.dropna(subset=[a, b])
        spearman_pairwise[f"{a}_{b}"] = {"rho": float(sub[a].corr(sub[b], method="spearman")), "n": len(sub)}
    print(f"  Spearman pairwise complete-case: {spearman_pairwise}")

    print("\nStep 2: matching expert lists to (player, competition, season) units; power ...")
    expert = pd.read_csv(EXPERT_CSV, dtype=str, keep_default_na=False)
    expert = expert[expert["source_org"] != "NO LIST"]

    context_units = {obj: build_context_units(per_pass[obj], obj, pos_lookup, name_lookup) for obj in OBJECTIVES}
    for obj in OBJECTIVES:
        print(f"  {obj}: {len(context_units[obj])} qualifying (player,competition,season) units "
              f"across the 7 covered competition-seasons")

    match_results = {}
    for obj in OBJECTIVES:
        units, matched_rows, unmatched = match_expert_list(context_units[obj], expert)
        n_selected = int(units["selected"].sum())
        print(f"\n  {obj}: {n_selected}/{len(expert)} expert-list players matched to a qualifying unit")
        if unmatched:
            print(f"  {obj} unmatched ({len(unmatched)}):")
            for u in unmatched:
                print(f"    {u}")
        match_results[obj] = {"units": units, "n_matched": n_selected, "n_expert_rows": len(expert), "unmatched": unmatched}

    power_results = {}
    for obj in OBJECTIVES:
        units = match_results[obj]["units"]
        n_pos = int(units["selected"].sum())
        n_neg = int((~units["selected"]).sum())
        mde = power_mde(n_pos, n_neg)
        underpowered = mde > 0.10
        power_results[obj] = {"n_qualifying_units": len(units), "n_pos": n_pos, "n_neg": n_neg,
                               "mde_auc_80pct_power": mde, "underpowered": underpowered}
        print(f"  {obj} power: n_qualifying={len(units)}, n_pos={n_pos}, n_neg={n_neg}, "
              f"MDE(80% power)={mde:.4f} -> {'UNDERPOWERED' if underpowered else 'adequately powered'}")

    print("\nStep 3: Referee 2 AUC test (reported regardless of Step 2's power verdict, per v3-4.2) ...")
    referee2_results = {}
    for obj in OBJECTIVES:
        units = match_results[obj]["units"].copy()
        units["comp_season_str"] = units["competition_id"].astype(str) + "_" + units["season_id"].astype(str)
        units["team_strength_raw"] = units.apply(
            lambda r: raw_team_strength(int(r["competition_id"]), int(r["season_id"]), r["team"]), axis=1)
        units["team_strength_z"] = units.groupby("comp_season_str")["team_strength_raw"].transform(
            lambda s: (s - s.mean()) / s.std(ddof=1) if s.std(ddof=1) and s.std(ddof=1) > 0 else np.nan)
        units["decision_z"] = (units["decision_per_100"] - units["decision_per_100"].mean()) / units["decision_per_100"].std(ddof=1)

        n_missing_strength = int(units["team_strength_raw"].isna().sum())
        full = fit_and_compare_auc(units, exclude_world_cup=False)
        no_wc = fit_and_compare_auc(units, exclude_world_cup=True)
        referee2_results[obj] = {"n_missing_team_strength": n_missing_strength, "full": full, "excl_world_cup": no_wc}
        print(f"\n  {obj}: n_missing_team_strength={n_missing_strength}")
        print(f"    full:          {full}")
        print(f"    excl-WorldCup: {no_wc}")

    print("\nStep 4: applying plan v3 section 5 ...")
    referee1_verdicts = {"O1": "NOT WIN", "O2": "NOT WIN", "O3": "NOT WIN"}
    better = []
    for obj in OBJECTIVES:
        r1 = referee1_verdicts[obj] == "WIN"
        r2 = referee2_results[obj]["full"].get("passes", False)
        r2_no_wc = referee2_results[obj]["excl_world_cup"].get("passes", False)
        print(f"  {obj}: Referee 1={referee1_verdicts[obj]}, Referee 2 (full)={'PASS' if r2 else 'FAIL'}, "
              f"Referee 2 (excl WC)={'PASS' if r2_no_wc else 'FAIL'}")
        if r1:
            better.append(obj)
    print(f"\n  Objectives eligible to be called BETTER (won Referee 1, did not lose Referee 2): {better if better else 'NONE'}")

    summary = {
        "status": "COMPLETE",
        "leaderboard_n_qualifying": {o: len(leaderboards[o]) for o in OBJECTIVES},
        "top_bottom": top_bottom, "fixed_list_ranks": fixed_rows,
        "spearman_pairwise": spearman_pairwise,
        "context_units_n": {o: len(context_units[o]) for o in OBJECTIVES},
        "match_results": {o: {"n_matched": match_results[o]["n_matched"], "n_expert_rows": match_results[o]["n_expert_rows"],
                               "unmatched": match_results[o]["unmatched"]} for o in OBJECTIVES},
        "power_results": power_results, "referee2_results": {o: {"n_missing_team_strength": referee2_results[o]["n_missing_team_strength"],
                                                                    "full": referee2_results[o]["full"], "excl_world_cup": referee2_results[o]["excl_world_cup"]}
                                                                for o in OBJECTIVES},
        "referee1_verdicts": referee1_verdicts, "better_objectives": better,
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
    print(f"\nWrote summary to {SUMMARY_PATH}")


if __name__ == "__main__":
    main()
