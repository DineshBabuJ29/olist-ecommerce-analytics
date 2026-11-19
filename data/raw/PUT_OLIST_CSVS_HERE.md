# Raw data goes here

1. Open https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce (free Kaggle login).
2. Click **Download** (`archive.zip`, ~43 MB).
3. Unzip it **into this folder**. You should see these files here:

```
olist_customers_dataset.csv
olist_geolocation_dataset.csv        (not used, can stay)
olist_order_items_dataset.csv
olist_order_payments_dataset.csv
olist_order_reviews_dataset.csv
olist_orders_dataset.csv
olist_products_dataset.csv
olist_sellers_dataset.csv
product_category_name_translation.csv
```

Never edit these files. All cleaning happens in `python/s01_clean_transform.py`,
so anyone can rerun the pipeline from the original data.
The raw files are git-ignored. Link to Kaggle instead of uploading them to GitHub.
