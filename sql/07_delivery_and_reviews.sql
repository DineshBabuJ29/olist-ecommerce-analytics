-- =====================================================================
-- 07  DELIVERY PERFORMANCE & CUSTOMER SATISFACTION
-- Business questions:
--   Q13  How often do we miss the promised delivery date?
--   Q14  How much does a late delivery hurt the review score?
--   Q15  Which states have the worst delivery experience?
--   Q16  Is delivery getting better or worse over time?
-- Scope: delivered orders only (is_delivered = 1).
-- =====================================================================

-- @name: delivery_kpis
-- Q13
SELECT COUNT(*)                                       AS delivered_orders,
       ROUND(AVG(delivery_days), 1)                   AS avg_delivery_days,
       ROUND(AVG(estimated_days), 1)                  AS avg_promised_days,
       ROUND(100.0 * AVG(is_late), 2)                 AS late_delivery_pct,
       ROUND(AVG(review_score), 2)                    AS avg_review_score
FROM fact_orders
WHERE is_delivered = 1;

-- @name: review_score_distribution
SELECT review_score,
       COUNT(*)                                            AS orders,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2)  AS pct_of_reviews
FROM fact_orders
WHERE is_valid = 1 AND review_score IS NOT NULL
GROUP BY review_score
ORDER BY review_score;

-- @name: late_vs_ontime_reviews
-- Q14. Headline comparison. A 1-2 star review counts as negative.
SELECT CASE WHEN is_late = 1 THEN 'Late' ELSE 'On time / early' END     AS delivery_status,
       COUNT(*)                                                         AS orders,
       ROUND(AVG(review_score), 2)                                      AS avg_review,
       ROUND(100.0 * AVG(CASE WHEN review_score <= 2 THEN 1.0 ELSE 0 END), 2) AS negative_review_pct,
       ROUND(100.0 * AVG(CASE WHEN review_score = 5 THEN 1.0 ELSE 0 END), 2)  AS five_star_pct
FROM fact_orders
WHERE is_delivered = 1 AND review_score IS NOT NULL
GROUP BY CASE WHEN is_late = 1 THEN 'Late' ELSE 'On time / early' END;

-- @name: review_by_delay_bucket
-- Q14 (detail). How the review score changes as the delay grows.
SELECT delay_bucket,
       COUNT(*)                                                         AS orders,
       ROUND(AVG(review_score), 2)                                      AS avg_review,
       ROUND(100.0 * AVG(CASE WHEN review_score <= 2 THEN 1.0 ELSE 0 END), 2) AS negative_review_pct
FROM fact_orders
WHERE is_delivered = 1 AND review_score IS NOT NULL
GROUP BY delay_bucket
ORDER BY delay_bucket;

-- @name: delivery_by_state
-- Q15. States with 300+ delivered orders, worst late rate first.
SELECT o.customer_state, s.state_name, s.region,
       COUNT(*)                                  AS delivered_orders,
       ROUND(AVG(o.delivery_days), 1)            AS avg_delivery_days,
       ROUND(AVG(o.estimated_days), 1)           AS avg_promised_days,
       ROUND(100.0 * AVG(o.is_late), 2)          AS late_delivery_pct,
       ROUND(AVG(o.review_score), 2)             AS avg_review,
       ROUND(AVG(o.freight_value), 2)            AS avg_freight
FROM fact_orders o
JOIN dim_states s ON s.state_code = o.customer_state
WHERE o.is_delivered = 1
GROUP BY o.customer_state, s.state_name, s.region
HAVING COUNT(*) >= 300
ORDER BY late_delivery_pct DESC;

-- @name: delivery_trend_monthly
-- Q16
SELECT order_month,
       COUNT(*)                                  AS delivered_orders,
       ROUND(AVG(delivery_days), 1)              AS avg_delivery_days,
       ROUND(100.0 * AVG(is_late), 2)            AS late_delivery_pct,
       ROUND(AVG(review_score), 2)               AS avg_review
FROM fact_orders
WHERE is_delivered = 1 AND in_analysis_window = 1
GROUP BY order_month
ORDER BY order_month;
