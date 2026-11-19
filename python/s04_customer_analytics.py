"""
STEP 4 - Customer analytics: repeat rate, cohort retention, RFM segmentation.

Outputs
  data/processed/dim_customers.csv   updated with R, F, M scores + segment (for Power BI)
  data/processed/cohort_retention.csv  long format: cohort_month, month_offset, customers, retention_pct
  outputs/figures/09_cohort_retention.png, 10_rfm_segments.png

Run:  python python/s04_customer_analytics.py
"""
import numpy as np
import pandas as pd

import config as C
from plot_style import plt, pct, save, PRIMARY, ACCENT


SEGMENT_ORDER = ["Champions", "Loyal", "Promising High-Value", "New / Recent",
                 "Needs Attention", "At Risk High-Value", "Lost / Hibernating"]


def rfm(valid: pd.DataFrame) -> pd.DataFrame:
    """Same logic as sql/05_customer_analysis.sql -> rfm_segments, done in pandas."""
    snapshot = valid["order_purchase_timestamp"].max().normalize() + pd.Timedelta(days=1)
    c = valid.groupby("customer_unique_id").agg(
        last_purchase=("order_purchase_timestamp", "max"),
        frequency=("order_id", "count"),
        monetary=("order_gmv", "sum"))
    c["recency_days"] = (snapshot - c["last_purchase"].dt.normalize()).dt.days
    # rank(method="first") breaks ties so qcut always gets 5 equal-sized groups
    c["r_score"] = pd.qcut(c["recency_days"].rank(method="first", ascending=False), 5, labels=[1, 2, 3, 4, 5]).astype(int)
    c["m_score"] = pd.qcut(c["monetary"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)
    c["f_score"] = np.select([c["frequency"] >= 3, c["frequency"] == 2], [5, 4], 1)

    r, f, mo = c["r_score"], c["f_score"], c["m_score"]
    c["rfm_segment"] = np.select(
        [(r >= 4) & (f >= 4) & (mo >= 4), f >= 4, (r >= 4) & (mo >= 4), r >= 4, r == 3, (r <= 2) & (mo >= 4)],
        SEGMENT_ORDER[:-1], SEGMENT_ORDER[-1])
    c["rfm_code"] = r.astype(str) + f.astype(str) + mo.astype(str)
    return c.drop(columns="last_purchase")


def cohorts(valid: pd.DataFrame) -> pd.DataFrame:
    v = valid[["customer_unique_id", "order_month", "order_month_num"]].copy()
    first = v.groupby("customer_unique_id")["order_month_num"].transform("min")
    v["cohort_month"] = v.groupby("customer_unique_id")["order_month"].transform("min")
    v["month_offset"] = v["order_month_num"] - first
    active = v.drop_duplicates(["customer_unique_id", "month_offset"])
    long = (active.groupby(["cohort_month", "month_offset"])["customer_unique_id"].nunique()
            .rename("customers").reset_index())
    size = long[long["month_offset"] == 0].set_index("cohort_month")["customers"]
    long["cohort_size"] = long["cohort_month"].map(size)
    long["retention_pct"] = (100 * long["customers"] / long["cohort_size"]).round(3)
    return long[long["cohort_month"].between(C.ANALYSIS_START_MONTH, C.ANALYSIS_END_MONTH)]


def run() -> dict:
    C.ensure_dirs()
    orders = pd.read_csv(C.PROCESSED_DIR / "fact_orders.csv", parse_dates=["order_purchase_timestamp"])
    valid = orders[orders["is_valid"] == 1]
    m = {}

    # ---- repeat purchase --------------------------------------------------- #
    per_cust = valid.groupby("customer_unique_id")["order_id"].count()
    gmv_cust = valid.groupby("customer_unique_id")["order_gmv"].sum()
    m["customers_with_valid_order"] = int(len(per_cust))
    m["repeat_customer_pct"] = round(float(100 * (per_cust > 1).mean()), 2)
    m["repeat_customer_gmv_pct"] = round(float(100 * gmv_cust[per_cust > 1].sum() / gmv_cust.sum()), 2)

    # ---- cohorts ----------------------------------------------------------- #
    long = cohorts(valid)
    long.to_csv(C.PROCESSED_DIR / "cohort_retention.csv", index=False, lineterminator="\n")
    wide = long.pivot(index="cohort_month", columns="month_offset", values="retention_pct")
    wide = wide.reindex(columns=range(0, 13))
    fig, ax = plt.subplots(figsize=(12, 6.5))
    shown = wide.drop(columns=0)  # month 0 is always 100%
    im = ax.imshow(shown.values, aspect="auto", cmap="Blues", vmin=0, vmax=max(1.0, np.nanmax(shown.values)))
    for (i, j), val in np.ndenumerate(shown.values):
        if not np.isnan(val):
            ax.text(j, i, f"{val:.1f}", ha="center", va="center", fontsize=7)
    ax.set_xticks(range(shown.shape[1]), [f"M{k}" for k in shown.columns])
    ax.set_yticks(range(len(shown.index)), shown.index)
    ax.grid(False)
    ax.set_title("Cohort retention: % of each month's new customers who order again in month N")
    fig.colorbar(im, ax=ax, label="% retained")
    save(fig, C.FIGURE_DIR / "09_cohort_retention.png")
    m1 = long[long["month_offset"] == 1]
    m["avg_month1_retention_pct"] = round(float(m1["retention_pct"].mean()), 2) if len(m1) else None
    m["cohorts_analysed"] = int(wide.shape[0])

    # ---- RFM --------------------------------------------------------------- #
    c = rfm(valid)
    seg = c.groupby("rfm_segment").agg(customers=("frequency", "size"), gmv=("monetary", "sum"),
                                       avg_recency=("recency_days", "mean"), avg_gmv=("monetary", "mean"))
    seg = seg.reindex([s for s in SEGMENT_ORDER if s in seg.index])
    seg["pct_customers"] = 100 * seg["customers"] / seg["customers"].sum()
    seg["pct_gmv"] = 100 * seg["gmv"] / seg["gmv"].sum()
    seg.round(2).to_csv(C.OUTPUT_DIR / "rfm_segment_summary.csv")

    fig, ax = plt.subplots(figsize=(10, 4.8))
    y = np.arange(len(seg))
    ax.barh(y - 0.2, seg["pct_customers"], 0.4, color=PRIMARY, label="% of customers")
    ax.barh(y + 0.2, seg["pct_gmv"], 0.4, color=ACCENT, label="% of GMV")
    ax.set_yticks(y, seg.index)
    ax.invert_yaxis()
    pct(ax, "x")
    ax.legend()
    ax.set_title("RFM segments: share of customers vs share of revenue")
    save(fig, C.FIGURE_DIR / "10_rfm_segments.png")
    m["rfm_segments"] = {k: {"pct_customers": round(float(r.pct_customers), 1),
                             "pct_gmv": round(float(r.pct_gmv), 1),
                             "avg_gmv": round(float(r.avg_gmv), 2)} for k, r in seg.iterrows()}

    # ---- write RFM back onto the customer dimension for Power BI ------------ #
    dim = pd.read_csv(C.PROCESSED_DIR / "dim_customers.csv")
    dim = dim.drop(columns=[col for col in ["recency_days", "r_score", "f_score", "m_score",
                                            "rfm_code", "rfm_segment"] if col in dim.columns])
    dim = dim.merge(c[["recency_days", "r_score", "f_score", "m_score", "rfm_code", "rfm_segment"]],
                    left_on="customer_unique_id", right_index=True, how="left")
    dim["rfm_segment"] = dim["rfm_segment"].fillna("No valid order")
    for col in ["recency_days", "r_score", "f_score", "m_score"]:
        dim[col] = dim[col].astype("Int64")
    dim.to_csv(C.PROCESSED_DIR / "dim_customers.csv", index=False, lineterminator="\n")
    print("  dim_customers.csv updated with RFM scores")
    return m


if __name__ == "__main__":
    for k, v in run().items():
        print(f"{k:35s} {v}")
