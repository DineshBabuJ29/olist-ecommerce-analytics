-- =====================================================================
-- 06  PRODUCT CATEGORY & SELLER PERFORMANCE
-- Business questions:
--   Q9   Which categories drive revenue, and how concentrated is it (Pareto)?
--   Q10  Which categories are growing fastest (H1-2018 vs H1-2017)?
--   Q11  Where is freight cost eating the basket (freight-to-price ratio)?
--   Q12  How concentrated is seller revenue, and which sellers hurt CX?
-- Item-level table: fact_order_items (one row per item sold).
-- =====================================================================

-- @name: category_performance
-- Q9. Category ranking with share, cumulative share (Pareto) and review score.
WITH cat AS (
  SELECT category,
         COUNT(DISTINCT order_id)   AS orders,
         COUNT(*)                   AS items_sold,
         SUM(price)                 AS revenue,
         AVG(price)                 AS avg_price,
         AVG(review_score)          AS avg_review,
         AVG(CASE WHEN is_delivered = 1 THEN is_late END) AS late_rate
  FROM fact_order_items
  WHERE is_valid = 1
  GROUP BY category
)
SELECT category, orders, items_sold,
       ROUND(revenue, 2)                                           AS revenue,
       ROUND(avg_price, 2)                                         AS avg_price,
       ROUND(avg_review, 2)                                        AS avg_review,
       ROUND(100.0 * late_rate, 2)                                 AS late_delivery_pct,
       RANK() OVER (ORDER BY revenue DESC)                         AS revenue_rank,
       ROUND(100.0 * revenue / SUM(revenue) OVER (), 2)            AS revenue_share_pct,
       ROUND(100.0 * SUM(revenue) OVER (ORDER BY revenue DESC
             ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
             / SUM(revenue) OVER (), 2)                            AS cumulative_share_pct
FROM cat
ORDER BY revenue DESC;

-- @name: category_growth_h1
-- Q10. First-half 2018 vs first-half 2017 revenue by category (categories with
-- at least 100 items in H1-2017 so that growth % is not driven by tiny bases).
WITH h1 AS (
  SELECT category,
         SUM(CASE WHEN order_month BETWEEN '2017-01' AND '2017-06' THEN price ELSE 0 END) AS rev_h1_2017,
         SUM(CASE WHEN order_month BETWEEN '2018-01' AND '2018-06' THEN price ELSE 0 END) AS rev_h1_2018,
         SUM(CASE WHEN order_month BETWEEN '2017-01' AND '2017-06' THEN 1 ELSE 0 END)     AS items_h1_2017
  FROM fact_order_items
  WHERE is_valid = 1
  GROUP BY category
)
SELECT category,
       ROUND(rev_h1_2017, 2)                                         AS rev_h1_2017,
       ROUND(rev_h1_2018, 2)                                         AS rev_h1_2018,
       ROUND(100.0 * (rev_h1_2018 - rev_h1_2017) / rev_h1_2017, 2)   AS growth_pct
FROM h1
WHERE items_h1_2017 >= 100
ORDER BY growth_pct DESC;

-- @name: freight_ratio_by_category
-- Q11. Categories where shipping is a large share of what the customer pays.
SELECT category,
       COUNT(*)                                         AS items_sold,
       ROUND(AVG(price), 2)                             AS avg_price,
       ROUND(AVG(freight_value), 2)                     AS avg_freight,
       ROUND(100.0 * SUM(freight_value) / SUM(price), 2) AS freight_to_price_pct
FROM fact_order_items
WHERE is_valid = 1
GROUP BY category
HAVING COUNT(*) >= 200
ORDER BY freight_to_price_pct DESC;

-- @name: seller_concentration
-- Q12a. Split sellers into 10 equal groups by revenue (decile 1 = top 10%).
WITH s AS (
  SELECT seller_id, SUM(price) AS revenue
  FROM fact_order_items
  WHERE is_valid = 1
  GROUP BY seller_id
),
d AS (
  SELECT seller_id, revenue, NTILE(10) OVER (ORDER BY revenue DESC) AS decile
  FROM s
)
SELECT decile,
       COUNT(*)                                                  AS sellers,
       ROUND(SUM(revenue), 2)                                    AS revenue,
       ROUND(100.0 * SUM(revenue) / SUM(SUM(revenue)) OVER (), 2) AS revenue_share_pct
FROM d
GROUP BY decile
ORDER BY decile;

-- @name: seller_scorecard
-- Q12b. Sellers with 30+ orders: revenue, CX (review, late %) and a combined flag.
WITH s AS (
  SELECT i.seller_id, ds.seller_state,
         COUNT(DISTINCT i.order_id)                         AS orders,
         SUM(i.price)                                       AS revenue,
         AVG(i.review_score)                                AS avg_review,
         AVG(CASE WHEN i.is_delivered = 1 THEN i.is_late END) AS late_rate
  FROM fact_order_items i
  JOIN dim_sellers ds ON ds.seller_id = i.seller_id
  WHERE i.is_valid = 1
  GROUP BY i.seller_id, ds.seller_state
)
SELECT seller_id, seller_state, orders,
       ROUND(revenue, 2)                        AS revenue,
       ROUND(avg_review, 2)                     AS avg_review,
       ROUND(100.0 * late_rate, 2)              AS late_delivery_pct,
       RANK() OVER (ORDER BY revenue DESC)      AS revenue_rank,
       CASE WHEN avg_review < 3.5 OR late_rate > 0.15 THEN 'Review seller'
            ELSE 'OK' END                       AS cx_flag
FROM s
WHERE orders >= 30
ORDER BY revenue DESC;

-- @name: seller_cx_flag_summary
-- How much revenue sits with sellers whose customer experience is poor?
WITH s AS (
  SELECT seller_id,
         COUNT(DISTINCT order_id)                         AS orders,
         SUM(price)                                       AS revenue,
         AVG(review_score)                                AS avg_review,
         AVG(CASE WHEN is_delivered = 1 THEN is_late END) AS late_rate
  FROM fact_order_items
  WHERE is_valid = 1
  GROUP BY seller_id
)
SELECT CASE WHEN avg_review < 3.5 OR late_rate > 0.15 THEN 'Review seller' ELSE 'OK' END AS cx_flag,
       COUNT(*)                                                    AS sellers,
       ROUND(SUM(revenue), 2)                                      AS revenue,
       ROUND(100.0 * SUM(revenue) / SUM(SUM(revenue)) OVER (), 2)  AS revenue_share_pct
FROM s
WHERE orders >= 30
GROUP BY CASE WHEN avg_review < 3.5 OR late_rate > 0.15 THEN 'Review seller' ELSE 'OK' END;
