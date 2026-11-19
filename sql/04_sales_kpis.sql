-- =====================================================================
-- 04  SALES PERFORMANCE KPIs
-- Business questions:
--   Q1  How big is the business? (GMV, orders, AOV, customers)
--   Q2  How is revenue trending month over month?
--   Q3  Is 2018 growing versus the same months of 2017?
--   Q4  When do customers buy (weekday x hour)?
--   Q5  Which states generate the revenue?
-- Concepts used: aggregation, CASE, CTEs, window functions
--   (LAG, AVG OVER with a frame, SUM OVER, RANK).
-- Valid order = status not canceled/unavailable (is_valid = 1).
-- =====================================================================

-- @name: headline_kpis
-- Q1. Whole-history headline numbers.
SELECT
  COUNT(*)                                             AS total_orders,
  COUNT(DISTINCT customer_unique_id)                   AS total_customers,
  ROUND(SUM(order_gmv), 2)                             AS gmv,
  ROUND(SUM(product_revenue), 2)                       AS product_revenue,
  ROUND(SUM(freight_value), 2)                         AS freight_revenue,
  ROUND(SUM(order_gmv) / COUNT(*), 2)                  AS avg_order_value,
  ROUND(1.0 * SUM(items_count) / COUNT(*), 2)          AS avg_items_per_order,
  ROUND(AVG(review_score), 2)                          AS avg_review_score
FROM fact_orders
WHERE is_valid = 1;

-- @name: monthly_trend
-- Q2. Monthly GMV with month-over-month growth and a 3-month moving average.
WITH monthly AS (
  SELECT order_month,
         COUNT(*)                            AS orders,
         COUNT(DISTINCT customer_unique_id)  AS customers,
         SUM(order_gmv)                      AS gmv
  FROM fact_orders
  WHERE is_valid = 1 AND in_analysis_window = 1
  GROUP BY order_month
)
SELECT order_month,
       orders,
       customers,
       ROUND(gmv, 2)                                                   AS gmv,
       ROUND(gmv / orders, 2)                                          AS aov,
       ROUND(100.0 * (gmv - LAG(gmv) OVER (ORDER BY order_month))
             / LAG(gmv) OVER (ORDER BY order_month), 2)                AS gmv_mom_growth_pct,
       ROUND(AVG(gmv) OVER (ORDER BY order_month
             ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 2)             AS gmv_3m_moving_avg,
       ROUND(SUM(gmv) OVER (ORDER BY order_month
             ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW), 2)     AS gmv_running_total
FROM monthly
ORDER BY order_month;

-- @name: yoy_jan_aug
-- Q3. Like-for-like comparison: January-August 2018 vs January-August 2017.
WITH ytd AS (
  SELECT order_year,
         COUNT(*)                            AS orders,
         SUM(order_gmv)                      AS gmv,
         COUNT(DISTINCT customer_unique_id)  AS customers
  FROM fact_orders
  WHERE is_valid = 1
    AND order_year IN (2017, 2018)
    AND SUBSTR(order_month, 6, 2) BETWEEN '01' AND '08'
  GROUP BY order_year
)
SELECT cur.order_year                                            AS year_,
       cur.orders, ROUND(cur.gmv, 2)                             AS gmv,
       ROUND(cur.gmv / cur.orders, 2)                            AS aov,
       ROUND(100.0 * (cur.orders - prev.orders) / prev.orders, 2) AS orders_yoy_pct,
       ROUND(100.0 * (cur.gmv - prev.gmv) / prev.gmv, 2)         AS gmv_yoy_pct
FROM ytd cur
LEFT JOIN ytd prev ON prev.order_year = cur.order_year - 1
ORDER BY cur.order_year;

-- @name: orders_by_weekday_hour
-- Q4. Purchase timing heat-map data.
SELECT order_weekday_num, order_weekday, order_hour, COUNT(*) AS orders
FROM fact_orders
WHERE is_valid = 1
GROUP BY order_weekday_num, order_weekday, order_hour
ORDER BY order_weekday_num, order_hour;

-- @name: orders_by_weekday
SELECT order_weekday_num, order_weekday,
       COUNT(*)                                            AS orders,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2)  AS pct_of_orders
FROM fact_orders
WHERE is_valid = 1
GROUP BY order_weekday_num, order_weekday
ORDER BY order_weekday_num;

-- @name: revenue_by_state
-- Q5. State ranking with revenue share and cumulative share (concentration).
WITH st AS (
  SELECT o.customer_state, s.state_name, s.region,
         COUNT(*)                            AS orders,
         COUNT(DISTINCT o.customer_unique_id) AS customers,
         SUM(o.order_gmv)                    AS gmv,
         AVG(o.freight_value)                AS avg_freight
  FROM fact_orders o
  JOIN dim_states s ON s.state_code = o.customer_state
  WHERE o.is_valid = 1
  GROUP BY o.customer_state, s.state_name, s.region
)
SELECT customer_state, state_name, region, orders, customers,
       ROUND(gmv, 2)                                                   AS gmv,
       ROUND(gmv / orders, 2)                                          AS aov,
       ROUND(avg_freight, 2)                                           AS avg_freight,
       RANK() OVER (ORDER BY gmv DESC)                                 AS gmv_rank,
       ROUND(100.0 * gmv / SUM(gmv) OVER (), 2)                        AS gmv_share_pct,
       ROUND(100.0 * SUM(gmv) OVER (ORDER BY gmv DESC
             ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
             / SUM(gmv) OVER (), 2)                                    AS cumulative_share_pct
FROM st
ORDER BY gmv DESC;

-- @name: revenue_by_region
SELECT s.region,
       COUNT(*)                                                       AS orders,
       ROUND(SUM(o.order_gmv), 2)                                     AS gmv,
       ROUND(100.0 * SUM(o.order_gmv) / SUM(SUM(o.order_gmv)) OVER (), 2) AS gmv_share_pct,
       ROUND(AVG(o.freight_value), 2)                                 AS avg_freight
FROM fact_orders o
JOIN dim_states s ON s.state_code = o.customer_state
WHERE o.is_valid = 1
GROUP BY s.region
ORDER BY gmv DESC;
