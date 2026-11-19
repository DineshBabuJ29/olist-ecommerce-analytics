"""
STEP 1 - Data quality audit, cleaning and transformation (ETL).

Input : 8 raw Olist CSVs in data/raw/
Output: a clean star schema in data/processed/
          fact_orders.csv       one row per order (order-level KPIs, delivery, review)
          fact_order_items.csv  one row per item sold (product / seller analysis)
          fact_payments.csv     one row per payment record
          dim_customers.csv     one row per real customer (customer_unique_id)
          dim_products.csv      one row per product, English category names
          dim_sellers.csv       one row per seller
          dim_states.csv        Brazilian state code -> name, region
        outputs/data_quality_report.csv  (what was wrong with the raw data)

Key business definitions (also in docs/DATA_DICTIONARY.md):
  * A "customer" is customer_unique_id. Olist's customer_id is a new id PER ORDER,
    so counting customer_id would make every customer look like a first-time buyer.
  * A "valid" order is any order whose status is not canceled/unavailable.
  * Product revenue = sum of item price.  GMV = price + freight (what the customer paid).
  * An order is "late" when it was delivered after the estimated delivery date.

Run:  python python/s01_clean_transform.py
"""
import pandas as pd
import numpy as np

import config as C


# --------------------------------------------------------------------------- #
# Load
# --------------------------------------------------------------------------- #
def find_raw(filename: str):
    """Find a raw file anywhere under data/raw (handles an extra unzip sub-folder)."""
    hits = list(C.RAW_DIR.rglob(filename))
    if not hits:
        raise FileNotFoundError(
            f"{filename} not found under {C.RAW_DIR}.\n"
            "Download https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce "
            "and unzip the CSVs into data/raw/."
        )
    return hits[0]


def load_raw() -> dict:
    # utf-8-sig strips the BOM that Olist's translation file has in its header.
    return {k: pd.read_csv(find_raw(f), encoding="utf-8-sig") for k, f in C.RAW_FILES.items()}


# --------------------------------------------------------------------------- #
# Audit
# --------------------------------------------------------------------------- #
PRIMARY_KEYS = {
    "customers": ["customer_id"], "orders": ["order_id"],
    "items": ["order_id", "order_item_id"],
    "payments": ["order_id", "payment_sequential"], "reviews": ["review_id", "order_id"],
    "products": ["product_id"], "sellers": ["seller_id"],
    "category_translation": ["product_category_name"],
}


def audit(raw: dict) -> pd.DataFrame:
    """Row counts, duplicate keys and missing values for every raw table."""
    rows = []
    for name, df in raw.items():
        dup = int(df.duplicated(subset=PRIMARY_KEYS[name]).sum())
        for col in df.columns:
            rows.append({
                "table": name, "rows": len(df), "duplicate_keys": dup,
                "column": col, "nulls": int(df[col].isna().sum()),
                "null_pct": round(100 * df[col].isna().mean(), 2),
            })
    report = pd.DataFrame(rows)
    report.to_csv(C.OUTPUT_DIR / "data_quality_report.csv", index=False)
    return report


# --------------------------------------------------------------------------- #
# Transform
# --------------------------------------------------------------------------- #
ORDER_DATE_COLS = [
    "order_purchase_timestamp", "order_approved_at", "order_delivered_carrier_date",
    "order_delivered_customer_date", "order_estimated_delivery_date",
]


def clean_orders(orders: pd.DataFrame, customers: pd.DataFrame, issues: dict) -> pd.DataFrame:
    o = orders.drop_duplicates("order_id").copy()
    for col in ORDER_DATE_COLS:
        o[col] = pd.to_datetime(o[col], errors="coerce")

    # Map the per-order customer_id to the real customer (customer_unique_id).
    o = o.merge(customers[["customer_id", "customer_unique_id", "customer_city", "customer_state"]],
                on="customer_id", how="left")

    o["is_valid"] = (~o["order_status"].isin(C.INVALID_STATUSES)).astype(int)

    # Delivery metrics only make sense for delivered orders with a delivery date.
    delivered = (o["order_status"] == "delivered") & o["order_delivered_customer_date"].notna()
    # A delivery timestamp earlier than the purchase is a data error: drop the metric, keep the order.
    bad_dates = delivered & (o["order_delivered_customer_date"] < o["order_purchase_timestamp"])
    issues["delivered_before_purchase"] = int(bad_dates.sum())
    issues["delivered_status_without_date"] = int(
        ((o["order_status"] == "delivered") & o["order_delivered_customer_date"].isna()).sum())
    delivered &= ~bad_dates
    o["is_delivered"] = delivered.astype(int)

    secs_per_day = 86400
    o["delivery_days"] = np.where(
        delivered,
        (o["order_delivered_customer_date"] - o["order_purchase_timestamp"]).dt.total_seconds() / secs_per_day,
        np.nan).round(1)
    o["estimated_days"] = ((o["order_estimated_delivery_date"] - o["order_purchase_timestamp"])
                           .dt.total_seconds() / secs_per_day).round(1)
    # Compare calendar days: delivered on the promised day counts as on time.
    o["delay_days"] = np.where(
        delivered,
        (o["order_delivered_customer_date"].dt.normalize()
         - o["order_estimated_delivery_date"].dt.normalize()).dt.days,
        np.nan)
    o["is_late"] = np.where(delivered, (o["delay_days"] > 0).astype(float), np.nan)
    # Nullable integers, so the CSVs contain 1/0/blank rather than 1.0/0.0 (MySQL-friendly).
    o["delay_days"] = o["delay_days"].astype("Int64")
    o["is_late"] = o["is_late"].astype("Int64")
    o["delay_bucket"] = pd.cut(
        o["delay_days"], bins=[-np.inf, -8, -1, 0, 3, 7, np.inf],
        labels=["1. Early 8+ days", "2. Early 1-7 days", "3. On the day",
                "4. Late 1-3 days", "5. Late 4-7 days", "6. Late 8+ days"]).astype("string")

    # Pre-computed calendar fields. They keep the SQL files free of date functions,
    # which differ between MySQL and SQLite, so the same SQL runs on both.
    ts = o["order_purchase_timestamp"]
    o["purchase_date"] = ts.dt.strftime("%Y-%m-%d")
    o["order_year"] = ts.dt.year
    o["order_month"] = ts.dt.strftime("%Y-%m")
    o["order_month_num"] = ts.dt.year * 12 + ts.dt.month       # month index for cohort maths
    o["purchase_day_num"] = (ts.dt.normalize() - pd.Timestamp("2016-01-01")).dt.days  # day index for recency
    o["order_weekday"] = ts.dt.day_name().str[:3]
    o["order_weekday_num"] = ts.dt.dayofweek + 1                # 1 = Monday
    o["order_hour"] = ts.dt.hour
    o["in_analysis_window"] = o["order_month"].between(
        C.ANALYSIS_START_MONTH, C.ANALYSIS_END_MONTH).astype(int)
    return o


def clean_items(items: pd.DataFrame, issues: dict) -> pd.DataFrame:
    i = items.drop_duplicates(["order_id", "order_item_id"]).copy()
    issues["items_non_positive_price"] = int((i["price"] <= 0).sum())
    i = i[i["price"] > 0]
    i["item_gmv"] = (i["price"] + i["freight_value"]).round(2)
    return i


def clean_payments(payments: pd.DataFrame, issues: dict) -> pd.DataFrame:
    p = payments.drop_duplicates(["order_id", "payment_sequential"]).copy()
    # Olist contains a few 'not_defined' payments with value 0 - they carry no money.
    mask = (p["payment_type"] == "not_defined") | (p["payment_value"] <= 0)
    issues["payments_not_defined_or_zero"] = int(mask.sum())
    return p[~mask]


def clean_reviews(reviews: pd.DataFrame, issues: dict) -> pd.DataFrame:
    """One review per order: keep the most recently answered one."""
    r = reviews.copy()
    r["review_answer_timestamp"] = pd.to_datetime(r["review_answer_timestamp"], errors="coerce")
    issues["orders_with_multiple_reviews"] = int(r["order_id"].duplicated().sum())
    r = (r.sort_values("review_answer_timestamp")
          .drop_duplicates("order_id", keep="last"))
    r["has_comment"] = r["review_comment_message"].notna().astype(int)
    return r[["order_id", "review_score", "has_comment"]]


def build_products(products: pd.DataFrame, translation: pd.DataFrame, issues: dict) -> pd.DataFrame:
    p = products.rename(columns={  # Olist misspells "length" in two column names
        "product_name_lenght": "product_name_length",
        "product_description_lenght": "product_description_length"}).copy()
    mapping = dict(zip(translation["product_category_name"], translation["product_category_name_english"]))
    mapping.update(C.EXTRA_CATEGORY_TRANSLATIONS)
    issues["products_without_category"] = int(p["product_category_name"].isna().sum())
    p["category"] = (p["product_category_name"].map(mapping)
                     .fillna(p["product_category_name"])   # untranslated -> keep original
                     .fillna("unknown")
                     .str.replace("_", " ").str.strip().str.title())
    keep = ["product_id", "category", "product_category_name", "product_photos_qty",
            "product_weight_g", "product_length_cm", "product_height_cm", "product_width_cm"]
    return p[keep].rename(columns={"product_category_name": "category_portuguese"})


def build_fact_orders(o, items, payments, reviews) -> pd.DataFrame:
    item_agg = items.groupby("order_id").agg(
        items_count=("order_item_id", "count"),
        sellers_count=("seller_id", "nunique"),
        product_revenue=("price", "sum"),
        freight_value=("freight_value", "sum"),
    )
    item_agg["order_gmv"] = item_agg["product_revenue"] + item_agg["freight_value"]

    # Main payment type = the method that paid the largest share of the order.
    main_type = (payments.sort_values("payment_value", ascending=False)
                 .drop_duplicates("order_id").set_index("order_id")["payment_type"])
    pay_agg = payments.groupby("order_id").agg(
        payment_value=("payment_value", "sum"),
        max_installments=("payment_installments", "max"))
    pay_agg["main_payment_type"] = main_type

    f = (o.merge(item_agg, on="order_id", how="left")
          .merge(pay_agg, on="order_id", how="left")
          .merge(reviews, on="order_id", how="left"))
    for col in ["items_count", "sellers_count"]:
        f[col] = f[col].fillna(0).astype(int)
    for col in ["review_score", "has_comment", "max_installments"]:
        f[col] = f[col].astype("Int64")
    for col in ["product_revenue", "freight_value", "order_gmv", "payment_value"]:
        f[col] = f[col].round(2)

    # First valid order of each customer -> "new customer" flag (used in Power BI).
    valid = f[f["is_valid"] == 1].sort_values("order_purchase_timestamp")
    first_ids = valid.drop_duplicates("customer_unique_id")["order_id"]
    f["is_first_order"] = f["order_id"].isin(first_ids).astype(int)
    return f


def build_dim_customers(f: pd.DataFrame) -> pd.DataFrame:
    """Every customer that appears in fact_orders (so no Power BI relationship is broken);
    purchase statistics count valid orders only."""
    everyone = (f.sort_values("order_purchase_timestamp")
                 .groupby("customer_unique_id")[["customer_city", "customer_state"]].last())
    valid = f[f["is_valid"] == 1].sort_values("order_purchase_timestamp")
    g = valid.groupby("customer_unique_id")
    stats = pd.DataFrame({
        "first_order_date": g["purchase_date"].first(),
        "last_order_date": g["purchase_date"].last(),
        "cohort_month": g["order_month"].first(),
        "cohort_month_num": g["order_month_num"].first(),
        "total_orders": g["order_id"].count(),
        "total_gmv": g["order_gmv"].sum().round(2),
    })
    d = everyone.join(stats, how="left").reset_index()
    d["total_orders"] = d["total_orders"].fillna(0).astype(int)
    d["total_gmv"] = d["total_gmv"].fillna(0)
    d["cohort_month_num"] = d["cohort_month_num"].astype("Int64")
    d["customer_type"] = np.select([d["total_orders"] > 1, d["total_orders"] == 1],
                                   ["Repeat", "One-time"], "No valid order")
    return d


def build_dim_states() -> pd.DataFrame:
    return pd.DataFrame(
        [(code, name, region, f"{name}, Brazil") for code, (name, region) in C.BRAZIL_STATES.items()],
        columns=["state_code", "state_name", "region", "map_location"])


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def run() -> dict:
    C.ensure_dirs()
    raw = load_raw()
    report = audit(raw)
    issues = {}

    orders = clean_orders(raw["orders"], raw["customers"], issues)
    items = clean_items(raw["items"], issues)
    payments = clean_payments(raw["payments"], issues)
    reviews = clean_reviews(raw["reviews"], issues)
    products = build_products(raw["products"], raw["category_translation"], issues)
    sellers = raw["sellers"].drop_duplicates("seller_id")

    fact_orders = build_fact_orders(orders, items, payments, reviews)
    issues["orders_without_items"] = int((fact_orders["items_count"] == 0).sum())
    issues["orders_without_payment"] = int(fact_orders["payment_value"].isna().sum())
    issues["orders_payment_vs_gmv_diff_gt_1"] = int(
        ((fact_orders["payment_value"] - fact_orders["order_gmv"]).abs() > 1).sum())

    # Items carry the order-level fields they are analysed by, so product and seller
    # visuals do not need a fact-to-fact relationship in Power BI.
    order_cols = ["order_id", "customer_unique_id", "customer_state", "purchase_date", "order_month",
                  "order_month_num", "in_analysis_window", "is_valid", "is_delivered", "is_late",
                  "delivery_days", "review_score"]
    fact_items = (items.merge(fact_orders[order_cols], on="order_id", how="inner")
                       .merge(products[["product_id", "category"]], on="product_id", how="left"))
    fact_items["category"] = fact_items["category"].fillna("Unknown")

    fact_payments = payments.merge(
        fact_orders[["order_id", "purchase_date", "order_month", "is_valid", "in_analysis_window"]],
        on="order_id", how="inner")

    dim_customers = build_dim_customers(fact_orders)

    drop_cols = ["customer_id"] + ORDER_DATE_COLS[1:4]  # keep purchase + estimated timestamps
    out = {
        "fact_orders": fact_orders.drop(columns=drop_cols),
        "fact_order_items": fact_items.drop(columns=["shipping_limit_date"]),
        "fact_payments": fact_payments,
        "dim_customers": dim_customers,
        "dim_products": products,
        "dim_sellers": sellers,
        "dim_states": build_dim_states(),
    }
    for name, df in out.items():
        # "\n" line endings so MySQL LOAD DATA (sql/02_load_mysql.sql) reads them on Windows too
        df.to_csv(C.PROCESSED_DIR / f"{name}.csv", index=False, date_format="%Y-%m-%d %H:%M:%S",
                  lineterminator="\n")

    # ---- console summary ------------------------------------------------- #
    print("\nRAW TABLES")
    print(report.groupby("table")[["rows", "duplicate_keys"]].first().to_string())
    print("\nCOLUMNS WITH MISSING VALUES")
    print(report[report["nulls"] > 0][["table", "column", "nulls", "null_pct"]].to_string(index=False))
    print("\nCLEANING ISSUES HANDLED")
    for k, v in issues.items():
        print(f"  {k:40s} {v:>8,}")
    print("\nPROCESSED TABLES")
    for name, df in out.items():
        print(f"  {name:20s} {len(df):>9,} rows  {df.shape[1]:>3} cols")

    return {
        "raw_orders": len(raw["orders"]),
        "raw_items": len(raw["items"]),
        "customers_unique": int(dim_customers.shape[0]),
        "products": len(products), "sellers": len(sellers),
        "first_purchase": str(fact_orders["purchase_date"].min()),
        "last_purchase": str(fact_orders["purchase_date"].max()),
        "cleaning_issues": issues,
    }


if __name__ == "__main__":
    run()
