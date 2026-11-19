"""
Central configuration: every script imports its paths and settings from here,
so nothing is hard-coded twice.
"""
from pathlib import Path

# Project root = the folder that contains /python, /sql, /data ...
ROOT = Path(__file__).resolve().parents[1]

RAW_DIR = ROOT / "data" / "raw"            # the 9 Kaggle CSVs go here (untouched)
PROCESSED_DIR = ROOT / "data" / "processed"  # clean star-schema tables (SQL + Power BI read these)
DB_PATH = ROOT / "data" / "olist.db"         # SQLite copy used to run/verify the SQL files
SQL_DIR = ROOT / "sql"
OUTPUT_DIR = ROOT / "outputs"
FIGURE_DIR = OUTPUT_DIR / "figures"
SQL_RESULT_DIR = OUTPUT_DIR / "sql_results"

# Olist data runs Sep-2016 .. Oct-2018, but 2016 and Sep/Oct-2018 contain only a
# handful of orders (collection start/end). Trend analysis uses complete months only.
ANALYSIS_START_MONTH = "2017-01"
ANALYSIS_END_MONTH = "2018-08"

# Order statuses that never became a sale.
INVALID_STATUSES = ["canceled", "unavailable"]

RAW_FILES = {
    "customers": "olist_customers_dataset.csv",
    "orders": "olist_orders_dataset.csv",
    "items": "olist_order_items_dataset.csv",
    "payments": "olist_order_payments_dataset.csv",
    "reviews": "olist_order_reviews_dataset.csv",
    "products": "olist_products_dataset.csv",
    "sellers": "olist_sellers_dataset.csv",
    "category_translation": "product_category_name_translation.csv",
    # olist_geolocation_dataset.csv (1M rows) is intentionally not used:
    # state-level geography is enough for the business questions here.
}

# Brazilian state code -> (state name, region). Used for maps and regional rollups.
BRAZIL_STATES = {
    "AC": ("Acre", "North"), "AL": ("Alagoas", "Northeast"), "AP": ("Amapa", "North"),
    "AM": ("Amazonas", "North"), "BA": ("Bahia", "Northeast"), "CE": ("Ceara", "Northeast"),
    "DF": ("Distrito Federal", "Central-West"), "ES": ("Espirito Santo", "Southeast"),
    "GO": ("Goias", "Central-West"), "MA": ("Maranhao", "Northeast"),
    "MT": ("Mato Grosso", "Central-West"), "MS": ("Mato Grosso do Sul", "Central-West"),
    "MG": ("Minas Gerais", "Southeast"), "PA": ("Para", "North"), "PB": ("Paraiba", "Northeast"),
    "PR": ("Parana", "South"), "PE": ("Pernambuco", "Northeast"), "PI": ("Piaui", "Northeast"),
    "RJ": ("Rio de Janeiro", "Southeast"), "RN": ("Rio Grande do Norte", "Northeast"),
    "RS": ("Rio Grande do Sul", "South"), "RO": ("Rondonia", "North"), "RR": ("Roraima", "North"),
    "SC": ("Santa Catarina", "South"), "SP": ("Sao Paulo", "Southeast"),
    "SE": ("Sergipe", "Northeast"), "TO": ("Tocantins", "North"),
}

# Two Portuguese categories are missing from Olist's own translation file.
EXTRA_CATEGORY_TRANSLATIONS = {
    "pc_gamer": "pc_gamer",
    "portateis_cozinha_e_preparadores_de_alimentos": "portable_kitchen_food_preparers",
}


def ensure_dirs() -> None:
    for d in (PROCESSED_DIR, OUTPUT_DIR, FIGURE_DIR, SQL_RESULT_DIR):
        d.mkdir(parents=True, exist_ok=True)
