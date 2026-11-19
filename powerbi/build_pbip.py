"""
Generate the Power BI Project (.pbip) for the Olist dashboard.

    python powerbi/build_pbip.py

Writes powerbi/Olist_Ecommerce_Dashboard.pbip plus two folders:
  Olist_Ecommerce_Dashboard.SemanticModel/  data model: Power Query, types, relationships, DAX measures
  Olist_Ecommerce_Dashboard.Report/         4 report pages and their visuals

Open the .pbip in Power BI Desktop, click Refresh, then File > Save As .pbix.

A .pbip is Power BI's text-based project format (the same model and report as a .pbix, stored
as JSON). That's why it can be generated from code and kept in Git.
"""
import json
import shutil
import sys
import uuid
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "python"))
import config as C  # noqa: E402

NAME = "Olist_Ecommerce_Dashboard"
SM_DIR = HERE / f"{NAME}.SemanticModel"
RPT_DIR = HERE / f"{NAME}.Report"
M = "_Measures"

# --------------------------------------------------------------------------- #
# 1. SEMANTIC MODEL
# --------------------------------------------------------------------------- #
TABLES = ["fact_orders", "fact_order_items", "fact_payments", "dim_customers",
          "dim_products", "dim_sellers", "dim_states", "cohort_retention"]

TEXT_COLS = {"order_id", "customer_unique_id", "product_id", "seller_id", "rfm_code", "order_month",
             "cohort_month", "delay_bucket", "state_code", "customer_state", "seller_state",
             "seller_zip_code_prefix", "customer_city", "seller_city"}
DATE_COLS = {"purchase_date", "first_order_date", "last_order_date"}
DATETIME_COLS = {"order_purchase_timestamp", "order_estimated_delivery_date"}


def column_types(table: str):
    """Infer (column, tmsl_type, m_type) from the processed CSV."""
    df = pd.read_csv(C.PROCESSED_DIR / f"{table}.csv", low_memory=False)
    out = []
    for col in df.columns:
        s = df[col]
        if col in DATE_COLS:
            out.append((col, "dateTime", "type date"))
        elif col in DATETIME_COLS:
            out.append((col, "dateTime", "type datetime"))
        elif col in TEXT_COLS or s.dtype == object:
            out.append((col, "string", "type text"))
        elif pd.api.types.is_integer_dtype(s) or (s.dropna() % 1 == 0).all():
            out.append((col, "int64", "Int64.Type"))
        else:
            out.append((col, "double", "type number"))
    return out


def csv_partition(table: str, types):
    type_list = ", ".join(f'{{"{c}", {m}}}' for c, _, m in types)
    return [
        "let",
        f'    Source = Csv.Document(File.Contents(DataFolder & "{table}.csv"), '
        '[Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),',
        "    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),",
        "    // empty CSV cells -> null, so numeric columns convert cleanly",
        '    Blanks = Table.TransformColumns(Promoted, {}, each if _ = "" then null else _),',
        f'    Typed = Table.TransformColumnTypes(Blanks, {{{type_list}}}, "en-US")',
        "in",
        "    Typed",
    ]


DATE_M = [
    "let",
    "    StartDate = #date(2016, 9, 1),",
    "    EndDate = #date(2018, 10, 31),",
    "    Dates = List.Dates(StartDate, Duration.Days(EndDate - StartDate) + 1, #duration(1, 0, 0, 0)),",
    '    T0 = Table.FromList(Dates, Splitter.SplitByNothing(), {"Date"}),',
    '    T1 = Table.TransformColumnTypes(T0, {{"Date", type date}}),',
    '    T2 = Table.AddColumn(T1, "Year", each Date.Year([Date]), Int64.Type),',
    '    T3 = Table.AddColumn(T2, "Quarter", each "Q" & Text.From(Date.QuarterOfYear([Date])), type text),',
    '    T4 = Table.AddColumn(T3, "Month Num", each Date.Month([Date]), Int64.Type),',
    '    T5 = Table.AddColumn(T4, "Month", each Date.ToText([Date], "MMM", "en-US"), type text),',
    '    T6 = Table.AddColumn(T5, "Year Month", each Date.ToText([Date], "yyyy-MM", "en-US"), type text),',
    '    T7 = Table.AddColumn(T6, "Weekday", each Date.ToText([Date], "ddd", "en-US"), type text),',
    '    T8 = Table.AddColumn(T7, "Weekday Num", each Date.DayOfWeek([Date], Day.Monday) + 1, Int64.Type),',
    '    T9 = Table.AddColumn(T8, "In Analysis Window", each if [Date] >= #date(2017, 1, 1) '
    'and [Date] <= #date(2018, 8, 31) then 1 else 0, Int64.Type)',
    "in",
    "    T9",
]
DATE_COLUMNS = [("Date", "dateTime"), ("Year", "int64"), ("Quarter", "string"), ("Month Num", "int64"),
                ("Month", "string"), ("Year Month", "string"), ("Weekday", "string"),
                ("Weekday Num", "int64"), ("In Analysis Window", "int64")]

# (name, DAX, format string, display folder)
MONEY = '"R$" #,0'
MONEY2 = '"R$" #,0.00'
PCT = "0.0%"
MEASURES = [
    # ---- Sales
    ("Orders", "CALCULATE ( COUNTROWS ( fact_orders ), fact_orders[is_valid] = 1 )", "#,0", "Sales"),
    ("GMV", "CALCULATE ( SUM ( fact_orders[order_gmv] ), fact_orders[is_valid] = 1 )", MONEY, "Sales"),
    ("Product Revenue", "CALCULATE ( SUM ( fact_orders[product_revenue] ), fact_orders[is_valid] = 1 )", MONEY, "Sales"),
    ("Freight Revenue", "CALCULATE ( SUM ( fact_orders[freight_value] ), fact_orders[is_valid] = 1 )", MONEY, "Sales"),
    ("AOV", "DIVIDE ( [GMV], [Orders] )", MONEY2, "Sales"),
    ("Items per Order", "DIVIDE ( CALCULATE ( SUM ( fact_orders[items_count] ), fact_orders[is_valid] = 1 ), [Orders] )", "0.00", "Sales"),
    ("Cancellation Rate %", "DIVIDE ( CALCULATE ( COUNTROWS ( fact_orders ), fact_orders[is_valid] = 0 ), COUNTROWS ( fact_orders ) )", PCT, "Sales"),
    # ---- Customers
    ("Customers", "CALCULATE ( DISTINCTCOUNT ( fact_orders[customer_unique_id] ), fact_orders[is_valid] = 1 )", "#,0", "Customers"),
    ("New Customers", "CALCULATE ( DISTINCTCOUNT ( fact_orders[customer_unique_id] ), fact_orders[is_valid] = 1, fact_orders[is_first_order] = 1 )", "#,0", "Customers"),
    # customers who placed a repeat (not-first) order in the selected period
    ("Returning Customers", "CALCULATE ( DISTINCTCOUNT ( fact_orders[customer_unique_id] ), fact_orders[is_valid] = 1, fact_orders[is_first_order] = 0 )", "#,0", "Customers"),
    ("Repeat Customer Rate %", "DIVIDE ( CALCULATE ( COUNTROWS ( dim_customers ), dim_customers[total_orders] >= 2 ), CALCULATE ( COUNTROWS ( dim_customers ), dim_customers[total_orders] >= 1 ) )", "0.00%", "Customers"),
    ("GMV per Customer", "DIVIDE ( [GMV], [Customers] )", MONEY2, "Customers"),
    ("Cohort Retention %",
     "VAR Offset = SELECTEDVALUE ( cohort_retention[month_offset] )\n"
     "RETURN IF ( Offset >= 1 && Offset <= 12, DIVIDE ( SUM ( cohort_retention[customers] ), MAX ( cohort_retention[cohort_size] ) ) )",
     "0.00%", "Customers"),
    # ---- Delivery & CX
    ("Delivered Orders", "CALCULATE ( COUNTROWS ( fact_orders ), fact_orders[is_delivered] = 1 )", "#,0", "Delivery & CX"),
    ("Late Orders", "CALCULATE ( COUNTROWS ( fact_orders ), fact_orders[is_late] = 1 )", "#,0", "Delivery & CX"),
    ("Late Delivery %", "DIVIDE ( [Late Orders], [Delivered Orders] )", PCT, "Delivery & CX"),
    ("Avg Delivery Days", "CALCULATE ( AVERAGE ( fact_orders[delivery_days] ), fact_orders[is_delivered] = 1 )", "0.0", "Delivery & CX"),
    ("Avg Promised Days", "CALCULATE ( AVERAGE ( fact_orders[estimated_days] ), fact_orders[is_delivered] = 1 )", "0.0", "Delivery & CX"),
    ("Avg Review Score", "CALCULATE ( AVERAGE ( fact_orders[review_score] ), fact_orders[is_valid] = 1 )", "0.00", "Delivery & CX"),
    ("Negative Review %",
     # NOT ISBLANK is required: in DAX, BLANK <= 2 is TRUE, so orders without a review would count as negative
     "DIVIDE (\n    CALCULATE ( COUNTROWS ( fact_orders ), fact_orders[review_score] <= 2, NOT ISBLANK ( fact_orders[review_score] ), fact_orders[is_valid] = 1 ),\n"
     "    CALCULATE ( COUNTROWS ( fact_orders ), NOT ISBLANK ( fact_orders[review_score] ), fact_orders[is_valid] = 1 )\n)",
     PCT, "Delivery & CX"),
    # is_delivered = 1 is required: in DAX, BLANK = 0 is TRUE, so undelivered orders would count as "on time"
    ("Avg Review (Delivered)", "CALCULATE ( [Avg Review Score], fact_orders[is_delivered] = 1 )", "0.00", "Delivery & CX"),
    ("Avg Review (Late)", "CALCULATE ( [Avg Review Score], fact_orders[is_delivered] = 1, fact_orders[is_late] = 1 )", "0.00", "Delivery & CX"),
    ("Avg Review (On Time)", "CALCULATE ( [Avg Review Score], fact_orders[is_delivered] = 1, fact_orders[is_late] = 0 )", "0.00", "Delivery & CX"),
    ("Review Gap Late vs On Time", "[Avg Review (On Time)] - [Avg Review (Late)]", "0.00", "Delivery & CX"),
    ("Insight Late Reviews",
     '"Late orders average " & FORMAT ( [Avg Review (Late)], "0.00" ) & " stars vs " & FORMAT ( [Avg Review (On Time)], "0.00" ) & " for on-time orders"',
     None, "Delivery & CX"),
    # ---- Time intelligence
    ("GMV PM", "CALCULATE ( [GMV], DATEADD ( 'Date'[Date], -1, MONTH ) )", MONEY, "Time Intelligence"),
    ("GMV MoM %", "DIVIDE ( [GMV] - [GMV PM], [GMV PM] )", PCT, "Time Intelligence"),
    ("GMV PY", "CALCULATE ( [GMV], SAMEPERIODLASTYEAR ( 'Date'[Date] ) )", MONEY, "Time Intelligence"),
    ("GMV YoY %", "DIVIDE ( [GMV] - [GMV PY], [GMV PY] )", PCT, "Time Intelligence"),
    ("GMV YTD", "TOTALYTD ( [GMV], 'Date'[Date] )", MONEY, "Time Intelligence"),
    ("GMV 3M Moving Avg",
     "VAR Months =\n    CALCULATETABLE ( VALUES ( 'Date'[Year Month] ), DATESINPERIOD ( 'Date'[Date], MAX ( 'Date'[Date] ), -3, MONTH ) )\n"
     "RETURN\n    AVERAGEX ( Months, VAR ym = 'Date'[Year Month] RETURN CALCULATE ( [GMV], REMOVEFILTERS ( 'Date' ), 'Date'[Year Month] = ym ) )",
     MONEY, "Time Intelligence"),
    ("Orders PY", "CALCULATE ( [Orders], SAMEPERIODLASTYEAR ( 'Date'[Date] ) )", "#,0", "Time Intelligence"),
    ("Orders YoY %", "DIVIDE ( [Orders] - [Orders PY], [Orders PY] )", PCT, "Time Intelligence"),
    # Trend versions: blank outside Jan-2017..Aug-2018 so charts skip the incomplete months
    ("GMV (Trend)", "IF ( MAX ( 'Date'[In Analysis Window] ) = 1, [GMV] )", MONEY, "Time Intelligence"),
    ("Orders (Trend)", "IF ( MAX ( 'Date'[In Analysis Window] ) = 1, [Orders] )", "#,0", "Time Intelligence"),
    ("GMV 3M Moving Avg (Trend)", "IF ( MAX ( 'Date'[In Analysis Window] ) = 1, [GMV 3M Moving Avg] )", MONEY, "Time Intelligence"),
    ("Late Delivery % (Trend)", "IF ( MAX ( 'Date'[In Analysis Window] ) = 1, [Late Delivery %] )", PCT, "Time Intelligence"),
    ("Avg Review Score (Trend)", "IF ( MAX ( 'Date'[In Analysis Window] ) = 1, [Avg Review Score] )", "0.00", "Time Intelligence"),
    # ---- Product & seller (item grain)
    ("Item Revenue", "CALCULATE ( SUM ( fact_order_items[price] ), fact_order_items[is_valid] = 1 )", MONEY, "Product & Seller"),
    ("Item Freight", "CALCULATE ( SUM ( fact_order_items[freight_value] ), fact_order_items[is_valid] = 1 )", MONEY, "Product & Seller"),
    ("Items Sold", "CALCULATE ( COUNTROWS ( fact_order_items ), fact_order_items[is_valid] = 1 )", "#,0", "Product & Seller"),
    ("Item Orders", "CALCULATE ( DISTINCTCOUNT ( fact_order_items[order_id] ), fact_order_items[is_valid] = 1 )", "#,0", "Product & Seller"),
    ("Freight to Price %", "DIVIDE ( [Item Freight], [Item Revenue] )", PCT, "Product & Seller"),
    ("Item Avg Review", "CALCULATE ( AVERAGE ( fact_order_items[review_score] ), fact_order_items[is_valid] = 1 )", "0.00", "Product & Seller"),
    ("Item Late Delivery %",
     "DIVIDE ( CALCULATE ( COUNTROWS ( fact_order_items ), fact_order_items[is_late] = 1 ), "
     "CALCULATE ( COUNTROWS ( fact_order_items ), fact_order_items[is_delivered] = 1 ) )", PCT, "Product & Seller"),
    # HASONEVALUE: rank only on a single category row, never on the Total row
    ("Category Rank",
     "IF (\n    HASONEVALUE ( dim_products[category] ) && NOT ISBLANK ( [Item Revenue] ),\n"
     "    RANKX ( ALLSELECTED ( dim_products[category] ), [Item Revenue], , DESC, DENSE )\n)",
     "0", "Product & Seller"),
    ("Category Share %", "DIVIDE ( [Item Revenue], CALCULATE ( [Item Revenue], ALLSELECTED ( dim_products[category] ) ) )", PCT, "Product & Seller"),
    ("Category Cumulative %",
     "VAR CurrentRevenue = [Item Revenue]\n"
     "VAR Categories = ADDCOLUMNS ( ALLSELECTED ( dim_products[category] ), \"@rev\", [Item Revenue] )\n"
     "VAR Cumulative = SUMX ( FILTER ( Categories, [@rev] >= CurrentRevenue ), [@rev] )\n"
     "RETURN IF ( NOT ISBLANK ( CurrentRevenue ), DIVIDE ( Cumulative, SUMX ( Categories, [@rev] ) ) )",
     PCT, "Product & Seller"),
    ("Item Revenue Top 10", "IF ( [Category Rank] <= 10, [Item Revenue] )", MONEY, "Product & Seller"),
    # Pareto chart shows the top 20 categories (enough to cross 80%) so the labels stay readable;
    # the cumulative % is still measured against ALL categories.
    ("Item Revenue Top 20", "IF ( [Category Rank] <= 20, [Item Revenue] )", MONEY, "Product & Seller"),
    ("Category Cumulative % Top 20", "IF ( [Category Rank] <= 20, [Category Cumulative %] )", PCT, "Product & Seller"),
    ("Active Sellers", "CALCULATE ( DISTINCTCOUNT ( fact_order_items[seller_id] ), fact_order_items[is_valid] = 1 )", "#,0", "Product & Seller"),
    ("Seller CX Flag",
     'IF ( NOT HASONEVALUE ( dim_sellers[seller_id] ) || ISBLANK ( [Item Revenue] ), BLANK (), '
     'IF ( [Item Avg Review] < 3.5 || [Item Late Delivery %] > 0.15, "Review", "OK" ) )',
     None, "Product & Seller"),
]

RELATIONSHIPS = [  # (many table, many column, one table, one column)
    ("fact_orders", "purchase_date", "Date", "Date"),
    ("fact_order_items", "purchase_date", "Date", "Date"),
    ("fact_payments", "purchase_date", "Date", "Date"),
    ("fact_orders", "customer_unique_id", "dim_customers", "customer_unique_id"),
    ("fact_order_items", "customer_unique_id", "dim_customers", "customer_unique_id"),
    ("fact_order_items", "product_id", "dim_products", "product_id"),
    ("fact_order_items", "seller_id", "dim_sellers", "seller_id"),
    ("dim_customers", "customer_state", "dim_states", "state_code"),
]


def build_model():
    folder = str(C.PROCESSED_DIR) + "\\"
    tables = []
    for t in TABLES:
        types = column_types(t)
        tables.append({
            "name": t,
            "lineageTag": str(uuid.uuid4()),
            "columns": [{"name": c, "dataType": d, "sourceColumn": c, "summarizeBy": "none",
                         "lineageTag": str(uuid.uuid4()),
                         **({"formatString": "yyyy-mm-dd"} if c in DATE_COLS else {})}
                        for c, d, _ in types],
            "partitions": [{"name": t, "mode": "import",
                            "source": {"type": "m", "expression": csv_partition(t, types)}}],
        })
    date_cols = []
    for c, d in DATE_COLUMNS:
        col = {"name": c, "dataType": d, "sourceColumn": c, "summarizeBy": "none",
               "lineageTag": str(uuid.uuid4())}
        if c == "Date":
            col.update({"isKey": True, "formatString": "yyyy-mm-dd"})
        if c == "Month":
            col["sortByColumn"] = "Month Num"
        if c == "Weekday":
            col["sortByColumn"] = "Weekday Num"
        date_cols.append(col)
    tables.append({"name": "Date", "dataCategory": "Time", "lineageTag": str(uuid.uuid4()),
                   "columns": date_cols,
                   "partitions": [{"name": "Date", "mode": "import", "source": {"type": "m", "expression": DATE_M}}]})
    measures = []
    for name, dax, fmt, folder_name in MEASURES:
        m = {"name": name, "expression": dax.split("\n") if "\n" in dax else dax,
             "displayFolder": folder_name, "lineageTag": str(uuid.uuid4())}
        if fmt:
            m["formatString"] = fmt
        measures.append(m)
    tables.append({
        "name": M, "lineageTag": str(uuid.uuid4()),
        "columns": [{"name": "Placeholder", "dataType": "string", "sourceColumn": "Placeholder",
                     "isHidden": True, "summarizeBy": "none", "lineageTag": str(uuid.uuid4())}],
        "partitions": [{"name": M, "mode": "import", "source": {"type": "m", "expression": [
            "let", '    Source = #table(type table [Placeholder = text], {})', "in", "    Source"]}}],
        "measures": measures,
    })
    rels = [{"name": str(uuid.uuid4()), "fromTable": a, "fromColumn": b, "toTable": c, "toColumn": d}
            for a, b, c, d in RELATIONSHIPS]
    query_order = ["DataFolder"] + TABLES + ["Date", M]
    return {
        "compatibilityLevel": 1567,
        "model": {
            "culture": "en-US",
            "dataAccessOptions": {"legacyRedirects": True, "returnErrorValuesAsNull": True},
            "defaultPowerBIDataSourceVersion": "powerBI_V3",
            "sourceQueryCulture": "en-US",
            "tables": tables,
            "relationships": rels,
            "expressions": [{
                "name": "DataFolder", "kind": "m", "lineageTag": str(uuid.uuid4()),
                "expression": f'"{folder}" meta [IsParameterQuery = true, Type = "Text", IsParameterQueryRequired = true]',
            }],
            "annotations": [
                {"name": "PBI_QueryOrder", "value": json.dumps(query_order)},
                {"name": "__PBI_TimeIntelligenceEnabled", "value": "0"},
                {"name": "PBIDesktopVersion", "value": "2.149.1054.0"},
            ],
        },
    }


# --------------------------------------------------------------------------- #
# 2. REPORT
# --------------------------------------------------------------------------- #
def lit(v):
    if isinstance(v, bool):
        return {"expr": {"Literal": {"Value": "true" if v else "false"}}}
    if isinstance(v, (int, float)):
        return {"expr": {"Literal": {"Value": f"{v}D"}}}
    return {"expr": {"Literal": {"Value": "'" + str(v).replace("'", "''") + "'"}}}


def hexid():
    return uuid.uuid4().hex[:20]


def col(table, name):
    return ("col", table, name)


def mea(name):
    return ("mea", M, name)


def field_expr(f, alias):
    kind, _, name = f
    key = "Column" if kind == "col" else "Measure"
    return {key: {"Expression": {"SourceRef": {"Source": alias}}, "Property": name}}


def query_ref(f):
    return f"{f[1]}.{f[2]}"


class Page:
    def __init__(self, name, ordinal):
        self.name, self.ordinal, self.visuals, self.z = name, ordinal, [], 0

    def add(self, vtype, x, y, w, h, roles=None, title=None, sort=None, objects=None, extra_vc=None):
        """roles: {role: [field, ...]}. sort: (field, 'asc'|'desc')."""
        self.z += 1000
        sv = {"visualType": vtype, "drillFilterOtherVisuals": True}
        if roles:
            aliases, frm = {}, []
            for fields in roles.values():
                for f in fields:
                    if f[1] not in aliases:
                        a = f"t{len(aliases)}"
                        aliases[f[1]] = a
                        frm.append({"Name": a, "Entity": f[1], "Type": 0})
            select, seen = [], set()
            for fields in roles.values():
                for f in fields:
                    if query_ref(f) in seen:
                        continue
                    seen.add(query_ref(f))
                    e = field_expr(f, aliases[f[1]])
                    e.update({"Name": query_ref(f), "NativeReferenceName": f[2]})
                    select.append(e)
            # "active" marks the drill level of an axis. Only charts' Category / matrix Rows / slicers
            # use it. On a table it would hide every column except the first.
            def is_active(i, r, f):
                return i == 0 and f[0] == "col" and (r in ("Category", "Rows") or vtype == "slicer")
            sv["projections"] = {r: [{"queryRef": query_ref(f), **({"active": True} if is_active(i, r, f) else {})}
                                     for i, f in enumerate(fs)] for r, fs in roles.items()}
            pq = {"Version": 2, "From": frm, "Select": select}
            if sort:
                f, direction = sort
                pq["OrderBy"] = [{"Direction": 1 if direction == "asc" else 2,
                                  "Expression": field_expr(f, aliases[f[1]])}]
            sv["prototypeQuery"] = pq
            if sort:
                sv["hasDefaultSort"] = True
        if objects:
            sv["objects"] = objects
        vc = {}
        if title:
            vc["title"] = [{"properties": {"show": lit(True), "text": lit(title),
                                           "fontSize": lit(11)}}]
        if extra_vc:
            vc.update(extra_vc)
        if vc:
            sv["vcObjects"] = vc
        cfg = {"name": hexid(), "layouts": [{"id": 0, "position": {"x": x, "y": y, "z": self.z, "width": w,
                                                                   "height": h, "tabOrder": self.z}}],
               "singleVisual": sv}
        self.visuals.append({"x": x, "y": y, "z": self.z, "width": w, "height": h,
                             "config": json.dumps(cfg), "filters": "[]", "tabOrder": self.z})

    # ---- convenience builders ------------------------------------------------ #
    def header(self, title, subtitle):
        objects = {"general": [{"properties": {"paragraphs": [
            {"textRuns": [{"value": title, "textStyle": {"fontWeight": "bold", "fontSize": "20pt", "color": "#0F172A"}}]},
            {"textRuns": [{"value": subtitle, "textStyle": {"fontSize": "10pt", "color": "#475569"}}]},
        ]}}]}
        self.add("textbox", 16, 4, 820, 62, objects=objects,
                 extra_vc={"background": [{"properties": {"show": lit(False)}}],
                           "border": [{"properties": {"show": lit(False)}}]})

    def slicer(self, field, x, title, w=200):
        self.add("slicer", x, 8, w, 56, roles={"Values": [field]},
                 objects={"data": [{"properties": {"mode": lit("Dropdown")}}],
                          "header": [{"properties": {"text": lit(title)}}]})

    def cards(self, measures, y=74, h=88):
        n = len(measures)
        gap = 12
        w = (1280 - 32 - gap * (n - 1)) // n
        for i, name in enumerate(measures):
            self.add("card", 16 + i * (w + gap), y, w, h, roles={"Values": [mea(name)]},
                     objects={"labels": [{"properties": {"fontSize": lit(22)}}],
                              "categoryLabels": [{"properties": {"show": lit(True), "fontSize": lit(10)}}]})

    def textnote(self, text, x, y, w, h):
        objects = {"general": [{"properties": {"paragraphs": [
            {"textRuns": [{"value": text, "textStyle": {"fontSize": "10pt", "color": "#1E3A8A"}}]}]}}]}
        self.add("textbox", x, y, w, h, objects=objects)

    def to_section(self):
        return {"name": hexid(), "displayName": self.name, "displayOption": 1, "width": 1280, "height": 720,
                "ordinal": self.ordinal, "filters": "[]", "config": "{}", "visualContainers": self.visuals}


LABELS_ON = {"labels": [{"properties": {"show": lit(True)}}]}


def table_style(widths: dict):
    """Fixed column widths (px) for a table visual so every column fits without side-scrolling.
    widths: {field: px}. Also: compact 9pt text and wrapped headers."""
    return {
        "columnWidth": [{"properties": {"value": {"expr": {"Literal": {"Value": f"{px}D"}}}},
                         "selector": {"metadata": query_ref(f)}} for f, px in widths.items()],
        "values": [{"properties": {"fontSize": lit(9)}}],
        "columnHeaders": [{"properties": {"fontSize": lit(9), "wordWrap": lit(True)}}],
        "total": [{"properties": {"fontSize": lit(9)}}],
    }


def build_pages():
    d_ym = col("Date", "Year Month")
    pages = []

    # ---------------- Page 1: Executive Overview
    p = Page("Executive Overview", 0)
    p.header("Olist E-Commerce | Executive Overview",
             "99k marketplace orders, Brazil, Sep 2016 - Oct 2018. Trends show complete months (Jan 2017 - Aug 2018).")
    p.slicer(col("Date", "Year"), 860, "Year")
    p.slicer(col("dim_states", "region"), 1070, "Customer region")
    p.cards(["GMV", "Orders", "AOV", "Customers", "Avg Review Score", "Late Delivery %"])
    p.add("lineClusteredColumnComboChart", 16, 174, 820, 270,
          roles={"Category": [d_ym], "Y": [mea("Orders (Trend)")], "Y2": [mea("GMV (Trend)")]},
          title="Monthly orders (columns) and GMV (line)", sort=(d_ym, "asc"))
    p.add("barChart", 848, 174, 416, 270,
          roles={"Category": [col("dim_products", "category")], "Y": [mea("Item Revenue Top 10")]},
          title="Top 10 categories by product revenue", sort=(mea("Item Revenue Top 10"), "desc"),
          objects=LABELS_ON)
    p.add("barChart", 16, 456, 500, 252,
          roles={"Category": [col("dim_states", "state_name")], "Y": [mea("GMV")]},
          title="GMV by customer state", sort=(mea("GMV"), "desc"))
    p.add("lineChart", 528, 456, 736, 252,
          roles={"Category": [d_ym], "Y": [mea("GMV (Trend)"), mea("GMV 3M Moving Avg (Trend)")]},
          title="GMV trend with 3-month moving average", sort=(d_ym, "asc"))
    pages.append(p)

    # ---------------- Page 2: Customers & Retention
    p = Page("Customers & Retention", 1)
    p.header("Customers & Retention",
             "Customer = customer_unique_id. Only ~3% of customers ever place a second order.")
    p.slicer(col("dim_states", "region"), 1070, "Customer region")
    p.cards(["Customers", "New Customers", "Returning Customers", "Repeat Customer Rate %", "GMV per Customer"])
    grad = {"values": [{"properties": {"backColor": {"solid": {"color": {"expr": {"FillRule": {
        "Input": {"Measure": {"Expression": {"SourceRef": {"Entity": M}}, "Property": "Cohort Retention %"}},
        "FillRule": {"linearGradient2": {
            "min": {"color": {"Literal": {"Value": "'#FFFFFF'"}}},
            "max": {"color": {"Literal": {"Value": "'#2563EB'"}}},
            "nullColoringStrategy": {"strategy": {"Literal": {"Value": "'asZero'"}}}}}}}}}}},
        "selector": {"data": [{"dataViewWildcard": {"matchingOption": 1}}], "metadata": f"{M}.Cohort Retention %"}}],
        "subTotals": [{"properties": {"rowSubtotals": lit(False), "columnSubtotals": lit(False)}}]}
    p.add("pivotTable", 16, 174, 740, 534,
          roles={"Rows": [col("cohort_retention", "cohort_month")],
                 "Columns": [col("cohort_retention", "month_offset")],
                 "Values": [mea("Cohort Retention %")]},
          title="Cohort retention: % of each month's new customers who order again N months later",
          objects=grad)
    p.add("treemap", 768, 174, 496, 250,
          roles={"Group": [col("dim_customers", "rfm_segment")], "Values": [mea("GMV")]},
          title="GMV by RFM segment", objects=LABELS_ON)
    rfm_cols = {col("dim_customers", "rfm_segment"): 130, mea("Customers"): 66, mea("GMV"): 96,
                mea("GMV per Customer"): 82, mea("Avg Review Score"): 64}
    p.add("tableEx", 768, 436, 496, 272, roles={"Values": list(rfm_cols)},
          title="RFM segment summary", sort=(mea("GMV"), "desc"), objects=table_style(rfm_cols))
    pages.append(p)

    # ---------------- Page 3: Products & Sellers
    p = Page("Products & Sellers", 2)
    p.header("Products & Sellers",
             "Item-level view. 18 of 74 categories make 80% of product revenue.")
    p.slicer(col("Date", "Year"), 860, "Year")
    p.slicer(col("dim_products", "category"), 1070, "Category")
    p.cards(["Item Revenue", "Items Sold", "Active Sellers", "Freight to Price %", "Item Avg Review"])
    p.add("lineClusteredColumnComboChart", 16, 174, 1248, 250,
          roles={"Category": [col("dim_products", "category")], "Y": [mea("Item Revenue Top 20")],
                 "Y2": [mea("Category Cumulative % Top 20")]},
          title="Category Pareto, top 20 of 74: revenue (columns) and cumulative share of ALL revenue (line)",
          sort=(mea("Item Revenue Top 20"), "desc"))
    cat_cols = {col("dim_products", "category"): 150, mea("Category Rank"): 50, mea("Item Revenue"): 92,
                mea("Category Share %"): 70, mea("Freight to Price %"): 74, mea("Item Avg Review"): 70}
    p.add("tableEx", 16, 436, 612, 272, roles={"Values": list(cat_cols)},
          title="Category scorecard", sort=(mea("Item Revenue"), "desc"), objects=table_style(cat_cols))
    seller_cols = {col("dim_sellers", "seller_id"): 170, col("dim_sellers", "seller_state"): 44,
                   mea("Item Orders"): 52, mea("Item Revenue"): 84, mea("Item Avg Review"): 60,
                   mea("Item Late Delivery %"): 62, mea("Seller CX Flag"): 52}
    p.add("tableEx", 640, 436, 624, 272, roles={"Values": list(seller_cols)},
          title="Seller scorecard (flag = review < 3.5 or > 15% late)", sort=(mea("Item Revenue"), "desc"),
          objects=table_style(seller_cols))
    pages.append(p)

    # ---------------- Page 4: Delivery & Customer Experience
    p = Page("Delivery & Customer Experience", 3)
    p.header("Delivery & Customer Experience",
             "Late = delivered after the promised date. Late orders are 6.7x more likely to get a 1-2 star review.")
    p.slicer(col("Date", "Year"), 860, "Year")
    p.slicer(col("dim_states", "region"), 1070, "Customer region")
    p.cards(["Avg Delivery Days", "Avg Promised Days", "Late Delivery %", "Negative Review %",
             "Review Gap Late vs On Time"])
    p.add("columnChart", 16, 174, 620, 250,
          roles={"Category": [col("fact_orders", "delay_bucket")], "Y": [mea("Avg Review (Delivered)")]},
          title="Average review score by delivery delay", sort=(col("fact_orders", "delay_bucket"), "asc"),
          objects=LABELS_ON)
    p.add("barChart", 648, 174, 616, 250,
          roles={"Category": [col("dim_states", "state_name")], "Y": [mea("Late Delivery %")]},
          title="Late-delivery rate by customer state", sort=(mea("Late Delivery %"), "desc"))
    p.add("lineChart", 16, 436, 620, 236,
          roles={"Category": [d_ym], "Y": [mea("Late Delivery % (Trend)")]},
          title="Late-delivery rate by month", sort=(d_ym, "asc"))
    p.add("columnChart", 648, 436, 616, 272,
          roles={"Category": [col("fact_orders", "review_score")], "Y": [mea("Orders")]},
          title="Review score distribution (orders)", sort=(col("fact_orders", "review_score"), "asc"),
          objects=LABELS_ON)
    p.add("card", 16, 678, 620, 32, roles={"Values": [mea("Insight Late Reviews")]},
          objects={"labels": [{"properties": {"fontSize": lit(11)}}],
                   "categoryLabels": [{"properties": {"show": lit(False)}}]})
    pages.append(p)
    return pages


def build_report():
    theme_name = "OlistTheme.json"
    config = {
        "version": "5.68",
        "themeCollection": {
            "baseTheme": {"name": "CY25SU11", "version": {"visual": "2.4.0", "report": "3.0.0", "page": "2.3.0"}, "type": 2},
            "customTheme": {"name": theme_name, "reportVersionAtImport": {"visual": "2.4.0", "report": "3.0.0", "page": "2.3.0"}, "type": 1},
        },
        "activeSectionIndex": 0,
        "defaultDrillFilterOtherVisuals": True,
        "settings": {"useNewFilterPaneExperience": True, "allowChangeFilterTypes": True,
                     "useStylableVisualContainerHeader": True, "exportDataMode": 1,
                     "useEnhancedTooltips": True},
    }
    return {
        "config": json.dumps(config),
        "layoutOptimization": 0,
        "resourcePackages": [
            {"resourcePackage": {"name": "SharedResources", "type": 2, "disabled": False,
                                 "items": [{"type": 202, "path": "BaseThemes/CY25SU11.json", "name": "CY25SU11"}]}},
            {"resourcePackage": {"name": "RegisteredResources", "type": 1, "disabled": False,
                                 "items": [{"type": 201, "path": theme_name, "name": theme_name}]}},
        ],
        "sections": [p.to_section() for p in build_pages()],
    }, theme_name


# --------------------------------------------------------------------------- #
def write_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def main():
    for d in (SM_DIR, RPT_DIR):
        if d.exists():
            shutil.rmtree(d)
    # Semantic model
    write_json(SM_DIR / "definition.pbism", {"version": "1.0", "settings": {}})
    write_json(SM_DIR / "model.bim", build_model())
    # Report
    report, theme_name = build_report()
    write_json(RPT_DIR / "definition.pbir",
               {"version": "4.0", "datasetReference": {"byPath": {"path": f"../{NAME}.SemanticModel"}}})
    write_json(RPT_DIR / "report.json", report)
    res = RPT_DIR / "StaticResources"
    shutil.copytree(HERE / "_template" / "SharedResources", res / "SharedResources")
    theme = json.loads((HERE / "olist_theme.json").read_text(encoding="utf-8"))
    theme["name"] = theme_name
    write_json(res / "RegisteredResources" / theme_name, theme)
    # Project file
    write_json(HERE / f"{NAME}.pbip",
               {"version": "1.0", "artifacts": [{"report": {"path": f"{NAME}.Report"}}],
                "settings": {"enableAutoRecovery": True}})
    (HERE / ".gitignore").write_text("**/.pbi/localSettings.json\n**/.pbi/cache.abf\n", encoding="utf-8")
    n_vis = sum(len(s["visualContainers"]) for s in report["sections"])
    print(f"Wrote {NAME}.pbip: {len(TABLES) + 2} tables, {len(MEASURES)} measures, "
          f"{len(RELATIONSHIPS)} relationships, {len(report['sections'])} pages, {n_vis} visuals")


if __name__ == "__main__":
    main()
