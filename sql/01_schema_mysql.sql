-- =====================================================================
-- 01  MySQL 8 SCHEMA - star schema for the Olist e-commerce project
--
-- Run this in MySQL Workbench first, then 02_load_mysql.sql.
-- The tables mirror the CSVs written by python/s01_clean_transform.py
-- and python/s04_customer_analytics.py into data/processed/.
--
--            dim_states
--                |
--          dim_customers ----< fact_orders
--                |
--                +-----------< fact_order_items >---- dim_products
--                                               >---- dim_sellers
--   fact_payments >---- fact_orders (order_id)
--   cohort_retention: standalone summary table
-- =====================================================================

CREATE DATABASE IF NOT EXISTS olist_analytics CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE olist_analytics;

DROP TABLE IF EXISTS fact_payments;
DROP TABLE IF EXISTS fact_order_items;
DROP TABLE IF EXISTS fact_orders;
DROP TABLE IF EXISTS cohort_retention;
DROP TABLE IF EXISTS dim_customers;
DROP TABLE IF EXISTS dim_products;
DROP TABLE IF EXISTS dim_sellers;
DROP TABLE IF EXISTS dim_states;

-- ---------------------------------------------------------------- dimensions
CREATE TABLE dim_states (
  state_code    CHAR(2)      PRIMARY KEY,
  state_name    VARCHAR(40)  NOT NULL,
  region        VARCHAR(20)  NOT NULL,
  map_location  VARCHAR(60)  NOT NULL
);

CREATE TABLE dim_customers (
  customer_unique_id  VARCHAR(32)   PRIMARY KEY,
  customer_city       VARCHAR(60),
  customer_state      CHAR(2),
  first_order_date    DATE,
  last_order_date     DATE,
  cohort_month        CHAR(7),
  cohort_month_num    INT,
  total_orders        INT           NOT NULL,
  total_gmv           DECIMAL(12,2) NOT NULL,
  customer_type       VARCHAR(20)   NOT NULL,
  recency_days        INT,
  r_score             TINYINT,
  f_score             TINYINT,
  m_score             TINYINT,
  rfm_code            CHAR(3),
  rfm_segment         VARCHAR(30)   NOT NULL,
  KEY ix_cust_state (customer_state)
);

CREATE TABLE dim_products (
  product_id           VARCHAR(32)  PRIMARY KEY,
  category             VARCHAR(80)  NOT NULL,
  category_portuguese  VARCHAR(80),
  product_photos_qty   INT,
  product_weight_g     INT,
  product_length_cm    INT,
  product_height_cm    INT,
  product_width_cm     INT
);

CREATE TABLE dim_sellers (
  seller_id               VARCHAR(32) PRIMARY KEY,
  seller_zip_code_prefix  INT,
  seller_city             VARCHAR(60),
  seller_state            CHAR(2)
);

-- --------------------------------------------------------------------- facts
CREATE TABLE fact_orders (
  order_id                       VARCHAR(32)   PRIMARY KEY,
  order_status                   VARCHAR(20)   NOT NULL,
  order_purchase_timestamp       DATETIME      NOT NULL,
  order_estimated_delivery_date  DATETIME,
  customer_unique_id             VARCHAR(32)   NOT NULL,
  customer_city                  VARCHAR(60),
  customer_state                 CHAR(2),
  is_valid                       TINYINT       NOT NULL,
  is_delivered                   TINYINT       NOT NULL,
  delivery_days                  DECIMAL(6,1),
  estimated_days                 DECIMAL(6,1),
  delay_days                     INT,
  is_late                        TINYINT,
  delay_bucket                   VARCHAR(20),
  purchase_date                  DATE          NOT NULL,
  order_year                     SMALLINT      NOT NULL,
  order_month                    CHAR(7)       NOT NULL,
  order_month_num                INT           NOT NULL,
  purchase_day_num               INT           NOT NULL,
  order_weekday                  CHAR(3)       NOT NULL,
  order_weekday_num              TINYINT       NOT NULL,
  order_hour                     TINYINT       NOT NULL,
  in_analysis_window             TINYINT       NOT NULL,
  items_count                    INT           NOT NULL,
  sellers_count                  INT           NOT NULL,
  product_revenue                DECIMAL(12,2),
  freight_value                  DECIMAL(12,2),
  order_gmv                      DECIMAL(12,2),
  payment_value                  DECIMAL(12,2),
  max_installments               INT,
  main_payment_type              VARCHAR(20),
  review_score                   TINYINT,
  has_comment                    TINYINT,
  is_first_order                 TINYINT       NOT NULL,
  KEY ix_orders_customer (customer_unique_id),
  KEY ix_orders_month (order_month),
  CONSTRAINT fk_orders_customer FOREIGN KEY (customer_unique_id)
    REFERENCES dim_customers (customer_unique_id)
);

CREATE TABLE fact_order_items (
  order_id            VARCHAR(32)   NOT NULL,
  order_item_id       INT           NOT NULL,
  product_id          VARCHAR(32)   NOT NULL,
  seller_id           VARCHAR(32)   NOT NULL,
  price               DECIMAL(10,2) NOT NULL,
  freight_value       DECIMAL(10,2) NOT NULL,
  item_gmv            DECIMAL(10,2) NOT NULL,
  customer_unique_id  VARCHAR(32)   NOT NULL,
  customer_state      CHAR(2),
  purchase_date       DATE          NOT NULL,
  order_month         CHAR(7)       NOT NULL,
  order_month_num     INT           NOT NULL,
  in_analysis_window  TINYINT       NOT NULL,
  is_valid            TINYINT       NOT NULL,
  is_delivered        TINYINT       NOT NULL,
  is_late             TINYINT,
  delivery_days       DECIMAL(6,1),
  review_score        TINYINT,
  category            VARCHAR(80)   NOT NULL,
  PRIMARY KEY (order_id, order_item_id),
  KEY ix_items_product (product_id),
  KEY ix_items_seller (seller_id),
  CONSTRAINT fk_items_order   FOREIGN KEY (order_id)   REFERENCES fact_orders (order_id),
  CONSTRAINT fk_items_product FOREIGN KEY (product_id) REFERENCES dim_products (product_id),
  CONSTRAINT fk_items_seller  FOREIGN KEY (seller_id)  REFERENCES dim_sellers (seller_id)
);

CREATE TABLE fact_payments (
  order_id              VARCHAR(32)   NOT NULL,
  payment_sequential    INT           NOT NULL,
  payment_type          VARCHAR(20)   NOT NULL,
  payment_installments  INT           NOT NULL,
  payment_value         DECIMAL(10,2) NOT NULL,
  purchase_date         DATE          NOT NULL,
  order_month           CHAR(7)       NOT NULL,
  is_valid              TINYINT       NOT NULL,
  in_analysis_window    TINYINT       NOT NULL,
  PRIMARY KEY (order_id, payment_sequential),
  CONSTRAINT fk_pay_order FOREIGN KEY (order_id) REFERENCES fact_orders (order_id)
);

CREATE TABLE cohort_retention (
  cohort_month   CHAR(7)      NOT NULL,
  month_offset   INT          NOT NULL,
  customers      INT          NOT NULL,
  cohort_size    INT          NOT NULL,
  retention_pct  DECIMAL(7,3) NOT NULL,
  PRIMARY KEY (cohort_month, month_offset)
);
