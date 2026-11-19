"""
STEP 2 - Load the clean tables into a SQL database and run every analysis query.

Why SQLite here?  It ships with Python, so the whole project runs with zero setup
and every query in /sql is verified automatically. The same SQL files are written
in portable SQL (CTEs, window functions, CASE, no vendor date functions), so they
also run unchanged on MySQL 8. Use sql/01_schema_mysql.sql + 02_load_mysql.sql
to load the same CSVs into MySQL Workbench.

Output: data/olist.db and one CSV per query in outputs/sql_results/

Run:  python python/s02_build_database.py
"""
import re
import sqlite3

import pandas as pd

import config as C

TABLES = ["fact_orders", "fact_order_items", "fact_payments",
          "dim_customers", "dim_products", "dim_sellers", "dim_states"]
INDEXES = [
    "CREATE INDEX ix_orders_customer ON fact_orders(customer_unique_id)",
    "CREATE INDEX ix_orders_month ON fact_orders(order_month)",
    "CREATE INDEX ix_items_order ON fact_order_items(order_id)",
    "CREATE INDEX ix_items_product ON fact_order_items(product_id)",
    "CREATE INDEX ix_items_seller ON fact_order_items(seller_id)",
    "CREATE INDEX ix_pay_order ON fact_payments(order_id)",
]
ANALYSIS_FILES = ["03_data_quality_checks.sql", "04_sales_kpis.sql", "05_customer_analysis.sql",
                  "06_product_seller_analysis.sql", "07_delivery_and_reviews.sql", "08_payments.sql"]


def build_db() -> sqlite3.Connection:
    if C.DB_PATH.exists():
        C.DB_PATH.unlink()
    con = sqlite3.connect(C.DB_PATH)
    for t in TABLES:
        df = pd.read_csv(C.PROCESSED_DIR / f"{t}.csv")
        df.to_sql(t, con, index=False)
        print(f"  loaded {t:18s} {len(df):>9,} rows")
    for stmt in INDEXES:
        con.execute(stmt)
    con.commit()
    return con


def split_queries(sql_text: str):
    """Yield (name, sql) for every statement tagged with '-- @name: x'."""
    for stmt in sql_text.split(";"):
        m = re.search(r"--\s*@name:\s*(\w+)", stmt)
        body = "\n".join(l for l in stmt.splitlines() if l.strip() and not l.strip().startswith("--"))
        if m and body.strip():
            yield m.group(1), body


def run_queries(con) -> dict:
    results = {}
    for fname in ANALYSIS_FILES:
        text = (C.SQL_DIR / fname).read_text(encoding="utf-8")
        print(f"\n### {fname}")
        for name, sql in split_queries(text):
            df = pd.read_sql_query(sql, con)
            df.to_csv(C.SQL_RESULT_DIR / f"{fname[:2]}_{name}.csv", index=False)
            results[name] = df
            print(f"\n-- {name}  ({len(df)} rows)")
            print(df.head(12).to_string(index=False))
    return results


def run() -> dict:
    C.ensure_dirs()
    print("Building SQLite database ...")
    con = build_db()
    try:
        results = run_queries(con)
    finally:
        con.close()
    print(f"\n{len(results)} queries ran OK -> {C.SQL_RESULT_DIR}")
    return {"sql_queries_run": len(results)}


if __name__ == "__main__":
    run()
