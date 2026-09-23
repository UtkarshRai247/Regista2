"""
Task 09 — Step 0 (fold file) + PART 1: Cross-fitting (Amendment v2-4).

Retrains pass-success, possession-value, and behavior-policy 5 times
each (one fold held out per retrain), using the FROZEN features and
hyperparameters of commit 9db72ef -- only the training data changes.
Every match ends up scored exactly once, by a model that never saw it.

Performance note: the per-match Python-loop feature-building steps
(possession-value's action-state rows at horizon=10, and the EV
feature-construction geometry) are fold-independent -- computed ONCE
here and reused across all 5 folds, per the plan's timing analysis.

Run: python src/decision_engine/task09_crossfit.py
"""
import json
import time
import warnings

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import roc_auc_score

from decompose import DATA_DIR, EVENTS_DIR, compute_realized_values, match_competition_lookup
from pass_success import FEATURES as PS_FEATURES, prep_X
from pitch_direction import normalize_xy, team_period_directions
from policy import softmax_per_group
from possession_value import FEATURES as PV_FEATURES, PATTERN_CODE
from reml_crossed import fit_reml
from task04_situation_context import load_matches_meta
from task05_study_a_discovery import join_ev, recover_raw_positions
from task06_study_a_confirmation import (
    bootstrap_g_stats as _bootstrap_g_stats,
    build_available_types_table_with_mean, bootstrap_delta, cand_mask, confirmation_match_ids, parse_candidates,
)

warnings.filterwarnings("ignore")

SCORED_PATH = DATA_DIR / "processed" / "options_scored.parquet"
PV_PARTS_DIR = DATA_DIR / "processed" / "possession_value_parts"
TYPED_PATH = DATA_DIR / "processed" / "options_typed.parquet"
PASSES_PATH = DATA_DIR / "processed" / "passes_situation.parquet"
STUDY_B_UNITS_PATH = DATA_DIR / "processed" / "study_b_units.parquet"
CV_FOLDS_PATH = DATA_DIR / "splits" / "cv_folds.csv"
SUMMARY_PATH = DATA_DIR / "task09_crossfit.json"
CROSSFIT_OPTIONS_PATH = DATA_DIR / "processed" / "crossfit_options.parquet"
CROSSFIT_PASSES_PATH = DATA_DIR / "processed" / "crossfit_passes.parquet"

CV_SEED = 20260920
N_FOLDS = 5
TIME_BUDGET_SECONDS = 4 * 3600
ROBUST_CANDIDATES = [
    {"zone": "middle", "under_pressure": False, "game_state": "leading", "option_type": "lateral_medium"},
    {"zone": "middle", "under_pressure": False, "game_state": "level", "option_type": "lateral_medium"},
    {"zone": "middle", "under_pressure": False, "game_state": "trailing", "option_type": "lateral_medium"},
]


def make_ps_model():
    return xgb.XGBClassifier(n_estimators=200, max_depth=4, learning_rate=0.05,
                              subsample=0.8, colsample_bytree=0.8, random_state=42, eval_metric="logloss")


def make_pv_model():
    return xgb.XGBClassifier(n_estimators=300, max_depth=5, learning_rate=0.05,
                              subsample=0.8, colsample_bytree=0.8, random_state=42, eval_metric="logloss")


def make_policy_model():
    return xgb.XGBClassifier(n_estimators=200, max_depth=4, learning_rate=0.05,
                              subsample=0.8, colsample_bytree=0.8, random_state=42, eval_metric="logloss")


def build_cv_folds(matches_meta: dict) -> pd.DataFrame:
    rng = np.random.default_rng(CV_SEED)
    by_comp = {}
    for mid, m in matches_meta.items():
        by_comp.setdefault((m["competition_id"], m["season_id"]), []).append(mid)
    rows = []
    for (comp_id, season_id), mids in sorted(by_comp.items()):
        mids = sorted(mids)
        n = len(mids)
        perm = rng.permutation(n)
        fold_of = np.empty(n, dtype=int)
        for rank, idx in enumerate(perm):
            fold_of[idx] = rank % N_FOLDS
        for mid, fold in zip(mids, fold_of):
            rows.append({"match_id": mid, "competition_id": comp_id, "season_id": season_id, "fold": int(fold)})
    return pd.DataFrame(rows)


def build_ev_context(match_ids: list) -> tuple:
    """Fold-independent: direction lookup + (time_remaining, score_diff)
    per event, exactly as expected_value.py's main() builds them."""
    directions_by_match, ev_context = {}, {}
    for i, mid in enumerate(match_ids):
        ev = pd.read_parquet(EVENTS_DIR / f"{mid}.parquet")
        dirs, _, _ = team_period_directions(ev)
        directions_by_match[mid] = dirs
        ev = ev.sort_values("index").reset_index(drop=True)
        ev["t"] = ev["minute"] * 60 + ev["second"]
        period_end = ev.groupby("period")["t"].transform("max")
        ev["time_remaining_period"] = period_end - ev["t"]
        teams = ev["team"].dropna().unique().tolist()
        score = {t: 0 for t in teams}
        is_goal = ((ev["type"] == "Shot") & (ev["shot_outcome"] == "Goal")) | (ev["type"] == "Own Goal Against")
        score_diff_col = []
        for j in range(len(ev)):
            row = ev.iloc[j]
            opp = [t for t in teams if t != row["team"]]
            opp = opp[0] if opp else None
            score_diff_col.append(score.get(row["team"], 0) - score.get(opp, 0) if opp else 0)
            if is_goal.iloc[j]:
                scorer = row["team"]
                if row["type"] == "Own Goal Against":
                    scorer = opp
                if scorer in score:
                    score[scorer] += 1
        ev["score_diff"] = score_diff_col
        for _, r in ev.iterrows():
            ev_context[(mid, r["id"])] = (r["time_remaining_period"], r["score_diff"])
        if (i + 1) % 50 == 0:
            print(f"  ev_context: {i + 1}/{len(match_ids)} matches")
    return directions_by_match, ev_context


def build_success_turnover_X(base: pd.DataFrame, directions_by_match: dict, ev_context: dict):
    """Fold-independent EV feature matrices, exactly expected_value.py's construction."""
    rows_success, rows_turnover = [], []
    for _, r in base.iterrows():
        mid, eid, team, period = r["match_id"], r["event_id"], r["team"], r["period"]
        direction = directions_by_match[mid].get((team, period), 1)
        time_remaining, score_diff = ev_context.get((mid, eid), (np.nan, 0))
        ax, ay = normalize_xy(r["candidate_x"], r["candidate_y"], direction)
        px, py = normalize_xy(r["passer_x"], r["passer_y"], direction)
        rows_success.append({"ball_x": ax, "ball_y": ay, "prev_x": px, "prev_y": py,
                              "time_remaining_period": time_remaining, "score_diff": score_diff,
                              "play_pattern_code": PATTERN_CODE["Regular Play"]})
        opp_direction = -direction
        tx, ty = normalize_xy(r["candidate_x"], r["candidate_y"], opp_direction)
        px2, py2 = normalize_xy(r["passer_x"], r["passer_y"], opp_direction)
        rows_turnover.append({"ball_x": tx, "ball_y": ty, "prev_x": px2, "prev_y": py2,
                               "time_remaining_period": time_remaining, "score_diff": -score_diff,
                               "play_pattern_code": PATTERN_CODE["From Counter"]})
    X_success = pd.DataFrame(rows_success)[PV_FEATURES]
    X_turnover = pd.DataFrame(rows_turnover)[PV_FEATURES]
    return X_success, X_turnover


def run_folds(base, folds_df, X_ps_all, X_policy_all, X_success_all, X_turnover_all, pv_parts_df):
    options_out, pass_out = [], []
    pv_oof = []
    ps_oof_pred, ps_oof_true = [], []
    policy_oof_records = []

    for fold_id in range(N_FOLDS):
        t0 = time.time()
        fold_matches = set(folds_df.loc[folds_df["fold"] == fold_id, "match_id"])
        train_mask = ~base["match_id"].isin(fold_matches)
        test_mask = base["match_id"].isin(fold_matches)

        chosen_train_mask = train_mask & base["chosen"]
        ps_model = make_ps_model()
        ps_model.fit(X_ps_all[chosen_train_mask.values], base.loc[chosen_train_mask, "pass_complete"].astype(int))
        p_success_test = ps_model.predict_proba(X_ps_all[test_mask.values])[:, 1]
        chosen_test_mask = test_mask & base["chosen"]
        ps_oof_pred.append(ps_model.predict_proba(X_ps_all[chosen_test_mask.values])[:, 1])
        ps_oof_true.append(base.loc[chosen_test_mask, "pass_complete"].astype(int).values)

        pv_train_rows = pv_parts_df[~pv_parts_df["match_id"].isin(fold_matches)]
        pv_test_rows = pv_parts_df[pv_parts_df["match_id"].isin(fold_matches)]
        pv_model = make_pv_model()
        pv_model.fit(pv_train_rows[PV_FEATURES], pv_train_rows["label"])
        v_success_test = pv_model.predict_proba(X_success_all[test_mask.values])[:, 1]
        v_turnover_test = -pv_model.predict_proba(X_turnover_all[test_mask.values])[:, 1]
        ev_test = p_success_test * v_success_test + (1 - p_success_test) * v_turnover_test
        pv_pred_test = pv_model.predict_proba(pv_test_rows[PV_FEATURES])[:, 1]
        pv_oof.append(pd.DataFrame({"label": pv_test_rows["label"].values, "pred": pv_pred_test}))

        policy_model = make_policy_model()
        policy_model.fit(X_policy_all[train_mask.values], base.loc[train_mask, "chosen"].astype(int))
        raw_score_test = policy_model.predict_proba(X_policy_all[test_mask.values])[:, 1]
        event_ids_test = base.loc[test_mask, "event_id"].values
        policy_prob_test = softmax_per_group(raw_score_test, event_ids_test)

        out = base.loc[test_mask, ["match_id", "event_id", "team", "period",
                                    "candidate_x", "candidate_y", "chosen", "pass_complete"]].copy()
        out["p_success"] = p_success_test
        out["ev"] = ev_test
        out["policy_probability"] = policy_prob_test
        options_out.append(out)

        ranked = out.sort_values(["event_id", "policy_probability"], ascending=[True, False]).copy()
        ranked["rank"] = ranked.groupby("event_id").cumcount()
        chosen_ranks = ranked.loc[ranked["chosen"], ["event_id", "rank"]]
        policy_oof_records.append(chosen_ranks)

        realized_frames = [compute_realized_values(mid, pv_model) for mid in sorted(fold_matches)]
        realized = pd.concat(realized_frames, ignore_index=True)

        out2 = out.copy()
        out2["ev_x_prob"] = out2["ev"] * out2["policy_probability"]
        grp = out2.groupby("event_id")
        per_pass = grp.agg(
            match_id=("match_id", "first"), team=("team", "first"),
            ev_chosen=("ev", lambda s: s[out2.loc[s.index, "chosen"]].iloc[0]),
            policy_weighted_ev=("ev_x_prob", "sum"),
        ).reset_index()
        per_pass["decision"] = per_pass["ev_chosen"] - per_pass["policy_weighted_ev"]
        per_pass = per_pass.merge(realized, on="event_id", how="left")
        per_pass["execution"] = per_pass["realized_value"] - per_pass["ev_chosen"]
        pass_out.append(per_pass)

        print(f"  fold {fold_id}: {len(fold_matches)} matches, {test_mask.sum()} option rows, "
              f"{time.time() - t0:.1f}s")

    options_df = pd.concat(options_out, ignore_index=True)
    pass_df = pd.concat(pass_out, ignore_index=True)
    pv_oof_df = pd.concat(pv_oof, ignore_index=True)
    ps_oof_pred = np.concatenate(ps_oof_pred)
    ps_oof_true = np.concatenate(ps_oof_true)
    policy_oof_df = pd.concat(policy_oof_records, ignore_index=True)
    return options_df, pass_df, pv_oof_df, ps_oof_pred, ps_oof_true, policy_oof_df


def report_auc_calibration(options_df, pv_oof_df, ps_oof_pred, ps_oof_true, policy_oof_df):
    in_sample = {
        "pass_success": json.loads((DATA_DIR / "pass_success_summary.json").read_text())["auc"],
        "possession_value": json.loads((DATA_DIR / "possession_value_summary.json").read_text())["auc"],
        "policy_top1": json.loads((DATA_DIR / "policy_summary.json").read_text())["top1_accuracy"],
        "policy_top3": json.loads((DATA_DIR / "policy_summary.json").read_text())["top3_accuracy"],
    }
    oof = {
        "pass_success_auc": float(roc_auc_score(ps_oof_true, ps_oof_pred)),
        "possession_value_auc": float(roc_auc_score(pv_oof_df["label"], pv_oof_df["pred"])),
        "policy_top1_accuracy": float((policy_oof_df["rank"] == 0).mean()),
        "policy_top3_accuracy": float((policy_oof_df["rank"] < 3).mean()),
    }
    print(json.dumps({"in_sample": in_sample, "out_of_fold": oof}, indent=2))
    return {"in_sample": in_sample, "out_of_fold": oof}


def build_confirmation_g_table(options_df: pd.DataFrame, confirmation_ids: list):
    typed = pd.read_parquet(TYPED_PATH, filters=[("match_id", "in", confirmation_ids)])
    typed = recover_raw_positions(typed)
    cf_ev = options_df[options_df["match_id"].isin(confirmation_ids)][
        ["match_id", "event_id", "team", "period", "candidate_x", "candidate_y", "chosen", "ev"]]
    opt, join_report = join_ev(typed, cf_ev)
    print(json.dumps(join_report, indent=2))
    if join_report["match_rate"] != 1.0 or join_report["n_group_size_mismatches"]:
        raise RuntimeError(f"cross-fitted EV join failed on confirmation half: {join_report}")

    passes = pd.read_parquet(PASSES_PATH, filters=[("match_id", "in", confirmation_ids)])
    cell_info = passes[["match_id", "event_id", "zone", "under_pressure", "game_state",
                         "team", "competition_id", "season_id", "n_visible_players"]]
    opt = opt.drop(columns=["team"]).merge(cell_info[["match_id", "event_id", "team"]],
                                            on=["match_id", "event_id"])
    avail = build_available_types_table_with_mean(opt, cell_info)
    g_table = avail[avail["option_type"] != avail["j"]].copy()
    g_table["g"] = g_table["ev_star"] - g_table["ev_star_j"]
    g_table["g_mean"] = g_table["ev_mean"] - g_table["ev_mean_j"]
    return opt, avail, g_table, cell_info, join_report


def step4(options_df, pass_df, candidates, confirmation_ids):
    opt, avail, g_table, cell_info, join_report = build_confirmation_g_table(options_df, confirmation_ids)

    rows = []
    for cand in candidates:
        sub = g_table[cand_mask(g_table, cand)]
        stats = _bootstrap_g_stats(sub, confirmation_ids)
        n_total = len(sub)

        ph1_input = sub.rename(columns={"g": "g_max_tmp", "g_mean": "g"})
        ph1 = _bootstrap_g_stats(ph1_input, confirmation_ids)

        matched = sub[sub["n_options"] == sub["n_options_j"]]
        n_matched = len(matched)
        ph2 = _bootstrap_g_stats(matched, confirmation_ids)
        ph2_share = n_matched / n_total if n_total else None

        rows.append({**cand, "G": stats["G"], "ci_low": stats["ci_low"], "ci_high": stats["ci_high"],
                     "P": stats["P"], "L": stats["L"], "n_passes": stats["n_passes"], "n_matches": stats["n_matches"],
                     "ph1_G": ph1["G"], "ph1_ci_low": ph1["ci_low"], "ph1_ci_high": ph1["ci_high"],
                     "ph2_G": ph2["G"], "ph2_ci_low": ph2["ci_low"], "ph2_ci_high": ph2["ci_high"],
                     "ph2_n_passes": n_matched, "ph2_share_retained": ph2_share})
    step1_df = pd.DataFrame(rows)

    ev_chosen = opt.loc[opt["chosen"], ["match_id", "event_id", "option_type"]].rename(
        columns={"option_type": "chosen_type"})
    exec_df = pass_df[pass_df["match_id"].isin(confirmation_ids)][
        ["match_id", "event_id", "ev_chosen", "execution"]].rename(columns={"ev_chosen": "ev"})
    exec_df = exec_df.merge(ev_chosen, on=["match_id", "event_id"])
    ps_full = options_df[options_df["chosen"] & options_df["match_id"].isin(confirmation_ids)][
        ["match_id", "event_id", "p_success", "pass_complete"]]
    exec_df = exec_df.merge(ps_full, on=["match_id", "event_id"])
    exec_df = exec_df.merge(cell_info, on=["match_id", "event_id"])

    gate_d_rows = []
    for cand in candidates:
        z, p, gs, k = cand["zone"], cand["under_pressure"], cand["game_state"], cand["option_type"]
        cell_df = exec_df[(exec_df["zone"] == z) & (exec_df["under_pressure"] == p) & (exec_df["game_state"] == gs)]
        k_df = cell_df[cell_df["chosen_type"] == k]
        ref_df = cell_df[cell_df["chosen_type"] != k]
        bias_k = float(k_df["execution"].mean())
        bias_ref = float(ref_df["execution"].mean())
        delta = bias_ref - bias_k
        ci_low, ci_high = bootstrap_delta(k_df, ref_df, confirmation_ids)
        comp_bias_k = float((k_df["pass_complete"].astype(float) - k_df["p_success"]).mean())
        comp_bias_ref = float((ref_df["pass_complete"].astype(float) - ref_df["p_success"]).mean())
        comp_relative_pp = (comp_bias_ref - comp_bias_k) * 100
        row_g = step1_df[cand_mask(step1_df, cand)].iloc[0]
        gate_pass = bool(ci_high < row_g["G"]) if row_g["G"] is not None else None
        gate_d_rows.append({**cand, "confirmation_G": row_g["G"], "bias_k": bias_k, "bias_ref": bias_ref,
                             "delta": delta, "delta_ci_low": float(ci_low), "delta_ci_high": float(ci_high),
                             "completion_calibration_relative_pp": comp_relative_pp,
                             "gate_d_pass": gate_pass, "n_k": len(k_df), "n_ref": len(ref_df)})
    gate_d_df = pd.DataFrame(gate_d_rows)

    return step1_df, gate_d_df


def apply_v243(step1_df, gate_d_df, robust_candidates):
    verdicts = []
    for cand in robust_candidates:
        row = step1_df[cand_mask(step1_df, cand)].iloc[0]
        gd_row = gate_d_df[cand_mask(gate_d_df, cand)].iloc[0]
        g_ok = (row["G"] is not None) and (row["G"] > 0) and (row["ci_low"] is not None) and (row["ci_low"] > 0)
        l_ok = (row["L"] is not None) and (row["L"] >= 0.5)
        gate_ok = bool(gd_row["gate_d_pass"])
        ph1_ok = (row["ph1_G"] is not None) and (row["ph1_G"] > 0) and (row["ph1_ci_low"] is not None) and (row["ph1_ci_low"] > 0)
        ph2_ok = (row["ph2_G"] is not None) and (row["ph2_G"] > 0) and (row["ph2_ci_low"] is not None) and (row["ph2_ci_low"] > 0)
        stays_robust = bool(g_ok and l_ok and gate_ok and ph1_ok and ph2_ok)
        verdicts.append({**cand, "G_positive_ci_excl_zero": g_ok, "L_ge_0.5": l_ok, "gate_d_pass": gate_ok,
                          "ph1_positive_ci_excl_zero": ph1_ok, "ph2_positive_ci_excl_zero": ph2_ok,
                          "stays_robust_under_crossfit": stays_robust})
    return pd.DataFrame(verdicts)


def step5_secondary(pass_df):
    print("Part 1 Step 5: cross-fitted point estimates for S (Study B) and Study C choice share ...")
    units = pd.read_parquet(STUDY_B_UNITS_PATH)
    comp_lookup = match_competition_lookup()
    pd_full = pass_df.copy()
    pd_full["competition_id"] = pd_full["match_id"].map(lambda m: comp_lookup.get(m, (None, None))[0])
    pd_full["season_id"] = pd_full["match_id"].map(lambda m: comp_lookup.get(m, (None, None))[1])
    # pass_df already carries its own "team" column (per_pass agg's team=("team","first"));
    # only player_id is missing, so pull just that to avoid a team/team_x,team_y collision.
    passes_situation = pd.read_parquet(PASSES_PATH, columns=["match_id", "event_id", "player_id"])
    pd_full = pd_full.merge(passes_situation, on=["match_id", "event_id"])

    unit_keys = units[["player_id", "team", "competition_id", "season_id"]]
    merged = pd_full.merge(unit_keys, on=["player_id", "team", "competition_id", "season_id"])
    unit_means = merged.groupby(["player_id", "team", "competition_id", "season_id"])["decision"] \
        .mean().reset_index().rename(columns={"decision": "mean_decision"})
    cf_units = units.drop(columns=["mean_decision"]).merge(
        unit_means, on=["player_id", "team", "competition_id", "season_id"], how="left")
    cf_units = cf_units.dropna(subset=["mean_decision"])
    fit_cf = fit_reml(cf_units, x_cols=["share_defensive", "share_final", "share_pressure"])
    print(f"  Cross-fitted S (point estimate): {fit_cf['S']}")

    metrics = pd.read_parquet(DATA_DIR / "processed" / "player_season_metrics.parquet")
    qualifying = metrics[metrics["n_eligible_passes"] >= 200][["player_id", "competition_id", "season_id"]]
    per_pass_138 = pd_full.merge(qualifying, on=["player_id", "competition_id", "season_id"])
    unit_stats = per_pass_138.groupby(["player_id", "competition_id", "season_id"]).agg(
        mean_decision=("decision", "mean"), mean_execution=("execution", "mean")).reset_index()
    var_dec = float(unit_stats["mean_decision"].var(ddof=1))
    var_exe = float(unit_stats["mean_execution"].var(ddof=1))
    choice_share_raw_cf = var_dec / (var_dec + var_exe)
    print(f"  Cross-fitted Study C choice share (raw/uncorrected): {choice_share_raw_cf}")

    # Split-half-corrected point estimate too (v2-4.4: "point estimate ...
    # no bootstrap required" -- the primary Task 08 number is the
    # split-half-corrected median, not the raw share, so that's the
    # comparable quantity here; only the outer bootstrap-of-units layer
    # is skipped, not the split-half correction itself).
    from task08_study_c import one_split
    grouped = {}
    for (pid, cid, sid), g in per_pass_138.groupby(["player_id", "competition_id", "season_id"]):
        grouped[(pid, cid, sid)] = (g["decision"].values, g["execution"].values)
    keys = list(grouped.keys())
    rng = np.random.default_rng(20260920)
    splits = [one_split(grouped, keys, rng) for _ in range(100)]
    choice_share_corrected_cf = float(np.median([s["choice_share"] for s in splits]))
    print(f"  Cross-fitted Study C choice share (split-half corrected, median of 100 splits, no bootstrap): "
          f"{choice_share_corrected_cf}")

    return {"study_b_S_crossfit": fit_cf["S"], "study_b_var_player_crossfit": fit_cf["var_player"],
            "study_b_var_team_crossfit": fit_cf["var_team"],
            "study_c_choice_share_crossfit_raw": choice_share_raw_cf,
            "study_c_choice_share_crossfit_corrected": choice_share_corrected_cf,
            "n_units_study_b": len(cf_units), "n_units_study_c": len(unit_stats)}


def main():
    t_start = time.time()
    matches_meta = load_matches_meta()
    print("Step 0: building cv_folds.csv ...")
    folds_df = build_cv_folds(matches_meta)
    CV_FOLDS_PATH.parent.mkdir(parents=True, exist_ok=True)
    folds_df.to_csv(CV_FOLDS_PATH, index=False)
    print(folds_df.groupby(["competition_id", "season_id", "fold"]).size().unstack(fill_value=0).to_string())
    print(f"Total matches: {len(folds_df)}")

    print("\nPART 1 Step 1-2: loading base data and building fold-independent feature matrices ...")
    base = pd.read_parquet(SCORED_PATH).drop(columns=["p_success"])
    match_ids = sorted(base["match_id"].unique())
    X_ps_all = prep_X(base)
    X_policy_all = X_ps_all
    pv_parts = list(PV_PARTS_DIR.glob("*.parquet"))
    pv_parts_df = pd.concat((pd.read_parquet(p) for p in pv_parts), ignore_index=True)
    print(f"  possession-value training rows available: {len(pv_parts_df)}")

    print("  building EV feature matrices (fold-independent, one pass over all matches) ...")
    t0 = time.time()
    directions_by_match, ev_context = build_ev_context(match_ids)
    print(f"  ev_context build time: {time.time() - t0:.1f}s")
    t0 = time.time()
    X_success_all, X_turnover_all = build_success_turnover_X(base, directions_by_match, ev_context)
    print(f"  success/turnover X build time: {time.time() - t0:.1f}s")

    print("\nPART 1 Step 2: retraining and scoring 5 folds ...")
    options_df, pass_df, pv_oof_df, ps_oof_pred, ps_oof_true, policy_oof_df = run_folds(
        base, folds_df, X_ps_all, X_policy_all, X_success_all, X_turnover_all, pv_parts_df)
    print(f"Cross-fitted options rows: {len(options_df)} (expected 1,237,611)")
    print(f"Cross-fitted pass rows: {len(pass_df)} (expected 171,618)")
    options_df.to_parquet(CROSSFIT_OPTIONS_PATH)
    pass_df.to_parquet(CROSSFIT_PASSES_PATH)

    print("\nPART 1 Step 3: AUC/calibration, out-of-fold vs in-sample ...")
    auc_report = report_auc_calibration(options_df, pv_oof_df, ps_oof_pred, ps_oof_true, policy_oof_df)

    elapsed = time.time() - t_start
    print(f"\nElapsed before Step 4: {elapsed / 60:.1f} minutes")
    projected_total = elapsed * 3  # rough: step4 + step5 + Part 2 remaining, conservative multiplier
    if projected_total > TIME_BUDGET_SECONDS:
        print(f"STOPPING after Part 1 Step 3/4 checkpoint: projected total runtime "
              f"({projected_total / 3600:.1f}h) exceeds the 4-hour budget.")
        summary = {"status": "PARTIAL", "reason": "time budget", "elapsed_seconds": elapsed,
                   "auc_report": auc_report}
        SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
        return

    print("\nPART 1 Step 4: recomputing G/CI/P/L/GateD/PH1/PH2 for the 7 CONFIRMED candidates ...")
    confirmation_ids = confirmation_match_ids()
    candidates = parse_candidates()
    step1_df, gate_d_df = step4(options_df, pass_df, candidates, confirmation_ids)
    print(step1_df.to_string())
    print(gate_d_df.to_string())

    print("\nApplying v2-4.3's decision rule to the 3 ROBUST candidates ...")
    verdicts = apply_v243(step1_df, gate_d_df, ROBUST_CANDIDATES)
    print(verdicts.to_string())

    print(f"\nElapsed after Step 4: {(time.time() - t_start) / 60:.1f} minutes")

    step5_results = step5_secondary(pass_df)

    summary = {
        "status": "COMPLETE", "n_folds": N_FOLDS, "elapsed_seconds_total": time.time() - t_start,
        "auc_calibration": auc_report,
        "step4_stats": step1_df.to_dict("records"), "step4_gate_d": gate_d_df.to_dict("records"),
        "v2_4_3_verdicts": verdicts.to_dict("records"), "step5_secondary": step5_results,
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
    print(f"\nWrote summary to {SUMMARY_PATH}")


if __name__ == "__main__":
    main()
