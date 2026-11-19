-- =====================================================================
-- 03  DATA QUALITY CHECKS  (run after loading the processed tables)
-- Portable SQL: runs unchanged on MySQL 8 and SQLite.
-- Each query starts with a line "-- @name: <id>". The Python runner uses
-- that name for the result file in outputs/sql_results/.
-- =====================================================================

-- @name: table_row_counts
SELECT 'fact_orders' AS table_name, COUNT(*) AS row_count FROM fact_orders
UNION ALL SELECT 'fact_order_items', COUNT(*) FROM fact_order_items
UNION ALL SELECT 'fact_payments', COUNT(*) FROM fact_payments
UNION ALL SELECT 'dim_customers', COUNT(*) FROM dim_customers
UNION ALL SELECT 'dim_products', COUNT(*) FROM dim_products
UNION ALL SELECT 'dim_sellers', COUNT(*) FROM dim_sellers;

-- @name: order_status_distribution
SELECT order_status,
       COUNT(*)                                                  AS orders,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2)        AS pct_of_orders
FROM fact_orders
GROUP BY order_status
ORDER BY orders DESC;

-- @name: duplicate_order_ids
-- Expect 0 rows.
SELECT order_id, COUNT(*) AS copies
FROM fact_orders
GROUP BY order_id
HAVING COUNT(*) > 1;

-- @name: orphan_checks
-- Expect 0 in every column.
SELECT
  (SELECT COUNT(*) FROM fact_order_items i
     LEFT JOIN dim_products p ON p.product_id = i.product_id
    WHERE p.product_id IS NULL)                                   AS items_without_product,
  (SELECT COUNT(*) FROM fact_order_items i
     LEFT JOIN dim_sellers s ON s.seller_id = i.seller_id
    WHERE s.seller_id IS NULL)                                    AS items_without_seller,
  (SELECT COUNT(*) FROM fact_orders o
     LEFT JOIN dim_customers c ON c.customer_unique_id = o.customer_unique_id
    WHERE c.customer_unique_id IS NULL)                           AS orders_without_customer;

-- @name: orders_missing_items_or_payment
SELECT
  SUM(CASE WHEN items_count = 0 THEN 1 ELSE 0 END)                AS orders_without_items,
  SUM(CASE WHEN payment_value IS NULL THEN 1 ELSE 0 END)          AS orders_without_payment,
  SUM(CASE WHEN ABS(payment_value - order_gmv) > 1 THEN 1 ELSE 0 END) AS payment_gmv_mismatch
FROM fact_orders;

-- @name: monthly_order_volume
-- Shows why 2016 and Sep/Oct-2018 are excluded from trend analysis.
SELECT order_month, COUNT(*) AS orders, MAX(in_analysis_window) AS in_analysis_window
FROM fact_orders
GROUP BY order_month
ORDER BY order_month;
