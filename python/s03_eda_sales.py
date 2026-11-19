"""
STEP 3 - Exploratory analysis of sales, products, geography, delivery and payments (Python/pandas).

The SQL files answer the same questions in SQL. Here they are answered in pandas, and
each answer is saved as a chart in outputs/figures/. Doing both is deliberate:
interviews test SQL and Python separately.

Run:  python python/s03_eda_sales.py
"""
import numpy as np
import pandas as pd

import config as C
from plot_style import plt, money, pct, save, PRIMARY, ACCENT, NEGATIVE, NEUTRAL


def load():
    orders = pd.read_csv(C.PROCESSED_DIR / "fact_orders.csv", parse_dates=["order_purchase_timestamp"])
    items = pd.read_csv(C.PROCESSED_DIR / "fact_order_items.csv")
    states = pd.read_csv(C.PROCESSED_DIR / "dim_states.csv")
    return orders, items, states


def monthly_trend(valid, m):
    w = valid[valid["in_analysis_window"] == 1]
    monthly = w.groupby("order_month").agg(orders=("order_id", "count"), gmv=("order_gmv", "sum"))
    monthly["aov"] = monthly["gmv"] / monthly["orders"]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 6.5), sharex=True,
                                   gridspec_kw={"height_ratios": [2, 1]})
    ax1.plot(monthly.index, monthly["gmv"], marker="o", color=PRIMARY)
    ax1.set_title("Monthly GMV, Jan 2017 - Aug 2018")
    money(ax1)
    peak = monthly["gmv"].idxmax()
    ax1.annotate(f"Peak {peak}", (peak, monthly.loc[peak, "gmv"]), xytext=(0, 8),
                 textcoords="offset points", ha="center", color=ACCENT, fontweight="bold")
    ax2.bar(monthly.index, monthly["orders"], color=NEUTRAL)
    ax2.set_title("Orders per month")
    ax2.tick_params(axis="x", rotation=60)
    save(fig, C.FIGURE_DIR / "01_monthly_gmv_orders.png")

    m["peak_month"] = peak
    m["peak_month_gmv"] = round(float(monthly.loc[peak, "gmv"]), 2)
    m["peak_month_orders"] = int(monthly.loc[peak, "orders"])
    m["median_month_orders"] = float(monthly["orders"].median())
    monthly.round(2).to_csv(C.OUTPUT_DIR / "monthly_summary.csv")

    # Like-for-like growth: Jan-Aug 2018 vs Jan-Aug 2017
    jan_aug = valid[valid["order_month"].str[5:7].between("01", "08")]
    by_year = jan_aug.groupby("order_year").agg(orders=("order_id", "count"), gmv=("order_gmv", "sum"))
    if {2017, 2018} <= set(by_year.index):
        m["yoy_gmv_growth_pct"] = round(100 * (by_year.loc[2018, "gmv"] / by_year.loc[2017, "gmv"] - 1), 1)
        m["yoy_orders_growth_pct"] = round(100 * (by_year.loc[2018, "orders"] / by_year.loc[2017, "orders"] - 1), 1)


def weekday_hour(valid, m):
    pivot = valid.pivot_table(index="order_weekday_num", columns="order_hour", values="order_id",
                              aggfunc="count", fill_value=0).reindex(columns=range(24), fill_value=0)
    labels = valid.drop_duplicates("order_weekday_num").set_index("order_weekday_num")["order_weekday"]
    fig, ax = plt.subplots(figsize=(12, 3.8))
    im = ax.imshow(pivot.values, aspect="auto", cmap="Blues")
    ax.set_yticks(range(len(pivot.index)), labels.reindex(pivot.index).values)
    ax.set_xticks(range(24))
    ax.set_xlabel("Hour of day")
    ax.grid(False)
    ax.set_title("When customers order (weekday x hour)")
    fig.colorbar(im, ax=ax, label="Orders")
    save(fig, C.FIGURE_DIR / "02_orders_weekday_hour.png")

    by_day = valid.groupby("order_weekday")["order_id"].count()
    m["busiest_weekday"] = by_day.idxmax()
    m["quietest_weekday"] = by_day.idxmin()
    hours = valid.groupby("order_hour")["order_id"].count()
    m["share_orders_10_to_22h_pct"] = round(100 * hours.loc[10:22].sum() / hours.sum(), 1)


def categories(items, m):
    v = items[items["is_valid"] == 1]
    cat = v.groupby("category").agg(revenue=("price", "sum"), items=("order_item_id", "count"),
                                     avg_review=("review_score", "mean")).sort_values("revenue", ascending=False)
    cat["share"] = 100 * cat["revenue"] / cat["revenue"].sum()
    cat["cum_share"] = cat["share"].cumsum()
    cat.round(3).to_csv(C.OUTPUT_DIR / "category_summary.csv")

    top = cat.head(15).iloc[::-1]
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.barh(top.index, top["revenue"], color=PRIMARY)
    money(ax, "x")
    ax.set_title("Top 15 categories by product revenue")
    save(fig, C.FIGURE_DIR / "03_top_categories.png")

    # Pareto: bars = revenue, line = cumulative %
    fig, ax = plt.subplots(figsize=(12, 4.5))
    x = np.arange(len(cat))
    ax.bar(x, cat["revenue"], color=PRIMARY)
    money(ax)
    ax2 = ax.twinx()
    ax2.plot(x, cat["cum_share"], color=ACCENT)
    ax2.axhline(80, color=NEUTRAL, ls="--", lw=1)
    ax2.set_ylim(0, 105)
    pct(ax2)
    ax2.grid(False)
    ax.set_xticks([])
    ax.set_xlabel(f"{len(cat)} categories, sorted by revenue")
    ax.set_title("Category Pareto: how concentrated is revenue?")
    save(fig, C.FIGURE_DIR / "04_category_pareto.png")

    n80 = int((cat["cum_share"] < 80).sum() + 1)
    m["categories_total"] = len(cat)
    m["categories_for_80pct_revenue"] = n80
    m["top_category"] = cat.index[0]
    m["top_category_share_pct"] = round(float(cat["share"].iloc[0]), 1)
    m["top3_categories"] = list(cat.index[:3])
    m["top3_categories_share_pct"] = round(float(cat["share"].iloc[:3].sum()), 1)

    # Freight burden
    fr = v.groupby("category").agg(price=("price", "sum"), freight=("freight_value", "sum"),
                                    n=("order_item_id", "count"))
    fr = fr[fr["n"] >= 200]
    fr["freight_pct"] = 100 * fr["freight"] / fr["price"]
    fr = fr.sort_values("freight_pct", ascending=False)
    if len(fr):
        m["highest_freight_category"] = fr.index[0]
        m["highest_freight_pct"] = round(float(fr["freight_pct"].iloc[0]), 1)
        m["overall_freight_pct"] = round(float(100 * v["freight_value"].sum() / v["price"].sum()), 1)


def geography(valid, states, m):
    st = (valid.groupby("customer_state").agg(gmv=("order_gmv", "sum"), orders=("order_id", "count"),
                                              freight=("freight_value", "mean"))
          .join(states.set_index("state_code")[["state_name", "region"]]))
    st = st.sort_values("gmv", ascending=False)
    st["share"] = 100 * st["gmv"] / st["gmv"].sum()
    top = st.head(10).iloc[::-1]
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.barh(top["state_name"], top["share"], color=PRIMARY)
    pct(ax, "x")
    ax.set_title("Share of GMV by customer state (top 10)")
    save(fig, C.FIGURE_DIR / "05_gmv_by_state.png")

    m["top_state"] = st["state_name"].iloc[0]
    m["top_state_share_pct"] = round(float(st["share"].iloc[0]), 1)
    m["top3_states_share_pct"] = round(float(st["share"].iloc[:3].sum()), 1)
    reg = st.groupby("region")["freight"].mean()
    if "Southeast" in reg and "North" in reg:
        m["avg_freight_southeast"] = round(float(reg["Southeast"]), 2)
        m["avg_freight_north"] = round(float(reg["North"]), 2)


def delivery(orders, states, m):
    d = orders[orders["is_delivered"] == 1]
    m["delivered_orders"] = int(len(d))
    m["avg_delivery_days"] = round(float(d["delivery_days"].mean()), 1)
    m["avg_promised_days"] = round(float(d["estimated_days"].mean()), 1)
    m["late_delivery_pct"] = round(float(100 * d["is_late"].mean()), 1)

    r = d.dropna(subset=["review_score"])
    b = r.groupby("delay_bucket").agg(avg_review=("review_score", "mean"),
                                      neg=("review_score", lambda s: 100 * (s <= 2).mean()),
                                      n=("order_id", "count"))
    fig, ax = plt.subplots(figsize=(10, 4.5))
    colors = [PRIMARY if "Late" not in i else NEGATIVE for i in b.index]
    bars = ax.bar([i[3:] for i in b.index], b["avg_review"], color=colors)
    ax.bar_label(bars, fmt="%.2f")
    ax.set_ylim(0, 5)
    ax.set_ylabel("Average review score (1-5)")
    ax.set_title("Late deliveries destroy review scores")
    save(fig, C.FIGURE_DIR / "06_review_by_delay.png")

    late = r[r["is_late"] == 1]
    ontime = r[r["is_late"] == 0]
    m["avg_review_late"] = round(float(late["review_score"].mean()), 2)
    m["avg_review_ontime"] = round(float(ontime["review_score"].mean()), 2)
    m["neg_review_pct_late"] = round(float(100 * (late["review_score"] <= 2).mean()), 1)
    m["neg_review_pct_ontime"] = round(float(100 * (ontime["review_score"] <= 2).mean()), 1)

    st = (d.groupby("customer_state").agg(late=("is_late", "mean"), days=("delivery_days", "mean"),
                                          n=("order_id", "count"))
          .join(states.set_index("state_code")["state_name"]))
    st = st[st["n"] >= 300].sort_values("late", ascending=False)
    fig, ax = plt.subplots(figsize=(9, 5.5))
    top = st.head(12).iloc[::-1]
    ax.barh(top["state_name"], 100 * top["late"], color=NEGATIVE)
    ax.axvline(100 * d["is_late"].mean(), color=NEUTRAL, ls="--", label="Overall")
    pct(ax, "x")
    ax.legend()
    ax.set_title("Late-delivery rate by state (states with 300+ orders)")
    save(fig, C.FIGURE_DIR / "07_late_rate_by_state.png")
    if len(st):
        m["worst_late_state"] = st["state_name"].iloc[0]
        m["worst_late_state_pct"] = round(float(100 * st["late"].iloc[0]), 1)
        m["best_late_state"] = st["state_name"].iloc[-1]
        m["best_late_state_pct"] = round(float(100 * st["late"].iloc[-1]), 1)


def payments(valid, m):
    p = valid.dropna(subset=["main_payment_type"]).groupby("main_payment_type")["order_id"].count()
    p = (100 * p / p.sum()).sort_values()
    fig, ax = plt.subplots(figsize=(8, 3.5))
    bars = ax.barh(p.index.str.replace("_", " ").str.title(), p.values, color=PRIMARY)
    ax.bar_label(bars, fmt="%.1f%%")
    pct(ax, "x")
    ax.set_title("Main payment method (% of orders)")
    save(fig, C.FIGURE_DIR / "08_payment_mix.png")
    m["credit_card_share_pct"] = round(float(p.get("credit_card", 0)), 1)
    m["boleto_share_pct"] = round(float(p.get("boleto", 0)), 1)
    cc = valid[valid["main_payment_type"] == "credit_card"]
    m["cc_orders_with_installments_pct"] = round(float(100 * (cc["max_installments"] > 1).mean()), 1)


def run() -> dict:
    C.ensure_dirs()
    orders, items, states = load()
    valid = orders[orders["is_valid"] == 1]
    m = {
        "valid_orders": int(len(valid)),
        "gmv": round(float(valid["order_gmv"].sum()), 2),
        "product_revenue": round(float(valid["product_revenue"].sum()), 2),
        "aov": round(float(valid["order_gmv"].mean()), 2),
        "avg_review": round(float(valid["review_score"].mean()), 2),
        "canceled_unavailable_pct": round(float(100 * (1 - orders["is_valid"].mean())), 2),
    }
    print("Building EDA charts ...")
    monthly_trend(valid, m)
    weekday_hour(valid, m)
    categories(items, m)
    geography(valid, states, m)
    delivery(orders, states, m)
    payments(valid, m)
    return m


if __name__ == "__main__":
    for k, v in run().items():
        print(f"{k:35s} {v}")
