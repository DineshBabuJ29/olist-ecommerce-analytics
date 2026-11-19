"""
STEP 5 - Statistical testing: is the late-delivery effect real or just noise?

Hypotheses (delivered orders with a review):
  H1  Late orders receive lower review scores than on-time orders.
      Review scores are ordinal (1-5) and not normally distributed, so the test is
      the Mann-Whitney U test (non-parametric), not a t-test.
  H2  The share of negative (1-2 star) reviews depends on delivery status.
      Chi-square test of independence on a 2x2 table + relative risk.
  H3  Longer delivery time correlates with lower review score.
      Spearman rank correlation (works for ordinal data).
  Plus a bootstrap 95% confidence interval for the difference in mean review score.

Output: outputs/statistical_tests.csv

Run:  python python/s05_statistical_tests.py
"""
import numpy as np
import pandas as pd
from scipy import stats

import config as C

ALPHA = 0.05


def bootstrap_mean_diff(a, b, n=2000, seed=42):
    rng = np.random.default_rng(seed)
    diffs = [rng.choice(a, len(a)).mean() - rng.choice(b, len(b)).mean() for _ in range(n)]
    return np.percentile(diffs, [2.5, 97.5])


def run() -> dict:
    C.ensure_dirs()
    o = pd.read_csv(C.PROCESSED_DIR / "fact_orders.csv")
    d = o[(o["is_delivered"] == 1) & o["review_score"].notna()]
    late = d.loc[d["is_late"] == 1, "review_score"].to_numpy(float)
    ontime = d.loc[d["is_late"] == 0, "review_score"].to_numpy(float)
    rows = []

    # H1 Mann-Whitney U (one-sided: late < on-time)
    u, p1 = stats.mannwhitneyu(late, ontime, alternative="less")
    # rank-biserial correlation = effect size for Mann-Whitney (-1..1)
    effect = 1 - 2 * u / (len(late) * len(ontime))
    rows.append({"hypothesis": "H1 late orders get lower review scores",
                 "test": "Mann-Whitney U (one-sided)", "statistic": round(float(u), 1),
                 "p_value": float(p1), "effect_size": round(float(effect), 3),
                 "effect_measure": "rank-biserial r",
                 "result": "Reject H0" if p1 < ALPHA else "Fail to reject H0"})

    # H2 Chi-square on negative-review share
    neg = d["review_score"] <= 2
    table = pd.crosstab(d["is_late"], neg)
    chi2, p2, dof, _ = stats.chi2_contingency(table)
    neg_late = neg[d["is_late"] == 1].mean()
    neg_ontime = neg[d["is_late"] == 0].mean()
    rows.append({"hypothesis": "H2 negative-review share depends on lateness",
                 "test": "Chi-square test of independence", "statistic": round(float(chi2), 1),
                 "p_value": float(p2), "effect_size": round(float(neg_late / neg_ontime), 2),
                 "effect_measure": "relative risk of a 1-2 star review (late / on-time)",
                 "result": "Reject H0" if p2 < ALPHA else "Fail to reject H0"})

    # H3 Spearman correlation
    rho, p3 = stats.spearmanr(d["delivery_days"], d["review_score"])
    rows.append({"hypothesis": "H3 longer delivery -> lower review",
                 "test": "Spearman rank correlation", "statistic": round(float(rho), 3),
                 "p_value": float(p3), "effect_size": round(float(rho), 3),
                 "effect_measure": "Spearman rho",
                 "result": "Reject H0" if p3 < ALPHA else "Fail to reject H0"})

    lo, hi = bootstrap_mean_diff(ontime, late)
    out = pd.DataFrame(rows)
    out.to_csv(C.OUTPUT_DIR / "statistical_tests.csv", index=False)
    print(out.to_string(index=False))
    print(f"\nMean review on-time {ontime.mean():.2f} vs late {late.mean():.2f}; "
          f"difference 95% CI [{lo:.2f}, {hi:.2f}] (bootstrap, 2,000 resamples)")

    return {
        "test_n_late": int(len(late)), "test_n_ontime": int(len(ontime)),
        "mw_p_value": float(p1), "mw_rank_biserial": round(float(effect), 3),
        "chi2_p_value": float(p2), "neg_review_relative_risk": round(float(neg_late / neg_ontime), 2),
        "spearman_rho": round(float(rho), 3), "spearman_p_value": float(p3),
        "review_diff_ci_low": round(float(lo), 2), "review_diff_ci_high": round(float(hi), 2),
    }


if __name__ == "__main__":
    run()
