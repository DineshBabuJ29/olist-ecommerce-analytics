-- =====================================================================
-- 08  PAYMENT BEHAVIOUR
-- Business questions:
--   Q17  Which payment methods do customers use, and how much value?
--   Q18  Do instalments drive bigger baskets?
-- =====================================================================

-- @name: payment_method_mix
-- Q17. Main payment method per order (the method that paid the largest share).
SELECT main_payment_type,
       COUNT(*)                                                     AS orders,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2)           AS pct_orders,
       ROUND(SUM(payment_value), 2)                                 AS payment_value,
       ROUND(100.0 * SUM(payment_value) / SUM(SUM(payment_value)) OVER (), 2) AS pct_value,
       ROUND(AVG(payment_value), 2)                                 AS avg_order_payment
FROM fact_orders
WHERE is_valid = 1 AND main_payment_type IS NOT NULL
GROUP BY main_payment_type
ORDER BY orders DESC;

-- @name: installments_vs_basket
-- Q18. Credit-card orders only (only cards allow instalments).
SELECT CASE WHEN max_installments <= 1 THEN '1 (single payment)'
            WHEN max_installments <= 3 THEN '2-3'
            WHEN max_installments <= 6 THEN '4-6'
            ELSE '7+' END                                AS installments,
       COUNT(*)                                          AS orders,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct_orders,
       ROUND(AVG(order_gmv), 2)                          AS avg_order_value
FROM fact_orders
WHERE is_valid = 1 AND main_payment_type = 'credit_card'
GROUP BY CASE WHEN max_installments <= 1 THEN '1 (single payment)'
              WHEN max_installments <= 3 THEN '2-3'
              WHEN max_installments <= 6 THEN '4-6'
              ELSE '7+' END
ORDER BY installments;
