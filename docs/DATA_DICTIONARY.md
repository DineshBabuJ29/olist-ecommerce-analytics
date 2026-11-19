# Data Dictionary

## Source
**Brazilian E-Commerce Public Dataset by Olist** (Kaggle, CC BY-NC-SA 4.0). These are real, anonymised
orders from the Olist marketplace in Brazil, Sep 2016 - Oct 2018: ~99k orders, ~96k customers,
~3k sellers, 32k products. Company and partner names were replaced, and review text is in Portuguese.

### Raw tables and how they join
```
customers (customer_id) --< orders (order_id) --< order_items >-- products (product_id)
                                  |                    >-- sellers (seller_id)
                                  +--< payments
                                  +--< reviews
products.product_category_name --> category_translation
```
**The main trap in this dataset:** `customer_id` is created **per order**. The real person is
`customer_unique_id`. Counting `customer_id` makes repeat purchases look like 0%.

## Business definitions (used the same way in SQL, Python and DAX)
| Term | Definition |
|---|---|
| Valid order | `order_status` not in (`canceled`, `unavailable`) |
| Product revenue | Sum of item `price` |
| Freight | Sum of item `freight_value` (shipping charged to the customer) |
| **GMV** | Product revenue + freight (the amount the customer paid for the goods and delivery) |
| **AOV** | GMV / number of valid orders |
| Customer | A distinct `customer_unique_id` |
| Repeat customer | A customer with 2 or more valid orders |
| Delivered order | Status `delivered` with a valid delivery date that is after the purchase date |
| **Late** | Delivered on a later calendar day than `order_estimated_delivery_date` |
| Negative review | Review score of 1 or 2 |
| Cohort | Month of a customer's first valid order |
| Month-N retention | % of a cohort that ordered again N calendar months after their first order |
| Analysis window | Jan 2017 - Aug 2018. The months outside it are incomplete (data collection start/end) |

## Processed tables (`data/processed/`)

### fact_orders: one row per order
| Column | Meaning |
|---|---|
| order_id | Order key |
| order_status | delivered, shipped, canceled, ... |
| order_purchase_timestamp / order_estimated_delivery_date | Raw timestamps |
| customer_unique_id, customer_city, customer_state | Real customer and location |
| is_valid / is_delivered / is_late | 0/1 flags (see definitions) |
| delivery_days | Purchase to delivery, in days (delivered orders only) |
| estimated_days | Purchase to promised date, in days |
| delay_days | Delivered date minus promised date (negative = early) |
| delay_bucket | Early 8+ / Early 1-7 / On the day / Late 1-3 / Late 4-7 / Late 8+ |
| purchase_date, order_year, order_month | Calendar fields |
| order_month_num | year*12 + month (for cohort maths without date functions) |
| purchase_day_num | Days since 2016-01-01 (for recency without date functions) |
| order_weekday(_num), order_hour | Purchase timing |
| in_analysis_window | 1 if Jan 2017 - Aug 2018 |
| items_count, sellers_count | Basket size |
| product_revenue, freight_value, order_gmv | Money (BRL) |
| payment_value, max_installments, main_payment_type | Payment summary |
| review_score, has_comment | Latest review for the order |
| is_first_order | 1 = the customer's first valid order (new-customer measure) |

### fact_order_items: one row per item sold
`order_id, order_item_id, product_id, seller_id, price, freight_value, item_gmv` plus order-level
copies (`customer_unique_id, customer_state, purchase_date, order_month, is_valid, is_delivered,
is_late, delivery_days, review_score`) and `category`. The copies are there so product and seller
analysis doesn't need a fact-to-fact join.

### fact_payments: one row per payment record
`order_id, payment_sequential, payment_type, payment_installments, payment_value` + date fields.

### dim_customers: one row per customer_unique_id
Location, `first_order_date`, `last_order_date`, `cohort_month`, `total_orders`, `total_gmv`,
`customer_type` (One-time / Repeat), and RFM fields: `recency_days`, `r_score`, `f_score`, `m_score`,
`rfm_code`, `rfm_segment`.

### dim_products
`product_id`, `category` (English, title case; "Unknown" when missing), `category_portuguese`,
weight and dimensions.

### dim_sellers / dim_states
Seller location; Brazilian state code to name, region and `map_location` (for Power BI maps).

### cohort_retention
`cohort_month, month_offset, customers, cohort_size, retention_pct`: long format, ready for a matrix heat-map.

## RFM scoring
| Score | Rule |
|---|---|
| R (1-5) | Quintile of days since last order (5 = most recent) |
| F | 1 order = 1, 2 orders = 4, 3+ orders = 5. Fixed tiers, because ~97% of customers order once, so quintiles would be meaningless |
| M (1-5) | Quintile of lifetime GMV |

| Segment | Rule (checked in this order) |
|---|---|
| Champions | R>=4, F>=4, M>=4 |
| Loyal | F>=4 |
| Promising High-Value | R>=4, M>=4 |
| New / Recent | R>=4 |
| Needs Attention | R=3 |
| At Risk High-Value | R<=2, M>=4 |
| Lost / Hibernating | everything else |
