-- =====================================================================
-- 02  LOAD THE PROCESSED CSVs INTO MySQL 8
--
-- Before running:
--   1. Run python/run_all.py so that data/processed/ contains the CSVs.
--   2. Allow local file loading (one time):
--        * Server:     SET GLOBAL local_infile = 1;   (needs an admin account)
--        * Workbench:  Edit connection -> Advanced -> Others: OPT_LOCAL_INFILE=1
--   3. If your project folder is somewhere else, find/replace the path below.
--      Use forward slashes (/) in the path, even on Windows.
--
-- Empty CSV cells are loaded into @variables and converted with NULLIF(),
-- so a missing value becomes NULL, not 0 or ''.
-- Tables load in foreign-key order: dimensions first, then facts.
-- =====================================================================
USE olist_analytics;

LOAD DATA LOCAL INFILE 'C:/Users/Dinesh Babu J/Downloads/Ecommerce_Analytics_Olist/data/processed/dim_states.csv'
INTO TABLE dim_states
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' LINES TERMINATED BY '\n' IGNORE 1 LINES
(state_code, state_name, region, map_location);

LOAD DATA LOCAL INFILE 'C:/Users/Dinesh Babu J/Downloads/Ecommerce_Analytics_Olist/data/processed/dim_customers.csv'
INTO TABLE dim_customers
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' LINES TERMINATED BY '\n' IGNORE 1 LINES
(customer_unique_id, @city, @state, @first, @last, @cohort, @cohort_num, total_orders, total_gmv,
 customer_type, @recency, @r, @f, @m, @rfm_code, rfm_segment)
SET customer_city    = NULLIF(@city, ''),
    customer_state   = NULLIF(@state, ''),
    first_order_date = NULLIF(@first, ''),
    last_order_date  = NULLIF(@last, ''),
    cohort_month     = NULLIF(@cohort, ''),
    cohort_month_num = NULLIF(@cohort_num, ''),
    recency_days     = NULLIF(@recency, ''),
    r_score          = NULLIF(@r, ''),
    f_score          = NULLIF(@f, ''),
    m_score          = NULLIF(@m, ''),
    rfm_code         = NULLIF(@rfm_code, '');

LOAD DATA LOCAL INFILE 'C:/Users/Dinesh Babu J/Downloads/Ecommerce_Analytics_Olist/data/processed/dim_products.csv'
INTO TABLE dim_products
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' LINES TERMINATED BY '\n' IGNORE 1 LINES
(product_id, category, @cat_pt, @photos, @weight, @len, @height, @width)
SET category_portuguese = NULLIF(@cat_pt, ''),
    product_photos_qty  = NULLIF(@photos, ''),
    product_weight_g    = NULLIF(@weight, ''),
    product_length_cm   = NULLIF(@len, ''),
    product_height_cm   = NULLIF(@height, ''),
    product_width_cm    = NULLIF(@width, '');

LOAD DATA LOCAL INFILE 'C:/Users/Dinesh Babu J/Downloads/Ecommerce_Analytics_Olist/data/processed/dim_sellers.csv'
INTO TABLE dim_sellers
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' LINES TERMINATED BY '\n' IGNORE 1 LINES
(seller_id, seller_zip_code_prefix, seller_city, seller_state);

LOAD DATA LOCAL INFILE 'C:/Users/Dinesh Babu J/Downloads/Ecommerce_Analytics_Olist/data/processed/fact_orders.csv'
INTO TABLE fact_orders
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' LINES TERMINATED BY '\n' IGNORE 1 LINES
(order_id, order_status, order_purchase_timestamp, @est_date, customer_unique_id, @city, @state,
 is_valid, is_delivered, @delivery_days, @estimated_days, @delay_days, @is_late, @delay_bucket,
 purchase_date, order_year, order_month, order_month_num, purchase_day_num, order_weekday,
 order_weekday_num, order_hour, in_analysis_window, items_count, sellers_count,
 @product_revenue, @freight, @gmv, @payment, @installments, @pay_type, @review, @has_comment,
 is_first_order)
SET order_estimated_delivery_date = NULLIF(@est_date, ''),
    customer_city      = NULLIF(@city, ''),
    customer_state     = NULLIF(@state, ''),
    delivery_days      = NULLIF(@delivery_days, ''),
    estimated_days     = NULLIF(@estimated_days, ''),
    delay_days         = NULLIF(@delay_days, ''),
    is_late            = NULLIF(@is_late, ''),
    delay_bucket       = NULLIF(@delay_bucket, ''),
    product_revenue    = NULLIF(@product_revenue, ''),
    freight_value      = NULLIF(@freight, ''),
    order_gmv          = NULLIF(@gmv, ''),
    payment_value      = NULLIF(@payment, ''),
    max_installments   = NULLIF(@installments, ''),
    main_payment_type  = NULLIF(@pay_type, ''),
    review_score       = NULLIF(@review, ''),
    has_comment        = NULLIF(@has_comment, '');

LOAD DATA LOCAL INFILE 'C:/Users/Dinesh Babu J/Downloads/Ecommerce_Analytics_Olist/data/processed/fact_order_items.csv'
INTO TABLE fact_order_items
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' LINES TERMINATED BY '\n' IGNORE 1 LINES
(order_id, order_item_id, product_id, seller_id, price, freight_value, item_gmv, customer_unique_id,
 @state, purchase_date, order_month, order_month_num, in_analysis_window, is_valid, is_delivered,
 @is_late, @delivery_days, @review, category)
SET customer_state = NULLIF(@state, ''),
    is_late        = NULLIF(@is_late, ''),
    delivery_days  = NULLIF(@delivery_days, ''),
    review_score   = NULLIF(@review, '');

LOAD DATA LOCAL INFILE 'C:/Users/Dinesh Babu J/Downloads/Ecommerce_Analytics_Olist/data/processed/fact_payments.csv'
INTO TABLE fact_payments
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' LINES TERMINATED BY '\n' IGNORE 1 LINES
(order_id, payment_sequential, payment_type, payment_installments, payment_value, purchase_date,
 order_month, is_valid, in_analysis_window);

LOAD DATA LOCAL INFILE 'C:/Users/Dinesh Babu J/Downloads/Ecommerce_Analytics_Olist/data/processed/cohort_retention.csv'
INTO TABLE cohort_retention
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' LINES TERMINATED BY '\n' IGNORE 1 LINES
(cohort_month, month_offset, customers, cohort_size, retention_pct);

-- Quick check: the counts should match the "PROCESSED TABLES" printout of s01_clean_transform.py
SELECT 'fact_orders' AS t, COUNT(*) AS n FROM fact_orders
UNION ALL SELECT 'fact_order_items', COUNT(*) FROM fact_order_items
UNION ALL SELECT 'fact_payments', COUNT(*) FROM fact_payments
UNION ALL SELECT 'dim_customers', COUNT(*) FROM dim_customers
UNION ALL SELECT 'dim_products', COUNT(*) FROM dim_products
UNION ALL SELECT 'dim_sellers', COUNT(*) FROM dim_sellers
UNION ALL SELECT 'cohort_retention', COUNT(*) FROM cohort_retention;
SHOW WARNINGS LIMIT 20;
