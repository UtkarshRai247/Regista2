"""
Hand-built REML estimator for a linear model with two CROSSED random
effects (player, team context) and KNOWN per-observation residual
variance (the stage-1 standard error squared). Built because R is not
available (Amendment v2-3.2) and statsmodels' MixedLM assumes a single
homoscedastic residual variance, not per-unit known variances.

Model: y_i = X_i @ b + u_{player(i)} + v_{context(i)} + e_i
  e_i ~ N(0, se_i^2)  (known, fixed)
  u_p ~ N(0, var_player) iid across P players
  v_t ~ N(0, var_team)  iid across T team-contexts
  u, v, e mutually independent.

Marginal covariance V = D + U C U', D = diag(se_i^2), U = [Z_player, Z_context]
(n x (P+T) 0/1 indicator columns), C = blockdiag(var_player*I_P, var_team*I_T).

Each stage-1 unit belongs to exactly ONE player and ONE team context, so
Z_player'D^-1Z_player and Z_context'D^-1Z_context are diagonal, and the
cross-block Z_player'D^-1Z_context has at most one nonzero per unit. This
means A = C^-1 + U'D^-1U (used by the Woodbury identity to invert V) is a
SPARSE (P+T) x (P+T) matrix, not the dense n x n V itself -- with n=1,701
stage-1 units, P=1,232 players, T=157 team-contexts (Study B's real
design), this turns each likelihood evaluation from an O(n^3) dense solve
into a sparse solve over ~1,389 dimensions with ~5,900 nonzeros, fast
enough to run the 1,000-draw bootstrap and the 300-fit recovery test in
this task. COO's automatic summing of duplicate (row, col) entries also
makes this exactly correct for player-cluster bootstrap resamples, where
a resampled player's units (and hence their (player, context) pairs) can
appear more than once in one replicate.

Run standalone for a self-check: python src/decision_engine/reml_crossed.py
"""
import numpy as np
import pandas as pd
from scipy import sparse
from scipy.optimize import minimize
from scipy.sparse.linalg import splu


def _factorize(units: pd.DataFrame):
    player_codes, player_uniques = pd.factorize(units["player_id"])
    context_key = (units["team"].astype(str) + "||" + units["competition_id"].astype(str)
                   + "||" + units["season_id"].astype(str))
    context_codes, context_uniques = pd.factorize(context_key)
    return player_codes, len(player_uniques), context_codes, len(context_uniques)


def _build_X(units: pd.DataFrame, x_cols: list) -> np.ndarray:
    return np.column_stack([np.ones(len(units))] + [units[c].values.astype(float) for c in x_cols])


def _sparse_A(log_vars, inv_se2, player_codes, context_codes, P, T):
    var_p, var_t = np.exp(log_vars)
    d1 = np.bincount(player_codes, weights=inv_se2, minlength=P) + 1.0 / var_p
    d2 = np.bincount(context_codes, weights=inv_se2, minlength=T) + 1.0 / var_t
    diag_vals = np.concatenate([d1, d2])
    n = len(inv_se2)
    rows = np.concatenate([np.arange(P + T), player_codes, P + context_codes])
    cols = np.concatenate([np.arange(P + T), P + context_codes, player_codes])
    vals = np.concatenate([diag_vals, inv_se2, inv_se2])
    A = sparse.coo_matrix((vals, (rows, cols)), shape=(P + T, P + T)).tocsc()
    return A, var_p, var_t


def _neg2_reml(log_vars, y, X, inv_se2, log_se2_sum, player_codes, context_codes, P, T):
    n = len(y)
    A, var_p, var_t = _sparse_A(log_vars, inv_se2, player_codes, context_codes, P, T)
    lu = splu(A)
    logdet_A = float(np.sum(np.log(np.abs(lu.L.diagonal()))) + np.sum(np.log(np.abs(lu.U.diagonal()))))
    logdet_C = P * np.log(var_p) + T * np.log(var_t)

    XY = np.column_stack([X, y])
    Dinv_XY = inv_se2[:, None] * XY
    rhs = np.zeros((P + T, XY.shape[1]))
    np.add.at(rhs, player_codes, Dinv_XY)
    np.add.at(rhs, P + context_codes, Dinv_XY)
    Z = lu.solve(rhs)
    UZ = Z[player_codes] + Z[P + context_codes]
    Vinv_XY = Dinv_XY - inv_se2[:, None] * UZ
    Vinv_X, Vinv_y = Vinv_XY[:, :-1], Vinv_XY[:, -1]

    XtVinvX = X.T @ Vinv_X
    XtVinvy = X.T @ Vinv_y
    b_hat = np.linalg.solve(XtVinvX, XtVinvy)
    rss = float(y @ Vinv_y - b_hat @ XtVinvy)
    _, logdet_XtVinvX = np.linalg.slogdet(XtVinvX)

    neg2ll = log_se2_sum + logdet_C + logdet_A + logdet_XtVinvX + rss
    return neg2ll, b_hat, var_p, var_t


def fit_reml(units: pd.DataFrame, x_cols: list, y_col: str = "mean_decision",
             se_col: str = "se", x0=None) -> dict:
    """units: one row per stage-1 unit. Must have player_id, team,
    competition_id, season_id, y_col, se_col, and every column in x_cols.
    Duplicate rows (bootstrap resamples) are handled correctly."""
    y = units[y_col].values.astype(float)
    se2 = units[se_col].values.astype(float) ** 2
    inv_se2 = 1.0 / se2
    log_se2_sum = float(np.sum(np.log(se2)))
    X = _build_X(units, x_cols)
    player_codes, P, context_codes, T = _factorize(units)

    if x0 is None:
        start = max(float(np.var(y)), 1e-8) / 3.0
        x0 = np.log([start, start])

    def obj(log_vars):
        neg2ll, _, _, _ = _neg2_reml(log_vars, y, X, inv_se2, log_se2_sum, player_codes, context_codes, P, T)
        return neg2ll

    res = minimize(obj, x0, method="Nelder-Mead",
                    options={"xatol": 1e-6, "fatol": 1e-6, "maxiter": 2000, "maxfev": 2000})
    neg2ll, b_hat, var_p, var_t = _neg2_reml(res.x, y, X, inv_se2, log_se2_sum,
                                              player_codes, context_codes, P, T)
    S = var_p / (var_p + var_t)
    return {
        "converged": bool(res.success), "var_player": float(var_p), "var_team": float(var_t),
        "S": float(S), "b": b_hat.tolist(), "x_cols": ["intercept"] + list(x_cols),
        "n_units": len(units), "n_players": P, "n_contexts": T, "neg2ll": float(neg2ll),
    }


def bootstrap_by_player(units: pd.DataFrame, x_cols: list, n_boot: int, seed: int,
                         y_col: str = "mean_decision", se_col: str = "se") -> np.ndarray:
    """Cluster bootstrap resampling players (Amendment v2-5.1 fix).

    Task 07's original version kept the real player_id on every resampled
    copy, so a player drawn twice was pooled by _factorize into ONE
    inflated group instead of two independent draws of the player-level
    random effect -- inflating var_player and biasing S's interval
    upward. Fix: each of the P drawn *slots* gets a synthetic id
    (f"{player_id}__{slot}"), so two draws of the same real player are
    always treated as two distinct players. Team context ids are left
    untouched, per the brief."""
    rng = np.random.default_rng(seed)
    players = units["player_id"].unique()
    P = len(players)
    groups = units.groupby("player_id").indices
    s_hats = np.empty(n_boot)
    for b in range(n_boot):
        drawn = rng.choice(players, size=P, replace=True)
        parts = []
        for slot, p in enumerate(drawn):
            block = units.iloc[groups[p]].copy()
            block["player_id"] = f"{p}__{slot}"
            parts.append(block)
        rep = pd.concat(parts, ignore_index=True)
        fit = fit_reml(rep, x_cols=x_cols, y_col=y_col, se_col=se_col)
        s_hats[b] = fit["S"]
    return s_hats


def simulate_units(units: pd.DataFrame, var_player: float, var_team: float, seed: int) -> pd.DataFrame:
    """Simulate y (mean_decision) from known variance components on the
    REAL design (real players/contexts/SEs). True fixed effects are 0 --
    only the variance components are the recovery test's target, and GLS
    profiling for b is exact given V regardless of b's true value."""
    rng = np.random.default_rng(seed)
    player_codes, P, context_codes, T = _factorize(units)
    u = rng.normal(0.0, np.sqrt(var_player), size=P) if var_player > 0 else np.zeros(P)
    v = rng.normal(0.0, np.sqrt(var_team), size=T) if var_team > 0 else np.zeros(T)
    se = units["se"].values.astype(float)
    e = rng.normal(0.0, se)
    y_sim = u[player_codes] + v[context_codes] + e
    out = units.copy()
    out["mean_decision"] = y_sim
    return out


if __name__ == "__main__":
    # Self-check: sparse Woodbury REML vs. brute-force dense REML on a
    # tiny synthetic design, before trusting this on the real 1,701-unit
    # Study B design.
    rng = np.random.default_rng(0)
    n_players, n_contexts, n = 8, 5, 30
    player_ids = rng.integers(0, n_players, size=n)
    teams = rng.integers(0, n_contexts, size=n)
    units = pd.DataFrame({
        "player_id": player_ids, "team": teams, "competition_id": 1, "season_id": 1,
        "se": rng.uniform(0.05, 0.2, size=n),
        "x1": rng.normal(size=n),
    })
    true_var_p, true_var_t = 0.02, 0.01
    units = simulate_units(units, true_var_p, true_var_t, seed=1)

    fit_sparse = fit_reml(units, x_cols=["x1"])

    # brute-force dense REML for comparison
    y = units["mean_decision"].values
    X = _build_X(units, ["x1"])
    se2 = units["se"].values ** 2
    player_codes, P, context_codes, T = _factorize(units)
    Zu = np.zeros((n, P)); Zu[np.arange(n), player_codes] = 1
    Zv = np.zeros((n, T)); Zv[np.arange(n), context_codes] = 1

    def dense_neg2ll(log_vars):
        var_p, var_t = np.exp(log_vars)
        V = np.diag(se2) + var_p * Zu @ Zu.T + var_t * Zv @ Zv.T
        Vinv = np.linalg.inv(V)
        _, logdet_V = np.linalg.slogdet(V)
        XtVinvX = X.T @ Vinv @ X
        b = np.linalg.solve(XtVinvX, X.T @ Vinv @ y)
        resid = y - X @ b
        rss = resid @ Vinv @ resid
        _, logdet_XtVinvX = np.linalg.slogdet(XtVinvX)
        return logdet_V + logdet_XtVinvX + rss

    dense_res = minimize(dense_neg2ll, np.log([0.02, 0.02]), method="Nelder-Mead")
    dense_var_p, dense_var_t = np.exp(dense_res.x)

    print("sparse Woodbury fit:", fit_sparse["var_player"], fit_sparse["var_team"])
    print("dense brute-force fit:", dense_var_p, dense_var_t)
    print("true:", true_var_p, true_var_t)
    assert abs(fit_sparse["var_player"] - dense_var_p) < 1e-4
    assert abs(fit_sparse["var_team"] - dense_var_t) < 1e-4
    print("OK: sparse Woodbury REML matches brute-force dense REML.")

    # Unit test (Amendment v2-5.1): a player drawn twice in
    # bootstrap_by_player must be treated as two distinct players, not
    # pooled into one inflated group under their shared real player_id.
    test_units = pd.DataFrame({
        "player_id": [1, 1, 2, 2, 3, 3], "team": [10, 11, 12, 13, 14, 15],
        "competition_id": 1, "season_id": 1, "se": 0.1,
        "mean_decision": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    })

    class _FixedChoice:
        """Forces np.random.default_rng(...).choice to always return
        player 1 twice and player 2 once, regardless of seed, so the
        bootstrap draw is deterministic for this test."""
        def choice(self, a, size, replace):
            return np.array([1, 1, 2])

    drawn = _FixedChoice().choice(test_units["player_id"].unique(), size=3, replace=True)
    groups = test_units.groupby("player_id").indices
    buggy_parts = [test_units.iloc[groups[p]] for p in drawn]
    buggy_rep = pd.concat(buggy_parts, ignore_index=True)
    _, n_players_buggy, _, _ = _factorize(buggy_rep)

    fixed_parts = []
    for slot, p in enumerate(drawn):
        block = test_units.iloc[groups[p]].copy()
        block["player_id"] = f"{p}__{slot}"
        fixed_parts.append(block)
    fixed_rep = pd.concat(fixed_parts, ignore_index=True)
    _, n_players_fixed, _, _ = _factorize(fixed_rep)

    print(f"\nbootstrap fresh-id test: buggy grouping -> {n_players_buggy} distinct players "
          f"(player 1 drawn twice collapses to 1); fixed grouping -> {n_players_fixed} distinct players "
          "(player 1's two draws counted separately)")
    assert n_players_buggy == 2, "expected the buggy (pre-fix) path to collapse player 1's two draws into one group"
    assert n_players_fixed == 3, "expected the fixed path to keep player 1's two draws as two distinct groups"
    print("OK: bootstrap_by_player's fresh-id fix is verified (v2-5.1).")
