-- =====================================================================
-- 05  CUSTOMER ANALYSIS: repeat purchase, cohort retention, RFM
-- Business questions:
--   Q6  How many customers come back for a second order?
--   Q7  Of each monthly cohort of new customers, how many return later?
--   Q8  Which customers are Champions / At Risk / Lost (RFM)?
-- Always count customers with customer_unique_id. customer_id changes
-- with every order, so it would show a 0% repeat rate.
-- Concepts: CTEs, CASE bucketing, conditional aggregation (pivot),
--           NTILE, MAX() OVER (), self-joins.
-- =====================================================================

-- @name: repeat_purchase_summary
-- Q6
WITH cust AS (
  SELECT customer_unique_id, COUNT(*) AS orders, SUM(order_gmv) AS gmv
  FROM fact_orders
  WHERE is_valid = 1
  GROUP BY customer_unique_id
)
SELECT CASE WHEN orders = 1 THEN '1 order'
            WHEN orders = 2 THEN '2 orders'
            ELSE '3+ orders' END                                   AS order_bucket,
       COUNT(*)                                                    AS customers,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2)          AS pct_of_customers,
       ROUND(SUM(gmv), 2)                                          AS gmv,
       ROUND(100.0 * SUM(gmv) / SUM(SUM(gmv)) OVER (), 2)          AS pct_of_gmv,
       ROUND(SUM(gmv) / COUNT(*), 2)                               AS gmv_per_customer
FROM cust
GROUP BY CASE WHEN orders = 1 THEN '1 order'
              WHEN orders = 2 THEN '2 orders'
              ELSE '3+ orders' END
ORDER BY order_bucket;

-- @name: cohort_retention
-- Q7. Cohort = month of a customer's first valid order. month_offset 1 =
-- the calendar month after the first purchase. Cohorts are limited to the
-- analysis window so every cohort has at least a few months to return.
WITH first_order AS (
  SELECT customer_unique_id, MIN(order_month_num) AS cohort_num
  FROM fact_orders
  WHERE is_valid = 1
  GROUP BY customer_unique_id
),
activity AS (
  SELECT DISTINCT o.customer_unique_id,
         f.cohort_num,
         o.order_month_num - f.cohort_num AS month_offset
  FROM fact_orders o
  JOIN first_order f ON f.customer_unique_id = o.customer_unique_id
  WHERE o.is_valid = 1
),
cohort_names AS (
  SELECT DISTINCT order_month_num, order_month FROM fact_orders
)
SELECT n.order_month                                                         AS cohort_month,
       SUM(CASE WHEN a.month_offset = 0 THEN 1 ELSE 0 END)                    AS cohort_size,
       ROUND(100.0 * SUM(CASE WHEN a.month_offset = 1 THEN 1 ELSE 0 END)
             / SUM(CASE WHEN a.month_offset = 0 THEN 1 ELSE 0 END), 2)        AS m1_retention_pct,
       ROUND(100.0 * SUM(CASE WHEN a.month_offset = 2 THEN 1 ELSE 0 END)
             / SUM(CASE WHEN a.month_offset = 0 THEN 1 ELSE 0 END), 2)        AS m2_retention_pct,
       ROUND(100.0 * SUM(CASE WHEN a.month_offset = 3 THEN 1 ELSE 0 END)
             / SUM(CASE WHEN a.month_offset = 0 THEN 1 ELSE 0 END), 2)        AS m3_retention_pct,
       ROUND(100.0 * SUM(CASE WHEN a.month_offset = 6 THEN 1 ELSE 0 END)
             / SUM(CASE WHEN a.month_offset = 0 THEN 1 ELSE 0 END), 2)        AS m6_retention_pct,
       ROUND(100.0 * COUNT(DISTINCT CASE WHEN a.month_offset > 0 THEN a.customer_unique_id END)
             / SUM(CASE WHEN a.month_offset = 0 THEN 1 ELSE 0 END), 2)        AS ever_returned_pct
FROM activity a
JOIN cohort_names n ON n.order_month_num = a.cohort_num
WHERE n.order_month BETWEEN '2017-01' AND '2018-08'
GROUP BY n.order_month
ORDER BY n.order_month;

-- @name: rfm_segments
-- Q8. RFM scoring.
--   Recency  : days since the last order, scored 5 (most recent) .. 1 with NTILE(5)
--   Frequency: ~97% of Olist customers order once, so NTILE would split
--              identical values at random. Fixed tiers are used instead.
--   Monetary : total GMV, NTILE(5)
WITH cust AS (
  SELECT customer_unique_id,
         MAX(purchase_day_num) AS last_day,
         COUNT(*)              AS frequency,
         SUM(order_gmv)        AS monetary
  FROM fact_orders
  WHERE is_valid = 1
  GROUP BY customer_unique_id
),
scored AS (
  SELECT customer_unique_id, frequency, monetary,
         MAX(last_day) OVER () - last_day                      AS recency_days,
         NTILE(5) OVER (ORDER BY last_day ASC)                 AS r_score,
         CASE WHEN frequency >= 3 THEN 5
              WHEN frequency = 2 THEN 4
              ELSE 1 END                                       AS f_score,
         NTILE(5) OVER (ORDER BY monetary ASC)                 AS m_score
  FROM cust
),
segmented AS (
  SELECT *,
         CASE
           WHEN r_score >= 4 AND f_score >= 4 AND m_score >= 4 THEN 'Champions'
           WHEN f_score >= 4                                   THEN 'Loyal'
           WHEN r_score >= 4 AND m_score >= 4                  THEN 'Promising High-Value'
           WHEN r_score >= 4                                   THEN 'New / Recent'
           WHEN r_score = 3                                    THEN 'Needs Attention'
           WHEN r_score <= 2 AND m_score >= 4                  THEN 'At Risk High-Value'
           ELSE 'Lost / Hibernating'
         END AS segment
  FROM scored
)
SELECT segment,
       COUNT(*)                                                 AS customers,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2)       AS pct_customers,
       ROUND(SUM(monetary), 2)                                  AS gmv,
       ROUND(100.0 * SUM(monetary) / SUM(SUM(monetary)) OVER (), 2) AS pct_gmv,
       ROUND(AVG(recency_days), 0)                              AS avg_recency_days,
       ROUND(AVG(frequency), 2)                                 AS avg_orders,
       ROUND(AVG(monetary), 2)                                  AS avg_gmv
FROM segmented
GROUP BY segment
ORDER BY gmv DESC;

-- @name: top_customers
-- Top 20 customers by lifetime GMV, with their share of total GMV.
WITH cust AS (
  SELECT customer_unique_id, MAX(customer_state) AS state,
         COUNT(*) AS orders, SUM(order_gmv) AS gmv
  FROM fact_orders
  WHERE is_valid = 1
  GROUP BY customer_unique_id
)
SELECT customer_unique_id, state, orders, ROUND(gmv, 2) AS gmv,
       ROUND(100.0 * gmv / SUM(gmv) OVER (), 3) AS pct_of_total_gmv
FROM cust
ORDER BY gmv DESC
LIMIT 20;

-- @name: new_vs_returning_by_month
-- Monthly orders split into first orders and repeat orders.
SELECT order_month,
       SUM(CASE WHEN is_first_order = 1 THEN 1 ELSE 0 END)   AS first_orders,
       SUM(CASE WHEN is_first_order = 0 THEN 1 ELSE 0 END)   AS repeat_orders,
       ROUND(100.0 * SUM(CASE WHEN is_first_order = 0 THEN 1 ELSE 0 END) / COUNT(*), 2)
                                                             AS repeat_order_pct
FROM fact_orders
WHERE is_valid = 1 AND in_analysis_window = 1
GROUP BY order_month
ORDER BY order_month;
